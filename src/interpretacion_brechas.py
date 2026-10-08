"""Lecturas descriptivas para la sección Brechas y perfiles.

Las funciones de este módulo resumen diferencias observadas sin inferir
causalidad ni significancia estadística. La EPH es una encuesta por muestreo,
por lo que cualquier comparación debe interpretarse junto con los tamaños de
muestra y, cuando corresponda, con medidas de error muestral.
"""
from __future__ import annotations

import math
import re

import pandas as pd


ETIQUETAS_METRICAS = {
    "tasa_actividad": "tasa de actividad",
    "tasa_empleo": "tasa de empleo",
    "tasa_desocupacion": "tasa de desocupación",
    "tasa_informalidad": "tasa de informalidad",
}


def _numero(valor: object) -> float | None:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numero):
        return None
    return numero


def _orden_decil(categoria: object) -> int | None:
    coincidencia = re.search(r"(\d+)", str(categoria))
    return int(coincidencia.group(1)) if coincidencia else None


def _rango_muestral(vista: pd.DataFrame) -> str | None:
    if "n_muestra" not in vista.columns:
        return None
    muestra = pd.to_numeric(vista["n_muestra"], errors="coerce").dropna()
    if muestra.empty:
        return None
    minimo = int(muestra.min())
    maximo = int(muestra.max())
    if minimo == maximo:
        return f"Cada categoría contiene {minimo} observaciones muestrales."
    return f"Los tamaños muestrales por categoría van de {minimo} a {maximo} observaciones."


def lectura_dimension(vista: pd.DataFrame, dimension: str, metrica: str) -> list[str]:
    """Resume extremos y diferencia descriptiva para una tasa seleccionada."""
    if vista is None or vista.empty or metrica not in vista.columns:
        return ["No hay datos suficientes para construir una lectura descriptiva."]

    datos = vista[["categoria", metrica]].copy()
    datos[metrica] = pd.to_numeric(datos[metrica], errors="coerce")
    datos = datos.dropna(subset=[metrica])
    if len(datos) < 2:
        return ["Hay menos de dos categorías con datos válidos para comparar."]

    mayor = datos.loc[datos[metrica].idxmax()]
    menor = datos.loc[datos[metrica].idxmin()]
    valor_mayor = float(mayor[metrica])
    valor_menor = float(menor[metrica])
    diferencia = valor_mayor - valor_menor
    etiqueta = ETIQUETAS_METRICAS.get(metrica, metrica.replace("_", " "))

    mensajes = [
        (
            f"En {dimension.lower()}, la mayor {etiqueta} observada corresponde a "
            f"{mayor['categoria']} ({valor_mayor:.2f}%) y la menor a "
            f"{menor['categoria']} ({valor_menor:.2f}%)."
        ),
        f"La diferencia descriptiva entre ambos extremos es de {diferencia:.2f} puntos porcentuales.",
    ]
    rango = _rango_muestral(vista)
    if rango:
        mensajes.append(rango)
    mensajes.append(
        "La comparación es descriptiva: no implica causalidad ni, por sí sola, significancia estadística."
    )
    return mensajes


def lectura_deciles(vista: pd.DataFrame) -> list[str]:
    """Resume distancia nominal entre extremos de la escala decílica de ingreso."""
    columna = "ingreso_promedio_ponderado_ocupados"
    if vista is None or vista.empty or columna not in vista.columns:
        return ["No hay datos suficientes para interpretar los deciles de ingreso."]

    datos = vista[["categoria", columna]].copy()
    datos[columna] = pd.to_numeric(datos[columna], errors="coerce")
    datos["_orden"] = datos["categoria"].map(_orden_decil)
    datos = datos.dropna(subset=[columna, "_orden"]).sort_values("_orden")
    if len(datos) < 2:
        return ["Hay menos de dos deciles con ingreso válido para comparar."]

    inferior = datos.iloc[0]
    superior = datos.iloc[-1]
    ingreso_inf = float(inferior[columna])
    ingreso_sup = float(superior[columna])
    brecha = ingreso_sup - ingreso_inf
    razon = ingreso_sup / ingreso_inf if ingreso_inf > 0 else None

    mensajes = [
        (
            f"El ingreso medio de la ocupación principal va de ${ingreso_inf:,.0f} en "
            f"{inferior['categoria']} a ${ingreso_sup:,.0f} en {superior['categoria']}."
        ),
        f"La distancia nominal entre ambos extremos es de ${brecha:,.0f}.",
    ]
    if razon is not None and math.isfinite(razon):
        mensajes.append(
            f"El ingreso medio del extremo superior equivale a {razon:.2f} veces el del extremo inferior."
        )
    rango = _rango_muestral(vista)
    if rango:
        mensajes.append(rango)
    mensajes.append(
        "La progresión entre deciles es esperable por construcción de ADECOCUR; esta lectura dimensiona la distancia nominal y no explica sus causas."
    )
    return mensajes
