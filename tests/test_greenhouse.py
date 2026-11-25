"""Tests del conector de Greenhouse, sin internet.

Usamos un JSON guardado con la misma forma que devuelve la API real.
Así el test no depende de que la empresa tenga ofertas hoy.
"""

import json
from pathlib import Path

from buscador.conectores import greenhouse
from buscador.filtros import nos_interesa

FIXTURE = Path(__file__).parent / "fixtures" / "greenhouse_ejemplo.json"
EMPRESA = {"nombre": "Ejemplo", "sector": "Tecnología", "plataforma": "greenhouse", "board": "ejemplo"}


def _ofertas():
    crudos = json.loads(FIXTURE.read_text(encoding="utf-8"))["jobs"]
    return [greenhouse.convertir(c, EMPRESA) for c in crudos]


def test_convierte_campos_basicos():
    primera = _ofertas()[0]
    assert primera.empresa == "Ejemplo"
    assert primera.titulo == "Software Engineer Intern"
    assert primera.ciudad == "Madrid"
    assert primera.fecha_publicacion == "2026-11-02"
    assert "Ingeniería Informática" in primera.descripcion
    assert "<" not in primera.descripcion  # sin etiquetas HTML


def test_filtra_solo_practicas_it_en_espana():
    titulos = [o.titulo for o in _ofertas() if nos_interesa(o)]
    assert titulos == ["Software Engineer Intern", "Becario/a Desarrollo Web (Híbrido)"]
    # Fuera: Senior (no es prácticas), Marketing (no es IT), Lisboa (no es España)


def test_detecta_modalidad():
    becario = _ofertas()[4]
    assert becario.ciudad == "Valencia"
    assert becario.modalidad == "híbrido"


def test_obtener_ofertas_usa_el_board(monkeypatch):
    llamado_con = {}

    def falso_descargar(board):
        llamado_con["board"] = board
        return json.loads(FIXTURE.read_text(encoding="utf-8"))["jobs"]

    monkeypatch.setattr(greenhouse, "descargar", falso_descargar)
    assert len(greenhouse.obtener_ofertas(EMPRESA)) == 5
    assert llamado_con["board"] == "ejemplo"
