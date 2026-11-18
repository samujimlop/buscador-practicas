"""Qué pasa cuando pulsas "Sí" en una oferta.

AHORA: solo te manda el enlace para aplicar.

LO QUE VAS A PROGRAMAR TÚ (issues del repo):
  1. carta.py: pedir a la API de Claude una carta personalizada a partir de
     tu CV (perfil/cv.md) y de la oferta.
  2. Convertir la carta a PDF.
  3. Mandarte por Telegram la carta + tu CV en PDF (sendDocument) junto al enlace.

La idea es que esta función siga siendo el único punto de entrada:
respuestas.py la llama y no necesita saber cómo se hace la carta.
"""

from __future__ import annotations

from . import telegram


def preparar(oferta: dict) -> None:
    telegram.enviar(
        "📝 Aún no sé escribir cartas (¡issue pendiente!).\n"
        f'De momento, aquí tienes el enlace para aplicar: <a href="{telegram.escapar(oferta["url"])}">'
        f"{telegram.escapar(oferta['titulo'])}</a>"
    )
