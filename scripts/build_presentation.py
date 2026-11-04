#!/usr/bin/env python3
"""Genera las gráficas y el PPTX de la exposición de 15 minutos."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_AUTO_SIZE

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "informe" / "img"
OUT = ROOT / "informe" / "presentacion_oee.pptx"

NAVY = RGBColor(0x12, 0x23, 0x9E)
DARK = RGBColor(0x25, 0x24, 0x23)
GRAY = RGBColor(0x60, 0x5E, 0x5C)
LIGHT = RGBColor(0xF3, 0xF2, 0xF1)
BORDER = RGBColor(0xE1, 0xDF, 0xDD)
YELLOW = RGBColor(0xF2, 0xC8, 0x11)
BLUE = RGBColor(0x11, 0x8D, 0xFF)
RED = RGBColor(0xD8, 0x3B, 0x01)
GREEN = RGBColor(0x10, 0x7C, 0x10)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def build_charts():
    # --- OEE por máquina ---
    machines = ["Vinilos_1", "Vinilos_2", "Vinilos_3", "Vinilos_4"]
    oee = [63.0, 33.7, 73.6, 75.5]
    colors = ["#118DFF", "#D83B01", "#107C10", "#F2C811"]
    fig, ax = plt.subplots(figsize=(12.8, 6.4), dpi=200)
    bars = ax.bar(machines, oee, color=colors, width=0.58)
    ax.axhline(75, color="#605E5C", linestyle="--", linewidth=1.5)
    ax.text(-0.45, 77.0, "Meta 75 %", color="#605E5C", fontsize=10, ha="left")
    for b, v in zip(bars, oee):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f} %",
                ha="center", va="bottom", fontsize=14, fontweight="bold", color="#252423")
    ax.set_ylim(0, 100)
    ax.set_ylabel("OEE (%)", fontsize=12)
    fig.suptitle("OEE histórico por máquina", x=0.02, y=0.97, ha="left",
                 fontsize=20, fontweight="bold")
    fig.text(0.02, 0.90, "Calidad = 100 % (supuesto) · cobertura de referencia 52,8 % de las horas",
             fontsize=10.5, color="#605E5C")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#E1DFDD", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=11)
    fig.subplots_adjust(top=0.82, left=0.08, right=0.98, bottom=0.12)
    fig.savefig(IMG / "chart_oee_maquinas.png", facecolor="white")
    plt.close(fig)

    # --- Pareto 2024 ---
    labels = ["16", "5", "6", "7", "12", "9", "17", "10"]
    hours = [1304.4, 860.8, 731.8, 378.4, 128.5, 104.5, 102.5, 95.2]
    total = 3976.0
    cum = []
    acc = 0
    for h in hours:
        acc += h
        cum.append(100 * acc / total)
    fig, ax1 = plt.subplots(figsize=(12.8, 6.4), dpi=200)
    bars = ax1.bar(labels, hours, color=["#F2C811"] * 3 + ["#BFBFBF"] * 5, width=0.62)
    ax1.set_xlabel("Código de paro", fontsize=12)
    ax1.set_ylabel("Horas de paro", fontsize=12)
    fig.suptitle("Pareto de paro 2024", x=0.02, y=0.97, ha="left",
                 fontsize=20, fontweight="bold")
    fig.text(0.02, 0.90, "3 causas = 72,9 % · 4 causas = 82,4 % · solo 1,9 % es falla electromecánica/energía/preventivo",
             fontsize=10.5, color="#605E5C")
    for b, v in zip(bars, hours):
        ax1.text(b.get_x() + b.get_width() / 2, v + 18, f"{v:,.0f}", ha="center",
                 va="bottom", fontsize=10, color="#252423")
    ax2 = ax1.twinx()
    ax2.plot(labels, cum, color="#118DFF", marker="o", linewidth=2.5, markersize=5)
    ax2.axhline(80, color="#605E5C", linestyle="--", linewidth=1.2)
    ax2.text(7.45, 81, "80 %", color="#605E5C", fontsize=10, ha="right")
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("% acumulado", fontsize=12, color="#118DFF")
    ax2.tick_params(axis="y", labelcolor="#118DFF")
    ax1.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    ax1.grid(axis="y", color="#E1DFDD", linewidth=0.8)
    ax1.set_axisbelow(True)
    ax1.tick_params(axis="both", labelsize=11)
    fig.subplots_adjust(top=0.82, left=0.08, right=0.90, bottom=0.12)
    fig.savefig(IMG / "chart_pareto_2024.png", facecolor="white")
    plt.close(fig)

    # Recorte del dashboard para que quepa en una diapositiva 16:9
    im = Image.open(IMG / "grafana_operativo.png")
    im.crop((0, 0, 1440, 1000)).save(IMG / "grafana_operativo_crop.png")


def add_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_text(slide, text, left, top, width, height, size=18, bold=False, italic=False,
             color=DARK, align=PP_ALIGN.LEFT, font="Segoe UI", anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = align
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.italic = italic
    p.font.color.rgb = color
    p.font.name = font
    return box


def add_bullets(slide, items, left, top, width, height, size=18, color=DARK, spacing=8):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = "•  " + item
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.font.name = "Segoe UI"
        p.space_after = Pt(spacing)
    return box


def add_footer(slide, number):
    add_text(slide, "OEE Envasado · Taller 5", 0.45, 7.05, 5.0, 0.3, size=9, color=GRAY)
    add_text(slide, str(number), 12.45, 7.02, 0.45, 0.3, size=9, color=GRAY, align=PP_ALIGN.RIGHT)


def add_title(slide, title, subtitle=None, number=None):
    add_text(slide, title, 0.55, 0.35, 12.2, 0.7, size=28, bold=True, color=DARK)
    if subtitle:
        add_text(slide, subtitle, 0.55, 1.02, 12.2, 0.4, size=13, color=GRAY)
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.55), Inches(1.45), Inches(1.2), Inches(0.06))
    line.fill.solid(); line.fill.fore_color.rgb = YELLOW; line.line.fill.background()
    if number:
        add_footer(slide, number)


def add_card(slide, title, body, left, top, width, height, accent=YELLOW):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid(); shape.fill.fore_color.rgb = LIGHT
    shape.line.color.rgb = BORDER
    shape.line.width = Pt(0.75)
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(0.08), Inches(height))
    bar.fill.solid(); bar.fill.fore_color.rgb = accent; bar.line.fill.background()
    add_text(slide, title, left + 0.18, top + 0.12, width - 0.3, 0.35, size=14, bold=True)
    add_text(slide, body, left + 0.18, top + 0.5, width - 0.3, height - 0.6, size=12, color=GRAY)


def add_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def build_pptx():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    # 1. Portada
    s = prs.slides.add_slide(blank); add_bg(s, NAVY)
    add_text(s, "OEE ENVASADO", 0.8, 1.3, 11.5, 0.6, size=16, bold=True, color=YELLOW)
    add_text(s, "Solución de BI end-to-end\npara líneas de envasado", 0.8, 1.9, 11.5, 1.6,
             size=40, bold=True, color=WHITE)
    add_text(s, "PostgreSQL · Python · Docker · Grafana · Power BI", 0.8, 3.85, 11.5, 0.4,
             size=16, color=RGBColor(0xD9, 0xD9, 0xD9))
    add_text(s, "Integrantes:  [Nombre 1] · [Nombre 2] · [Nombre 3]", 0.8, 4.7, 11.5, 0.4,
             size=14, color=WHITE)
    add_text(s, "Taller 5 · Inteligencia de Negocios · Noviembre 2026", 0.8, 5.15, 11.5, 0.4,
             size=12, color=RGBColor(0xD9, 0xD9, 0xD9))
    add_text(s, "“El Excel cuenta lo que pasó; esta solución explica por qué pasó y avisa cuando está pasando.”",
             0.8, 6.2, 11.8, 0.5, size=12, color=YELLOW)
    add_notes(s, "Buenos días. Soy [nombre] y voy a presentar la solución de BI que construimos para las cuatro líneas de envasado. El problema es simple: hoy la producción y los paros se registran a mano y se consolidan en un Excel con macros. Eso sirve para el comité mensual, pero no para comparar máquinas, turnos y años, ni para reaccionar durante el turno.")

    # 2. Problema
    s = prs.slides.add_slide(blank); add_bg(s, WHITE)
    add_title(s, "El problema: un Excel que llega tarde", "Captura manual → transcripción → comité mensual", 2)
    add_card(s, "1. Captura manual", "Las operarias llenan el formato P-MTO-22 “hora a hora”: producción, código de paro y duración.", 0.55, 1.8, 3.9, 1.7, BLUE)
    add_card(s, "2. Excel con macros", "Mantenimiento transcribe a un libro con macros; de ahí salen tablas dinámicas y gráficos.", 4.7, 1.8, 3.9, 1.7, YELLOW)
    add_card(s, "3. Comité mensual", "El reporte llega semanas después; no hay alerta ni comparación ágil por turno/referencia.", 8.85, 1.8, 3.9, 1.7, RED)
    add_text(s, "Dos dolores", 0.55, 3.9, 4.0, 0.4, size=18, bold=True)
    add_bullets(s, [
        "No hay modelo dimensional: cada pregunta exige rearmar el Excel.",
        "No hay OEE ni componentes: solo horas, producción y % de códigos.",
        "No hay near real-time ni alertas: el supervisor se entera después.",
        "No hay trazabilidad, validaciones ni gobierno del dato.",
    ], 0.55, 4.35, 11.8, 2.2, size=15)
    add_notes(s, "Cada turno las operarias llenan el P-MTO-22. Producción lo envía a mantenimiento y mantenimiento lo transcribe a un Excel con macros. Ese flujo tiene tres consecuencias: el dato llega tarde, el Excel es ancho y manual, y no hay OEE. La empresa necesita dos cosas: análisis de tendencias para la dirección y monitoreo casi en tiempo real para los supervisores.")

    # 3. Dos usuarios
    s = prs.slides.add_slide(blank); add_bg(s, WHITE)
    add_title(s, "Dos usuarios, dos preguntas", "La misma base de datos, dos capas de consumo", 3)
    add_card(s, "Alta dirección / comité", "“¿Cómo evoluciona el OEE? ¿Qué máquina pierde más horas? ¿Dónde invertir?”\n\n→ Tendencias, Pareto, MTBF/MTTR, comparativos anuales.", 0.55, 1.8, 5.9, 2.2, YELLOW)
    add_card(s, "Supervisión / mantenimiento", "“¿Cómo está la línea ahora? ¿Debo intervenir?”\n\n→ Estado por máquina, series de tiempo, alertas.", 6.85, 1.8, 5.9, 2.2, BLUE)
    add_text(s, "Grafana", 0.55, 4.35, 3.0, 0.4, size=20, bold=True, color=BLUE)
    add_text(s, "Near real-time · 10 s · alertas · estado", 0.55, 4.8, 5.8, 0.5, size=14, color=GRAY)
    add_text(s, "Power BI", 6.85, 4.35, 3.0, 0.4, size=20, bold=True, color=YELLOW)
    add_text(s, "Estratégico · mensual · DAX · RLS · narrativa", 6.85, 4.8, 5.8, 0.5, size=14, color=GRAY)
    add_text(s, "No son intercambiables: Grafana no reemplaza el modelo semántico; Power BI no reemplaza las alertas operativas.",
             0.55, 5.75, 12.2, 0.8, size=13, color=GRAY)
    add_notes(s, "La alta dirección pregunta qué pasó y por qué; eso es Power BI. El supervisor pregunta qué está pasando ahora; eso es Grafana. No son intercambiables: Grafana no tiene modelo semántico ni DAX; Power BI no está pensado para refresco subminuto ni alertas de planta.")

    # 4. Fuente y trampas
    s = prs.slides.add_slide(blank); add_bg(s, WHITE)
    add_title(s, "La fuente y sus tres trampas", "8.208 filas · 58 columnas · 2022-01 a 2025-03 · 4 máquinas", 4)
    add_card(s, "Trampa 1: la columna no es el código", "‘Codigo de paro 5 = 40’ significa 40 MINUTOS del código 5. El código está en la posición de la columna.", 0.55, 1.8, 12.2, 1.05, RED)
    add_card(s, "Trampa 2: las filas no son una por producción", "5.157 filas tienen pacas; 3.051 son filas hijas de paro. Una fila de producción puede tener varios paros.", 0.55, 3.0, 12.2, 1.05, YELLOW)
    add_card(s, "Trampa 3: columnas contaminadas", "‘Unidad por display’ a veces contiene el turno (587 filas). ‘Horas no trabajadas’ es un dato de día, no de paro.", 0.55, 4.2, 12.2, 1.05, BLUE)
    add_text(s, "Consecuencia: el ETL despivota los 18 códigos y separa producción de paros. Sin eso, todo el análisis queda mal.",
             0.55, 5.65, 12.2, 0.8, size=13, color=GRAY)
    add_notes(s, "La hoja tiene 8.208 filas y 58 columnas. La primera trampa es la más importante: la columna ‘Codigo de paro N’ no contiene el código, contiene los minutos. La segunda: las filas no son una por producción; hay 3.051 filas hijas de paro. La tercera: ‘Unidad por display’ a veces contiene el turno y ‘Horas no trabajadas’ es un dato de día. Por eso el ETL despivota los códigos y separa producción de paros.")

    # 5. Calidad
    s = prs.slides.add_slide(blank); add_bg(s, WHITE)
    add_title(s, "Diagnóstico de calidad", "Lo que se limpió y lo que se documentó", 5)
    nums = [("42", "duplicados exactos", RED), ("49,7 %", "sin referencia", YELLOW),
            ("51,4 %", "sin turno", YELLOW), ("78,3 %", "sin subcódigo", YELLOW),
            ("0 %", "datos de rechazo", RED)]
    for i, (v, l, c) in enumerate(nums):
        x = 0.55 + i * 2.5
        add_text(s, v, x, 1.9, 2.2, 0.8, size=34, bold=True, color=c, align=PP_ALIGN.CENTER)
        add_text(s, l, x, 2.7, 2.2, 0.5, size=12, color=GRAY, align=PP_ALIGN.CENTER)
    add_bullets(s, [
        "Duplicados: 1.019 pacas, 129 h trabajadas y 18,12 h de paro; se conserva la primera fila.",
        "Sin referencia no hay unidades/paca: el OEE se calcula solo sobre el 52,8 % de las horas.",
        "Sin turno no se imputa: se agrupa en SD. Sin subcódigo se usa SIN_ESP.",
        "La fuente no captura rechazos: Calidad = 100 % y el OEE es un límite superior.",
    ], 0.55, 3.55, 12.2, 2.6, size=14)
    add_notes(s, "Encontramos 42 filas duplicadas exactas: 1.019 pacas, 129 horas y 18,12 horas de paro. El 49,7 % de los registros no tienen referencia; sin referencia no hay rendimiento. El 51,4 % no tiene turno y el 78,3 % de los eventos no tiene subcódigo. Y la limitación más importante: la fuente no captura rechazos, así que la calidad se asume 100 % y el OEE es un límite superior.")

    # 6. Arquitectura
    s = prs.slides.add_slide(blank); add_bg(s, WHITE)
    add_title(s, "Arquitectura de la solución", "Docker Compose · ETL reproducible · auditoría", 6)
    def box(text, x, y, w=2.2, h=1.1, fill=LIGHT, color=DARK):
        sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        sh.fill.solid(); sh.fill.fore_color.rgb = fill; sh.line.color.rgb = BORDER
        tf = sh.text_frame; tf.text = text; tf.word_wrap = True
        for p in tf.paragraphs:
            p.alignment = PP_ALIGN.CENTER; p.font.size = Pt(12); p.font.color.rgb = color; p.font.bold = True
    box("Fuente\n.xlsm + P-MTO-22", 0.7, 2.1, 2.5, 1.2, WHITE, DARK)
    box("ETL Python\nlimpieza + calidad", 3.8, 2.1, 2.5, 1.2, LIGHT, DARK)
    box("PostgreSQL 16\nconstelación + vistas", 6.9, 2.1, 2.5, 1.2, NAVY, WHITE)
    box("Grafana\nnear real-time", 10.0, 1.5, 2.5, 1.0, LIGHT, DARK)
    box("Power BI\nestratégico + RLS", 10.0, 2.8, 2.5, 1.0, LIGHT, DARK)
    for x1, x2 in [(3.2, 3.8), (6.3, 6.9)]:
        arr = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x1), Inches(2.55), Inches(0.5), Inches(0.3))
        arr.fill.solid(); arr.fill.fore_color.rgb = YELLOW; arr.line.fill.background()
    for y in [1.95, 3.25]:
        arr = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(9.4), Inches(y), Inches(0.5), Inches(0.3))
        arr.fill.solid(); arr.fill.fore_color.rgb = YELLOW; arr.line.fill.background()
    add_bullets(s, [
        "Docker Compose: PostgreSQL, Grafana, ETL y simulador.",
        "ETL idempotente: trunca y recarga en una transacción.",
        "Auditoría: etl_run, etl_quality, etl_reconciliacion.",
        "Simulador: 1 minuto cada 2 s para demostrar la alerta.",
    ], 0.7, 4.45, 6.0, 2.2, size=14)
    add_text(s, "PostgreSQL por ventanas, CTE, FILTER y tipos exactos.\nPython por reproducibilidad y pruebas.",
             7.2, 4.45, 5.4, 1.0, size=13, color=GRAY)
    add_notes(s, "La arquitectura tiene cuatro capas: fuente, ETL en Python, PostgreSQL en constelación y consumo con Grafana y Power BI. Todo está contenerizado. Hay un simulador que inserta un minuto cada dos segundos para demostrar que el tablero y la alerta reaccionan. Y una capa de auditoría: cada corrida guarda calidad, conciliación y alertas.")

    # 7. Modelo
    s = prs.slides.add_slide(blank); add_bg(s, WHITE)
    add_title(s, "Modelo dimensional: constelación", "Dos hechos, dimensiones conformadas", 7)
    def dim(text, x, y, w=1.8, h=0.7, fill=LIGHT):
        sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        sh.fill.solid(); sh.fill.fore_color.rgb = fill; sh.line.color.rgb = BORDER
        tf = sh.text_frame; tf.text = text; tf.word_wrap = True
        for p in tf.paragraphs:
            p.alignment = PP_ALIGN.CENTER; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = DARK
    dim("dim_tiempo", 0.7, 1.8); dim("dim_maquina", 2.7, 1.8); dim("dim_turno", 4.7, 1.8)
    dim("dim_referencia", 6.7, 1.8); dim("dim_operario", 8.7, 1.8); dim("dim_codigo_paro", 10.7, 1.8)
    dim("dim_subcodigo_paro", 10.7, 4.9)
    box("fact_produccion\n5.137 registros", 3.0, 3.0, 3.0, 0.95, NAVY, WHITE)
    box("fact_paro\n16.482 eventos", 7.0, 3.0, 3.0, 0.95, NAVY, WHITE)
    add_text(s, "Grano: un registro de producción\n(pacas u horas, tras deduplicar)", 3.0, 4.05, 3.0, 0.6, size=10, color=GRAY)
    add_text(s, "Grano: un evento de paro\n(fila × columna 1..18, minutos > 0)", 7.0, 4.05, 3.0, 0.6, size=10, color=GRAY)
    add_text(s, "Si se unen en una sola tabla, cada paro duplica las pacas/horas. La constelación evita el fan-out.",
             0.7, 5.5, 12.0, 0.5, size=13, color=GRAY)
    add_text(s, "SCD2 en dim_referencia: la conversión unidades/paca se versiona.",
             0.7, 6.05, 12.0, 0.4, size=12, color=GRAY)
    add_notes(s, "El modelo es una constelación. Tenemos dos hechos: fact_produccion, con grano de un registro de producción, 5.137 filas; y fact_paro, con grano de un evento de paro, 16.482 eventos. Si los uniéramos en una tabla, cada paro duplicaría las pacas y horas. Las dimensiones son conformadas. La referencia es SCD Tipo 2 para versionar la conversión unidades/paca.")

    # 8. OEE
    s = prs.slides.add_slide(blank); add_bg(s, NAVY)
    add_text(s, "OEE", 0.8, 0.7, 3.0, 0.5, size=16, bold=True, color=YELLOW)
    add_text(s, "OEE = A × P × Q", 0.8, 1.2, 11.8, 1.0, size=44, bold=True, color=WHITE)
    add_text(s, "Disponibilidad × Rendimiento × Calidad", 0.8, 2.25, 11.8, 0.5, size=16, color=RGBColor(0xD9,0xD9,0xD9))
    add_text(s, "A = (horas trabajadas − horas paro) / horas trabajadas", 0.8, 3.2, 12.0, 0.45, size=18, color=WHITE)
    add_text(s, "P = unidades producidas / (minutos operativos × 72)", 0.8, 3.75, 12.0, 0.45, size=18, color=WHITE)
    add_text(s, "Q = unidades buenas / unidades producidas  →  no disponible: se asume 1,0", 0.8, 4.3, 12.0, 0.45, size=18, color=YELLOW)
    add_text(s, "Paro = suma de los 18 códigos · Unidades = pacas × unidades/paca · 72 u/min = estándar",
             0.8, 5.35, 12.0, 0.4, size=12, color=RGBColor(0xD9,0xD9,0xD9))
    add_text(s, "El 58 % de las observaciones supera 100 % de rendimiento → se aplica tope y se conserva el valor sin tope para diagnosticar.",
             0.8, 5.9, 12.0, 0.6, size=11, color=RGBColor(0xD9,0xD9,0xD9))
    add_notes(s, "OEE es disponibilidad por rendimiento por calidad. Disponibilidad es horas operativas sobre horas trabajadas; las horas operativas son las horas trabajadas menos el paro. Rendimiento es unidades producidas sobre unidades ideales; las unidades ideales son minutos operativos por 72. Calidad sería unidades buenas sobre producidas, pero la fuente no captura rechazos, así que se asume 100 % y el OEE es un límite superior. Además, como las filas hijas de paro no siempre traen referencia, se asigna el paro proporcionalmente por horas trabajadas.")

    # 9. ETL
    s = prs.slides.add_slide(blank); add_bg(s, WHITE)
    add_title(s, "ETL y conciliación", "La prueba de que el dato cargado es el mismo que el Excel", 9)
    rows = [
        ("Filas leídas", "8.208", "8.166 después de dedup", "−42"),
        ("Registros de producción", "5.157", "5.137", "−20"),
        ("Eventos de paro", "16.532", "16.482", "−50"),
        ("Pacas", "378.778", "377.759", "−1.019"),
        ("Horas trabajadas", "38.063,35", "37.934,35", "−129"),
        ("Horas de paro", "8.449,65", "8.431,54", "−18,12"),
    ]
    # tabla simple con shapes
    x0, y0, w = 0.55, 1.85, 12.2
    headers = ["Métrica", "Fuente bruta", "Cargado", "Diferencia"]
    colw = [4.2, 2.6, 2.6, 2.8]
    y = y0
    for j, h in enumerate(headers):
        add_text(s, h, x0 + sum(colw[:j]), y, colw[j], 0.35, size=11, bold=True, color=GRAY)
    y += 0.38
    for r in rows:
        for j, v in enumerate(r):
            add_text(s, v, x0 + sum(colw[:j]), y, colw[j], 0.3, size=11, color=DARK)
        y += 0.38
    add_text(s, "Las diferencias brutas corresponden exactamente a los 42 duplicados. Las métricas críticas fuente dedup vs cargado dan 0.",
             0.55, 4.65, 12.2, 0.5, size=13, color=GRAY)
    add_bullets(s, [
        "25 reglas de calidad en audit.etl_quality.",
        "Conciliación en audit.etl_reconciliacion; si falla, el ETL no carga.",
        "Idempotente: TRUNCATE + INSERT en una transacción.",
    ], 0.55, 5.35, 12.2, 1.4, size=13)
    add_notes(s, "El ETL lee 8.208 filas, detecta 42 duplicados y carga 8.166. De ahí salen 5.137 registros de producción y 16.482 eventos de paro. La conciliación demuestra que después de deduplicar la fuente y la base coinciden en pacas, horas y paro. Las diferencias brutas son exactamente los 42 duplicados. Si una métrica crítica no da cero, el ETL falla.")

    # 10. Resultados
    s = prs.slides.add_slide(blank); add_bg(s, WHITE)
    add_title(s, "Resultados: el promedio esconde la historia", "OEE histórico por máquina · calidad = 100 % (supuesto)", 10)
    s.shapes.add_picture(str(IMG / "chart_oee_maquinas.png"), Inches(0.45), Inches(1.7), width=Inches(8.2))
    add_bullets(s, [
        "Global 70,4 %; 2024 71,0 %; 2025 70,2 %.",
        "V3 y V4 en la meta (73,6 / 75,5 %).",
        "V2 en 33,7 %: rendimiento 55,8 %, MTBF 2,54 h, MTTR 0,84 h.",
        "V1 en 63,0 %: oportunidad de disponibilidad.",
    ], 8.9, 1.9, 4.0, 3.4, size=13)
    add_text(s, "Prioridad: Vinilos_2. No es solo paro; es velocidad y referencia.",
             8.9, 5.45, 4.0, 0.8, size=14, bold=True, color=RED)
    add_notes(s, "El OEE global es 70,4 %. Pero el promedio esconde la historia: Vinilos_3 y Vinilos_4 están en la meta, Vinilos_1 en 63 % y Vinilos_2 en 33,7 %. Vinilos_2 no es solo disponibilidad; su rendimiento es 55,8 %, y tiene el MTBF más bajo y el MTTR más alto. Es la prioridad.")

    # 11. Pareto
    s = prs.slides.add_slide(blank); add_bg(s, WHITE)
    add_title(s, "Pareto 2024: el problema es operativo", "Tres causas concentran 72,9 % de las horas", 11)
    s.shapes.add_picture(str(IMG / "chart_pareto_2024.png"), Inches(0.45), Inches(1.7), width=Inches(8.2))
    add_bullets(s, [
        "16 Alimentación/aseo: 1.304 h (32,8 %).",
        "5 Ajuste operativo: 861 h (21,7 %).",
        "6 Limpieza por derrame: 732 h (18,4 %).",
        "7 Alistamiento: 378 h (9,5 %) → acumulado 82,4 %.",
        "Solo 1,9 % es falla electromecánica/energía/preventivo.",
    ], 8.9, 1.9, 4.0, 3.6, size=13)
    add_text(s, "Palanca: estandarizar la operación (5S, ajuste, limpieza) antes de invertir en mantenimiento.",
             8.9, 5.55, 4.0, 0.8, size=13, bold=True, color=GRAY)
    add_notes(s, "En 2024, tres causas concentran el 72,9 % de las horas: código 16, alimentación y aseo; código 5, ajuste operativo; y código 6, limpieza por derrame. Si agregamos el 7, llegamos al 82,4 %. Solo el 1,9 % es falla electromecánica, energía o preventivo. La conclusión es que el problema principal es operativo, no mantenimiento.")

    # 12. Grafana
    s = prs.slides.add_slide(blank); add_bg(s, WHITE)
    add_title(s, "Grafana: operación y alerta", "OEE < 60 % durante 1 minuto → Firing", 12)
    s.shapes.add_picture(str(IMG / "grafana_operativo_crop.png"), Inches(0.45), Inches(1.55), width=Inches(7.8))
    add_bullets(s, [
        "5 stat panels + series + estado + Pareto + turnos.",
        "Variables: máquina y turno (multivalor).",
        "Refresco cada 10 s; alerta por máquina.",
        "Webhook → audit.alertas_recibidas.",
        "Demo: forzar anomalía en Vinilos_4 y ver Firing.",
    ], 9.05, 1.75, 3.8, 3.6, size=12)
    add_text(s, "Umbral: 85 % clase mundial · 75 % meta · 60 % límite de control inferior.",
             9.05, 5.55, 3.8, 0.8, size=12, bold=True, color=GRAY)
    add_notes(s, "Grafana es la capa operativa. Arriba vemos OEE global, disponibilidad, rendimiento, paro y alertas. Abajo la serie por máquina, el estado actual, el Pareto, los minutos de paro, el OEE por turno y las últimas alertas. Las variables permiten filtrar por máquina y turno. La regla es OEE menor que 60 % durante un minuto; el umbral se justifica porque 85 % es clase mundial, 75 % es la meta y 60 % es el límite de control inferior. En la demo forzamos una anomalía y vemos cómo la línea se cae y la regla pasa a Firing.")

    # 13. Power BI
    s = prs.slides.add_slide(blank); add_bg(s, WHITE)
    add_title(s, "Power BI: análisis y gobierno", "PBIP + PBIR + DAX + RLS", 13)
    s.shapes.add_picture(str(IMG / "powerbi_resumen.png"), Inches(0.45), Inches(1.55), width=Inches(7.8))
    add_bullets(s, [
        "Modelo: 7 dimensiones, 2 hechos, 2 vistas.",
        "DAX: OEE, A/P/Q, YTD, año anterior, YoY, MTBF/MTTR, Pareto.",
        "5 páginas: resumen, máquinas, Pareto, turnos, detalle.",
        "RLS: Supervisores V1–V4 + Gerencia.",
        "PBIP/PBIR: texto diffable, sin .pbix binario.",
    ], 9.05, 1.75, 3.8, 3.8, size=12)
    add_text(s, "Drill-down código → subcódigo; drill-through a detalle.",
             9.05, 5.65, 3.8, 0.6, size=12, bold=True, color=GRAY)
    add_notes(s, "Power BI es la capa estratégica. El modelo tiene siete dimensiones, dos hechos y dos vistas. Las medidas DAX incluyen OEE, disponibilidad, rendimiento, calidad, OEE YTD, año anterior, variación YoY, MTBF, MTTR y Pareto acumulado. Hay cinco páginas. La seguridad es RLS por línea. El proyecto está en PBIP con modelo TMSL y reporte PBIR, no en .pbix binario, para poder revisarlo en Git.")

    # 14. Conclusiones
    s = prs.slides.add_slide(blank); add_bg(s, NAVY)
    add_text(s, "Conclusiones y mejoras", 0.8, 0.6, 11.8, 0.7, size=30, bold=True, color=WHITE)
    add_text(s, "Conclusiones", 0.8, 1.7, 5.8, 0.4, size=16, bold=True, color=YELLOW)
    add_bullets(s, [
        "Excel mensual → modelo dimensional confiable, conciliación 100 %.",
        "El problema principal es operativo: 16, 5 y 6 = 72,9 % de las horas.",
        "Vinilos_2 es la prioridad: OEE 33,7 %, rendimiento 55,8 %.",
    ], 0.8, 2.2, 5.8, 2.6, size=14, color=WHITE)
    add_text(s, "Mejoras", 6.9, 1.7, 5.8, 0.4, size=16, bold=True, color=YELLOW)
    add_bullets(s, [
        "Capturar unidades rechazadas → completar Calidad.",
        "Completar referencia/turno → subir cobertura de 52,8 %.",
        "Calibrar el estándar de 72 u/min (58 % supera 100 %).",
    ], 6.9, 2.2, 5.8, 2.6, size=14, color=WHITE)
    add_text(s, "“El Excel cuenta lo que pasó; esta solución explica por qué pasó y avisa cuando está pasando.”",
             0.8, 5.35, 11.8, 0.8, size=16, italic=True, color=YELLOW)
    add_notes(s, "Tres conclusiones: la solución convierte un Excel mensual en un modelo dimensional confiable; el problema principal es operativo, no solo mecánico; y Vinilos_2 es la prioridad. Tres mejoras: capturar rechazos, completar referencia y turno, y calibrar el estándar de 72 unidades por minuto. La frase final: el Excel cuenta lo que pasó; esta solución explica por qué pasó y avisa cuando está pasando.")

    # 15. Gracias
    s = prs.slides.add_slide(blank); add_bg(s, WHITE)
    add_text(s, "Gracias", 0.8, 2.0, 11.8, 0.9, size=48, bold=True, color=DARK)
    add_text(s, "¿Preguntas?", 0.8, 3.0, 11.8, 0.6, size=24, color=GRAY)
    add_text(s, "Repositorio:  https://github.com/<usuario>/oee-envasado-bi", 0.8, 4.2, 11.8, 0.4, size=14, color=GRAY)
    add_text(s, "Documentación: documentacion/  ·  Informe: informe/informe.pdf", 0.8, 4.7, 11.8, 0.4, size=14, color=GRAY)
    add_text(s, "Guion y cuestionario: documentacion/12_guion_exposicion.md  ·  13_cuestionario_practica.md",
             0.8, 5.2, 11.8, 0.4, size=12, color=GRAY)
    add_notes(s, "Gracias. Quedo atento a las preguntas.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    print(f"PPTX generado en {OUT}")


if __name__ == "__main__":
    build_charts()
    build_pptx()
