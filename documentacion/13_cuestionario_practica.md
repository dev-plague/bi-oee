# Cuestionario de práctica — OEE Envasado

> **Cómo usarlo:** responde en voz alta antes de leer la respuesta. Marca las
> que falles y repítelas. Si aciertas 80 % o más, estás listo para exponer.
>
> **Niveles:** B = básico (debes saberlo), I = intermedio (te diferencia),
> A = avanzado (pregunta de jurado exigente).

---

## A. Contexto y negocio

**A1. (B) ¿Qué problema resuelve el proyecto?**
Convierte el registro manual de producción y paros (P-MTO-22) y el Excel con
macros en una solución de BI end-to-end: ETL, modelo dimensional en PostgreSQL,
Grafana para operación near real-time y Power BI para análisis estratégico.

**A2. (B) ¿Quiénes son los usuarios y qué pregunta responde cada uno?**
Alta dirección: tendencias, comparativos, Pareto, inversión. Jefatura de
producción: turnos, referencias, eficiencia. Mantenimiento: causas raíz,
MTBF/MTTR. Supervisores: estado actual y alertas. Calidad: paros por calidad.
TI: reproducibilidad, seguridad y gobierno.

**A3. (B) ¿Por qué no basta el Excel actual?**
Porque es mensual, no tiene modelo dimensional, no calcula OEE, no tiene
trazabilidad ni validaciones, no soporta múltiples usuarios y no permite
reaccionar durante el turno.

**A4. (I) ¿Por qué dos tableros y no uno solo?**
Porque las preguntas y la latencia son distintas: Grafana responde “qué pasa
ahora” (segundos/minutos, alertas); Power BI responde “qué pasó y por qué”
(meses/años, DAX, RLS, narrativa). No son intercambiables.

**A5. (A) Si la empresa solo pudiera quedarse con un tablero, ¿cuál y por qué?**
Depende del usuario. Para la operación diaria, Grafana porque alerta y muestra
el estado; para el comité y la inversión, Power BI porque compara periodos y
explica causas. Si el objetivo es reducir paros, Grafana tiene impacto más
inmediato; si es priorizar inversión, Power BI.

---

## B. Data y calidad

**B1. (B) ¿Cuántas filas y columnas tiene la fuente?**
8.208 filas × 58 columnas en la hoja `Base De Datos`; periodo 2022-01-01 a
2025-03-28.

**B2. (B) ¿Qué contiene realmente `Codigo de paro N`?**
Minutos de paro del código N. El código está implícito en la posición de la
columna. Ejemplo: `Codigo de paro 5 = 40` son 40 minutos del código 5.

**B3. (B) ¿Por qué hay filas sin producción?**
Porque una fila de producción puede tener varios paros y el Excel agrega filas
hijas solo con el paro. Hay 3.051 filas hijas; no se descartan, se despivotan a
`fact_paro`.

**B4. (B) ¿Cuántos duplicados exactos hay y qué se hizo?**
42 filas duplicadas exactas; se conserva la primera. Representan 1.019 pacas,
129 horas trabajadas y 18,12 horas de paro.

**B5. (I) ¿Qué significa que la cobertura de referencia sea 52,8 %?**
Que solo el 52,8 % de las horas trabajadas tiene una referencia con conversión
unidades/paca conocida. El OEE se calcula sobre ese subconjunto; el resto no
tiene rendimiento calculable.

**B6. (I) ¿Por qué 2022 no tiene OEE y 2023 es parcial?**
Porque en 2022 el 100 % de los registros no tienen referencia, y en 2023 la
cobertura es 23 %. Sin unidades/paca no se puede calcular rendimiento.

**B7. (I) ¿Qué es `Horas no trabajadas` y por qué no se usa?**
Es un dato a nivel día (valores 0, 8, 16, 24) con semántica inconsistente; no
equivale al paro. Se conserva en `fact_produccion` para trazabilidad, pero el
OEE usa los 18 códigos de paro.

**B8. (A) ¿Cómo detectarías un dato atípico?**
Con la capacidad ideal: `pacas > 1,5 × horas × 60 × 72 / unidades_paca`, o
`horas > 16`, o pacas sin horas. Se marca `es_outlier` y se conserva. Hay 22
marcados.

**B9. (A) ¿Qué pasa con los nombres de las operarias?**
Se seudonimizan con SHA-256 + sal (`OP-xxxxxxxx`); el nombre real no se carga.
El texto libre se redacta con `[PERSONA]`. Hay 0 nombres reales en la base.

**B10. (A) ¿Qué dato falta estructuralmente?**
Unidades rechazadas / buenas. Sin eso, la calidad se asume 100 % y el OEE es un
límite superior.

---

## C. Modelo dimensional

**C1. (B) ¿Qué es una constelación?**
Un conjunto de tablas de hechos que comparten dimensiones conformadas. Aquí:
`fact_produccion` y `fact_paro` comparten tiempo, máquina, turno, referencia y
operario.

**C2. (B) ¿Cuál es el grano de `fact_produccion`?**
Un registro de producción: una fila del Excel con pacas u horas, después de
deduplicar. 5.137 filas.

**C3. (B) ¿Cuál es el grano de `fact_paro`?**
Un evento de paro: una fila de origen × una columna de código (1..18) con
minutos > 0. 16.482 eventos.

**C4. (B) ¿Por qué no unir producción y paros en una sola tabla?**
Porque cada paro duplicaría las pacas/horas de su registro (fan-out). La
constelación evita esa duplicación y permite drill-across.

**C5. (I) ¿Por qué `dim_referencia` es SCD Tipo 2?**
Porque la conversión unidades/paca puede cambiar con el empaque. La historia
debe conservar la versión vigente en la fecha del hecho. Un Tipo 1 borraría la
historia; un Tipo 3 no escala a más de dos versiones.

**C6. (I) ¿Cómo se modela la jerarquía de paros?**
`dim_codigo_paro` (nivel 1) → `dim_subcodigo_paro` (nivel 2/3), con
`codigo_key`, `subcodigo_padre`, `nivel` y `ruta`. Permite drill-down sin
recursión.

**C7. (A) ¿Por qué `dim_tiempo` es una dimensión construida?**
Porque el Excel no tiene calendario. Se genera 2021–2027 con año, trimestre,
mes, día, semana ISO, fin de semana y período `YYYY-MM`. Es la base de
`TOTALYTD` y `SAMEPERIODLASTYEAR`.

**C8. (A) ¿Qué dimensión sería candidata a SCD2 además de referencia?**
`dim_operario` si se quisiera historiar asignación a turno/línea; hoy no hay
historia. `dim_maquina` si cambiara de capacidad o configuración; hoy solo
cambia el nombre.

---

## D. Métricas y OEE

**D1. (B) ¿Cuál es la fórmula del OEE?**
`OEE = Disponibilidad × Rendimiento × Calidad`.

**D2. (B) ¿Cómo se calcula la disponibilidad?**
`(horas trabajadas − horas de paro) / horas trabajadas`.

**D3. (B) ¿Cómo se calcula el rendimiento?**
`unidades producidas / (minutos operativos × 72)`, donde
`unidades = pacas × unidades_por_paca`.

**D4. (B) ¿Cómo se calcula la calidad?**
`unidades buenas / unidades producidas`. **No disponible**; se asume 1,0.

**D5. (B) ¿Cuál es el OEE global y por máquina?**
Global 70,4 %. V1 63,0 %, V2 33,7 %, V3 73,6 %, V4 75,5 %.

**D6. (I) ¿Por qué Vinilos_2 tiene OEE tan bajo?**
Por rendimiento: 55,8 %, muy por debajo del resto. Además tiene el MTBF más bajo
(2,54 h) y el MTTR más alto (0,84 h). Hay que revisar velocidad, referencia,
dosificación/transfer y calibración del estándar.

**D7. (I) ¿Por qué el rendimiento supera 100 % en muchas observaciones?**
Porque el estándar de 72 u/min o la conversión unidades/paca están subestimados,
o las pacas están sobre-registradas. Se conserva `rendimiento_calculado` sin
tope para diagnosticar y `rendimiento` con tope para el OEE oficial.

**D8. (I) ¿Por qué se asigna el paro proporcionalmente?**
Porque las filas hijas de paro no siempre traen la misma referencia/turno que la
fila de producción. Se distribuye por horas trabajadas para no perder paros; es
una decisión documentada.

**D9. (I) ¿Qué es MTBF y MTTR?**
MTBF = horas operativas / fallas no programadas (confiabilidad). MTTR = horas de
paro no programado / fallas (velocidad de reparación).

**D10. (A) ¿Qué es el Pareto y qué concluye?**
Ordena causas por horas y acumula. En 2024, códigos 16, 5 y 6 explican 72,9 %;
con el 7, 82,4 %. Solo 1,9 % es falla electromecánica/energía/preventivo. La
palanca principal es operativa, no mantenimiento.

**D11. (A) ¿Por qué el OEE de 2024 es 71,0 % y el global 70,4 %?**
Porque el global incluye 2023 (cobertura 23 %, OEE 62,8 %) y 2025 (70,2 %); el
peso de 2023 baja el promedio. 2024 y 2025 son los años confiables.

**D12. (A) Si la calidad fuera 95 %, ¿cómo cambiaría el OEE?**
Se multiplicaría por 0,95. El OEE actual es un límite superior; con calidad 95 %
el OEE global bajaría de 70,4 % a ~66,9 %.

---

## E. ETL y SQL

**E1. (B) ¿Qué herramienta usa el ETL y por qué?**
Python + pandas + openpyxl + psycopg2, en Docker. Por reproducibilidad, pruebas,
lectura de `.xlsm` sin macros y despliegue con un comando.

**E2. (B) ¿El ETL es idempotente?**
Sí. Trunca hechos y dimensiones (excepto `dim_tiempo`) y recarga en una
transacción. Si falla, hace rollback.

**E3. (B) ¿Cómo se prueba que los totales concilian?**
Con `audit.etl_reconciliacion`: compara fuente vs cargado para pacas, horas,
paro, filas y eventos. Las métricas críticas deben dar 0 con tolerancia 0,01.

**E4. (I) ¿Qué pasa si un dato no concilia?**
El ETL falla y deja la corrida en `ERROR`; no carga un dato inconsistente. Las
diferencias brutas por duplicados se registran como no críticas y explicadas.

**E5. (I) ¿Qué consultas SQL usan ventanas?**
OEE mensual (`LAG`, `SUM() OVER`), ranking (`RANK`), Pareto (`SUM() OVER`,
`ROW_NUMBER`), top causas (`ROW_NUMBER() PARTITION BY`), media móvil
(`AVG() OVER`), comparativo anual (`FILTER`), drill-down (`UNION ALL`).

**E6. (I) ¿Qué índices existen y por qué?**
`fact_produccion(tiempo_key)`, `(maquina_key, tiempo_key)`,
`fact_paro(tiempo_key)`, `(maquina_key, tiempo_key)`, `codigo_key`,
`subcodigo_key`, `fact_produccion_hora(maquina_key, ts_hora DESC)`. Responden al
patrón “filtrar por fecha/máquina y agregar”.

**E7. (A) ¿Por qué no hay particionamiento?**
Porque el volumen es ~8 k filas. Si crece a millones, se particiona
`fact_paro` por año/mes y se convierte `vw_oee_diario_maquina` en vista
materializada.

**E8. (A) ¿Cómo agregarías una nueva referencia?**
El ETL la crea desde el catálogo o por regla de formato; si no hay conversión,
queda `SIN_DATO` y no entra al rendimiento. Si cambia la conversión, se versiona
en SCD2.

---

## F. Grafana

**F1. (B) ¿Cómo se conecta Grafana a la base?**
Datasource PostgreSQL `oee-postgres`, usuario `oee_grafana` (solo lectura),
contraseña desde `.env`; provisioning como código.

**F2. (B) ¿Qué paneles tiene el tablero?**
OEE global, disponibilidad, rendimiento, paro, alertas; serie OEE por máquina;
estado por máquina; Pareto; minutos de paro; OEE por turno; últimas alertas.

**F3. (B) ¿Qué variables tiene?**
`maquina` y `turno`, multivalor con “All”; rango de tiempo de 30 min, con
override de 5 años para Pareto/turno.

**F4. (I) ¿Cuál es la regla de alerta y su umbral?**
OEE < 0,60 durante 1 minuto, una regla por máquina. 85 % clase mundial, 75 %
meta, 60 % límite de control inferior (meta − 15 pp).

**F5. (I) ¿Cómo se demuestra que la alerta reacciona?**
El simulador inserta 1 minuto cada 2 s; se fuerza una anomalía en Vinilos_4; la
línea cae, el estado pasa a PARO y la regla a Firing; el webhook guarda la
alerta en `audit.alertas_recibidas`.

**F6. (A) ¿Por qué Grafana no reemplaza a Power BI?**
Porque no tiene modelo semántico, DAX, RLS ni narrativa para el comité; es
excelente para series, estado y alertas, pero no para análisis estratégico
complejo.

---

## G. Power BI

**G1. (B) ¿Qué formato de proyecto se usa y por qué?**
PBIP + PBIR + `model.bim` (TMSL). Es texto diffable, revisable en Git, sin
`.pbix` binario.

**G2. (B) ¿Cómo se conecta a la base?**
PostgreSQL `localhost:5432`, base `oee_bi`, usuario `oee_bi`, modo Import;
credenciales fuera del proyecto.

**G3. (B) ¿Qué medidas de inteligencia de tiempo tiene?**
`OEE YTD` con `TOTALYTD`, `OEE Año Anterior` con `SAMEPERIODLASTYEAR`, variación
YoY.

**G4. (I) ¿Qué páginas tiene el reporte?**
Resumen ejecutivo, análisis por máquina, Pareto, turnos/referencias y detalle de
paros.

**G5. (I) ¿Cómo funciona el RLS?**
Roles `Supervisor_Vinilos_1..4` con filtro en `dim_maquina[codigo]`; el filtro
se propaga a los hechos por relaciones 1:*. `Gerencia` no tiene filtro.

**G6. (A) ¿Por qué `Calidad % = 1` en DAX y no un cálculo?**
Porque la fuente no tiene rechazos. Se deja como medida para que, al agregar
`unidades_rechazadas`, solo cambie esa medida.

**G7. (A) ¿Por qué las capturas de Power BI son una maqueta?**
Porque Power BI Desktop no corre en Linux. El PBIP es el artefacto real; las
capturas nativas se generan al abrirlo en Windows.

---

## H. Seguridad y gobierno

**H1. (B) ¿Cómo se protegen los datos personales?**
Seudonimización SHA-256 + sal (`OP-`/`PM-`), sin nombres reales en la base,
redacción de texto libre, minimización y acceso por roles.

**H2. (B) ¿Dónde están las contraseñas?**
En `.env`, que está en `.gitignore`; el repositorio solo incluye
`.env.example` con placeholders.

**H3. (I) ¿Qué roles de PostgreSQL existen?**
`oee_admin` (DDL), `oee_etl` (carga), `oee_bi` (lectura Power BI/DBeaver),
`oee_grafana` (lectura Grafana).

**H4. (I) ¿Qué pasa si cambia `PII_SALT`?**
Cambian todos los seudónimos y hashes; se pierde la correspondencia con cargas
anteriores. Hay que mantener la sal estable y custodiarla.

**H5. (A) ¿Cómo auditan una carga?**
`audit.etl_run` (run_id, estado, conteos), `audit.etl_quality` (25 reglas),
`audit.etl_reconciliacion` (fuente vs cargado), `audit.alertas_recibidas`
(webhook).

---

## I. Arquitectura y evolución

**I1. (B) ¿Por qué PostgreSQL y no MySQL?**
Ventanas, CTE, `FILTER`, vistas, tipos numéricos exactos y mejores conectores
analíticos; el modelo es analítico y el volumen es pequeño.

**I2. (I) ¿Cómo evolucionaría a PLC/SCADA?**
OPC UA en el edge → MQTT → procesador (Faust/Kafka Streams) → TimescaleDB para
series y PostgreSQL para dimensiones/hechos. Mismo modelo, más frecuencia;
microparos, velocidad real y alertas en segundos.

**I3. (A) ¿Qué riesgos tiene esa evolución?**
Ciberseguridad OT/IT, sincronización NTP, pérdida de conectividad (buffer
store-and-forward), reinicio de contadores, calidad de las señales y gobierno
de PII en el edge.

**I4. (A) ¿Qué no cambiaría con PLC/SCADA?**
La semántica de OEE (A × P × Q), las dimensiones conformadas, los umbrales, el
modelo de Power BI y las reglas de seguridad/gobierno.

---

## J. Preguntas trampa

**J1. “El rendimiento es 100 %, ¿por qué el OEE no es 100 %?”**
Porque el OEE es un producto: disponibilidad 70,8 % × rendimiento 100 % ×
calidad 100 % ≈ 70,8 %.

**J2. “La suma de paros no coincide con `Horas no trabajadas`.”**
Porque `Horas no trabajadas` es un dato de día con otra semántica; el paro real
son los 18 códigos. `Tiempo de Paro` sí coincide con la suma de códigos en el
100 % de las filas.

**J3. “¿Por qué 2022 no tiene OEE?”**
Porque no hay referencia en el 100 % de los registros; sin unidades/paca no hay
rendimiento.

**J4. “¿Por qué la calidad es 100 %?”**
Porque la fuente no captura rechazos. Es un supuesto documentado; el OEE es un
límite superior.

**J5. “¿Cómo sé que no inventaron los datos?”**
Porque `audit.etl_reconciliacion` compara fuente vs cargado y las métricas
críticas dan 0; además cada hecho guarda `origen_fila` para rastrear al Excel.

**J6. “¿Por qué no calcularon todo en Excel?”**
Porque Excel no escala, no tiene modelo dimensional, no es multiusuario, no
tiene auditoría, no permite alertas y no es reproducible.

**J7. “¿Por qué no usaron Power BI para todo?”**
Porque Power BI no está pensado para refresco subminuto ni alertas operativas;
Grafana sí. Y Grafana no reemplaza el modelo semántico/DAX para el comité.

**J8. “¿Qué harían diferente con más tiempo?”**
Capturar rechazos y referencia/turno, calibrar el estándar, agregar
microparos y migrar a PLC/SCADA con TimescaleDB.

---

## K. Autoevaluación

| Aciertos (de 73) | Nivel |
|---:|---|
| 0–25 | Repasa la guía de apropiación y las secciones A–D. |
| 26–45 | Vas bien; refuerza métricas y modelo. |
| 46–60 | Listo para exponer; practica el guion en voz alta. |
| 61–73 | Puedes responder preguntas de jurado exigente. |

**Consejo final:** si no sabes un número, no lo inventes. Di dónde está la
consulta (`db/queries/…`, `audit.etl_reconciliacion`, `vw_kpi_global`) y ofrece
verificarlo. La credibilidad del proyecto está en la conciliación, no en
memorizar cifras.
