-- ============================================================
-- 12. OEE y unidades por referencia (top y bottom)
-- Pregunta: ¿qué referencias son más rentables en horas-máquina?
-- ============================================================
WITH prod AS (
    SELECT
        r.referencia_natural AS referencia,
        SUM(p.unidades_producidas) AS unidades,
        SUM(p.minutos_ideales)     AS minutos_ideales,
        SUM(p.pacas_producidas)    AS pacas,
        SUM(p.horas_trabajadas)    AS horas_trabajadas
    FROM oee.fact_produccion p
    JOIN oee.dim_referencia r ON r.referencia_key = p.referencia_key
    WHERE r.referencia_natural <> 'SIN_REF'
    GROUP BY r.referencia_natural
),
calc AS (
    SELECT
        *,
        unidades / NULLIF(minutos_ideales, 0)                      AS oee_sin_tope,
        LEAST(unidades / NULLIF(minutos_ideales, 0), 1.0)          AS oee
    FROM prod
)
SELECT
    RANK() OVER (ORDER BY oee DESC NULLS LAST) AS ranking,
    referencia,
    ROUND(unidades, 0)              AS unidades,
    ROUND(pacas, 0)                 AS pacas,
    ROUND(horas_trabajadas, 1)      AS horas_trabajadas,
    ROUND(oee, 3)                    AS oee,
    ROUND(oee_sin_tope, 3)          AS oee_sin_tope
FROM calc
WHERE minutos_ideales > 0
ORDER BY ranking
LIMIT 30;
