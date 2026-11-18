# Tareas para Samuel

Cuando exista el repositorio, cada una de estas será una issue. Hazlas en
una rama propia y abre un pull request: lo reviso y te comento.

## 1. Verificar los `board` de Greenhouse (calentamiento, ~30 min)
En `empresas.yaml` hay tres empresas con `verificado: false`. Para cada una,
abre `https://boards-api.greenhouse.io/v1/boards/<board>/jobs` en el navegador.
Si devuelve JSON con ofertas, pon `verificado: true`. Si da 404, busca su
página de empleo real y su `board` correcto, o cámbiala a `pendiente`.
Busca tres scaleups españolas más que usen Greenhouse y añádelas.

## 2. Conector de Lever (fácil)
API pública: `https://api.lever.co/v0/postings/<empresa>?mode=json`.
Mismo patrón que Greenhouse: `descargar`, `convertir`, `obtener_ofertas`,
fixture y test. Pista: la ubicación está en `categories.location` y la fecha
en `createdAt` (milisegundos desde 1970).

## 3. Conector de Workday (el importante)
Muchas grandes empresas lo usan. La página es
`https://<empresa>.wd3.myworkdayjobs.com/<sitio>` y por debajo hace un
**POST** a `https://<empresa>.wd3.myworkdayjobs.com/wday/cxs/<empresa>/<sitio>/jobs`
con un JSON como `{"limit": 20, "offset": 0, "searchText": "intern"}`.
Retos: **paginar** (repetir subiendo `offset` hasta que no haya más) y que el
número `wd3` cambia según la empresa (wd1, wd3, wd5...), así que debe ir en
`empresas.yaml`. Compruébalo con la pestaña Red antes de escribir código.

## 4. Identificar plataformas de las empresas "pendiente"
Con el truco de F12 → Red del README, rellena `plataforma` para las grandes
(Telefónica, Santander, BBVA, Iberdrola, Repsol, Indra, Amadeus...). Aunque
aún no haya conector, saberlo nos dice cuál conviene escribir antes.

## 5. Más adelante
- Conector de SuccessFactors o Phenom (según lo que salga en la tarea 4).
- Alertas por Telegram cuando aparezca una oferta nueva.
- Afinar `filtros.py` con casos reales que se cuelen o se escapen (siempre con test).
