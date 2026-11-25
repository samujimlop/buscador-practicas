"""Convertir la carta (texto) en un PDF sencillo con fpdf2 (issue #8).

fpdf2 está escrito en Python puro: no necesita instalar nada más en
GitHub Actions. Sus fuentes de serie (Helvetica, Times...) solo conocen el
alfabeto "latin-1": las tildes y la ñ van bien, pero las comillas curvas,
los guiones largos o los emojis no. Por eso los cambiamos antes.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from fpdf import FPDF

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

EQUIVALENTES = {"“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "–": "-", "—": "-",
                "…": "...", "•": "-", " ": " ", " ": " "}


def a_latin1(texto: str) -> str:
    for raro, normal in EQUIVALENTES.items():
        texto = texto.replace(raro, normal)
    # Lo que aún no quepa en latin-1 (emojis...) se convierte en "?"
    return texto.encode("latin-1", errors="replace").decode("latin-1")


def nombre_fichero(empresa: str) -> str:
    """'Indra / Minsait' -> 'Carta_Indra_Minsait.pdf'"""
    limpio = re.sub(r"[^\w]+", "_", empresa, flags=re.UNICODE).strip("_")
    return f"Carta_{limpio or 'empresa'}.pdf"


def fecha_larga(hoy: date | None = None) -> str:
    hoy = hoy or date.today()
    return f"{hoy.day} de {MESES[hoy.month - 1]} de {hoy.year}"


def carta_a_pdf(texto: str, ruta: Path, lugar: str = "", hoy: date | None = None) -> Path:
    """`lugar` (p. ej. "Madrid") va delante de la fecha; viene del secreto CARTA_LUGAR."""
    pdf = FPDF(format="A4")
    pdf.set_margins(25, 25, 25)
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, a_latin1(f"{lugar}, {fecha_larga(hoy)}" if lugar else fecha_larga(hoy)), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.set_font("Helvetica", size=11)
    for parrafo in re.split(r"\n\s*\n", texto.strip()):
        pdf.multi_cell(0, 6, a_latin1(parrafo.strip()), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    pdf.output(str(ruta))
    return ruta
