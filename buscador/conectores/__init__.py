"""Registro de conectores.

Para añadir una plataforma nueva:
  1. crea buscador/conectores/<plataforma>.py copiando la forma de greenhouse.py
  2. regístrala aquí abajo
  3. en empresas.yaml pon `plataforma: <plataforma>` en las empresas que la usen
"""

from . import greenhouse, successfactors, workday

CONECTORES = {
    "greenhouse": greenhouse.obtener_ofertas,
    "successfactors": successfactors.obtener_ofertas,
    "workday": workday.obtener_ofertas,
    # "lever": lever.obtener_ofertas,              <- issue #3 para Samuel
}
