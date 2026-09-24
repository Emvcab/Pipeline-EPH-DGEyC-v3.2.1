"""Dashboard institucional de indicadores EPH para el aglomerado 18."""

from __future__ import annotations

import hmac
import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="EPH · Santiago del Estero - La Banda",
    page_icon="📊",
    layout="wide",
)

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import monitor_actualizaciones as monitor
import portal_admin
import pipeline as core
from pipeline import normalizar_estado, normalizar_periodo


DIR_RESULTADOS = RAIZ / "results"
DIR_SNAPSHOT = RAIZ / "data_snapshot"
DIR_DOCS = RAIZ / "docs"
ESTADOS_VALIDOS = {"VALIDADO", "PUBLICADO"}


def leer_json(ruta: Path) -> dict | None:
    """Lee JSON sin interrumpir el dashboard si falta o está dañado."""
    try:
        return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None
    except (OSError, json.JSONDecodeError):
        return None


def leer_csv(ruta: Path) -> pd.DataFrame | None:
    """Lee CSV con un resultado comprensible ante archivos ausentes o inválidos."""
    try:
        return pd.read_csv(ruta) if ruta.exists() else None
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        return None


def directorio_publicable(directorio: Path) -> bool:
    """Acepta un directorio sólo si su último período está validado."""
    historico = leer_csv(directorio / "historico_SDE.csv")
    estados = leer_csv(directorio / "estado_periodos.csv")
    if historico is None or historico.empty or estados is None or estados.empty:
        return False
    periodos_historico = historico["periodo"].map(normalizar_periodo)
    periodos_estado = estados["periodo"].map(normalizar_periodo)
    estados_normalizados = estados["estado"].map(normalizar_estado)
    if periodos_historico.isna().any() or periodos_estado.isna().any():
        return False
    ultimo_indice = historico.sort_values(["anio", "trimestre"]).index[-1]
    ultimo = periodos_historico.loc[ultimo_indice]
    fila = estados[periodos_estado == ultimo]
    if fila.empty:
        return False
    return estados_normalizados.loc[fila.index[-1]] in ESTADOS_VALIDOS


def seleccionar_fuente() -> tuple[Path | None, bool, str]:
    """Prioriza resultados locales validados y conserva el snapshot como contingencia."""
    if directorio_publicable(DIR_RESULTADOS):
        return DIR_RESULTADOS, False, "Resultados locales validados"
    if directorio_publicable(DIR_SNAPSHOT):
        return DIR_SNAPSHOT, True, "Snapshot agregado validado"
    return None, False, "Sin datos validados"


def formato_numero(valor: object, decimales: int = 0, prefijo: str = "") -> str:
    """Formatea métricas y evita mostrar errores cuando el dato no existe."""
    if valor is None or pd.isna(valor):
        return "No disponible"
    return f"{prefijo}{float(valor):,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formato_tasa(valor: object) -> str:
    return "No disponible" if valor is None or pd.isna(valor) else f"{float(valor):.2f}%"


def boton_descarga(ruta: Path, etiqueta: str, clave: str) -> None:
    """Ofrece un archivo existente o explica claramente su ausencia."""
    if ruta.exists() and ruta.is_file():
        st.download_button(
            etiqueta,
            data=ruta.read_bytes(),
            file_name=ruta.name,
            key=clave,
        )
    else:
        st.caption(f"{ruta.name}: no disponible para esta fuente.")


def _config_texto(secret_key: str, env_key: str) -> str | None:
    """Lee configuración administrativa desde secrets o variables de entorno."""
    valor_entorno = os.getenv(env_key)
    if valor_entorno:
        return valor_entorno
    try:
        valor = st.secrets.get(secret_key)
    except (FileNotFoundError, KeyError):
        valor = None
    return str(valor) if valor not in (None, "") else None


def _config_bool(secret_key: str, env_key: str, default: bool = False) -> bool:
    valor = _config_texto(secret_key, env_key)
    if valor is None:
        return default
    return valor.strip().lower() in {"1", "true", "si", "sí", "yes", "on"}


def administrador_autenticado() -> bool:
    """Autenticación simple para el MVP; no sustituye un SSO institucional."""
    clave_configurada = _config_texto("admin_password", "EPH_ADMIN_PASSWORD")
    if not clave_configurada:
        st.warning(
            "El área administrativa está en modo lectura porque no se configuró "
            "`admin_password`/`EPH_ADMIN_PASSWORD`."
        )
        return False
    if st.session_state.get("admin_autenticado", False):
        c1, c2 = st.columns([4, 1])
        c1.success("Sesión administrativa habilitada.")
        if c2.button("Cerrar sesión", key="admin_logout"):
            st.session_state["admin_autenticado"] = False
            st.rerun()
        return True

    clave_ingresada = st.text_input(
        "Clave de administración", type="password", key="admin_password_input"
    )
    if st.button("Ingresar al área administrativa", key="admin_login"):
        if hmac.compare_digest(clave_ingresada, clave_configurada):
            st.session_state["admin_autenticado"] = True
            st.rerun()
        st.error("Clave incorrecta.")
    return False


def definir_periodo_admin(periodo: str) -> None:
    """Carga un período sugerido en los controles sin publicar nada."""
    normalizado = normalizar_periodo(periodo)
    if normalizado is None:
        return
    st.session_state["admin_anio"] = int(normalizado[:4])
    st.session_state["admin_trimestre"] = int(normalizado[-1])


def mostrar_reporte_prevalidacion(reporte: dict) -> None:
    """Renderiza un reporte del monitor en lenguaje operativo."""
    st.subheader(f"Prevalidación {reporte.get('periodo', '')}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Estado", str(reporte.get("estado_prevalidacion", "Sin estado")))
    c2.metric(
        "Período anterior",
        str(reporte.get("comparacion_historica", {}).get("periodo_anterior") or "No disponible"),
    )
    alertas = reporte.get("comparacion_historica", {}).get("alertas", [])
    c3.metric("Alertas orientativas", len(alertas))

    validacion = reporte.get("validacion_critica", {})
    controles = validacion.get("controles", [])
    if controles:
        st.markdown("**Controles críticos**")
        st.dataframe(pd.DataFrame(controles), width="stretch", hide_index=True)

    variaciones = reporte.get("comparacion_historica", {}).get("variaciones", {})
    if variaciones:
        filas = []
        for variable, datos in variaciones.items():
            fila = {"variable": variable, **datos}
            filas.append(fila)
        st.markdown("**Comparación con el histórico**")
        st.dataframe(pd.DataFrame(filas), width="stretch", hide_index=True)

    if alertas:
        st.warning(
            "Se detectaron variaciones que merecen revisión. Son alertas operativas; "
            "no constituyen pruebas de significancia estadística."
        )
        st.dataframe(pd.DataFrame(alertas), width="stretch", hide_index=True)
    else:
        st.success("No se detectaron alertas por encima de los umbrales operativos.")


DIR_ACTIVO, USANDO_SNAPSHOT, DESCRIPCION_FUENTE = seleccionar_fuente()

st.title("Mercado laboral en Santiago del Estero - La Banda")
st.markdown("**Fuente:** Encuesta Permanente de Hogares — INDEC.")
st.markdown("**Alcance territorial:** Aglomerado 18 — Santiago del Estero - La Banda.")
st.caption(
    "Los datos públicos son producidos por el INDEC. Los indicadores son calculados por "
    "este pipeline mediante PONDERA; no constituyen una nueva estadística oficial provincial."
)

if DIR_ACTIVO is None:
    st.error(
        "No hay un histórico acompañado por estados de validación. Se conserva cualquier "
        "archivo existente, pero no se lo muestra hasta que supere los controles críticos."
    )
    st.stop()

if USANDO_SNAPSHOT:
    st.info(
        "El tablero está usando el snapshot agregado y validado. No necesita ZIP ni "
        "microdatos individuales para funcionar."
    )
else:
    st.success("El tablero está usando resultados locales validados.")

historico = leer_csv(DIR_ACTIVO / "historico_SDE.csv")
estados = leer_csv(DIR_ACTIVO / "estado_periodos.csv")
meta_historico = leer_json(DIR_ACTIVO / "historico_SDE.meta.json") or {}

if historico is None or historico.empty or estados is None:
    st.error("Los archivos validados no pudieron leerse. Se requiere revisar el snapshot.")
    st.stop()

historico["periodo"] = historico["periodo"].map(normalizar_periodo)
estados["periodo"] = estados["periodo"].map(normalizar_periodo)
estados["estado"] = estados["estado"].map(normalizar_estado)
if historico["periodo"].isna().any() or estados["periodo"].isna().any():
    st.error("Hay períodos fuera del formato canónico YYYYTx en los archivos del dashboard.")
    st.stop()

periodos_validos = set(
    estados.loc[estados["estado"].isin(ESTADOS_VALIDOS), "periodo"]
)
df = historico[historico["periodo"].isin(periodos_validos)].copy()
df = df.sort_values(["anio", "trimestre"]).reset_index(drop=True)
if df.empty:
    st.error("No hay períodos con estado VALIDADO o PUBLICADO.")
    st.stop()

ultimo = df.iloc[-1]
periodo_ultimo = str(ultimo["periodo"])
estado_ultimo = estados.loc[estados["periodo"].astype(str) == periodo_ultimo].iloc[-1]

(
    tab_resumen,
    tab_evolucion,
    tab_ingresos,
    tab_calendario,
    tab_calidad,
    tab_documentacion,
    tab_admin,
) = st.tabs([
    "Resumen ejecutivo",
    "Evolución laboral",
    "Ingresos",
    "Calendario",
    "Calidad y auditoría",
    "Documentación y descargas",
    "Administración",
])


with tab_resumen:
    st.header("Resumen ejecutivo")
    a, b, c = st.columns(3)
    a.metric("Último período validado", periodo_ultimo)
    b.metric("Estado de validación", str(estado_ultimo["estado"]))
    b.caption(str(estado_ultimo.get("mensaje", "Sin mensaje adicional")))
    c.metric(
        "Fecha de actualización",
        str(meta_historico.get("ultima_ejecucion_exitosa")
            or meta_historico.get("fecha_hora_generacion") or "No disponible"),
    )

    st.subheader("Indicadores principales")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tasa de actividad oficial", formato_tasa(ultimo.get("tasa_actividad_oficial")))
    c2.metric("Tasa de empleo oficial", formato_tasa(ultimo.get("tasa_empleo_oficial")))
    c3.metric("Tasa de desocupación", formato_tasa(ultimo.get("tasa_desocupacion")))
    c4.metric("Proporción inactiva total", formato_tasa(ultimo.get("proporcion_inactiva_total")))
    st.caption(
        "La proporción inactiva total es complementaria: 100 menos la tasa de actividad oficial."
    )

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Personas en muestra", formato_numero(ultimo.get("n_personas_muestra")))
    c6.metric("Hogares en muestra", formato_numero(ultimo.get("n_hogares_muestra")))
    c7.metric("Población total expandida", formato_numero(ultimo.get("poblacion_expandida_total")))
    c8.metric("Tasa de informalidad", formato_tasa(ultimo.get("tasa_informalidad")))
    if pd.isna(ultimo.get("tasa_informalidad")):
        st.warning("La informalidad no está disponible porque la variable EMPLEO no existe en ese período.")
    st.info(
        "Advertencia territorial: los microdatos públicos identifican el aglomerado conjunto y "
        "no permiten separar Santiago Capital de La Banda."
    )


with tab_evolucion:
    st.header("Evolución laboral")
    st.subheader("Actividad y empleo oficiales")
    columnas_conjuntas = [
        col for col in ["tasa_actividad_oficial", "tasa_empleo_oficial"] if col in df.columns
    ]
    if columnas_conjuntas:
        st.line_chart(df.set_index("periodo")[columnas_conjuntas])
    else:
        st.info("Las tasas oficiales todavía no están disponibles.")

    izquierda, derecha = st.columns(2)
    with izquierda:
        st.subheader("Desocupación")
        if "tasa_desocupacion" in df.columns:
            st.line_chart(df.set_index("periodo")[["tasa_desocupacion"]])
        else:
            st.info("La tasa de desocupación no está disponible.")
    with derecha:
        st.subheader("Proporción inactiva total")
        if "proporcion_inactiva_total" in df.columns:
            st.line_chart(df.set_index("periodo")[["proporcion_inactiva_total"]])
        else:
            st.info("El indicador complementario no está disponible.")

    st.subheader("Informalidad")
    informalidad = df[["periodo", "tasa_informalidad"]].dropna() if "tasa_informalidad" in df else pd.DataFrame()
    if len(informalidad) >= 2:
        st.line_chart(informalidad.set_index("periodo"))
    else:
        st.info("No hay suficientes períodos con EMPLEO disponible para mostrar una evolución.")
    st.caption(
        "En 2023T1, 2023T2 y 2023T3, la variable necesaria para estimar informalidad "
        "no está disponible. Por ese motivo, el indicador se presenta como no disponible "
        "y no se realiza imputación ni se reemplazan faltantes por cero."
    )


with tab_ingresos:
    st.header("Ingresos nominales")
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Ingreso promedio ponderado",
        formato_numero(ultimo.get("ingreso_promedio_ponderado_observado"), prefijo="$"),
    )
    c2.metric(
        "Ingreso mediano",
        formato_numero(ultimo.get("ingreso_mediano_observado"), prefijo="$"),
    )
    c3.metric(
        "No respuesta de ingresos",
        formato_tasa(ultimo.get("tasa_no_respuesta_ingresos_ocupados")),
    )
    st.warning(
        "Los ingresos son nominales y no representan directamente variaciones del poder "
        "adquisitivo. Para comparaciones reales se requiere deflactación."
    )
    columnas_ingresos = [
        col for col in [
            "ingreso_promedio_ponderado_observado", "ingreso_mediano_observado"
        ] if col in df.columns
    ]
    if columnas_ingresos:
        st.line_chart(df.set_index("periodo")[columnas_ingresos])
    else:
        st.info("No hay una serie de ingresos disponible.")


with tab_calendario:
    st.header("Calendario de publicaciones EPH")
    st.caption(
        "Reutiliza el mismo calendario operativo del pipeline. El estado indica si el período "
        "ya fue validado/publicado localmente o si todavía está pendiente/futuro."
    )
    calendario = portal_admin.construir_calendario(DIR_ACTIVO)
    resumen_cal = portal_admin.resumen_calendario(calendario)
    c1, c2, c3 = st.columns(3)
    c1.metric("Último período validado", periodo_ultimo)
    pendiente = resumen_cal.get("pendiente")
    proxima = resumen_cal.get("proxima_publicacion")
    c2.metric(
        "Pendiente de incorporación",
        pendiente["periodo"] if pendiente else "Ninguno",
        pendiente["publicacion_estimada"] if pendiente else None,
    )
    c3.metric(
        "Próxima publicación esperada",
        proxima["periodo"] if proxima else "Sin fecha futura",
        proxima["publicacion_estimada"] if proxima else None,
    )

    visibles = calendario[
        calendario["periodo"].str[:4].astype(int) >= max(2023, int(periodo_ultimo[:4]) - 1)
    ].copy()
    st.dataframe(
        visibles[["periodo", "publicacion_estimada", "estado"]],
        width="stretch",
        hide_index=True,
    )
    st.info(
        "El calendario indica cuándo corresponde esperar cada publicación. El monitor del área "
        "administrativa verifica después si el ZIP oficial está efectivamente disponible en INDEC."
    )


with tab_calidad:
    st.header("Calidad y auditoría")
    validados = int(estados["estado"].isin(ESTADOS_VALIDOS).sum())
    advertencias = 0
    for periodo in df["periodo"].astype(str):
        esquema_periodo = leer_json(DIR_ACTIVO / f"validacion_esquema_{periodo}.json") or {}
        if any(
            resultado.get("nivel") == "advertencia"
            for resultado in esquema_periodo.values()
            if isinstance(resultado, dict)
        ):
            advertencias += 1
    c1, c2, c3 = st.columns(3)
    c1.metric("Períodos validados", validados)
    c2.metric("Períodos con advertencias", advertencias)
    c3.metric("Última ejecución", str(estado_ultimo["estado"]))

    st.subheader("Estado de períodos")
    st.dataframe(estados, width="stretch", hide_index=True)

    periodo_seleccionado = st.selectbox(
        "Período a auditar", df["periodo"].astype(str).tolist(), index=len(df) - 1
    )
    fila_periodo = df[df["periodo"].astype(str) == periodo_seleccionado].iloc[-1]
    r1, r2, r3 = st.columns(3)
    r1.metric("Personas en muestra", formato_numero(fila_periodo.get("n_personas_muestra")))
    r2.metric("Hogares en muestra", formato_numero(fila_periodo.get("n_hogares_muestra")))
    r3.metric(
        "Población expandida", formato_numero(fila_periodo.get("poblacion_expandida_total"))
    )
    izquierda, derecha = st.columns(2)
    with izquierda:
        st.subheader("Variables, nulos y códigos especiales")
        calidad = leer_csv(DIR_ACTIVO / f"calidad_datos_SDE_{periodo_seleccionado}.csv")
        if calidad is not None and not calidad.empty:
            st.dataframe(calidad, width="stretch", hide_index=True)
        else:
            calidad_agregada = leer_csv(DIR_ACTIVO / "calidad_snapshot_SDE.csv")
            if calidad_agregada is not None:
                fila_calidad = calidad_agregada[
                    calidad_agregada["periodo"].astype(str) == periodo_seleccionado
                ]
                st.dataframe(fila_calidad, width="stretch", hide_index=True)
                st.caption(
                    "Control agregado del snapshot. Los conteos de nulos y códigos especiales por "
                    "variable requieren regenerar el período desde los microdatos."
                )
            else:
                st.info("No hay un reporte de calidad disponible para este período.")
    with derecha:
        st.subheader("Cambios de esquema")
        esquema = leer_json(DIR_ACTIVO / f"validacion_esquema_{periodo_seleccionado}.json")
        if esquema:
            for base in ["individual", "hogar"]:
                resultado = esquema.get(base, {})
                st.write(f"**Base {base}:** {resultado.get('nivel', 'sin estado')}")
                faltantes = resultado.get("obligatorias_faltantes", [])
                opcionales = resultado.get("opcionales_faltantes", [])
                st.caption(
                    f"Obligatorias faltantes: {faltantes or 'ninguna'} · "
                    f"Opcionales faltantes: {opcionales or 'ninguna'}"
                )
        else:
            st.info("No hay validación de esquema disponible para este período.")

    st.subheader("Validaciones lógicas")
    validacion_publicacion = leer_json(
        DIR_ACTIVO / f"validacion_publicacion_{periodo_seleccionado}.json"
    )
    if validacion_publicacion and validacion_publicacion.get("controles"):
        st.dataframe(
            pd.DataFrame(validacion_publicacion["controles"]),
            width="stretch",
            hide_index=True,
        )
    else:
        fila = df[df["periodo"].astype(str) == periodo_seleccionado].iloc[-1]
        chequeos = pd.DataFrame([
            {"control": "población total positiva", "cumple": fila["poblacion_expandida_total"] > 0},
            {"control": "tasas oficiales entre 0 y 100", "cumple": all(
                0 <= float(fila[col]) <= 100
                for col in ["tasa_actividad_oficial", "tasa_empleo_oficial", "tasa_desocupacion"]
            )},
            {"control": "actividad + proporción inactiva = 100", "cumple": abs(
                float(fila["tasa_actividad_oficial"])
                + float(fila["proporcion_inactiva_total"]) - 100
            ) <= 0.02},
        ])
        st.dataframe(chequeos, width="stretch", hide_index=True)

    boton_descarga(
        DIR_ACTIVO / f"indicadores_SDE_{periodo_seleccionado}.meta.json",
        "Descargar metadatos del período",
        f"meta_auditoria_{periodo_seleccionado}",
    )


with tab_documentacion:
    st.header("Documentación y descargas")
    st.caption(f"Fuente activa: {DESCRIPCION_FUENTE}.")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Datos agregados")
        boton_descarga(DIR_ACTIVO / "historico_SDE.csv", "Descargar histórico", "dl_hist")
        boton_descarga(
            DIR_ACTIVO / f"indicadores_SDE_{periodo_ultimo}.csv",
            f"Descargar indicadores {periodo_ultimo}",
            "dl_ind",
        )
        boton_descarga(
            DIR_ACTIVO / f"calidad_datos_SDE_{periodo_ultimo}.csv",
            f"Descargar calidad {periodo_ultimo}",
            "dl_cal",
        )
        boton_descarga(DIR_ACTIVO / "estado_periodos.csv", "Descargar estado de períodos", "dl_estado")
    with c2:
        st.subheader("Metadatos y manifiesto")
        boton_descarga(
            DIR_ACTIVO / "historico_SDE.meta.json",
            "Descargar metadatos del histórico",
            "dl_meta_hist",
        )
        boton_descarga(
            DIR_ACTIVO / "manifest_salidas.json",
            "Descargar manifiesto de salidas",
            "dl_manifest",
        )
        boton_descarga(
            DIR_ACTIVO / f"validacion_esquema_{periodo_ultimo}.json",
            "Descargar validación de esquema",
            "dl_esquema",
        )

    st.subheader("Guías")
    for nombre, etiqueta in [
        ("DICCIONARIO_DATOS.md", "Diccionario de datos"),
        ("GUIA_USO.md", "Guía de uso"),
        ("METODOLOGIA.md", "Metodología"),
        ("MONITOR_ACTUALIZACIONES.md", "Monitor de actualizaciones"),
        ("PORTAL_ADMINISTRACION.md", "Portal y administración"),
    ]:
        ruta = DIR_ACTIVO / nombre
        if not ruta.exists():
            ruta = DIR_DOCS / nombre
        boton_descarga(ruta, f"Descargar {etiqueta}", f"doc_{nombre}")

    st.info(
        "Los posibles indicadores operativos futuros requieren bases internas y una "
        "definición institucional previa. No se derivan de los microdatos públicos."
    )


with tab_admin:
    st.header("Administración del Pipeline EPH")
    st.caption(
        "Área para operadores autorizados. Consulta INDEC, prevalida períodos y, sólo con "
        "confirmación explícita, incorpora un trimestre al histórico."
    )

    if administrador_autenticado():
        escrituras_habilitadas = _config_bool(
            "admin_enable_writes", "EPH_ADMIN_ENABLE_WRITES", default=False
        )
        if escrituras_habilitadas:
            st.success("Modo de incorporación habilitado para esta instalación.")
        else:
            st.info(
                "Monitor y prevalidación habilitados. La incorporación final está bloqueada "
                "hasta configurar `admin_enable_writes=true` o `EPH_ADMIN_ENABLE_WRITES=1`."
            )

        st.subheader("1. Buscar nuevas publicaciones")
        if st.button("Consultar INDEC ahora", key="admin_monitor", type="primary"):
            with st.spinner("Consultando disponibilidad de nuevas publicaciones..."):
                consulta = monitor.detectar_nuevas_publicaciones()
                try:
                    monitor.guardar_consulta_monitor(consulta)
                except OSError:
                    pass
                st.session_state["consulta_monitor"] = consulta

        consulta = st.session_state.get("consulta_monitor")
        if consulta:
            m1, m2, m3 = st.columns(3)
            m1.metric("Último período local", consulta.get("ultimo_periodo_local", ""))
            m2.metric(
                "Nuevas publicaciones", len(consulta.get("nuevas_publicaciones", []))
            )
            m3.metric("Estado del monitor", consulta.get("estado_monitor", ""))
            items = consulta.get("periodos_consultados", [])
            if items:
                st.dataframe(
                    pd.DataFrame(items)[
                        ["periodo", "estado_consulta", "estado_http", "detalle"]
                    ],
                    width="stretch",
                    hide_index=True,
                )
            if consulta.get("errores_consulta"):
                st.warning(
                    "Hubo errores de conectividad. No se interpreta un error de consulta como "
                    "ausencia de una publicación."
                )

        st.subheader("2. Prevalidar un trimestre")
        nuevas = [] if not consulta else [
            x["periodo"] for x in consulta.get("nuevas_publicaciones", [])
        ]
        col_a, col_b = st.columns(2)
        with col_a:
            anio_objetivo = st.number_input(
                "Año", min_value=2023, max_value=2100, value=2026, step=1, key="admin_anio"
            )
        with col_b:
            trimestre_objetivo = st.selectbox(
                "Trimestre", core.TRIMESTRES, key="admin_trimestre"
            )
        if nuevas:
            sugerido = nuevas[0]
            st.info(f"El monitor detectó como primer período nuevo disponible: **{sugerido}**.")
            st.button(
                f"Usar {sugerido}",
                key="usar_sugerido",
                on_click=definir_periodo_admin,
                args=(sugerido,),
            )

        periodo_objetivo = monitor.Periodo(int(anio_objetivo), int(trimestre_objetivo))
        forzar_pre = st.checkbox("Forzar redescarga del ZIP", key="admin_forzar_pre")
        if st.button(
            f"Prevalidar {periodo_objetivo.codigo}", key="admin_prevalidar"
        ):
            with st.spinner(
                f"Descargando y prevalidando {periodo_objetivo.codigo} sin publicar..."
            ):
                try:
                    reporte = monitor.prevalidar_periodo(
                        periodo_objetivo, forzar_descarga=forzar_pre
                    )
                    st.session_state["reporte_prevalidacion"] = reporte
                    st.success(
                        f"Prevalidación terminada: {reporte['estado_prevalidacion']}."
                    )
                except Exception as error:
                    st.error(f"No se pudo completar la prevalidación: {error}")

        prevalidaciones = portal_admin.listar_prevalidaciones()
        if not prevalidaciones.empty:
            st.caption("Prevalidaciones guardadas en esta instalación")
            st.dataframe(
                prevalidaciones[
                    ["periodo", "estado_prevalidacion", "fecha_prevalidacion", "n_alertas"]
                ],
                width="stretch",
                hide_index=True,
            )
            opciones = prevalidaciones["periodo"].tolist()
            elegido = st.selectbox(
                "Abrir reporte", opciones, index=len(opciones) - 1, key="admin_reporte_select"
            )
            if st.button("Cargar reporte", key="admin_cargar_reporte"):
                try:
                    st.session_state["reporte_prevalidacion"] = (
                        portal_admin.cargar_prevalidacion(elegido)
                    )
                except Exception as error:
                    st.error(str(error))

        reporte_activo = st.session_state.get("reporte_prevalidacion")
        if reporte_activo:
            mostrar_reporte_prevalidacion(reporte_activo)

            st.subheader("3. Incorporar al histórico")
            periodo_publicar = str(reporte_activo.get("periodo", ""))
            if reporte_activo.get("estado_prevalidacion") != "LISTO_PARA_REVISION":
                st.error(
                    "Este reporte no está listo para revisión final. La incorporación permanece bloqueada."
                )
            elif not escrituras_habilitadas:
                st.warning(
                    "La prevalidación está lista, pero esta instalación está configurada en modo "
                    "seguro sin escrituras finales."
                )
            else:
                st.warning(
                    "Esta acción ejecuta nuevamente el pipeline completo, actualiza `results/` y, "
                    "si todos los controles vuelven a aprobarse, actualiza el snapshot."
                )
                revisado = st.checkbox(
                    "Confirmo que revisé los controles, alertas y metodología del período.",
                    key="admin_revisado",
                )
                confirmacion = st.text_input(
                    f"Escriba {periodo_publicar} para confirmar", key="admin_confirmacion"
                )
                if st.button(
                    f"Incorporar {periodo_publicar} y actualizar snapshot",
                    key="admin_publicar",
                    disabled=not revisado,
                    type="primary",
                ):
                    with st.spinner("Ejecutando validación final y publicación transaccional..."):
                        try:
                            resultado = portal_admin.publicar_periodo_asistido(
                                periodo_publicar,
                                confirmacion=confirmacion,
                                publicar_snapshot=True,
                            )
                            st.success(
                                f"{resultado['periodo']} incorporado correctamente. "
                                "El snapshot fue actualizado."
                            )
                            st.session_state.pop("reporte_prevalidacion", None)
                            st.session_state.pop("consulta_monitor", None)
                            st.rerun()
                        except Exception as error:
                            st.error(
                                f"La incorporación no se completó y se conserva el último estado válido: {error}"
                            )

        st.caption(
            "En Streamlit Cloud el sistema de archivos puede ser efímero. Para uso institucional "
            "persistente, la incorporación debe ejecutarse en infraestructura de la Dirección o "
            "sobre un almacenamiento persistente."
        )


st.divider()
st.caption(
    "Práctica Profesionalizante II · ITSE 2026 · "
    "Achaval · Cabaña · Constantinidi · Gomez · Pinto Villegas"
)
