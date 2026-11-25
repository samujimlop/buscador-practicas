"""Hablar con Telegram: lo mínimo para mandar mensajes con botones y leer respuestas.

La API de bots de Telegram es HTTP normal: cada acción es una URL
https://api.telegram.org/bot<TOKEN>/<método> y le mandas JSON.
Documentación: https://core.telegram.org/bots/api

Configuración (variables de entorno, en GitHub van como "secrets"):
    TELEGRAM_TOKEN    lo que te da @BotFather al crear el bot
    TELEGRAM_CHAT_ID  tu chat con el bot (ver README, "Alertas por Telegram")

Si no están puestas, `configurado()` devuelve False y el resto del programa
se salta las alertas sin fallar. Así los tests y tu ordenador funcionan
sin bot.
"""

from __future__ import annotations

import html
import os

import requests

URL_API = "https://api.telegram.org/bot{token}/{metodo}"
TIEMPO_MAXIMO = 30


def configurado() -> bool:
    return bool(os.environ.get("TELEGRAM_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def chat_id() -> str:
    return os.environ["TELEGRAM_CHAT_ID"]


def llamar(metodo: str, **parametros) -> dict | list:
    """Llama a un método de la API y devuelve el campo `result`.

    Telegram siempre responde {"ok": true/false, "result": ..., "description": ...}.
    """
    url = URL_API.format(token=os.environ["TELEGRAM_TOKEN"], metodo=metodo)
    respuesta = requests.post(url, json=parametros, timeout=TIEMPO_MAXIMO)
    datos = respuesta.json()
    if not datos.get("ok"):
        # Ojo: nunca imprimas la URL, que lleva el token dentro.
        raise RuntimeError(f"Telegram {metodo}: {datos.get('description', respuesta.status_code)}")
    return datos["result"]


def escapar(texto: str) -> str:
    """Usamos el modo HTML de Telegram, así que hay que escapar <, > y &."""
    return html.escape(texto or "", quote=False)


def enviar(texto: str, botones: list[list[dict]] | None = None) -> dict:
    parametros = {
        "chat_id": chat_id(),
        "text": texto,
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": True},
    }
    if botones:
        parametros["reply_markup"] = {"inline_keyboard": botones}
    return llamar("sendMessage", **parametros)


def editar(mensaje: dict, texto: str) -> None:
    """Sustituye el texto de un mensaje ya enviado (y le quita los botones)."""
    llamar("editMessageText", chat_id=mensaje["chat"]["id"], message_id=mensaje["message_id"],
           text=texto, parse_mode="HTML", link_preview_options={"is_disabled": True})


def contestar_boton(callback_id: str, texto: str = "") -> None:
    """Telegram deja el botón "cargando" hasta que contestas al callback.

    Solo se puede contestar durante un rato (y una vez): si el worker ya lo
    contestó, o si leemos el clic media hora después, Telegram da error.
    No pasa nada: seguimos con lo importante.
    """
    try:
        llamar("answerCallbackQuery", callback_query_id=callback_id, text=texto)
    except RuntimeError:
        pass


def actualizaciones(desde: int) -> list[dict]:
    """Lo que ha pasado en el chat desde la última vez (clics, mensajes...).

    `desde` es el offset: el update_id siguiente al último que procesamos.
    Al pedir con ese offset, Telegram da por leídos los anteriores.
    """
    return llamar("getUpdates", offset=desde, timeout=0,
                  allowed_updates=["callback_query", "message"])


def enviar_documento(documento, texto: str = "") -> dict:
    """Manda un fichero (sendDocument).

    `documento` puede ser:
      - una ruta (Path) a un fichero de este ordenador: lo subimos.
      - un texto con el file_id de un fichero que ya está en Telegram
        (por ejemplo, tu CV, que le mandaste al bot una vez): no hay que subirlo.

    Ojo: para subir ficheros Telegram no acepta JSON, sino "multipart/form-data"
    (lo mismo que hace un formulario web con un <input type="file">).
    """
    url = URL_API.format(token=os.environ["TELEGRAM_TOKEN"], metodo="sendDocument")
    datos = {"chat_id": chat_id(), "caption": texto, "parse_mode": "HTML"}
    if isinstance(documento, str):
        respuesta = requests.post(url, data={**datos, "document": documento}, timeout=TIEMPO_MAXIMO)
    else:
        with open(documento, "rb") as f:
            respuesta = requests.post(url, data=datos, files={"document": (documento.name, f, "application/pdf")},
                                      timeout=TIEMPO_MAXIMO)
    resultado = respuesta.json()
    if not resultado.get("ok"):
        raise RuntimeError(f"Telegram sendDocument: {resultado.get('description', respuesta.status_code)}")
    return resultado["result"]


def descargar_fichero(file_id: str) -> bytes:
    """Descarga un fichero que está en Telegram (p. ej. tu CV) a partir de su file_id.

    Dos pasos: getFile nos dice en qué ruta está, y luego lo bajamos de
    https://api.telegram.org/file/bot<TOKEN>/<ruta>. Esa URL lleva el token:
    nunca la imprimas.
    """
    ruta = llamar("getFile", file_id=file_id)["file_path"]
    url = f"https://api.telegram.org/file/bot{os.environ['TELEGRAM_TOKEN']}/{ruta}"
    respuesta = requests.get(url, timeout=TIEMPO_MAXIMO)
    if respuesta.status_code != 200:
        raise RuntimeError(f"Telegram: no se pudo descargar el fichero ({respuesta.status_code})")
    return respuesta.content
