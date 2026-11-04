"""Construcción de dimensiones y hechos a partir de la fuente limpia."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from catalogs import (
    code_dim_map,
    normalize_subcode,
    stable_hash,
    subcode_display_name,
)
from clean import CODE_COLS, HOUR_COLS, CleanResult
from config import AREA_TIPO, CODE_DIM, MACHINE_DIM, SHIFT_DIM, SUBCODE_CATALOG

SUBCODE_COL_BY_CODE = {
    1: "Sub Codigo de paro 1",
    3: "Subcodigo 3",
    5: "Subcodigo 5",
}


def _none_if_nan(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _area_order() -> list[str]:
    names: list[str] = []
    for _, _, area, _, _, _ in CODE_DIM:
        if area not in names:
            names.append(area)
    return names


def build_dimensions(clean: CleanResult, catalog: dict[str, dict]) -> dict[str, pd.DataFrame]:
    df = clean.df

    # ---- dim_area ------------------------------------------------------
    area_names = _area_order()
    for name in df["area_involucrada"].dropna().unique():
        if name not in area_names:
            area_names.append(name)
    dim_area = pd.DataFrame(
        {
            "area_key": range(1, len(area_names) + 1),
            "nombre": area_names,
            "tipo": [AREA_TIPO.get(n, "Otro") for n in area_names],
        }
    )
    area_key = dict(zip(dim_area["nombre"], dim_area["area_key"]))

    # ---- dim_maquina ---------------------------------------------------
    dim_maquina = pd.DataFrame(
        [
            {
                "maquina_key": i,
                "codigo": codigo,
                "nombre": nombre,
                "factor_produccion_legacy": factor,
                "activa": activa,
            }
            for i, (codigo, nombre, factor, activa) in enumerate(MACHINE_DIM, start=1)
        ]
    )
    maquina_key = dict(zip(dim_maquina["codigo"], dim_maquina["maquina_key"]))

    # ---- dim_turno -----------------------------------------------------
    dim_turno = pd.DataFrame(
        [
            {
                "turno_key": i,
                "codigo": codigo,
                "nombre": nombre,
                "hora_inicio": inicio,
                "hora_fin": fin,
                "duracion_horas": duracion,
                "es_nocturno": nocturno,
                "es_valido": valido,
            }
            for i, (codigo, nombre, inicio, fin, duracion, nocturno, valido) in enumerate(
                SHIFT_DIM, start=1
            )
        ]
    )
    turno_key = dict(zip(dim_turno["codigo"], dim_turno["turno_key"]))

    # ---- dim_referencia (SCD2, versión 1) ------------------------------
    ref_names = set(df["referencia_norm"].unique()) | set(catalog.keys()) | {"SIN_REF"}
    ref_rows = []
    ref_key: dict[str, int] = {}
    for i, name in enumerate(sorted(ref_names, key=lambda x: (x == "SIN_REF", x)), start=1):
        info = (
            {
                "num_colores": None,
                "unidades_por_display": None,
                "unidades_por_paca": None,
                "unidades_por_minuto_ideal": None,
                "origen": "ETL",
            }
            if name == "SIN_REF"
            else catalog.get(name)
        )
        if info is None:
            # La referencia existe en los datos pero no en el catálogo:
            # derive_reference ya se aplicó en clean; se recupera de la fila.
            row = df.loc[df["referencia_norm"] == name].iloc[0]
            info = {
                "num_colores": _none_if_nan(row["num_colores"]),
                "unidades_por_display": _none_if_nan(row["unidades_por_display"]),
                "unidades_por_paca": _none_if_nan(row["upp"]),
                "unidades_por_minuto_ideal": _none_if_nan(row["ideal_speed"]),
                "origen": row["origen_ref"],
            }
        ref_key[name] = i
        ref_rows.append(
            {
                "referencia_key": i,
                "referencia_natural": name,
                "nombre_normalizado": "Sin referencia" if name == "SIN_REF" else name,
                "num_colores": info["num_colores"],
                "unidades_por_display": info["unidades_por_display"],
                "unidades_por_paca": info["unidades_por_paca"],
                "unidades_por_minuto_ideal": info["unidades_por_minuto_ideal"] or 72,
                "vigente_desde": pd.Timestamp("1900-01-01").date(),
                "vigente_hasta": pd.Timestamp("9999-12-31").date(),
                "es_vigente": True,
                "version": 1,
                "origen": info["origen"],
            }
        )
    dim_referencia = pd.DataFrame(ref_rows)

    # ---- dim_operario --------------------------------------------------
    op = (
        df[["operario_seudonimo", "operario_hash", "operario_valido"]]
        .drop_duplicates(subset=["operario_seudonimo"])
        .rename(columns={"operario_valido": "es_valido"})
        .sort_values("operario_seudonimo")
        .reset_index(drop=True)
    )
    if "OP-00000000" not in set(op["operario_seudonimo"]):
        op = pd.concat(
            [
                pd.DataFrame(
                    [
                        {
                            "operario_seudonimo": "OP-00000000",
                            "operario_hash": stable_hash("SIN_ASIGNADO"),
                            "es_valido": False,
                        }
                    ]
                ),
                op,
            ],
            ignore_index=True,
        )
    op.insert(0, "operario_key", range(1, len(op) + 1))
    op = op.rename(columns={"operario_seudonimo": "seudonimo", "operario_hash": "nombre_hash"})
    op["activo"] = True
    dim_operario = op[["operario_key", "seudonimo", "nombre_hash", "activo", "es_valido"]]
    operario_key = dict(zip(dim_operario["seudonimo"], dim_operario["operario_key"]))

    # ---- dim_codigo_paro ----------------------------------------------
    code_map = code_dim_map()
    dim_codigo_paro = pd.DataFrame(
        [
            {
                "codigo_key": i,
                "codigo": c,
                "nombre": code_map[c]["nombre"],
                "area_key": area_key[code_map[c]["area_impacto"]],
                "categoria": code_map[c]["categoria"],
                "es_programado": code_map[c]["es_programado"],
                "documentado_pmto22": code_map[c]["documentado_pmto22"],
            }
            for i, c in enumerate(range(1, 19), start=1)
        ]
    )
    codigo_key = dict(zip(dim_codigo_paro["codigo"], dim_codigo_paro["codigo_key"]))

    # ---- dim_subcodigo_paro -------------------------------------------
    subcodes: dict[tuple[int, str], str] = {
        (c, s): n for c, s, n in SUBCODE_CATALOG
    }
    for code in (1, 3, 5):
        col = SUBCODE_COL_BY_CODE[code]
        for raw, norm in zip(df[col], df[col].map(lambda x, c=code: normalize_subcode(x, c))):
            if norm == "SIN_ESP":
                subcodes.setdefault((code, norm), "Sin especificar")
            elif (code, norm) not in subcodes:
                subcodes[(code, norm)] = subcode_display_name(code, norm, raw)
    for code in range(1, 19):
        subcodes.setdefault((code, "SIN_ESP"), "Sin especificar")

    sub_rows = []
    sub_key: dict[tuple[int, str], int] = {}
    for i, ((code, sub), nombre) in enumerate(sorted(subcodes.items()), start=1):
        parts = sub.split(".")
        nivel = len(parts) if sub != "SIN_ESP" else 2
        parent = ".".join(parts[:-1]) if nivel >= 3 else None
        sub_key[(code, sub)] = i
        sub_rows.append(
            {
                "subcodigo_key": i,
                "codigo_key": codigo_key[code],
                "subcodigo": sub,
                "nombre": nombre,
                "nivel": nivel,
                "subcodigo_padre": parent,
                "ruta": f"{code}|{sub}",
                "es_estimado": (code, sub) not in set(
                    (c, s) for c, s, _ in SUBCODE_CATALOG
                ) and sub != "SIN_ESP",
            }
        )
    dim_subcodigo_paro = pd.DataFrame(sub_rows)

    # ---- dim_personal --------------------------------------------------
    pm = (
        df.loc[df["personal_seudonimo"].notna(), ["personal_seudonimo", "personal_hash", "area_involucrada"]]
        .drop_duplicates(subset=["personal_seudonimo"])
        .copy()
    )
    pm["area_key"] = pm["area_involucrada"].map(area_key)
    pm = pm.sort_values("personal_seudonimo").reset_index(drop=True)
    pm.insert(0, "personal_key", range(1, len(pm) + 1))
    pm = pm.rename(
        columns={
            "personal_seudonimo": "seudonimo",
            "personal_hash": "nombre_hash",
        }
    )
    pm["es_valido"] = True
    dim_personal = pm[["personal_key", "seudonimo", "nombre_hash", "area_key", "es_valido"]]
    personal_key = dict(zip(dim_personal["seudonimo"], dim_personal["personal_key"]))

    return {
        "dim_area": dim_area,
        "dim_maquina": dim_maquina,
        "dim_turno": dim_turno,
        "dim_referencia": dim_referencia,
        "dim_operario": dim_operario,
        "dim_codigo_paro": dim_codigo_paro,
        "dim_subcodigo_paro": dim_subcodigo_paro,
        "dim_personal": dim_personal,
        "_keys": {
            "area": area_key,
            "maquina": maquina_key,
            "turno": turno_key,
            "referencia": ref_key,
            "operario": operario_key,
            "codigo": codigo_key,
            "subcodigo": sub_key,
            "personal": personal_key,
        },
    }


def build_facts(clean: CleanResult, dims: dict[str, Any]) -> dict[str, pd.DataFrame]:
    df = clean.df
    keys = dims["_keys"]

    prod = df.loc[df["es_produccion"]].copy()
    fact_produccion = pd.DataFrame(
        {
            "tiempo_key": prod["tiempo_key"].astype(int),
            "maquina_key": prod["maquina"].map(keys["maquina"]),
            "turno_key": prod["turno_codigo"].map(keys["turno"]),
            "referencia_key": prod["referencia_norm"].map(keys["referencia"]),
            "operario_key": prod["operario_seudonimo"].map(keys["operario"]),
            "origen_fila": prod["origen_fila"].astype(int),
            "pacas_producidas": prod["pacas"].astype(float),
            "horas_trabajadas": prod["horas_trabajadas"].astype(float),
            "horas_no_trabajadas_dia": prod["horas_no_trabajadas_dia"],
            "unidades_producidas": prod["unidades"],
            "minutos_ideales": prod["minutos_ideales"],
            "tipo_paro_texto": prod["tipo_paro_texto"],
            "observaciones": prod["observaciones"],
            "es_outlier": prod["es_outlier"].astype(bool),
            "es_incompleto": prod["es_incompleto"].astype(bool),
            "hash_origen": [
                stable_hash(r.origen_fila, r.fecha, r.maquina, r.pacas, r.horas_trabajadas, r.referencia_norm)
                for r in prod.itertuples()
            ],
        }
    )

    code_map = code_dim_map()

    # Despivotado robusto del formato ancho: una columna de código = un evento.
    event_frames = []
    for code in range(1, 19):
        col_min = f"Codigo de paro {code}"
        col_h = f"Codigo {code} en horas"
        minutos = pd.to_numeric(df[col_min], errors="coerce")
        horas = pd.to_numeric(df[col_h], errors="coerce")
        mask = minutos.fillna(0) > 0
        if not mask.any():
            continue
        sub_col = SUBCODE_COL_BY_CODE.get(code)
        sub_raw = df[sub_col] if sub_col in df.columns else pd.Series([None] * len(df), index=df.index)
        sub_norm = sub_raw.map(lambda x, c=code: normalize_subcode(x, c))
        part = pd.DataFrame(
            {
                "tiempo_key": df["tiempo_key"].astype(int),
                "maquina_key": df["maquina"].map(keys["maquina"]),
                "turno_key": df["turno_codigo"].map(keys["turno"]),
                "referencia_key": df["referencia_norm"].map(keys["referencia"]),
                "operario_key": df["operario_seudonimo"].map(keys["operario"]),
                "codigo_key": keys["codigo"][code],
                "subcodigo_key": [
                    keys["subcodigo"][(code, s)] for s in sub_norm
                ],
                "area_key": [
                    keys["area"].get(a) if isinstance(a, str) else keys["area"][code_map[code]["area_impacto"]]
                    for a in df["area_involucrada"]
                ],
                "personal_key": [
                    keys["personal"].get(p) if isinstance(p, str) else None
                    for p in df["personal_seudonimo"]
                ],
                "origen_fila": df["origen_fila"].astype(int),
                "origen_columna": code,
                "minutos_paro": minutos,
                "horas_paro": np.where(
                    horas.fillna(0) > 0, horas, minutos / 60.0
                ),
                "area_involucrada_texto": df["area_involucrada"],
                "tipo_paro_texto": df["tipo_paro_texto"],
                "observacion_paro": df["observacion_paro"],
                "es_sin_produccion": df["es_sin_produccion"].astype(bool),
                "hash_origen": [
                    stable_hash(f, code, m, s, a)
                    for f, m, s, a in zip(
                        df["origen_fila"], minutos, sub_norm, df["area_involucrada"]
                    )
                ],
                "_mask": mask,
            }
        )
        part = part.loc[mask.values]
        # Para códigos distintos de 1, 3 y 5, el área de impacto es la del código.
        if code not in (1, 3, 5):
            part["area_key"] = keys["area"][code_map[code]["area_impacto"]]
            part["personal_key"] = None
        event_frames.append(part)

    fact_paro = (
        pd.concat(event_frames, ignore_index=True)
        if event_frames
        else pd.DataFrame(
            columns=[
                "tiempo_key", "maquina_key", "turno_key", "referencia_key",
                "operario_key", "codigo_key", "subcodigo_key", "area_key",
                "personal_key", "origen_fila", "origen_columna", "minutos_paro",
                "horas_paro", "area_involucrada_texto", "tipo_paro_texto",
                "observacion_paro", "es_sin_produccion", "hash_origen",
            ]
        )
    )
    fact_paro = fact_paro.drop(columns=["_mask"], errors="ignore")

    return {"fact_produccion": fact_produccion, "fact_paro": fact_paro}


def build_staging(clean: CleanResult, source_path: str, sheet: str) -> pd.DataFrame:
    """Payload crudo redactado (sin nombres reales) para auditoría."""
    import re

    raw = clean.raw.copy()
    records = raw.to_dict("records")

    # Lista de nombres reales para redactarlos también en texto libre.
    names: set[str] = set()
    for col in ("Operario", "Personal involucrado"):
        if col in raw.columns:
            names |= {str(x).strip() for x in raw[col].dropna() if str(x).strip()}
    names = {n for n in names if len(n) >= 4 and n.lower() not in {"no aplica", "operarios"}}
    pattern = (
        re.compile("|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)), re.IGNORECASE)
        if names
        else None
    )

    def redact(value: Any) -> Any:
        value = _none_if_nan(value)
        if value is None or pattern is None:
            return value
        return pattern.sub("[PERSONA]", str(value))

    def jval(value: Any) -> Any:
        value = _none_if_nan(value)
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return float(value)
        return value

    rows = []
    for rec in records:
        payload = {
            "fecha": jval(str(rec.get("Fecha"))),
            "mes": jval(rec.get("Mes")),
            "anio": jval(rec.get("Año")),
            "maquina": jval(rec.get("Maquina")),
            "operario_hash": None,   # se redacta: nunca se guarda el nombre
            "referencia": jval(rec.get("Referencia")),
            "pacas": jval(rec.get("Pacas producidas")),
            "horas_trabajadas": jval(rec.get("Horas trabajadas")),
            "turno": jval(rec.get("Turno")),
            "paro_h": jval(rec.get("_paro_h")),
            "tipo_paro": jval(redact(rec.get("Tipo de paro"))),
            "observaciones": jval(redact(rec.get("Observaciones de paro"))),
        }
        rows.append(
            {
                "origen_archivo": source_path,
                "origen_hoja": sheet,
                "origen_fila": int(rec.get("origen_fila")),
                "payload": payload,
                "hash_origen": stable_hash(
                    rec.get("origen_fila"),
                    payload["fecha"],
                    payload["maquina"],
                    payload["pacas"],
                    payload["horas_trabajadas"],
                ),
            }
        )
    return pd.DataFrame(rows)
