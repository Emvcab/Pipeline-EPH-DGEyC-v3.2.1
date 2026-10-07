# Plan V3.3 — respuesta a devolución de la DPE

## Objetivo

Evolucionar el producto validado en V3.2.1 sin reescribir el motor ETL, incorporando mejoras de visualización, interactividad, profundidad analítica, contexto y exportación.

## Incremento 1 — V3.3.0 · implementado

- Plotly en las series principales.
- Ejes Y ajustados al rango visible.
- Selección de período de referencia.
- Comparación entre dos trimestres.
- Rango temporal Desde/Hasta.
- 74 tests aprobados.

Este incremento mejora la exploración de los indicadores ya validados. No recalcula las fórmulas del ETL ni modifica el histórico.

## Incremento 2 — profundidad analítica

Objetivo: pasar de indicadores agregados a evidencia segmentada.

Análisis propuestos sobre microdatos individuales, respetando PONDERA y controles de calidad:

- tasas de actividad, empleo y desocupación por sexo;
- grupos de edad definidos metodológicamente;
- nivel educativo;
- informalidad por segmentos cuando `EMPLEO` esté disponible;
- distribución de ingresos y deciles;
- brechas absolutas y relativas entre grupos.

Antes de incorporar estas salidas al histórico se deben definir denominadores, categorías y reglas de calidad en documentación metodológica y tests.

## Incremento 3 — contexto territorial

La EPH pública del proyecto representa el Aglomerado 18 y no debe presentarse como total provincial. Para comparaciones provinciales, regionales o nacionales se debe identificar una fuente oficial compatible de INDEC y documentar diferencias de universo, cobertura y periodicidad.

No se incorporará una comparación territorial hasta verificar que sea metodológicamente comparable.

## Incremento 4 — reporte estático

Generar un PDF por período con:

- indicadores principales;
- comparaciones temporales;
- gráficos;
- análisis segmentado;
- notas de calidad;
- contexto metodológico y fuente.

El PDF será un producto de salida del portal; no reemplazará el histórico ni las validaciones del pipeline.

## Incremento 5 — preguntas de negocio

Antes de ampliar indicadores operativos, relevar con usuarios/productores de la EPH qué preguntas necesitan responder de manera recurrente. Las nuevas vistas deberán vincularse con una pregunta institucional concreta y no agregarse únicamente por disponibilidad técnica.

## Principio de diseño

La V3.3 amplía la capacidad analítica y de consulta, pero mantiene una separación clara entre:

`microdatos → cálculo validado → histórico → visualización/interpretación`

La interfaz puede cambiar filtros y períodos de análisis; no debe cambiar silenciosamente definiciones metodológicas del ETL.
