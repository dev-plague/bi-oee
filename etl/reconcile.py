"""Conciliación fuente -> modelo cargado."""
from __future__ import annotations

from typing import Any

from clean import CleanResult


def _row(
    metrica: str,
    fuente: float,
    cargado: float,
    detalle: str,
    tolerancia: float = 0.01,
    critico: bool = True,
    concilia: bool | None = None,
) -> dict[str, Any]:
    diff = float(cargado) - float(fuente)
    if concilia is None:
        concilia = abs(diff) <= tolerancia
    return {
        "metrica": metrica,
        "valor_fuente": float(fuente),
        "valor_cargado": float(cargado),
        "diferencia": diff,
        "tolerancia": float(tolerancia),
        "concilia": bool(concilia),
        "critico": critico,
        "detalle": detalle,
    }


def build(clean: CleanResult, conn) -> list[dict[str, Any]]:
    s = clean.stats
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*),
                   COALESCE(SUM(pacas_producidas), 0),
                   COALESCE(SUM(horas_trabajadas), 0),
                   COALESCE(SUM(unidades_producidas), 0)
            FROM oee.fact_produccion
            """
        )
        prod_count, pacas_load, horas_load, unidades_load = cur.fetchone()
        cur.execute(
            "SELECT COUNT(*), COALESCE(SUM(horas_paro), 0) FROM oee.fact_paro"
        )
        paro_count, paro_load = cur.fetchone()

    rows: list[dict[str, Any]] = []

    rows.append(_row(
        "filas_produccion", s["registros_produccion"], prod_count,
        "Registros de producción (pacas u horas) después de deduplicar.",
        tolerancia=0,
    ))
    rows.append(_row(
        "pacas_producidas", s["pacas_produccion"], pacas_load,
        "Pacas producidas; la fuente después de deduplicar.",
    ))
    rows.append(_row(
        "horas_trabajadas", s["horas_produccion"], horas_load,
        "Horas trabajadas; la fuente después de deduplicar.",
    ))
    rows.append(_row(
        "horas_paro", s["paro_h_total"], paro_load,
        "Horas de paro = suma de los 18 pares código/horas.",
    ))
    rows.append(_row(
        "eventos_paro", s["eventos_paro"], paro_count,
        "Eventos con minutos de paro > 0 (formato ancho despivotado).",
        tolerancia=0,
    ))
    rows.append(_row(
        "tiempo_paro_vs_codigos", clean.df["tiempo_paro"].sum(), paro_load,
        "Columna Tiempo de Paro vs suma de códigos cargados.",
    ))

    # Diferencias explicadas por la deduplicación (no son errores).
    rows.append(_row(
        "pacas_brutas_vs_dedup", s["pacas_brutas"], s["pacas_brutas"] - s["pacas_duplicadas"],
        f"Diferencia explicada por {s['duplicados_exactos']} filas duplicadas exactas.",
        critico=False, concilia=True,
    ))
    rows.append(_row(
        "horas_brutas_vs_dedup", s["horas_brutas"], s["horas_brutas"] - s["horas_duplicadas"],
        f"Diferencia explicada por {s['duplicados_exactos']} filas duplicadas exactas.",
        critico=False, concilia=True,
    ))
    rows.append(_row(
        "paro_bruto_vs_dedup", s["paro_h_brutas"], s["paro_h_brutas"] - s["paro_h_duplicadas"],
        f"Diferencia explicada por {s['duplicados_exactos']} filas duplicadas exactas.",
        critico=False, concilia=True,
    ))

    return rows
