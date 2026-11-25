"""Prueba educada de los portales SuccessFactors (RMK / jobs2web): una petición por URL."""
import re, time, requests
UA = "buscador-practicas/0.1 (proyecto personal de estudiante)"
SITIOS = {
    "Telefónica": "https://jobs.telefonica.com",
    "Indra": "https://careers.indragroup.com",
    "CaixaBank": "https://caixabankcareers.com",
    "Deloitte": "https://empleo.es.deloitte.com",
    "KPMG": "https://carreras.kpmg.es",
    "EY": "https://careers.ey.com",
}
for nombre, base in SITIOS.items():
    for ruta in ["/search/?q=pr%C3%A1cticas&locationsearch=&sortColumn=referencedate&sortDirection=desc",
                 "/services/rss/job/?locale=es_ES&keywords=(pr%C3%A1cticas)"]:
        try:
            r = requests.get(base + ruta, headers={"User-Agent": UA}, timeout=30)
            filas = re.findall(r'class="jobTitle-link[^"]*"\s+href="([^"]+)"[^>]*>([^<]+)<', r.text)
            items = re.findall(r"<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>", r.text, re.S)
            locs = re.findall(r'class="jobLocation[^"]*"[^>]*>\s*([^<]+?)\s*<', r.text)
            total = re.search(r'(\d+)\s*</b>\s*(?:de|of)\s*<b>\s*(\d+)', r.text) or re.search(r'paginationLabel[^>]*>([^<]+)<', r.text)
            print(f"### {nombre} {ruta[:30]} -> {r.status_code} {r.headers.get('content-type','')[:30]} filas={len(filas)} rss={len(items)} total={total.group(0)[:60] if total else None}")
            for href, t in filas[:3]: print("     ", t.strip()[:70], "|", href[:80])
            for l in locs[:3]: print("      loc:", l[:60])
            for t, l in items[:3]: print("      rss:", t.strip()[:70], "|", l.strip()[:80])
        except Exception as e:
            print(f"### {nombre} {ruta[:30]} ERROR {e}")
        time.sleep(3)
