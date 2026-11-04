-- ============================================================
-- 04. Top 5 causas de paro por máquina y año
-- Pregunta: ¿la causa raíz es la misma en todas las líneas?
-- ============================================================
WITH base AS (
    SELECT
        t.anio,
        m.codigo AS maquina,
        c.codigo,
        c.nombre AS causa,
        SUM(f.horas_paro) AS horas_paro,
        COUNT(*)          AS eventos
    FROM oee.fact_paro f
    JOIN oee.dim_tiempo t     ON t.tiempo_key = f.tiempo_key
    JOIN oee.dim_maquina m    ON m.maquina_key = f.maquina_key
    JOIN oee.dim_codigo_paro c ON c.codigo_key = f.codigo_key
    WHERE t.anio = 2024
    GROUP BY t.anio, m.codigo, c.codigo, c.nombre
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY anio, maquina ORDER BY horas_paro DESC, codigo
        ) AS posicion,
        SUM(horas_paro) OVER (PARTITION BY anio, maquina) AS total_maquina
    FROM base
)
SELECT
    anio,
    maquina,
    posicion,
    codigo,
    causa,
    ROUND(horas_paro, 2)                                          AS horas_paro,
    ROUND(100.0 * horas_paro / NULLIF(total_maquina, 0), 1)       AS porcentaje_maquina
FROM ranked
WHERE posicion <= 5
ORDER BY anio, maquina, posicion;
