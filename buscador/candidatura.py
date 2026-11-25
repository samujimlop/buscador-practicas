"""Qué pasa cuando pulsas "Sí" en una oferta (issues #7 y #8).

1. carta.py le pide a Claude una carta adaptada a la oferta y a tu CV.
2. pdf.py la convierte en un PDF ("Carta_<Empresa>.pdf") en una carpeta
   temporal: nunca dentro del repo, que es público.
3. Te llegan por Telegram: la carta, tu CV y el enlace para aplicar.

La candidatura la envías TÚ desde la web de la empresa, después de revisar
la carta. El bot nunca aplica por su cuenta.

Tu CV en PDF: no cabe en un secreto de GitHub (máximo 48 KB), así que se lo
mandas una vez al bot por Telegram. Telegram lo guarda y nos da un
identificador (file_id) que apuntamos en data/cv_telegram.json. Ese
identificador solo funciona con el token de tu bot, así que no sirve de
nada a quien lo lea en el repo.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import carta, pdf, telegram

FICHERO_CV = Path(__file__).resolve().parent.parent / "data" / "cv_telegram.json"

log = logging.getLogger("buscador")


def cv_guardado() -> dict | None:
    if not FICHERO_CV.exists():
        return None
    return json.loads(FICHERO_CV.read_text(encoding="utf-8"))


def guardar_cv(documento: dict) -> None:
    """Llamado por respuestas.py cuando le mandas un PDF al bot."""
    FICHERO_CV.parent.mkdir(exist_ok=True)
    FICHERO_CV.write_text(json.dumps({
        "file_id": documento["file_id"],
        "nombre": documento.get("file_name", "CV.pdf"),
        "fecha": datetime.now(timezone.utc).isoformat(timespec="minutes"),
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def preparar(oferta: dict) -> None:
    empresa = telegram.escapar(oferta["empresa"])
    titulo = telegram.escapar(oferta["titulo"])
    enlace = f'🔗 <a href="{telegram.escapar(oferta["url"])}">Aplicar en la web de {empresa}</a>'

    try:
        texto = carta.generar_carta(oferta)
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / pdf.nombre_fichero(oferta["empresa"])
            pdf.carta_a_pdf(texto, ruta, lugar=os.environ.get("CARTA_LUGAR", ""))
            telegram.enviar_documento(ruta, f"📝 Carta para <b>{titulo}</b> · {empresa}")
    except carta.CartaError as error:
        telegram.enviar(f"⚠️ No he podido escribir la carta: {telegram.escapar(str(error))}\n\n{enlace}")
        return
    except Exception as error:
        # Solo el tipo de error: el mensaje podría contener parte del CV o de la carta.
        log.warning("Fallo preparando la carta: %s", type(error).__name__)
        telegram.enviar(f"⚠️ Algo ha fallado preparando la carta ({type(error).__name__}).\n\n{enlace}")
        return

    cv = cv_guardado()
    if cv:
        telegram.enviar_documento(cv["file_id"], "📎 Tu CV")
    else:
        telegram.enviar("📎 Aún no tengo tu CV en PDF: mándamelo por este chat y lo adjuntaré a partir de ahora.")

    telegram.enviar(f"{enlace}\n\n👀 Revisa la carta antes de enviarla: Claude puede equivocarse.")
