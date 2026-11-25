"""Decidir qué ofertas nos interesan y limpiar la ciudad.

Aquí no hay magia: son listas de palabras. Si ves que se cuela algo que no
es de prácticas, o que se escapa algo que sí lo es, añade o quita palabras
y añade un test en tests/test_filtros.py con ese caso.
"""

from __future__ import annotations

import re
import unicodedata

from .modelo import Oferta


def _sin_acentos(texto: str) -> str:
    """'Prácticas en Málaga' -> 'practicas en malaga' (más fácil de comparar)."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def _patron(palabra: str) -> str:
    """Palabra completa, salvo si acaba en * (entonces vale como prefijo).

    \b es "límite de palabra": así "intern" no encaja en "international",
    pero "ingenier*" sí encaja en "ingeniero", "ingeniera" e "ingeniería".
    """
    if palabra.endswith("*"):
        return rf"\b{re.escape(palabra[:-1])}"
    return rf"\b{re.escape(palabra)}\b"


def _contiene_alguna(texto: str, palabras: list[str]) -> bool:
    texto = _sin_acentos(texto)
    return any(re.search(_patron(p), texto) for p in palabras)


# --- ¿Es una oferta de prácticas? -----------------------------------------

PALABRAS_PRACTICAS = [
    "practica", "practicas", "beca", "becas", "becari*",
    "intern", "interns", "internship*", "trainee*", "student", "estudiante*",
    "graduate program", "programa de graduados", "working student", "placement",
]

# Si el título dice esto, casi seguro no es para estudiantes.
PALABRAS_EXCLUIR = [
    "senior", "sr", "lead", "manager", "director", "head of",
    "principal", "staff engineer", "jefe", "responsable",
]


def es_practica(oferta: Oferta) -> bool:
    if _contiene_alguna(oferta.titulo, PALABRAS_EXCLUIR):
        return False
    # El título manda; la descripción solo cuenta si el título es ambiguo.
    if _contiene_alguna(oferta.titulo, PALABRAS_PRACTICAS):
        return True
    return _contiene_alguna(oferta.descripcion[:600], ["practicas", "beca", "internship*"])


# --- ¿Es de informática? ----------------------------------------------------

PALABRAS_INFORMATICA = [
    "software", "developer*", "desarroll*", "programad*", "programming",
    "engineer*", "ingenier*", "informatic*", "computer", "it", "tech", "technology",
    "tecnolog*", "ciberseguridad", "ai engineer", "software engineer",
    "data", "datos", "machine learning", "ia", "ai", "inteligencia artificial",
    "cloud", "devops", "backend", "back-end", "frontend", "front-end",
    "full stack", "fullstack", "ciberseguridad", "cybersecurity", "security",
    "sistemas", "systems", "qa", "testing", "mobile", "android", "ios", "web",
    "digital", "sap", "analytics",
]


def es_informatica(oferta: Oferta) -> bool:
    texto = f"{oferta.titulo} {oferta.departamento}"
    if _contiene_alguna(texto, PALABRAS_INFORMATICA):
        return True
    return _contiene_alguna(oferta.descripcion[:1500], ["software", "programacion", "python", "java"])


# --- Ciudad -----------------------------------------------------------------

# Clave: cómo puede aparecer escrita (sin acentos, minúsculas). Valor: nombre limpio.
CIUDADES = {
    "madrid": "Madrid", "alcobendas": "Madrid", "las rozas": "Madrid",
    "boadilla": "Madrid", "tres cantos": "Madrid", "pozuelo": "Madrid",
    "getafe": "Madrid", "majadahonda": "Madrid", "san sebastian de los reyes": "Madrid",
    "barcelona": "Barcelona", "sant cugat": "Barcelona", "martorell": "Barcelona",
    "l'hospitalet": "Barcelona", "hospitalet": "Barcelona",
    "valencia": "Valencia", "paterna": "Valencia",
    "sevilla": "Sevilla", "seville": "Sevilla",
    "malaga": "Málaga", "bilbao": "Bilbao", "zaragoza": "Zaragoza",
    "valladolid": "Valladolid", "alicante": "Alicante", "murcia": "Murcia",
    "a coruna": "A Coruña", "la coruna": "A Coruña", "arteixo": "A Coruña",
    "vigo": "Vigo", "oviedo": "Oviedo", "gijon": "Gijón", "santander": "Santander",
    "granada": "Granada", "cordoba": "Córdoba", "salamanca": "Salamanca",
    "pamplona": "Pamplona", "san sebastian": "San Sebastián", "donostia": "San Sebastián",
    "vitoria": "Vitoria", "palma": "Palma", "las palmas": "Las Palmas",
    "tenerife": "Santa Cruz de Tenerife", "albacete": "Albacete", "huelva": "Huelva",
    "cadiz": "Cádiz", "algeciras": "Cádiz", "leon": "León", "burgos": "Burgos",
    "tarragona": "Tarragona", "girona": "Girona", "castellon": "Castellón",
    "logrono": "Logroño", "sabadell": "Barcelona", "terrassa": "Barcelona",
    "badalona": "Barcelona", "cornella": "Barcelona", "el prat": "Barcelona",
    "leganes": "Madrid", "alcala de henares": "Madrid", "torrejon": "Madrid",
    "mostoles": "Madrid", "alcorcon": "Madrid", "fuenlabrada": "Madrid",
    "boecillo": "Valladolid", "aviles": "Asturias", "asturias": "Asturias",
    "toledo": "Toledo", "ciudad real": "Ciudad Real", "cuenca": "Cuenca",
    "guadalajara": "Guadalajara", "jaen": "Jaén", "almeria": "Almería",
    "badajoz": "Badajoz", "caceres": "Cáceres", "lugo": "Lugo", "ourense": "Ourense",
    "pontevedra": "Pontevedra", "lleida": "Lleida", "huesca": "Huesca", "teruel": "Teruel",
    "soria": "Soria", "segovia": "Segovia", "avila": "Ávila", "zamora": "Zamora",
    "palencia": "Palencia", "elche": "Alicante", "cartagena": "Murcia",
}

PALABRAS_ESPANA = ["spain", "espana", "espanya"]


def normalizar_ciudad(ubicacion: str) -> str:
    """'Madrid, Community of Madrid, Spain' -> 'Madrid'. Si no la conoce, ''.

    Si aparecen varias ciudades ("Madrid, Barcelona"), gana la PRIMERA que se
    menciona. Si dos claves empiezan en el mismo sitio, gana la más larga:
    "san sebastian de los reyes" (Madrid) antes que "san sebastian" (Gipuzkoa).
    """
    texto = _sin_acentos(ubicacion)
    mejor = None  # (posición, -longitud, ciudad)
    for clave, ciudad in CIUDADES.items():
        m = re.search(rf"\b{re.escape(clave)}\b", texto)
        if m:
            candidato = (m.start(), -len(clave), ciudad)
            mejor = min(mejor, candidato) if mejor else candidato
    return mejor[2] if mejor else ""


def es_en_espana(oferta: Oferta) -> bool:
    if oferta.ciudad:
        return True
    texto = _sin_acentos(f"{oferta.ubicacion_original} {oferta.pais}")
    return any(p in texto for p in PALABRAS_ESPANA)


def detectar_modalidad(texto: str) -> str:
    texto = _sin_acentos(texto)
    if "hibrid" in texto or "hybrid" in texto:
        return "híbrido"
    if "remot" in texto or "remote" in texto or "teletrabajo" in texto:
        return "remoto"
    return ""


def nos_interesa(oferta: Oferta) -> bool:
    return es_en_espana(oferta) and es_practica(oferta) and es_informatica(oferta)
