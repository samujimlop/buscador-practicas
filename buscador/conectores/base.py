"""Lo que tienen en común todos los conectores.

Un conector es una función con esta forma:

    def obtener_ofertas(empresa: dict) -> list[Oferta]

`empresa` es la entrada de empresas.yaml (nombre, sector, y los parámetros
que necesite esa plataforma, por ejemplo el `board` en Greenhouse).
Devuelve TODAS las ofertas que encuentre; el filtrado de prácticas e
informática se hace después, en un único sitio (filtros.py).
"""

from __future__ import annotations

import html
import re

import requests

# Nos identificamos de forma honesta y con un tiempo de espera razonable.
CABECERAS = {
    "User-Agent": "buscador-practicas/0.1 (proyecto de estudiante; uso personal)",
    "Accept": "application/json",
}
TIEMPO_MAXIMO = 30  # segundos


def sesion() -> requests.Session:
    s = requests.Session()
    s.headers.update(CABECERAS)
    return s


def html_a_texto(contenido: str) -> str:
    """Quita etiquetas HTML para poder buscar palabras en la descripción."""
    contenido = html.unescape(contenido or "")
    contenido = re.sub(r"<[^>]+>", " ", contenido)
    return re.sub(r"\s+", " ", contenido).strip()
