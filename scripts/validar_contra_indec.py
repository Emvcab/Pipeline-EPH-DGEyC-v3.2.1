from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.validacion_metodologica import comparar_con_referencia

RUTA_HISTORICO = RAIZ / "results" / "historico_SDE.csv"
if not RUTA_HISTORICO.exists():
    RUTA_HISTORICO = RAIZ / "data_snapshot" / "historico_SDE.csv"

RUTA_REFERENCIA = RAIZ / "docs" / "referencia_indec_aglomerado18.csv"
RUTA_SALIDA = RAIZ / "results" / "validacion_metodologica_indec.csv"

if not RUTA_HISTORICO.exists():
    raise FileNotFoundError("No se encontró historico_SDE.csv en results/ ni data_snapshot/.")
if not RUTA_REFERENCIA.exists():
    raise FileNotFoundError("No se encontró docs/referencia_indec_aglomerado18.csv.")

historico = pd.read_csv(RUTA_HISTORICO)
referencia = pd.read_csv(RUTA_REFERENCIA)

comparacion = comparar_con_referencia(historico, referencia)
RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
comparacion.to_csv(RUTA_SALIDA, index=False, encoding="utf-8-sig")

print(comparacion.to_string(index=False))
print()
print("Resumen:")
print(comparacion["estado"].value_counts().to_string())
print(f"\nSalida: {RUTA_SALIDA}")

if (comparacion["estado"] != "OK").any():
    raise SystemExit(1)
