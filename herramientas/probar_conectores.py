"""Ejecuta los conectores reales y enseña qué sale (no guarda nada).

Uso: python -m herramientas.probar_conectores [Empresa ...]
"""
import logging
import sys

from buscador.conectores import CONECTORES
from buscador.filtros import es_en_espana, es_practica, nos_interesa
from buscador.main import cargar_empresas

logging.basicConfig(level=logging.INFO)
solo = set(sys.argv[1:])
for e in cargar_empresas():
    f = CONECTORES.get(e.get("plataforma"))
    if not f or (solo and e["nombre"] not in solo):
        continue
    try:
        ofertas = f(e)
    except Exception as err:
        print(f"### {e['nombre']}: ERROR {err}")
        continue
    buenas = [o for o in ofertas if nos_interesa(o)]
    print(f"### {e['nombre']}: {len(ofertas)} descargadas, {sum(es_practica(o) for o in ofertas)} prácticas, "
          f"{sum(es_en_espana(o) for o in ofertas)} en España, {len(buenas)} prácticas IT en España")
    for o in buenas[:8]:
        print(f"    + {o.titulo[:70]} | {o.ciudad or o.ubicacion_original[:30]} | {o.fecha_publicacion}")
    for o in [o for o in ofertas if es_practica(o) and es_en_espana(o) and not nos_interesa(o)][:4]:
        print(f"    - (no IT) {o.titulo[:70]}")
