# Historial de cambios

## 3.2.1 — 2026-09-24

### Corregido — calendario y ejecución por lote

- Se incorpora `estado_registrado()` para distinguir un estado realmente persistido en `estado_periodos.csv` de una estimación basada únicamente en la fecha esperada.
- `--calendario` aclara que **no consulta INDEC en línea** y diferencia estados locales, `SIN PROCESAR` y `FUTURO`.
- `SIN PROCESAR` ya no implica que el ZIP esté publicado: indica que la fecha esperada fue alcanzada y remite al monitor para verificar disponibilidad real.
- `procesar_lote()` omite períodos futuros que nunca fueron registrados, evitando intentos innecesarios de descarga con `--anio` o `--todos`.
- Se conserva el monitor como única comprobación remota de disponibilidad del ZIP de microdatos.
- Se actualizan README, guías, manual técnico, arquitectura, portal y registro HTML para reflejar esta separación conceptual.
- Se agrega `docs/VALIDACION_LOCAL_V3_2_1.md` con la prueba manual realizada en VS Code.
- 3 pruebas nuevas específicas del ajuste; suite total: **68 tests**.
- `PIPELINE_VERSION` pasa a `3.2.1`.

---

## 3.2.0 — 2026-09-22

### Portal para usuarios no técnicos

- El dashboard pasa a ser un portal de siete secciones, incorporando **Calendario** y **Administración**.
- El calendario web reutiliza `fecha_publicacion_esperada()` y `estado_trimestre()`; no duplica reglas del pipeline.
- Nueva capa `src/portal_admin.py` para listar prevalidaciones y ejecutar una incorporación asistida con confirmación explícita.
- Área administrativa protegida por clave configurable fuera del repositorio.
- Publicación desde la UI deshabilitada por defecto; requiere `admin_enable_writes=true` / `EPH_ADMIN_ENABLE_WRITES=1`.
- El operador puede consultar INDEC, prevalidar, revisar controles y alertas, y luego incorporar el período sin usar la terminal.
- La publicación final vuelve a ejecutar el pipeline completo y conserva sus controles transaccionales y rollback.
- Nueva guía `docs/PORTAL_ADMINISTRACION.md` y plantilla `.streamlit/secrets.toml.example`.
- 6 pruebas nuevas del portal; suite total: **65 tests**.
- `PIPELINE_VERSION` pasa a `3.2.0`.

Todos los cambios relevantes del proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el versionado [Semantic Versioning](https://semver.org/lang/es/).


## 3.1.0 — 2026-09-22

### Agregado
- **Monitor de nuevas publicaciones EPH** (`src/monitor_actualizaciones.py`) que consulta los ZIP oficiales esperables según el calendario del pipeline.
- **Prevalidación asistida** de un trimestre nuevo sin modificar el histórico ni el snapshot vigentes.
- Comparación automática con el período anterior y alertas orientativas por variaciones amplias de tasas, tamaño muestral y población expandida.
- Reportes JSON y Markdown de prevalidación con metadatos y manifiesto de auditoría.
- Workflow semanal y ejecución manual mediante GitHub Actions para consultar novedades sin publicar datos.
- 9 pruebas automatizadas del monitor; suite total: **59 tests**.

### Cambiado
- `PIPELINE_VERSION` pasa a `3.1.0`.
- `ANIOS` incorpora 2026 para permitir el procesamiento explícito de los nuevos trimestres.

### Seguridad operativa
- El monitor **no publica automáticamente**. La promoción al histórico y al snapshot continúa requiriendo ejecución y revisión humana explícitas.
- Los umbrales de alerta se documentan como controles operativos, no como pruebas de significancia estadística.

---

## 3.0.0 — 2026-07-13

- Separación entre tasas principales sobre población total y tasas específicas de 10 años y más.
- Migración explícita de nombres históricos sin cambio silencioso de denominador.
- Metadatos completos, manifiesto general y clasificación de cargas.
- Estados por período, controles críticos y promoción transaccional.
- Snapshot agregado para Streamlit, con conservación del anterior ante fallas.
- Dashboard institucional en cinco secciones, sin afirmaciones predictivas.
- Documentación metodológica y pruebas ampliadas.

---

## [2.2.0] — 2026-06-30

### Agregado
- **Calendario de publicaciones INDEC** — flag `--calendario` muestra cronograma esperado vs estado local (procesado / esperando / futuro); la disponibilidad web se verifica por separado desde v3.1
- **Validación automática de esquema** — el pipeline verifica que las columnas esperadas estén presentes antes de procesar. Si el INDEC cambia algo crítico, el pipeline avisa antes de generar resultados
- Archivo `validacion_esquema_<periodo>.json` por trimestre con resultado de la validación
- Constantes `ESQUEMA_OBLIGATORIO_INDIVIDUAL`, `ESQUEMA_OBLIGATORIO_HOGAR`, `ESQUEMA_OPCIONAL_INDIVIDUAL`
- 7 tests nuevos (total: 31 tests pasando)

### Motivación
Implementación de sugerencia recibida en devolución institucional de la DGEyC:
> "Debería incluirse un calendario, ya que el pipeline se activa con cada nueva
> publicación y debería considerarse la contingencia, auditoría y disponibilización
> del nuevo reporte, o fallas en la extracción."

---
---

## [2.1.0] — 2026-06-30

### Agregado
- **Sistema de metadatos automáticos** — cada archivo CSV generado por el pipeline ahora se acompaña de un archivo `.meta.json` con información completa para su uso (versión del pipeline, fecha de generación, fuente, esquema de columnas con tipos y descripciones, hash de integridad SHA-256)
- Función `generar_metadatos()` con diccionario embebido de las ~30 columnas del histórico
- Función `calcular_hash()` para verificación de integridad
- Constante `PIPELINE_VERSION` para trazabilidad de versiones
- 7 tests nuevos para el sistema de metadatos (total: 24 tests)

### Cambiado
- `guardar_trimestre()` ahora genera 4 CSV + 4 JSON por trimestre procesado
- Docstring del pipeline actualizado con la nueva estructura de salidas

### Motivación
Implementación de sugerencia recibida en devolución institucional de la DGEyC:
> "Los csv o xlsx que se exporten del pipeline o las Loads deben estar acompañadas
> de metadatos para ser usables."

---


## [2.0.0] — 2026-06-26

### Cambiado
- **Refactorización profesional completa del pipeline**, reduciendo de 1.434 a 411 líneas (-71%) sin pérdida de funcionalidad técnica
- Adopción de estándares profesionales: `type hints` completos, `docstrings`, logging estructurado, manejo explícito de errores
- Centralización de constantes en sección de configuración al inicio del archivo
- Reemplazo de `os.path` por `pathlib.Path` para manejo de rutas
- Reorganización del proyecto en estructura de carpetas profesional (`src/`, `docs/`, `tests/`, `data/`, `results/`, `logs/`)

### Agregado
- `README.md` con instrucciones de instalación y uso
- `requirements.txt` con dependencias pinned
- `.gitignore` profesional
- `CHANGELOG.md` (este archivo)
- `LICENSE`
- Suite de tests básicos en `tests/`
- Documentación de arquitectura en `docs/ARQUITECTURA.md`

### Eliminado
- Funciones de diagnóstico geográfico (información movida a documentación)
- Inventario de columnas por trimestre (uso único, no aporta valor continuo)
- Variables descriptivas decodificadas innecesarias para cálculos
- Múltiples archivos redundantes de salida
- Prints duplicados con logs

---

## [1.5.0] — 2026-06-07

### Agregado
- Lectura robusta probando 4 combinaciones de separador/codificación
- Cálculo de ingreso promedio ponderado
- Reporte de calidad de datos por trimestre
- Base unida individuo-hogar por `CODUSU + NRO_HOGAR`
- Tasa de inactividad
- Sistema de logs con timestamp en carpeta `logs/`
- Flag `--forzar` para re-descargar ZIPs existentes

### Cambiado
- Migración a `pathlib.Path` en lugar de strings para rutas
- Logging básico reemplaza algunos prints

---

## [1.0.0] — 2026-05-18

### Agregado
- Versión inicial del pipeline (Hito 1)
- Descarga automatizada desde el FTP del INDEC
- Filtrado por aglomerado 18 (Santiago del Estero — La Banda)
- Cálculo de tasas: actividad, empleo, desocupación, informalidad
- Cálculo de ingreso promedio simple y mediana
- Tres modos de ejecución: trimestre, año completo, todos los trimestres
- Histórico acumulado en `historico_SDE.csv`
