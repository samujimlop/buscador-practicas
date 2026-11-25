"""Tests del conector de SuccessFactors con un RSS guardado (sin internet)."""
import xml.etree.ElementTree as ET
from pathlib import Path

from buscador.conectores import successfactors
from buscador.filtros import nos_interesa

FIXTURE = Path(__file__).parent / "fixtures" / "successfactors_ejemplo.xml"
EMPRESA = {"nombre": "Ejemplo", "sector": "Telecomunicaciones", "plataforma": "successfactors",
           "portal": "https://jobs.ejemplo.com"}


def _crudos():
    return [{c: (i.findtext(c) or "").strip() for c in ("title", "link", "description", "pubDate")}
            for i in ET.parse(FIXTURE).iter("item")]


def test_separa_titulo_y_lugar():
    assert successfactors.separar_titulo("Prácticas I+D (La Coruña, ES, 15003)") == ("Prácticas I+D", "La Coruña, ES, 15003")
    assert successfactors.separar_titulo("Sin lugar") == ("Sin lugar", "")


def test_convierte():
    o = successfactors.convertir(_crudos()[0], EMPRESA)
    assert o.titulo == "Prácticas Desarrollo Backend Java"
    assert o.ciudad == "Madrid" and o.pais == "Spain"
    assert o.fecha_publicacion == "2026-11-24"
    assert o.modalidad == "híbrido"
    assert "<" not in o.descripcion


def test_filtra_practicas_it_en_espana():
    ofertas = [successfactors.convertir(c, EMPRESA) for c in _crudos()]
    assert [o.titulo for o in ofertas if nos_interesa(o)] == ["Prácticas Desarrollo Backend Java"]
    # Fuera: administrativa (no IT), Lisboa (no España), senior (no prácticas)


def test_descargar_junta_busquedas_sin_duplicados(monkeypatch):
    class Resp:
        content = FIXTURE.read_bytes()
        def raise_for_status(self): pass

    class Sesion:
        headers = {}
        llamadas = []
        def get(self, url, params, timeout):
            self.llamadas.append(params["keywords"]); return Resp()

    s = Sesion()
    monkeypatch.setattr(successfactors, "sesion", lambda: s)
    monkeypatch.setattr(successfactors, "PAUSA", 0)
    crudos = successfactors.descargar("https://jobs.ejemplo.com/", ["prácticas", "intern"])
    assert len(crudos) == 4  # las dos búsquedas devuelven lo mismo: sin duplicar
    assert s.llamadas == ["(prácticas)", "(intern)"]


def test_xml_roto_no_pierde_ofertas():
    roto = FIXTURE.read_text(encoding="utf-8").replace("Python.", "R&D sin escapar")
    crudos = successfactors.leer_items(roto)
    assert len(crudos) == 4
    assert crudos[0]["title"] == "Prácticas Desarrollo Backend Java (Madrid, ES, 28050)"
    assert crudos[0]["link"].endswith("/111/")
