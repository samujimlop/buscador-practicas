"""Punto de entrada: python -m buscador.main

Pasos:
  1. Lee empresas.yaml
  2. Para cada empresa, llama al conector de su plataforma
  3. Se queda con las prácticas de informática en España (filtros.py)
  4. Lo compara con la ejecución anterior para marcar las ofertas nuevas
  5. Escribe docs/ofertas.json, que es lo que lee la web
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import alertas, telegram
from .conectores import CONECTORES
from .filtros import nos_interesa

RAIZ = Path(__file__).resolve().parent.parent
FICHERO_EMPRESAS = RAIZ / "empresas.yaml"
FICHERO_SALIDA = RAIZ / "docs" / "ofertas.json"

log = logging.getLogger("buscador")


def cargar_empresas(ruta: Path = FICHERO_EMPRESAS) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)["empresas"]


def cargar_anterior(ruta: Path = FICHERO_SALIDA) -> dict:
    if not ruta.exists():
        return {"ofertas": []}
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def ejecutar(empresas: list[dict], anterior: dict, hoy: str) -> dict:
    vistas_antes = {o["id"]: o for o in anterior.get("ofertas", [])}
    ofertas: list[dict] = []
    estado: list[dict] = []

    for empresa in empresas:
        plataforma = empresa.get("plataforma", "pendiente")
        conector = CONECTORES.get(plataforma)
        if conector is None:
            # "manual": la plataforma no deja leerla automáticamente; la web enseña el enlace.
            estado.append({
                "empresa": empresa["nombre"],
                "estado": "a mano" if plataforma == "manual" else "sin conector",
                "plataforma": plataforma,
                "web": empresa.get("web", ""),
                "sector": empresa.get("sector", ""),
            })
            continue

        try:
            todas = conector(empresa)
        except Exception as error:  # una empresa caída no debe parar las demás
            log.warning("Fallo en %s: %s", empresa["nombre"], error)
            # Conservamos sus ofertas de ayer: un fallo puntual no significa
            # que las ofertas hayan desaparecido.
            ofertas += [o for o in vistas_antes.values() if o["empresa"] == empresa["nombre"]]
            estado.append({"empresa": empresa["nombre"], "estado": "error", "detalle": str(error)[:200]})
            continue

        interesantes = [o for o in todas if nos_interesa(o)]
        for oferta in interesantes:
            previa = vistas_antes.get(oferta.id)
            oferta.primera_vez_vista = previa["primera_vez_vista"] if previa else hoy
            ofertas.append(oferta.a_dict())

        log.info("%s: %d ofertas, %d de prácticas IT", empresa["nombre"], len(todas), len(interesantes))
        estado.append({
            "empresa": empresa["nombre"], "estado": "ok",
            "total": len(todas), "practicas_it": len(interesantes),
        })

    ofertas.sort(key=lambda o: (o["primera_vez_vista"], o["fecha_publicacion"]), reverse=True)
    return {
        "actualizado": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "ofertas": ofertas,
        "estado": estado,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    hoy = datetime.now(timezone.utc).date().isoformat()
    anterior = cargar_anterior()
    resultado = ejecutar(cargar_empresas(), anterior, hoy)

    FICHERO_SALIDA.parent.mkdir(exist_ok=True)
    with open(FICHERO_SALIDA, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=1)

    log.info("Guardadas %d ofertas en %s", len(resultado["ofertas"]), FICHERO_SALIDA)
    avisar_nuevas(anterior, resultado)
    if os.environ.get("GITHUB_EVENT_NAME") == "repository_dispatch":
        resumen_de_busqueda(anterior, resultado)  # la pediste con /buscar
    return 0


def ofertas_nuevas(anterior: dict, resultado: dict) -> list[dict]:
    """Las que no estaban en la ejecución anterior."""
    ids_antes = {o["id"] for o in anterior.get("ofertas", [])}
    return [o for o in resultado["ofertas"] if o["id"] not in ids_antes]


def avisar_nuevas(anterior: dict, resultado: dict) -> None:
    nuevas = ofertas_nuevas(anterior, resultado)
    if anterior.get("actualizado") is None:
        # Primera ejecución: todo es "nuevo". Mejor un resumen que 50 mensajes.
        if nuevas and telegram.configurado():
            telegram.enviar(f"👋 Primera búsqueda hecha: {len(nuevas)} ofertas de prácticas IT. "
                            "Míralas en la web; a partir de mañana te aviso solo de las nuevas.")
        return
    alertas.avisar(nuevas)


def resumen_de_busqueda(anterior: dict, resultado: dict) -> None:
    """Cuando lanzas la búsqueda a mano desde Telegram, te contestamos siempre."""
    if not telegram.configurado():
        return
    nuevas = len(ofertas_nuevas(anterior, resultado))
    fallos = sum(1 for e in resultado["estado"] if e["estado"] == "error")
    texto = (f"🔎 Búsqueda terminada: {len(resultado['ofertas'])} prácticas IT en total, "
             f"{nuevas} nuevas" + (f" ({nuevas} avisos arriba)." if nuevas else "."))
    if fallos:
        texto += f"\n⚠️ {fallos} empresas han fallado hoy (lo verás en la web)."
    telegram.enviar(texto)


if __name__ == "__main__":
    sys.exit(main())
