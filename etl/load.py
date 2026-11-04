"""Carga del modelo dimensional en PostgreSQL."""
from __future__ import annotations

import math
import time
from typing import Any

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import Json, execute_values

from config import DB_CONFIG

DIM_ORDER = [
    ("oee.dim_area", ["area_key", "nombre", "tipo"]),
    ("oee.dim_maquina", ["maquina_key", "codigo", "nombre", "factor_produccion_legacy", "activa"]),
    ("oee.dim_turno", ["turno_key", "codigo", "nombre", "hora_inicio", "hora_fin", "duracion_horas", "es_nocturno", "es_valido"]),
    ("oee.dim_referencia", ["referencia_key", "referencia_natural", "nombre_normalizado", "num_colores", "unidades_por_display", "unidades_por_paca", "unidades_por_minuto_ideal", "vigente_desde", "vigente_hasta", "es_vigente", "version", "origen"]),
    ("oee.dim_operario", ["operario_key", "seudonimo", "nombre_hash", "activo", "es_valido"]),
    ("oee.dim_codigo_paro", ["codigo_key", "codigo", "nombre", "area_key", "categoria", "es_programado", "documentado_pmto22"]),
    ("oee.dim_subcodigo_paro", ["subcodigo_key", "codigo_key", "subcodigo", "nombre", "nivel", "subcodigo_padre", "ruta", "es_estimado"]),
    ("oee.dim_personal", ["personal_key", "seudonimo", "nombre_hash", "area_key", "es_valido"]),
]

FACT_ORDER = [
    ("oee.fact_produccion", ["tiempo_key", "maquina_key", "turno_key", "referencia_key", "operario_key", "origen_fila", "pacas_producidas", "horas_trabajadas", "horas_no_trabajadas_dia", "unidades_producidas", "minutos_ideales", "tipo_paro_texto", "observaciones", "es_outlier", "es_incompleto", "hash_origen"]),
    ("oee.fact_paro", ["tiempo_key", "maquina_key", "turno_key", "referencia_key", "operario_key", "codigo_key", "subcodigo_key", "area_key", "personal_key", "origen_fila", "origen_columna", "minutos_paro", "horas_paro", "area_involucrada_texto", "tipo_paro_texto", "observacion_paro", "es_sin_produccion", "hash_origen"]),
]


def connect(retries: int = 40, delay: int = 2):
    last_error: Exception | None = None
    for _ in range(retries):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except psycopg2.OperationalError as exc:  # pragma: no cover - depende del entorno
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"No se pudo conectar a PostgreSQL: {last_error}")


def _pyval(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if math.isnan(float(value)) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if value is pd.NaT:
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def truncate_all(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            TRUNCATE TABLE
                oee.fact_produccion,
                oee.fact_paro,
                oee.fact_produccion_hora,
                oee.dim_maquina,
                oee.dim_turno,
                oee.dim_referencia,
                oee.dim_operario,
                oee.dim_area,
                oee.dim_codigo_paro,
                oee.dim_subcodigo_paro,
                oee.dim_personal,
                stg.registro_crudo
            CASCADE
            """
        )


def _insert_df(conn, table: str, df: pd.DataFrame, columns: list[str], page_size: int = 1000) -> int:
    if df is None or df.empty:
        return 0
    data = df[columns]
    rows = [tuple(_pyval(v) for v in row) for row in data.itertuples(index=False, name=None)]
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s"
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=page_size)
    return len(rows)


def insert_dimensions(conn, dims: dict[str, Any]) -> dict[str, int]:
    counts = {}
    for table, columns in DIM_ORDER:
        key = table.split(".")[-1]
        counts[key] = _insert_df(conn, table, dims[key], columns)
    return counts


def insert_facts(conn, facts: dict[str, Any]) -> dict[str, int]:
    counts = {}
    for table, columns in FACT_ORDER:
        key = table.split(".")[-1]
        counts[key] = _insert_df(conn, table, facts[key], columns)
    return counts


def insert_staging(conn, staging: pd.DataFrame) -> int:
    if staging.empty:
        return 0
    rows = [
        (
            r.origen_archivo,
            r.origen_hoja,
            int(r.origen_fila),
            Json(r.payload),
            r.hash_origen,
        )
        for r in staging.itertuples(index=False)
    ]
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO stg.registro_crudo
                (origen_archivo, origen_hoja, origen_fila, payload, hash_origen)
            VALUES %s
            """,
            rows,
            page_size=1000,
        )
    return len(rows)


def reset_sequences(conn) -> None:
    targets = [
        ("oee.dim_area", "area_key"),
        ("oee.dim_maquina", "maquina_key"),
        ("oee.dim_turno", "turno_key"),
        ("oee.dim_referencia", "referencia_key"),
        ("oee.dim_operario", "operario_key"),
        ("oee.dim_codigo_paro", "codigo_key"),
        ("oee.dim_subcodigo_paro", "subcodigo_key"),
        ("oee.dim_personal", "personal_key"),
        ("oee.fact_produccion", "produccion_key"),
        ("oee.fact_paro", "paro_key"),
        ("oee.fact_produccion_hora", "hora_key"),
    ]
    with conn.cursor() as cur:
        for table, column in targets:
            cur.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', '{column}'),
                    COALESCE((SELECT MAX({column}) FROM {table}), 1),
                    (SELECT COUNT(*) > 0 FROM {table})
                )
                """
            )


def start_run(conn, run_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO audit.etl_run (run_id, estado) VALUES (%s, 'EN_CURSO')",
            (run_id,),
        )


def finish_run(conn, run_id: str, estado: str, stats: dict[str, Any], notas: str = "") -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE audit.etl_run
               SET fin = now(),
                   estado = %s,
                   filas_leidas = %s,
                   filas_produccion = %s,
                   filas_paro = %s,
                   notas = %s
             WHERE run_id = %s
            """,
            (
                estado,
                stats.get("filas_leidas"),
                stats.get("registros_produccion"),
                stats.get("eventos_paro"),
                notas,
                run_id,
            ),
        )


def insert_quality(conn, run_id: str, checks: list[dict[str, Any]]) -> None:
    if not checks:
        return
    rows = [
        (
            run_id,
            c["regla"],
            c["severidad"],
            c.get("tabla"),
            c.get("filas_afectadas"),
            c.get("detalle"),
        )
        for c in checks
    ]
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO audit.etl_quality
                (run_id, regla, severidad, tabla, filas_afectadas, detalle)
            VALUES %s
            """,
            rows,
        )


def insert_reconciliation(conn, run_id: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    data = [
        (
            run_id,
            r["metrica"],
            r.get("valor_fuente"),
            r.get("valor_cargado"),
            r.get("diferencia"),
            r.get("tolerancia", 0.01),
            bool(r.get("concilia")),
            r.get("detalle"),
        )
        for r in rows
    ]
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO audit.etl_reconciliacion
                (run_id, metrica, valor_fuente, valor_cargado, diferencia, tolerancia, concilia, detalle)
            VALUES %s
            """,
            data,
        )
