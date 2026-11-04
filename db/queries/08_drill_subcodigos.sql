-- ============================================================
-- 08. Drill-down jerárquico código -> subcódigo
-- Pregunta: dentro de una causa, ¿qué componente falla?
-- ============================================================
WITH detail AS (
    SELECT
        c.codigo,
        c.nombre AS causa,
        s.subcodigo,
        s.nombre AS subcausa,
        s.nivel,
        0 AS es_subtotal,
        SUM(f.horas_paro) AS horas_paro,
        COUNT(*) AS eventos
    FROM oee.fact_paro f
    JOIN oee.dim_codigo_paro c    ON c.codigo_key = f.codigo_key
    JOIN oee.dim_subcodigo_paro s ON s.subcodigo_key = f.subcodigo_key
    JOIN oee.dim_tiempo t         ON t.tiempo_key = f.tiempo_key
    WHERE t.anio = 2024
      AND c.codigo IN (1, 3, 5)
    GROUP BY c.codigo, c.nombre, s.subcodigo, s.nombre, s.nivel
),
subtotales AS (
    SELECT
        c.codigo,
        c.nombre AS causa,
        NULL::varchar AS subcodigo,
        'Subtotal código'::varchar AS subcausa,
        NULL::smallint AS nivel,
        1 AS es_subtotal,
        SUM(f.horas_paro) AS horas_paro,
        COUNT(*) AS eventos
    FROM oee.fact_paro f
    JOIN oee.dim_codigo_paro c ON c.codigo_key = f.codigo_key
    JOIN oee.dim_tiempo t      ON t.tiempo_key = f.tiempo_key
    WHERE t.anio = 2024 AND c.codigo IN (1, 3, 5)
    GROUP BY c.codigo, c.nombre
),
total AS (
    SELECT
        NULL::smallint AS codigo,
        'TOTAL'::varchar AS causa,
        NULL::varchar AS subcodigo,
        NULL::varchar AS subcausa,
        NULL::smallint AS nivel,
        2 AS es_subtotal,
        SUM(f.horas_paro) AS horas_paro,
        COUNT(*) AS eventos
    FROM oee.fact_paro f
    JOIN oee.dim_codigo_paro c ON c.codigo_key = f.codigo_key
    JOIN oee.dim_tiempo t      ON t.tiempo_key = f.tiempo_key
    WHERE t.anio = 2024 AND c.codigo IN (1, 3, 5)
)
SELECT codigo, causa, subcodigo, subcausa, nivel, es_subtotal,
       ROUND(horas_paro, 2) AS horas_paro, eventos
FROM (
    SELECT * FROM detail
    UNION ALL
    SELECT * FROM subtotales
    UNION ALL
    SELECT * FROM total
) x
ORDER BY codigo NULLS LAST, es_subtotal, subcodigo NULLS LAST;
