from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from interpretacion_brechas import lectura_deciles, lectura_dimension


def test_lectura_dimension_identifica_extremos_y_brecha():
    df = pd.DataFrame({
        "categoria": ["Varón", "Mujer"],
        "tasa_empleo": [55.0, 42.0],
        "n_muestra": [500, 520],
    })
    mensajes = lectura_dimension(df, "Sexo", "tasa_empleo")
    texto = " ".join(mensajes)
    assert "Varón" in texto
    assert "Mujer" in texto
    assert "13.00 puntos porcentuales" in texto
    assert "descriptiva" in texto


def test_lectura_dimension_requiere_dos_categorias_validas():
    df = pd.DataFrame({"categoria": ["A", "B"], "tasa_actividad": [50.0, None]})
    mensajes = lectura_dimension(df, "Edad", "tasa_actividad")
    assert "menos de dos categorías" in mensajes[0]


def test_lectura_deciles_ordena_numericamente_y_calcula_razon():
    df = pd.DataFrame({
        "categoria": ["Decil 10", "Decil 1", "Decil 2"],
        "ingreso_promedio_ponderado_ocupados": [1000, 100, 200],
        "n_muestra": [40, 50, 45],
    })
    mensajes = lectura_deciles(df)
    texto = " ".join(mensajes)
    assert "Decil 1" in texto
    assert "Decil 10" in texto
    assert "$900" in texto
    assert "10.00 veces" in texto
    assert "ADECOCUR" in texto


def test_lectura_deciles_sin_datos():
    mensajes = lectura_deciles(pd.DataFrame())
    assert "No hay datos suficientes" in mensajes[0]
