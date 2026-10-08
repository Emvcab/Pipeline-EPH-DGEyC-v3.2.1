"""Utilidades puras de visualización y selección temporal para el portal EPH.

No contiene lógica estadística del ETL. Se limita a preparar rangos y comparaciones
para que la interfaz pueda mostrar variaciones sin forzar los ejes a cero.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def rango_eje(
    valores: Iterable[object],
    margen_relativo: float = 0.12,
    margen_minimo: float = 0.5,
) -> tuple[float, float] | None:
    """Devuelve un rango Y acolchado a partir de valores válidos.

    El objetivo es dejar visible la variación real de la serie en lugar de forzar
    el eje a comenzar en cero. Si no hay valores numéricos, devuelve ``None``.
    """
    serie = pd.to_numeric(pd.Series(list(valores)), errors="coerce").dropna()
    if serie.empty:
        return None

    minimo = float(serie.min())
    maximo = float(serie.max())
    amplitud = maximo - minimo
    base = max(abs(minimo), abs(maximo), 1.0)
    margen = max(amplitud * margen_relativo, base * 0.02, margen_minimo)

    if amplitud == 0:
        margen = max(abs(minimo) * 0.05, margen_minimo)

    return minimo - margen, maximo + margen


def filtrar_rango_periodos(
    df: pd.DataFrame,
    desde: str,
    hasta: str,
    columna: str = "periodo",
) -> pd.DataFrame:
    """Filtra un dataframe según el orden en que aparecen sus períodos.

    Requiere que el dataframe ya esté ordenado cronológicamente, como ocurre en el
    portal. Si el usuario invierte inicio y fin, la función normaliza el orden.
    """
    periodos = df[columna].astype(str).tolist()
    if desde not in periodos or hasta not in periodos:
        raise ValueError("El período seleccionado no existe en el histórico visible.")

    i = periodos.index(desde)
    j = periodos.index(hasta)
    if i > j:
        i, j = j, i
    return df.iloc[i : j + 1].copy()


def variacion(valor_actual: object, valor_anterior: object) -> float | None:
    """Calcula una diferencia simple, o ``None`` si alguno de los valores falta."""
    if valor_actual is None or valor_anterior is None:
        return None
    if pd.isna(valor_actual) or pd.isna(valor_anterior):
        return None
    return float(valor_actual) - float(valor_anterior)
