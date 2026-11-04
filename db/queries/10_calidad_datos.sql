-- ============================================================
-- 10. Calidad de datos y conciliación de la última corrida ETL
-- Pregunta: ¿los totales cargados concuerdan con la fuente?
-- ============================================================
SELECT
    r.metrica,
    r.valor_fuente,
    r.valor_cargado,
    r.diferencia,
    r.tolerancia,
    r.concilia,
    r.detalle
FROM audit.etl_reconciliacion r
ORDER BY r.id DESC
LIMIT 20;

-- Reglas de calidad de la última corrida
SELECT
    q.regla,
    q.severidad,
    q.filas_afectadas,
    q.detalle
FROM audit.etl_quality q
JOIN audit.etl_run r ON r.run_id = q.run_id
WHERE r.estado = 'OK'
ORDER BY q.severidad, q.regla;
