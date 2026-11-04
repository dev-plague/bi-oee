"""Pruebas unitarias del ETL (no requieren base de datos)."""
from __future__ import annotations

import pandas as pd
import pytest

from catalogs import (
    canonical_ref,
    derive_reference,
    normalize_shift,
    normalize_subcode,
    pseudonym,
)
from clean import clean_source
from transform import build_dimensions, build_facts


def _base_row(**overrides):
    row = {
        "Fecha": pd.Timestamp("2025-01-15"),
        "Mes": "enero",
        "Año": 2025,
        "Maquina": "Vinilos_1",
        "Operario": "Ana",
        "Referencia": "Pintorcitos 22cc (6 col)",
        "Pacas producidas": 10,
        "Horas trabajadas": 8,
        "Turno": "6am-2pm (Turno 1)",
        "Horas no trabajadas": 16,
        "Tipo de paro": "[19] No aplica",
        "Observaciones de paro": "No aplica",
        "Tiempo de Paro": 0.5,
        "Observaciones": None,
        "Unidad por display": None,
        "Área involucrada en subcodigo 5": None,
        "Personal involucrado": None,
        "Sub Codigo de paro 1": None,
        "Subcodigo 3": None,
        "Subcodigo 5": None,
    }
    for i in range(1, 19):
        row[f"Codigo de paro {i}"] = 0
        row[f"Codigo {i} en horas"] = 0
    row["Codigo de paro 1"] = 30
    row["Codigo 1 en horas"] = 0.5
    row.update(overrides)
    return row


def _df(rows):
    df = pd.DataFrame(rows)
    df.insert(0, "origen_fila", range(10, 10 + len(df)))
    return df


def test_canonical_ref_variants():
    assert canonical_ref("Alocdor 22cc (6col)") == "Alocolor 22cc (6 col)"
    assert canonical_ref("Klips 15cc (12col)") == "Klips 15cc (12 col)"
    assert canonical_ref("Licitación 15 cc (6 col)") == "Licitación 15cc (6 col)"
    assert canonical_ref(None) == "SIN_REF"
    assert canonical_ref("No aplica") == "SIN_REF"


def test_derive_reference_rules():
    assert derive_reference("Parchesitos 22cc (6 col)")["unidades_por_paca"] == 600
    assert derive_reference("Parchesitos 22cc (12 col)")["unidades_por_paca"] == 600
    assert derive_reference("Parchesitos 30cc (12 col)")["unidades_por_paca"] == 336
    assert derive_reference("Parchesitos 125cc")["unidades_por_paca"] == 45
    assert derive_reference("Vinilos x 30 Blanco")["unidades_por_paca"] == 336
    assert derive_reference("SIN_REF")["unidades_por_paca"] is None


def test_normalize_subcode():
    assert normalize_subcode("1.2D  RETENEDORES Y ORING", 1) == "1.2.D"
    assert normalize_subcode("1.2.C Cambio de Valvula", 1) == "1.2.C"
    assert normalize_subcode("1.4.3 Sensor", 1) == "1.4.C"
    assert normalize_subcode("4.2  SISTEMA DOSIFICADOR", 5) == "5.2"
    assert normalize_subcode("4.4 TRANSFER Y PISADOR", 5) == "5.5"
    assert normalize_subcode("1.1 SISTEMA ALIMENTADOR DE ENVASES", 1) == "1.1"
    assert normalize_subcode("Sin especificar", 5) == "SIN_ESP"
    assert normalize_subcode("x", 7) == "SIN_ESP"


def test_normalize_shift():
    assert normalize_shift("6am-2pm (Turno 1)")[0] == "T1"
    assert normalize_shift("2pm-10pm (Turno 2)")[0] == "T2"
    assert normalize_shift("10pm-6am (Turno 3)")[0] == "T3"
    assert normalize_shift("6am-4:30pm")[0] == "T1E"
    assert normalize_shift(None)[0] == "SD"
    assert normalize_shift("No aplica")[0] == "SD"


def test_pseudonym_is_deterministic_and_hides_name():
    a = pseudonym("Ana", "OP", "salt")
    b = pseudonym("ana", "OP", "salt")
    assert a == b
    assert a[0].startswith("OP-")
    assert "ana" not in a[0].lower()
    assert len(a[1]) == 64


def test_clean_and_transform_small_dataset():
    rows = [
        _base_row(),
        _base_row(
            **{
                "Pacas producidas": None,
                "Horas trabajadas": None,
                "Tiempo de Paro": 0.25,
                "Codigo de paro 1": 0,
                "Codigo 1 en horas": 0,
                "Codigo de paro 5": 15,
                "Codigo 5 en horas": 0.25,
                "Subcodigo 5": "5.2 Sistema de dosificación de pintura, frontal posterior",
            }
        ),
    ]
    clean = clean_source(_df(rows), {})
    assert clean.stats["filas_leidas"] == 2
    assert clean.stats["registros_produccion"] == 1
    assert clean.stats["eventos_paro"] == 2
    assert clean.stats["pacas_produccion"] == 10
    assert clean.stats["paro_h_total"] == pytest.approx(0.75)

    dims = build_dimensions(clean, {})
    facts = build_facts(clean, dims)
    assert len(facts["fact_produccion"]) == 1
    assert len(facts["fact_paro"]) == 2
    assert facts["fact_produccion"].iloc[0]["unidades_producidas"] == 6000
    assert "Ana" not in set(dims["dim_operario"]["seudonimo"])


def test_duplicate_rows_are_removed():
    clean = clean_source(_df([_base_row(), _base_row()]), {})
    assert clean.stats["filas_leidas"] == 2
    assert clean.stats["duplicados_exactos"] == 1
    assert clean.stats["registros_produccion"] == 1
    assert clean.stats["pacas_produccion"] == 10
