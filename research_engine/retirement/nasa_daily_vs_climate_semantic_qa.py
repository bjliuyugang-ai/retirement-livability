#!/usr/bin/env python3
"""NASA POWER same-coordinate same-period daily vs custom climatology parameter QA.
Linan 30.19634 N 119.35251 E. Compare 2019-2020 daily mean T2M_MAX/T2M_MIN
against requested 2019-2020 climatology T2M_MAX_AVG/T2M_MIN_AVG.
Do NOT assume either endpoint is correct until source time and semantics match.
"""
import datetime,hashlib,json,pathlib,statistics,urllib.parse,urllib.request
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
LAT=30.19634;LON=119.35251
def get(endpoint,params,name):
 url="https://power.larc.nasa.gov/api/temporal/"+endpoint+"/point?"+urllib.parse.urlencode(params,safe=",")
 req=urllib.request.Request(url,headers={"User-Agent":"RetirementNASAParameterSemanticQA/1.0","Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=95) as r:b=r.read()
 (OUT/("NASA_PARAM_QA_"+name+".json")).write_bytes(b)
 return url,json.loads(b),hashlib.sha256(b).hexdigest()
base={"latitude":LAT,"longitude":LON,"community":"SB","format":"JSON"}
u1,daily,sha1=get("daily",{**base,"parameters":"T2M_MAX,T2M_MIN,T2M","start":"20190101","end":"20201231"},"DAILY_2019_2020")
u2,clim,sha2=get("climatology",{**base,"parameters":"T2M_MAX_AVG,T2M_MIN_AVG,T2M","start":2019,"end":2020},"CLIM_2019_2020")
dd=(daily.get("properties") or {}).get("parameter") or {}
cc=(clim.get("properties") or {}).get("parameter") or {}
if not {"T2M_MAX","T2M_MIN"}.issubset(dd) or not {"T2M_MAX_AVG","T2M_MIN_AVG"}.issubset(cc):
 raise ValueError("Missing expected daily vs climatology temperature parameter")
counts={}
comparisons=[]
for mon,number in [("JAN",1),("FEB",2),("JUL",7),("DEC",12)]:
 def dailymean(key):
  series=dd[key]
  values=[float(v) for date,v in series.items() if len(date)==8 and int(date[4:6])==number and 2019<=int(date[:4])<=2020 and v is not None and float(v)>-999]
  if len(values)<50 and mon!="FEB":raise ValueError("Insufficient daily samples "+key+" "+mon+":"+str(len(values)))
  return round(statistics.mean(values),3),len(values)
 avgh,nh=dailymean("T2M_MAX");avgl,nl=dailymean("T2M_MIN")
 ch=float(cc["T2M_MAX_AVG"][mon]);cl=float(cc["T2M_MIN_AVG"][mon])
 comparisons.append({"month":mon,"daily_max_mean_c":avgh,"climatology_MAX_AVG_c":ch,
    "difference_clim_minus_daily_max_c":round(ch-avgh,3),
    "daily_min_mean_c":avgl,"climatology_MIN_AVG_c":cl,
    "difference_clim_minus_daily_min_c":round(cl-avgl,3),
    "daily_samples":nh})
large=sum(abs(x["difference_clim_minus_daily_max_c"])>=2 or abs(x["difference_clim_minus_daily_min_c"])>=2 for x in comparisons)
out={"schema":"NASA_SAME_POINT_SAME_YEAR_DAILY_CLIMATOLOGY_SEMANTIC_TEST_V1",
 "generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "site":"Linan historic point, NOT residence","point":[LAT,LON],
 "period":"2019-2020",
 "daily_source_url":u1,"daily_sha256":sha1,
 "climatology_source_url":u2,"climatology_sha256":sha2,
 "daily_header":daily.get("header"),"clim_header":clim.get("header"),
 "comparisons":comparisons,"months_with_differences_ge2c":large,
 "semantic_qa_status":"INCONSISTENT_EXPECTED_DAILY_EXTREME_AVERAGES" if large else "CONSISTENT_WITH_DAILY_EXTREME_MEANS",
 "formal_valid_county_screenings":0,
 "limitations":["If NASA climatology uses different aggregation methods, cannot use as average daily Tmax thresholds without resolving",
 "Only one historical point, no station QA, no county grading"]}
(OUT/"nasa_daily_vs_climatology_semantic_QA.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":out["semantic_qa_status"],"differences_ge2":large,"compared":comparisons},ensure_ascii=False),flush=True)
