"""Tests de alertas y respuestas sin hablar con Telegram de verdad.

Truco: sustituimos `telegram.llamar` por una función falsa que apunta qué
le han pedido. Así comprobamos QUÉ mandaríamos, sin red ni token.
"""

import json

import pytest

from buscador import alertas, candidatura, main, respuestas, telegram

OFERTA = {
    "id": "abc123def456", "empresa": "Ejemplo & Cía", "titulo": "Becario <Backend>",
    "url": "https://ejemplo.com/ofertas/1", "ciudad": "Madrid", "modalidad": "híbrido",
}


@pytest.fixture
def bot(monkeypatch):
    """Telegram falso: guarda cada llamada en una lista."""
    llamadas = []
    monkeypatch.setenv("TELEGRAM_TOKEN", "token-de-prueba")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(telegram, "llamar", lambda metodo, **p: llamadas.append((metodo, p)) or {})
    return llamadas


def test_sin_configurar_no_manda_nada(monkeypatch):
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    assert alertas.avisar([OFERTA]) == 0


def test_alerta_con_botones_y_texto_escapado(bot):
    assert alertas.avisar([OFERTA]) == 1
    metodo, p = bot[0]
    assert metodo == "sendMessage"
    assert "Becario &lt;Backend&gt;" in p["text"]  # HTML escapado
    assert "Ejemplo &amp; Cía" in p["text"]
    botones = p["reply_markup"]["inline_keyboard"][0]
    assert [b["callback_data"] for b in botones] == ["si:abc123def456", "no:abc123def456"]
    assert all(len(b["callback_data"].encode()) <= 64 for b in botones)  # límite de Telegram


def test_maximo_de_alertas_por_dia(bot):
    muchas = [dict(OFERTA, id=f"id{i}") for i in range(alertas.MAXIMO_POR_DIA + 5)]
    assert alertas.avisar(muchas) == alertas.MAXIMO_POR_DIA
    assert "5 ofertas nuevas más" in bot[-1][1]["text"]


def _clic(update_id, data, chat=42):
    return {"update_id": update_id, "callback_query": {
        "id": f"cb{update_id}", "data": data,
        "message": {"message_id": 7, "chat": {"id": chat}}}}


def test_procesar_si_y_no(bot, monkeypatch):
    preparadas = []
    monkeypatch.setattr(candidatura, "preparar", preparadas.append)
    otra = dict(OFERTA, id="zzz")
    decisiones = {}

    siguiente = respuestas.procesar(
        [_clic(10, "si:abc123def456"), _clic(11, "no:zzz")],
        {OFERTA["id"]: OFERTA, "zzz": otra}, decisiones, mi_chat="42")

    assert siguiente == 12  # la próxima vez pedimos desde el 12
    assert decisiones["abc123def456"]["decision"] == "si"
    assert decisiones["zzz"]["decision"] == "no"
    assert preparadas == [OFERTA]  # solo la del "sí"
    assert [m for m, _ in bot].count("answerCallbackQuery") == 2


def test_ignora_clics_de_otros_chats(bot, monkeypatch):
    monkeypatch.setattr(candidatura, "preparar", lambda o: pytest.fail("no debería preparar"))
    decisiones = {}
    respuestas.procesar([_clic(5, "si:abc123def456", chat=999)], {OFERTA["id"]: OFERTA}, decisiones, "42")
    assert decisiones == {}


def test_oferta_desconocida(bot):
    decisiones = {}
    respuestas.procesar([_clic(1, "si:noexiste")], {}, decisiones, "42")
    assert decisiones == {}
    assert bot[0][0] == "answerCallbackQuery"


def test_primera_ejecucion_manda_solo_resumen(bot):
    resultado = {"ofertas": [OFERTA, dict(OFERTA, id="otra")]}
    main.avisar_nuevas({"actualizado": None, "ofertas": []}, resultado)
    assert len(bot) == 1 and "Primera búsqueda" in bot[0][1]["text"]


def test_despues_avisa_solo_de_las_nuevas(bot):
    anterior = {"actualizado": "2026-11-18T06:30", "ofertas": [OFERTA]}
    nueva = dict(OFERTA, id="nueva1")
    main.avisar_nuevas(anterior, {"ofertas": [OFERTA, nueva]})
    assert len(bot) == 1
    assert "si:nueva1" in str(bot[0][1]["reply_markup"])


# --- Webhook (respuestas al momento) ---------------------------------------

def test_mensaje_del_webhook_desde_el_evento(monkeypatch, tmp_path):
    evento = tmp_path / "evento.json"
    evento.write_text('{"client_payload": {"update": {"update_id": 3}}}', encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "repository_dispatch")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(evento))
    assert respuestas.update_del_webhook() == {"update_id": 3}
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    assert respuestas.update_del_webhook() is None


def test_main_con_webhook_procesa_el_clic_y_guarda_un_fichero(bot, monkeypatch, tmp_path):
    monkeypatch.setattr(respuestas, "CARPETA_DECISIONES", tmp_path / "decisiones")
    monkeypatch.setattr(respuestas, "FICHERO_OFERTAS", tmp_path / "ofertas.json")
    (tmp_path / "ofertas.json").write_text(json.dumps({"ofertas": [OFERTA]}), encoding="utf-8")
    monkeypatch.setattr(respuestas, "update_del_webhook", lambda: _clic(1, "no:abc123def456"))
    respuestas.main()
    guardada = json.loads((tmp_path / "decisiones" / "abc123def456.json").read_text(encoding="utf-8"))
    assert guardada["decision"] == "no"
    assert "getUpdates" not in [m for m, _ in bot]  # con webhook no se pregunta a Telegram


def test_polling_con_webhook_activo_no_falla(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(respuestas, "CARPETA_DECISIONES", tmp_path)
    monkeypatch.setattr(respuestas, "update_del_webhook", lambda: None)

    def conflicto(desde):
        raise RuntimeError("Telegram getUpdates: Conflict: can't use getUpdates method while webhook is active")
    monkeypatch.setattr(telegram, "actualizaciones", conflicto)
    assert respuestas.main() == 0


def test_contestar_tarde_un_boton_no_rompe_nada(monkeypatch):
    def caducado(metodo, **p):
        raise RuntimeError("Telegram answerCallbackQuery: query is too old")
    monkeypatch.setattr(telegram, "llamar", caducado)
    telegram.contestar_boton("cb1", "Apuntado")  # no lanza excepción


def test_resumen_de_busqueda(bot):
    anterior = {"ofertas": [OFERTA]}
    resultado = {"ofertas": [OFERTA, dict(OFERTA, id="nueva")],
                 "estado": [{"estado": "ok"}, {"estado": "error"}]}
    main.resumen_de_busqueda(anterior, resultado)
    texto = bot[-1][1]["text"]
    assert "2 prácticas IT en total, 1 nuevas" in texto and "1 empresas han fallado" in texto
