"""Prueba educada de la API de Workday: UA honesto, una petición por empresa, sin reintentos."""
import json, time, requests
UA = "buscador-practicas/0.1 (proyecto personal de estudiante)"
for host, tenant, site in [("bbva.wd3", "bbva", "BBVA"), ("santander.wd3", "santander", "SantanderCareers"), ("amadeus.wd502", "amadeus", "jobs")]:
    origen = f"https://{host}.myworkdayjobs.com"
    r = requests.post(f"{origen}/wday/cxs/{tenant}/{site}/jobs",
                      json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "intern"},
                      headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"}, timeout=30)
    print("###", host, r.status_code, r.headers.get("content-type"), r.headers.get("retry-after"), repr(r.text[:120]))
    if r.ok:
        d = r.json(); print("   total", d.get("total"))
        for j in d.get("jobPostings", [])[:3]: print("     ", json.dumps(j, ensure_ascii=False)[:250])
    time.sleep(5)
