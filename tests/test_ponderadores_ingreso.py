import pandas as pd

from src.pipeline import (
    ESQUEMA_OBLIGATORIO_INDIVIDUAL,
    ESQUEMA_OPCIONAL_INDIVIDUAL,
    calcular_indicadores,
    validar_esquema,
)


def _hogar():
    return pd.DataFrame(
        {
            "AGLOMERADO": [18, 18],
            "REALIZADA": [1, 1],
            "CODUSU": ["A", "B"],
            "NRO_HOGAR": [1, 1],
        }
    )


def _individual(con_pondiio=True):
    datos = {
        "AGLOMERADO": [18, 18],
        "PONDERA": [1, 1],
        "ESTADO": [1, 1],
        "P21": [100, 1000],
        "CH04": [1, 2],
        "CH06": [30, 40],
        "CODUSU": ["A", "B"],
        "NRO_HOGAR": [1, 1],
    }
    if con_pondiio:
        # Si se usara PONDERA, el promedio sería 550.
        # Con PONDIIO, el promedio correcto es (100*9 + 1000*1) / 10 = 190.
        datos["PONDIIO"] = [9, 1]
    return pd.DataFrame(datos)


def test_promedio_ponderado_p21_usa_pondiio_y_no_pondera():
    r = calcular_indicadores(_individual(con_pondiio=True), _hogar(), 2026, 1)

    assert r["ingreso_promedio_observado"] == 550.0
    assert r["ingreso_promedio_ponderado_observado"] == 190.0
    assert r["n_ocupados_con_pondiio_valido"] == 2


def test_sin_pondiio_no_hay_fallback_silencioso_a_pondera():
    r = calcular_indicadores(_individual(con_pondiio=False), _hogar(), 2026, 1)

    assert r["ingreso_promedio_observado"] == 550.0
    assert r["ingreso_promedio_ponderado_observado"] is None
    assert r["n_ocupados_con_pondiio_valido"] == 0


def test_falta_pondiio_se_registra_como_advertencia_de_esquema():
    df = _individual(con_pondiio=False)

    validacion = validar_esquema(
        df,
        ESQUEMA_OBLIGATORIO_INDIVIDUAL,
        ESQUEMA_OPCIONAL_INDIVIDUAL,
        "individual",
        2026,
        1,
    )

    assert validacion["nivel"] == "advertencia"
    assert "PONDIIO" in validacion["opcionales_faltantes"]
