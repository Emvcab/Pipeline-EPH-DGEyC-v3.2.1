from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import pandas as pd

INDICADORES = {
    "tasa_actividad_oficial": "tasa_actividad_indec",
    "tasa_empleo_oficial": "tasa_empleo_indec",
    "tasa_desocupacion": "tasa_desocupacion_indec",
}


def redondear_un_decimal(valor: float) -> float:
    """Replica un redondeo decimal convencional a una cifra."""
    return float(Decimal(str(valor)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def comparar_con_referencia(
    historico: pd.DataFrame,
    referencia: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compara las tasas del pipeline con los valores publicados por INDEC.

    La concordancia se evalúa a una cifra decimal porque los informes técnicos
    publican las tasas por aglomerado con una cifra decimal.
    """
    requeridas_hist = {"periodo", *INDICADORES.keys()}
    requeridas_ref = {"periodo", *INDICADORES.values()}
    faltan_hist = requeridas_hist - set(historico.columns)
    faltan_ref = requeridas_ref - set(referencia.columns)
    if faltan_hist:
        raise ValueError(f"Faltan columnas en histórico: {sorted(faltan_hist)}")
    if faltan_ref:
        raise ValueError(f"Faltan columnas en referencia INDEC: {sorted(faltan_ref)}")

    h = historico.copy()
    r = referencia.copy()
    h["periodo"] = h["periodo"].astype(str)
    r["periodo"] = r["periodo"].astype(str)

    combinado = h.merge(r, on="periodo", how="inner", validate="one_to_one")
    filas = []

    for _, fila in combinado.iterrows():
        for col_pipeline, col_indec in INDICADORES.items():
            valor_pipeline = float(fila[col_pipeline])
            valor_indec = float(fila[col_indec])
            valor_pipeline_1d = redondear_un_decimal(valor_pipeline)
            estado = "OK" if valor_pipeline_1d == valor_indec else "REVISAR"
            filas.append({
                "periodo": fila["periodo"],
                "indicador": col_pipeline,
                "pipeline": valor_pipeline,
                "pipeline_redondeado_1d": valor_pipeline_1d,
                "indec_publicado": valor_indec,
                "diferencia_pp": round(valor_pipeline - valor_indec, 2),
                "estado": estado,
                "fuente_oficial": fila.get("fuente_oficial"),
            })

    return pd.DataFrame(filas)
