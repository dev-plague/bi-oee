-- ============================================================
-- Dimensión calendario construida por el equipo (2021-2027)
-- ============================================================
INSERT INTO oee.dim_tiempo (
    tiempo_key, fecha, anio, trimestre, mes, nombre_mes, dia,
    dia_semana, nombre_dia, semana_iso, anio_semana, periodo_anio_mes,
    es_fin_semana, es_festivo
)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::integer,
    d::date,
    EXTRACT(YEAR FROM d)::smallint,
    EXTRACT(QUARTER FROM d)::smallint,
    EXTRACT(MONTH FROM d)::smallint,
    CASE EXTRACT(MONTH FROM d)
        WHEN 1 THEN 'enero'      WHEN 2 THEN 'febrero'
        WHEN 3 THEN 'marzo'      WHEN 4 THEN 'abril'
        WHEN 5 THEN 'mayo'       WHEN 6 THEN 'junio'
        WHEN 7 THEN 'julio'      WHEN 8 THEN 'agosto'
        WHEN 9 THEN 'septiembre' WHEN 10 THEN 'octubre'
        WHEN 11 THEN 'noviembre' WHEN 12 THEN 'diciembre'
    END,
    EXTRACT(DAY FROM d)::smallint,
    EXTRACT(ISODOW FROM d)::smallint,
    CASE EXTRACT(ISODOW FROM d)
        WHEN 1 THEN 'lunes'     WHEN 2 THEN 'martes'
        WHEN 3 THEN 'miércoles' WHEN 4 THEN 'jueves'
        WHEN 5 THEN 'viernes'   WHEN 6 THEN 'sábado'
        WHEN 7 THEN 'domingo'
    END,
    EXTRACT(WEEK FROM d)::smallint,
    EXTRACT(YEAR FROM d)::text || '-W' || LPAD(EXTRACT(WEEK FROM d)::text, 2, '0'),
    TO_CHAR(d, 'YYYY-MM'),
    EXTRACT(ISODOW FROM d) IN (6, 7),
    false
FROM generate_series(DATE '2021-01-01', DATE '2027-12-31', INTERVAL '1 day') AS d
ON CONFLICT (tiempo_key) DO NOTHING;
