-- ============================================================
-- 06. MTBF y MTTR por máquina y mes (solo fallas no programadas)
-- Pregunta: ¿la línea falla mucho o tarda mucho en repararse?
-- ============================================================
WITH prod AS (
    SELECT
        anio,
        mes,
        maquina,
        SUM(horas_operativas) AS horas_operativas
    FROM oee.vw_oee_diario_maquina
    GROUP BY anio, mes, maquina
),
fallas AS (
    SELECT
        t.anio,
        t.mes,
        m.codigo AS maquina,
        COUNT(*)                    AS fallas,
        SUM(f.horas_paro)           AS horas_paro_no_programado
    FROM oee.fact_paro f
    JOIN oee.dim_codigo_paro c ON c.codigo_key = f.codigo_key
    JOIN oee.dim_tiempo t      ON t.tiempo_key = f.tiempo_key
    JOIN oee.dim_maquina m     ON m.maquina_key = f.maquina_key
    WHERE c.es_programado = false
    GROUP BY t.anio, t.mes, m.codigo
)
SELECT
    p.anio,
    p.mes,
    p.maquina,
    ROUND(p.horas_operativas, 1)                                          AS horas_operativas,
    COALESCE(f.fallas, 0)                                                 AS fallas,
    ROUND(p.horas_operativas / NULLIF(f.fallas, 0), 2)                    AS mtbf_horas,
    ROUND(f.horas_paro_no_programado / NULLIF(f.fallas, 0), 2)            AS mttr_horas,
    ROUND(f.horas_paro_no_programado, 1)                                  AS horas_paro_no_programado
FROM prod p
LEFT JOIN fallas f
       ON f.anio = p.anio AND f.mes = p.mes AND f.maquina = p.maquina
WHERE p.anio = 2024
ORDER BY p.mes, p.maquina;
