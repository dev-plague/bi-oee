# 04. Diccionario de datos y lineage

Convenciones: `PK` = clave primaria, `FK` = clave foránea, `NK` = clave natural
única. Todos los objetos viven en el esquema `oee` salvo staging (`stg`) y
auditoría (`audit`). La fuente se abre con `openpyxl` en modo `data_only=True`
(sin ejecutar macros).

## 1. `dim_tiempo` — calendario construido

| Columna | Tipo | Llave | Regla / origen |
|---|---|---|---|
| `tiempo_key` | integer | PK | `TO_CHAR(fecha,'YYYYMMDD')::int`; generado por `generate_series`. |
| `fecha` | date | NK | Día calendario 2021-01-01 a 2027-12-31. |
| `anio` | smallint | | `EXTRACT(YEAR FROM fecha)`. |
| `trimestre` | smallint | | `EXTRACT(QUARTER FROM fecha)`. |
| `mes` | smallint | | `EXTRACT(MONTH FROM fecha)`. |
| `nombre_mes` | varchar(20) | | Nombre en español (CASE). |
| `dia` | smallint | | `EXTRACT(DAY FROM fecha)`. |
| `dia_semana` | smallint | | ISO: 1=lunes … 7=domingo. |
| `nombre_dia` | varchar(20) | | Nombre en español. |
| `semana_iso` | smallint | | `EXTRACT(WEEK FROM fecha)`. |
| `anio_semana` | varchar(8) | | `YYYY-Www`. |
| `periodo_anio_mes` | varchar(7) | | `TO_CHAR(fecha,'YYYY-MM')`. |
| `es_fin_semana` | boolean | | ISO 6/7. |
| `es_festivo` | boolean | | `false`; se puede poblar con un calendario de festivos. |

**Origen:** no existe en el Excel; se construye en `db/init/02_time.sql`.

## 2. `dim_maquina`

| Columna | Tipo | Llave | Regla / origen |
|---|---|---|---|
| `maquina_key` | smallint | PK | Identidad. |
| `codigo` | varchar(20) | NK | `Maquina` normalizada: `Vinilos_1..Vinilos_4`. |
| `nombre` | varchar(60) | | Nombre descriptivo. |
| `factor_produccion_legacy` | numeric(6,3) | | Hoja `Tiempos`: 1,10 / 1,16 / 1,00 / 1,00. Se conserva, **no** se aplica al OEE. |
| `activa` | boolean | | `true`. |

**Origen:** catálogo de máquinas + hoja `Tiempos` del `.xlsm`.

## 3. `dim_turno`

| Columna | Tipo | Llave | Regla / origen |
|---|---|---|---|
| `turno_key` | smallint | PK | Identidad. |
| `codigo` | varchar(10) | NK | `T1`, `T2`, `T3`, `T1E`, `T12`, `T23`, `SD`. |
| `nombre` | varchar(60) | | Etiqueta legible. |
| `hora_inicio` / `hora_fin` | time | | Horario canónico. |
| `duracion_horas` | numeric(4,1) | | 8 / 10,5 / 12 / nulo (SD). |
| `es_nocturno` | boolean | | T3, T23. |
| `es_valido` | boolean | | `false` para `SD`. |

**Origen:** columna `Turno` del Excel (texto libre) → `normalize_shift`.
Variantes observadas: `6am-2pm`, `2pm-10pm`, `10pm-6am`, `6am-4:30pm`,
`6am-6pm`, `6pm-6am`, `No aplica`, vacío.

## 4. `dim_referencia` (SCD Tipo 2)

| Columna | Tipo | Llave | Regla / origen |
|---|---|---|---|
| `referencia_key` | integer | PK | Identidad. |
| `referencia_natural` | varchar(80) | NK (con `version`) | Nombre normalizado (`canonical_ref`). |
| `nombre_normalizado` | varchar(80) | | Igual a la natural, útil para visuales. |
| `num_colores` | smallint | | De `(N col)` o del catálogo. |
| `unidades_por_display` | integer | | Catálogo `Tablas Desplegables` col. Z o regla de formato. |
| `unidades_por_paca` | integer | | Catálogo col. AA o `num_colores × unidades_por_display`. |
| `unidades_por_minuto_ideal` | numeric(6,2) | | Catálogo col. AB; por defecto 72. |
| `vigente_desde` | date | | 1900-01-01 para la versión 1. |
| `vigente_hasta` | date | | 9999-12-31 para la versión vigente. |
| `es_vigente` | boolean | | `true`. |
| `version` | smallint | | 1. |
| `origen` | varchar(30) | | `CATALOGO`, `REGLA_FORMATO`, `SUPUESTO`, `SIN_DATO`, `ETL`. |

**Origen:** columna `Referencia` + catálogo de `Tablas Desplegables` (columnas
W–AB) + reglas de formato para las referencias que no están en el catálogo.

**Reglas de formato** (cuando no hay catálogo):

| Patrón | Unidades/paca | Ejemplo |
|---|---:|---|
| `125cc` | 45 | Parchesitos 125cc |
| `(6 col)` + 15cc | 6 × 120 = 720 | Pintorcitos 15cc |
| `(6 col)` + 22cc | 6 × 100 = 600 | Parchesitos 22cc |
| `(6 col)` + 30cc | 6 × 56 = 336 | Parchesitos 30cc |
| `(12 col)` + 15cc | 12 × 60 = 720 | Klips 15cc (12 col) |
| `(12 col)` + 22cc | 12 × 50 = 600 | Parchesitos 22cc (12 col) |
| `(12 col)` + 30cc | 12 × 28 = 336 | Parchesitos 30cc (12 col) |
| `(7 col)` + 30cc | 7 × 36 = 252 | Stanford 30cc (7 col) |
| `Vinilos x 30` | 6 × 56 = 336 | supuesto documentado |

## 5. `dim_operario`

| Columna | Tipo | Llave | Regla / origen |
|---|---|---|---|
| `operario_key` | integer | PK | Identidad. |
| `seudonimo` | varchar(20) | NK | `OP-` + primeros 8 hex de `SHA-256(salt + nombre)`. |
| `nombre_hash` | char(64) | NK | SHA-256 completo. |
| `activo` | boolean | | `true`. |
| `es_valido` | boolean | | `false` para vacío / “No aplica”. |

**Origen:** columna `Operario`. Los nombres reales **no** se cargan.

## 6. `dim_area`

| Columna | Tipo | Llave | Regla / origen |
|---|---|---|---|
| `area_key` | smallint | PK | Identidad. |
| `nombre` | varchar(60) | NK | Mantenimiento, Producción, Calidad, Almacén de materias primas, Paro programado, Auxiliar de piso, etc. |
| `tipo` | varchar(30) | | Clasificación del área. |

**Origen:** columna `ÁREA DE IMPACTO` de `TABLA CODIGOS` y
`Área involucrada en subcodigo 5`.

## 7. `dim_codigo_paro`

| Columna | Tipo | Llave | Regla / origen |
|---|---|---|---|
| `codigo_key` | smallint | PK | Identidad. |
| `codigo` | smallint | NK | 1..18. |
| `nombre` | varchar(150) | | P-MTO-22 (1..17); 18 = Desinfección heredada. |
| `area_key` | smallint | FK `dim_area` | Área de impacto. |
| `categoria` | varchar(30) | | Mantenimiento, Producción, Calidad, Suministro, Programado, Otro. |
| `es_programado` | boolean | | 4, 15, 16, 17. |
| `documentado_pmto22` | boolean | | `false` solo para 18. |

**Origen:** `TABLA CODIGOS` (columnas E/F) + PDF P-MTO-22 + hoja `Registro`
(código 18).

## 8. `dim_subcodigo_paro`

| Columna | Tipo | Llave | Regla / origen |
|---|---|---|---|
| `subcodigo_key` | integer | PK | Identidad. |
| `codigo_key` | smallint | FK `dim_codigo_paro` | Código padre. |
| `subcodigo` | varchar(20) | NK (con código) | `1.1`, `1.1.A`, `3.3`, `5.10`, `SIN_ESP`. |
| `nombre` | varchar(180) | | Catálogo o texto normalizado. |
| `nivel` | smallint | | 2 para `x.y`, 3 para `x.y.z`. |
| `subcodigo_padre` | varchar(20) | | Para nivel 3, `x.y`. |
| `ruta` | varchar(60) | | `codigo|subcodigo`. |
| `es_estimado` | boolean | | `true` si no estaba en el catálogo. |

**Origen:** columnas `Sub Codigo de paro 1`, `Subcodigo 3`, `Subcodigo 5` +
`TABLA CODIGOS`. Los subcódigos 4.x se mapean a 5.x por nombre.

## 9. `dim_personal`

| Columna | Tipo | Llave | Regla / origen |
|---|---|---|---|
| `personal_key` | integer | PK | Identidad. |
| `seudonimo` | varchar(20) | NK | `PM-` + 8 hex de SHA-256. |
| `nombre_hash` | char(64) | NK | SHA-256. |
| `area_key` | smallint | FK `dim_area` | Área del técnico. |
| `es_valido` | boolean | | `true`. |

**Origen:** columna `Personal involucrado` (solo aplica a código 5).

## 10. `fact_produccion`

| Columna | Tipo | Llave | Regla / origen |
|---|---|---|---|
| `produccion_key` | bigint | PK | Identidad. |
| `tiempo_key` | integer | FK `dim_tiempo` | `Fecha` → `YYYYMMDD`. |
| `maquina_key` | smallint | FK `dim_maquina` | `Maquina`. |
| `turno_key` | smallint | FK `dim_turno` | `Turno` normalizado; vacío → `SD`. |
| `referencia_key` | integer | FK `dim_referencia` | `Referencia` normalizada; vacío → `SIN_REF`. |
| `operario_key` | integer | FK `dim_operario` | `Operario` seudonimizado; vacío → `OP-00000000`. |
| `origen_fila` | integer | NK | Fila Excel (1-indexada). Trazabilidad. |
| `pacas_producidas` | numeric(12,2) | | `Pacas producidas`, imputado a 0 si falta. |
| `horas_trabajadas` | numeric(8,2) | | `Horas trabajadas`, imputado a 0 si falta. |
| `horas_no_trabajadas_dia` | numeric(8,2) | | `Horas no trabajadas`; dato de día, no se usa en OEE. |
| `unidades_producidas` | numeric(14,2) | | `pacas × unidades_por_paca`; nulo si no hay referencia. |
| `minutos_ideales` | numeric(14,2) | | `horas_trabajadas × 60 × unidades_por_minuto_ideal`; nulo si no hay referencia. |
| `tipo_paro_texto` | varchar(200) | | `Tipo de paro` (texto heredado). |
| `observaciones` | text | | `Observaciones`. |
| `es_outlier` | boolean | | Capacidad ideal, horas > 16, pacas sin horas. |
| `es_incompleto` | boolean | | Pacas u horas faltantes. |
| `hash_origen` | char(64) | | SHA-256 de la fila para auditoría. |
| `cargado_en` | timestamptz | | `now()`. |

**Grano:** un registro de producción. **No** incluye paros.

## 11. `fact_paro`

| Columna | Tipo | Llave | Regla / origen |
|---|---|---|---|
| `paro_key` | bigint | PK | Identidad. |
| `tiempo_key` | integer | FK `dim_tiempo` | `Fecha`. |
| `maquina_key` | smallint | FK `dim_maquina` | `Maquina`. |
| `turno_key` | smallint | FK `dim_turno` | `Turno`; vacío → `SD`. |
| `referencia_key` | integer | FK `dim_referencia` | `Referencia`; vacío → `SIN_REF`. |
| `operario_key` | integer | FK `dim_operario` | `Operario` seudonimizado. |
| `codigo_key` | smallint | FK `dim_codigo_paro` | Posición de la columna 1..18. |
| `subcodigo_key` | integer | FK `dim_subcodigo_paro` | Subcódigo normalizado; `SIN_ESP` si no aplica. |
| `area_key` | smallint | FK `dim_area` | Código 5: `Área involucrada`; resto: área del código. |
| `personal_key` | integer | FK `dim_personal` | `Personal involucrado` (código 5). |
| `origen_fila` | integer | NK (con columna) | Fila Excel. |
| `origen_columna` | smallint | NK (con fila) | 1..18. |
| `minutos_paro` | numeric(10,2) | | `Codigo de paro N` (¡son minutos!). |
| `horas_paro` | numeric(12,8) | | `Codigo N en horas` (o minutos/60). |
| `area_involucrada_texto` | varchar(60) | | Texto original. |
| `tipo_paro_texto` | varchar(200) | | `Tipo de paro`. |
| `observacion_paro` | text | | `Observaciones de paro`. |
| `es_sin_produccion` | boolean | | No hay producción el mismo día/máquina. |
| `hash_origen` | char(64) | | SHA-256 del evento. |
| `cargado_en` | timestamptz | | `now()`. |

**Grano:** un evento de paro. Se excluyen minutos ≤ 0.

## 12. `fact_produccion_hora` (simulación / futura fuente PLC)

| Columna | Tipo | Llave | Regla / origen |
|---|---|---|---|
| `hora_key` | bigint | PK | Identidad. |
| `ts_hora` | timestamptz | NK (con máquina) | Timestamp del simulador (UTC). |
| `tiempo_key` | integer | FK `dim_tiempo` | Día del timestamp. |
| `maquina_key` | smallint | FK `dim_maquina` | Máquina. |
| `turno_key` | smallint | FK `dim_turno` | T1 por defecto. |
| `referencia_key` | integer | FK `dim_referencia` | Referencia simulada. |
| `pacas_producidas` | numeric(10,2) | | `unidades / unidades_por_paca`. |
| `unidades_producidas` | numeric(14,2) | | `minutos_operacion × 72 × performance`. |
| `minutos_planificados` | numeric(6,2) | | 1 (o el tramo simulado). |
| `minutos_operacion` | numeric(6,2) | | `planificados − paro`. |
| `minutos_paro` | numeric(6,2) | | Paro simulado. |
| `origen` | varchar(20) | | `SIMULACION`. |

## 13. Vistas y su lineage

| Vista | Fuente | Transformación |
|---|---|---|
| `vw_oee_base_dia` | `fact_produccion`, `fact_paro`, dims | Agrega a día × máquina; **FULL OUTER JOIN** para no perder paros sin producción; asigna paro proporcional a las horas con referencia. |
| `vw_oee_diario_maquina` | `vw_oee_base_dia` | Ratios A/P/Q/OEE; `rendimiento` con tope 1,0; `oee_calculado` sin tope. |
| `vw_oee_mensual_maquina` | `vw_oee_diario_maquina` | Agrega a mes × máquina; recalcula ratios (no promedia promedios). |
| `vw_oee_base_turno` | hechos + dims | Igual que día, pero a día × máquina × turno; los paros con turno vacío quedan en `SD`. |
| `vw_oee_turno` | `vw_oee_base_turno` | Agrega a mes × turno. |
| `vw_pareto_paros` | `fact_paro` + dims | Agrupa por mes/máquina/código/subcódigo; `SUM() OVER` para acumulado y ranking. |
| `vw_mtbf_mttr` | `vw_oee_base_dia`, `fact_paro`, dims | MTBF = horas operativas / fallas; MTTR = horas de paro no programado / fallas. |
| `vw_estado_actual_maquina` | `fact_produccion_hora` | Últimos 15 minutos por máquina; estado OK/ALERTA/PARO. |
| `vw_oee_hora` | `fact_produccion_hora` | Agrega por minuto × máquina para Grafana. |
| `vw_kpi_global` | `vw_oee_diario_maquina` | KPIs globales del histórico. |
| `vw_alertas_recientes` | `audit.alertas_recibidas` | Últimas 100 alertas del webhook. |

## 14. Staging y auditoría

| Tabla | Contenido | PII |
|---|---|---|
| `stg.registro_crudo` | Payload JSONB por fila, hash, fila y hoja. | Nombres redactados (`operario_hash=null`, texto con `[PERSONA]`). |
| `audit.etl_run` | Corrida: inicio, fin, estado, conteos. | No. |
| `audit.etl_quality` | Reglas, severidad, filas afectadas, detalle. | No. |
| `audit.etl_reconciliacion` | Métrica, fuente, cargado, diferencia, tolerancia. | No. |
| `audit.alertas_recibidas` | Webhook de Grafana (estado, regla, máquina, valor). | No. |
