"""Conector de Workday.

Los portales de Workday (https://<empresa>.wdN.myworkdayjobs.com/<sitio>) son
una web hecha en JavaScript que por debajo pide los datos a una API JSON:

    POST https://<empresa>.wdN.myworkdayjobs.com/wday/cxs/<empresa>/<sitio>/jobs
         {"appliedFacets": {...}, "limit": 20, "offset": 0, "searchText": "intern"}

Lo descubrimos con F12 → pestaña Red, viendo qué pide la página al cargar.

Tres ideas importantes de este conector:

1. **Facetas (filtros):** la respuesta trae `facets`, los filtros que ves a la
   izquierda en la web (país, área...). Buscamos el de país "Spain/España" y
   repetimos la búsqueda con él, para no descargar ofertas de todo el mundo.
2. **Paginación:** la API devuelve 20 ofertas cada vez. Vamos subiendo
   `offset` hasta llegar a `total`.
3. **Detalle:** el listado solo trae título, ruta y un texto de ubicación
   ("Madrid" o "3 Locations"). Para las que parecen prácticas pedimos el
   detalle (GET <sitio><externalPath>), que trae la descripción completa.

Algunas empresas en Workday bloquean las peticiones que vienen de servidores
(responden 429). No intentamos saltarnos eso: el error queda registrado y la
web enseña el enlace para buscar a mano.

En empresas.yaml:
    - nombre: Amadeus
      plataforma: workday
      host: amadeus.wd502      # lo que va antes de .myworkdayjobs.com
      tenant: amadeus          # suele coincidir con el principio del host
      sitio: jobs              # lo que va después de la barra en la URL
"""

from __future__ import annotations

import re
import time
from datetime import date, timedelta

from ..filtros import detectar_modalidad, es_practica, normalizar_ciudad
from ..modelo import Oferta
from .base import TIEMPO_MAXIMO, html_a_texto, sesion

BUSQUEDAS = ["intern", "prácticas", "becario", "trainee"]
POR_PAGINA = 20
MAX_PAGINAS = 10      # tope de seguridad: 200 ofertas por búsqueda
PAUSA = 1.0
NOMBRES_ESPANA = {"spain", "españa", "espana"}


class Workday:
    def __init__(self, host: str, tenant: str, sitio: str):
        self.web = f"https://{host}.myworkdayjobs.com/{sitio}"
        self.api = f"https://{host}.myworkdayjobs.com/wday/cxs/{tenant}/{sitio}"
        self.s = sesion()

    def buscar(self, texto: str, facetas: dict | None = None, offset: int = 0) -> dict:
        r = self.s.post(f"{self.api}/jobs", timeout=TIEMPO_MAXIMO, json={
            "appliedFacets": facetas or {}, "limit": POR_PAGINA, "offset": offset, "searchText": texto})
        r.raise_for_status()
        time.sleep(PAUSA)
        return r.json()

    def detalle(self, ruta: str) -> dict:
        r = self.s.get(f"{self.api}{ruta}", timeout=TIEMPO_MAXIMO)
        r.raise_for_status()
        time.sleep(PAUSA)
        return r.json().get("jobPostingInfo", {})


def faceta_espana(facetas: list[dict]) -> dict | None:
    """Busca recursivamente el valor "Spain" dentro de las facetas de país.

    Devuelve algo como {"locationCountry": ["bd34c5..."]} listo para appliedFacets.
    """
    for faceta in facetas or []:
        parametro = faceta.get("facetParameter", "")
        for valor in faceta.get("values", []):
            if "values" in valor:  # grupo anidado (p. ej. locationMainGroup)
                encontrado = faceta_espana([valor])
                if encontrado:
                    return encontrado
            elif "country" in parametro.lower() and valor.get("descriptor", "").lower() in NOMBRES_ESPANA:
                return {parametro: [valor["id"]]}
    return None


def fecha_desde_texto(texto: str, hoy: date | None = None) -> str:
    """'Posted 3 Days Ago' / 'Publicado hace 3 días' -> fecha ISO aproximada."""
    hoy = hoy or date.today()
    t = texto.lower()
    if "today" in t or "hoy" in t:
        return hoy.isoformat()
    if "yesterday" in t or "ayer" in t:
        return (hoy - timedelta(days=1)).isoformat()
    m = re.search(r"(\d+)\+?\s*(?:days?|días?)", t)
    return (hoy - timedelta(days=int(m.group(1)))).isoformat() if m else ""


def descargar(cfg: dict) -> list[tuple[dict, dict]]:
    """Devuelve pares (fila del listado, detalle) de las ofertas candidatas."""
    wd = Workday(cfg["host"], cfg["tenant"], cfg["sitio"])
    espana = faceta_espana(wd.buscar("", None).get("facets", []))

    filas: dict[str, dict] = {}
    for palabra in BUSQUEDAS:
        offset = 0
        for _ in range(MAX_PAGINAS):
            datos = wd.buscar(palabra, espana, offset)
            for fila in datos.get("jobPostings", []):
                filas.setdefault(fila["externalPath"], fila)
            offset += POR_PAGINA
            if offset >= datos.get("total", 0):
                break

    resultado = []
    for ruta, fila in filas.items():
        # Pedir el detalle cuesta una petición: solo lo hacemos si el título lo merece.
        if es_practica(Oferta(empresa="", titulo=fila.get("title", ""), url="")):
            resultado.append((fila, wd.detalle(ruta)))
    return resultado


def convertir(fila: dict, detalle: dict, cfg: dict) -> Oferta:
    ubicacion = detalle.get("location") or fila.get("locationsText", "")
    extra = detalle.get("additionalLocations") or []
    todas = ", ".join([ubicacion, *extra])
    pais = (detalle.get("country") or {}).get("descriptor", "")
    descripcion = html_a_texto(detalle.get("jobDescription", ""))
    url = detalle.get("externalUrl") or f"https://{cfg['host']}.myworkdayjobs.com/{cfg['sitio']}{fila['externalPath']}"
    return Oferta(
        empresa=cfg["nombre"],
        sector=cfg.get("sector", ""),
        titulo=(detalle.get("title") or fila.get("title", "")).strip(),
        url=url,
        ubicacion_original=todas.strip(", "),
        ciudad=normalizar_ciudad(todas),
        pais=pais,
        modalidad=detectar_modalidad(f"{detalle.get('remoteType', '')} {todas}"),
        fecha_publicacion=detalle.get("startDate", "")[:10] or fecha_desde_texto(fila.get("postedOn", "")),
        descripcion=descripcion,
    )


def obtener_ofertas(empresa: dict) -> list[Oferta]:
    return [convertir(f, d, empresa) for f, d in descargar(empresa)]
