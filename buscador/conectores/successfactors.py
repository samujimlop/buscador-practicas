"""Conector de SAP SuccessFactors (portales "RMK", antes jobs2web).

Muchas grandes empresas españolas (Telefónica, Indra, CaixaBank, Deloitte,
KPMG, EY...) tienen su portal de empleo en SuccessFactors. Todos esos
portales comparten una misma pieza que nos viene genial: un **canal RSS**
de ofertas que acepta palabras clave:

    https://<portal>/services/rss/job/?locale=es_ES&keywords=(prácticas)

RSS es XML estándar (lo mismo que usan los blogs y podcasts), así que no
hay que "rascar" HTML: lo leemos con la librería estándar de Python.

Cada <item> trae:
    <title>Prácticas Consultor/a I+D (La Coruña, ES, 15003)</title>
    <link>https://.../job/La-Coruña-Prácticas-.../1441865533/</link>
    <description>... HTML de la oferta ...</description>
    <pubDate>Tue, 25 Nov 2026 08:00:00 GMT</pubDate>

Ojo: el canal devuelve como mucho ~20 ofertas por consulta, por eso
lanzamos varias búsquedas (prácticas, becario, intern...) y juntamos los
resultados quitando duplicados.

En empresas.yaml:
    - nombre: Telefónica
      plataforma: successfactors
      portal: https://jobs.telefonica.com
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from ..filtros import detectar_modalidad, normalizar_ciudad
from ..modelo import Oferta
from .base import TIEMPO_MAXIMO, html_a_texto, sesion

BUSQUEDAS = ["prácticas", "becario", "beca", "intern", "internship", "trainee"]
PAUSA = 1.5  # segundos entre peticiones: somos educados con su servidor


def descargar(portal: str, busquedas: list[str] = BUSQUEDAS) -> list[dict]:
    """Devuelve los <item> del RSS como diccionarios, sin duplicados."""
    s = sesion()
    s.headers["Accept"] = "application/rss+xml, application/xml"
    vistos: dict[str, dict] = {}
    for palabra in busquedas:
        r = s.get(f"{portal.rstrip('/')}/services/rss/job/",
                  params={"locale": "es_ES", "keywords": f"({palabra})"}, timeout=TIEMPO_MAXIMO)
        r.raise_for_status()
        for item in ET.fromstring(r.content).iter("item"):
            crudo = {campo: (item.findtext(campo) or "").strip()
                     for campo in ("title", "link", "description", "pubDate")}
            vistos.setdefault(crudo["link"], crudo)
        time.sleep(PAUSA)
    return list(vistos.values())


# "Prácticas Consultor/a I+D (La Coruña, ES, 15003)" -> ("Prácticas Consultor/a I+D", "La Coruña, ES, 15003")
TITULO_Y_LUGAR = re.compile(r"^(.*)\s+\(([^()]*)\)\s*$")


def separar_titulo(titulo: str) -> tuple[str, str]:
    m = TITULO_Y_LUGAR.match(titulo)
    return (m.group(1).strip(), m.group(2).strip()) if m else (titulo.strip(), "")


def convertir(crudo: dict, empresa: dict) -> Oferta:
    titulo, lugar = separar_titulo(crudo["title"])
    fecha = ""
    if crudo.get("pubDate"):
        try:
            fecha = parsedate_to_datetime(crudo["pubDate"]).date().isoformat()
        except (TypeError, ValueError):
            pass
    descripcion = html_a_texto(crudo.get("description", ""))
    return Oferta(
        empresa=empresa["nombre"],
        sector=empresa.get("sector", ""),
        titulo=titulo,
        url=crudo["link"],
        ubicacion_original=lugar,
        ciudad=normalizar_ciudad(lugar),
        # SuccessFactors pone el país como código de 2 letras: "Madrid, ES, 28046"
        pais="Spain" if re.search(r"(^|,\s*)ES(,|$)", lugar) else "",
        modalidad=detectar_modalidad(f"{titulo} {descripcion[:400]}"),
        fecha_publicacion=fecha,
        descripcion=descripcion,
    )


def obtener_ofertas(empresa: dict) -> list[Oferta]:
    return [convertir(c, empresa) for c in descargar(empresa["portal"])]
