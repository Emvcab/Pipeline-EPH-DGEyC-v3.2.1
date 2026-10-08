# Metodología de indicadores

## Universo y ponderación

El procesamiento filtra `AGLOMERADO = 18` y usa `PONDERA` para transformar observaciones de muestra en estimaciones poblacionales. No se imputan faltantes ni se convierten en cero.

## Indicadores principales

```text
tasa_actividad_oficial = PEA expandida / población total expandida × 100
tasa_empleo_oficial = ocupados expandidos / población total expandida × 100
tasa_desocupacion = desocupados expandidos / PEA expandida × 100
proporcion_inactiva_total = 100 - tasa_actividad_oficial
```

La proporción inactiva total es complementaria. No equivale a la tasa específica de inactividad de 10 años y más.

## Indicadores de 10 años y más

```text
tasa_actividad_10_mas = PEA expandida / población de 10 años y más expandida × 100
tasa_empleo_10_mas = ocupados expandidos / población de 10 años y más expandida × 100
tasa_inactividad_10_mas = inactivos expandidos / población de 10 años y más expandida × 100
```

## Informalidad e ingresos

Informalidad: ocupados ponderados con `EMPLEO = 2` / ocupados ponderados con `EMPLEO` en `{1, 2}` × 100. En `2023T1`, `2023T2` y `2023T3`, la variable necesaria para estimar informalidad no está disponible. Por ese motivo, el indicador se presenta como no disponible y no se realiza imputación ni se reemplazan faltantes por cero.

En el indicador agregado heredado del motor ETL 3.2.1 se consideran ocupados con `P21 > 0` y se conserva la formulación histórica del proyecto para no alterar la serie ya validada. En la nueva capa segmentada V3.3, los promedios de `P21` utilizan `PONDIIO`, el factor de expansión específico que INDEC publica para el ingreso de la ocupación principal. Todos los valores monetarios son pesos argentinos nominales y requieren deflactación para estudiar poder adquisitivo.

## Limitaciones

- El Aglomerado 18 reúne Santiago del Estero y La Banda sin desagregación pública entre ciudades.
- Los microdatos públicos no permiten evaluar encuestadores ni personal de carga.
- Los resultados calculados no sustituyen procedimientos institucionales confirmados.
- Machine Learning podrá evaluarse en una etapa posterior, una vez definido un problema institucional concreto, con datos suficientes y validación metodológica.

## Antecedente documental

`Reporte_Ejecutivo_EPH_SDE_4T2025.pdf` conserva cifras y textos producidos con la denominación anterior de tasas y una línea predictiva descartada para este hito. No existe en el repositorio una fuente editable equivalente. El archivo se conserva sin alteraciones y no se ofrece desde el dashboard.

## Análisis segmentado incorporado en V3.3

La capa de análisis segmentado no modifica las tasas agregadas históricas del motor ETL 3.2.1. Se genera como una salida adicional a partir de la base individual filtrada para el Aglomerado 18.

- **Sexo:** las tasas de actividad, empleo y desocupación se calculan para la población de **14 años y más**, siguiendo el criterio de tasas específicas utilizado en los informes de mercado de trabajo del INDEC. `CH04=1` corresponde a varón y `CH04=2` a mujer.
- **Edad:** se presentan grupos de 14 a 29 años, 30 a 64 años y 65 años y más. Las tasas se calculan dentro de cada grupo.
- **Nivel educativo:** se utiliza `NIVEL_ED` (o `NIVELED` como compatibilidad histórica) y se excluye `9=Ns/Nr` de las categorías publicadas.
- **Deciles de ingreso:** cuando la base incluye `ADECOCUR` y `PONDIIO`, se utiliza la escala decílica construida por INDEC para el ingreso de la ocupación principal dentro del aglomerado. No se reemplaza por deciles calculados localmente si la variable no está disponible.
- **Ingresos:** el promedio mostrado por segmento usa `P21 > 0` y `PONDIIO` entre ocupados, porque INDEC identifica `PONDIIO` como el ponderador corregido por no respuesta para el ingreso de la ocupación principal. Se expresa en pesos corrientes y no mide poder adquisitivo.

Estas estimaciones son descriptivas. Las diferencias entre grupos no se presentan como causalidad ni como significancia estadística sin un tratamiento específico de errores muestrales.
## Alcance inferencial de las comparaciones

Las diferencias entre períodos y grupos que presenta el portal son de carácter descriptivo.

La Encuesta Permanente de Hogares es una encuesta por muestreo. El pipeline utiliza los ponderadores correspondientes para producir estimaciones poblacionales, pero esta versión no estima errores estándar, intervalos de confianza ni pruebas de hipótesis asociadas al diseño muestral.

Por este motivo, una diferencia observada —por ejemplo, entre varones y mujeres o entre dos trimestres— puede describirse en puntos porcentuales, pero no debe interpretarse automáticamente como una diferencia estadísticamente significativa.

El sistema tampoco atribuye causalidad a las diferencias observadas.