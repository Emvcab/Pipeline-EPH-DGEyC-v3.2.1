from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from analisis_segmentado import generar_analisis_segmentado


def base_mock() -> pd.DataFrame:
    return pd.DataFrame({
        "AGLOMERADO": [18] * 10,
        "PONDERA": [100] * 10,
        "ESTADO": [1, 2, 1, 3, 1, 2, 1, 3, 1, 1],
        "EMPLEO": [1, 0, 2, 0, 2, 0, 1, 0, 2, 1],
        "P21": [100, 0, 300, 0, 500, 0, 700, 0, 900, 1100],
        "CH04": [1, 1, 2, 2, 1, 2, 1, 2, 2, 1],
        "CH06": [20, 22, 25, 28, 35, 40, 50, 55, 70, 75],
        "NIVEL_ED": [3, 3, 4, 4, 4, 5, 6, 6, 2, 1],
        "ADECOCUR": [1, 0, 3, 0, 5, 0, 7, 0, 9, 10],
    })


def test_genera_dimensiones_principales():
    resultado = generar_analisis_segmentado(base_mock(), 2025, 4)
    dims = set(resultado["dimension"])
    assert {"Sexo", "Edad", "Nivel educativo", "Decil de ingreso"} <= dims


def test_sexo_usa_14_mas():
    datos = base_mock()
    extra = datos.iloc[[0]].copy()
    extra["CH06"] = 10
    extra["CH04"] = 1
    extra["PONDERA"] = 10000
    datos = pd.concat([datos, extra], ignore_index=True)
    resultado = generar_analisis_segmentado(datos, 2025, 4)
    varon = resultado[(resultado["dimension"] == "Sexo") & (resultado["categoria"] == "Varón")].iloc[0]
    assert varon["universo"] == "Población de 14 años y más"
    assert varon["poblacion_expandida"] < 10000


def test_no_inventa_deciles_si_falta_adecocur():
    resultado = generar_analisis_segmentado(base_mock().drop(columns=["ADECOCUR"]), 2025, 4)
    assert "Decil de ingreso" not in set(resultado["dimension"])


def test_acepta_niveled_como_nombre_alternativo():
    datos = base_mock().rename(columns={"NIVEL_ED": "NIVELED"})
    resultado = generar_analisis_segmentado(datos, 2025, 4)
    assert "Nivel educativo" in set(resultado["dimension"])
