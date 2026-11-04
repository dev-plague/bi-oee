# Proyecto Power BI — `OEE_Vinilos.pbip`

## 1. Por qué PBIP + PBIR + `model.bim`

- El `.pbix` es un binario/ZIP que Git no puede diffear ni fusionar.
- **PBIP** separa modelo y reporte; **PBIR** guarda páginas y visuales en JSON.
- El modelo se versiona en **TMSL** (`model.bim`), legible y revisable en Pull
  Request.
- Las credenciales no se guardan; Power BI las pide al actualizar.

## 2. Estructura

```
powerbi/
├── OEE_Vinilos.pbip
├── OEE_Vinilos.SemanticModel/
│   ├── definition.pbism
│   └── model.bim                 # tablas, relaciones, medidas, roles RLS
├── OEE_Vinilos.Report/
│   ├── definition.pbir
│   └── definition/
│       ├── version.json
│       ├── report.json
│       └── pages/
│           ├── pages.json
│           ├── resumen/...
│           ├── maquinas/...
│           ├── pareto/...
│           ├── turnos/...
│           └── detalle/...
├── DAX_medidas.md
└── screenshots/
    ├── resumen.html
    └── pareto.html
```

## 3. Cómo abrir

1. Instalar **Power BI Desktop** (Windows) actualizado.
2. `Archivo → Abrir` → `powerbi/OEE_Vinilos.pbip`.
3. Si Power BI pide habilitar PBIP/PBIR: `Archivo → Opciones → Características
   de vista previa` → activar **Power BI Project (.pbip)** y **PBIR**.
4. `Inicio → Actualizar`. Credenciales:
   - Servidor: `localhost:5432` (o el host de Docker).
   - Base: `oee_bi`.
   - Usuario: `oee_bi`.
   - Contraseña: `OEE_BI_PASSWORD` de `.env`.
5. Verificar que el modelo tenga datos y que `dim_tiempo` esté marcada como
   **tabla de fechas** (`Modelado → Marcar como tabla de fechas` → `fecha`).

> Si Power BI no está en la misma máquina que Docker, reemplazar `localhost` por
> la IP/host correspondiente en las particiones M (`model.bim`).

## 4. Modelo

- **Dimensiones**: `dim_tiempo`, `dim_maquina`, `dim_turno`, `dim_referencia`,
  `dim_operario`, `dim_codigo_paro`, `dim_subcodigo_paro`.
- **Hechos**: `fact_produccion`, `fact_paro`, `vw_oee_diario_maquina`,
  `vw_mtbf_mttr`.
- **Medidas**: tabla `_Medidas` (ver `DAX_medidas.md`).
- **Relaciones**: 1:* en una dirección, dimensión → hecho.
- **RLS**: `Supervisor_Vinilos_1..4`, `Gerencia`.

## 5. Páginas

| Página | Visuales |
|---|---|
| Resumen ejecutivo | Tarjetas OEE/A/P/Calidad, línea mensual, barras por máquina, texto. |
| Análisis por máquina | Slicers, OEE YTD, tabla A/P/OEE/MTBF/MTTR, cobertura. |
| Pareto de paros | Slicers, barras de horas, tabla con % acumulado, texto de drill. |
| Turnos y referencias | OEE por turno, tabla por referencia, cobertura. |
| Detalle de paros | Tabla fecha/máquina/turno/código/subcódigo/horas; destino de drill-through. |

## 6. Drill-down y drill-through

- **Drill-down**: en la tabla del Pareto, usar `dim_codigo_paro` y
  `dim_subcodigo_paro`; el icono de expansión permite bajar de código a
  subcódigo.
- **Drill-through**: configurar la página 5 como destino con el campo
  `dim_codigo_paro[codigo]`; desde una causa, clic derecho → *Examinar* →
  *Detalle de paros*.

## 7. Refresco

- Modo **Import**.
- Programar después del ETL (p. ej. 06:00 y 18:00) en el workspace.
- Para near real-time usar Grafana, no Power BI.

## 8. Capturas

`screenshots/resumen.html` y `screenshots/pareto.html` son maquetas de diseño
con datos reales; las imágenes finales están en `../informe/img/`. Reemplazar
por capturas nativas al abrir el PBIP.

## 9. Limitaciones conocidas

- `Calidad % = 1` (sin rechazos en la fuente).
- OEE solo para registros con referencia (52,8 % de horas).
- El PBIP generado programáticamente puede requerir ajustes de posición/tema al
  abrirlo; el modelo y las medidas son el artefacto principal.
- La conexión usa `localhost`; ajustar según el entorno.
