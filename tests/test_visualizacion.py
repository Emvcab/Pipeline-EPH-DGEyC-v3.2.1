import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from visualizacion import filtrar_rango_periodos, rango_eje, variacion


def test_rango_eje_no_fuerza_cero_si_serie_esta_lejos_de_cero():
    rango = rango_eje([40.0, 41.0, 42.0])
    assert rango is not None
    minimo, maximo = rango
    assert minimo > 0
    assert minimo < 40.0
    assert maximo > 42.0


def test_rango_eje_acepta_valores_constantes():
    minimo, maximo = rango_eje([55.0, 55.0, 55.0])
    assert minimo < 55.0 < maximo


def test_rango_eje_sin_datos_devuelve_none():
    assert rango_eje([None, float("nan")]) is None


def test_filtrar_rango_periodos_normal():
    df = pd.DataFrame({"periodo": ["2025T1", "2025T2", "2025T3"], "x": [1, 2, 3]})
    salida = filtrar_rango_periodos(df, "2025T1", "2025T2")
    assert salida["periodo"].tolist() == ["2025T1", "2025T2"]


def test_filtrar_rango_periodos_invierte_si_hace_falta():
    df = pd.DataFrame({"periodo": ["2025T1", "2025T2", "2025T3"], "x": [1, 2, 3]})
    salida = filtrar_rango_periodos(df, "2025T3", "2025T2")
    assert salida["periodo"].tolist() == ["2025T2", "2025T3"]


def test_variacion_maneja_nulos():
    assert variacion(42.0, 40.5) == 1.5
    assert variacion(None, 40.5) is None
