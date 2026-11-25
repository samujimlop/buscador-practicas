"""Escribir una carta de presentación con la API de Claude (issue #7).

La idea es sencilla: le damos a Claude tu CV y la oferta, y le pedimos una
carta adaptada. Todo lo "inteligente" está en el prompt (las instrucciones);
el código solo junta las piezas y hace una llamada a la API.

De dónde sale cada cosa:
    ANTHROPIC_API_KEY   secreto de GitHub; el SDK lo lee solo del entorno
    Tu CV               el PDF que le mandaste al bot por Telegram: Claude
                        sabe leer PDFs, así que se lo pasamos tal cual.
                        (Alternativa: el secreto CV_TEXTO con el CV en texto.)
    PERFIL_NOTAS        secreto opcional: lo que quieres destacar siempre
                        (p. ej. "prefiero backend", "disponible desde febrero")
En tu ordenador puedes usar perfil/cv.md y perfil/notas.md (perfil/ está en
.gitignore, así que nunca se sube).

⚠️ El repo es público: nunca imprimas el CV ni la carta en los logs.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

import anthropic

from .conectores.base import TIEMPO_MAXIMO, html_a_texto, sesion

MODELO = "claude-opus-5-5"
CARPETA_PERFIL = Path(__file__).resolve().parent.parent / "perfil"
MAX_PAGINA = 8000  # caracteres de la web de la oferta, si no tenemos su descripción

# Las instrucciones fijas van en el "system prompt". Lo que cambia en cada
# carta (CV, oferta) va en el mensaje del usuario.
INSTRUCCIONES = """\
Eres un orientador profesional que ayuda a un estudiante de Ingeniería \
Informática a solicitar prácticas en España. Escribes cartas de presentación \
cortas, concretas y sinceras.

Reglas:
- Usa solo información que aparezca en el CV o en las notas del candidato. \
No inventes experiencia, cifras, notas, certificados ni fechas. Si la oferta \
pide algo que el candidato no tiene, no lo menciones o muestra ganas de aprenderlo.
- Conecta 2 o 3 cosas concretas del CV (proyectos, tecnologías, experiencia) \
con lo que pide la oferta. Nada de frases genéricas que valdrían para cualquier empresa.
- Escribe en el idioma de la oferta (español o inglés).
- Entre 250 y 320 palabras, en 3 o 4 párrafos.
- Empieza con un saludo ("Estimado equipo de selección de <empresa>:" o similar) \
y termina con una despedida y el nombre completo del candidato.
- Devuelve solo el texto de la carta, sin títulos, sin Markdown y sin comentarios.
"""


def leer_perfil(variable: str, fichero: str) -> str:
    """Primero el secreto (GitHub Actions); si no está, el fichero local."""
    valor = os.environ.get(variable, "").strip()
    if valor:
        return valor
    ruta = CARPETA_PERFIL / fichero
    return ruta.read_text(encoding="utf-8").strip() if ruta.exists() else ""


def descripcion_oferta(oferta: dict) -> str:
    """La descripción guardada en ofertas.json o, si no está, la web de la oferta."""
    if oferta.get("descripcion"):
        return oferta["descripcion"]
    try:
        r = sesion().get(oferta["url"], timeout=TIEMPO_MAXIMO)
        r.raise_for_status()
        return html_a_texto(r.text)[:MAX_PAGINA]
    except Exception:  # sin descripción la carta sale más genérica, pero sale
        return ""


def construir_mensaje(oferta: dict, cv: str, notas: str, descripcion: str) -> str:
    """Junta todo en el mensaje para Claude. Separado para poder probarlo."""
    partes = [
        "<cv>", cv, "</cv>",
        "<notas_del_candidato>", notas or "(sin notas)", "</notas_del_candidato>",
        "<oferta>",
        f"Empresa: {oferta.get('empresa', '')}",
        f"Puesto: {oferta.get('titulo', '')}",
        f"Ubicación: {oferta.get('ubicacion_original') or oferta.get('ciudad', '')}",
        f"Enlace: {oferta.get('url', '')}",
        "Descripción:", descripcion or "(no disponible: básate en el puesto y la empresa)",
        "</oferta>",
        "Escribe la carta de presentación para esta oferta.",
    ]
    return "\n".join(partes)


class CartaError(Exception):
    """Algo impidió escribir la carta (falta el CV, sin créditos, rechazo...)."""


def contenido_para_claude(oferta: dict, cv_pdf: bytes | None) -> list[dict]:
    """El mensaje para Claude: el CV (en texto o como PDF adjunto) y la oferta.

    Un mensaje puede tener varios "bloques": aquí, si hay PDF, primero va el
    documento y después el texto con las instrucciones de la oferta.
    """
    notas = leer_perfil("PERFIL_NOTAS", "notas.md")
    cv_texto = leer_perfil("CV_TEXTO", "cv.md")
    bloques = []
    if cv_texto:
        cv = cv_texto
    elif cv_pdf:
        cv = "(Es el documento PDF adjunto.)"
        bloques.append({"type": "document", "title": "CV del candidato", "source": {
            "type": "base64", "media_type": "application/pdf",
            "data": base64.b64encode(cv_pdf).decode("ascii")}})
    else:
        raise CartaError("Falta tu CV: mándamelo en PDF por este chat")
    bloques.append({"type": "text", "text": construir_mensaje(oferta, cv, notas, descripcion_oferta(oferta))})
    return bloques


def generar_carta(oferta: dict, cv_pdf: bytes | None = None,
                  cliente: anthropic.Anthropic | None = None) -> str:
    contenido = contenido_para_claude(oferta, cv_pdf)

    cliente = cliente or anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno
    try:
        respuesta = cliente.beta.messages.create(
            model=MODELO,
            max_tokens=16000,
            system=INSTRUCCIONES,
            output_config={"effort": "medium"},  # "esfuerzo" de razonamiento: de sobra para una carta
            # Si el filtro de seguridad rechazara la petición por error, la API
            # la repite sola con otro modelo en vez de devolver nada.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": contenido}],
        )
    except anthropic.AuthenticationError as e:
        raise CartaError("La clave ANTHROPIC_API_KEY no es válida") from e
    except anthropic.BadRequestError as e:
        # Por ejemplo, si te quedas sin créditos la API responde 400 con ese aviso.
        raise CartaError(f"La API rechazó la petición: {e.message}") from e
    except anthropic.APIStatusError as e:
        raise CartaError(f"Error de la API ({e.status_code})") from e
    except anthropic.APIConnectionError as e:
        raise CartaError("No se pudo conectar con la API de Claude") from e

    if respuesta.stop_reason == "refusal":
        raise CartaError("Claude no ha querido escribir esta carta")
    texto = "".join(b.text for b in respuesta.content if b.type == "text").strip()
    if not texto:
        raise CartaError("La respuesta llegó vacía")
    return texto
