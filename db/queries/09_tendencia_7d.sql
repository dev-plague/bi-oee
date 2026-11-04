-- ============================================================
-- 09. Tendencia diaria y media móvil de 7 días por máquina
-- Pregunta: ¿la mejora es sostenida o solo un buen día?
-- ============================================================
WITH daily AS (
    SELECT
        fecha,
        maquina,
        SUM(unidades_producidas) AS unidades,
        SUM(minutos_ideales)     AS minutos_ideales
    FROM oee.vw_oee_diario_maquina
    GROUP BY fecha, maquina
),
calc AS (
    SELECT
        fecha,
        maquina,
        unidades / NULLIF(minutos_ideales, 0) AS oee
    FROM daily
)
SELECT
    fecha,
    maquina,
    ROUND(oee, 3)                                                        AS oee_dia,
    ROUND(AVG(oee) OVER (
        PARTITION BY maquina ORDER BY fecha
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 3)                                                                AS oee_media_7d,
    ROUND(AVG(oee) OVER (
        PARTITION BY maquina ORDER BY fecha
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ), 3)                                                                AS oee_media_30d
FROM calc
WHERE fecha >= DATE '2024-01-01'
ORDER BY maquina, fecha;
