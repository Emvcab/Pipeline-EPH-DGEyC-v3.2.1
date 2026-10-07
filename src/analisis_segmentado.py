"""Análisis segmentado de microdatos EPH para el Aglomerado 18.

Este módulo agrega una capa analítica sobre el motor ETL 3.2.1 sin modificar
sus indicadores agregados. Las tasas específicas de sexo se calculan para la
población de 14 años y más, en línea con los cuadros de mercado de trabajo del
INDEC. Los resultados son descriptivos y deben interpretarse considerando el
error muestral de la EPH.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


SEXO = {1: "Varón", 2: "Mujer"}
NIVEL_EDUCATIVO = {
    1: "Primario incompleto",
    2: "Primario completo",
    3: "Secundario incompleto",
    4: "Secundario completo",
    5: "Superior/universitario incompleto",
    6: "Superior/universitario completo",
    7: "Sin instrucción",
}


def _columna(df: pd.DataFrame, *candidatas: str) -> str | None:
    """Devuelve la primera columna disponible entre varios nombres equivalentes."""
    mapa = {str(c).upper(): str(c) for c in df.columns}
    for candidata in candidatas:
        if candidata.upper() in mapa:
            return mapa[candidata.upper()]
    return None


def _num(df: pd.DataFrame, columna: str) -> pd.Series:
    return pd.to_numeric(df[columna], errors="coerce")


def _suma_pesos(df: pd.DataFrame) -> float:
    if df.empty or "PONDERA" not in df.columns:
        return 0.0
    pesos = pd.to_numeric(df["PONDERA"], errors="coerce")
    return float(pesos[pesos > 0].sum())


def _porcentaje(num: float, den: float) -> float | None:
    if den <= 0:
        return None
    return round(num / den * 100, 2)


def _promedio_ponderado(df: pd.DataFrame, variable: str) -> float | None:
    if df.empty or variable not in df.columns or "PONDERA" not in df.columns:
        return None
    valores = pd.to_numeric(df[variable], errors="coerce")
    pesos = pd.to_numeric(df["PONDERA"], errors="coerce")
    validos = valores.notna() & pesos.notna() & (pesos > 0)
    if not validos.any():
        return None
    suma = float(pesos[validos].sum())
    if suma <= 0:
        return None
    return round(float((valores[validos] * pesos[validos]).sum()) / suma, 0)


def _indicadores_grupo(
    grupo: pd.DataFrame,
    *,
    dimension: str,
    categoria: str,
    periodo: str,
    universo: str,
) -> dict:
    estado = pd.to_numeric(grupo["ESTADO"], errors="coerce")
    poblacion = _suma_pesos(grupo)
    pea = _suma_pesos(grupo[estado.isin([1, 2])])
    ocupados = grupo[estado == 1].copy()
    ocup = _suma_pesos(ocupados)
    desocup = _suma_pesos(grupo[estado == 2])

    informalidad = None
    if "EMPLEO" in ocupados.columns and not ocupados.empty:
        empleo = pd.to_numeric(ocupados["EMPLEO"], errors="coerce")
        validos = ocupados[empleo.isin([1, 2])]
        if not validos.empty:
            empleo_validos = pd.to_numeric(validos["EMPLEO"], errors="coerce")
            informalidad = _porcentaje(
                _suma_pesos(validos[empleo_validos == 2]),
                _suma_pesos(validos),
            )

    ingresos = ocupados.copy()
    if "P21" in ingresos.columns:
        p21 = pd.to_numeric(ingresos["P21"], errors="coerce")
        ingresos = ingresos[p21 > 0]
    else:
        ingresos = ingresos.iloc[0:0]

    return {
        "periodo": periodo,
        "dimension": dimension,
        "categoria": categoria,
        "universo": universo,
        "n_muestra": int(len(grupo)),
        "poblacion_expandida": int(round(poblacion)),
        "tasa_actividad": _porcentaje(pea, poblacion),
        "tasa_empleo": _porcentaje(ocup, poblacion),
        "tasa_desocupacion": _porcentaje(desocup, pea),
        "tasa_informalidad": informalidad,
        "ingreso_promedio_ponderado_ocupados": _promedio_ponderado(ingresos, "P21"),
    }


def generar_analisis_segmentado(
    sde_ind: pd.DataFrame, anio: int, trimestre: int
) -> pd.DataFrame:
    """Construye indicadores por sexo, edad, educación y decil de ingreso.

    - Sexo: tasas específicas para personas de 14 años y más.
    - Edad: 14-29, 30-64 y 65 años y más.
    - Educación: personas de 14 años y más; NIVEL_ED/NIVELED 1..7.
    - Deciles: ADECOCUR (decil del ingreso de la ocupación principal dentro del
      aglomerado), sólo ocupados con P21 > 0. Si ADECOCUR no está disponible no
      se fabrican deciles alternativos.
    """
    periodo = f"{anio}T{trimestre}"
    if sde_ind.empty:
        return pd.DataFrame()

    datos = sde_ind.copy()
    datos["CH06"] = pd.to_numeric(datos["CH06"], errors="coerce")
    datos["CH04"] = pd.to_numeric(datos["CH04"], errors="coerce")
    datos["ESTADO"] = pd.to_numeric(datos["ESTADO"], errors="coerce")
    datos["PONDERA"] = pd.to_numeric(datos["PONDERA"], errors="coerce")
    filas: list[dict] = []

    # Sexo: el INDEC presenta tasas específicas para la población de 14 años y más.
    mayores14 = datos[datos["CH06"] >= 14]
    for codigo, etiqueta in SEXO.items():
        grupo = mayores14[mayores14["CH04"] == codigo]
        if not grupo.empty:
            filas.append(_indicadores_grupo(
                grupo, dimension="Sexo", categoria=etiqueta, periodo=periodo,
                universo="Población de 14 años y más",
            ))

    # Edad: bandas cercanas a las utilizadas en los informes de mercado de trabajo.
    grupos_edad = [
        ("14 a 29 años", 14, 29),
        ("30 a 64 años", 30, 64),
        ("65 años y más", 65, None),
    ]
    for etiqueta, minimo, maximo in grupos_edad:
        mascara = datos["CH06"] >= minimo
        if maximo is not None:
            mascara &= datos["CH06"] <= maximo
        grupo = datos[mascara]
        if not grupo.empty:
            filas.append(_indicadores_grupo(
                grupo, dimension="Edad", categoria=etiqueta, periodo=periodo,
                universo="Grupo de edad",
            ))

    # Nivel educativo. La base aparece documentada como NIVEL_ED y en algunos
    # sistemas históricos como NIVELED; se aceptan ambos nombres.
    col_educacion = _columna(datos, "NIVEL_ED", "NIVELED")
    if col_educacion is not None:
        educacion = pd.to_numeric(datos[col_educacion], errors="coerce")
        for codigo, etiqueta in NIVEL_EDUCATIVO.items():
            grupo = datos[(datos["CH06"] >= 14) & (educacion == codigo)]
            if not grupo.empty:
                filas.append(_indicadores_grupo(
                    grupo, dimension="Nivel educativo", categoria=etiqueta,
                    periodo=periodo, universo="Población de 14 años y más",
                ))

    # Decil del ingreso de la ocupación principal del aglomerado. Se utiliza la
    # variable construida por INDEC, no un qcut local que alteraría la metodología.
    col_decil = _columna(datos, "ADECOCUR")
    if col_decil is not None and "P21" in datos.columns:
        estado = pd.to_numeric(datos["ESTADO"], errors="coerce")
        p21 = pd.to_numeric(datos["P21"], errors="coerce")
        decil = pd.to_numeric(datos[col_decil], errors="coerce")
        ocupados = datos[(estado == 1) & (p21 > 0) & decil.between(1, 10)].copy()
        if not ocupados.empty:
            ocupados["__decil"] = pd.to_numeric(ocupados[col_decil], errors="coerce")
            for codigo in range(1, 11):
                grupo = ocupados[ocupados["__decil"] == codigo]
                if grupo.empty:
                    continue
                filas.append({
                    "periodo": periodo,
                    "dimension": "Decil de ingreso",
                    "categoria": f"Decil {codigo}",
                    "universo": "Ocupados con P21 > 0; ADECOCUR del aglomerado",
                    "n_muestra": int(len(grupo)),
                    "poblacion_expandida": int(round(_suma_pesos(grupo))),
                    "tasa_actividad": np.nan,
                    "tasa_empleo": np.nan,
                    "tasa_desocupacion": np.nan,
                    "tasa_informalidad": np.nan,
                    "ingreso_promedio_ponderado_ocupados": _promedio_ponderado(grupo, "P21"),
                })

    return pd.DataFrame(filas)


def dimensiones_disponibles(df: pd.DataFrame) -> list[str]:
    if df is None or df.empty or "dimension" not in df.columns:
        return []
    return sorted(df["dimension"].dropna().astype(str).unique().tolist())
