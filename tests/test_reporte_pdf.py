from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from reporte_pdf import generar_reporte_pdf


def historico_demo() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "anio": 2025, "trimestre": 3, "periodo": "2025T3",
            "tasa_actividad_oficial": 45.0, "tasa_empleo_oficial": 44.0,
            "tasa_desocupacion": 2.2, "proporcion_inactiva_total": 55.0,
            "tasa_informalidad": 58.0, "n_personas_muestra": 1500,
            "n_hogares_muestra": 430, "poblacion_expandida_total": 420000,
            "pea_expandida": 189000, "ingreso_promedio_ponderado_observado": 410000,
            "ingreso_mediano_observado": 350000, "tasa_no_respuesta_ingresos_ocupados": 1.2,
        },
        {
            "anio": 2025, "trimestre": 4, "periodo": "2025T4",
            "tasa_actividad_oficial": 46.2, "tasa_empleo_oficial": 45.3,
            "tasa_desocupacion": 1.9, "proporcion_inactiva_total": 53.8,
            "tasa_informalidad": 57.0, "n_personas_muestra": 1520,
            "n_hogares_muestra": 435, "poblacion_expandida_total": 421000,
            "pea_expandida": 194500, "ingreso_promedio_ponderado_observado": 450000,
            "ingreso_mediano_observado": 380000, "tasa_no_respuesta_ingresos_ocupados": 1.0,
        },
    ])


def segmentado_demo() -> pd.DataFrame:
    filas = [
        {"dimension": "Sexo", "categoria": "Varón", "n_muestra": 520, "poblacion_expandida": 170000, "tasa_actividad": 66.5, "tasa_empleo": 65.1, "tasa_desocupacion": 2.1, "tasa_informalidad": 55.0},
        {"dimension": "Sexo", "categoria": "Mujer", "n_muestra": 580, "poblacion_expandida": 184000, "tasa_actividad": 40.4, "tasa_empleo": 39.5, "tasa_desocupacion": 2.2, "tasa_informalidad": 59.0},
        {"dimension": "Edad", "categoria": "14 a 29 años", "n_muestra": 360, "poblacion_expandida": 98000, "tasa_actividad": 48.0, "tasa_empleo": 45.0, "tasa_desocupacion": 6.2, "tasa_informalidad": 63.0},
        {"dimension": "Edad", "categoria": "30 a 64 años", "n_muestra": 650, "poblacion_expandida": 210000, "tasa_actividad": 74.0, "tasa_empleo": 73.0, "tasa_desocupacion": 1.4, "tasa_informalidad": 53.0},
        {"dimension": "Edad", "categoria": "65 años y más", "n_muestra": 90, "poblacion_expandida": 46000, "tasa_actividad": 16.0, "tasa_empleo": 15.8, "tasa_desocupacion": 1.0, "tasa_informalidad": 48.0},
    ]
    for d in range(1, 11):
        filas.append({
            "dimension": "Decil de ingreso", "categoria": f"Decil {d}", "n_muestra": 55,
            "poblacion_expandida": 17000, "ingreso_promedio_ponderado_ocupados": d * 100000,
        })
    return pd.DataFrame(filas)


def test_genera_pdf_valido_con_segmentacion():
    contenido = generar_reporte_pdf(
        historico_demo(), "2025T4", periodo_comparacion="2025T3", segmentado=segmentado_demo()
    )
    assert contenido.startswith(b"%PDF")
    assert len(contenido) > 10_000


def test_genera_pdf_sin_segmentacion():
    contenido = generar_reporte_pdf(historico_demo(), "2025T4", segmentado=None)
    assert contenido.startswith(b"%PDF")
    assert len(contenido) > 5_000


def test_periodo_inexistente_falla_claro():
    with pytest.raises(ValueError, match="no existe"):
        generar_reporte_pdf(historico_demo(), "2030T1")


def test_historico_vacio_falla_claro():
    with pytest.raises(ValueError, match="vacío"):
        generar_reporte_pdf(pd.DataFrame(), "2025T4")
