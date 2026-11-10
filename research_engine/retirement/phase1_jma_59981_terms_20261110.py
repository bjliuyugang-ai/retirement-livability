#!/usr/bin/env python3
import requests,re,json,datetime,statistics,pathlib,time
from bs4 import BeautifulSoup
base="https://ds.data.jma.go.jp/gmd/tcc/tcc/products/climate/climatview/graph_mkhtml.php"
rs={}
for rmode in (0,1,2,3,4,5,6,9):
 try:
  p={"e":0,"k":0,"m":6,"n":59981,"r":rmode,"s":3,"y":2020}
  q=requests.get(base,params=p,timeout=25)
  q.raise_for_status()
  soup=BeautifulSoup(q.text,"html.parser")
  dates={}
  for tr in soup.find_all("tr"):
   td=[x.get_text(" ",strip=True) for x in tr.find_all(["td","th"],recursive=False)]
   if len(td)<3:continue
   m=re.search(r"\b((?:19|20)\d\d)-(0[1-9]|1[0-2])\b",td[0])
   if not m:continue
   try:
    temp=float(td[2])
    if -10<temp<50:dates[f"{m.group(1)}-{m.group(2)}"]=temp
   except:pass
  keys=sorted(dates)
  rs[str(rmode)]={"status":q.status_code,"all_months":len(keys),"from":keys[0] if keys else None,"to":keys[-1] if keys else None,"period_1991_2020":sum("1991"<=k[:4]<="2020" for k in keys),"total_html_len":len(q.content)}
  if rmode==4:rs[str(rmode)]["monthly_sample"]={k:v for k,v in dates.items() if k.startswith("2020")}
  print(rmode,rs[str(rmode)],flush=True)
 except Exception as e:rs[str(rmode)]={"error":str(e)}
 time.sleep(.5)
path=pathlib.Path("research_engine/retirement/status");path.mkdir(parents=True,exist_ok=True)
(path/"phase1_jma_59981_term_mode_probe_20261110.json").write_text(json.dumps({"time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"url":base,"modes":rs},ensure_ascii=False,indent=2),encoding="utf-8")
