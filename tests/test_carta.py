"""Tests de la carta sin gastar dinero: Claude y Telegram son falsos.

El cliente falso imita lo justo de `anthropic.Anthropic`:
cliente.beta.messages.create(...) devuelve algo con .content y .stop_reason.
Así comprobamos QUÉ le mandaríamos a Claude. El CV es inventado.
"""

from datetime import date
from types import SimpleNamespace

import pytest

from buscador import candidatura, carta, pdf, respuestas, telegram

CV_FALSO = "# Ana Prueba\nProyecto: app de recetas con Angular y Firebase."
OFERTA = {
    "id": "abc123def456", "empresa": "Indra / Minsait", "titulo": "Beca Desarrollo Backend",
    "url": "https://ejemplo.com/oferta/1", "ciudad": "Madrid",
    "descripcion": "Buscamos estudiante con Java y Spring.",
}


class ClaudeFalso:
    def __init__(self, texto="Estimado equipo:\n\nMe interesa.\n\nAna Prueba", stop_reason="end_turn"):
        self.peticiones = []
        respuesta = SimpleNamespace(stop_reason=stop_reason,
                                    content=[SimpleNamespace(type="text", text=texto)])

        def create(**peticion):
            self.peticiones.append(peticion)
            return respuesta
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=create))


@pytest.fixture
def cv(monkeypatch):
    monkeypatch.setenv("CV_TEXTO", CV_FALSO)
    monkeypatch.delenv("PERFIL_NOTAS", raising=False)


def test_el_prompt_lleva_cv_y_oferta(cv):
    claude = ClaudeFalso()
    texto = carta.generar_carta(OFERTA, cliente=claude)
    assert texto.startswith("Estimado equipo")
    peticion = claude.peticiones[0]
    assert peticion["model"] == "claude-opus-5-5"
    mensaje = peticion["messages"][0]["content"]
    assert CV_FALSO in mensaje
    assert "Indra / Minsait" in mensaje and "Java y Spring" in mensaje
    assert "No inventes" in peticion["system"]


def test_sin_cv_no_llama_a_claude(monkeypatch, tmp_path):
    monkeypatch.delenv("CV_TEXTO", raising=False)
    monkeypatch.setattr(carta, "CARPETA_PERFIL", tmp_path)  # sin perfil/cv.md
    claude = ClaudeFalso()
    with pytest.raises(carta.CartaError, match="CV_TEXTO"):
        carta.generar_carta(OFERTA, cliente=claude)
    assert claude.peticiones == []


def test_rechazo(cv):
    with pytest.raises(carta.CartaError):
        carta.generar_carta(OFERTA, cliente=ClaudeFalso(texto="", stop_reason="refusal"))


def test_pdf_con_tildes_y_comillas(tmp_path):
    ruta = pdf.carta_a_pdf("Estimado equipo de “Telefónica” — España…\n\nUn saludo,\nAna Peña",
                           tmp_path / "c.pdf", lugar="Madrid", hoy=date(2026, 11, 25))
    assert ruta.read_bytes().startswith(b"%PDF")
    assert pdf.nombre_fichero("Indra / Minsait") == "Carta_Indra_Minsait.pdf"
    assert pdf.fecha_larga(date(2026, 11, 25)) == "25 de noviembre de 2026"


@pytest.fixture
def bot(monkeypatch, tmp_path):
    """Telegram falso + data/ temporal (para no tocar el repo)."""
    enviados = []
    monkeypatch.setenv("TELEGRAM_TOKEN", "token-de-prueba")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(telegram, "enviar", lambda texto, botones=None: enviados.append(("texto", texto)))
    monkeypatch.setattr(telegram, "enviar_documento",
                        lambda doc, texto="": enviados.append(("doc", getattr(doc, "name", doc))))
    monkeypatch.setattr(candidatura, "FICHERO_CV", tmp_path / "cv_telegram.json")
    return enviados


def test_preparar_manda_carta_cv_y_enlace(bot, cv, monkeypatch):
    monkeypatch.setattr(carta, "generar_carta", lambda oferta: "Estimado equipo:\n\nHola.")
    candidatura.guardar_cv({"file_id": "FILE123", "file_name": "CV.pdf"})
    candidatura.preparar(OFERTA)
    assert bot[0] == ("doc", "Carta_Indra_Minsait.pdf")
    assert bot[1] == ("doc", "FILE123")
    assert "ejemplo.com/oferta/1" in bot[2][1] and "Revisa la carta" in bot[2][1]


def test_preparar_sin_creditos_manda_el_enlace(bot, monkeypatch):
    def sin_creditos(oferta):
        raise carta.CartaError("La API rechazó la petición: credit balance is too low")
    monkeypatch.setattr(carta, "generar_carta", sin_creditos)
    candidatura.preparar(OFERTA)
    assert len(bot) == 1
    assert "No he podido escribir la carta" in bot[0][1] and "ejemplo.com/oferta/1" in bot[0][1]


def test_un_pdf_en_el_chat_se_guarda_como_cv(bot):
    pdf_mio = {"chat": {"id": 42}, "document": {"file_id": "F1", "file_name": "CV.pdf", "mime_type": "application/pdf"}}
    pdf_ajeno = {"chat": {"id": 666}, "document": {"file_id": "MALO", "mime_type": "application/pdf"}}
    respuestas.procesar([{"update_id": 1, "message": pdf_ajeno}], {}, {}, "42")
    assert candidatura.cv_guardado() is None
    respuestas.procesar([{"update_id": 2, "message": pdf_mio}], {}, {}, "42")
    assert candidatura.cv_guardado()["file_id"] == "F1"
