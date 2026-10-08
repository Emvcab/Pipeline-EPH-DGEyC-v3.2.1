import pandas as pd

from src.pipeline import calcular_indicadores


def _datos_sinteticos():
    """
    Caso controlado para verificar que los universos total, 10+ y 14+
    se calculan de forma independiente.

    PONDERA por edad/estado:
    - 8 años, menor de 10 (ESTADO=4): 50
    - 12 años, ocupado (ESTADO=1): 10
    - 14 años, ocupado (ESTADO=1): 20
    - 20 años, desocupado (ESTADO=2): 30
    - 30 años, inactivo (ESTADO=3): 40
    """
    individual = pd.DataFrame(
        {
            "AGLOMERADO": [18, 18, 18, 18, 18],
            "PONDERA": [50, 10, 20, 30, 40],
            "ESTADO": [4, 1, 1, 2, 3],
            "P21": [-9, 100, 200, -9, -9],
            "CH04": [1, 1, 2, 1, 2],
            "CH06": [8, 12, 14, 20, 30],
            "CODUSU": ["A", "B", "C", "D", "E"],
            "NRO_HOGAR": [1, 1, 1, 1, 1],
        }
    )

    hogar = pd.DataFrame(
        {
            "AGLOMERADO": [18, 18, 18, 18, 18],
            "REALIZADA": [1, 1, 1, 1, 1],
            "CODUSU": ["A", "B", "C", "D", "E"],
            "NRO_HOGAR": [1, 1, 1, 1, 1],
        }
    )
    return individual, hogar


def test_tasas_14_mas_respetan_universo_especifico():
    individual, hogar = _datos_sinteticos()
    r = calcular_indicadores(individual, hogar, 2026, 1)

    # Universo 14+: pesos 20 + 30 + 40 = 90
    # PEA 14+: 20 + 30 = 50
    # Ocupados 14+: 20
    # Desocupados 14+: 30
    assert r["poblacion_expandida_14_mas"] == 90
    assert r["pea_expandida_14_mas"] == 50
    assert r["ocupados_expandidos_14_mas"] == 20
    assert r["desocupados_expandidos_14_mas"] == 30

    assert r["tasa_actividad_14_mas"] == 55.56
    assert r["tasa_empleo_14_mas"] == 22.22
    assert r["tasa_desocupacion_14_mas"] == 60.0


def test_indicadores_10_mas_se_conservan_como_referencia_historica():
    individual, hogar = _datos_sinteticos()
    r = calcular_indicadores(individual, hogar, 2026, 1)

    # Universo 10+: pesos 10 + 20 + 30 + 40 = 100
    # PEA 10+: 10 + 20 + 30 = 60
    # Ocupados 10+: 10 + 20 = 30
    # Inactivos 10+: 40
    assert r["poblacion_expandida_mayor10"] == 100
    assert r["tasa_actividad_10_mas"] == 60.0
    assert r["tasa_empleo_10_mas"] == 30.0
    assert r["tasa_inactividad_10_mas"] == 40.0


def test_tasas_principales_no_cambian_al_agregar_14_mas():
    individual, hogar = _datos_sinteticos()
    r = calcular_indicadores(individual, hogar, 2026, 1)

    # Población total expandida = 150
    # PEA = 60, ocupados = 30, desocupados = 30
    assert r["poblacion_expandida_total"] == 150
    assert r["tasa_actividad_oficial"] == 40.0
    assert r["tasa_empleo_oficial"] == 20.0
    assert r["tasa_desocupacion"] == 50.0
