#!/usr/bin/env python3
"""Genera el JSON del tablero de Grafana (versionable y reproducible)."""
from __future__ import annotations

import json
from pathlib import Path

DS = {"type": "postgres", "uid": "oee-postgres"}
OUT = Path(__file__).resolve().parent.parent / "grafana" / "dashboards" / "oee_operativo.json"


def target(sql: str, ref: str = "A", fmt: str = "table") -> dict:
    return {
        "refId": ref,
        "datasource": DS,
        "format": fmt,
        "rawQuery": True,
        "rawSql": sql.strip(),
    }


def stat(title: str, sql: str, unit: str, x: int, y: int, w: int = 5, h: int = 6,
         thresholds: list | None = None, graph: str = "area") -> dict:
    steps = thresholds or [
        {"color": "red", "value": None},
        {"color": "orange", "value": 0.6},
        {"color": "yellow", "value": 0.75},
        {"color": "green", "value": 0.85},
    ]
    return {
        "type": "stat",
        "title": title,
        "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [target(sql)],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "min": 0,
                "max": 1 if unit == "percentunit" else None,
                "thresholds": {"mode": "absolute", "steps": steps},
                "color": {"mode": "thresholds"},
            },
            "overrides": [],
        },
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "orientation": "auto",
            "textMode": "auto",
            "colorMode": "value",
            "graphMode": graph,
            "justifyMode": "auto",
        },
    }


def timeseries(title: str, sql: str, x: int, y: int, w: int, h: int,
               unit: str = "percentunit", overrides: list | None = None,
               time_from: str | None = None) -> dict:
    p = {
        "type": "timeseries",
        "title": title,
        "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [target(sql, fmt="time_series")],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "min": 0,
                "max": 1 if unit == "percentunit" else None,
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "smooth",
                    "lineWidth": 2,
                    "fillOpacity": 12,
                    "showPoints": "never",
                    "spanNulls": True,
                    "stacking": {"mode": "none", "group": "A"},
                },
                "color": {"mode": "palette-classic"},
            },
            "overrides": overrides or [],
        },
        "options": {
            "legend": {"displayMode": "table", "placement": "bottom", "calcs": ["lastNotNull", "mean"]},
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
    }
    if time_from:
        p["timeFrom"] = time_from
    return p


def table(title: str, sql: str, x: int, y: int, w: int, h: int,
          overrides: list | None = None) -> dict:
    return {
        "type": "table",
        "title": title,
        "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [target(sql)],
        "fieldConfig": {
            "defaults": {
                "custom": {
                    "align": "auto",
                    "cellOptions": {"type": "auto"},
                    "inspect": False,
                },
            },
            "overrides": overrides or [],
        },
        "options": {
            "showHeader": True,
            "cellHeight": "sm",
            "footer": {"show": False, "reducer": ["sum"], "countRows": False, "fields": ""},
        },
    }


def barchart(title: str, sql: str, x: int, y: int, w: int, h: int,
             unit: str = "percentunit", x_field: str = "oee",
             y_field: str = "causa", time_from: str | None = None) -> dict:
    p = {
        "type": "barchart",
        "title": title,
        "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [target(sql)],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "min": 0,
                "color": {"mode": "continuous-GrYlRd"},
            },
            "overrides": [],
        },
        "options": {
            "orientation": "horizontal",
            "xField": x_field,
            "yField": y_field,
            "showValue": "auto",
            "stacking": "none",
            "legend": {"show": False},
            "tooltip": {"mode": "single"},
        },
    }
    if time_from:
        p["timeFrom"] = time_from
    return p


def text_panel(title: str, markdown: str, x: int, y: int, w: int, h: int) -> dict:
    return {
        "type": "text",
        "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "options": {"mode": "markdown", "content": markdown},
        "targets": [],
    }


def main() -> None:
    maquina_filter = "AND maquina IN (${maquina:sqlstring})"
    maquina_filter_f = "AND m.codigo IN (${maquina:sqlstring})"
    oee_15 = f"""
        SELECT COALESCE(
                 SUM(f.unidades_producidas) / NULLIF(SUM(f.minutos_planificados) * 72, 0),
                 0
               ) AS oee
        FROM oee.fact_produccion_hora f
        JOIN oee.dim_maquina m ON m.maquina_key = f.maquina_key
        WHERE f.ts_hora >= NOW() - INTERVAL '15 minutes'
          {maquina_filter_f}
    """
    disp_15 = f"""
        SELECT COALESCE(
                 SUM(f.minutos_operacion) / NULLIF(SUM(f.minutos_planificados), 0),
                 0
               ) AS disponibilidad
        FROM oee.fact_produccion_hora f
        JOIN oee.dim_maquina m ON m.maquina_key = f.maquina_key
        WHERE f.ts_hora >= NOW() - INTERVAL '15 minutes'
          {maquina_filter_f}
    """
    rend_15 = f"""
        SELECT COALESCE(
                 SUM(f.unidades_producidas) / NULLIF(SUM(f.minutos_operacion) * 72, 0),
                 0
               ) AS rendimiento
        FROM oee.fact_produccion_hora f
        JOIN oee.dim_maquina m ON m.maquina_key = f.maquina_key
        WHERE f.ts_hora >= NOW() - INTERVAL '15 minutes'
          {maquina_filter_f}
    """
    paro_15 = f"""
        SELECT COALESCE(SUM(f.minutos_paro), 0) AS minutos_paro
        FROM oee.fact_produccion_hora f
        JOIN oee.dim_maquina m ON m.maquina_key = f.maquina_key
        WHERE f.ts_hora >= NOW() - INTERVAL '15 minutes'
          {maquina_filter_f}
    """
    alertas_1h = """
        SELECT COUNT(*) AS alertas
        FROM oee.vw_alertas_recientes
        WHERE recibido_en >= NOW() - INTERVAL '1 hour'
    """

    oee_series = f"""
        SELECT hora AS "time", maquina AS metric, oee
        FROM oee.vw_oee_hora
        WHERE $__timeFilter(hora)
          {maquina_filter}
        ORDER BY 1
    """
    estado = f"""
        SELECT maquina,
               estado,
               ROUND(oee * 100, 1)            AS "OEE %",
               ROUND(disponibilidad * 100, 1) AS "Disp %",
               ROUND(rendimiento * 100, 1)    AS "Rend %",
               ROUND(minutos_paro, 1)         AS "Paro min",
               ultima_actualizacion
        FROM oee.vw_estado_actual_maquina
        WHERE maquina IN (${{maquina:sqlstring}})
        ORDER BY maquina
    """
    paro_series = f"""
        SELECT hora AS "time", maquina AS metric, minutos_paro
        FROM oee.vw_oee_hora
        WHERE $__timeFilter(hora)
          {maquina_filter}
        ORDER BY 1
    """
    pareto = """
        SELECT LEFT(c.nombre, 34) AS causa,
               ROUND(SUM(f.horas_paro)::numeric, 2) AS horas
        FROM oee.fact_paro f
        JOIN oee.dim_codigo_paro c ON c.codigo_key = f.codigo_key
        WHERE f.tiempo_key >= TO_CHAR(($__timeFrom())::timestamptz, 'YYYYMMDD')::integer
          AND f.tiempo_key <= TO_CHAR(($__timeTo())::timestamptz, 'YYYYMMDD')::integer
          AND f.maquina_key IN (
              SELECT maquina_key FROM oee.dim_maquina
              WHERE codigo IN (${maquina:sqlstring})
          )
        GROUP BY c.nombre
        ORDER BY horas DESC
        LIMIT 10
    """
    turno_oee = """
        SELECT turno,
               ROUND(
                 (SUM(horas_operativas_ref) / NULLIF(SUM(horas_trabajadas_ref), 0))
                 * LEAST(SUM(unidades_producidas) / NULLIF(SUM(minutos_ideales_operativos), 0), 1.0)
                 * 100, 1
               ) AS "OEE %"
        FROM oee.vw_oee_turno
        WHERE turno IN (${turno:sqlstring})
          AND periodo_anio_mes >= TO_CHAR(($__timeFrom())::timestamptz, 'YYYY-MM')
        GROUP BY turno
        ORDER BY "OEE %" DESC
    """
    alertas_tabla = """
        SELECT recibido_en   AS "Recibido",
               estado        AS "Estado",
               regla         AS "Regla",
               maquina       AS "Máquina",
               valor         AS "Valor"
        FROM oee.vw_alertas_recientes
        ORDER BY recibido_en DESC
        LIMIT 20
    """

    panels = [
        stat("OEE global (15 min)", oee_15, "percentunit", 0, 0, 5),
        stat("Disponibilidad (15 min)", disp_15, "percentunit", 5, 0, 5),
        stat("Rendimiento (15 min)", rend_15, "percentunit", 10, 0, 5),
        stat("Paro acumulado (15 min)", paro_15, "m", 15, 0, 4,
             thresholds=[{"color": "green", "value": None}, {"color": "yellow", "value": 15},
                         {"color": "red", "value": 30}], graph="none"),
        stat("Alertas (1 h)", alertas_1h, "none", 19, 0, 5,
             thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 1},
                         {"color": "red", "value": 3}], graph="none"),
        timeseries("OEE por máquina (near real-time)", oee_series, 0, 6, 14, 9),
        table("Estado actual por máquina", estado, 14, 6, 10, 9),
        barchart("Pareto de causas de paro (histórico)", pareto, 0, 15, 10, 9,
                 unit="none", x_field="causa", y_field="horas", time_from="5y"),
        timeseries("Minutos de paro por máquina", paro_series, 10, 15, 14, 9,
                   unit="m"),
        barchart("OEE por turno (histórico)", turno_oee, 0, 24, 8, 8,
                 unit="percent", x_field="turno", y_field="OEE %", time_from="5y"),
        table("Últimas alertas recibidas", alertas_tabla, 8, 24, 8, 8),
        text_panel(
            "Cómo leer este tablero",
            "**OEE = Disponibilidad × Rendimiento × Calidad**\n\n"
            "- **Disponibilidad** = minutos operativos / minutos planificados.\n"
            "- **Rendimiento** = unidades producidas / (minutos operativos × 72 u/min).\n"
            "- **Calidad** = 1,00 (la fuente no captura rechazos; ver informe).\n\n"
            "**Umbrales:** OEE < 60 % durante 1 minuto dispara alerta *warning*; "
            "la meta es 75 % y el mundo clase es 85 %. "
            "El Pareto usa los últimos 90 días y se filtra con la variable de máquina.",
            16, 24, 8, 8,
        ),
    ]

    for i, panel in enumerate(panels, start=1):
        panel["id"] = i

    dashboard = {
        "annotations": {
            "list": [
                {
                    "builtIn": 1,
                    "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(0, 211, 255, 1)",
                    "name": "Annotations & Alerts",
                    "type": "dashboard",
                }
            ]
        },
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "id": None,
        "links": [],
        "panels": panels,
        "refresh": "10s",
        "schemaVersion": 39,
        "tags": ["OEE", "Manufactura", "Near real-time"],
        "templating": {
            "list": [
                {
                    "name": "maquina",
                    "label": "Máquina",
                    "type": "query",
                    "datasource": DS,
                    "definition": "SELECT codigo FROM oee.dim_maquina ORDER BY 1",
                    "query": "SELECT codigo FROM oee.dim_maquina ORDER BY 1",
                    "refresh": 1,
                    "includeAll": True,
                    "multi": True,
                    "allValue": None,
                    "current": {"selected": True, "text": ["All"], "value": ["$__all"]},
                    "options": [],
                },
                {
                    "name": "turno",
                    "label": "Turno",
                    "type": "query",
                    "datasource": DS,
                    "definition": "SELECT codigo FROM oee.dim_turno WHERE es_valido ORDER BY 1",
                    "query": "SELECT codigo FROM oee.dim_turno WHERE es_valido ORDER BY 1",
                    "refresh": 1,
                    "includeAll": True,
                    "multi": True,
                    "allValue": None,
                    "current": {"selected": True, "text": ["All"], "value": ["$__all"]},
                    "options": [],
                },
            ]
        },
        "time": {"from": "now-30m", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": "OEE Envasado — Operación near real-time",
        "uid": "oee-operativo",
        "version": 1,
        "weekStart": "",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Dashboard escrito en {OUT}")


if __name__ == "__main__":
    main()
