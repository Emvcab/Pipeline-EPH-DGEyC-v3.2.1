import pandas as pd

from src.validacion_metodologica import comparar_con_referencia, redondear_un_decimal


def test_redondeo_metodologico_a_un_decimal():
    assert redondear_un_decimal(43.95) == 44.0
    assert redondear_un_decimal(41.23) == 41.2
    assert redondear_un_decimal(42.24) == 42.2


def test_comparacion_marca_ok_si_reproduce_publicacion_redondeada():
    historico = pd.DataFrame([{
        "periodo": "2025T4",
        "tasa_actividad_oficial": 41.23,
        "tasa_empleo_oficial": 40.97,
        "tasa_desocupacion": 0.63,
    }])
    referencia = pd.DataFrame([{
        "periodo": "2025T4",
        "tasa_actividad_indec": 41.2,
        "tasa_empleo_indec": 41.0,
        "tasa_desocupacion_indec": 0.6,
        "fuente_oficial": "INDEC",
    }])

    resultado = comparar_con_referencia(historico, referencia)

    assert len(resultado) == 3
    assert set(resultado["estado"]) == {"OK"}


def test_comparacion_detecta_discrepancia_real():
    historico = pd.DataFrame([{
        "periodo": "2025T4",
        "tasa_actividad_oficial": 40.0,
        "tasa_empleo_oficial": 40.97,
        "tasa_desocupacion": 0.63,
    }])
    referencia = pd.DataFrame([{
        "periodo": "2025T4",
        "tasa_actividad_indec": 41.2,
        "tasa_empleo_indec": 41.0,
        "tasa_desocupacion_indec": 0.6,
    }])

    resultado = comparar_con_referencia(historico, referencia)
    actividad = resultado[resultado["indicador"] == "tasa_actividad_oficial"].iloc[0]

    assert actividad["estado"] == "REVISAR"
