-- ============================================================
-- 11. Heatmap máquina x mes (OEE %)
-- Pregunta: ¿dónde se concentran los meses malos?
-- ============================================================
SELECT
    maquina,
    mes,
    ROUND(oee * 100, 1) AS oee_pct
FROM oee.vw_oee_mensual_maquina
WHERE anio = 2024
ORDER BY maquina, mes;
