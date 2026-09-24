"""Funciones auxiliares para el portal web de administración EPH.

La interfaz Streamlit consume estas funciones para mostrar el calendario,
listar prevalidaciones y ejecutar una incorporación controlada. La lógica
estadística permanece en :mod:`pipeline` y el monitoreo en
:mod:`monitor_actualizaciones`.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

import pandas as pd

import monitor_actualizaciones as monitor
import pipeline as core


MESES_NUMERO = {
    "Enero": 1,
    "Febrero": 2,
    "Marzo": 3,
    "Abril": 4,
    "Mayo": 5,
    "Junio": 6,
    "Julio": 7,
    "Agosto": 8,
    "Septiembre": 9,
    "Octubre": 10,
    "Noviembre": 11,
    "Diciembre": 12,
}


def construir_calendario(
    directorio: Path = core.DIR_RESULTADOS,
    anios: Optional[Iterable[int]] = None,
    fecha_referencia: Optional[datetime] = None,
) -> pd.DataFrame:
    """Devuelve el calendario operativo como tabla consumible por la UI.

    Reutiliza ``fecha_publicacion_esperada`` y ``estado_trimestre`` del pipeline;
    no mantiene una segunda regla de publicación.
    """
    hoy = fecha_referencia or datetime.now()
    anios_lista = list(anios) if anios is not None else core.ANIOS + [max(core.ANIOS) + 1]
    filas: list[dict[str, Any]] = []
    for anio in anios_lista:
        for trimestre in core.TRIMESTRES:
            mes, anio_pub = core.fecha_publicacion_esperada(anio, trimestre)
            estado = core.estado_trimestre(anio, trimestre, directorio)
            fecha_aprox = datetime(anio_pub, MESES_NUMERO[mes], 1)
            filas.append(
                {
                    "periodo": f"{anio}T{trimestre}",
                    "publicacion_estimada": f"{mes} {anio_pub}",
                    "anio_publicacion": anio_pub,
                    "mes_publicacion": MESES_NUMERO[mes],
                    "estado": estado,
                    "ya_correspondia_consultar": (anio_pub, MESES_NUMERO[mes])
                    <= (hoy.year, hoy.month),
                }
            )
    return pd.DataFrame(filas)


def resumen_calendario(
    calendario: pd.DataFrame,
    fecha_referencia: Optional[datetime] = None,
) -> dict[str, Any]:
    """Resume pendiente más antiguo y próxima publicación futura."""
    hoy = fecha_referencia or datetime.now()
    if calendario.empty:
        return {"pendiente": None, "proxima_publicacion": None}

    df = calendario.copy()
    validados = {"VALIDADO", "PUBLICADO"}
    pendientes = df[
        df["ya_correspondia_consultar"] & ~df["estado"].isin(validados)
    ].sort_values(["anio_publicacion", "mes_publicacion", "periodo"])

    futuros = df[
        (df["anio_publicacion"] > hoy.year)
        | ((df["anio_publicacion"] == hoy.year) & (df["mes_publicacion"] > hoy.month))
    ].sort_values(["anio_publicacion", "mes_publicacion", "periodo"])

    return {
        "pendiente": None if pendientes.empty else pendientes.iloc[0].to_dict(),
        "proxima_publicacion": None if futuros.empty else futuros.iloc[0].to_dict(),
    }


def listar_prevalidaciones(
    directorio_reportes: Path = monitor.DIR_MONITOR,
) -> pd.DataFrame:
    """Lista reportes de prevalidación válidos existentes en el área de monitor."""
    if not directorio_reportes.exists():
        return pd.DataFrame(
            columns=["periodo", "estado_prevalidacion", "fecha_prevalidacion", "ruta"]
        )

    filas: list[dict[str, Any]] = []
    for ruta in sorted(directorio_reportes.glob("prevalidacion_*.json")):
        if ruta.name.endswith(".meta.json"):
            continue
        try:
            reporte = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        periodo = core.normalizar_periodo(reporte.get("periodo"))
        if periodo is None:
            continue
        filas.append(
            {
                "periodo": periodo,
                "estado_prevalidacion": str(
                    reporte.get("estado_prevalidacion", "SIN_ESTADO")
                ),
                "fecha_prevalidacion": str(reporte.get("fecha_prevalidacion", "")),
                "n_alertas": len(
                    reporte.get("comparacion_historica", {}).get("alertas", [])
                ),
                "ruta": str(ruta),
            }
        )
    if not filas:
        return pd.DataFrame(
            columns=[
                "periodo",
                "estado_prevalidacion",
                "fecha_prevalidacion",
                "n_alertas",
                "ruta",
            ]
        )
    return pd.DataFrame(filas).sort_values("periodo").reset_index(drop=True)


def cargar_prevalidacion(
    periodo: str,
    directorio_reportes: Path = monitor.DIR_MONITOR,
) -> dict[str, Any]:
    """Carga un reporte de prevalidación por período."""
    normalizado = core.normalizar_periodo(periodo)
    if normalizado is None:
        raise ValueError("Período inválido; use formato AAAATn.")
    ruta = directorio_reportes / f"prevalidacion_{normalizado}.json"
    if not ruta.exists():
        raise FileNotFoundError(f"No existe prevalidación para {normalizado}.")
    return json.loads(ruta.read_text(encoding="utf-8"))


def publicar_periodo_asistido(
    periodo: str,
    confirmacion: str,
    publicar_snapshot: bool = True,
    forzar_descarga: bool = False,
    directorio_reportes: Path = monitor.DIR_MONITOR,
) -> dict[str, Any]:
    """Incorpora un período sólo si existe una prevalidación lista y confirmación explícita.

    Esta función es deliberadamente estricta para que la UI no pueda convertir un
    clic accidental en una publicación. La validación transaccional final continúa
    siendo la del pipeline principal.
    """
    normalizado = core.normalizar_periodo(periodo)
    if normalizado is None:
        raise ValueError("Período inválido; use formato AAAATn.")
    if confirmacion.strip().upper() != normalizado:
        raise ValueError(f"La confirmación debe ser exactamente {normalizado}.")

    reporte = cargar_prevalidacion(normalizado, directorio_reportes)
    if reporte.get("estado_prevalidacion") != "LISTO_PARA_REVISION":
        raise RuntimeError(
            "La prevalidación no está en estado LISTO_PARA_REVISION. "
            "Se requiere revisión antes de publicar."
        )

    anio = int(normalizado[:4])
    trimestre = int(normalizado[-1])
    indicadores = core.procesar_trimestre(anio, trimestre, forzar_descarga)
    if indicadores is None:
        raise RuntimeError(
            "El pipeline no validó el período. Se conserva el histórico anterior."
        )

    manifiesto_snapshot = None
    if publicar_snapshot:
        manifiesto_snapshot = core.publicar_snapshot_validado()

    return {
        "periodo": normalizado,
        "estado": "PUBLICADO" if publicar_snapshot else "VALIDADO",
        "indicadores": indicadores,
        "snapshot_actualizado": publicar_snapshot,
        "manifest_snapshot": manifiesto_snapshot,
        "fecha": core.ahora_iso(),
    }
