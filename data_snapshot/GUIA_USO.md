# Guía de uso

## Procesar

Desde la raíz del repositorio:

```bash
python src/pipeline.py --anio 2025 --trimestre 4
python src/pipeline.py --calendario
```

Revisar `results/estado_periodos.csv`, `validacion_publicacion_<periodo>.json`, los CSV y sus `.meta.json`. Un período `FALLIDO` no reemplaza el histórico vigente.

### Qué informa el calendario

`python src/pipeline.py --calendario` **no consulta INDEC en línea**. Muestra la fecha esperada y el estado local:

- si el período tiene una entrada en `estado_periodos.csv`, muestra ese estado real (`VALIDADO`, `FALLIDO`, etc.);
- `SIN PROCESAR` significa que la fecha esperada ya llegó pero todavía no existe una corrida local registrada;
- `FUTURO` significa que aún no corresponde esperar la publicación.

Antes de procesar un `SIN PROCESAR`, usar `python src/monitor_actualizaciones.py` para confirmar que el ZIP de microdatos esté realmente disponible.

Desde 3.2.1, `--todos` y los lotes por año omiten automáticamente períodos futuros no registrados.

## Preparar el snapshot

Sólo después de revisar un período `VALIDADO`:

```bash
python src/pipeline.py --publicar-snapshot
```

El comando excluye microdatos y no despliega la aplicación en la nube.

## Abrir el dashboard

```bash
python -m streamlit run notebooks/app.py
```

Si `results/` no tiene un último período validado, la aplicación usa `data_snapshot/` y muestra una explicación.

## Ante una falla

1. Leer el mensaje de `estado_periodos.csv`.
2. Revisar el último archivo de `logs/`.
3. Consultar la validación de esquema.
4. Corregir sin borrar el histórico ni el snapshot válidos.
5. Reprocesar y comprobar estado `VALIDADO`.

Los indicadores operativos de campo requieren bases internas. No deben inferirse de los microdatos públicos.

## Validación final

El snapshot de referencia incluido cubre **12 períodos**, desde `2023T1` hasta `2025T4`. En la prueba local de 3.2.1 se procesó y validó `2026T1`, por lo que el histórico local probado alcanzó **13 períodos**.

La implementación 3.2.1 fue verificada con `python -m pytest tests -q`: **68 tests aprobados**. La prueba manual del portal se documenta en `VALIDACION_LOCAL_V3_2_1.md`.


## Monitor de nuevas publicaciones (v3.1)

Antes de ejecutar una actualización del histórico puede consultarse INDEC con:

```bash
python src/monitor_actualizaciones.py
```

El monitor toma como referencia el último período de `results/historico_SDE.csv` y, si no existe, usa `data_snapshot/historico_SDE.csv`. Sólo consulta períodos cuyo mes esperado de publicación ya llegó.

Para descargar y prevalidar el primer período nuevo detectado, sin incorporarlo al histórico:

```bash
python src/monitor_actualizaciones.py --prevalidar
```

Los reportes quedan en `results/monitor_actualizaciones/`. Si la prevalidación es correcta, la persona responsable revisa el reporte y recién entonces ejecuta el pipeline normal para el período. Las alertas de variación son orientativas y no constituyen pruebas estadísticas.


## Portal web de administración

Ejecutar:

```bash
python -m streamlit run notebooks/app.py
```

La pestaña **Calendario** muestra fechas esperadas y estados locales; no confirma por sí sola la disponibilidad del ZIP en INDEC. El botón **Consultar INDEC ahora** del área administrativa realiza esa verificación. La pestaña **Administración** permite consultar INDEC y prevalidar un trimestre. La incorporación final está bloqueada hasta configurar credenciales y habilitar escrituras. Ver `PORTAL_ADMINISTRACION.md`.
