#!/usr/bin/env python3
"""One exact runtime reproduction of national scanner's detail path vs known-good public session."""
import csv,importlib.util,json,pathlib,re,http.cookiejar,urllib.request
from datetime import datetime,timezone

P=pathlib.Path("research_engine/retirement/national_funnel/R4_ENVIRONMENT_236/NATIONAL_PERMIT_236")
f=P/"run_national_permit_236.py"
spec=importlib.util.spec_from_file_location("national",f)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with (P/"output/runs/42467472886/NATIONAL_236_PERMIT_FACILITY_DETAIL_SAMPLE.csv").open(encoding="utf-8-sig",newline="") as stream:
 rows=list(csv.DictReader(stream))
sample=rows[:4]+[x for x in rows if x["permit_no"].startswith("91330226")][:1]
out={"schema":"PERMIT_DETAIL_RUNTIME_COMPARE_V1","utc":datetime.now(timezone.utc).isoformat(),"samples":[]}
for x in sample:
 req=m.make_client()
 try:
  initial=req(m.PAGE)
  body=req(x["detail_url"])
  coords=re.findall(r'<input[^>]*id="(?:longitude|latitude)"[^>]*>',body,re.I)
  fields={"src_length":len(body),"src_title":re.findall(r"<title[^>]*>(.*?)</title>",body,re.I|re.S)[:1],
   "initial_has_token":"tempReportKey" in initial,"latitude_token":"latitude" in body,
   "longitude_token":"longitude" in body,"has_company":x["company"] in body,
   "coords_input_tags":coords[:3],"xkgk_marker":"许可信息公开内容" in body,
   "source_prefix":body[:2000]}
 except Exception as e:fields={"error":repr(e)}
 direct=m.detail_one(x)
 out["samples"].append({"company":x["company"],"permit_no":x["permit_no"],"exact":fields,
  "detail_one":{"status":direct.get("detail_status"),"lon":direct.get("facility_lon"),"lat":direct.get("facility_lat"),"error":direct.get("error")}})
path=P/"output/AUDIT_EXACT_RUNTIME_DETAIL.json"
path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("DETAIL_RUNTIME",json.dumps([{"name":x["company"],"exact":{k:v for k,v in x["exact"].items() if k!="source_prefix"},"one":x["detail_one"]} for x in out["samples"]],ensure_ascii=False),flush=True)
