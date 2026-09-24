# Pipeline EPH — Santiago del Estero

**Versión del pipeline:** `3.2.1` (ajuste de calendario y ejecución segura de períodos futuros)

Sistema para descargar, integrar, validar y calcular indicadores trimestrales a partir de microdatos públicos de la Encuesta Permanente de Hogares (EPH) del INDEC para el **Aglomerado 18 — Santiago del Estero - La Banda**.

El snapshot de referencia incluido en el repositorio cubre **12 períodos**, desde `2023T1` hasta `2025T4`. En la validación local de la versión 3.2.1 se procesó correctamente `2026T1`, llevando el histórico local de prueba a **13 períodos**. Los datos agregados del snapshot sólo cambian cuando se ejecuta explícitamente `--publicar-snapshot`; en esta revisión se actualizaron únicamente documentos de acompañamiento.

**Entregado a:** Dirección General de Estadística y Censos (DGEyC) — Santiago del Estero
**Desarrollado por:** Práctica Profesionalizante II · ITSE 2026
**Grupo:** Achaval María José · Cabaña Emilio · Constantinidi Leandro · Gomez Cinthia · Pinto Villegas Eduardo

## Alcance

El proyecto automatiza las tareas necesarias para descargar, integrar, validar y calcular indicadores trimestrales a partir de microdatos públicos. Aplica `PONDERA`, conserva valores faltantes, produce metadatos y bloquea resultados que no superan los controles críticos.

Se presenta un dashboard institucional para usuarios no técnicos. 
El Aglomerado 18 representa conjuntamente Santiago del Estero y La Banda. Los microdatos públicos no permiten separar ambas ciudades ni evaluar encuestadores o personal de carga.

## Indicadores

Indicadores principales:

- `tasa_actividad_oficial` = PEA expandida / población total expandida × 100.
- `tasa_empleo_oficial` = ocupados expandidos / población total expandida × 100.
- `tasa_desocupacion` = desocupados expandidos / PEA expandida × 100.
- `proporcion_inactiva_total` = 100 - tasa de actividad oficial. Es complementaria.

Indicadores específicos de población de 10 años y más:

- `tasa_actividad_10_mas`.
- `tasa_empleo_10_mas`.
- `tasa_inactividad_10_mas`.

Los nombres anteriores `tasa_actividad`, `tasa_empleo` y `tasa_inactividad` correspondían al denominador de 10 años y más. La migración los renombra explícitamente y no cambia su significado en silencio.

Los ingresos son nominales. No representan directamente variaciones del poder adquisitivo y requieren deflactación para comparaciones reales. En `2023T1`, `2023T2` y `2023T3`, la variable necesaria para estimar informalidad no está disponible. Por ese motivo, el indicador se presenta como no disponible y no se realiza imputación ni se reemplazan faltantes por cero.

## Estructura

```text
Pipeline-EPH-DGEyC/
├── src/pipeline.py                 Pipeline, validaciones y publicación segura
├── src/monitor_actualizaciones.py  Monitor y prevalidación de nuevas publicaciones
├── src/portal_admin.py             Lógica auxiliar del portal administrativo
├── notebooks/app.py               Portal Streamlit (consulta + administración)
├── notebooks/eda_eph_sde.py       Análisis técnico complementario
├── tests/test_pipeline.py          Suite automatizada del ETL
├── tests/test_monitor_actualizaciones.py  Pruebas del monitor
├── data/                           ZIP y TXT locales, excluidos de Git
├── results/                        Salidas locales, excluidas de Git
├── data_snapshot/                  Agregados validados para Streamlit Cloud
├── logs/                           Registro operativo local
└── docs/
    ├── DICCIONARIO_DATOS.md
    ├── METODOLOGIA.md
    ├── GUIA_USO.md
    ├── MONITOR_ACTUALIZACIONES.md
    ├── PORTAL_ADMINISTRACION.md
    └── ARQUITECTURA.md
```

`data_snapshot/` contiene sólo histórico e indicadores agregados, control de calidad agregado, estados, validaciones, metadatos, manifiesto y documentación. No contiene ZIP, microdatos individuales ni bases unidas.

## Instalación

Requiere Python 3.10 o superior.

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Linux o macOS:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Ejecución

```bash
# Un trimestre
python src/pipeline.py --anio 2025 --trimestre 4

# Un año
python src/pipeline.py --anio 2025

# Todos los períodos configurados
# Desde 3.2.1, omite automáticamente períodos futuros que nunca fueron procesados.
python src/pipeline.py --todos

# Calendario local y fechas esperadas
# No consulta INDEC en línea; para disponibilidad real usar el monitor.
python src/pipeline.py --calendario

# Volver a descargar un ZIP
python src/pipeline.py --anio 2025 --trimestre 4 --forzar
```

Para actualizar localmente el snapshot sólo después de una validación exitosa:

```bash
python src/pipeline.py --publicar-snapshot
```

Este comando no despliega la aplicación en Streamlit Cloud. Sólo prepara los archivos agregados que deben revisarse antes de versionarlos.

### Cómo interpretar `--calendario` (v3.2.1)

El calendario es un **control local**, no un verificador web. Combina la fecha esperada de publicación con `results/estado_periodos.csv`:

- `VALIDADO` / `PUBLICADO` / otros estados registrados: resultado real de una corrida local del pipeline.
- `SIN PROCESAR`: la fecha esperada ya fue alcanzada, pero no existe un estado local para ese período. Antes de procesarlo se debe consultar el monitor.
- `FUTURO`: todavía no corresponde esperar ese trimestre según el calendario configurado.

Para saber si el ZIP de microdatos está efectivamente disponible en INDEC se usa `python src/monitor_actualizaciones.py`. Esta separación evita confundir **fecha esperada**, **disponibilidad real en INDEC** y **estado del histórico local**.

## Monitor de actualizaciones INDEC

La versión 3.1 incorpora un **módulo de actualización asistida** que consulta si existen nuevos trimestres publicados por INDEC sin modificar automáticamente el histórico ni el snapshot. La revisión humana continúa siendo obligatoria.

```bash
# Consultar si hay nuevas publicaciones esperables
python src/monitor_actualizaciones.py

# Detectar y prevalidar el primer trimestre nuevo disponible
python src/monitor_actualizaciones.py --prevalidar

# Prevalidar de forma explícita un período
python src/monitor_actualizaciones.py --anio 2026 --trimestre 1 --prevalidar
```

La prevalidación descarga el ZIP oficial, verifica estructura, filtra el Aglomerado 18, calcula indicadores y aplica los controles críticos del pipeline en un área de auditoría separada (`results/monitor_actualizaciones/`). También compara el nuevo trimestre con el último histórico y genera alertas orientativas ante variaciones amplias de tasas, tamaño muestral o población expandida. **Estas alertas no son pruebas de significancia estadística y nunca publican ni invalidan por sí solas un período.**

Si la revisión es satisfactoria, la incorporación sigue utilizando el flujo normal y explícito:

```bash
python src/pipeline.py --anio 2026 --trimestre 1
python src/pipeline.py --publicar-snapshot
```

El repositorio incluye además un workflow semanal de GitHub Actions (`.github/workflows/monitor-eph.yml`) que ejecuta únicamente la consulta de disponibilidad y guarda el reporte como artefacto. No ejecuta la publicación.

## Salidas, metadatos y manifiesto

Cada CSV exportado queda acompañado por `nombre_archivo.meta.json`.

| Salida | Clasificación |
|---|---|
| `historico_SDE.csv` | Crítica |
| `indicadores_SDE_<periodo>.csv` | Analítica |
| `calidad_datos_SDE_<periodo>.csv` | Calidad |
| `validacion_esquema_<periodo>.json` | Auditoría |
| `validacion_publicacion_<periodo>.json` | Auditoría |
| `estado_periodos.csv` | Auditoría |
| logs | Operativa |
| gráficos | Visualización |
| `manifest_salidas.json` y snapshot | Disponibilización |

Los metadatos documentan fuente, período, estructura, variables, tipos, unidades, fórmulas, filtros, nulos, códigos especiales, ponderador, advertencias, estado de validación, hash e identificador de ejecución. `results/manifest_salidas.json` relaciona cada salida con su metadata.

## Control previo a publicación

Estados posibles: `PENDIENTE`, `DESCARGADO`, `PROCESADO`, `EN_REVISION`, `VALIDADO`, `FALLIDO` y `PUBLICADO`.

Antes de promover un período se comprueban descarga y ZIP, archivos individual y hogar, esquema obligatorio, Aglomerado 18, población total positiva, duplicados, rango de tasas, complementariedad actividad-inactividad, desocupación calculable, filas razonables, archivos y metadatos, y disponibilidad de informalidad.

Las salidas se construyen en una carpeta temporal. Ante una falla crítica, el período queda `FALLIDO`, se registra un mensaje entendible y no se reemplaza el histórico ni el snapshot vigente.

## Portal web

Ejecución exacta desde la raíz:

```bash
python -m streamlit run notebooks/app.py
```

La versión 3.2 (con el ajuste 3.2.1 del calendario) transforma el dashboard en un portal de siete secciones: resumen ejecutivo, evolución laboral, ingresos, calendario, calidad y auditoría, documentación y descargas, y administración. Las vistas de consulta siguen usando `results/` únicamente si el último período es `VALIDADO` o `PUBLICADO`; en caso contrario conservan el último `data_snapshot/` validado.

El área administrativa permite consultar INDEC, prevalidar una nueva publicación y revisar alertas sin usar la terminal. La incorporación final está bloqueada por defecto y requiere clave administrativa, `admin_enable_writes=true`, un reporte `LISTO_PARA_REVISION`, confirmación humana y la validación transaccional final del pipeline. Ver `docs/PORTAL_ADMINISTRACION.md`.

Para Streamlit Cloud, configurar como archivo principal:

```text
notebooks/app.py
```

En despliegues con almacenamiento efímero se recomienda mantener la publicación final deshabilitada y ejecutarla en infraestructura persistente de la Dirección.

## Tests

```bash
python -m pytest tests -q
```

Las pruebas escriben sólo en directorios temporales y verifican fórmulas, migración de nombres, rangos, metadatos, manifiesto, bloqueo de publicación, conservación del snapshot, carga agregada y rutas relativas.

Resultado automatizado de la versión 3.2.1: **68 tests aprobados**. Además, la validación manual local comprobó el portal completo, el histórico hasta `2026T1`, el monitor de `2026T2`, la prevalidación y el área administrativa en modo de escritura bloqueada. Ver `docs/VALIDACION_LOCAL_V3_2_1.md`.

## Devolución institucional y mejoras incorporadas

- Portal web adaptado a usuarios no técnicos, con consulta y administración separadas.
- Calendario visible en web, con distinción explícita entre estado local y disponibilidad real verificada por el monitor.
- Metadatos automáticos para cada salida tabular.
- Clasificación de cargas y manifiesto general.
- Control previo a publicación y estados por período.
- Calendario, contingencia y conservación del último resultado validado.
- Snapshot agregado para ejecución independiente del ETL.
- Arquitectura ampliable mediante funciones documentadas y salidas trazables.

## Documentos históricos

`docs/INFORME_FINAL_HITO3.md`, `docs/RESUMEN_ENTREGA_ENTIDAD.md` y el reporte ejecutivo 4T2025 se conservan como evidencia de los hitos en la fecha en que fueron entregados. Sus cifras de períodos/tests no se reescriben retroactivamente; la situación vigente se resume en este README, el CHANGELOG y `docs/VALIDACION_LOCAL_V3_2_1.md`.

## Limitaciones y reporte anterior

- Los indicadores se calculan a partir de microdatos públicos y no sustituyen procedimientos institucionales confirmados.

- El archivo `docs/Reporte_Ejecutivo_EPH_SDE_4T2025.pdf` se conserva como antecedente, pero no se ofrece en el dashboard: utiliza los nombres y denominadores anteriores y contiene una línea futura que ya no representa el alcance del Hito 3. No existe una fuente editable equivalente en el repositorio.

## Fuente

Encuesta Permanente de Hogares — Instituto Nacional de Estadística y Censos (INDEC), República Argentina: <https://www.indec.gob.ar>.
