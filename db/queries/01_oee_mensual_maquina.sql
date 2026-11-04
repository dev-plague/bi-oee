-- ============================================================
-- 01. OEE mensual por máquina, variación mes a mes y YTD
-- Pregunta: ¿cómo evoluciona cada línea y cuánto aporta al acumulado del año?
-- Nota: "oee" aplica el tope de rendimiento al 100 %; "oee_sin_tope"
--       sirve para diagnosticar estándares mal calibrados.
-- ============================================================
WITH base AS (
    SELECT
        anio,
        mes,
        periodo_anio_mes,
        maquina,
        SUM(horas_trabajadas_ref)       AS horas_trabajadas_ref,
        SUM(horas_operativas_ref)       AS horas_operativas_ref,
        SUM(unidades_producidas)        AS unidades,
        SUM(minutos_ideales)            AS minutos_ideales,
        SUM(minutos_ideales_operativos) AS minutos_ideales_operativos
    FROM oee.vw_oee_diario_maquina
    GROUP BY anio, mes, periodo_anio_mes, maquina
),
calc AS (
    SELECT
        *,
        horas_operativas_ref / NULLIF(horas_trabajadas_ref, 0)                  AS disponibilidad,
        LEAST(unidades / NULLIF(minutos_ideales_operativos, 0), 1.0)            AS rendimiento,
        unidades / NULLIF(minutos_ideales, 0)                                   AS oee_sin_tope,
        (horas_operativas_ref / NULLIF(horas_trabajadas_ref, 0))
            * LEAST(unidades / NULLIF(minutos_ideales_operativos, 0), 1.0)      AS oee
    FROM base
)
SELECT
    anio,
    mes,
    periodo_anio_mes,
    maquina,
    ROUND(disponibilidad, 3)                                                     AS disponibilidad,
    ROUND(rendimiento, 3)                                                        AS rendimiento,
    ROUND(oee, 3)                                                                AS oee,
    ROUND(oee_sin_tope, 3)                                                       AS oee_sin_tope,
    ROUND(LAG(oee) OVER (PARTITION BY maquina ORDER BY anio, mes), 3)            AS oee_mes_anterior,
    ROUND(oee - LAG(oee) OVER (PARTITION BY maquina ORDER BY anio, mes), 3)      AS variacion_pp,
    ROUND(
        (SUM(horas_operativas_ref) OVER w / NULLIF(SUM(horas_trabajadas_ref) OVER w, 0))
        * LEAST(SUM(unidades) OVER w / NULLIF(SUM(minutos_ideales_operativos) OVER w, 0), 1.0),
        3
    )                                                                            AS oee_ytd
FROM calc
WHERE anio >= 2024
WINDOW w AS (
    PARTITION BY maquina, anio
    ORDER BY mes
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
)
ORDER BY anio, mes, maquina;
