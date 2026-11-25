"""Enseña un trozo del RSS crudo de un portal (para depurar)."""
import re, sys, requests
url = sys.argv[1].rstrip("/") + "/services/rss/job/?locale=es_ES&keywords=(intern)"
r = requests.get(url, headers={"User-Agent": "buscador-practicas/0.1 (proyecto personal de estudiante)"}, timeout=30)
t = r.content.decode("utf-8", errors="replace")
print("STATUS", r.status_code, r.headers.get("content-type"), len(t))
print("ITEMS", len(re.findall(r"<item", t)), "CIERRES", len(re.findall(r"</item>", t)))
print(t[:600].replace("\n", " | "))
i = t.find("<item"); print("PRIMER ITEM:", t[i:i+700].replace("\n", " | "))
