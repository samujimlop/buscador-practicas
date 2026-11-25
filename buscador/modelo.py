"""El formato común de una oferta.

Cada conector habla con una plataforma distinta (Greenhouse, Workday...)
y cada una devuelve los datos a su manera. Para que el resto del programa
no tenga que saber nada de eso, todos los conectores devuelven objetos
`Oferta`, siempre con los mismos campos.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field


MAX_DESCRIPCION = 4000  # caracteres: suficiente para la carta, sin inflar ofertas.json


@dataclass
class Oferta:
    empresa: str
    titulo: str
    url: str
    ciudad: str = ""          # ya normalizada: "Madrid", "Barcelona"... o "" si no se sabe
    ubicacion_original: str = ""  # el texto tal cual lo da la empresa, por si acaso
    pais: str = ""
    sector: str = ""
    departamento: str = ""
    modalidad: str = ""       # "presencial", "híbrido", "remoto" o ""
    fecha_publicacion: str = ""  # ISO 8601 (AAAA-MM-DD) si la plataforma la da
    descripcion: str = ""     # texto plano, se usa para filtrar y no se publica entero
    primera_vez_vista: str = ""  # la rellena main.py, no el conector
    etiquetas: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        """Identificador estable: la misma oferta siempre da el mismo id.

        Usamos la URL porque es lo único que no cambia entre ejecuciones.
        """
        return hashlib.sha1(self.url.encode("utf-8")).hexdigest()[:12]

    def a_dict(self) -> dict:
        datos = asdict(self)
        datos["id"] = self.id
        # Guardamos la descripción (recortada) porque la carta de presentación
        # la necesita cuando pulsas "Sí". La web no la enseña.
        datos["descripcion"] = self.descripcion[:MAX_DESCRIPCION]
        return datos
