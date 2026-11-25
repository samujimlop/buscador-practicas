import pytest

from buscador.filtros import es_informatica, es_practica, normalizar_ciudad
from buscador.main import ejecutar
from buscador.modelo import Oferta


def oferta(titulo, ubicacion="Madrid, Spain", **extra):
    return Oferta(empresa="X", titulo=titulo, url=f"https://x/{titulo}",
                  ubicacion_original=ubicacion, ciudad=normalizar_ciudad(ubicacion), **extra)


@pytest.mark.parametrize("titulo", [
    "Prácticas Desarrollo Java", "Beca Ciberseguridad", "Software Engineering Intern",
    "Becario/a Data Analytics", "IT Trainee",
])
def test_si_son_practicas(titulo):
    assert es_practica(oferta(titulo))


@pytest.mark.parametrize("titulo", [
    "Senior Data Engineer", "Engineering Manager", "International Sales Executive",
])
def test_no_son_practicas(titulo):
    assert not es_practica(oferta(titulo))


def test_informatica():
    assert es_informatica(oferta("Becario Desarrollo Backend"))
    assert not es_informatica(oferta("Becario Recursos Humanos"))


@pytest.mark.parametrize("texto,esperado", [
    ("Madrid, Community of Madrid, Spain", "Madrid"),
    ("Alcobendas", "Madrid"),
    ("San Sebastián de los Reyes, Madrid", "Madrid"),
    ("Donostia-San Sebastián", "San Sebastián"),
    ("Málaga, Andalucía", "Málaga"),
    ("Arteixo, A Coruña", "A Coruña"),
    ("Remote - EMEA", ""),
])
def test_normalizar_ciudad(texto, esperado):
    assert normalizar_ciudad(texto) == esperado


def test_ejecutar_conserva_fecha_de_primera_vez_y_aguanta_fallos(monkeypatch):
    from buscador import main

    buena = oferta("Software Intern")
    monkeypatch.setitem(main.CONECTORES, "falsa", lambda e: [buena])

    def rota(e):
        raise RuntimeError("timeout")

    monkeypatch.setitem(main.CONECTORES, "rota", rota)
    empresas = [
        {"nombre": "X", "plataforma": "falsa"},
        {"nombre": "Caída", "plataforma": "rota"},
        {"nombre": "Sin conector", "plataforma": "pendiente"},
    ]
    de_ayer = {"id": "zzz", "empresa": "Caída", "titulo": "Beca IT", "primera_vez_vista": "2026-11-01",
               "fecha_publicacion": ""}

    dia1 = ejecutar(empresas, {"ofertas": [de_ayer]}, hoy="2026-11-18")
    assert {o["empresa"] for o in dia1["ofertas"]} == {"X", "Caída"}  # la caída conserva lo de ayer
    assert [e["estado"] for e in dia1["estado"]] == ["ok", "error", "sin conector"]

    dia2 = ejecutar(empresas, dia1, hoy="2026-11-19")
    nueva = next(o for o in dia2["ofertas"] if o["empresa"] == "X")
    assert nueva["primera_vez_vista"] == "2026-11-18"  # no se resetea al volver a verla


def test_no_confunde_technician_con_informatica():
    assert not es_informatica(oferta("Electronics Maintenance Technician Trainee"))
    assert es_informatica(oferta("Beca Talentum - AI engineer - AI Native SOC"))
    assert es_informatica(oferta("Prácticas en Tecnología & Transformación"))


def test_primera_ciudad_mencionada():
    assert normalizar_ciudad("Madrid, Barcelona") == "Madrid"
    assert normalizar_ciudad("LOGROÑO") == "Logroño"
