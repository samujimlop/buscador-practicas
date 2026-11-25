"""Avisar por Telegram de las ofertas nuevas, con botones Sí / No.

El botón lleva dentro un texto corto (callback_data, máximo 64 bytes) que
Telegram nos devuelve cuando lo pulsas: "si:<id de la oferta>" o
"no:<id>". Así, al leer las respuestas, sabemos qué oferta era.
"""

from __future__ import annotations

import logging

from . import telegram

log = logging.getLogger("buscador")

MAXIMO_POR_DIA = 15  # para no inundarte el móvil el primer día


def texto_oferta(oferta: dict) -> str:
    lugar = oferta.get("ciudad") or oferta.get("ubicacion_original") or "Ubicación sin indicar"
    lineas = [
        f"🆕 <b>{telegram.escapar(oferta['titulo'])}</b>",
        f"🏢 {telegram.escapar(oferta['empresa'])} · 📍 {telegram.escapar(lugar)}",
    ]
    if oferta.get("modalidad"):
        lineas.append(f"💼 {telegram.escapar(oferta['modalidad'])}")
    lineas.append(f'<a href="{telegram.escapar(oferta["url"])}">Ver la oferta</a>')
    lineas.append("\n¿Preparo carta y candidatura?")
    return "\n".join(lineas)


def botones_oferta(oferta: dict) -> list[list[dict]]:
    return [[
        {"text": "✅ Sí, prepárala", "callback_data": f"si:{oferta['id']}"},
        {"text": "❌ No", "callback_data": f"no:{oferta['id']}"},
    ]]


def avisar(nuevas: list[dict]) -> int:
    """Manda una alerta por oferta nueva. Devuelve cuántas ha mandado."""
    if not nuevas:
        return 0
    if not telegram.configurado():
        log.info("Telegram sin configurar: no se mandan %d alertas", len(nuevas))
        return 0

    enviadas = 0
    for oferta in nuevas[:MAXIMO_POR_DIA]:
        try:
            telegram.enviar(texto_oferta(oferta), botones_oferta(oferta))
            enviadas += 1
        except Exception as error:  # una alerta fallida no debe tumbar la actualización
            log.warning("No se pudo avisar de %s: %s", oferta["id"], error)

    resto = len(nuevas) - MAXIMO_POR_DIA
    if resto > 0:
        telegram.enviar(f"…y {resto} ofertas nuevas más. Míralas en la web con el filtro «Solo nuevas».")
    return enviadas
