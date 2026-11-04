# Medidas DAX del modelo `OEE_Vinilos`

Todas las medidas viven en la tabla `_Medidas` (tabla contenedora). Las tablas
de hechos son `vw_oee_diario_maquina`, `fact_produccion`, `fact_paro` y
`vw_mtbf_mttr`; las dimensiones, `dim_*`.

## 1. Eficiencia

```dax
OEE % =
VAR d = [Disponibilidad %]
VAR r = [Rendimiento %]
VAR c = [Calidad %]
RETURN d * MIN ( r, 1 ) * c
```

```dax
Disponibilidad % =
DIVIDE (
    SUM ( vw_oee_diario_maquina[horas_operativas_ref] ),
    SUM ( vw_oee_diario_maquina[horas_trabajadas_ref] )
)
```

```dax
Rendimiento % =
DIVIDE (
    SUM ( vw_oee_diario_maquina[unidades_producidas] ),
    SUM ( vw_oee_diario_maquina[minutos_ideales_operativos] )
)
```

```dax
Calidad % = 1
```

> `Calidad % = 1` porque la fuente no captura rechazos. Es una **limitación
> documentada**; al añadir `unidades_rechazadas`, reemplazar por
> `DIVIDE ( [Unidades Buenas], [Unidades Producidas] )`.

## 2. Inteligencia de tiempo

```dax
OEE YTD % =
TOTALYTD ( [OEE %], dim_tiempo[fecha] )
```

```dax
OEE Año Anterior % =
CALCULATE ( [OEE %], SAMEPERIODLASTYEAR ( dim_tiempo[fecha] ) )
```

```dax
Var OEE YoY pp = [OEE %] - [OEE Año Anterior %]
```

```dax
Var OEE YoY % =
DIVIDE ( [OEE %] - [OEE Año Anterior %], [OEE Año Anterior %] )
```

```dax
OEE vs Meta pp = [OEE %] - 0.75
```

> `dim_tiempo` debe estar marcada como **tabla de fechas** y `fecha` debe ser
> continua, sin huecos, para que `TOTALYTD` y `SAMEPERIODLASTYEAR` funcionen.

## 3. Paros y mantenimiento

```dax
Horas Paro = SUM ( fact_paro[horas_paro] )
```

```dax
Eventos Paro = COUNTROWS ( fact_paro )
```

```dax
MTBF (h) =
DIVIDE ( SUM ( vw_mtbf_mttr[horas_operativas] ), SUM ( vw_mtbf_mttr[fallas] ) )
```

```dax
MTTR (h) =
DIVIDE (
    SUM ( vw_mtbf_mttr[horas_paro_no_programado] ),
    SUM ( vw_mtbf_mttr[fallas] )
)
```

## 4. Pareto

```dax
Pareto % Acumulado =
VAR actual = [Horas Paro]
VAR total = CALCULATE ( [Horas Paro], ALLSELECTED ( dim_codigo_paro ) )
VAR acum = CALCULATE (
    [Horas Paro],
    FILTER ( ALLSELECTED ( dim_codigo_paro ), [Horas Paro] >= actual )
)
RETURN DIVIDE ( acum, total )
```

> Usar en una tabla o gráfico con `dim_codigo_paro[nombre]` en el eje. El
> `ALLSELECTED` respeta los slicers de máquina/año.

## 5. Producción y cobertura

```dax
Unidades Producidas = SUM ( vw_oee_diario_maquina[unidades_producidas] )
Pacas Producidas = SUM ( vw_oee_diario_maquina[pacas] )
```

```dax
Cobertura Referencia % =
DIVIDE (
    SUM ( vw_oee_diario_maquina[horas_trabajadas_ref] ),
    SUM ( vw_oee_diario_maquina[horas_trabajadas] )
)
```

```dax
OEE Referencia % =
DIVIDE (
    SUM ( fact_produccion[unidades_producidas] ),
    SUM ( fact_produccion[minutos_ideales] )
)
```

> `OEE Referencia %` es una aproximación a nivel de referencia; no descuenta
> paros porque `fact_produccion` no tiene una asignación 1:1 de paros. Para el
> OEE oficial usar `[OEE %]` sobre `vw_oee_diario_maquina`.

## 6. Semáforo

```dax
Semáforo OEE =
SWITCH (
    TRUE (),
    [OEE %] >= 0.85, "🟢 Verde",
    [OEE %] >= 0.75, "🟡 Amarillo",
    [OEE %] >= 0.60, "🟠 Naranja",
    "🔴 Rojo"
)
```

## 7. Formato y carpetas

| Medida | Formato | Carpeta |
|---|---|---|
| `OEE %` | `0.0%` | OEE |
| `Disponibilidad %` | `0.0%` | OEE |
| `Rendimiento %` | `0.0%` | OEE |
| `Calidad %` | `0.0%` | OEE |
| `OEE YTD %` | `0.0%` | Tiempo |
| `OEE Año Anterior %` | `0.0%` | Tiempo |
| `Var OEE YoY pp` | `0.0%` | Tiempo |
| `Var OEE YoY %` | `0.0%` | Tiempo |
| `Horas Paro` | `0.0` | Paros |
| `Eventos Paro` | `0` | Paros |
| `MTBF (h)` / `MTTR (h)` | `0.00` | Mantenimiento |
| `Unidades Producidas` / `Pacas Producidas` | `#,0` | Producción |
| `Cobertura Referencia %` | `0.0%` | Gobierno |
| `Pareto % Acumulado` | `0.0%` | Paros |
| `Semáforo OEE` | Texto | OEE |
| `OEE vs Meta pp` | `0.0%` | OEE |
