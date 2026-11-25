"""Detecta qué plataforma de empleo (ATS) usa cada empresa.

Abre la página de empleo, busca "huellas" de plataformas conocidas en el HTML
y en los enlaces, y sigue un nivel los enlaces que parecen de ofertas.
Uso: python herramientas/detectar_plataformas.py
"""
import re
import sys
from urllib.parse import urljoin

import requests

HUELLAS = {
    "workday": r"[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com[^\"'\s<]*",
    "successfactors": r"(?:career\d*\.successfactors\.(?:com|eu)|jobs\.sap\.com|[a-z0-9.-]*\.jobs2web\.com|rmkcdn\.successfactors)[^\"'\s<]*",
    "greenhouse": r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/[^\"'\s<]*",
    "lever": r"jobs(?:\.eu)?\.lever\.co/[^\"'\s<]*",
    "phenom": r"(?:phenompeople\.com|cdn\.phenompeople|/widgets\b|phApp)[^\"'\s<]{0,60}",
    "eightfold": r"[a-z0-9-]+\.eightfold\.ai[^\"'\s<]*",
    "smartrecruiters": r"(?:jobs|careers)\.smartrecruiters\.com/[^\"'\s<]*",
    "teamtailor": r"[a-z0-9-]+\.teamtailor\.com[^\"'\s<]*",
    "taleo": r"[a-z0-9-]+\.taleo\.net[^\"'\s<]*",
    "avature": r"[a-z0-9-]+\.avature\.net[^\"'\s<]*",
    "cornerstone": r"[a-z0-9-]+\.csod\.com[^\"'\s<]*",
    "oracle_hcm": r"[a-z0-9-]+\.fa\.[a-z0-9-]+\.oraclecloud\.com[^\"'\s<]*",
    "icims": r"[a-z0-9-]+\.icims\.com[^\"'\s<]*",
    "ashby": r"jobs\.ashbyhq\.com/[^\"'\s<]*",
    "talentoteca/epreselec": r"(?:talentoteca\.es|epreselec\.com)[^\"'\s<]*",
    "pandape/computrabajo": r"[a-z0-9-]+\.pandape\.(?:computrabajo|infojobs)\.[a-z.]+[^\"'\s<]*",
}

EMPRESAS = {
    "Telefónica": ["https://www.telefonica.com/es/personas/trabaja-con-nosotros/", "https://jobs.telefonica.com/"],
    "Prosegur": ["https://www.prosegur.es/trabaja-con-nosotros", "https://www.prosegur.com/trabaja-con-nosotros"],
    "Indra / Minsait": ["https://www.indracompany.com/es/talento", "https://careers.indracompany.com/"],
    "Amadeus": ["https://amadeus.com/en/careers", "https://jobs.amadeus.com/"],
    "GMV": ["https://www.gmv.com/es-es/empleo"],
    "Banco Santander": ["https://www.santander.com/es/carreras", "https://santander.wd3.myworkdayjobs.com/SantanderCareers"],
    "BBVA": ["https://careers.bbva.com/"],
    "CaixaBank": ["https://www.caixabank.com/es/empleo.html"],
    "Banco Sabadell": ["https://www.grupbancsabadell.com/corp/es/talento.html"],
    "Bankinter": ["https://www.bankinter.com/www/es-es/cgi/ebk+gas+trabaja_con_nosotros"],
    "Mapfre": ["https://www.mapfre.com/trabaja-con-nosotros/"],
    "Iberdrola": ["https://www.iberdrola.com/talento"],
    "Repsol": ["https://www.repsol.com/es/empleo/index.cshtml"],
    "Endesa": ["https://jobs.enel.com/es_ES/careers/JobOpeningsSpain"],
    "Naturgy": ["https://www.naturgy.com/trabaja-con-nosotros/"],
    "Moeve": ["https://www.moeveglobal.com/es/talento"],
    "Inditex": ["https://careers.inditex.com/"],
    "Mercadona": ["https://info.mercadona.es/es/empleo"],
    "El Corte Inglés": ["https://www.elcorteingles.es/trabaja-con-nosotros/"],
    "Ferrovial": ["https://www.ferrovial.com/es/talento/"],
    "Acciona": ["https://www.acciona.com/es/talento/"],
    "Airbus": ["https://www.airbus.com/en/careers"],
    "SEAT / CUPRA": ["https://www.seat.com/careers"],
    "Accenture": ["https://www.accenture.com/es-es/careers"],
    "NTT DATA": ["https://es.nttdata.com/careers"],
    "Capgemini": ["https://www.capgemini.com/es-es/careers/"],
    "Deloitte": ["https://www2.deloitte.com/es/es/careers.html"],
    "PwC": ["https://www.pwc.es/es/empleo.html"],
    "EY": ["https://www.ey.com/es_es/careers"],
    "KPMG": ["https://kpmg.com/es/es/home/carreras.html"],
    "Google": ["https://www.google.com/about/careers/applications/jobs/results?location=Spain&target_level=INTERN_AND_APPRENTICE"],
    "Microsoft": ["https://jobs.careers.microsoft.com/global/en/search?lc=Spain"],
    "Amazon": ["https://www.amazon.jobs/en/search.json?country=ESP&result_limit=1"],
    "Glovo": ["https://about.glovoapp.com/careers/", "https://jobs.glovoapp.com/"],
    "Cabify": ["https://cabify.com/es/trabaja-con-nosotros"],
    "Idealista": ["https://www.idealista.com/info/trabaja-con-nosotros"],
    "Wallapop": ["https://about.wallapop.com/careers"],
    "Fever": ["https://feverup.com/careers"],
    "Factorial": ["https://factorialhr.com/careers"],
    "Jobandtalent": ["https://www.jobandtalent.com/careers"],
    "TravelPerk / Perk": ["https://www.perk.com/careers/"],
}

CABECERAS = {"User-Agent": "Mozilla/5.0 (buscador-practicas; diagnostico)"}
PISTA_ENLACE = re.compile(r"(job|career|carrera|empleo|oferta|vacante|talent|trabaja|position|opening)", re.I)


def huellas(texto):
    vistas = {}
    for nombre, patron in HUELLAS.items():
        m = re.findall(patron, texto, re.I)
        if m:
            vistas[nombre] = sorted(set(m))[:3]
    return vistas


def analizar(url):
    r = requests.get(url, headers=CABECERAS, timeout=20, allow_redirects=True)
    resultado = {"url_final": r.url, "status": r.status_code, "huellas": huellas(r.url + " " + r.text)}
    if not resultado["huellas"]:
        enlaces = set(re.findall(r'href="([^"#]+)"', r.text))
        candidatos = [urljoin(r.url, e) for e in enlaces if PISTA_ENLACE.search(e)][:12]
        for c in candidatos:
            try:
                r2 = requests.get(c, headers=CABECERAS, timeout=15, allow_redirects=True)
                h = huellas(r2.url + " " + r2.text)
                if h:
                    resultado["huellas"] = h
                    resultado["via"] = r2.url
                    break
            except Exception:
                pass
    return resultado


for empresa, urls in EMPRESAS.items():
    for url in urls:
        try:
            res = analizar(url)
        except Exception as e:
            print(f"### {empresa} | {url} | ERROR {type(e).__name__}: {str(e)[:120]}")
            continue
        print(f"### {empresa} | {url} -> {res['status']} {res['url_final'][:100]}")
        for k, v in res["huellas"].items():
            print(f"    {k}: {v}")
        if res.get("via"):
            print(f"    (vía {res['via'][:120]})")
        if res["huellas"]:
            break
sys.stdout.flush()
