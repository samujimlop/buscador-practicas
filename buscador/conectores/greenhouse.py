"""Conector de ejemplo: Greenhouse.

Greenhouse es una plataforma de selección que usan muchas tecnológicas y
scaleups. Tiene una API pública y documentada que no necesita clave:

    https://boards-api.greenhouse.io/v1/boards/<board>/jobs?content=true

donde <board> es el nombre de la empresa en Greenhouse. Lo sacas de la URL
de su página de empleo, por ejemplo job-boards.greenhouse.io/<board>.

Este fichero es el PATRÓN a seguir para el resto de conectores:
  1. descargar()   -> habla con la plataforma y devuelve los datos crudos
  2. convertir()   -> pasa UNA oferta cruda a nuestro formato `Oferta`
  3. obtener_ofertas() -> junta las dos cosas

Separar descargar y convertir permite probar convertir() sin internet,
con un JSON guardado en tests/fixtures/.
"""

from __future__ import annotations

from ..filtros import detectar_modalidad, normalizar_ciudad
from ..modelo import Oferta
from .base import TIEMPO_MAXIMO, html_a_texto, sesion

URL_API = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"


def descargar(board: str) -> list[dict]:
    respuesta = sesion().get(
        URL_API.format(board=board),
        params={"content": "true"},
        timeout=TIEMPO_MAXIMO,
    )
    respuesta.raise_for_status()  # si da 404 o 500, que salte un error claro
    return respuesta.json().get("jobs", [])


def convertir(crudo: dict, empresa: dict) -> Oferta:
    ubicacion = (crudo.get("location") or {}).get("name", "")
    departamentos = ", ".join(d.get("name", "") for d in crudo.get("departments", []))
    descripcion = html_a_texto(crudo.get("content", ""))
    fecha = crudo.get("first_published") or crudo.get("updated_at") or ""

    return Oferta(
        empresa=empresa["nombre"],
        sector=empresa.get("sector", ""),
        titulo=crudo.get("title", "").strip(),
        url=crudo.get("absolute_url", ""),
        ubicacion_original=ubicacion,
        ciudad=normalizar_ciudad(ubicacion),
        departamento=departamentos,
        modalidad=detectar_modalidad(f"{ubicacion} {crudo.get('title', '')}"),
        fecha_publicacion=fecha[:10],  # "2026-11-02T10:00:00Z" -> "2026-11-02"
        descripcion=descripcion,
    )


def obtener_ofertas(empresa: dict) -> list[Oferta]:
    return [convertir(c, empresa) for c in descargar(empresa["board"])]
