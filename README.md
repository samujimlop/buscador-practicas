# Buscador de prácticas

Recoge cada mañana las ofertas de **prácticas de informática** publicadas en los
portales de empleo propios de grandes empresas de toda España (no en InfoJobs
ni LinkedIn) y las enseña en una web con filtros por ciudad, empresa y sector.

## Cómo funciona

```
empresas.yaml ──► conectores ──► formato común ──► filtros ──► docs/ofertas.json ──► docs/index.html
 (qué vigilar)    (uno por        (Oferta)         (prácticas    (lo que lee           (la web)
                   plataforma)                      + IT + España) la web)
```

1. **`empresas.yaml`** dice qué empresas vigilar y con qué plataforma publican.
2. **Conectores** (`buscador/conectores/`): las empresas no programan su portal,
   lo montan sobre plataformas como Workday, SuccessFactors o Greenhouse. Cada
   plataforma tiene una API (normalmente JSON) igual para todos sus clientes,
   así que **un conector cubre todas las empresas de esa plataforma**.
3. **Formato común** (`buscador/modelo.py`): cada conector traduce sus datos a
   una `Oferta` con los mismos campos. El resto del programa no sabe de dónde
   vino cada oferta.
4. **Filtros** (`buscador/filtros.py`): listas de palabras para quedarse con
   prácticas (beca, intern, becario...) de informática (software, datos,
   ciberseguridad...) en España, y para limpiar la ciudad ("Alcobendas" → Madrid).
5. **`buscador/main.py`** lo junta todo, recuerda qué ofertas ya había ayer
   (para marcar las nuevas) y escribe `docs/ofertas.json`.
6. **GitHub Actions** (`.github/workflows/actualizar.yml`) lo ejecuta cada día a
   las 07:30 y **GitHub Pages** publica la carpeta `docs/` como web.

Si una empresa falla un día (web caída, cambio de API), las demás siguen y se
conservan sus ofertas de ayer. La web enseña el estado de cada empresa abajo.

## Probarlo en tu ordenador

```bash
python -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
pytest                      # tests, sin internet
python -m buscador.main     # busca ofertas de verdad y escribe docs/ofertas.json
python -m http.server -d docs 8000   # abre http://localhost:8000
```

## Añadir una empresa

Si su plataforma ya tiene conector, basta con añadirla a `empresas.yaml`.
Si no, primero hay que averiguar la plataforma: abre su página de ofertas,
pulsa F12 → pestaña **Red / Network** → filtra por **Fetch/XHR** y recarga.
El dominio al que llama la página te lo dice:

| Si ves...                         | Es...           |
|-----------------------------------|-----------------|
| `myworkdayjobs.com`               | Workday         |
| `greenhouse.io`                   | Greenhouse      |
| `lever.co`                        | Lever           |
| `successfactors` / `jobs.sap.com` | SuccessFactors  |
| `phenompeople` / `/widgets`       | Phenom          |
| `eightfold.ai`                    | Eightfold       |

## Escribir un conector nuevo

Copia la forma de `buscador/conectores/greenhouse.py`:

- `descargar(...)` habla con la plataforma y devuelve los datos crudos.
- `convertir(crudo, empresa)` pasa **una** oferta cruda a `Oferta`.
- `obtener_ofertas(empresa)` junta las dos.

Guarda una respuesta real de la API en `tests/fixtures/` y escribe un test de
`convertir()` como en `tests/test_greenhouse.py`. Regístralo en
`buscador/conectores/__init__.py`. Las tareas pendientes están en
[TAREAS.md](TAREAS.md).

## Buenas maneras

Es un proyecto personal que hace una petición por empresa al día y se
identifica en el `User-Agent`. Respeta eso: nada de ejecutarlo en bucle.
