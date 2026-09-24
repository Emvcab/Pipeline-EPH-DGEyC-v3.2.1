# Validación local — Pipeline EPH v3.2.1

**Fecha:** 24/09/2026  
**Entorno:** Windows + VS Code + entorno virtual Python  
**Alcance:** prueba funcional de la versión 3.2/3.2.1 antes de continuar con la evolución V4.

## Resultado general

La versión fue recorrida de punta a punta en entorno local. El ETL, el calendario, el monitor, la prevalidación y las siete secciones del portal funcionaron de acuerdo con el diseño. Durante la prueba se mantuvo la escritura administrativa final bloqueada para evitar modificaciones accidentales.

## Comprobaciones realizadas

1. **Histórico local:** `2026T1` fue descargado desde el repositorio EPH del INDEC, procesado para el Aglomerado 18, superó los controles críticos y quedó `VALIDADO` en `historico_SDE.csv`. El histórico local de prueba alcanzó 13 períodos (`2023T1` a `2026T1`).
2. **Calendario:** se verificó la corrección que separa estado local de fecha esperada. En v3.2.1 el calendario informa explícitamente que no consulta INDEC en línea.
3. **Monitor:** con último período local `2026T1`, el siguiente candidato fue `2026T2`. El monitor devolvió `NO_DISPONIBLE` porque la respuesta no era un ZIP EPH válido, aun cuando el servidor respondió HTTP 200.
4. **Administración:** la sesión administrativa se habilitó mediante variable de entorno. El monitor y la prevalidación quedaron disponibles, mientras la incorporación final permaneció bloqueada con `EPH_ADMIN_ENABLE_WRITES=0`.
5. **Prevalidación:** el reporte de `2026T1` quedó `LISTO_PARA_REVISION`, sin alertas operativas, con todos los controles críticos cumplidos y comparación contra `2025T4`.
6. **Portal:** se comprobaron Resumen ejecutivo, Evolución laboral, Ingresos, Calendario, Calidad y auditoría, Documentación y descargas y Administración. El resumen leyó correctamente `2026T1` desde los resultados locales.
7. **Pruebas automatizadas:** `python -m pytest tests -q` finaliza con **68 passed** en la versión consolidada 3.2.1.

## Distinción operativa clave

```text
CALENDARIO
  fecha esperada + estado local
  NO verifica INDEC en línea
        │
        ▼
MONITOR
  verifica si el ZIP de microdatos existe y es válido
        │
        ▼
PREVALIDACIÓN
  procesa en área separada y compara con el histórico
        │
        ▼
REVISIÓN HUMANA
        │
        ▼
PIPELINE NORMAL
  incorpora sólo si supera los controles críticos
```

## Estado del snapshot incluido en el repositorio

El paquete conserva los **datos agregados** de `data_snapshot/` hasta `2025T4` porque la publicación estadística del snapshot es una acción explícita y separada. En la revisión 3.2.1 sólo se refrescaron las guías de acompañamiento del snapshot para que el portal no muestre documentación obsoleta. La validación de `2026T1` se realizó sobre `results/` en el entorno local. Para llevar ese período al snapshot se debe ejecutar, después de la revisión institucional:

```bash
python src/pipeline.py --publicar-snapshot
```

Esta separación permite conservar un snapshot estable mientras se prueba una actualización nueva.
