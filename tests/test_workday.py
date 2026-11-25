"""Tests del conector de Workday con respuestas de ejemplo (sin internet)."""
from datetime import date

from buscador.conectores import workday
from buscador.filtros import nos_interesa

CFG = {"nombre": "Ejemplo", "sector": "Tecnología", "plataforma": "workday",
       "host": "ejemplo.wd3", "tenant": "ejemplo", "sitio": "Careers"}

FACETAS = [
    {"facetParameter": "jobFamilyGroup", "values": [{"descriptor": "IT", "id": "x1", "count": 4}]},
    {"facetParameter": "locationMainGroup", "values": [
        {"facetParameter": "locationCountry", "descriptor": "País", "values": [
            {"descriptor": "France", "id": "fr1", "count": 3},
            {"descriptor": "Spain", "id": "es1", "count": 5}]}]},
]


def test_encuentra_faceta_espana_anidada():
    assert workday.faceta_espana(FACETAS) == {"locationCountry": ["es1"]}
    assert workday.faceta_espana([]) is None


def test_fecha_desde_texto():
    hoy = date(2026, 11, 25)
    assert workday.fecha_desde_texto("Posted Today", hoy) == "2026-11-25"
    assert workday.fecha_desde_texto("Posted Yesterday", hoy) == "2026-11-24"
    assert workday.fecha_desde_texto("Posted 30+ Days Ago", hoy) == "2026-10-26"
    assert workday.fecha_desde_texto("", hoy) == ""


def test_descargar_pagina_filtra_y_pide_detalle(monkeypatch):
    llamadas = []

    class Falso:
        def __init__(self, *a):
            pass

        def buscar(self, texto, facetas=None, offset=0):
            llamadas.append((texto, facetas, offset))
            if texto == "":
                return {"total": 0, "facets": FACETAS, "jobPostings": []}
            if texto != "intern":
                return {"total": 0, "jobPostings": []}
            pagina = [
                {"title": "Software Intern", "externalPath": "/job/Madrid/Software-Intern_R1", "locationsText": "Madrid"},
                {"title": "Senior Engineer", "externalPath": "/job/Madrid/Senior_R2", "locationsText": "Madrid"},
            ] if offset == 0 else [
                {"title": "Data Intern", "externalPath": "/job/Barcelona/Data-Intern_R3", "locationsText": "2 Locations"},
            ]
            return {"total": 21, "jobPostings": pagina}

        def detalle(self, ruta):
            return {"title": ruta.split("/")[-1], "location": "Madrid", "country": {"descriptor": "Spain"},
                    "jobDescription": "<p>Python</p>", "startDate": "2026-11-20"}

    monkeypatch.setattr(workday, "Workday", Falso)
    pares = workday.descargar(CFG)
    assert [f["externalPath"] for f, _ in pares] == ["/job/Madrid/Software-Intern_R1", "/job/Barcelona/Data-Intern_R3"]
    assert ("intern", {"locationCountry": ["es1"]}, 20) in llamadas  # segunda página, con filtro España


def test_convertir():
    fila = {"title": "Software Intern", "externalPath": "/job/Madrid/Software-Intern_R1",
            "locationsText": "2 Locations", "postedOn": "Posted 3 Days Ago"}
    detalle = {"title": "Software Engineering Intern", "location": "Madrid", "additionalLocations": ["Barcelona"],
               "country": {"descriptor": "Spain"}, "jobDescription": "<p>Java &amp; Python</p>",
               "startDate": "2026-11-20", "externalUrl": "https://ejemplo.wd3.myworkdayjobs.com/Careers/job/R1"}
    o = workday.convertir(fila, detalle, CFG)
    assert o.titulo == "Software Engineering Intern"
    assert o.ciudad == "Madrid" and o.ubicacion_original == "Madrid, Barcelona"
    assert o.fecha_publicacion == "2026-11-20"
    assert o.descripcion == "Java & Python"
    assert nos_interesa(o)
