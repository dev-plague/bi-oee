# 06. Base de datos y consultas SQL analíticas

## 1. Motor y DDL

- **PostgreSQL 16** (imagen `postgres:16-alpine`).
- Esquemas: `oee` (modelo), `stg` (staging), `audit` (bitácora).
- DDL completo en `db/init/01_schema.sql`; calendario en `02_time.sql`.
- Administrable desde **DBeaver** (`localhost:5432`, base `oee_bi`, usuario
  `oee_bi`) o **Adminer** (`http://localhost:8081`).

### Restricciones

| Restricción | Dónde | Por qué |
|---|---|---|
| PK subrogada | Todas las dimensiones y hechos | Joins estables y pequeños. |
| FK | Hechos → dimensiones | Integridad referencial; evita huérfanos. |
| `UNIQUE` | `dim_*` claves naturales; `fact_produccion.origen_fila`; `fact_paro(origen_fila, origen_columna)` | Idempotencia y trazabilidad. |
| `CHECK` | `pacas >= 0`, `horas >= 0`, `minutos_paro > 0`, `origen_columna 1..18` | Evita valores imposibles. |
| `NOT NULL` | Claves y medidas base | El ETL imputa y marca, no deja nulos silenciosos. |

### Índices

| Índice | Tabla | Uso |
|---|---|---|
| `idx_fact_produccion_tiempo` | `fact_produccion` | Filtros por fecha. |
| `idx_fact_produccion_maquina_tiempo` | `fact_produccion` | Patrón máquina + rango de fechas. |
| `idx_fact_produccion_referencia` | `fact_produccion` | OEE por referencia. |
| `idx_fact_paro_tiempo` / `_maquina_tiempo` | `fact_paro` | Pareto y series. |
| `idx_fact_paro_codigo` / `_subcodigo` | `fact_paro` | Drill-down. |
| `idx_fact_hora_maquina_ts` | `fact_produccion_hora` | Últimos 15 min por máquina (Grafana). |
| `idx_dim_tiempo_anio_mes` | `dim_tiempo` | Agrupaciones mensuales. |

No se particiona a este volumen (~8 k filas). Si el histórico crece a millones,
se propone particionar `fact_paro` por año/mes y convertir
`vw_oee_diario_maquina` en vista materializada.

## 2. Consultas analíticas incluidas

| Archivo | Pregunta | Técnicas |
|---|---|---|
| `01_oee_mensual_maquina.sql` | Evolución mensual, variación y YTD | `LAG`, `SUM() OVER`, `WINDOW`, CTE |
| `02_ranking_maquinas.sql` | ¿Qué línea priorizar? | `RANK()` |
| `03_pareto_paros.sql` | ¿Qué causas concentran el 80 %? | `SUM() OVER`, `ROW_NUMBER`, acumulado |
| `04_top_causas_por_maquina.sql` | ¿La causa es la misma en todas las líneas? | `ROW_NUMBER() PARTITION BY` |
| `05_comparativo_anual.sql` | 2024 vs 2025 YTD | `FILTER`, agregación condicional |
| `06_mtbf_mttr.sql` | ¿Falla mucho o tarda mucho? | CTE, `NULLIF` |
| `07_turnos.sql` | ¿El turno nocturno rinde menos? | `RANK() PARTITION BY` |
| `08_drill_subcodigos.sql` | ¿Qué componente falla? | `UNION ALL`, jerarquía |
| `09_tendencia_7d.sql` | ¿La mejora es sostenida? | `AVG() OVER` (7 y 30 días) |
| `10_calidad_datos.sql` | ¿Los totales concilian? | `audit.etl_*` |
| `11_heatmap_maquina_mes.sql` | ¿Dónde se concentran los meses malos? | Agregación |
| `12_oee_por_referencia.sql` | ¿Qué referencia consume más horas-máquina? | `RANK()`, `LEAST` |

### Ejemplo 1 — OEE mensual con `LAG` y YTD

```sql
WITH base AS (
    SELECT anio, mes, periodo_anio_mes, maquina,
           SUM(horas_trabajadas_ref) AS htr,
           SUM(horas_operativas_ref) AS hor,
           SUM(unidades_producidas)  AS u,
           SUM(minutos_ideales)      AS mi,
           SUM(minutos_ideales_operativos) AS mio
    FROM oee.vw_oee_diario_maquina
    GROUP BY anio, mes, periodo_anio_mes, maquina
),
calc AS (
    SELECT *,
           hor / NULLIF(htr, 0) AS disponibilidad,
           LEAST(u / NULLIF(mio, 0), 1.0) AS rendimiento,
           (hor / NULLIF(htr, 0)) * LEAST(u / NULLIF(mio, 0), 1.0) AS oee
    FROM base
)
SELECT anio, mes, maquina,
       ROUND(oee, 3) AS oee,
       ROUND(LAG(oee) OVER (PARTITION BY maquina ORDER BY anio, mes), 3) AS oee_mes_anterior,
       ROUND(
         (SUM(hor) OVER w / NULLIF(SUM(htr) OVER w, 0))
         * LEAST(SUM(u) OVER w / NULLIF(SUM(mio) OVER w, 0), 1.0), 3
       ) AS oee_ytd
FROM calc
WINDOW w AS (
  PARTITION BY maquina, anio ORDER BY mes
  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
)
ORDER BY anio, mes, maquina;
```

**Resultado esperado (2024):** Vinilos_3 y Vinilos_4 lideran (~73–75 %);
Vinilos_2 queda muy por debajo (~34–38 %) por rendimiento.

### Ejemplo 2 — Pareto con acumulado

```sql
WITH base AS (
    SELECT c.codigo, c.nombre, SUM(f.horas_paro) AS horas
    FROM oee.fact_paro f
    JOIN oee.dim_codigo_paro c ON c.codigo_key = f.codigo_key
    JOIN oee.dim_tiempo t ON t.tiempo_key = f.tiempo_key
    WHERE t.anio = 2024
    GROUP BY c.codigo, c.nombre
),
calc AS (
    SELECT *,
           SUM(horas) OVER () AS total,
           SUM(horas) OVER (ORDER BY horas DESC, codigo
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS acum,
           ROW_NUMBER() OVER (ORDER BY horas DESC, codigo) AS rn
    FROM base
)
SELECT rn, codigo, nombre, ROUND(horas, 2) AS horas,
       ROUND(100.0 * horas / total, 1) AS pct,
       ROUND(100.0 * acum / total, 1) AS pct_acum
FROM calc
ORDER BY rn;
```

**Resultado (2024):** los códigos 16 (alimentación/aseo), 5 (ajuste operativo) y
6 (limpieza por derrame) concentran ~73 % de las horas de paro.

### Ejemplo 3 — MTBF / MTTR

```sql
WITH prod AS (
  SELECT anio, mes, maquina, SUM(horas_operativas) AS horas
  FROM oee.vw_oee_diario_maquina
  GROUP BY anio, mes, maquina
),
fallas AS (
  SELECT t.anio, t.mes, m.codigo AS maquina,
         COUNT(*) AS fallas, SUM(f.horas_paro) AS horas_paro
  FROM oee.fact_paro f
  JOIN oee.dim_codigo_paro c ON c.codigo_key = f.codigo_key
  JOIN oee.dim_tiempo t ON t.tiempo_key = f.tiempo_key
  JOIN oee.dim_maquina m ON m.maquina_key = f.maquina_key
  WHERE c.es_programado = false
  GROUP BY t.anio, t.mes, m.codigo
)
SELECT p.anio, p.mes, p.maquina,
       ROUND(p.horas / NULLIF(f.fallas, 0), 2) AS mtbf_h,
       ROUND(f.horas_paro / NULLIF(f.fallas, 0), 2) AS mttr_h
FROM prod p
LEFT JOIN fallas f USING (anio, mes, maquina)
ORDER BY p.anio, p.mes, p.maquina;
```

## 3. Cómo ejecutar las consultas

### DBeaver

1. Nueva conexión PostgreSQL: `localhost:5432`, base `oee_bi`, usuario `oee_bi`.
2. Abrir `db/queries/*.sql` y ejecutar con `Ctrl+Enter`.
3. Para parámetros, reemplazar `2024`/`2025` por el periodo deseado.

### psql

```bash
docker compose exec -T postgres psql -U oee_bi -d oee_bi -f - < db/queries/03_pareto_paros.sql
```

### Desde Python

```python
import psycopg2, pandas as pd
conn = psycopg2.connect(host="localhost", dbname="oee_bi", user="oee_bi", password="...")
df = pd.read_sql(open("db/queries/01_oee_mensual_maquina.sql").read(), conn)
```

## 4. Resultados de referencia

| Consulta | Hallazgo |
|---|---|
| `01` | OEE 2024 = 71,0 %; 2025 (ene–mar) = 70,2 %; 2023 parcial = 62,8 %. |
| `02` | Marzo 2025: Vinilos_3 (63,9 %) > Vinilos_1 (58,7 %) > Vinilos_4 (56,3 %) > Vinilos_2 (~30 %). |
| `03` | 3 causas concentran ~73 % de las horas de paro de 2024. |
| `04` | La causa #1 cambia por máquina; no hay una causa única. |
| `05` | 2025 vs 2024: todas las líneas caen; Vinilos_2 cae ~19 %. |
| `06` | MTBF 2,5–3,9 h; MTTR 0,6–0,84 h. |
| `07` | T1 y T3 son los turnos con mejor OEE; T1E y T12 tienen menor volumen. |
| `08` | En código 5, 5.2 (dosificación) y 5.5 (transfer) explican la mayor parte. |
| `09` | La media móvil de 7 días suaviza los picos; útil para ver sostenibilidad. |
| `10` | Todas las métricas críticas concilian; las diferencias brutas son duplicados. |
| `11` | Mapa de calor máquina × mes para el comité. |
| `12` | Referencias con OEE calculado > 100 % (estándar subcalibrado) y otras con bajo desempeño. |
