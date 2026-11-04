-- ============================================================
-- 05. Comparativo 2024 vs 2025 (YTD a marzo) por máquina
-- Pregunta: ¿mejoró o empeoró cada línea contra el mismo periodo?
-- ============================================================
WITH base AS (
    SELECT
        anio,
        maquina,
        SUM(unidades_producidas)  AS unidades,
        SUM(minutos_ideales)      AS minutos_ideales,
        SUM(horas_trabajadas_ref) AS horas_trabajadas_ref,
        SUM(horas_operativas_ref) AS horas_operativas_ref
    FROM oee.vw_oee_diario_maquina
    WHERE anio IN (2024, 2025) AND mes <= 3
    GROUP BY anio, maquina
),
pivot AS (
    SELECT
        maquina,
        SUM(unidades) FILTER (WHERE anio = 2024)        AS unidades_2024,
        SUM(minutos_ideales) FILTER (WHERE anio = 2024) AS ideal_2024,
        SUM(unidades) FILTER (WHERE anio = 2025)        AS unidades_2025,
        SUM(minutos_ideales) FILTER (WHERE anio = 2025) AS ideal_2025
    FROM base
    GROUP BY maquina
)
SELECT
    maquina,
    ROUND(unidades_2024 / NULLIF(ideal_2024, 0), 3)                     AS oee_2024,
    ROUND(unidades_2025 / NULLIF(ideal_2025, 0), 3)                     AS oee_2025,
    ROUND(unidades_2025 / NULLIF(ideal_2025, 0)
          - unidades_2024 / NULLIF(ideal_2024, 0), 3)                   AS variacion_pp,
    ROUND(100.0 * (unidades_2025 / NULLIF(ideal_2025, 0))
          / NULLIF(unidades_2024 / NULLIF(ideal_2024, 0), 0) - 100, 1)  AS variacion_pct
FROM pivot
ORDER BY variacion_pp DESC;
