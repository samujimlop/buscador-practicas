"""Registro de conectores.

Para añadir una plataforma nueva:
  1. crea buscador/conectores/<plataforma>.py copiando la forma de greenhouse.py
  2. regístrala aquí abajo
  3. en empresas.yaml pon `plataforma: <plataforma>` en las empresas que la usen
"""

from . import greenhouse

CONECTORES = {
    "greenhouse": greenhouse.obtener_ofertas,
    # "workday": workday.obtener_ofertas,          <- issue para Samuel
    # "lever": lever.obtener_ofertas,              <- issue para Samuel
    # "successfactors": successfactors.obtener_ofertas,
}
