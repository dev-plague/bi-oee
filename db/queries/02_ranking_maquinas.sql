-- ============================================================
-- 02. Ranking de máquinas por OEE ajustado en un mes
-- Pregunta: ¿qué línea requiere primero un plan de mejora?
-- ============================================================
WITH base AS (
    SELECT
        maquina,
        SUM(horas_trabajadas_ref)       AS horas_trabajadas_ref,
        SUM(horas_operativas_ref)       AS horas_operativas_ref,
        SUM(unidades_producidas)        AS unidades,
        SUM(minutos_ideales)            AS minutos_ideales,
        SUM(minutos_ideales_operativos) AS minutos_ideales_operativos
    FROM oee.vw_oee_diario_maquina
    WHERE anio = 2025 AND mes = 3
    GROUP BY maquina
),
calc AS (
    SELECT
        *,
        (horas_operativas_ref / NULLIF(horas_trabajadas_ref, 0))
            * LEAST(unidades / NULLIF(minutos_ideales_operativos, 0), 1.0) AS oee
    FROM base
)
SELECT
    RANK() OVER (ORDER BY oee DESC NULLS LAST)                          AS ranking,
    maquina,
    ROUND(horas_operativas_ref / NULLIF(horas_trabajadas_ref, 0), 3)    AS disponibilidad,
    ROUND(LEAST(unidades / NULLIF(minutos_ideales_operativos, 0), 1.0), 3) AS rendimiento,
    ROUND(oee, 3)                                                       AS oee,
    ROUND(unidades / NULLIF(minutos_ideales, 0), 3)                     AS oee_sin_tope,
    ROUND(horas_operativas_ref, 1)                                      AS horas_operativas,
    ROUND(unidades, 0)                                                  AS unidades
FROM calc
ORDER BY ranking;
