"""Limpieza, normalización y enriquecimiento de la fuente."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from catalogs import (
    canonical_ref,
    is_blank,
    normalize_area,
    normalize_shift,
    normalize_subcode,
    pseudonym,
    reference_info,
    strip_accents,
)
from config import IDEAL_UNITS_PER_MINUTE, PII_SALT

CODE_COLS = [f"Codigo de paro {i}" for i in range(1, 19)]
HOUR_COLS = [f"Codigo {i} en horas" for i in range(1, 19)]


@dataclass
class CleanResult:
    df: pd.DataFrame
    raw: pd.DataFrame
    stats: dict[str, Any]
    flags: dict[str, Any] = field(default_factory=dict)


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _txt(value: Any, maxlen: int | None = None) -> str | None:
    if is_blank(value):
        return None
    s = re.sub(r"\s+", " ", str(value).strip())
    if maxlen:
        s = s[:maxlen]
    return s or None


def _person(raw: Any, prefix: str, salt: str) -> tuple[str | None, str | None, bool]:
    seud, digest = pseudonym(raw, prefix, salt)
    if seud is None:
        return None, None, False
    return seud, digest, True


def clean_source(raw: pd.DataFrame, reference_catalog: dict[str, dict]) -> CleanResult:
    missing = [c for c in CODE_COLS + HOUR_COLS if c not in raw.columns]
    if missing:
        raise ValueError(f"Faltan columnas esperadas en la fuente: {missing}")

    raw_work = raw.copy()
    raw_work["_pacas"] = _num(raw_work["Pacas producidas"]).fillna(0.0)
    raw_work["_horas"] = _num(raw_work["Horas trabajadas"]).fillna(0.0)
    raw_work["_paro_h"] = raw_work[HOUR_COLS].apply(_num).fillna(0.0).sum(axis=1)
    raw_work["_paro_min"] = raw_work[CODE_COLS].apply(_num).fillna(0.0).sum(axis=1)

    subset = [c for c in raw_work.columns if c != "origen_fila"]
    dup_mask = raw_work.duplicated(subset=subset, keep="first")
    dup_df = raw_work.loc[dup_mask].copy()

    stats: dict[str, Any] = {
        "filas_leidas": int(len(raw_work)),
        "duplicados_exactos": int(dup_mask.sum()),
        "filas_tras_dedup": int(len(raw_work) - dup_mask.sum()),
        "pacas_brutas": float(raw_work["_pacas"].sum()),
        "horas_brutas": float(raw_work["_horas"].sum()),
        "paro_h_brutas": float(raw_work["_paro_h"].sum()),
        "pacas_duplicadas": float(dup_df["_pacas"].sum()),
        "horas_duplicadas": float(dup_df["_horas"].sum()),
        "paro_h_duplicadas": float(dup_df["_paro_h"].sum()),
        "produccion_duplicada": int((dup_df["Pacas producidas"].notna()).sum()),
    }

    df = raw_work.loc[~dup_mask].copy().reset_index(drop=True)

    # ---- Fechas y dimensiones base -------------------------------------
    df["fecha_dt"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["fecha"] = df["fecha_dt"].dt.date
    df["anio"] = df["fecha_dt"].dt.year
    df["mes"] = df["fecha_dt"].dt.month
    df["tiempo_key"] = df["fecha_dt"].dt.strftime("%Y%m%d").astype("Int64")

    mes_map = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
        "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
        "noviembre": 11, "diciembre": 12,
    }
    df["mes_texto_num"] = df["Mes"].astype(str).str.strip().str.lower().map(mes_map)
    df["anio_texto_num"] = _num(df["Año"])
    stats["mes_inconsistente"] = int(
        (df["mes_texto_num"].notna() & (df["mes_texto_num"] != df["mes"])).sum()
    )
    stats["anio_inconsistente"] = int(
        (df["anio_texto_num"].notna() & (df["anio_texto_num"] != df["anio"])).sum()
    )
    stats["fechas_invalidas"] = int(df["fecha"].isna().sum())
    df = df.loc[df["fecha"].notna()].copy()

    df["maquina"] = df["Maquina"].astype(str).str.strip()
    stats["maquinas_invalidas"] = int(
        (~df["maquina"].isin({"Vinilos_1", "Vinilos_2", "Vinilos_3", "Vinilos_4"})).sum()
    )

    df["turno_codigo"] = [normalize_shift(x)[0] for x in df["Turno"]]
    df["turno_nombre"] = [normalize_shift(x)[1] for x in df["Turno"]]
    stats["turno_sin_asignar"] = int((df["turno_codigo"] == "SD").sum())
    stats["unidad_por_display_con_turno"] = int(
        df["Unidad por display"].astype(str).str.contains("turno|am-|pm-", case=False, na=False).sum()
    )

    df["referencia_norm"] = df["Referencia"].map(canonical_ref)
    refs = df["referencia_norm"].map(lambda x: reference_info(x, reference_catalog))
    df["num_colores"] = refs.map(lambda d: d["num_colores"])
    df["unidades_por_display"] = refs.map(lambda d: d["unidades_por_display"])
    df["upp"] = refs.map(lambda d: d["unidades_por_paca"])
    df["ideal_speed"] = refs.map(
        lambda d: d["unidades_por_minuto_ideal"] or IDEAL_UNITS_PER_MINUTE
    )
    df["origen_ref"] = refs.map(lambda d: d["origen"])

    # ---- Producción ----------------------------------------------------
    df["pacas"] = _num(df["Pacas producidas"]).fillna(0.0).clip(lower=0)
    df["horas_trabajadas"] = _num(df["Horas trabajadas"]).fillna(0.0).clip(lower=0)
    df["paro_h"] = df[HOUR_COLS].apply(_num).fillna(0.0).sum(axis=1)
    df["paro_min"] = df[CODE_COLS].apply(_num).fillna(0.0).sum(axis=1)
    df["tiempo_paro"] = _num(df["Tiempo de Paro"]).fillna(0.0)
    df["descuadre_paro"] = (df["paro_h"] - df["tiempo_paro"]).abs()

    df["es_produccion"] = df["Pacas producidas"].notna() | (df["horas_trabajadas"] > 0)
    df["unidades"] = np.where(df["upp"].notna(), df["pacas"] * df["upp"], np.nan)
    df["minutos_ideales"] = np.where(
        df["upp"].notna(), df["horas_trabajadas"] * 60 * df["ideal_speed"], np.nan
    )

    stats["registros_produccion"] = int(df["es_produccion"].sum())
    stats["registros_paro"] = int((df["paro_min"] > 0).sum())
    stats["eventos_paro"] = int(df[CODE_COLS].apply(_num).gt(0).sum().sum())
    stats["produccion_sin_referencia"] = int(
        (df["es_produccion"] & (df["referencia_norm"] == "SIN_REF")).sum()
    )
    stats["produccion_con_referencia"] = int(
        (df["es_produccion"] & (df["referencia_norm"] != "SIN_REF")).sum()
    )
    stats["pacas_produccion"] = float(df.loc[df["es_produccion"], "pacas"].sum())
    stats["horas_produccion"] = float(df.loc[df["es_produccion"], "horas_trabajadas"].sum())
    stats["paro_h_total"] = float(df["paro_h"].sum())
    stats["descuadre_paro_max"] = float(df["descuadre_paro"].max())
    stats["descuadre_paro_filas"] = int((df["descuadre_paro"] > 0.01).sum())

    # ---- Personas (PII) ------------------------------------------------
    op = df["Operario"].map(lambda x: _person(x, "OP", PII_SALT))
    df["operario_seudonimo"] = [x[0] or "OP-00000000" for x in op]
    df["operario_hash"] = [
        x[1] or hashlib.sha256(f"{PII_SALT}|sin_asignado".encode()).hexdigest() for x in op
    ]
    df["operario_valido"] = [x[2] for x in op]

    pm = df["Personal involucrado"].map(lambda x: _person(x, "PM", PII_SALT))
    df["personal_seudonimo"] = [x[0] for x in pm]
    df["personal_hash"] = [x[1] for x in pm]
    df["personal_valido"] = [x[2] for x in pm]
    df["area_involucrada"] = df["Área involucrada en subcodigo 5"].map(normalize_area)

    # ---- Textos y banderas --------------------------------------------
    df["tipo_paro_texto"] = df["Tipo de paro"].map(lambda x: _txt(x, 200))
    df["observacion_paro"] = df["Observaciones de paro"].map(_txt)
    df["observaciones"] = df["Observaciones"].map(_txt)
    df["horas_no_trabajadas_dia"] = _num(df["Horas no trabajadas"])

    # Redacción de nombres propios en texto libre (minimización de PII).
    names: set[str] = set()
    for col in ("Operario", "Personal involucrado"):
        names |= {str(x).strip() for x in df[col].dropna() if str(x).strip()}
    names = {n for n in names if len(n) >= 4 and strip_accents(n).lower() not in {"no aplica", "operarios"}}
    if names:
        pattern = re.compile(
            "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)),
            re.IGNORECASE,
        )
        for col in ("observaciones", "observacion_paro", "tipo_paro_texto"):
            df[col] = df[col].map(lambda v: pattern.sub("[PERSONA]", v) if isinstance(v, str) else v)

    prod_keys = set(
        zip(
            df.loc[df["es_produccion"], "fecha"],
            df.loc[df["es_produccion"], "maquina"],
        )
    )
    df["es_sin_produccion"] = [
        (f, m) not in prod_keys and p > 0
        for f, m, p in zip(df["fecha"], df["maquina"], df["paro_min"])
    ]

    # Outliers: capacidad ideal y datos imposibles.
    capacidad = np.where(
        df["upp"].notna() & (df["upp"] > 0),
        df["horas_trabajadas"] * 60 * df["ideal_speed"] / df["upp"],
        np.inf,
    )
    df["es_outlier"] = (
        ((df["pacas"] > 1000) & df["upp"].isna())
        | ((np.isfinite(capacidad)) & (df["pacas"] > 1.5 * capacidad))
        | (df["horas_trabajadas"] > 16)
        | ((df["pacas"] > 0) & (df["horas_trabajadas"] == 0))
    )
    df["es_incompleto"] = (
        (df["Pacas producidas"].isna() & (df["horas_trabajadas"] > 0))
        | (df["Horas trabajadas"].isna() & df["Pacas producidas"].notna())
    )

    stats["outliers"] = int(df["es_outlier"].sum())
    stats["incompletos"] = int(df["es_incompleto"].sum())
    stats["paro_sin_produccion_filas"] = int(df["es_sin_produccion"].sum())
    stats["paro_sin_produccion_horas"] = float(df.loc[df["es_sin_produccion"], "paro_h"].sum())

    # Referencias que no se pudieron mapear a unidades/paca.
    stats["refs_sin_upp"] = sorted(
        df.loc[df["es_produccion"] & df["upp"].isna(), "referencia_norm"].unique().tolist()
    )

    flags = {
        "duplicados": dup_df,
        "maquinas_invalidas": df.loc[
            ~df["maquina"].isin({"Vinilos_1", "Vinilos_2", "Vinilos_3", "Vinilos_4"}),
            ["origen_fila", "maquina"],
        ],
        "fechas_invalidas": int(stats["fechas_invalidas"]),
    }
    return CleanResult(df=df, raw=raw_work, stats=stats, flags=flags)
