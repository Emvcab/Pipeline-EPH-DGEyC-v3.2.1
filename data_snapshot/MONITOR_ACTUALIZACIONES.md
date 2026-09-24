# Monitor de actualización asistida EPH

## Objetivo

Este módulo complementa el ETL principal con una etapa previa de vigilancia y revisión. Su propósito es detectar si el INDEC publicó un trimestre EPH que todavía no forma parte del histórico local del Aglomerado 18 y, opcionalmente, prevalidarlo antes de incorporarlo.

La decisión de diseño principal es deliberada: **detectar y prevalidar no equivale a publicar**. El histórico y el snapshot sólo se modifican mediante los comandos existentes del pipeline luego de una revisión humana.

### Diferencia entre calendario y monitor

El calendario (`python src/pipeline.py --calendario`) **no consulta INDEC en línea**. Sólo combina fechas esperadas con estados locales. Si aparece `SIN PROCESAR`, significa que la fecha esperada fue alcanzada, no que el ZIP exista.

El monitor es el componente que responde la pregunta **“¿el microdato EPH está realmente disponible como ZIP válido?”**. Puede recibir HTTP 200 y aun así devolver `NO_DISPONIBLE` si el contenido no es un ZIP EPH válido; esta validación evita procesar páginas HTML u otras respuestas del servidor como si fueran microdatos.

## Flujo operativo

```text
Histórico local
      │
      ▼
último período disponible
      │
      ▼
calendario esperado INDEC
      │
      ▼
consulta de ZIP oficial
      │
 ┌────┼─────────────┐
 │    │             │
 ▼    ▼             ▼
ERROR NO DISP.   DISPONIBLE
                   │
                   ▼
             prevalidación
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
     esquema    cálculos   comparación
        │          │          │
        └──────────┼──────────┘
                   ▼
           reporte EN_REVISION
                   │
             revisión humana
                   │
                   ▼
              ETL normal
```

## Comandos

Consulta sin procesar ni publicar:

```bash
python src/monitor_actualizaciones.py
```

Consulta y prevalidación del primer trimestre nuevo disponible:

```bash
python src/monitor_actualizaciones.py --prevalidar
```

Prevalidación explícita de un período:

```bash
python src/monitor_actualizaciones.py --anio 2026 --trimestre 1 --prevalidar
```

Forzar una nueva descarga durante la prevalidación:

```bash
python src/monitor_actualizaciones.py --anio 2026 --trimestre 1 --prevalidar --forzar
```

## Qué valida

La prevalidación reutiliza componentes del ETL principal para comprobar:

- descarga y formato ZIP;
- identificación de bases Individual y Hogar;
- esquema de variables obligatorias y opcionales;
- presencia del Aglomerado 18;
- cálculo de indicadores con `PONDERA`;
- controles críticos de rango, población, duplicados, muestra e informalidad;
- comparación con el último período histórico.

Los reportes se escriben en `results/monitor_actualizaciones/` y se acompañan de metadatos y manifiesto de auditoría.

## Alertas de variación

El monitor marca para revisión cambios amplios respecto del período anterior. Los umbrales iniciales son configurables:

- tasas: 5 puntos porcentuales;
- tamaño de muestra: 25%;
- población expandida: 20%.

Estos valores son **umbrales operativos de vigilancia**, no pruebas de hipótesis ni criterios de significancia estadística. Una alerta no significa que el dato sea incorrecto; sólo prioriza la revisión humana.

La variación del ingreso promedio ponderado se informa, pero no genera una alerta automática por defecto porque los ingresos del histórico son nominales.

## Estados de la consulta

- `DISPONIBLE`: el recurso respondió como ZIP válido.
- `NO_DISPONIBLE`: no se obtuvo un ZIP EPH válido. Puede ocurrir incluso con HTTP 200 si la respuesta no es el archivo esperado.
- `ERROR`: no fue posible determinar disponibilidad por un problema de red, dependencia o consulta.

Esta distinción evita interpretar una caída del sitio del INDEC como ausencia de publicación.

## Incorporación luego de revisar

Si el reporte es satisfactorio, la incorporación se mantiene separada y explícita:

```bash
python src/pipeline.py --anio 2026 --trimestre 1
```

Luego de verificar que el período quedó validado:

```bash
python src/pipeline.py --publicar-snapshot
```

## Automatización opcional

`.github/workflows/monitor-eph.yml` ejecuta la consulta una vez por semana y también permite iniciarla manualmente desde GitHub Actions. El workflow sólo monitorea y genera un artefacto de auditoría; no ejecuta la prevalidación ni publica un trimestre.

## Alcance institucional

El módulo está pensado como apoyo operativo para una Dirección de Estadística: automatiza tareas repetitivas y señala situaciones que merecen revisión, pero conserva la responsabilidad metodológica y de publicación en las personas responsables del proceso.
