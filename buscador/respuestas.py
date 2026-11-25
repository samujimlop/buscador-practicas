"""Leer lo que has contestado en Telegram: python -m buscador.respuestas

Hay dos formas de enterarnos de lo que pulsas en Telegram:

1. **Webhook (al momento):** Telegram avisa a un "worker" de Cloudflare
   (webhook/worker.js) en cuanto pulsas algo. El worker lanza este workflow
   con `repository_dispatch` y nos pasa el mensaje en el evento. Tarda
   1 o 2 minutos en total.
2. **Polling (cada 30 min, de reserva):** si no hay webhook, el workflow
   programado pregunta a Telegram con getUpdates qué ha pasado desde la
   última vez. Ojo: Telegram no deja usar getUpdates si hay webhook.

Estado que guardamos en el repo (para la siguiente ejecución):
    data/telegram_offset.json   por dónde íbamos leyendo (solo polling)
    data/decisiones/<id>.json   tu decisión de cada oferta: un fichero por
                                oferta, para que dos ejecuciones a la vez no
                                choquen al guardar en git
    data/cv_telegram.json       el file_id de tu CV si se lo mandaste al bot
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import candidatura, telegram

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data"
FICHERO_OFFSET = DATOS / "telegram_offset.json"
CARPETA_DECISIONES = DATOS / "decisiones"
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
            recibir_mensaje(upd.get("message") or {}, mi_chat)
            continue

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


def recibir_mensaje(mensaje: dict, mi_chat: str) -> None:
    """Si nos mandas un PDF, lo guardamos como tu CV. El resto de mensajes se ignoran."""
    if str(mensaje.get("chat", {}).get("id")) != str(mi_chat):
        return
    documento = mensaje.get("document") or {}
    if documento.get("mime_type") == "application/pdf":
        candidatura.guardar_cv(documento)
        telegram.enviar("📎 CV guardado. Lo adjuntaré a cada carta a partir de ahora.")


def cargar_decisiones() -> dict:
    return {f.stem: _leer_json(f, {}) for f in sorted(CARPETA_DECISIONES.glob("*.json"))}


def guardar_decisiones(decisiones: dict, antes: dict) -> None:
    """Escribe solo las decisiones nuevas o cambiadas, cada una en su fichero."""
    for id_oferta, datos in decisiones.items():
        if antes.get(id_oferta) != datos:
            _escribir_json(CARPETA_DECISIONES / f"{id_oferta}.json", datos)


def update_del_webhook() -> dict | None:
    """Si nos ha lanzado el worker, el mensaje de Telegram viene en el evento.

    GitHub deja el evento que lanzó el workflow en un JSON cuya ruta está en
    la variable GITHUB_EVENT_PATH.
    """
    if os.environ.get("GITHUB_EVENT_NAME") != "repository_dispatch":
        return None
    evento = _leer_json(Path(os.environ["GITHUB_EVENT_PATH"]), {})
    return evento.get("client_payload", {}).get("update")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not telegram.configurado():
        log.info("Telegram sin configurar: nada que leer")
        return 0

    decisiones = cargar_decisiones()
    antes = {k: dict(v) for k, v in decisiones.items()}
    ofertas = {o["id"]: o for o in _leer_json(FICHERO_OFERTAS, {"ofertas": []})["ofertas"]}

    update = update_del_webhook()
    if update:
        procesar([update], ofertas, decisiones, telegram.chat_id())
    else:
        offset = _leer_json(FICHERO_OFFSET, {"offset": 0})["offset"]
        try:
            nuevas = telegram.actualizaciones(offset)
        except RuntimeError as error:
            if "webhook" in str(error).lower():
                log.info("Hay webhook activo: las respuestas llegan al momento, no hace falta leer")
                return 0
            raise
        log.info("%d actualizaciones de Telegram", len(nuevas))
        siguiente = procesar(nuevas, ofertas, decisiones, telegram.chat_id())
        if siguiente:
            _escribir_json(FICHERO_OFFSET, {"offset": siguiente})

    guardar_decisiones(decisiones, antes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
