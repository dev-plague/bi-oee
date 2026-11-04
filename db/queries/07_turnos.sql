-- ============================================================
-- 07. OEE por turno y ranking dentro de cada mes
-- Pregunta: ¿el turno nocturno rinde menos? ¿es consistente?
-- ============================================================
WITH base AS (
    SELECT
        anio,
        mes,
        turno,
        SUM(horas_trabajadas_ref)       AS horas_trabajadas_ref,
        SUM(horas_operativas_ref)       AS horas_operativas_ref,
        SUM(unidades_producidas)        AS unidades,
        SUM(minutos_ideales)            AS minutos_ideales,
        SUM(minutos_ideales_operativos) AS minutos_ideales_operativos
    FROM oee.vw_oee_turno
    GROUP BY anio, mes, turno
),
calc AS (
    SELECT
        *,
        (horas_operativas_ref / NULLIF(horas_trabajadas_ref, 0))
            * LEAST(unidades / NULLIF(minutos_ideales_operativos, 0), 1.0) AS oee
    FROM base
)
SELECT
    anio,
    mes,
    turno,
    RANK() OVER (PARTITION BY anio, mes ORDER BY oee DESC NULLS LAST)       AS ranking,
    ROUND(horas_operativas_ref / NULLIF(horas_trabajadas_ref, 0), 3)        AS disponibilidad,
    ROUND(LEAST(unidades / NULLIF(minutos_ideales_operativos, 0), 1.0), 3)  AS rendimiento,
    ROUND(oee, 3)                                                           AS oee,
    ROUND(unidades, 0)                                                      AS unidades
FROM calc
WHERE anio = 2024 AND oee IS NOT NULL
ORDER BY mes, ranking;
