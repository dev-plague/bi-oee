# Guion de exposición — 15 minutos

> **Objetivo:** que cualquier integrante pueda exponer el proyecto con este
> guion, sin leer diapositivas. Cada bloque trae: tiempo, qué se ve en la
> diapositiva, qué decir y cómo hacer la transición.
>
> **Regla de oro:** no leas la diapositiva. La diapositiva muestra el dato; tú
> cuentas la historia.

---

## Resumen de tiempos

| # | Diapositiva | Tiempo | Acumulado |
|---|---|---:|---:|
| 1 | Portada | 0:40 | 0:40 |
| 2 | El problema | 1:20 | 2:00 |
| 3 | Dos usuarios, dos preguntas | 0:50 | 2:50 |
| 4 | La fuente y sus trampas | 1:30 | 4:20 |
| 5 | Diagnóstico de calidad | 1:00 | 5:20 |
| 6 | Arquitectura de la solución | 1:10 | 6:30 |
| 7 | Modelo dimensional | 1:10 | 7:40 |
| 8 | Cómo se calcula el OEE | 1:20 | 9:00 |
| 9 | ETL y conciliación | 1:10 | 10:10 |
| 10 | Resultados: OEE por máquina | 1:00 | 11:10 |
| 11 | Pareto de causas | 0:50 | 12:00 |
| 12 | Grafana y la alerta | 1:10 | 13:10 |
| 13 | Power BI y RLS | 1:00 | 14:10 |
| 14 | Conclusiones y mejoras | 0:50 | 15:00 |

**Si te quedas sin tiempo:** recorta las diapositivas 5 y 9 a una frase cada
una; nunca recortes la 10, 11 y 12 (son la evidencia).

---

## Diapositiva 1 — Portada (0:00–0:40)

**En pantalla:** título “OEE Envasado — Solución de BI end-to-end”, integrantes,
stack (PostgreSQL, Python, Grafana, Power BI), fecha.

**Guion:**

> “Buenos días. Soy [nombre] y voy a presentar la solución de BI que construimos
> para las cuatro líneas de envasado de vinilos y témperas. El problema es
> simple: hoy la producción y los paros se registran a mano y se consolidan en
> un Excel con macros. Eso sirve para el comité mensual, pero no para comparar
> máquinas, turnos y años, ni para reaccionar durante el turno. Lo que hicimos
> fue convertir ese Excel en una solución de datos completa: ETL, base
> dimensional, un tablero operativo en Grafana y un tablero analítico en Power
> BI.”

**Transición:** “Para entender la solución, primero hay que entender el
problema.”

---

## Diapositiva 2 — El problema (0:40–2:00)

**En pantalla:** tres columnas: “Captura manual”, “Excel con macros”, “Comité
mensual”. Abajo, dos dolores: *no tendencias* y *no tiempo real*.

**Guion:**

> “Cada turno, las operarias llenan el formato P-MTO-22, el ‘hora a hora’:
> producción, código de paro y duración. Producción lo envía a mantenimiento;
> mantenimiento lo transcribe a un Excel con macros. De ahí salen tablas
> dinámicas y gráficos para el comité mensual.
>
> Ese flujo tiene tres consecuencias. Primero, el dato llega tarde: cuando el
> comité ve el problema, ya pasaron semanas. Segundo, el Excel es ancho y
> manual: cada pregunta exige rearmar la tabla, y no hay modelo dimensional.
> Tercero, no hay OEE: se reportan horas, producción y porcentajes de códigos,
> pero no la eficiencia global ni sus componentes.
>
> La empresa necesita dos cosas distintas: que la alta dirección pueda analizar
> tendencias y causas para decidir inversiones, y que los supervisores puedan
> ver la línea casi en tiempo real y recibir una alerta.”

**Transición:** “Esas dos necesidades son las que definen la arquitectura.”

---

## Diapositiva 3 — Dos usuarios, dos preguntas (2:00–2:50)

**En pantalla:** dos tarjetas: **Alta dirección** → “¿qué pasó y por qué?”;
**Supervisión/mantenimiento** → “¿qué está pasando ahora?”. Debajo: Grafana vs
Power BI.

**Guion:**

> “La alta dirección pregunta ‘¿cómo evoluciona el OEE, qué máquina pierde más
> horas, dónde invertir?’. Eso es análisis histórico, comparativos, Pareto,
> MTBF/MTTR. La respuesta natural es Power BI.
>
> El supervisor pregunta ‘¿cómo está la línea ahora, debo intervenir?’. Eso es
> near real-time, estado por máquina y alertas. La respuesta natural es Grafana.
>
> No son intercambiables: Grafana no tiene un modelo semántico ni DAX para el
> comité; Power BI no está pensado para refresco subminuto ni alertas
> operativas. Por eso la solución tiene dos capas sobre la misma base.”

**Transición:** “Antes de la arquitectura, veamos qué había en el Excel.”

---

## Diapositiva 4 — La fuente y sus trampas (2:50–4:20)

**En pantalla:** tabla de bloques de columnas y tres “trampas” resaltadas:
`Codigo de paro N` = minutos, filas hijas, `Unidad por display`.

**Guion:**

> “La hoja `Base De Datos` tiene 8.208 filas y 58 columnas, de enero de 2022 a
> marzo de 2025. Hay cuatro máquinas, 34 operarios y 52 referencias.
>
> La primera trampa es la más importante: la columna ‘Codigo de paro N’ no
> contiene el código, contiene los **minutos**. El código está implícito en la
> posición de la columna. Por ejemplo, ‘Codigo de paro 5 = 40’ significa 40
> minutos del código 5. Si uno lee esa columna como código, todo el análisis
> queda mal.
>
> La segunda trampa: las filas no son una por producción. 5.157 filas tienen
> pacas y 3.051 son filas hijas de paro sin producción. Una fila de producción
> puede tener varios paros; una fila hija puede tener solo un paro. Por eso el
> modelo separa producción y paros.
>
> La tercera: ‘Unidad por display’ a veces contiene el turno, y ‘Horas no
> trabajadas’ parece un dato de día, no de paro. Ninguna de las dos se usa para
> el OEE.”

**Transición:** “Eso nos llevó a un diagnóstico de calidad.”

---

## Diapositiva 5 — Diagnóstico de calidad (4:20–5:20)

**En pantalla:** números grandes: 42 duplicados, 49,7 % sin referencia, 51,4 %
sin turno, 78,3 % sin subcódigo, 0 % de rechazos.

**Guion:**

> “Encontramos 42 filas duplicadas exactas: 1.019 pacas, 129 horas y 18,12 horas
> de paro. Las eliminamos y documentamos la diferencia.
>
> El 49,7 % de los registros de producción no tienen referencia. Sin referencia
> no hay unidades por paca, y sin unidades por paca no hay rendimiento. Por eso
> el OEE se calcula solo sobre el subconjunto con referencia; la cobertura se
> muestra en todos los tableros.
>
> El 51,4 % de las filas no tienen turno. No lo imputamos: se agrupan en ‘SD’.
> El 78,3 % de los eventos no tienen subcódigo; el drill-down rico es para los
> códigos 1, 3 y 5.
>
> Y la limitación más importante: la fuente no captura unidades rechazadas. La
> calidad se asume 100 %, así que el OEE es un límite superior. Es una
> limitación del dato, no del modelo.”

**Transición:** “Con ese diagnóstico, así se ve la solución completa.”

---

## Diapositiva 6 — Arquitectura de la solución (5:20–6:30)

**En pantalla:** diagrama: Excel → ETL Python → PostgreSQL → Grafana / Power BI.
Abajo: Docker Compose, auditoría y simulación.

**Guion:**

> “La arquitectura tiene cuatro capas. La fuente es el Excel y el P-MTO-22. La
> ingesta es un ETL en Python con pandas y openpyxl; no ejecuta macros, lee los
> datos, los limpia y los valida. El almacenamiento es PostgreSQL 16, con un
> esquema en constelación. Y el consumo son Grafana para operación y Power BI
> para estrategia.
>
> Todo está contenerizado con Docker Compose. Hay un servicio de simulación que
> inserta un minuto de producción cada dos segundos para demostrar que el
> tablero y la alerta reaccionan. Y hay una capa de auditoría: cada corrida
> guarda calidad, conciliación y alertas.
>
> La decisión de PostgreSQL es por funciones analíticas: ventanas, CTE, FILTER,
> vistas y tipos numéricos exactos. El ETL en Python se eligió por
> reproducibilidad y pruebas; Power Query o Talend no nos daban el mismo
> artefacto ejecutable en Docker.”

**Transición:** “Veamos cómo se organiza el dato en PostgreSQL.”

---

## Diapositiva 7 — Modelo dimensional (6:30–7:40)

**En pantalla:** constelación: `fact_produccion` y `fact_paro` al centro;
dimensiones alrededor: tiempo, máquina, turno, referencia, operario, código,
subcódigo. Grano de cada hecho.

**Guion:**

> “El modelo es una constelación, no una sola tabla. Tenemos dos hechos porque
> son dos procesos de negocio con granos distintos. `fact_produccion` tiene
> grano de un registro de producción: 5.137 filas. `fact_paro` tiene grano de un
> evento de paro: una fila por código con minutos mayores que cero, 16.482
> eventos.
>
> Si uniéramos todo en una tabla, cada paro duplicaría las pacas y las horas de
> su registro. La constelación evita ese fan-out.
>
> Las dimensiones son conformadas: tiempo, máquina, turno, referencia y
> operario. La dimensión de paros tiene dos niveles: código y subcódigo, con
> `nivel`, `subcodigo_padre` y `ruta` para hacer drill-down.
>
> La referencia es SCD Tipo 2: si cambia la conversión unidades por paca, se
> versiona y el hecho conserva la versión vigente. Un Tipo 1 borraría la
> historia; un Tipo 3 no escala a más de dos versiones.”

**Transición:** “Con ese modelo, así se calcula el OEE.”

---

## Diapositiva 8 — Cómo se calcula el OEE (7:40–9:00)

**En pantalla:** `OEE = A × P × Q`; debajo, las tres fórmulas y un ejemplo
numérico. Nota: “Calidad = 1 por limitación de la fuente”.

**Guion:**

> “OEE es disponibilidad por rendimiento por calidad.
>
> Disponibilidad es horas operativas sobre horas trabajadas. Las horas
> operativas son las horas trabajadas menos el paro. El paro sale de los 18
> códigos; de hecho, la columna ‘Tiempo de Paro’ coincide con la suma de los 18
> pares en el 100 % de las filas.
>
> Rendimiento es unidades producidas sobre unidades ideales. Las unidades
> producidas son pacas por unidades por paca, que salen del catálogo. Las
> unidades ideales son minutos operativos por 72 unidades por minuto.
>
> Calidad sería unidades buenas sobre producidas, pero la fuente no captura
> rechazos. Por eso la asumimos 100 % y decimos que el OEE es un límite
> superior.
>
> Hay un detalle fino: las filas hijas de paro no siempre tienen la misma
> referencia o turno. Para no perder paros, la vista agrega producción y paro
> por día y máquina, hace un FULL OUTER JOIN y asigna el paro a las horas con
> referencia en proporción a las horas trabajadas. Es una decisión documentada:
> no podemos saber a qué referencia pertenece un paro si la fila no la trae.
>
> También aplicamos un tope de rendimiento al 100 %. El 58 % de las
> observaciones día/máquina superan 100 %, lo que indica que el estándar de 72
> unidades por minuto está subestimado. Conservamos el valor sin tope para
> diagnosticar y el valor con tope para el OEE oficial.”

**Transición:** “¿Y cómo sabemos que el dato cargado es el mismo que el Excel?”

---

## Diapositiva 9 — ETL y conciliación (9:00–10:10)

**En pantalla:** tabla de conciliación: filas, pacas, horas, paro, eventos.
Números: 8.208 → 8.166; 5.137; 16.482; 377.759; 37.934,35; 8.431,535.

**Guion:**

> “El ETL lee 8.208 filas, detecta 42 duplicados exactos y carga 8.166 filas.
> De ahí salen 5.137 registros de producción y 16.482 eventos de paro.
>
> La conciliación es la prueba de que no inventamos nada. Después de
> deduplicar, la fuente y la base coinciden en pacas, horas trabajadas y horas
> de paro. La diferencia bruta son exactamente los 42 duplicados: 1.019 pacas,
> 129 horas y 18,12 horas de paro.
>
> El ETL es idempotente: trunca y recarga en una transacción. Si falla, hace
> rollback. Y deja una bitácora con 25 reglas de calidad y la conciliación en
> `audit.etl_quality` y `audit.etl_reconciliacion`.
>
> La regla es: si una métrica crítica no da cero con tolerancia de 0,01, el ETL
> falla. No se carga un dato que no concilie.”

**Transición:** “Con ese dato confiable, veamos los resultados.”

---

## Diapositiva 10 — Resultados: OEE por máquina (10:10–11:10)

**En pantalla:** gráfico de barras OEE por máquina: V1 63,0 %, V2 33,7 %,
V3 73,6 %, V4 75,5 %; línea de meta 75 %.

**Guion:**

> “El OEE global es 70,4 %. Pero el promedio esconde la historia. Vinilos_3 y
> Vinilos_4 están en la meta, con 73,6 % y 75,5 %. Vinilos_1 está en 63 %.
> Vinilos_2 está en 33,7 %, muy por debajo.
>
> ¿Por qué Vinilos_2? No es solo disponibilidad: su rendimiento es 55,8 %,
> mientras el resto está arriba del 95 %. Eso apunta a velocidad, referencia,
> dosificación o transfer. Además tiene el MTBF más bajo, 2,54 horas, y el MTTR
> más alto, 0,84 horas: falla más y tarda más en repararse.
>
> El OEE de 2024 es 71,0 % y el de 2025, a marzo, es 70,2 %. El de 2022 no se
> calcula porque no hay referencias; el de 2023 es parcial, con 23 % de
> cobertura.”

**Transición:** “Para saber dónde atacar, el Pareto.”

---

## Diapositiva 11 — Pareto de causas (11:10–12:00)

**En pantalla:** Pareto 2024: 16 (1.304 h), 5 (861 h), 6 (732 h), 7 (378 h);
acumulado 72,9 % en las tres primeras y 82,4 % en las cuatro.

**Guion:**

> “En 2024, tres causas concentran el 72,9 % de las horas de paro: código 16,
> alimentación y aseo; código 5, ajuste operativo; y código 6, limpieza por
> derrame. Si agregamos el 7, alistamiento, llegamos al 82,4 %.
>
> Lo llamativo es que solo el 1,9 % corresponde a fallas electromecánicas,
> energía o preventivo: códigos 1, 3 y 4. Es decir, el problema principal no es
> mantenimiento; es gestión operativa. La primera palanca es estandarizar la
> operación: 5S, ajuste, limpieza. La segunda es calibrar la velocidad de
> Vinilos_2. La inversión en mantenimiento viene después de ordenar lo
> operativo.
>
> El drill-down recomendado es código 5 hacia subcódigo 5.2, dosificación, y
> 5.5, transfer.”

**Transición:** “Eso es el análisis. Ahora veamos la operación en vivo.”

---

## Diapositiva 12 — Grafana y la alerta (12:00–13:10)

**En pantalla:** captura del tablero de Grafana y de la regla en Firing.

**Guion:**

> “Grafana es la capa operativa. Arriba tenemos OEE global, disponibilidad,
> rendimiento, paro acumulado y alertas de la última hora. Abajo, la serie de
> OEE por máquina, el estado actual, el Pareto histórico, los minutos de paro,
> el OEE por turno y las últimas alertas.
>
> Las variables permiten filtrar por máquina y por turno. El tablero se refresca
> cada 10 segundos.
>
> La regla de alerta es OEE menor que 60 % durante un minuto, por máquina. El
> umbral se justifica así: 85 % es clase mundial, 75 % es la meta y 60 % es el
> límite de control inferior, meta menos 15 puntos. Cuando se dispara, Grafana
> envía un webhook a un receptor local que guarda la alerta en
> `audit.alertas_recibidas`.
>
> En la demo forzamos una anomalía en Vinilos_4 y vemos cómo la línea se cae, el
> estado pasa a PARO y la regla pasa a Firing. En la captura se ve el valor
> 0.48708, por debajo de 0.6.”

**Transición:** “La capa estratégica es Power BI.”

---

## Diapositiva 13 — Power BI y RLS (13:10–14:10)

**En pantalla:** captura del resumen de Power BI y del Pareto; mención de
medidas DAX y RLS.

**Guion:**

> “Power BI es la capa estratégica. El modelo tiene siete dimensiones, dos
> hechos y dos vistas agregadas. Las medidas están en DAX: OEE, disponibilidad,
> rendimiento, calidad, OEE YTD, OEE del año anterior, variación YoY, MTBF,
> MTTR y Pareto acumulado.
>
> La inteligencia de tiempo se apoya en `dim_tiempo`, marcada como tabla de
> fechas, con TOTALYTD y SAMEPERIODLASTYEAR.
>
> Hay cinco páginas: resumen ejecutivo, análisis por máquina, Pareto, turnos y
> referencias, y detalle de paros. En el Pareto se puede hacer drill-down de
> código a subcódigo, y drill-through a la página de detalle.
>
> La seguridad es RLS: cuatro roles de supervisor, uno por línea, y un rol de
> gerencia sin filtro. El filtro está en `dim_maquina` y se propaga a los
> hechos.
>
> El proyecto está en formato PBIP con modelo TMSL y reporte PBIR, no en .pbix
> binario. Eso permite revisarlo en Git y hacer diff de las medidas.”

**Transición:** “Para cerrar, las conclusiones y el plan de mejora.”

---

## Diapositiva 14 — Conclusiones y mejoras (14:10–15:00)

**En pantalla:** tres conclusiones y tres mejoras; frase final.

**Guion:**

> “Tres conclusiones. Primera: la solución convierte un Excel mensual en un
> modelo dimensional confiable, con conciliación al 100 %. Segunda: el
> problema principal es operativo, no solo mecánico; las causas 16, 5 y 6
> explican el 73 % de las horas. Tercera: Vinilos_2 es la prioridad, por
> rendimiento y por MTBF/MTTR.
>
> Tres mejoras. Primera: capturar unidades rechazadas para completar la calidad.
> Segunda: completar referencia y turno en la fuente; hoy la cobertura de
> referencia es 52,8 % de las horas. Tercera: calibrar el estándar de 72
> unidades por minuto, porque el 58 % de las observaciones supera 100 % de
> rendimiento.
>
> La frase final: el Excel cuenta lo que pasó; esta solución explica por qué
> pasó y avisa cuando está pasando. Gracias.”

---

## Anexo: chuleta de números

| Dato | Valor |
|---|---:|
| Filas leídas | 8.208 |
| Duplicados | 42 |
| Después de dedup | 8.166 |
| Producción | 5.137 |
| Eventos de paro | 16.482 |
| Pacas | 377.759 |
| Horas trabajadas | 37.934,35 |
| Horas de paro | 8.431,535 |
| OEE global | 70,4 % |
| OEE 2024 | 71,0 % |
| OEE 2025 | 70,2 % |
| V1 / V2 / V3 / V4 | 63,0 / 33,7 / 73,6 / 75,5 % |
| Pareto 2024 top 3 | 72,9 % |
| Pareto 2024 top 4 | 82,4 % |
| Fallas electromecánicas | 1,9 % |
| Cobertura de referencia | 52,8 % |
| MTBF / MTTR | 2,5–3,9 h / 0,6–0,84 h |

## Anexo: qué hacer si te quedas en blanco

1. Respira y vuelve a la fórmula: **A × P × Q**.
2. Si te preguntan por un número, di el orden de magnitud y ofrece la consulta:
   “está en `vw_kpi_global` / `audit.etl_reconciliacion`”.
3. Si te preguntan algo que no sabes, di: “no lo tengo calculado, pero la
   consulta está en `db/queries/…` y lo verifico”.
4. Nunca inventes un dato. El proyecto se sostiene en la conciliación.
