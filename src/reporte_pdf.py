"""Generación de reportes PDF estáticos para el portal EPH.

El reporte resume un período validado del Aglomerado 18 a partir de salidas
agregadas del pipeline. No recalcula indicadores ni reemplaza las validaciones
estadísticas: consume el histórico y, cuando está disponible, el análisis
segmentado ya generado por el ETL.
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Iterable

import matplotlib

# Backend no interactivo para generar gráficos dentro del PDF.
# Evita depender de Tkinter/Tk en Windows y servidores.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from interpretacion_brechas import lectura_deciles, lectura_dimension


AZUL = colors.HexColor("#17365D")
AZUL_CLARO = colors.HexColor("#DCE6F1")
GRIS = colors.HexColor("#5B6573")
GRIS_CLARO = colors.HexColor("#F3F5F7")
BORDE = colors.HexColor("#D7DCE2")

ETIQUETAS = {
    "tasa_actividad_oficial": "Actividad",
    "tasa_empleo_oficial": "Empleo",
    "tasa_desocupacion": "Desocupación",
    "proporcion_inactiva_total": "Inactividad total",
    "tasa_informalidad": "Informalidad",
    "ingreso_promedio_ponderado_observado": "Ingreso promedio ponderado",
    "ingreso_mediano_observado": "Ingreso mediano",
}


def _numero(valor: object, decimales: int = 0, prefijo: str = "") -> str:
    if valor is None or pd.isna(valor):
        return "No disponible"
    texto = f"{float(valor):,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{prefijo}{texto}"


def _tasa(valor: object) -> str:
    return "No disponible" if valor is None or pd.isna(valor) else f"{float(valor):.2f}%"


def _delta(actual: object, comparacion: object) -> str:
    if actual is None or comparacion is None or pd.isna(actual) or pd.isna(comparacion):
        return "No disponible"
    return f"{float(actual) - float(comparacion):+.2f} p.p."


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TituloEPH",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=AZUL,
        alignment=TA_LEFT,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="SubtituloEPH",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=AZUL,
        spaceBefore=8,
        spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="TextoEPH",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=13,
        textColor=colors.HexColor("#28323C"),
        spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="NotaEPH",
        parent=styles["BodyText"],
        fontName="Helvetica-Oblique",
        fontSize=8.2,
        leading=11,
        textColor=GRIS,
        spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="CentroEPH",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
    ))
    return styles


def _table(data: list[list[object]], widths=None, header: bool = True, font_size: float = 8.0) -> Table:
    tabla = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    estilo = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.35, BORDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        estilo.extend([
            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
        if len(data) > 1:
            estilo.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLARO]))
    tabla.setStyle(TableStyle(estilo))
    return tabla


def _fig_to_image(fig, width: float = 17.2 * cm) -> Image:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    imagen = Image(buffer, width=width)
    ratio = imagen.imageHeight / imagen.imageWidth if imagen.imageWidth else 0.55
    imagen.drawHeight = width * ratio
    imagen._eph_buffer = buffer  # mantener vivo el BytesIO hasta construir el PDF
    return imagen


def _grafico_series(datos: pd.DataFrame, columnas: Iterable[str], titulo: str, ylabel: str) -> Image | None:
    columnas = [c for c in columnas if c in datos.columns]
    if datos.empty or not columnas:
        return None
    fig, ax = plt.subplots(figsize=(8.4, 3.25))
    hay_datos = False
    for col in columnas:
        serie = pd.to_numeric(datos[col], errors="coerce")
        if serie.notna().any():
            ax.plot(datos["periodo"].astype(str), serie, marker="o", linewidth=1.7, label=ETIQUETAS.get(col, col))
            hay_datos = True
    if not hay_datos:
        plt.close(fig)
        return None
    ax.set_title(titulo)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=45)
    ax.legend(frameon=False, ncol=max(1, min(len(columnas), 3)))
    fig.tight_layout()
    return _fig_to_image(fig)


def _grafico_segmentado(vista: pd.DataFrame, dimension: str) -> Image | None:
    if vista.empty:
        return None
    if dimension == "Decil de ingreso":
        col = "ingreso_promedio_ponderado_ocupados"
        if col not in vista.columns:
            return None
        datos = vista[["categoria", col]].copy()
        datos[col] = pd.to_numeric(datos[col], errors="coerce")
        datos["orden"] = pd.to_numeric(datos["categoria"].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
        datos = datos.dropna().sort_values("orden")
        if datos.empty:
            return None
        fig, ax = plt.subplots(figsize=(8.4, 3.0))
        ax.bar(datos["categoria"].astype(str), datos[col])
        ax.set_title("Ingreso medio de la ocupación principal por decil")
        ax.set_ylabel("Pesos corrientes")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", alpha=0.2)
        fig.tight_layout()
        return _fig_to_image(fig)

    col = "tasa_actividad"
    if col not in vista.columns:
        return None
    datos = vista[["categoria", col]].copy()
    datos[col] = pd.to_numeric(datos[col], errors="coerce")
    datos = datos.dropna()
    if datos.empty:
        return None
    fig, ax = plt.subplots(figsize=(8.4, 3.0))
    posiciones = list(range(len(datos)))
    ax.scatter(posiciones, datos[col], s=50)
    for x, y in zip(posiciones, datos[col]):
        ax.vlines(x, ymin=max(0, float(datos[col].min()) - 5), ymax=y, linewidth=1, alpha=0.45)
    ax.set_xticks(posiciones)
    ax.set_xticklabels(datos["categoria"].astype(str), rotation=25, ha="right")
    ax.set_title(f"Tasa de actividad por {dimension.lower()}")
    ax.set_ylabel("Porcentaje")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    return _fig_to_image(fig)


def _footer(canvas, doc):
    canvas.saveState()
    ancho, _ = A4
    canvas.setStrokeColor(BORDE)
    canvas.line(1.4 * cm, 1.05 * cm, ancho - 1.4 * cm, 1.05 * cm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRIS)
    canvas.drawString(1.4 * cm, 0.68 * cm, "Pipeline EPH · DGEyC Santiago del Estero · Aglomerado 18")
    canvas.drawRightString(ancho - 1.4 * cm, 0.68 * cm, f"Página {doc.page}")
    canvas.restoreState()


def generar_reporte_pdf(
    historico: pd.DataFrame,
    periodo: str,
    *,
    periodo_comparacion: str | None = None,
    segmentado: pd.DataFrame | None = None,
    fuente_descripcion: str = "Resultados validados",
) -> bytes:
    """Genera un PDF ejecutivo del período solicitado y devuelve sus bytes."""
    if historico is None or historico.empty:
        raise ValueError("El histórico está vacío.")
    if "periodo" not in historico.columns:
        raise ValueError("El histórico no contiene la columna periodo.")

    hist = historico.copy()
    hist["periodo"] = hist["periodo"].astype(str)
    fila = hist.loc[hist["periodo"] == str(periodo)]
    if fila.empty:
        raise ValueError(f"El período {periodo} no existe en el histórico.")
    fila = fila.iloc[-1]

    comp = None
    if periodo_comparacion:
        candidato = hist.loc[hist["periodo"] == str(periodo_comparacion)]
        if not candidato.empty:
            comp = candidato.iloc[-1]
    if comp is None:
        pos = hist.index[hist["periodo"] == str(periodo)].tolist()[-1]
        posiciones = hist.index.tolist()
        idx_lista = posiciones.index(pos)
        if idx_lista > 0:
            comp = hist.loc[posiciones[idx_lista - 1]]
            periodo_comparacion = str(comp["periodo"])

    styles = _styles()
    salida = BytesIO()
    doc = SimpleDocTemplate(
        salida,
        pagesize=A4,
        rightMargin=1.45 * cm,
        leftMargin=1.45 * cm,
        topMargin=1.45 * cm,
        bottomMargin=1.35 * cm,
        title=f"Reporte EPH {periodo}",
        author="Pipeline EPH · DGEyC Santiago del Estero",
    )
    story = []

    story.append(Paragraph("Reporte ejecutivo EPH", styles["TituloEPH"]))
    story.append(Paragraph(
        f"Aglomerado 18 - Santiago del Estero - La Banda · Período <b>{periodo}</b>",
        styles["SubtituloEPH"],
    ))
    story.append(Paragraph(
        "Reporte estático generado desde salidas agregadas validadas del Pipeline EPH. "
        "Su objetivo es facilitar la consulta y circulación institucional sin reemplazar el histórico, "
        "los metadatos ni los controles del pipeline.",
        styles["TextoEPH"],
    ))
    story.append(Paragraph(
        f"Fuente activa: {fuente_descripcion}. Generado: {datetime.now():%d/%m/%Y %H:%M}.",
        styles["NotaEPH"],
    ))
    story.append(Spacer(1, 0.12 * cm))

    story.append(Paragraph("1. Indicadores principales", styles["SubtituloEPH"]))
    resumen = [
        ["Indicador", str(periodo), f"Variación vs {periodo_comparacion or 'período anterior'}"],
    ]
    for columna in ["tasa_actividad_oficial", "tasa_empleo_oficial", "tasa_desocupacion", "proporcion_inactiva_total", "tasa_informalidad"]:
        actual = fila.get(columna)
        anterior = None if comp is None else comp.get(columna)
        resumen.append([ETIQUETAS.get(columna, columna), _tasa(actual), _delta(actual, anterior)])
    story.append(_table(resumen, widths=[7.1 * cm, 4.0 * cm, 5.7 * cm], font_size=8.4))
    story.append(Spacer(1, 0.22 * cm))

    muestra = [
        ["Personas en muestra", _numero(fila.get("n_personas_muestra")), "Población expandida", _numero(fila.get("poblacion_expandida_total"))],
        ["Hogares en muestra", _numero(fila.get("n_hogares_muestra")), "PEA expandida", _numero(fila.get("pea_expandida"))],
    ]
    story.append(_table(muestra, widths=[4.0 * cm, 3.2 * cm, 4.2 * cm, 5.4 * cm], header=False, font_size=8.2))
    story.append(Spacer(1, 0.22 * cm))
    story.append(Paragraph(
        "Las variaciones se expresan en puntos porcentuales y son descriptivas. La EPH es una encuesta por muestreo; "
        "este reporte no presenta pruebas de significancia estadística ni atribuye causalidad.",
        styles["NotaEPH"],
    ))

    story.append(Paragraph("2. Evolución reciente", styles["SubtituloEPH"]))
    hist_ordenado = hist.copy()
    if {"anio", "trimestre"}.issubset(hist_ordenado.columns):
        hist_ordenado = hist_ordenado.sort_values(["anio", "trimestre"])
    hasta = hist_ordenado.index[hist_ordenado["periodo"] == str(periodo)].tolist()[-1]
    posiciones = hist_ordenado.index.tolist()
    pos = posiciones.index(hasta)
    recientes = hist_ordenado.loc[posiciones[max(0, pos - 7):pos + 1]].copy()

    graf1 = _grafico_series(recientes, ["tasa_actividad_oficial", "tasa_empleo_oficial"], "Actividad y empleo", "Porcentaje")
    if graf1:
        story.append(graf1)
        story.append(Spacer(1, 0.18 * cm))
    graf2 = _grafico_series(recientes, ["tasa_desocupacion"], "Desocupación", "Porcentaje")
    if graf2:
        story.append(graf2)
        story.append(Spacer(1, 0.18 * cm))

    evolucion = [["Período", "Actividad", "Empleo", "Desocupación", "Informalidad"]]
    for _, r in recientes.iterrows():
        evolucion.append([
            str(r.get("periodo", "")), _tasa(r.get("tasa_actividad_oficial")), _tasa(r.get("tasa_empleo_oficial")),
            _tasa(r.get("tasa_desocupacion")), _tasa(r.get("tasa_informalidad")),
        ])
    story.append(_table(evolucion, widths=[3.2 * cm, 3.3 * cm, 3.3 * cm, 3.6 * cm, 3.6 * cm], font_size=7.7))

    story.append(Paragraph("3. Ingresos nominales", styles["SubtituloEPH"]))
    ingresos = [
        ["Indicador", "Valor"],
        ["Ingreso promedio ponderado observado", _numero(fila.get("ingreso_promedio_ponderado_observado"), prefijo="$ ")],
        ["Ingreso mediano observado", _numero(fila.get("ingreso_mediano_observado"), prefijo="$ ")],
        ["No respuesta de ingresos entre ocupados", _tasa(fila.get("tasa_no_respuesta_ingresos_ocupados"))],
    ]
    story.append(_table(ingresos, widths=[10.0 * cm, 6.5 * cm], font_size=8.4))
    story.append(Spacer(1, 0.18 * cm))
    story.append(Paragraph(
        "Los ingresos se expresan en pesos corrientes nominales. No representan directamente variaciones del poder adquisitivo; "
        "para comparaciones reales entre períodos se requiere deflactación.",
        styles["NotaEPH"],
    ))
    graf_ing = _grafico_series(recientes, ["ingreso_promedio_ponderado_observado", "ingreso_mediano_observado"], "Evolución reciente de ingresos observados", "Pesos corrientes")
    if graf_ing:
        story.append(graf_ing)

    story.append(Paragraph("4. Brechas y perfiles", styles["SubtituloEPH"]))
    if segmentado is None or segmentado.empty or "dimension" not in segmentado.columns:
        story.append(Paragraph(
            "No se encontró una salida segmentada agregada para este período en la fuente activa. El reporte conserva los indicadores generales sin fabricar desagregaciones.",
            styles["TextoEPH"],
        ))
    else:
        seg = segmentado.copy()
        for dimension in ["Sexo", "Edad", "Nivel educativo", "Decil de ingreso"]:
            vista = seg.loc[seg["dimension"].astype(str) == dimension].copy()
            if vista.empty:
                continue
            story.append(Paragraph(dimension, styles["SubtituloEPH"]))
            if dimension == "Decil de ingreso":
                vista["_orden"] = pd.to_numeric(vista["categoria"].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
                vista = vista.sort_values("_orden")
                datos = [["Decil", "Muestra", "Población expandida", "Ingreso medio"]]
                for _, r in vista.iterrows():
                    datos.append([
                        str(r.get("categoria", "")), _numero(r.get("n_muestra")), _numero(r.get("poblacion_expandida")),
                        _numero(r.get("ingreso_promedio_ponderado_ocupados"), prefijo="$ "),
                    ])
                story.append(_table(datos, widths=[3.1 * cm, 3.2 * cm, 4.8 * cm, 5.4 * cm], font_size=7.5))
                mensajes = lectura_deciles(vista)
            else:
                datos = [["Categoría", "Muestra", "Actividad", "Empleo", "Desocupación", "Informalidad"]]
                for _, r in vista.iterrows():
                    datos.append([
                        str(r.get("categoria", "")), _numero(r.get("n_muestra")), _tasa(r.get("tasa_actividad")),
                        _tasa(r.get("tasa_empleo")), _tasa(r.get("tasa_desocupacion")), _tasa(r.get("tasa_informalidad")),
                    ])
                story.append(_table(datos, widths=[5.0 * cm, 2.3 * cm, 2.3 * cm, 2.3 * cm, 2.9 * cm, 2.9 * cm], font_size=7.0))
                mensajes = lectura_dimension(vista, dimension, "tasa_actividad")

            graf = _grafico_segmentado(vista, dimension)
            if graf:
                story.append(Spacer(1, 0.12 * cm))
                story.append(graf)
            for mensaje in mensajes[:4]:
                story.append(Paragraph(f"• {mensaje}", styles["TextoEPH"]))
            story.append(Spacer(1, 0.14 * cm))

    story.append(Paragraph("5. Notas metodológicas y de calidad", styles["SubtituloEPH"]))
    notas = [
        "El reporte corresponde al Aglomerado 18, que representa conjuntamente Santiago del Estero y La Banda; los microdatos públicos no permiten separar ambas ciudades.",
        "Las tasas laborales y las expansiones generales usan los ponderadores definidos por el pipeline validado. Los ingresos segmentados utilizan PONDIIO cuando está disponible.",
        "Los deciles de ingreso se basan en ADECOCUR cuando INDEC publica esa variable; no se fabrican deciles alternativos si está ausente.",
        "Los valores faltantes se conservan como no disponibles y no se reemplazan por cero.",
        "Este PDF es una salida de consulta. La fuente de verdad continúa siendo el histórico validado, sus metadatos, el manifiesto y las validaciones del pipeline.",
    ]
    for nota in notas:
        story.append(Paragraph(f"• {nota}", styles["TextoEPH"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return salida.getvalue()
