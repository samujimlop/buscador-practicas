"""Leer lo que has contestado en Telegram: python -m buscador.respuestas

GitHub Actions no puede estar "escuchando" todo el rato, así que este
script se ejecuta cada 30 minutos (polling), pregunta a Telegram qué
botones has pulsado desde la última vez y apunta tu decisión.

Estado que guardamos en el repo (para la siguiente ejecución):
    data/telegram_offset.json   por dónde íbamos leyendo
    data/decisiones.json        {id_oferta: {"decision": "si"/"no", "fecha": ...}}
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import candidatura, telegram

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data"
FICHERO_OFFSET = DATOS / "telegram_offset.json"
FICHERO_DECISIONES = DATOS / "decisiones.json"
FICHERO_OFERTAS = RAIZ / "docs" / "ofertas.json"

log = logging.getLogger("buscador")


def _leer_json(ruta: Path, por_defecto):
    if not ruta.exists():
        return por_defecto
    return json.loads(ruta.read_text(encoding="utf-8"))


def _escribir_json(ruta: Path, datos) -> None:
    ruta.parent.mkdir(exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def procesar(actualizaciones: list[dict], ofertas: dict[str, dict], decisiones: dict, mi_chat: str) -> int:
    """Aplica cada clic. Devuelve el siguiente offset que hay que pedir.

    Separado de main() para poder probarlo sin Telegram (ver tests).
    """
    siguiente = 0
    for upd in actualizaciones:
        siguiente = max(siguiente, upd["update_id"] + 1)
        clic = upd.get("callback_query")
        if not clic:
            continue  # mensajes de texto: de momento los ignoramos

        mensaje = clic.get("message") or {}
        # Seguridad: solo hacemos caso a TU chat. Cualquiera puede escribir a un bot.
        if str(mensaje.get("chat", {}).get("id")) != str(mi_chat):
            log.warning("Ignorado un clic de otro chat")
            continue

        decision, _, id_oferta = clic.get("data", "").partition(":")
        oferta = ofertas.get(id_oferta)
        if decision not in ("si", "no") or oferta is None:
            telegram.contestar_boton(clic["id"], "No encuentro esa oferta (¿ya cerrada?)")
            continue

        decisiones[id_oferta] = {
            "decision": decision,
            "fecha": datetime.now(timezone.utc).isoformat(timespec="minutes"),
            "empresa": oferta["empresa"],
            "titulo": oferta["titulo"],
        }
        telegram.contestar_boton(clic["id"], "Apuntado ✅" if decision == "si" else "Descartada")

        resumen = f"<b>{telegram.escapar(oferta['titulo'])}</b> · {telegram.escapar(oferta['empresa'])}"
        if decision == "no":
            telegram.editar(mensaje, f"❌ Descartada: {resumen}")
        else:
            telegram.editar(mensaje, f"✅ Preparando candidatura: {resumen}")
            candidatura.preparar(oferta)
    return siguiente


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not telegram.configurado():
        log.info("Telegram sin configurar: nada que leer")
        return 0

    offset = _leer_json(FICHERO_OFFSET, {"offset": 0})["offset"]
    decisiones = _leer_json(FICHERO_DECISIONES, {})
    ofertas = {o["id"]: o for o in _leer_json(FICHERO_OFERTAS, {"ofertas": []})["ofertas"]}

    nuevas = telegram.actualizaciones(offset)
    log.info("%d actualizaciones de Telegram", len(nuevas))
    siguiente = procesar(nuevas, ofertas, decisiones, telegram.chat_id())

    if siguiente:
        _escribir_json(FICHERO_OFFSET, {"offset": siguiente})
        _escribir_json(FICHERO_DECISIONES, decisiones)
    return 0


if __name__ == "__main__":
    sys.exit(main())
