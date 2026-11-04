# 01. Diagnóstico y requerimientos de negocio

## 1. Stakeholders y preguntas de negocio

| Stakeholder | Rol en la decisión | Preguntas que debe responder |
|---|---|---|
| **Alta dirección / Gerencia** | Inversión, prioridades, comité mensual | ¿Cómo evoluciona el OEE por línea y por año? ¿Qué máquina pierde más horas? ¿La mejora es sostenida? ¿Dónde invertir? |
| **Jefatura de Producción** | Planificación, turnos, referencias | ¿Qué turno/referencia rinde menos? ¿Cómo se compara 2024 vs 2025? ¿Qué línea limita el plan? |
| **Coordinación de Mantenimiento** | Plan de mantenimiento, repuestos | ¿Cuáles son las causas raíz? ¿Qué subcódigo concentra las fallas? ¿Cuál es el MTBF/MTTR? |
| **Supervisores de línea** | Operación diaria | ¿Cómo está la línea ahora? ¿Debo intervenir? ¿Se disparó una alerta? |
| **Calidad** | Materia prima, laboratorio, reproceso | ¿Cuánto tiempo se pierde por calidad? ¿Qué códigos 12/13/11 pesan? |
| **TI / Datos** | Gobierno, seguridad, integración | ¿El ETL es reproducible? ¿Los totales concilian? ¿Quién accede a qué? |

## 2. Diagnóstico de la fuente

### 2.1 Estructura del `.xlsm`

La hoja **`Base De Datos`** tiene 8.208 filas de datos y 58 columnas, con
encabezado en la fila 9. Cubre del **2022-01-01** al **2025-03-28**. Es un
formato **ancho**: cada fila puede contener producción y hasta 18 códigos de
paro, cada uno con minutos y horas.

| Bloque | Columnas | Observación |
|---|---|---|
| Identificación | Fecha, Mes, Año, Máquina, Operario, Referencia | Texto libre en operario y referencia. |
| Producción | Unidades/minuto, Unidad/display, Display/paca, Pacas, Horas trabajadas, Turno | `Unidades/minuto` y `Display/paca` están vacías; `Unidad/display` contiene turnos en 587 filas. |
| Paro resumen | Horas no trabajadas, Tipo de paro, Observaciones de paro | `Tipo de paro` usa una numeración heredada (1–19) distinta a la del P-MTO-22. |
| Códigos 1–18 | `Codigo de paro N` (minutos) y `Codigo N en horas` | **La columna “Codigo de paro N” no contiene el código: contiene los minutos.** El código está implícito en la posición N. |
| Cierre | Tiempo de Paro, Observaciones | `Tiempo de Paro` = suma de los 18 pares, verificado al 100 %. |

Otras hojas relevantes:

- **`TABLA CODIGOS`**: catálogo de áreas de impacto, códigos [01]–[17] y
  subcódigos 1.x, 3.x, 5.x.
- **`Tablas Desplegables`**: listas de máquinas, turnos, referencias,
  subcódigos y la tabla de conversión `unidades/paca` (columna AA).
- **`Registro`**: formulario de captura; define el código 18 como
  “Desinfección” (no documentado en el P-MTO-22).
- **`Base de datos de Sub codigos`**: bitácora auxiliar 2023-10 a 2024-05 para
  los códigos 1, 3 y 5; se usa como validación, no como fuente principal.
- **`Tiempos` / `Calculadora de tiempos`**: cálculos auxiliares con fórmulas
  rotas (`#N/A`, `#NAME?`), factor de producción por máquina (1,10 / 1,16 / 1 / 1)
  y referencia de 72 unidades/minuto.

### 2.2 Problemas de calidad detectados

| # | Problema | Magnitud | Tratamiento |
|---|---|---:|---|
| 1 | Filas duplicadas exactas | 42 filas (22 de producción) | Se conserva la primera; se documenta la diferencia (1.019 pacas, 129 h, 18,12 h de paro). |
| 2 | Filas hijas sin producción | 3.051 filas | No se descartan: se despivotan a `fact_paro`. |
| 3 | Paros sin producción el mismo día/máquina | 5 filas, 1,92 h | Se conservan en `fact_paro`; la vista diaria los incluye con `FULL OUTER JOIN`. |
| 4 | Referencia faltante o “No aplica” | 2.586 de 5.137 registros (49,7 %) | `SIN_REF`; no se calcula rendimiento/OEE en esos registros; se reporta cobertura. |
| 5 | Turno vacío o “No aplica” | 4.218 filas (51,4 %) | Miembro `SD`; no se imputa turno. |
| 6 | `Unidad por display` con texto de turno | 587 filas | Se ignora como unidad de empaque; se usa el catálogo de referencias. |
| 7 | Referencias con typos/variantes | 52 valores únicos vs 40 del catálogo | Normalización (`Alocdor→Alocolor`, `12col→12 col`, etc.) y reglas de formato. |
| 8 | Subcódigos 4.x (numeración vieja) | 945 eventos | Mapeo por nombre a 5.x (4.2→5.2, 4.4→5.5, etc.). |
| 9 | Subcódigo faltante | 78,3 % de los eventos | Miembro `SIN_ESP`; el drill-down solo es rico para códigos 1, 3 y 5. |
| 10 | Código 18 no documentado | 8 eventos | Se carga como “Desinfección (heredado)” y se marca `documentado_pmto22=false`. |
| 11 | `Tipo de paro` con códigos 19 y numeración vieja | 4.426 filas | Se conserva como texto degenerado; no se usa para el OEE. |
| 12 | `Horas no trabajadas` con semántica de día | 4.162 filas; valores 0/8/16/24 | Se conserva en `fact_produccion`, pero **no** se usa en el OEE. |
| 13 | Pacas fuera de capacidad / horas > 16 / pacas sin horas | 22 filas | `es_outlier=true`; se conservan y se excluyen del rendimiento cuando no hay base. |
| 14 | Pacas u horas faltantes | 3 filas | Se imputan a 0 y `es_incompleto=true`. |
| 15 | Paro > horas trabajadas | 45 filas | `GREATEST(...,0)` en disponibilidad; se marca en calidad. |
| 16 | Rendimiento > 100 % | 58 % de las observaciones día/máquina | Se conserva `rendimiento_calculado` y se aplica tope al 100 % en el OEE oficial. |
| 17 | Nombres de operarias y técnicos | 34 operarios + 38 técnicos | Seudonimización SHA-256 + sal; redacción en texto libre. |
| 18 | Sin datos de rechazo/calidad | 0 registros | **Limitación estructural**: el OEE usa Calidad = 100 %. |

### 2.3 Limitaciones del esquema actual de reporte

1. **Cadencia mensual**: el comité ve el dato con semanas de retraso; no hay
   operación near real-time.
2. **Sin modelo dimensional**: tablas dinámicas sobre un Excel ancho; cada
   pregunta exige rearmar la tabla.
3. **Sin trazabilidad**: no hay id de registro, hash ni bitácora de cambios.
4. **Sin calidad de datos sistemática**: los errores se detectan a mano.
5. **Sin OEE**: se reportan horas, producción y porcentajes de códigos, pero no
   la eficiencia global ni sus componentes.
6. **Sin historia de turnos/operarios**: no se puede comparar turno o persona
   con rigor.
7. **Sin granularidad horaria**: el papel “hora a hora” no se digitaliza; el
   Excel solo guarda el día.
8. **Macros y archivo único**: riesgo de corrupción, bloqueo y pérdida de
   versiones; no apto para múltiples usuarios.

## 3. Requerimientos funcionales y no funcionales

### Funcionales

- RF1: cargar producción y paros históricos con calidad y conciliación.
- RF2: calcular OEE, disponibilidad, rendimiento y calidad por máquina, mes,
  año, turno y referencia.
- RF3: analizar Pareto de causas y subcódigos, con drill-down.
- RF4: comparar periodos (mes anterior, año anterior, YTD).
- RF5: monitorear el estado actual por máquina y alertar si el OEE cae.
- RF6: simular datos hora a hora para demostrar la reacción de Grafana.
- RF7: exponer consultas SQL analíticas y un modelo semántico para Power BI.
- RF8: auditar la carga (calidad, conciliación, lineage).

### No funcionales

- RNF1: reproducible desde cero con `docker compose` + `make`.
- RNF2: sin credenciales ni datos personales en Git.
- RNF3: tiempos de consulta < 2 s en los tableros (datos históricos ~8 k filas).
- RNF4: ETL idempotente (truncar y recargar en una transacción).
- RNF5: código y configuración versionados; Power BI en formato de texto.
- RNF6: roles de mínimo privilegio y RLS por línea.

## 4. Supuestos

- El archivo `.xlsm` es la fuente oficial y el P-MTO-22 la regla de negocio.
- La conversión `unidades/paca` del catálogo es válida para todo el periodo;
  si cambia, `dim_referencia` SCD2 permite versionar.
- El estándar de 72 unidades/minuto es el vigente; se aplica a todas las
  referencias y se documenta su impacto (rendimiento > 100 %).
- La calidad no se puede medir con la fuente actual; se asume 100 % y se
  recomienda capturar rechazos.
- Las fechas y horas del Excel están en hora local de Colombia (America/Bogota).
- El comité mensual usa el mes calendario; no se maneja calendario fiscal.
