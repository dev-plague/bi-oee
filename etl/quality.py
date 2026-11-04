"""Reglas de calidad de datos y bitácora."""
from __future__ import annotations

from typing import Any

import pandas as pd

from clean import CleanResult


def _check(
    regla: str,
    severidad: str,
    tabla: str,
    filas: int | None,
    detalle: str,
) -> dict[str, Any]:
    # Una regla que no encuentra filas afectadas pasa: se registra como INFO.
    if filas is not None and int(filas) == 0 and severidad in ("ERROR", "WARN"):
        severidad = "INFO"
        detalle = "OK. " + detalle
    return {
        "regla": regla,
        "severidad": severidad,
        "tabla": tabla,
        "filas_afectadas": None if filas is None else int(filas),
        "detalle": detalle,
    }


def run_checks(
    clean: CleanResult,
    dims: dict[str, Any],
    facts: dict[str, Any],
    conn,
) -> list[dict[str, Any]]:
    s = clean.stats
    checks: list[dict[str, Any]] = []

    checks.append(_check("filas_leidas", "INFO", "stg.registro_crudo", s["filas_leidas"], "Filas físicas leídas del .xlsm."))
    checks.append(_check("duplicados_exactos", "WARN", "stg.registro_crudo", s["duplicados_exactos"], "Se conserva la primera ocurrencia."))
    checks.append(_check("filas_tras_dedup", "INFO", "stg.registro_crudo", s["filas_tras_dedup"], "Filas únicas usadas para el modelo."))

    checks.append(_check(
        "fechas_invalidas", "ERROR", "fact_produccion", s["fechas_invalidas"],
        "Filas sin fecha parseable; se excluyen del modelo.",
    ))
    checks.append(_check(
        "mes_inconsistente", "ERROR", "dim_tiempo", s["mes_inconsistente"],
        "El texto 'Mes' no coincide con la fecha; se usa la fecha como verdad.",
    ))
    checks.append(_check(
        "anio_inconsistente", "ERROR", "dim_tiempo", s["anio_inconsistente"],
        "El texto 'Año' no coincide con la fecha; se usa la fecha como verdad.",
    ))
    checks.append(_check(
        "maquinas_invalidas", "ERROR", "dim_maquina", s["maquinas_invalidas"],
        "Máquinas fuera del catálogo Vinilos_1..Vinilos_4.",
    ))

    neg_pacas = int((clean.raw["_pacas"] < 0).sum())
    neg_horas = int((clean.raw["_horas"] < 0).sum())
    checks.append(_check("pacas_negativas", "ERROR", "fact_produccion", neg_pacas, "Pacas < 0."))
    checks.append(_check("horas_negativas", "ERROR", "fact_produccion", neg_horas, "Horas trabajadas < 0."))

    checks.append(_check(
        "descuadre_tiempo_paro", "ERROR", "fact_paro", s["descuadre_paro_filas"],
        f"Filas donde suma(codigos en horas) != Tiempo de Paro (max {s['descuadre_paro_max']:.4f} h).",
    ))
    checks.append(_check(
        "registros_produccion", "INFO", "fact_produccion", s["registros_produccion"],
        f"Pacas={s['pacas_produccion']:.0f}; horas={s['horas_produccion']:.2f}.",
    ))
    checks.append(_check(
        "eventos_paro", "INFO", "fact_paro", s["eventos_paro"],
        f"Horas de paro={s['paro_h_total']:.2f}.",
    ))

    cobertura = (
        s["produccion_con_referencia"] / s["registros_produccion"]
        if s["registros_produccion"]
        else 0
    )
    checks.append(_check(
        "produccion_sin_referencia", "WARN", "fact_produccion", s["produccion_sin_referencia"],
        f"Cobertura de referencia={cobertura:.1%}. Sin referencia no se puede calcular Rendimiento/OEE.",
    ))
    checks.append(_check(
        "turno_sin_asignar", "WARN", "dim_turno", s["turno_sin_asignar"],
        "Turno vacío o 'No aplica'; se usa el miembro SD.",
    ))
    checks.append(_check(
        "unidad_por_display_con_turno", "WARN", "stg.registro_crudo", s["unidad_por_display_con_turno"],
        "La columna 'Unidad por display' contiene turnos; no se usa como unidad de empaque.",
    ))

    paro_mayor = int(
        (
            clean.df["es_produccion"]
            & (clean.df["paro_h"] > clean.df["horas_trabajadas"] + 0.01)
        ).sum()
    )
    checks.append(_check(
        "paro_mayor_que_horas", "WARN", "fact_produccion", paro_mayor,
        "Registros con horas de paro > horas trabajadas; el cálculo usa GREATEST(...,0).",
    ))
    checks.append(_check(
        "paro_sin_produccion", "WARN", "fact_paro", s["paro_sin_produccion_filas"],
        f"{s['paro_sin_produccion_horas']:.2f} h de paro sin producción el mismo día/máquina.",
    ))
    checks.append(_check(
        "outliers_produccion", "WARN", "fact_produccion", s["outliers"],
        "Pacas fuera de capacidad ideal, horas > 16 o pacas sin horas. Se conservan pero se marcan.",
    ))
    checks.append(_check(
        "registros_incompletos", "WARN", "fact_produccion", s["incompletos"],
        "Pacas u horas faltantes; se imputan a 0 y se marcan.",
    ))
    checks.append(_check(
        "referencias_sin_unidades_por_paca", "WARN", "dim_referencia", len(s["refs_sin_upp"]),
        "Referencias sin conversión unidades/paca: " + ", ".join(s["refs_sin_upp"][:15]),
    ))

    # Cobertura de subcódigo en los eventos.
    fp = facts.get("fact_paro")
    if fp is not None and not fp.empty:
        sub = dims["dim_subcodigo_paro"][["subcodigo_key", "subcodigo"]]
        merged = fp.merge(sub, on="subcodigo_key", how="left")
        sin_esp = int((merged["subcodigo"] == "SIN_ESP").sum())
        checks.append(_check(
            "subcodigo_sin_especificar", "WARN", "fact_paro", sin_esp,
            f"{sin_esp / len(fp):.1%} de los eventos no tienen subcódigo; se usa SIN_ESP.",
        ))
        checks.append(_check(
            "subcodigos_estimados", "INFO", "dim_subcodigo_paro",
            int(dims["dim_subcodigo_paro"]["es_estimado"].sum()),
            "Subcódigos encontrados en los datos que no estaban en el catálogo.",
        ))

    # PII: los seudónimos y hashes deben tener la forma esperada.
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM oee.dim_operario WHERE seudonimo !~ '^OP-[0-9A-F]{8}$'")
        bad_op = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM oee.dim_personal WHERE seudonimo !~ '^PM-[0-9A-F]{8}$'")
        bad_pm = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM oee.dim_operario WHERE nombre_hash !~ '^[0-9a-f]{64}$'")
        bad_hash = int(cur.fetchone()[0])
        cur.execute("SELECT payload::text FROM stg.registro_crudo")
        texts = [r[0] for r in cur.fetchall()]

    names: set[str] = set()
    for col in ("Operario", "Personal involucrado"):
        names |= {str(x).strip() for x in clean.raw[col].dropna() if str(x).strip()}
    names = {n for n in names if len(n) >= 4 and n.lower() not in {"no aplica", "operarios"}}
    # Se revisa cada texto una sola vez.
    lowered_names = [n.lower() for n in names]
    found = (
        sum(1 for t in texts if any(n in t.lower() for n in lowered_names))
        if lowered_names
        else 0
    )

    checks.append(_check(
        "pii_seudonimos", "ERROR", "dim_operario", bad_op + bad_pm,
        "Seudónimos fuera del patrón OP-xxxxxxxx / PM-xxxxxxxx.",
    ))
    checks.append(_check(
        "pii_hashes", "ERROR", "dim_operario", bad_hash,
        "Hashes de nombre fuera del patrón SHA-256.",
    ))
    checks.append(_check(
        "pii_nombres_en_staging", "ERROR", "stg.registro_crudo", found,
        "Textos de staging que aún contienen un nombre real.",
    ))

    return checks
