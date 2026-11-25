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
    """Telegram deja el botón "cargando" hasta que contestas al callback."""
    llamar("answerCallbackQuery", callback_query_id=callback_id, text=texto)


def actualizaciones(desde: int) -> list[dict]:
    """Lo que ha pasado en el chat desde la última vez (clics, mensajes...).

    `desde` es el offset: el update_id siguiente al último que procesamos.
    Al pedir con ese offset, Telegram da por leídos los anteriores.
    """
    return llamar("getUpdates", offset=desde, timeout=0,
                  allowed_updates=["callback_query", "message"])
