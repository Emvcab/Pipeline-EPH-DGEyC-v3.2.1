# Matriz de validación metodológica de indicadores

## Objetivo

Documentar la correspondencia entre los indicadores calculados por el Pipeline EPH y los universos, variables, ponderadores y fórmulas utilizados para su construcción.

## Clasificación de indicadores

### 1. Indicadores principales

- **Tasa de actividad:** PEA expandida / población total expandida × 100.
- **Tasa de empleo:** ocupados expandidos / población total expandida × 100.
- **Tasa de desocupación:** desocupados expandidos / PEA expandida × 100.

Ponderador general: `PONDERA`.

### 2. Indicadores específicos comparables con publicaciones actuales del INDEC

- **Tasa de actividad 14 años y más:** PEA de 14 años y más / población de 14 años y más × 100.
- **Tasa de empleo 14 años y más:** ocupados de 14 años y más / población de 14 años y más × 100.
- **Tasa de desocupación 14 años y más:** desocupados de 14 años y más / PEA de 14 años y más × 100.

Ponderador general: `PONDERA`.

### 3. Indicadores complementarios de referencia histórica

- **Tasa de actividad 10 años y más.**
- **Tasa de empleo 10 años y más.**
- **Tasa de inactividad 10 años y más.**

Estos indicadores se conservan para trazabilidad histórica y análisis complementario. No deben presentarse como sustitutos de las tasas específicas de 14 años y más utilizadas como referencia en las publicaciones actuales.

## Ingresos

El ingreso de la ocupación principal (`P21`) requiere revisión específica del ponderador. En la V3.4 se verificará y documentará el uso de `PONDIIO` para las estimaciones ponderadas de ingresos y `ADECOCUR` para la escala decílica cuando dichas variables estén disponibles.

## Alcance inferencial

Las estimaciones y brechas que presenta el portal son descriptivas. La versión actual no calcula errores estándar, intervalos de confianza ni pruebas de hipótesis asociadas al diseño muestral; por lo tanto, las diferencias observadas no deben interpretarse automáticamente como estadísticamente significativas ni causales.

## Validación empírica contra publicaciones oficiales del INDEC

Las tasas principales calculadas por el Pipeline EPH fueron contrastadas con los valores
publicados oficialmente por el INDEC para el Aglomerado 18 — Santiago del Estero–La Banda.

Se verificaron nueve trimestres consecutivos:

- 2024T1
- 2024T2
- 2024T3
- 2024T4
- 2025T1
- 2025T2
- 2025T3
- 2025T4
- 2026T1

Para cada período se compararon:

- tasa de actividad;
- tasa de empleo;
- tasa de desocupación.

Esto representa 27 comparaciones independientes.

### Resultado

**27 de 27 comparaciones concordaron con los valores publicados por INDEC al nivel de
redondeo de una cifra decimal utilizado en sus informes técnicos.**

Por lo tanto, las tasas principales del pipeline quedan clasificadas como:

| Indicador | Estado metodológico |
|---|---|
| Tasa de actividad | VALIDADA Y REPRODUCIDA |
| Tasa de empleo | VALIDADA Y REPRODUCIDA |
| Tasa de desocupación | VALIDADA Y REPRODUCIDA |
| Tasas específicas 14 años y más | IMPLEMENTADAS Y TESTEADAS |
| Tasas 10 años y más | COMPLEMENTARIAS DE REFERENCIA HISTÓRICA |
| Ingreso P21 con PONDIIO | IMPLEMENTADO Y TESTEADO |
| Deciles mediante ADECOCUR | IMPLEMENTACIÓN CONCORDANTE |
| Informalidad laboral | PENDIENTE DE CONTRASTE EXTERNO |

La evidencia detallada se conserva en:

`docs/validacion_metodologica_indec.csv`

La comparación puede regenerarse ejecutando:

`python scripts/validar_contra_indec.py`

La reproducción de los valores publicados no implica certificación formal por parte del
INDEC ni de la DGEyC. Tampoco constituye una prueba de significancia estadística.