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

## Alertas por Telegram

Cada mañana, si hay ofertas nuevas, el bot te manda una por mensaje con dos
botones: **✅ Sí, prepárala** y **❌ No**. Cada 30 minutos
(`.github/workflows/respuestas.yml`) se leen los botones que has pulsado y se
guardan en `data/decisiones.json`. Al pulsar "Sí", se llama a
`buscador/candidatura.py`: Claude escribe una carta adaptada a esa oferta y a
tu CV, y te llegan por Telegram la carta en PDF, tu CV y el enlace para
aplicar. La candidatura la envías tú, después de revisar la carta.

```
búsqueda diaria ──► alertas.py ──► Telegram ──► tú pulsas ──► respuestas.py (cada 30 min) ──► candidatura.py
```

### Configurarlo (10 minutos)

1. En Telegram, habla con **@BotFather**, escribe `/newbot` y sigue los pasos.
   Te dará un **token** del tipo `123456:ABC...`. Es una contraseña: no la pegues en el código.
2. Abre el chat con tu bot nuevo y mándale `/start` (si no, no te puede escribir).
3. En el navegador, abre `https://api.telegram.org/bot<TOKEN>/getUpdates`.
   Busca `"chat":{"id":` y apunta ese número: es tu **chat id**.
4. En GitHub, ve a Settings → Secrets and variables → Actions → **New repository secret**, y crea:
   - `TELEGRAM_TOKEN` con el token
   - `TELEGRAM_CHAT_ID` con el número
5. Pruébalo: Actions → "Actualizar ofertas" → **Run workflow**.

### La carta de presentación con Claude

Más secretos, en el mismo sitio (Settings → Secrets and variables → Actions):

| Secreto | Qué es |
|---|---|
| `ANTHROPIC_API_KEY` | Tu clave de la API de Claude (console.anthropic.com). Cada carta cuesta unos céntimos. |
| `CV_TEXTO` | Opcional. Tu CV en texto. Si no está, Claude lee el PDF que le mandaste al bot. |
| `PERFIL_NOTAS` | Opcional. Lo que quieres que destaque siempre ("prefiero backend", "disponible desde febrero"...). |
| `CARTA_LUGAR` | Opcional. La ciudad que va delante de la fecha en la carta. |

**Tu CV en PDF:** mándaselo una vez al bot por el chat de Telegram. Se guarda
su identificador en `data/cv_telegram.json` (solo funciona con el token de tu
bot). Claude lo lee para escribir cada carta (solo usa lo que pone: no inventa
experiencia) y el bot te lo adjunta. Si mandas otro PDF, sustituye al anterior.

El repo es público: el CV y las cartas **nunca** se guardan en el repo ni se
imprimen en los logs. En tu ordenador puedes probar con `perfil/cv.md`
(la carpeta `perfil/` está en `.gitignore`).

### Respuestas al momento (webhook con Cloudflare, gratis)

Sin esto, los botones se leen cada 30 minutos (y GitHub a veces retrasa o se
salta esas ejecuciones programadas). Con un webhook, Telegram avisa en cuanto
pulsas algo y la carta te llega en 1 o 2 minutos. Además puedes escribir
`/buscar` para lanzar la búsqueda cuando quieras.

```
Telegram ──► worker de Cloudflare ──► GitHub Actions (repository_dispatch) ──► Telegram
```

El "worker" es un programa de 80 líneas (`webhook/worker.js`) que vive en
Cloudflare: contesta al momento y le pide a GitHub que lance el workflow.

1. **Worker:** crea una cuenta gratis en Cloudflare → *Workers & Pages* →
   *Create* → *Worker* ("Hello World") → nombre `buscador-practicas` → *Deploy*.
   Luego *Edit code*, borra lo que hay, pega `webhook/worker.js` y *Deploy*.
   Apunta su dirección: `https://buscador-practicas.<algo>.workers.dev`.
2. **Token de GitHub** (para que el worker pueda lanzar workflows): GitHub →
   Settings → Developer settings → *Fine-grained tokens* → *Generate new token*.
   Repository access: *Only select repositories* → este repo. Permissions:
   *Contents: Read and write*. Nada más.
3. **Variables del worker** (*Settings → Variables and Secrets*):

   | Nombre | Tipo | Valor |
   |---|---|---|
   | `TELEGRAM_TOKEN` | Secret | el token del bot |
   | `TELEGRAM_CHAT_ID` | Text | tu chat id |
   | `TELEGRAM_SECRET` | Secret | una contraseña que inventes (solo letras, números, `_` y `-`) |
   | `GITHUB_TOKEN` | Secret | el token del paso 2 |
   | `REPO` | Text | `samujimlop/buscador-practicas` |

4. **Conectar Telegram con el worker:** abre en el navegador (cambiando las tres partes):
   `https://api.telegram.org/bot<TOKEN>/setWebhook?url=<DIRECCIÓN_DEL_WORKER>&secret_token=<TELEGRAM_SECRET>`.
   Debe responder `"Webhook was set"`.
5. **Pruébalo:** escribe `/buscar` al bot.

Para volver al modo de cada 30 minutos: `https://api.telegram.org/bot<TOKEN>/deleteWebhook`.

**Seguridad:** cualquiera puede escribir a un bot si sabe su nombre, por eso
`respuestas.py` solo hace caso a los clics que vienen de tu `TELEGRAM_CHAT_ID`.

**Minutos de Actions:** la lectura cada 30 minutos son unas 34 ejecuciones al
día, cerca de 1.000 minutos al mes. Entra en los 2.000 minutos gratis de un
repo privado (3.000 con GitHub Pro). Si algún día se queda corto, cambia el
`cron` o pasa a webhook.

## Probarlo en tu ordenador

```bash
python -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
pytest                      # tests, sin internet
python -m buscador.main     # busca ofertas de verdad y escribe docs/ofertas.json
python -m http.server -d docs 8000   # abre http://localhost:8000
```

## Plataformas soportadas

| Plataforma | Conector | Empresas (nov. 2026) |
|---|---|---|
| SAP SuccessFactors (RSS) | `successfactors.py` | Telefónica, Indra/Minsait, CaixaBank, Deloitte, KPMG, EY |
| Greenhouse | `greenhouse.py` | Cabify, Typeform |
| Workday | `workday.py` (bloqueado desde GitHub, ver abajo) | Santander, BBVA, Repsol, Ferrovial, Acciona, Airbus, Amadeus, Accenture |

**Workday** responde `429 Too Many Requests` a las peticiones que salen de los
servidores de GitHub. No intentamos saltarnos ese bloqueo: esas empresas van
con `plataforma: manual` y la web las enseña en "Revisa también a mano" con el
enlace a su buscador. El conector funciona (tiene tests); si algún día lo
ejecutas desde tu ordenador, cambia `manual` por `workday` en `empresas.yaml`.

Para probar conectores contra las webs reales sin guardar nada:
Actions → **Probar conectores** → Run workflow.

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
