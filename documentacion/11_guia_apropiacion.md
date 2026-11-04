# Guía de apropiación del proyecto OEE Envasado

> **Para quién es esta guía:** para ti, que vas a presentar, defender y operar
> el proyecto. No es el informe académico: es el “detrás de cámaras” —qué data
> hay, por qué se tomó cada decisión, cómo se calcula cada métrica, cómo entrar
> a la base, a Grafana y a Power BI, y cómo explicarlo sin depender de nadie.
>
> **Cómo leerla:** si tienes 20 minutos, lee las secciones 1, 3 y 10. Si tienes
> una hora, lee todo. Si vas a exponer, usa la sección 10 como guion.

---

## 1. La historia en una página

La empresa fabrica vinilos y témperas en cuatro líneas de envasado:
`Vinilos_1`, `Vinilos_2`, `Vinilos_3` y `Vinilos_4`. Cada turno, las operarias
llenan a mano el formato **P-MTO-22** (“hora a hora”): producción, códigos de
paro y duración. Producción envía los formatos a mantenimiento; mantenimiento
los transcribe a un **Excel con macros** (`SEGUIMIENTO TEMPERAS Y VINILOS
Actividad.xlsm`), y de ahí salen tablas dinámicas y gráficos para el comité
mensual.

Ese esquema resuelve el reporte mensual, pero no permite:

1. **Estratégico:** comparar máquinas, turnos, referencias y años; identificar
   causas raíz y priorizar inversión.
2. **Operativo:** ver la línea casi en tiempo real y recibir una alerta cuando
   el OEE se sale de rango.

La solución que construimos hace tres cosas:

- **Ordena el dato:** ETL reproducible que limpia, valida, seudonimiza y carga
  un modelo dimensional en PostgreSQL.
- **Calcula la eficiencia:** OEE = Disponibilidad × Rendimiento × Calidad, con
  sus componentes, Pareto de paros, MTBF/MTTR y comparativos.
- **Lo pone a disposición de dos usuarios distintos:** Grafana para operación
  (minutos/segundos) y Power BI para estrategia (meses/años).

La frase que resume el proyecto: **“el Excel cuenta lo que pasó; esta solución
explica por qué pasó y avisa cuando está pasando”**.

---

## 2. La data: qué hay exactamente y qué descubrimos

### 2.1 Fuente y volumen

| Archivo | Uso |
|---|---|
| `SEGUIMIENTO TEMPERAS Y VINILOS Actividad.xlsm` | Hoja `Base De Datos` (8.208 filas × 58 columnas), catálogos y tablas dinámicas. |
| `P-MTO-21-V1_Registro_paros_de_produccion_actividad.pdf` | Reglas de negocio: 17 códigos de paro, campos del formato, flujo y reportes. |

Periodo: **2022-01-01 a 2025-03-28**. Cuatro máquinas. 34 operarios (texto
libre). 52 referencias (texto libre) contra 40 del catálogo.

La hoja `Base De Datos` tiene el encabezado en la **fila 9** y los datos desde la
fila 10. Las columnas se agrupan así:

| Bloque | Columnas | Qué contiene realmente |
|---|---|---|
| Identificación | `Fecha`, `Mes`, `Año`, `Maquina`, `Operario`, `Referencia` | Fecha y dimensiones; operario y referencia son texto libre. |
| Producción | `Unidades producidas cada minuto`, `Unidad por display`, `Display por paca`, `Pacas producidas`, `Horas trabajadas`, `Turno` | `Unidades/minuto` y `Display/paca` están vacías; `Unidad/display` a veces contiene el turno. |
| Resumen de paro | `Horas no trabajadas`, `Tipo de paro`, `Observaciones de paro` | Texto heredado; `Horas no trabajadas` es un dato de día. |
| Códigos 1–18 | `Codigo de paro N` y `Codigo N en horas` | **La columna “Codigo de paro N” contiene minutos, no el código.** El código es la posición N. |
| Cierre | `Tiempo de Paro`, `Observaciones` | `Tiempo de Paro` = suma de los 18 pares código/horas. |

### 2.2 Los 10 hallazgos que tienes que saber explicar

1. **“Codigo de paro N” son minutos, no el código.**
   Ejemplo: `Codigo de paro 5 = 40` significa “40 minutos de paro del código 5”,
   no “código 5”. La columna `Codigo 5 en horas = 0,6667` confirma la conversión.
   El ETL usa la **posición de la columna** como código y despivota los 18 pares.

2. **Las filas no son una por registro de producción.**
   De 8.208 filas, **5.157** tienen pacas (producción) y **3.051** son filas
   hijas de paro sin producción. Una fila de producción puede tener varios
   paros; una fila hija puede tener solo un paro. Por eso el modelo separa
   `fact_produccion` y `fact_paro`.

3. **`Tiempo de Paro` concilia perfecto.**
   En el 100 % de las filas, `Tiempo de Paro` = suma de los 18 `Codigo N en
   horas`. Es una de las mejores noticias del dataset: el problema no es la
   suma, es la captura.

4. **`Unidad por display` está contaminada.**
   587 filas tienen un turno (`6am-2pm`, etc.) en esa columna. No se usa como
   unidad de empaque; la conversión sale del catálogo de referencias.

5. **`Horas no trabajadas` no es “tiempo de paro”.**
   Toma valores 0, 8, 16, 24 y parece un dato de día (¿la planta trabajó 1, 2 o
   3 turnos?). No se usa en el OEE; se conserva en `fact_produccion` para
   trazabilidad.

6. **`Tipo de paro` es una numeración heredada.**
   Usa códigos 1–19 con textos como `[19] No aplica`, `17. PARO DE MAQUINA`,
   `9.FALTA DE PROGRAMACIÓN`. No coincide con los 17 códigos del P-MTO-22. Se
   conserva como texto, pero el análisis usa las columnas 1–18.

7. **El código 18 no está en el P-MTO-22.**
   La hoja `Registro` lo define como “Desinfección”; el PDF solo lista 17
   códigos. Se carga como código 18 y se marca `documentado_pmto22 = false`.

8. **Referencias: 52 valores contra 40 del catálogo.**
   Hay typos y variantes: `Alocdor` vs `Alocolor`, `12col` vs `12 col`,
   `Estilo Kids` vs `Stilo Kids`, `Parchesitos 125 cc`. Se normalizan y, cuando
   no hay catálogo, se deriva `unidades/paca` por regla de formato.

9. **Turnos: 8 variantes de texto y 51,4 % sin turno.**
   `6am-2pm (Turno 1)`, `6am-2pm`, `2pm-10pm (Turno 2)`, `10pm-6am (Turno 3)`,
   `6am-4:30pm`, `6am-6pm`, `6pm-6am`, `No aplica`, vacío. Se normalizan a
   `T1`, `T2`, `T3`, `T1E`, `T12`, `T23`, `SD`. No se imputa turno.

10. **Subcódigos solo para los códigos 1, 3 y 5.**
    El formato solo detalla esos tres. El **78,3 %** de los 16.482 eventos queda
    en `SIN_ESP`. Además, hay 945 eventos con numeración vieja `4.x` que se
    mapean a `5.x` por nombre (4.2→5.2, 4.4→5.5, etc.).

### 2.3 Un ejemplo completo, fila a fila

Fila 10 del Excel (2025-03-25, `Vinilos_3`, Diana, `Parchesitos 22cc (6 col)`):

- `Pacas producidas = 25`, `Horas trabajadas = 9.5`, turno `6am-4:30pm`.
- `Codigo de paro 5 = 40` min, `Codigo 5 en horas = 0.6667`.
- `Codigo de paro 6 = 117` min, `Codigo 6 en horas = 1.95`.
- `Codigo de paro 7 = 60` min, `Codigo 7 en horas = 1.0`.
- `Codigo de paro 8 = 60` min, `Codigo 8 en horas = 1.0`.
- `Codigo de paro 15 = 30` min, `Codigo 15 en horas = 0.5`.
- `Codigo de paro 16 = 70` min, `Codigo 16 en horas = 1.1667`.
- `Codigo de paro 17 = 6` min, `Codigo 17 en horas = 0.1`.
- `Tiempo de Paro = 6.3833` h (suma exacta).

El ETL produce:

- **1 fila** en `fact_produccion`: 25 pacas, 9,5 h, 15.000 unidades (25 × 600),
  41.040 minutos ideales (9,5 × 60 × 72).
- **7 filas** en `fact_paro`: una por cada código con minutos > 0, con
  `minutos_paro`, `horas_paro`, código, subcódigo (5.2 para el código 5) y
  dimensión de máquina/turno/referencia/operario.

Así se evita duplicar las 25 pacas siete veces.

### 2.4 Conteos que debes memorizar

| Concepto | Valor |
|---|---:|
| Filas leídas | 8.208 |
| Duplicados exactos | 42 |
| Filas después de deduplicar | 8.166 |
| Registros de producción | 5.137 |
| Eventos de paro | 16.482 |
| Pacas | 377.759 |
| Horas trabajadas | 37.934,35 |
| Horas de paro | 8.431,535 |
| Registros sin referencia | 2.586 (50,3 %) |
| Cobertura de referencia (horas) | 52,8 % |
| Turnos sin asignar | 4.218 |
| Eventos sin subcódigo | 12.898 (78,3 %) |
| Outliers marcados | 22 |
| Incompletos | 3 |
| Paros sin producción el mismo día/máquina | 5 (1,92 h) |
| Filas con paro > horas | 45 |

---

## 3. Las métricas: cómo se abordaron y por qué

### 3.1 La fórmula y la lógica

**OEE = Disponibilidad × Rendimiento × Calidad**

Cada componente responde a una pregunta distinta:

| Componente | Pregunta | Fórmula | Dónde se calcula |
|---|---|---|---|
| **Disponibilidad** | ¿La máquina estuvo disponible? | `(horas trabajadas − horas de paro) / horas trabajadas` | `vw_oee_base_dia` → `vw_oee_diario_maquina` |
| **Rendimiento** | ¿Produjo a la velocidad esperada? | `unidades producidas / (minutos operativos × 72)` | idem |
| **Calidad** | ¿Lo producido era bueno? | `unidades buenas / unidades producidas` | **No disponible**; se asume 1,0 |

La fuente no tiene unidades rechazadas. Por eso el OEE que reportamos es un
**límite superior**: `A × P × 1`. Es honesto decirlo en la exposición. Si se
agrega `unidades_rechazadas` al formato, solo cambia la vista/DAX, no el modelo.

### 3.2 Tiempo planificado, operativo y paro

La fuente da `Horas trabajadas` por registro de producción. La tratamos como
**tiempo atendido/planificado** de ese registro. El paro se resta:

```
horas_operativas = max(horas_trabajadas − horas_paro, 0)
disponibilidad   = horas_operativas / horas_trabajadas
```

No usamos `Horas no trabajadas` porque su semántica es de día y no concilia.
Ejemplo: un registro con 9,5 h y 6,38 h de paro tiene 3,12 h operativas y
disponibilidad 32,8 %.

### 3.3 Rendimiento: unidades y unidades ideales

Para convertir pacas a unidades necesitamos `unidades_por_paca`. Sale del
catálogo de referencias (`Tablas Desplegables`, columna AA) o de una regla de
formato:

- 6 colores × 100 unidades/display = 600 unidades/paca (22cc).
- 12 colores × 50 = 600 (22cc).
- 6 colores × 120 = 720 (15cc).
- 12 colores × 28 = 336 (30cc 12 col).
- `Parchesitos 125cc` = 45.
- etc.

Luego:

```
unidades_producidas = pacas × unidades_por_paca
minutos_ideales     = horas_trabajadas × 60 × 72
rendimiento         = unidades_producidas / minutos_ideales_operativos
```

**¿Por qué 72 u/min?** Es el estándar que usa el Excel actual (`Tablas
Desplegables`, columna AB). Se documenta como supuesto. Si el estándar está mal
calibrado, el rendimiento se distorsiona; por eso conservamos
`rendimiento_calculado` sin tope y `rendimiento` con tope al 100 %.

**El problema de rendimiento > 100 %:** 58 % de las observaciones día/máquina
superan 100 %. Eso no es físicamente posible si el estándar fuera correcto.
Posibles causas: el estándar de 72 u/min es bajo, la conversión unidades/paca
está subestimada, o las pacas están sobre-registradas. Decisión: el OEE oficial
usa `MIN(rendimiento, 1)`; el valor sin tope queda para diagnosticar.

### 3.4 La asignación proporcional del paro (la parte fina)

Problema: las filas hijas de paro no siempre tienen la misma referencia/turno
que la fila de producción. Si se unen por turno/referencia, se pierden paros.
Solución en `vw_oee_base_dia`:

1. Se agrega producción por **día × máquina**: horas trabajadas, horas con
   referencia, unidades, minutos ideales.
2. Se agrega paro por **día × máquina**: horas de paro, eventos, fallas.
3. Se usa `FULL OUTER JOIN` para incluir paros sin producción.
4. Las horas de paro se asignan a las horas con referencia en proporción a las
   horas trabajadas:

```
horas_paro_ref = horas_paro_total × (horas_trabajadas_ref / horas_trabajadas)
```

5. Con eso:

```
horas_operativas_ref = max(horas_trabajadas_ref − horas_paro_ref, 0)
disponibilidad       = horas_operativas_ref / horas_trabajadas_ref
rendimiento          = unidades / (minutos_ideales × disponibilidad)
OEE                  = disponibilidad × MIN(rendimiento, 1)
```

Esta asignación es una **decisión documentada**: no se puede saber a qué
referencia pertenece un paro si la fila hija no la trae. Se distribuye por horas
trabajadas, que es la mejor proxy disponible. La cobertura de referencia se
muestra al lado para que el lector sepa qué tan representativo es el OEE.

### 3.5 Los números y cómo interpretarlos

**Global:** OEE 70,4 %, disponibilidad 70,8 %, rendimiento 99,4 %, cobertura
52,8 %.

**Por año:**

| Año | OEE | Disponibilidad | Rendimiento | Cobertura |
|---|---:|---:|---:|---:|
| 2023 | 62,8 % | 62,8 % | 100 % | 23,0 % |
| 2024 | 71,0 % | 72,6 % | 97,8 % | 98,5 % |
| 2025 (ene–mar) | 70,2 % | 70,2 % | 100 % | 100 % |

- **2022 no tiene OEE:** 0 % de referencias; no hay unidades/paca.
- **2023 es parcial:** solo 23 % de cobertura; úsalo con cuidado.
- **2024–2025 son confiables** para OEE.

**Por máquina:**

| Máquina | OEE | Disponibilidad | Rendimiento | MTBF | MTTR |
|---|---:|---:|---:|---:|---:|
| Vinilos_1 | 63,0 % | 65,9 % | 95,6 % | 2,95 h | 0,73 h |
| Vinilos_2 | **33,7 %** | 60,3 % | **55,8 %** | 2,54 h | 0,84 h |
| Vinilos_3 | 73,6 % | 73,6 % | 100 % | 3,85 h | 0,59 h |
| Vinilos_4 | 75,5 % | 75,5 % | 100 % | 3,94 h | 0,60 h |

**Lectura:** Vinilos_2 no es solo un problema de paros; su rendimiento es
55,8 %, mucho más bajo que el resto. Hay que revisar velocidad, referencia,
dosificación/transfer y calibración del estándar. Vinilos_4 y Vinilos_3 están
en la meta; Vinilos_1 está en el medio.

**Pareto 2024:** los códigos 16 (alimentación/aseo), 5 (ajuste operativo) y 6
(limpieza por derrame) explican **72,9 %** de las horas. El 7 (alistamiento)
agrega 9,5 % y lleva el acumulado a 82,4 %. Solo **1,9 %** corresponde a fallas
electromecánicas/energía/preventivo (01+03+04). La conclusión para el comité:
**primero gestión operativa, luego mantenimiento**.

**MTBF/MTTR:** MTBF = horas operativas / fallas no programadas; MTTR = horas de
paro no programado / fallas. Vinilos_2 tiene el MTBF más bajo (2,54 h) y el
MTTR más alto (0,84 h): falla más y tarda más en repararse.

### 3.6 Preguntas trampa y respuestas cortas

| Pregunta | Respuesta |
|---|---|
| “Si el rendimiento es 100 %, ¿por qué el OEE no es 100 %?” | Porque la disponibilidad es 70,8 %; el OEE es el producto. |
| “¿Por qué Vinilos_2 tiene rendimiento 55,8 %?” | Su mezcla de referencias (Parchesitos 125cc, 45 u/paca) y la velocidad real están por debajo del estándar; hay que calibrar y revisar dosificación/transfer. |
| “¿Por qué 2022 no tiene OEE?” | No hay referencia en el 100 % de los registros; sin unidades/paca no hay rendimiento. |
| “¿Por qué la calidad es 100 %?” | La fuente no captura rechazos; es un supuesto documentado y el OEE es un límite superior. |
| “¿Por qué la suma de paros no coincide con `Horas no trabajadas`?” | Porque `Horas no trabajadas` es un dato de día con otra semántica; el paro real son los 18 códigos. |
| “¿Por qué el rendimiento supera 100 %?” | El estándar de 72 u/min o la conversión están subestimados; se conserva sin tope para diagnosticar y con tope para el OEE oficial. |
| “¿Cómo sé que los totales están bien?” | `audit.etl_reconciliacion` compara fuente vs cargado; las métricas críticas dan 0. |
| “¿Qué pasa si cambia el empaque?” | `dim_referencia` es SCD2; se versiona y el hecho conserva la versión vigente. |

---

## 4. El modelo dimensional: cómo está armado

### 4.1 Constelación, no una sola tabla

Tenemos **dos hechos**:

- `fact_produccion`: grano = un registro de producción (5.137 filas).
- `fact_paro`: grano = un evento de paro (16.482 filas).

Comparten dimensiones conformadas: tiempo, máquina, turno, referencia,
operario. Si uniéramos todo en una tabla, cada paro duplicaría las pacas/horas
de su registro (fan-out). La constelación evita eso y permite drill-across.

### 4.2 Dimensiones

| Dimensión | Qué representa | Clave |
|---|---|---|
| `dim_tiempo` | Calendario 2021–2027, construido | `tiempo_key = YYYYMMDD` |
| `dim_maquina` | 4 líneas | `maquina_key` |
| `dim_turno` | T1, T2, T3, T1E, T12, T23, SD | `turno_key` |
| `dim_referencia` | Referencia, colores, unidades/paca, velocidad, versión | `referencia_key` |
| `dim_operario` | Seudónimo de operaria | `operario_key` |
| `dim_codigo_paro` | Código 1–18, área, categoría, programado | `codigo_key` |
| `dim_subcodigo_paro` | Subcódigo, nivel, padre, ruta | `subcodigo_key` |
| `dim_area` | Área de impacto | `area_key` |
| `dim_personal` | Seudónimo de técnico | `personal_key` |

### 4.3 SCD Tipo 2 en `dim_referencia`

La conversión `unidades/paca` depende del empaque. Si cambia, el OEE histórico
debe seguir calculándose con la conversión vigente en la fecha. Por eso:

- `referencia_natural` + `version` = clave única.
- `vigente_desde`, `vigente_hasta`, `es_vigente`.
- El hecho guarda `referencia_key` de la versión usada.
- Si cambia el catálogo: se cierra la versión anterior y se inserta la nueva.

No hay historia de cambios en el Excel, así que todo el histórico queda en
versión 1; la estructura está lista para cuando ocurra.

### 4.4 Jerarquía de paros

`dim_codigo_paro` (nivel 1) → `dim_subcodigo_paro` (nivel 2/3):

- `1` → `1.1` → `1.1.A`.
- `5` → `5.2` (dosificación), `5.5` (transfer), etc.
- `subcodigo_padre`, `nivel` y `ruta` permiten drill-down sin recursión.
- Los códigos sin subcódigo usan `SIN_ESP`.

### 4.5 Matriz de bus

| Proceso | Tiempo | Máquina | Turno | Referencia | Operario | Código | Subcódigo | Área | Personal |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Producción | X | X | X | X | X |  |  |  |  |
| Paros | X | X | X | X | X | X | X | X | X |
| OEE diario | X | X |  |  |  |  |  |  |  |
| OEE turno | X | X | X |  |  |  |  |  |  |
| Pareto | X | X |  |  |  | X | X |  |  |
| MTBF/MTTR | X | X |  |  |  |  |  |  |  |
| Near real-time | X | X | X | X |  |  |  |  |  |

### 4.6 Qué vista usar para cada pregunta

| Pregunta | Vista / tabla |
|---|---|
| ¿OEE de una máquina en un día? | `oee.vw_oee_diario_maquina` |
| ¿OEE por mes? | `oee.vw_oee_mensual_maquina` |
| ¿OEE por turno? | `oee.vw_oee_turno` |
| ¿Pareto por código/subcódigo? | `oee.vw_pareto_paros` |
| ¿MTBF/MTTR? | `oee.vw_mtbf_mttr` |
| ¿Estado actual? | `oee.vw_estado_actual_maquina` |
| ¿Serie por minuto? | `oee.vw_oee_hora` |
| ¿KPIs globales? | `oee.vw_kpi_global` |
| ¿Detalle de un paro? | `oee.fact_paro` + dimensiones |
| ¿Detalle de producción? | `oee.fact_produccion` + dimensiones |

---

## 5. El ETL: qué hace, archivo por archivo

### 5.1 Flujo

```
extract.py  →  clean.py  →  transform.py  →  load.py
                                      ├→ quality.py
                                      └→ reconcile.py
```

| Archivo | Responsabilidad |
|---|---|
| `extract.py` | Lee la hoja `Base De Datos` con `openpyxl` (sin macros) y el catálogo de referencias. |
| `clean.py` | Deduplica, parsea fechas, normaliza turnos/referencias, seudonimiza, marca outliers, calcula minutos/horas. |
| `transform.py` | Construye dimensiones y hechos; despivota los 18 códigos; arma el staging redactado. |
| `load.py` | `TRUNCATE` + `INSERT` en una transacción; ajusta secuencias. |
| `quality.py` | 25 reglas de calidad; escribe `audit.etl_quality`. |
| `reconcile.py` | Compara fuente vs cargado; escribe `audit.etl_reconciliacion`. |
| `run_etl.py` | Orquesta todo y falla si la conciliación crítica no da 0. |

### 5.2 Reglas de limpieza más importantes

| Regla | Qué hace | Efecto |
|---|---|---|
| Deduplicar | `drop_duplicates` sobre 58 columnas | −42 filas |
| Normalizar turno | Texto → T1/T2/T3/T1E/T12/T23/SD | 4.218 SD |
| Normalizar referencia | Typos, `12col`, `Alocdor`, etc. | 52 valores → 62 miembros |
| Unidades/paca | Catálogo o regla de formato | 49,7 % de registros con referencia |
| Despivotar | 18 columnas → eventos | 16.482 eventos |
| Subcódigo | Mapeo 4.x→5.x, `SIN_ESP` | 12.898 SIN_ESP |
| PII | SHA-256 + sal; `[PERSONA]` | 0 nombres reales |
| Outliers | Capacidad ideal, horas > 16, pacas sin horas | 22 marcados |
| Incompletos | Pacas u horas faltantes | 3 marcados |
| Paro sin producción | Sin registro de producción mismo día/máquina | 5 filas, 1,92 h |

### 5.3 Conciliación (lo que debes mostrar si te preguntan)

| Métrica | Fuente | Cargado | Diferencia |
|---|---:|---:|---:|
| Filas de producción | 5.137 | 5.137 | 0 |
| Pacas | 377.759 | 377.759 | 0 |
| Horas trabajadas | 37.934,35 | 37.934,35 | 0 |
| Horas de paro | 8.431,535 | 8.431,535 | 0 |
| Eventos de paro | 16.482 | 16.482 | 0 |
| Pacas brutas vs dedup | 378.778 | 377.759 | −1.019 (explicada) |
| Horas brutas vs dedup | 38.063,35 | 37.934,35 | −129 (explicada) |
| Paro bruto vs dedup | 8.449,65 | 8.431,54 | −18,12 (explicada) |

La regla es: **las métricas críticas deben dar 0 con tolerancia 0,01**; las
diferencias brutas se explican por los 42 duplicados.

### 5.4 Idempotencia

- El ETL trunca hechos y dimensiones (excepto `dim_tiempo`) y recarga en una
  transacción. Si falla, `ROLLBACK`.
- `fact_produccion.origen_fila` y `fact_paro(origen_fila, origen_columna)` son
  únicos.
- `reset_sequences()` ajusta las secuencias después de la carga.
- `audit.etl_run` guarda `run_id`, estado, conteos y notas.

### 5.5 Cómo agregar datos nuevos

1. Reemplazar/ampliar el `.xlsm` en `data/raw/`.
2. `make etl` (vuelve a cargar todo; es idempotente).
3. Si el nuevo archivo trae una referencia nueva, el ETL crea el miembro con
   `origen = REGLA_FORMATO` o `SIN_DATO`.
4. Si trae un código/subcódigo nuevo, se agrega al catálogo/dinámico y se marca
   `es_estimado = true` si no estaba.
5. Revisar `audit.etl_quality` y `audit.etl_reconciliacion`.

---

## 6. Cómo entrar a la base de datos

### 6.1 Datos de conexión

| Parámetro | Valor |
|---|---|
| Host | `localhost` (desde tu máquina) / `postgres` (desde otro contenedor) |
| Puerto | `5432` |
| Base | `oee_bi` |
| Usuario solo lectura | `oee_bi` |
| Usuario ETL | `oee_etl` |
| Usuario admin | `oee_admin` |
| Contraseñas | en `.env` (`OEE_BI_PASSWORD`, `OEE_ETL_PASSWORD`, `POSTGRES_PASSWORD`) |

No pegues contraseñas en el chat ni en Git. Para verlas localmente:

```bash
grep OEE_BI_PASSWORD .env
```

### 6.2 DBeaver paso a paso

1. `Database → New Database Connection → PostgreSQL`.
2. Host `localhost`, port `5432`, database `oee_bi`, username `oee_bi`.
3. Password: la de `.env`.
4. En `Driver properties`, `sslmode = disable` si es local.
5. `Test Connection` → `Finish`.
6. En el navegador, expandir `oee_bi → Schemas → oee → Views`.
7. Abrir `vw_kpi_global` y ejecutar `SELECT * FROM oee.vw_kpi_global;`.

### 6.3 psql desde el contenedor

```bash
# Como usuario de solo lectura
docker compose exec postgres psql -U oee_bi -d oee_bi

# Como admin (para calidad/auditoría)
docker compose exec postgres psql -U oee_admin -d oee_bi
```

Dentro de psql:

```sql
\dn                 -- esquemas
\dv oee.*           -- vistas
\d+ oee.fact_paro   -- estructura
SELECT * FROM oee.vw_kpi_global;
```

### 6.4 Las 6 consultas que debes correr primero

```sql
-- 1. KPIs globales
SELECT * FROM oee.vw_kpi_global;

-- 2. OEE por máquina (histórico)
SELECT maquina,
       ROUND((SUM(horas_operativas_ref)/NULLIF(SUM(horas_trabajadas_ref),0))::numeric,3) AS disponibilidad,
       ROUND(LEAST(SUM(unidades_producidas)/NULLIF(SUM(minutos_ideales_operativos),0),1)::numeric,3) AS rendimiento,
       ROUND(((SUM(horas_operativas_ref)/NULLIF(SUM(horas_trabajadas_ref),0))
              * LEAST(SUM(unidades_producidas)/NULLIF(SUM(minutos_ideales_operativos),0),1))::numeric,3) AS oee
FROM oee.vw_oee_diario_maquina
GROUP BY maquina ORDER BY oee DESC;

-- 3. Pareto 2024
SELECT codigo, causa, ROUND(SUM(horas_paro),1) AS horas
FROM oee.vw_pareto_paros
WHERE anio = 2024
GROUP BY codigo, causa
ORDER BY horas DESC;

-- 4. MTBF/MTTR por máquina
SELECT maquina,
       ROUND((SUM(horas_operativas)/NULLIF(SUM(fallas),0))::numeric,2) AS mtbf_h,
       ROUND((SUM(horas_paro_no_programado)/NULLIF(SUM(fallas),0))::numeric,2) AS mttr_h
FROM oee.vw_mtbf_mttr
GROUP BY maquina ORDER BY maquina;

-- 5. Estado actual (si el simulador está corriendo)
SELECT * FROM oee.vw_estado_actual_maquina ORDER BY maquina;

-- 6. Conciliación de la última carga
SELECT metrica, valor_fuente, valor_cargado, diferencia, concilia
FROM audit.etl_reconciliacion
ORDER BY id DESC LIMIT 20;
```

### 6.5 Esquemas y tablas que debes conocer

| Esquema | Contenido | Quién accede |
|---|---|---|
| `oee` | Dimensiones, hechos, vistas | `oee_bi`, `oee_grafana`, `oee_etl` |
| `stg` | `registro_crudo` (payload redactado) | `oee_etl` |
| `audit` | `etl_run`, `etl_quality`, `etl_reconciliacion`, `alertas_recibidas` | `oee_etl`, `oee_bi` (lectura) |

### 6.6 Backup y restauración

```bash
# Backup
docker compose exec -T postgres pg_dump -U oee_admin -d oee_bi -Fc > backup_oee.dump

# Restaurar (base vacía)
docker compose exec -T postgres pg_restore -U oee_admin -d oee_bi < backup_oee.dump
```

---

## 7. Cómo entrar a Grafana y demostrar la alerta

### 7.1 Acceso

- URL: `http://localhost:3000`.
- Usuario: `GRAFANA_ADMIN_USER` de `.env` (por defecto `admin`).
- Contraseña: `GRAFANA_ADMIN_PASSWORD` de `.env`.
- Dashboard: carpeta **OEE** → “OEE Envasado — Operación near real-time”.

### 7.2 Qué mostrar en una demo

1. **Fila superior:** OEE global, disponibilidad, rendimiento, paro acumulado,
   alertas. Explicar que se calculan sobre los últimos 15 minutos.
2. **OEE por máquina:** la línea que se cae; en la demo forzada será
   Vinilos_4.
3. **Estado actual:** tabla OK / ALERTA / PARO. Si una máquina está en PARO,
   el OEE baja.
4. **Pareto:** causas históricas (últimos 5 años).
5. **Minutos de paro:** la serie que se dispara.
6. **OEE por turno:** comparación T1/T2/T3.
7. **Últimas alertas:** `firing` / `resolved`.

### 7.3 Forzar la alerta (guion de demo)

```bash
# 1. Detener el simulador normal
docker compose stop simulator

# 2. Levantar uno forzado en Vinilos_4
docker compose --profile sim run -d --service-ports --name oee-sim-force \
  simulator python simulate_realtime.py --serve-alerts \
  --force-anomaly --anomaly-machine Vinilos_4

# 3. Esperar ~90 s y consultar el estado
curl -u admin:TU_PASSWORD http://localhost:3000/api/prometheus/grafana/api/v1/rules

# 4. Ver la alerta recibida en la base
docker compose exec postgres psql -U oee_admin -d oee_bi \
  -c "SELECT * FROM audit.alertas_recibidas ORDER BY recibido_en DESC LIMIT 5;"

# 5. Volver a la normalidad
docker stop oee-sim-force && docker rm oee-sim-force
docker compose --profile sim up -d simulator
```

La regla usa `OEE < 0,60` durante `1m`. En la captura del informe se ve el
valor `0.48708` y el estado **Firing**.

### 7.4 Si algo falla

| Síntoma | Causa | Solución |
|---|---|---|
| “No data” | Simulador apagado o ventana de 30 min sin datos | `make sim`; refrescar |
| “column maquina does not exist” | Dashboard viejo en caché | recargar con `?v=...` |
| Alerta no dispara | OEE > 0,60 en la ventana de 10 min | forzar anomalía más tiempo |
| Webhook no recibe | Simulador sin `--serve-alerts` | `make sim` |
| Datasource sin conexión | Contraseña en `.env` incorrecta | revisar y `docker compose restart grafana` |

---

## 8. Cómo abrir y explicar Power BI

### 8.1 Formato

El proyecto es **PBIP** con modelo **TMSL** (`model.bim`) y reporte **PBIR**
(JSON por página/visual). No hay `.pbix` binario. Ventaja: Git puede diffear,
revisar y fusionar; el modelo y las medidas son texto.

### 8.2 Abrir

1. Power BI Desktop (Windows) actualizado.
2. `Archivo → Abrir` → `powerbi/OEE_Vinilos.pbip`.
3. Si pide vista previa: `Opciones → Características de vista previa` →
   activar PBIP/PBIR.
4. `Inicio → Actualizar`.
5. Credenciales: servidor `localhost:5432`, base `oee_bi`, usuario `oee_bi`,
   contraseña de `.env`.
6. Verificar que `dim_tiempo` esté marcada como **tabla de fechas** (`fecha`).

### 8.3 Modelo

- Dimensiones: `dim_tiempo`, `dim_maquina`, `dim_turno`, `dim_referencia`,
  `dim_operario`, `dim_codigo_paro`, `dim_subcodigo_paro`.
- Hechos: `fact_produccion`, `fact_paro`, `vw_oee_diario_maquina`,
  `vw_mtbf_mttr`.
- Medidas: `_Medidas` (tabla contenedora).
- Relaciones 1:* en una dirección, dimensión → hecho.

### 8.4 Medidas DAX que debes saber explicar

| Medida | Fórmula | Qué significa |
|---|---|---|
| `OEE %` | `[Disponibilidad %] * MIN([Rendimiento %],1) * [Calidad %]` | Eficiencia global con tope de rendimiento. |
| `Disponibilidad %` | `SUM(horas_operativas_ref)/SUM(horas_trabajadas_ref)` | Tiempo disponible. |
| `Rendimiento %` | `SUM(unidades)/SUM(minutos_ideales_operativos)` | Velocidad vs estándar. |
| `Calidad %` | `1` | Supuesto documentado. |
| `OEE YTD %` | `TOTALYTD([OEE %], dim_tiempo[fecha])` | Acumulado del año. |
| `OEE Año Anterior %` | `CALCULATE([OEE %], SAMEPERIODLASTYEAR(...))` | Mismo periodo del año anterior. |
| `Var OEE YoY pp` | `[OEE %] - [OEE Año Anterior %]` | Mejora/empeora. |
| `Horas Paro` | `SUM(fact_paro[horas_paro])` | Horas perdidas. |
| `MTBF (h)` | `horas_operativas / fallas` | Confiabilidad. |
| `MTTR (h)` | `horas_paro_no_programado / fallas` | Velocidad de reparación. |
| `Pareto % Acumulado` | `CALCULATE` + `FILTER(ALLSELECTED(...))` | Acumulado para el Pareto. |
| `Semáforo OEE` | `SWITCH(TRUE(), ...)` | Verde/amarillo/naranja/rojo. |

### 8.5 Páginas

1. **Resumen ejecutivo:** tarjetas OEE/A/P/Calidad, línea mensual, barras por
   máquina, texto.
2. **Análisis por máquina:** slicers, OEE YTD, tabla A/P/OEE/MTBF/MTTR,
   cobertura.
3. **Pareto:** barras por causa, tabla con % acumulado, drill-down.
4. **Turnos y referencias:** OEE por turno, tabla por referencia.
5. **Detalle de paros:** tabla fecha/máquina/turno/código/subcódigo/horas,
   destino de drill-through.

### 8.6 RLS

| Rol | Filtro |
|---|---|
| `Supervisor_Vinilos_1` | `dim_maquina[codigo] = "Vinilos_1"` |
| `Supervisor_Vinilos_2` | `dim_maquina[codigo] = "Vinilos_2"` |
| `Supervisor_Vinilos_3` | `dim_maquina[codigo] = "Vinilos_3"` |
| `Supervisor_Vinilos_4` | `dim_maquina[codigo] = "Vinilos_4"` |
| `Gerencia` | Sin filtro |

Probar en `Modelado → Ver como rol`.

### 8.7 Sobre las capturas

Las imágenes `informe/img/powerbi_*.png` son una **maqueta de diseño con datos
reales** porque Power BI Desktop no corre en Linux. El PBIP es el artefacto
real; al abrirlo en Windows, reemplaza las capturas por las nativas.

---

## 9. Reproducción, Git y secretos

### 9.1 Desde cero

```bash
cd /home/dev-plague/Documents/universidad/bi/Taller_5
cp .env.example .env          # cambiar credenciales y PII_SALT
mkdir -p data/raw             # copiar .xlsm y PDF
make reset
make up
make etl
make sim
make test
```

### 9.2 Variables de `.env`

| Variable | Para qué |
|---|---|
| `POSTGRES_*` | Base y usuario admin. |
| `OEE_ETL_PASSWORD` | Rol de carga. |
| `OEE_BI_PASSWORD` | Rol de lectura Power BI/DBeaver. |
| `OEE_GRAFANA_PASSWORD` | Rol de lectura Grafana. |
| `GRAFANA_ADMIN_*` | Login de Grafana. |
| `PII_SALT` | Sal de seudonimización. **Si cambia, cambian los seudónimos.** |
| `SOURCE_XLSM` | Ruta del Excel dentro del contenedor. |
| `SIM_*` | Intervalo y probabilidad de anomalía. |

### 9.3 Qué se ignora y por qué

- `docs/`: fuente original y enunciado; no se publica.
- `data/raw/`: `.xlsm` y PDF; datos sensibles/grandes.
- `data/private/`: mapeos PII locales.
- `.env`: secretos.
- `*.pbix`: binarios; el proyecto es PBIP.
- `.openchamber/`: capturas del agente.

### 9.4 Git

El repo tiene 10 commits por fase, con autores placeholder `Integrante 1/2/3`.
Para publicar:

```bash
git remote add origin https://github.com/<usuario>/oee-envasado-bi.git
git branch -M main
git push -u origin main
```

Si el docente exige nombres reales en los commits:

```bash
git rebase -i --root
# cambiar el autor de cada commit, o usar git filter-repo
```

---

## 10. Cómo explicarlo (guiones listos)

### 10.1 Pitch de 2 minutos

> “La empresa registra producción y paros a mano y los pasa a un Excel con
> macros. Eso sirve para el comité mensual, pero no para comparar máquinas,
> turnos y años ni para reaccionar en el turno. Construimos una solución
> contenerizada: un ETL en Python que limpia y valida 8.208 filas, un modelo en
> constelación en PostgreSQL, y dos capas de consumo. Grafana muestra el OEE
> near real-time y alerta si cae por debajo de 60 %. Power BI analiza
> tendencias, Pareto, MTBF/MTTR y comparativos anuales con DAX y RLS. Los
> totales concilian al 100 % después de eliminar 42 duplicados. El hallazgo
> principal: Vinilos_2 tiene OEE 33,7 % por rendimiento, y las causas 16, 5 y 6
> explican el 73 % de las horas de paro. La calidad no se puede medir todavía
> porque la fuente no captura rechazos; el OEE es un límite superior.”

### 10.2 Demo de 10 minutos

1. **Grafana (3 min):** abrir el dashboard, mostrar OEE global y por máquina;
   señalar Vinilos_4 en PARO; mostrar la tabla de alertas.
2. **Alerta (2 min):** explicar la regla `OEE < 0,60` durante 1 min; mostrar la
   captura de la regla en Firing o forzarla.
3. **Power BI (3 min):** abrir el resumen, mostrar la línea mensual, la tabla
   por máquina y el Pareto; hacer drill-down de código 5 a subcódigo 5.2.
4. **Cierre (2 min):** reconciliación, PII, reproducibilidad y mejoras.

### 10.3 Preguntas del jurado y respuestas

| Pregunta | Respuesta |
|---|---|
| ¿Por qué PostgreSQL y no MySQL? | Ventanas, CTE, `FILTER`, vistas, tipos exactos y mejores conectores analíticos; el volumen es pequeño pero el modelo es analítico. |
| ¿Por qué constelación? | Dos procesos con granos distintos; unirlos duplicaría magnitudes. |
| ¿Por qué SCD2? | La conversión unidades/paca puede cambiar; la historia debe conservar la versión. |
| ¿Por qué calidad 100 %? | La fuente no captura rechazos; se documenta como limitación y se propone el campo. |
| ¿Por qué el rendimiento supera 100 %? | Estándar de 72 u/min o conversión subestimados; se conserva sin tope para diagnosticar y con tope para el OEE. |
| ¿Cómo validan los totales? | `audit.etl_reconciliacion`; métricas críticas con diferencia 0. |
| ¿Cómo protegen PII? | SHA-256 + sal, seudónimos, redacción de texto libre, sin nombres en la base. |
| ¿Por qué PBIP/PBIR? | Texto diffable, sin `.pbix` binario, revisable en Git. |
| ¿Por qué Grafana y Power BI? | Grafana para operación/alertas; Power BI para análisis/DAX/RLS. No son intercambiables. |
| ¿Qué harían con PLC/SCADA? | OPC UA → MQTT → TimescaleDB/PostgreSQL; mismo modelo, más frecuencia. |
| ¿Cuál es la mejora más rentable? | Completar referencia/turno y capturar rechazos; luego calibrar el estándar. |
| ¿Qué línea priorizar? | Vinilos_2: OEE 33,7 %, rendimiento 55,8 %, MTBF 2,54 h, MTTR 0,84 h. |

### 10.4 Narrativa de negocio (para el comité)

> “No todo es mantenimiento. El 72,9 % de las horas de paro de 2024 está en
> alimentación/aseo, ajuste operativo y limpieza por derrame. Solo el 1,9 % es
> falla electromecánica, energía o preventivo. La primera palanca es
> estandarizar la operación (5S, ajuste, limpieza); la segunda es calibrar la
> velocidad de Vinilos_2. La inversión en mantenimiento debe venir después de
> ordenar lo operativo.”

---

## 11. Checklist para apropiarte del proyecto

- [ ] Entender la diferencia entre `fact_produccion` y `fact_paro`.
- [ ] Saber explicar por qué “Codigo de paro N” son minutos.
- [ ] Saber calcular a mano un OEE con un ejemplo (A × P × Q).
- [ ] Saber de dónde sale `unidades_por_paca` y qué pasa si falta.
- [ ] Saber por qué se asigna el paro proporcionalmente.
- [ ] Saber por qué calidad = 1 y qué falta para completarla.
- [ ] Saber abrir DBeaver y correr `vw_kpi_global`.
- [ ] Saber abrir Grafana y forzar la alerta.
- [ ] Saber abrir el PBIP y refrescar.
- [ ] Saber probar RLS con “Ver como rol”.
- [ ] Saber ejecutar `make reset && make up && make etl && make sim`.
- [ ] Saber dónde están los secretos y por qué no se versionan.
- [ ] Saber explicar las 3 limitaciones principales y el plan de mejora.

---

## 12. Glosario

| Término | Definición |
|---|---|
| **OEE** | Overall Equipment Effectiveness: A × P × Q. |
| **Disponibilidad** | Tiempo operativo / tiempo planificado. |
| **Rendimiento** | Producción real / producción ideal. |
| **Calidad** | Unidades buenas / unidades producidas. |
| **MTBF** | Mean Time Between Failures. |
| **MTTR** | Mean Time To Repair. |
| **Grano** | Nivel de detalle de una tabla de hechos. |
| **Estrella** | Un hecho + dimensiones. |
| **Constelación** | Varios hechos + dimensiones conformadas. |
| **SCD2** | Slowly Changing Dimension Tipo 2: versiona la historia. |
| **ETL** | Extract, Transform, Load. |
| **Staging** | Zona intermedia de datos crudos/redactados. |
| **RLS** | Row-Level Security. |
| **PBIP** | Power BI Project (formato de texto). |
| **PBIR** | Power BI Enhanced Report Format (JSON por página/visual). |
| **TMSL** | Tabular Model Scripting Language (`model.bim`). |
| **PII** | Personally Identifiable Information. |
| **OPC UA / MQTT** | Protocolos de planta/streaming para PLC/SCADA. |
