from datetime import datetime
from pathlib import Path
import json
import sys

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import portal_admin as portal  # noqa: E402


def test_calendario_reutiliza_reglas_del_pipeline(monkeypatch, tmp_path):
    monkeypatch.setattr(
        portal.core,
        "estado_trimestre",
        lambda anio, trimestre, directorio: "PUBLICADO" if (anio, trimestre) == (2026, 1) else "FUTURO",
    )
    df = portal.construir_calendario(
        tmp_path,
        anios=[2026],
        fecha_referencia=datetime(2026, 7, 1),
    )
    t1 = df[df["periodo"] == "2026T1"].iloc[0]
    t2 = df[df["periodo"] == "2026T2"].iloc[0]
    assert t1["publicacion_estimada"] == "Junio 2026"
    assert t2["publicacion_estimada"] == "Septiembre 2026"
    assert bool(t1["ya_correspondia_consultar"]) is True
    assert bool(t2["ya_correspondia_consultar"]) is False


def test_resumen_calendario_distingue_pendiente_y_proxima():
    df = pd.DataFrame([
        {
            "periodo": "2026T1", "publicacion_estimada": "Junio 2026",
            "anio_publicacion": 2026, "mes_publicacion": 6,
            "estado": "PUBLICADO", "ya_correspondia_consultar": True,
        },
        {
            "periodo": "2026T2", "publicacion_estimada": "Septiembre 2026",
            "anio_publicacion": 2026, "mes_publicacion": 9,
            "estado": "PENDIENTE", "ya_correspondia_consultar": True,
        },
        {
            "periodo": "2026T3", "publicacion_estimada": "Diciembre 2026",
            "anio_publicacion": 2026, "mes_publicacion": 12,
            "estado": "FUTURO", "ya_correspondia_consultar": False,
        },
    ])
    resumen = portal.resumen_calendario(df, datetime(2026, 9, 22))
    assert resumen["pendiente"]["periodo"] == "2026T2"
    assert resumen["proxima_publicacion"]["periodo"] == "2026T3"


def test_listar_y_cargar_prevalidaciones(tmp_path):
    reporte = {
        "periodo": "2026T1",
        "estado_prevalidacion": "LISTO_PARA_REVISION",
        "fecha_prevalidacion": "2026-09-22T10:00:00",
        "comparacion_historica": {"alertas": [{"variable": "x"}]},
    }
    (tmp_path / "prevalidacion_2026T1.json").write_text(
        json.dumps(reporte), encoding="utf-8"
    )
    (tmp_path / "prevalidacion_2026T1.meta.json").write_text("{}", encoding="utf-8")
    df = portal.listar_prevalidaciones(tmp_path)
    assert df["periodo"].tolist() == ["2026T1"]
    assert int(df.iloc[0]["n_alertas"]) == 1
    assert portal.cargar_prevalidacion("2026T1", tmp_path)["estado_prevalidacion"] == "LISTO_PARA_REVISION"


def test_publicacion_asistida_exige_confirmacion(tmp_path):
    reporte = {
        "periodo": "2026T1",
        "estado_prevalidacion": "LISTO_PARA_REVISION",
    }
    (tmp_path / "prevalidacion_2026T1.json").write_text(
        json.dumps(reporte), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="exactamente"):
        portal.publicar_periodo_asistido(
            "2026T1", "2026T2", directorio_reportes=tmp_path
        )


def test_publicacion_asistida_bloquea_reporte_no_listo(tmp_path):
    reporte = {
        "periodo": "2026T1",
        "estado_prevalidacion": "REQUIERE_REVISION",
    }
    (tmp_path / "prevalidacion_2026T1.json").write_text(
        json.dumps(reporte), encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="LISTO_PARA_REVISION"):
        portal.publicar_periodo_asistido(
            "2026T1", "2026T1", directorio_reportes=tmp_path
        )


def test_publicacion_asistida_ejecuta_pipeline_y_snapshot(tmp_path, monkeypatch):
    reporte = {
        "periodo": "2026T1",
        "estado_prevalidacion": "LISTO_PARA_REVISION",
    }
    (tmp_path / "prevalidacion_2026T1.json").write_text(
        json.dumps(reporte), encoding="utf-8"
    )
    llamadas = []
    monkeypatch.setattr(
        portal.core,
        "procesar_trimestre",
        lambda anio, trimestre, forzar=False: llamadas.append((anio, trimestre, forzar)) or {"periodo": "2026T1"},
    )
    monkeypatch.setattr(
        portal.core,
        "publicar_snapshot_validado",
        lambda: {"archivos": []},
    )
    resultado = portal.publicar_periodo_asistido(
        "2026T1", "2026T1", directorio_reportes=tmp_path
    )
    assert llamadas == [(2026, 1, False)]
    assert resultado["estado"] == "PUBLICADO"
    assert resultado["snapshot_actualizado"] is True
