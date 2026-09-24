"""
Monitor de actualizaciones EPH — INDEC
======================================
Complemento del Pipeline EPH de la DGEyC Santiago del Estero.

Detecta nuevas publicaciones de microdatos trimestrales del INDEC y permite
prevalidarlas sin incorporarlas automáticamente al histórico oficial del
proyecto. La publicación sigue siendo una decisión humana explícita.

Uso básico::

    python src/monitor_actualizaciones.py
    python src/monitor_actualizaciones.py --prevalidar
    python src/monitor_actualizaciones.py --anio 2026 --trimestre 1 --prevalidar

Las alertas de variación son controles operativos orientativos. No representan
pruebas de significancia estadística ni reemplazan la revisión metodológica.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

import pipeline as core

try:
    import requests
except ImportError:  # pragma: no cover - requirements incluye requests
    requests = None  # type: ignore[assignment]


URL_BASES_INDEC = "https://www.indec.gob.ar/Institucional/Indec/BasesDeDatos"
DIR_MONITOR = core.DIR_RESULTADOS / "monitor_actualizaciones"

# Umbrales de vigilancia operativa. Son deliberadamente simples y configurables.
# Una alerta pide revisión; nunca invalida por sí misma un dato oficial.
UMBRAL_TASA_PP = 5.0
UMBRAL_MUESTRA_PCT = 25.0
UMBRAL_POBLACION_PCT = 20.0

MESES_NUMERO = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5,
    "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9,
    "Octubre": 10, "Noviembre": 11, "Diciembre": 12,
}

TASAS_A_VIGILAR = [
    "tasa_actividad_oficial",
    "tasa_empleo_oficial",
    "tasa_desocupacion",
    "proporcion_inactiva_total",
    "tasa_actividad_10_mas",
    "tasa_empleo_10_mas",
    "tasa_inactividad_10_mas",
    "tasa_informalidad",
]


@dataclass(frozen=True, order=True)
class Periodo:
    anio: int
    trimestre: int

    @property
    def codigo(self) -> str:
        return f"{self.anio}T{self.trimestre}"


def construir_url_zip(periodo: Periodo) -> str:
    """Construye la URL oficial TXT usando el patrón vigente del INDEC."""
    nombre = f"EPH_usu_{periodo.trimestre}_Trim_{periodo.anio}_txt.zip"
    return core.URL_BASE + nombre


def periodo_siguiente(periodo: Periodo) -> Periodo:
    """Devuelve el trimestre cronológicamente siguiente."""
    if periodo.trimestre == 4:
        return Periodo(periodo.anio + 1, 1)
    return Periodo(periodo.anio, periodo.trimestre + 1)


def _periodo_desde_codigo(valor: object) -> Optional[Periodo]:
    normalizado = core.normalizar_periodo(valor)
    if normalizado is None:
        return None
    return Periodo(int(normalizado[:4]), int(normalizado[-1]))


def ultimo_periodo_local(
    historico_resultados: Path = core.DIR_RESULTADOS / "historico_SDE.csv",
    historico_snapshot: Path = core.DIR_SNAPSHOT / "historico_SDE.csv",
) -> Periodo:
    """Obtiene el último período local, priorizando results/ y luego snapshot."""
    ruta = historico_resultados if historico_resultados.exists() else historico_snapshot
    if not ruta.exists():
        raise FileNotFoundError(
            "No se encontró historico_SDE.csv en results/ ni en data_snapshot/."
        )
    historico = core.migrar_historico(pd.read_csv(ruta))
    periodos = [_periodo_desde_codigo(v) for v in historico.get("periodo", [])]
    validos = [p for p in periodos if p is not None]
    if not validos:
        raise ValueError(f"{ruta} no contiene períodos válidos.")
    return max(validos)


def periodo_deberia_estar_publicado(
    periodo: Periodo, fecha_referencia: Optional[datetime] = None
) -> bool:
    """Indica si, según el calendario operativo del proyecto, ya toca consultar."""
    fecha = fecha_referencia or datetime.now()
    mes, anio_publicacion = core.fecha_publicacion_esperada(periodo.anio, periodo.trimestre)
    return (anio_publicacion, MESES_NUMERO[mes]) <= (fecha.year, fecha.month)


def periodos_candidatos(
    ultimo: Periodo,
    fecha_referencia: Optional[datetime] = None,
    max_periodos: int = 8,
) -> list[Periodo]:
    """Genera períodos posteriores cuyo mes esperado de publicación ya llegó."""
    if max_periodos < 1:
        return []
    candidatos: list[Periodo] = []
    actual = periodo_siguiente(ultimo)
    while len(candidatos) < max_periodos and periodo_deberia_estar_publicado(
        actual, fecha_referencia
    ):
        candidatos.append(actual)
        actual = periodo_siguiente(actual)
    return candidatos


def consultar_zip_remoto(
    periodo: Periodo,
    session: Any = None,
    timeout: int = 20,
) -> dict[str, Any]:
    """Comprueba disponibilidad del ZIP sin descargarlo completo.

    Se solicita sólo el comienzo del archivo mediante ``Range`` y se verifica
    que la respuesta tenga firma ZIP (PK) o content-type compatible.
    """
    url = construir_url_zip(periodo)
    if requests is None and session is None:
        return {
            "periodo": periodo.codigo,
            "url": url,
            "disponible": False,
            "estado_consulta": "ERROR",
            "estado_http": None,
            "detalle": "La dependencia requests no está instalada.",
        }

    cliente = session or requests
    respuesta = None
    try:
        respuesta = cliente.get(
            url,
            timeout=timeout,
            stream=True,
            allow_redirects=True,
            headers={"Range": "bytes=0-7", "User-Agent": "Pipeline-EPH-DGEyC-monitor/3.1"},
        )
        estado = int(respuesta.status_code)
        tipo = str(respuesta.headers.get("content-type", "")).lower()
        firma = b""
        if estado in {200, 206}:
            for bloque in respuesta.iter_content(chunk_size=8):
                if bloque:
                    firma = bloque[:8]
                    break
        es_zip = firma.startswith(b"PK") or "zip" in tipo
        disponible = estado in {200, 206} and es_zip
        detalle = (
            "ZIP oficial disponible."
            if disponible
            else f"No disponible como ZIP válido (HTTP {estado})."
        )
        return {
            "periodo": periodo.codigo,
            "url": url,
            "disponible": disponible,
            "estado_consulta": "DISPONIBLE" if disponible else "NO_DISPONIBLE",
            "estado_http": estado,
            "content_type": tipo or None,
            "detalle": detalle,
        }
    except Exception as error:  # red externa: se reporta sin romper el monitor
        return {
            "periodo": periodo.codigo,
            "url": url,
            "disponible": False,
            "estado_consulta": "ERROR",
            "estado_http": None,
            "detalle": f"No se pudo consultar INDEC: {error}",
        }
    finally:
        if respuesta is not None:
            try:
                respuesta.close()
            except Exception:
                pass


def detectar_nuevas_publicaciones(
    historico_resultados: Path = core.DIR_RESULTADOS / "historico_SDE.csv",
    historico_snapshot: Path = core.DIR_SNAPSHOT / "historico_SDE.csv",
    fecha_referencia: Optional[datetime] = None,
    session: Any = None,
    max_periodos: int = 8,
) -> dict[str, Any]:
    """Consulta los períodos posteriores al último histórico y devuelve novedades."""
    ultimo = ultimo_periodo_local(historico_resultados, historico_snapshot)
    candidatos = periodos_candidatos(ultimo, fecha_referencia, max_periodos)
    consultas = [consultar_zip_remoto(p, session=session) for p in candidatos]
    nuevas = [c for c in consultas if c["disponible"]]
    errores = [c for c in consultas if c.get("estado_consulta") == "ERROR"]
    return {
        "fecha_consulta": core.ahora_iso(),
        "fuente": "INDEC - Bases de datos EPH",
        "pagina_bases": URL_BASES_INDEC,
        "ultimo_periodo_local": ultimo.codigo,
        "periodos_consultados": consultas,
        "nuevas_publicaciones": nuevas,
        "hay_novedades": bool(nuevas),
        "errores_consulta": errores,
        "estado_monitor": "ERROR" if errores else ("NOVEDAD" if nuevas else "SIN_NOVEDADES"),
    }


def _variacion_porcentual(actual: Any, anterior: Any) -> Optional[float]:
    try:
        a = float(actual)
        b = float(anterior)
    except (TypeError, ValueError):
        return None
    if pd.isna(a) or pd.isna(b) or b == 0:
        return None
    return round((a - b) / abs(b) * 100, 2)


def comparar_con_historico(
    indicadores: dict[str, Any],
    historico: pd.DataFrame,
    umbral_tasa_pp: float = UMBRAL_TASA_PP,
    umbral_muestra_pct: float = UMBRAL_MUESTRA_PCT,
    umbral_poblacion_pct: float = UMBRAL_POBLACION_PCT,
) -> dict[str, Any]:
    """Compara con el trimestre anterior y genera alertas orientativas."""
    historico = core.migrar_historico(historico.copy())
    historico = historico[historico["periodo"] != indicadores["periodo"]]
    if historico.empty:
        return {"periodo_anterior": None, "variaciones": {}, "alertas": []}

    anterior = historico.sort_values(["anio", "trimestre"]).iloc[-1]
    variaciones: dict[str, Any] = {}
    alertas: list[dict[str, Any]] = []

    for columna in TASAS_A_VIGILAR:
        actual = indicadores.get(columna)
        previo = anterior.get(columna)
        if actual is None or previo is None or pd.isna(actual) or pd.isna(previo):
            continue
        delta = round(float(actual) - float(previo), 2)
        variaciones[columna] = {
            "anterior": float(previo), "actual": float(actual), "delta_pp": delta
        }
        if abs(delta) >= umbral_tasa_pp:
            alertas.append({
                "tipo": "variacion_tasa",
                "variable": columna,
                "nivel": "REVISAR",
                "detalle": f"Variación de {delta:+.2f} puntos porcentuales respecto del período anterior.",
            })

    for columna, umbral in [
        ("n_personas_muestra", umbral_muestra_pct),
        ("n_hogares_muestra", umbral_muestra_pct),
        ("poblacion_expandida_total", umbral_poblacion_pct),
    ]:
        variacion = _variacion_porcentual(indicadores.get(columna), anterior.get(columna))
        if variacion is None:
            continue
        variaciones[columna] = {
            "anterior": float(anterior[columna]),
            "actual": float(indicadores[columna]),
            "variacion_pct": variacion,
        }
        if abs(variacion) >= umbral:
            alertas.append({
                "tipo": "variacion_estructura",
                "variable": columna,
                "nivel": "REVISAR",
                "detalle": f"Variación de {variacion:+.2f}% respecto del período anterior.",
            })

    ingreso = "ingreso_promedio_ponderado_observado"
    var_ingreso = _variacion_porcentual(indicadores.get(ingreso), anterior.get(ingreso))
    if var_ingreso is not None:
        variaciones[ingreso] = {
            "anterior": float(anterior[ingreso]),
            "actual": float(indicadores[ingreso]),
            "variacion_pct": var_ingreso,
            "nota": "Variación nominal; no se interpreta como cambio real del poder adquisitivo.",
        }

    return {
        "periodo_anterior": str(anterior["periodo"]),
        "variaciones": variaciones,
        "alertas": alertas,
        "criterio_alertas": {
            "tasas_pp": umbral_tasa_pp,
            "muestra_pct": umbral_muestra_pct,
            "poblacion_pct": umbral_poblacion_pct,
            "nota": "Umbrales operativos de revisión; no son pruebas de significancia estadística.",
        },
    }


def _cargar_historico_para_revision(
    historico_resultados: Path,
    historico_snapshot: Path,
) -> pd.DataFrame:
    ruta = historico_resultados if historico_resultados.exists() else historico_snapshot
    if not ruta.exists():
        raise FileNotFoundError("No existe histórico local para comparar la prevalidación.")
    return core.migrar_historico(pd.read_csv(ruta))


def _render_markdown(reporte: dict[str, Any]) -> str:
    periodo = reporte["periodo"]
    lineas = [
        f"# Prevalidación EPH — {periodo}",
        "",
        f"**Estado:** {reporte['estado_prevalidacion']}",
        f"**Fecha:** {reporte['fecha_prevalidacion']}",
        f"**Fuente:** INDEC — {reporte['url_origen']}",
        "",
        "> Este reporte no publica el período. La incorporación al histórico requiere revisión humana y ejecución explícita del pipeline.",
        "",
        "## Controles críticos",
        "",
    ]
    for control in reporte["validacion_critica"]["controles"]:
        simbolo = "OK" if control["cumple"] else "REVISAR"
        lineas.append(f"- **{simbolo}** · `{control['control']}` — {control['detalle']}")

    lineas.extend(["", "## Comparación con el período anterior", ""])
    comparacion = reporte["comparacion_historica"]
    if comparacion["periodo_anterior"] is None:
        lineas.append("No hay un período anterior disponible para comparar.")
    else:
        lineas.append(f"Período de referencia: **{comparacion['periodo_anterior']}**.")
        lineas.append("")
        for variable, datos in comparacion["variaciones"].items():
            if "delta_pp" in datos:
                lineas.append(
                    f"- `{variable}`: {datos['anterior']:.2f} → {datos['actual']:.2f} "
                    f"({datos['delta_pp']:+.2f} pp)"
                )
            elif "variacion_pct" in datos:
                lineas.append(
                    f"- `{variable}`: {datos['anterior']:.2f} → {datos['actual']:.2f} "
                    f"({datos['variacion_pct']:+.2f}%)"
                )

    lineas.extend(["", "## Alertas orientativas", ""])
    alertas = comparacion["alertas"]
    if not alertas:
        lineas.append("No se detectaron variaciones que superen los umbrales operativos configurados.")
    else:
        for alerta in alertas:
            lineas.append(f"- **{alerta['nivel']}** · `{alerta['variable']}` — {alerta['detalle']}")

    lineas.extend([
        "",
        "## Próximo paso",
        "",
        "Si la revisión metodológica y operativa es satisfactoria:",
        "",
        f"```bash\npython src/pipeline.py --anio {reporte['anio']} --trimestre {reporte['trimestre']}\n```",
        "",
        "Luego, sólo tras validar el resultado:",
        "",
        "```bash\npython src/pipeline.py --publicar-snapshot\n```",
        "",
    ])
    return "\n".join(lineas)


def prevalidar_periodo(
    periodo: Periodo,
    forzar_descarga: bool = False,
    directorio_reportes: Path = DIR_MONITOR,
    historico_resultados: Path = core.DIR_RESULTADOS / "historico_SDE.csv",
    historico_snapshot: Path = core.DIR_SNAPSHOT / "historico_SDE.csv",
) -> dict[str, Any]:
    """Descarga y procesa en modo revisión, sin promover el período al histórico."""
    directorio_reportes.mkdir(parents=True, exist_ok=True)
    ruta_zip = core.descargar_zip(periodo.anio, periodo.trimestre, forzar_descarga)
    if ruta_zip is None:
        raise RuntimeError(f"No se pudo descargar {periodo.codigo} desde INDEC.")
    ruta_ind, ruta_hog = core.extraer_zip(ruta_zip, periodo.anio, periodo.trimestre)
    if ruta_ind is None or ruta_hog is None:
        raise RuntimeError("No se identificaron las bases individual y hogar.")

    sde_ind, sde_hog = core.cargar_y_filtrar(
        ruta_ind, ruta_hog, periodo.anio, periodo.trimestre, directorio_reportes
    )
    indicadores = core.calcular_indicadores(sde_ind, sde_hog, periodo.anio, periodo.trimestre)
    historico = _cargar_historico_para_revision(historico_resultados, historico_snapshot)
    historico_propuesto = pd.concat(
        [historico, pd.DataFrame([indicadores])], ignore_index=True, sort=False
    )
    validacion = core.validar_publicacion(
        indicadores, historico_propuesto, sde_ind, sde_hog, rutas_requeridas=[]
    )
    comparacion = comparar_con_historico(indicadores, historico)

    estado = "LISTO_PARA_REVISION" if validacion["es_valida"] else "REQUIERE_REVISION"
    reporte = {
        "periodo": periodo.codigo,
        "anio": periodo.anio,
        "trimestre": periodo.trimestre,
        "fecha_prevalidacion": core.ahora_iso(),
        "estado_prevalidacion": estado,
        "publicado_automaticamente": False,
        "requiere_aprobacion_humana": True,
        "url_origen": construir_url_zip(periodo),
        "pagina_bases_indec": URL_BASES_INDEC,
        "archivo_zip": ruta_zip.name,
        "indicadores": indicadores,
        "validacion_critica": validacion,
        "comparacion_historica": comparacion,
        "advertencias": [
            "Las alertas son umbrales operativos y no pruebas de significancia estadística.",
            "Los ingresos son nominales y no deben interpretarse como variaciones reales sin deflactar.",
            "La prevalidación no modifica historico_SDE.csv ni data_snapshot/.",
        ],
    }

    ruta_json = directorio_reportes / f"prevalidacion_{periodo.codigo}.json"
    ruta_md = directorio_reportes / f"prevalidacion_{periodo.codigo}.md"
    ruta_json.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
    ruta_md.write_text(_render_markdown(reporte), encoding="utf-8")
    core.guardar_metadatos_genericos(
        ruta_json,
        f"Reporte estructurado de prevalidación para {periodo.codigo}.",
        "Auditoría",
        periodo=periodo.codigo,
        anio=periodo.anio,
        trimestre=periodo.trimestre,
        estado_validacion="EN_REVISION",
        archivo_origen=ruta_zip.name,
    )
    core.guardar_metadatos_genericos(
        ruta_md,
        f"Reporte legible de prevalidación para {periodo.codigo}.",
        "Auditoría",
        periodo=periodo.codigo,
        anio=periodo.anio,
        trimestre=periodo.trimestre,
        estado_validacion="EN_REVISION",
        archivo_origen=ruta_zip.name,
    )
    core.generar_manifiesto(directorio_reportes)
    return reporte


def guardar_consulta_monitor(
    consulta: dict[str, Any], directorio_reportes: Path = DIR_MONITOR
) -> Path:
    """Persiste el último chequeo del monitor para auditoría y automatización."""
    directorio_reportes.mkdir(parents=True, exist_ok=True)
    ruta = directorio_reportes / "ultima_consulta.json"
    ruta.write_text(json.dumps(consulta, ensure_ascii=False, indent=2), encoding="utf-8")
    core.guardar_metadatos_genericos(
        ruta,
        "Última consulta automática de disponibilidad de microdatos EPH en INDEC.",
        "Operativa",
        estado_validacion="EN_REVISION",
        archivo_origen=URL_BASES_INDEC,
    )
    core.generar_manifiesto(directorio_reportes)
    return ruta


def imprimir_consulta(consulta: dict[str, Any]) -> None:
    print("\nMONITOR DE ACTUALIZACIONES EPH — INDEC")
    print("=" * 47)
    print(f"Último período local: {consulta['ultimo_periodo_local']}")
    consultas = consulta["periodos_consultados"]
    if not consultas:
        print("No hay períodos nuevos cuyo mes esperado de publicación haya llegado.")
        return
    for item in consultas:
        estado = item.get("estado_consulta")
        if estado == "DISPONIBLE":
            marca = "DISPONIBLE"
        elif estado == "ERROR":
            marca = "ERROR DE CONSULTA"
        else:
            marca = "NO DISPONIBLE"
        print(f"  {item['periodo']}: {marca} · {item['detalle']}")
    if consulta["hay_novedades"]:
        primero = consulta["nuevas_publicaciones"][0]["periodo"]
        print(f"\nNueva publicación detectada: {primero}")
        print("Puede prevalidarse con:")
        print("  python src/monitor_actualizaciones.py --prevalidar")
    elif consulta.get("errores_consulta"):
        print("\nLa consulta no pudo completarse para todos los períodos; revisar conectividad antes de concluir que no hay novedades.")
    else:
        print("\nNo se detectaron nuevas publicaciones disponibles.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Monitor asistido de nuevas publicaciones EPH del INDEC"
    )
    parser.add_argument("--prevalidar", action="store_true", help="Prevalida sin publicar.")
    parser.add_argument("--anio", type=int)
    parser.add_argument("--trimestre", type=int, choices=core.TRIMESTRES)
    parser.add_argument("--forzar", action="store_true", help="Fuerza redescarga en prevalidación.")
    parser.add_argument("--no-guardar", action="store_true", help="No persiste la consulta del monitor.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s · %(message)s")
    core.log = logging.getLogger("pipeline_eph")

    if bool(args.anio) ^ bool(args.trimestre):
        parser.error("--anio y --trimestre deben usarse juntos.")

    if args.anio and args.trimestre:
        periodo = Periodo(args.anio, args.trimestre)
        disponibilidad = consultar_zip_remoto(periodo)
        errores = [disponibilidad] if disponibilidad.get("estado_consulta") == "ERROR" else []
        consulta = {
            "fecha_consulta": core.ahora_iso(),
            "fuente": "INDEC - Bases de datos EPH",
            "pagina_bases": URL_BASES_INDEC,
            "ultimo_periodo_local": ultimo_periodo_local().codigo,
            "periodos_consultados": [disponibilidad],
            "nuevas_publicaciones": [disponibilidad] if disponibilidad["disponible"] else [],
            "hay_novedades": disponibilidad["disponible"],
            "errores_consulta": errores,
            "estado_monitor": "ERROR" if errores else ("NOVEDAD" if disponibilidad["disponible"] else "SIN_NOVEDADES"),
        }
    else:
        consulta = detectar_nuevas_publicaciones()

    imprimir_consulta(consulta)
    if not args.no_guardar:
        guardar_consulta_monitor(consulta)

    if not args.prevalidar:
        return

    if args.anio and args.trimestre:
        objetivo = Periodo(args.anio, args.trimestre)
    else:
        nuevas = consulta["nuevas_publicaciones"]
        if not nuevas:
            print("\nNo hay una publicación nueva disponible para prevalidar.")
            return
        # Se procesa primero el período faltante más antiguo para conservar continuidad temporal.
        objetivo = _periodo_desde_codigo(nuevas[0]["periodo"])
        assert objetivo is not None

    print(f"\nPrevalidando {objetivo.codigo} sin modificar el histórico...")
    reporte = prevalidar_periodo(objetivo, args.forzar)
    print(f"Estado: {reporte['estado_prevalidacion']}")
    print(f"Reporte: {DIR_MONITOR / f'prevalidacion_{objetivo.codigo}.md'}")
    if reporte["comparacion_historica"]["alertas"]:
        print(
            f"Alertas orientativas: {len(reporte['comparacion_historica']['alertas'])} "
            "(requieren revisión humana)."
        )


if __name__ == "__main__":
    main()
