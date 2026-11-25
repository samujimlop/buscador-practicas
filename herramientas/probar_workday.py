import json, requests
H={"Accept":"application/json","Content-Type":"application/json","User-Agent":"buscador-practicas/0.1"}
for host,tenant,site in [("santander.wd3","santander","SantanderCareers"),("bbva.wd3","bbva","BBVA"),("amadeus.wd502","amadeus","jobs")]:
    base=f"https://{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
    r=requests.post(base+"/jobs",json={"appliedFacets":{},"limit":20,"offset":0,"searchText":"intern"},headers=H,timeout=30)
    print("###",host,r.status_code)
    d=r.json(); print("total",d.get("total")); 
    for j in d.get("jobPostings",[])[:4]: print("  ",json.dumps(j,ensure_ascii=False)[:300])
    if d.get("jobPostings"):
        p=d["jobPostings"][0]["externalPath"]
        r2=requests.get(base+p,headers=H,timeout=30); i=r2.json().get("jobPostingInfo",{})
        print("  DETAIL keys",list(i.keys())); print("  ",{k:i.get(k) for k in ["title","location","additionalLocations","country","startDate","postedOn","externalUrl","timeType"]})
