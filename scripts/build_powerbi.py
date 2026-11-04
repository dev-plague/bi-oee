#!/usr/bin/env python3
"""Genera el proyecto Power BI PBIP: modelo TMSL + reporte PBIR.

El objetivo es versionar el modelo semántico y las páginas como JSON/TMSL,
en lugar de un .pbix binario. El proyecto se abre con Power BI Desktop
(Windows) y se actualiza contra PostgreSQL.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "powerbi"
PROJECT = "OEE_Vinilos"
SM = ROOT / f"{PROJECT}.SemanticModel"
RP = ROOT / f"{PROJECT}.Report"
HOST = "localhost:5432"
DB = "oee_bi"


def col(name, dtype, hidden=False, is_key=False, fmt=None, source=None):
    c = {"name": name, "dataType": dtype, "sourceColumn": source or name}
    if hidden:
        c["isHidden"] = True
    if is_key:
        c["isKey"] = True
    if fmt:
        c["formatString"] = fmt
    return c


def measure(name, expr, fmt="0.0%", folder="OEE", description=""):
    m = {"name": name, "expression": expr, "formatString": fmt, "displayFolder": folder}
    if description:
        m["description"] = description
    return m


def m_partition(schema, item):
    return {
        "name": item,
        "mode": "import",
        "source": {
            "type": "m",
            "expression": [
                "let",
                f'    Source = PostgreSQL.Database("{HOST}", "{DB}"),',
                f'    dbo = Source{{[Schema="{schema}", Item="{item}"]}}[Data]',
                "in",
                "    dbo",
            ],
        },
    }


def table(name, columns, measures=None, schema="oee", item=None, calc=None, category=None):
    t = {
        "name": name,
        "columns": columns,
        "partitions": (
            [
                {
                    "name": name,
                    "mode": "import",
                    "source": {"type": "calculated", "expression": calc},
                }
            ]
            if calc
            else [m_partition(schema, item or name)]
        ),
    }
    if measures:
        t["measures"] = measures
    if category:
        t["dataCategory"] = category
    return t


def rel(name, from_table, from_col, to_table, to_col):
    return {
        "name": name,
        "fromTable": from_table,
        "fromColumn": from_col,
        "toTable": to_table,
        "toColumn": to_col,
        "crossFilteringBehavior": "oneDirection",
    }


def build_model():
    dim_tiempo = table(
        "dim_tiempo",
        [
            col("tiempo_key", "int64", hidden=True, is_key=True),
            col("fecha", "dateTime", fmt="yyyy-mm-dd"),
            col("anio", "int64"),
            col("trimestre", "int64"),
            col("mes", "int64"),
            col("nombre_mes", "string"),
            col("dia", "int64"),
            col("dia_semana", "int64"),
            col("nombre_dia", "string"),
            col("semana_iso", "int64"),
            col("anio_semana", "string"),
            col("periodo_anio_mes", "string"),
            col("es_fin_semana", "boolean"),
            col("es_festivo", "boolean"),
        ],
        category="Time",
    )

    dim_maquina = table(
        "dim_maquina",
        [
            col("maquina_key", "int64", hidden=True, is_key=True),
            col("codigo", "string"),
            col("nombre", "string"),
            col("factor_produccion_legacy", "double"),
            col("activa", "boolean"),
        ],
    )

    dim_turno = table(
        "dim_turno",
        [
            col("turno_key", "int64", hidden=True, is_key=True),
            col("codigo", "string"),
            col("nombre", "string"),
            col("hora_inicio", "string"),
            col("hora_fin", "string"),
            col("duracion_horas", "double"),
            col("es_nocturno", "boolean"),
            col("es_valido", "boolean"),
        ],
    )

    dim_referencia = table(
        "dim_referencia",
        [
            col("referencia_key", "int64", hidden=True, is_key=True),
            col("referencia_natural", "string"),
            col("nombre_normalizado", "string"),
            col("num_colores", "int64"),
            col("unidades_por_display", "int64"),
            col("unidades_por_paca", "int64"),
            col("unidades_por_minuto_ideal", "double"),
            col("vigente_desde", "dateTime", fmt="yyyy-mm-dd"),
            col("vigente_hasta", "dateTime", fmt="yyyy-mm-dd"),
            col("es_vigente", "boolean"),
            col("version", "int64"),
            col("origen", "string"),
        ],
    )

    dim_operario = table(
        "dim_operario",
        [
            col("operario_key", "int64", hidden=True, is_key=True),
            col("seudonimo", "string"),
            col("nombre_hash", "string", hidden=True),
            col("activo", "boolean"),
            col("es_valido", "boolean"),
        ],
    )

    dim_codigo = table(
        "dim_codigo_paro",
        [
            col("codigo_key", "int64", hidden=True, is_key=True),
            col("codigo", "int64"),
            col("nombre", "string"),
            col("area_key", "int64", hidden=True),
            col("categoria", "string"),
            col("es_programado", "boolean"),
            col("documentado_pmto22", "boolean"),
        ],
    )

    dim_subcodigo = table(
        "dim_subcodigo_paro",
        [
            col("subcodigo_key", "int64", hidden=True, is_key=True),
            col("codigo_key", "int64", hidden=True),
            col("subcodigo", "string"),
            col("nombre", "string"),
            col("nivel", "int64"),
            col("subcodigo_padre", "string"),
            col("ruta", "string"),
            col("es_estimado", "boolean"),
        ],
    )

    fact_produccion = table(
        "fact_produccion",
        [
            col("produccion_key", "int64", hidden=True, is_key=True),
            col("tiempo_key", "int64", hidden=True),
            col("maquina_key", "int64", hidden=True),
            col("turno_key", "int64", hidden=True),
            col("referencia_key", "int64", hidden=True),
            col("operario_key", "int64", hidden=True),
            col("pacas_producidas", "double"),
            col("horas_trabajadas", "double"),
            col("unidades_producidas", "double"),
            col("minutos_ideales", "double"),
            col("es_outlier", "boolean"),
            col("es_incompleto", "boolean"),
        ],
    )

    fact_paro = table(
        "fact_paro",
        [
            col("paro_key", "int64", hidden=True, is_key=True),
            col("tiempo_key", "int64", hidden=True),
            col("maquina_key", "int64", hidden=True),
            col("turno_key", "int64", hidden=True),
            col("codigo_key", "int64", hidden=True),
            col("subcodigo_key", "int64", hidden=True),
            col("minutos_paro", "double"),
            col("horas_paro", "double"),
            col("es_sin_produccion", "boolean"),
        ],
    )

    oee_diario = table(
        "vw_oee_diario_maquina",
        [
            col("tiempo_key", "int64", hidden=True),
            col("fecha", "dateTime", fmt="yyyy-mm-dd"),
            col("anio", "int64"),
            col("mes", "int64"),
            col("periodo_anio_mes", "string"),
            col("maquina_key", "int64", hidden=True),
            col("maquina", "string"),
            col("horas_trabajadas", "double"),
            col("horas_paro", "double"),
            col("horas_operativas", "double"),
            col("horas_trabajadas_ref", "double"),
            col("horas_operativas_ref", "double"),
            col("pacas", "double"),
            col("unidades_producidas", "double"),
            col("minutos_ideales", "double"),
            col("minutos_ideales_operativos", "double"),
            col("eventos_paro", "int64"),
            col("fallas", "int64"),
            col("horas_paro_no_programado", "double"),
            col("registros_produccion", "int64"),
            col("cobertura_referencia", "double"),
            col("disponibilidad_total", "double"),
            col("disponibilidad", "double"),
            col("rendimiento", "double"),
            col("rendimiento_calculado", "double"),
            col("calidad", "double"),
            col("oee_calculado", "double"),
            col("oee", "double"),
        ],
    )

    mtbf = table(
        "vw_mtbf_mttr",
        [
            col("fecha", "dateTime", fmt="yyyy-mm-dd"),
            col("anio", "int64"),
            col("mes", "int64"),
            col("maquina", "string"),
            col("maquina_key", "int64", hidden=True),
            col("horas_operativas", "double"),
            col("fallas", "int64"),
            col("horas_paro_no_programado", "double"),
            col("mtbf_horas", "double"),
            col("mttr_horas", "double"),
        ],
    )

    medidas = [
        measure(
            "OEE %",
            "VAR d = [Disponibilidad %]\nVAR r = [Rendimiento %]\nVAR c = [Calidad %]\nRETURN d * MIN(r, 1) * c",
            description="OEE con tope de rendimiento al 100 %.",
        ),
        measure(
            "Disponibilidad %",
            "DIVIDE ( SUM ( vw_oee_diario_maquina[horas_operativas_ref] ), SUM ( vw_oee_diario_maquina[horas_trabajadas_ref] ) )",
            description="Horas operativas / horas trabajadas, sobre registros con referencia conocida.",
        ),
        measure(
            "Rendimiento %",
            "DIVIDE ( SUM ( vw_oee_diario_maquina[unidades_producidas] ), SUM ( vw_oee_diario_maquina[minutos_ideales_operativos] ) )",
            description="Unidades producidas / unidades ideales en el tiempo operativo.",
        ),
        measure(
            "Calidad %",
            "1",
            description="La fuente no captura rechazos; se asume 100 % y se documenta como limitación.",
        ),
        measure("OEE YTD %", "TOTALYTD ( [OEE %], dim_tiempo[fecha] )", description="OEE acumulado del año."),
        measure(
            "OEE Año Anterior %",
            "CALCULATE ( [OEE %], SAMEPERIODLASTYEAR ( dim_tiempo[fecha] ) )",
            description="OEE del mismo periodo del año anterior.",
        ),
        measure("Var OEE YoY pp", "[OEE %] - [OEE Año Anterior %]", fmt="0.0%", description="Variación en puntos porcentuales."),
        measure("Var OEE YoY %", "DIVIDE ( [OEE %] - [OEE Año Anterior %], [OEE Año Anterior %] )", description="Variación relativa."),
        measure("Horas Paro", "SUM ( fact_paro[horas_paro] )", fmt="0.0", folder="Paros", description="Horas de paro."),
        measure("Eventos Paro", "COUNTROWS ( fact_paro )", fmt="0", folder="Paros", description="Número de eventos de paro."),
        measure(
            "MTBF (h)",
            "DIVIDE ( SUM ( vw_mtbf_mttr[horas_operativas] ), SUM ( vw_mtbf_mttr[fallas] ) )",
            fmt="0.00",
            folder="Mantenimiento",
            description="Tiempo medio entre fallas no programadas.",
        ),
        measure(
            "MTTR (h)",
            "DIVIDE ( SUM ( vw_mtbf_mttr[horas_paro_no_programado] ), SUM ( vw_mtbf_mttr[fallas] ) )",
            fmt="0.00",
            folder="Mantenimiento",
            description="Tiempo medio de reparación.",
        ),
        measure("Unidades Producidas", "SUM ( vw_oee_diario_maquina[unidades_producidas] )", fmt="#,0", folder="Producción"),
        measure("Pacas Producidas", "SUM ( vw_oee_diario_maquina[pacas] )", fmt="#,0", folder="Producción"),
        measure(
            "Cobertura Referencia %",
            "DIVIDE ( SUM ( vw_oee_diario_maquina[horas_trabajadas_ref] ), SUM ( vw_oee_diario_maquina[horas_trabajadas] ) )",
            description="Porcentaje de horas con referencia conocida; indica confiabilidad del OEE.",
        ),
        measure(
            "Pareto % Acumulado",
            "VAR actual = [Horas Paro]\n"
            "VAR total = CALCULATE ( [Horas Paro], ALLSELECTED ( dim_codigo_paro ) )\n"
            "VAR acum = CALCULATE ( [Horas Paro], FILTER ( ALLSELECTED ( dim_codigo_paro ), [Horas Paro] >= actual ) )\n"
            "RETURN DIVIDE ( acum, total )",
            folder="Paros",
            description="Porcentaje acumulado para el Pareto de causas.",
        ),
        measure(
            "Semáforo OEE",
            'SWITCH ( TRUE (), [OEE %] >= 0.85, "🟢 Verde", [OEE %] >= 0.75, "🟡 Amarillo", [OEE %] >= 0.60, "🟠 Naranja", "🔴 Rojo" )',
            fmt="@",
            description="Clasificación cualitativa del OEE.",
        ),
        measure("OEE vs Meta pp", "[OEE %] - 0.75", description="Diferencia contra la meta de 75 %."),
        measure(
            "OEE Referencia %",
            "DIVIDE ( SUM ( fact_produccion[unidades_producidas] ), SUM ( fact_produccion[minutos_ideales] ) )",
            description="OEE calculado a nivel de referencia (sin asignar paros).",
        ),
    ]

    medidas_table = table(
        "_Medidas",
        [col("Valor", "string", hidden=True, source="[Valor]")],
        measures=medidas,
        calc='ROW("Valor", "")',
    )

    model = {
        "name": PROJECT,
        "compatibilityLevel": 1600,
        "model": {
            "culture": "es-CO",
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "dataSources": [
                {
                    "name": "PostgreSQL_oee",
                    "connectionString": f"Provider=PostgreSQL;Data Source={HOST};Initial Catalog={DB};",
                    "impersonationMode": "impersonateServiceAccount",
                }
            ],
            "tables": [
                dim_tiempo,
                dim_maquina,
                dim_turno,
                dim_referencia,
                dim_operario,
                dim_codigo,
                dim_subcodigo,
                fact_produccion,
                fact_paro,
                oee_diario,
                mtbf,
                medidas_table,
            ],
            "relationships": [
                rel("rel_oee_tiempo", "vw_oee_diario_maquina", "tiempo_key", "dim_tiempo", "tiempo_key"),
                rel("rel_oee_maquina", "vw_oee_diario_maquina", "maquina_key", "dim_maquina", "maquina_key"),
                rel("rel_prod_tiempo", "fact_produccion", "tiempo_key", "dim_tiempo", "tiempo_key"),
                rel("rel_prod_maquina", "fact_produccion", "maquina_key", "dim_maquina", "maquina_key"),
                rel("rel_prod_turno", "fact_produccion", "turno_key", "dim_turno", "turno_key"),
                rel("rel_prod_ref", "fact_produccion", "referencia_key", "dim_referencia", "referencia_key"),
                rel("rel_prod_operario", "fact_produccion", "operario_key", "dim_operario", "operario_key"),
                rel("rel_paro_tiempo", "fact_paro", "tiempo_key", "dim_tiempo", "tiempo_key"),
                rel("rel_paro_maquina", "fact_paro", "maquina_key", "dim_maquina", "maquina_key"),
                rel("rel_paro_turno", "fact_paro", "turno_key", "dim_turno", "turno_key"),
                rel("rel_paro_codigo", "fact_paro", "codigo_key", "dim_codigo_paro", "codigo_key"),
                rel("rel_paro_subcodigo", "fact_paro", "subcodigo_key", "dim_subcodigo_paro", "subcodigo_key"),
                rel("rel_subcodigo_codigo", "dim_subcodigo_paro", "codigo_key", "dim_codigo_paro", "codigo_key"),
                rel("rel_mtbf_tiempo", "vw_mtbf_mttr", "fecha", "dim_tiempo", "fecha"),
                rel("rel_mtbf_maquina", "vw_mtbf_mttr", "maquina_key", "dim_maquina", "maquina_key"),
            ],
            "roles": [
                {
                    "name": f"Supervisor_{m}",
                    "modelPermission": "read",
                    "tablePermissions": [
                        {"name": "dim_maquina", "filterExpression": f'dim_maquina[codigo] = "{m}"'}
                    ],
                }
                for m in ("Vinilos_1", "Vinilos_2", "Vinilos_3", "Vinilos_4")
            ]
            + [{"name": "Gerencia", "modelPermission": "read"}],
        },
    }
    return model


# ------------------------------------------------------------------
# PBIR
# ------------------------------------------------------------------

def visual(name, x, y, w, h, vtype, query_state=None, objects=None):
    v = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/1.0.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": 0, "width": w, "height": h, "tabOrder": 0},
        "visual": {"visualType": vtype},
    }
    if query_state:
        v["visual"]["query"] = {"queryState": query_state}
    if objects:
        v["visual"]["objects"] = objects
    return v


def field_column(table, prop):
    return {
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": prop}},
        "queryRef": f"{table}.{prop}",
        "nativeQueryRef": prop,
    }


def field_measure(table, prop):
    return {
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": prop}},
        "queryRef": f"{table}.{prop}",
        "nativeQueryRef": prop,
    }


def page(name, display, visuals, width=1280, height=720):
    return {
        "name": name,
        "displayName": display,
        "displayOption": "FitToPage",
        "height": height,
        "width": width,
        "visualInteractions": [],
        "filters": "[]",
        "visuals": visuals,
    }


def build_report():
    # Página 1: resumen ejecutivo
    p1 = page(
        "resumen",
        "1. Resumen ejecutivo",
        [
            visual("v1_oee", 20, 20, 290, 130, "card",
                   {"Values": {"projections": [field_measure("_Medidas", "OEE %")]}}),
            visual("v1_disp", 330, 20, 290, 130, "card",
                   {"Values": {"projections": [field_measure("_Medidas", "Disponibilidad %")]}}),
            visual("v1_rend", 640, 20, 290, 130, "card",
                   {"Values": {"projections": [field_measure("_Medidas", "Rendimiento %")]}}),
            visual("v1_paro", 950, 20, 290, 130, "card",
                   {"Values": {"projections": [field_measure("_Medidas", "Horas Paro")]}}),
            visual("v1_trend", 20, 170, 780, 300, "lineChart",
                   {
                       "Category": {"projections": [field_column("dim_tiempo", "periodo_anio_mes")]},
                       "Y": {"projections": [field_measure("_Medidas", "OEE %")]},
                       "Series": {"projections": [field_column("dim_maquina", "codigo")]},
                   }),
            visual("v1_maquinas", 820, 170, 420, 300, "barChart",
                   {
                       "Category": {"projections": [field_column("dim_maquina", "codigo")]},
                       "Y": {"projections": [field_measure("_Medidas", "OEE %")]},
                   }),
            visual("v1_texto", 20, 490, 1220, 200, "textbox",
                   objects={
                       "general": [
                           {
                               "properties": {
                                   "paragraphs": [
                                       {
                                           "textRuns": [
                                               {
                                                   "value": (
                                                       "OEE = Disponibilidad × Rendimiento × Calidad. "
                                                       "Meta 75 %, clase mundial 85 %. "
                                                       "La calidad se asume 100 % porque la fuente no captura rechazos. "
                                                       "Usar los slicers de año y máquina para explorar."
                                                   )
                                               }
                                           ]
                                       }
                                   ]
                               }
                           }
                       ]
                   }),
        ],
    )

    # Página 2: análisis por máquina
    p2 = page(
        "maquinas",
        "2. Análisis por máquina",
        [
            visual("v2_slicer_maquina", 20, 20, 250, 120, "slicer",
                   {"Values": {"projections": [field_column("dim_maquina", "codigo")]}}),
            visual("v2_slicer_anio", 290, 20, 200, 120, "slicer",
                   {"Values": {"projections": [field_column("dim_tiempo", "anio")]}}),
            visual("v2_trend", 20, 160, 780, 300, "lineChart",
                   {
                       "Category": {"projections": [field_column("dim_tiempo", "periodo_anio_mes")]},
                       "Y": {"projections": [field_measure("_Medidas", "OEE YTD %")]},
                       "Series": {"projections": [field_column("dim_maquina", "codigo")]},
                   }),
            visual("v2_tabla", 820, 160, 420, 300, "tableEx",
                   {
                       "Values": {
                           "projections": [
                               field_column("dim_maquina", "codigo"),
                               field_measure("_Medidas", "OEE %"),
                               field_measure("_Medidas", "Disponibilidad %"),
                               field_measure("_Medidas", "Rendimiento %"),
                               field_measure("_Medidas", "MTBF (h)"),
                               field_measure("_Medidas", "MTTR (h)"),
                           ]
                       }
                   }),
            visual("v2_cobertura", 20, 480, 1220, 180, "barChart",
                   {
                       "Category": {"projections": [field_column("dim_maquina", "codigo")]},
                       "Y": {"projections": [field_measure("_Medidas", "Cobertura Referencia %")]},
                   }),
        ],
    )

    # Página 3: Pareto
    p3 = page(
        "pareto",
        "3. Pareto de paros",
        [
            visual("v3_slicer_maquina", 20, 20, 250, 120, "slicer",
                   {"Values": {"projections": [field_column("dim_maquina", "codigo")]}}),
            visual("v3_slicer_anio", 290, 20, 200, 120, "slicer",
                   {"Values": {"projections": [field_column("dim_tiempo", "anio")]}}),
            visual("v3_barras", 20, 160, 740, 350, "barChart",
                   {
                       "Category": {"projections": [field_column("dim_codigo_paro", "nombre")]},
                       "Y": {"projections": [field_measure("_Medidas", "Horas Paro")]},
                   }),
            visual("v3_tabla", 780, 160, 460, 350, "tableEx",
                   {
                       "Values": {
                           "projections": [
                               field_column("dim_codigo_paro", "codigo"),
                               field_column("dim_codigo_paro", "nombre"),
                               field_measure("_Medidas", "Horas Paro"),
                               field_measure("_Medidas", "Eventos Paro"),
                               field_measure("_Medidas", "Pareto % Acumulado"),
                           ]
                       }
                   }),
            visual("v3_texto", 20, 530, 1220, 150, "textbox",
                   objects={
                       "general": [
                           {
                               "properties": {
                                   "paragraphs": [
                                       {
                                           "textRuns": [
                                               {
                                                   "value": (
                                                       "Drill-down: en la tabla, expandir de código a subcódigo "
                                                       "(dim_subcodigo_paro). Drill-through: clic derecho en una causa "
                                                       "→ Examinar → Detalle de paros."
                                                   )
                                               }
                                           ]
                                       }
                                   ]
                               }
                           }
                       ]
                   }),
        ],
    )

    # Página 4: turnos y referencias
    p4 = page(
        "turnos",
        "4. Turnos y referencias",
        [
            visual("v4_turno", 20, 20, 600, 300, "barChart",
                   {
                       "Category": {"projections": [field_column("dim_turno", "nombre")]},
                       "Y": {"projections": [field_measure("_Medidas", "OEE %")]},
                   }),
            visual("v4_ref", 640, 20, 600, 300, "tableEx",
                   {
                       "Values": {
                           "projections": [
                               field_column("dim_referencia", "referencia_natural"),
                               field_measure("_Medidas", "OEE Referencia %"),
                               field_measure("_Medidas", "Pacas Producidas"),
                           ]
                       }
                   }),
            visual("v4_cobertura", 20, 340, 1220, 300, "barChart",
                   {
                       "Category": {"projections": [field_column("dim_maquina", "codigo")]},
                       "Y": {"projections": [field_measure("_Medidas", "Cobertura Referencia %")]},
                   }),
        ],
    )

    # Página 5: detalle de paros (destino de drill-through)
    p5 = page(
        "detalle",
        "5. Detalle de paros",
        [
            visual("v5_slicer_maquina", 20, 20, 250, 120, "slicer",
                   {"Values": {"projections": [field_column("dim_maquina", "codigo")]}}),
            visual("v5_slicer_codigo", 290, 20, 300, 120, "slicer",
                   {"Values": {"projections": [field_column("dim_codigo_paro", "nombre")]}}),
            visual("v5_tabla", 20, 160, 1220, 500, "tableEx",
                   {
                       "Values": {
                           "projections": [
                               field_column("dim_tiempo", "fecha"),
                               field_column("dim_maquina", "codigo"),
                               field_column("dim_turno", "codigo"),
                               field_column("dim_codigo_paro", "nombre"),
                               field_column("dim_subcodigo_paro", "subcodigo"),
                               field_column("dim_subcodigo_paro", "nombre"),
                               field_measure("_Medidas", "Horas Paro"),
                           ]
                       }
                   }),
        ],
    )

    pages = [p1, p2, p3, p4, p5]
    return pages


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    model = build_model()
    write_json(SM / "model.bim", model)
    write_json(
        SM / "definition.pbism",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
            "version": "4.0",
            "settings": {},
        },
    )

    pages = build_report()
    write_json(
        ROOT / f"{PROJECT}.pbip",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/pbip/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{PROJECT}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    write_json(
        RP / "definition.pbir",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json",
            "version": "1.0",
            "datasetReference": {"byPath": {"path": f"../{PROJECT}.SemanticModel"}},
        },
    )
    write_json(RP / "definition" / "version.json", {"version": "1.0"})
    write_json(
        RP / "definition" / "report.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json",
            "themeCollection": {
                "baseTheme": {
                    "name": "CY24SU10",
                    "reportVersionAtImport": "5.55",
                    "type": "SharedResources",
                }
            },
            "objects": {},
            "reportIdentifier": str(uuid.uuid4()),
        },
    )
    write_json(
        RP / "definition" / "pages" / "pages.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pages/1.0.0/schema.json",
            "pageOrder": [p["name"] for p in pages],
            "activePageName": pages[0]["name"],
        },
    )
    for p in pages:
        page_dir = RP / "definition" / "pages" / p["name"]
        page_json = {k: v for k, v in p.items() if k != "visuals"}
        page_json["$schema"] = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.0.0/schema.json"
        write_json(page_dir / "page.json", page_json)
        for v in p["visuals"]:
            write_json(page_dir / "visuals" / v["name"] / "visual.json", v)

    print(f"PBIP generado en {ROOT}")
    print(f"  modelo: {SM / 'model.bim'}")
    print(f"  reporte: {RP / 'definition'}")


if __name__ == "__main__":
    main()
