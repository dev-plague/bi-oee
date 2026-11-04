-- ============================================================
-- 03. Pareto de causas de paro (horas) con % acumulado
-- Pregunta: ¿qué 20 % de causas concentra el 80 % del tiempo perdido?
-- ============================================================
WITH base AS (
    SELECT
        c.codigo,
        c.nombre AS causa,
        SUM(f.horas_paro) AS horas_paro
    FROM oee.fact_paro f
    JOIN oee.dim_codigo_paro c ON c.codigo_key = f.codigo_key
    JOIN oee.dim_tiempo t      ON t.tiempo_key = f.tiempo_key
    WHERE t.anio = 2024
    GROUP BY c.codigo, c.nombre
),
calc AS (
    SELECT
        *,
        SUM(horas_paro) OVER ()                                            AS total_horas,
        SUM(horas_paro) OVER (
            ORDER BY horas_paro DESC, codigo
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )                                                                  AS horas_acumuladas,
        ROW_NUMBER() OVER (ORDER BY horas_paro DESC, codigo)               AS ranking
    FROM base
)
SELECT
    ranking,
    codigo,
    causa,
    ROUND(horas_paro, 2)                                                   AS horas_paro,
    ROUND(100.0 * horas_paro / NULLIF(total_horas, 0), 1)                  AS porcentaje,
    ROUND(100.0 * horas_acumuladas / NULLIF(total_horas, 0), 1)            AS porcentaje_acumulado,
    CASE
        WHEN horas_acumuladas / NULLIF(total_horas, 0) <= 0.80 THEN 'A (80 %)'
        WHEN horas_acumuladas / NULLIF(total_horas, 0) <= 0.95 THEN 'B (15 %)'
        ELSE 'C (5 %)'
    END                                                                    AS clase_pareto
FROM calc
ORDER BY ranking;
