from datetime import datetime
from pathlib import Path
import sys

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import monitor_actualizaciones as monitor  # noqa: E402


class FakeResponse:
    def __init__(self, status_code=200, content_type="application/zip", data=b"PK\x03\x04abcd"):
        self.status_code = status_code
        self.headers = {"content-type": content_type}
        self._data = data
        self.closed = False

    def iter_content(self, chunk_size=8):
        yield self._data

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return self.responses.pop(0)


def _historico_base() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "anio": 2025, "trimestre": 3, "periodo": "2025T3",
            "n_personas_muestra": 1000, "n_hogares_muestra": 300,
            "poblacion_expandida_total": 420000,
            "poblacion_expandida_mayor10": 370000,
            "pea_expandida": 190000, "ocupados_expandidos": 175000,
            "desocupados_expandidos": 15000, "inactivos_expandidos": 180000,
            "tasa_actividad_oficial": 45.24, "tasa_empleo_oficial": 41.67,
            "tasa_desocupacion": 7.89, "proporcion_inactiva_total": 54.76,
            "tasa_actividad_10_mas": 51.35, "tasa_empleo_10_mas": 47.30,
            "tasa_inactividad_10_mas": 48.65, "tasa_informalidad": 45.0,
            "ingreso_promedio_ponderado_observado": 500000,
        },
        {
            "anio": 2025, "trimestre": 4, "periodo": "2025T4",
            "n_personas_muestra": 1100, "n_hogares_muestra": 320,
            "poblacion_expandida_total": 430000,
            "poblacion_expandida_mayor10": 380000,
            "pea_expandida": 195000, "ocupados_expandidos": 180000,
            "desocupados_expandidos": 15000, "inactivos_expandidos": 185000,
            "tasa_actividad_oficial": 45.35, "tasa_empleo_oficial": 41.86,
            "tasa_desocupacion": 7.69, "proporcion_inactiva_total": 54.65,
            "tasa_actividad_10_mas": 51.32, "tasa_empleo_10_mas": 47.37,
            "tasa_inactividad_10_mas": 48.68, "tasa_informalidad": 44.0,
            "ingreso_promedio_ponderado_observado": 550000,
        },
    ])


def test_periodo_siguiente_cambia_de_anio():
    assert monitor.periodo_siguiente(monitor.Periodo(2025, 4)) == monitor.Periodo(2026, 1)


def test_candidatos_respetan_calendario_operativo():
    candidatos = monitor.periodos_candidatos(
        monitor.Periodo(2025, 4), datetime(2026, 9, 22)
    )
    assert [p.codigo for p in candidatos] == ["2026T1", "2026T2"]


def test_ultimo_periodo_local_usa_snapshot_como_contingencia(tmp_path):
    results = tmp_path / "results.csv"
    snapshot = tmp_path / "snapshot.csv"
    _historico_base().to_csv(snapshot, index=False)
    assert monitor.ultimo_periodo_local(results, snapshot).codigo == "2025T4"


def test_consulta_zip_valida_firma_pk():
    session = FakeSession([FakeResponse()])
    resultado = monitor.consultar_zip_remoto(monitor.Periodo(2026, 1), session=session)
    assert resultado["disponible"] is True
    assert resultado["estado_http"] == 200
    assert "EPH_usu_1_Trim_2026_txt.zip" in session.urls[0]


def test_consulta_zip_404_no_disponible():
    session = FakeSession([FakeResponse(status_code=404, content_type="text/html", data=b"")])
    resultado = monitor.consultar_zip_remoto(monitor.Periodo(2026, 2), session=session)
    assert resultado["disponible"] is False
    assert resultado["estado_http"] == 404


def test_detector_identifica_solo_publicacion_real(tmp_path):
    historico = tmp_path / "historico.csv"
    _historico_base().to_csv(historico, index=False)
    session = FakeSession([
        FakeResponse(status_code=200),
        FakeResponse(status_code=404, content_type="text/html", data=b""),
    ])
    resultado = monitor.detectar_nuevas_publicaciones(
        historico_resultados=historico,
        historico_snapshot=tmp_path / "no_existe.csv",
        fecha_referencia=datetime(2026, 9, 22),
        session=session,
    )
    assert resultado["hay_novedades"] is True
    assert [x["periodo"] for x in resultado["nuevas_publicaciones"]] == ["2026T1"]


def test_comparacion_genera_alerta_por_salto_grande():
    indicadores = _historico_base().iloc[-1].to_dict()
    indicadores.update({
        "anio": 2026, "trimestre": 1, "periodo": "2026T1",
        "tasa_desocupacion": 15.0,
        "n_personas_muestra": 700,
    })
    resultado = monitor.comparar_con_historico(indicadores, _historico_base())
    variables = {a["variable"] for a in resultado["alertas"]}
    assert "tasa_desocupacion" in variables
    assert "n_personas_muestra" in variables
    assert "significancia" in resultado["criterio_alertas"]["nota"]


def test_guardar_consulta_monitor_genera_auditoria(tmp_path):
    consulta = {
        "fecha_consulta": "2026-09-22T10:00:00",
        "fuente": "INDEC - Bases de datos EPH",
        "pagina_bases": monitor.URL_BASES_INDEC,
        "ultimo_periodo_local": "2025T4",
        "periodos_consultados": [],
        "nuevas_publicaciones": [],
        "hay_novedades": False,
        "errores_consulta": [],
        "estado_monitor": "SIN_NOVEDADES",
    }
    ruta = monitor.guardar_consulta_monitor(consulta, tmp_path)
    assert ruta.exists()
    assert ruta.with_suffix(".meta.json").exists()
    assert (tmp_path / "manifest_salidas.json").exists()


def test_prevalidacion_no_modifica_historico_y_genera_reporte(tmp_path, monkeypatch):
    historico = tmp_path / "historico_SDE.csv"
    base = _historico_base()
    base.to_csv(historico, index=False)
    bytes_antes = historico.read_bytes()

    zip_mock = tmp_path / "EPH_usu_1_Trim_2026_txt.zip"
    zip_mock.write_bytes(b"PKmock")
    ind_mock = tmp_path / "individual.txt"
    hog_mock = tmp_path / "hogar.txt"
    ind_mock.write_text("mock", encoding="utf-8")
    hog_mock.write_text("mock", encoding="utf-8")

    sde_ind = pd.DataFrame({"AGLOMERADO": [18] * 120, "EMPLEO": [1] * 120})
    sde_hog = pd.DataFrame({"AGLOMERADO": [18] * 40})
    indicadores = base.iloc[-1].to_dict()
    indicadores.update({
        "anio": 2026,
        "trimestre": 1,
        "periodo": "2026T1",
        "n_personas_muestra": 1120,
        "n_hogares_muestra": 325,
        "fecha_procesamiento": "2026-09-22 10:00:00",
        "fuente": "EPH INDEC",
    })

    monkeypatch.setattr(monitor.core, "descargar_zip", lambda *args, **kwargs: zip_mock)
    monkeypatch.setattr(monitor.core, "extraer_zip", lambda *args, **kwargs: (ind_mock, hog_mock))
    monkeypatch.setattr(
        monitor.core, "cargar_y_filtrar", lambda *args, **kwargs: (sde_ind, sde_hog)
    )
    monkeypatch.setattr(monitor.core, "calcular_indicadores", lambda *args, **kwargs: indicadores)
    monkeypatch.setattr(
        monitor.core,
        "validar_publicacion",
        lambda *args, **kwargs: {
            "periodo": "2026T1",
            "fecha_validacion": "2026-09-22T10:00:00",
            "estado": "VALIDADO",
            "es_valida": True,
            "controles": [
                {
                    "control": "prueba_prevalidacion",
                    "cumple": True,
                    "critico": True,
                    "detalle": "Control simulado satisfactorio.",
                }
            ],
            "errores": [],
        },
    )

    salida = tmp_path / "monitor"
    reporte = monitor.prevalidar_periodo(
        monitor.Periodo(2026, 1),
        directorio_reportes=salida,
        historico_resultados=historico,
        historico_snapshot=tmp_path / "snapshot_inexistente.csv",
    )

    assert reporte["estado_prevalidacion"] == "LISTO_PARA_REVISION"
    assert reporte["publicado_automaticamente"] is False
    assert historico.read_bytes() == bytes_antes
    assert (salida / "prevalidacion_2026T1.json").exists()
    assert (salida / "prevalidacion_2026T1.md").exists()
    assert (salida / "manifest_salidas.json").exists()
