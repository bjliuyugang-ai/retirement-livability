#!/usr/bin/env python3
"""2024/2025 same-definition annual PM2.5/O3/good days source verification:
Beijing MEE + Shanghai Municipal Statistics. Urban level ONLY.
"""
import datetime,hashlib,html,json,pathlib,re,urllib.request
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
cases=[
 {"city":"北京","year":2024,"pm25":30.5,"o3_p90":171,"good_pct":79.2,
  "url":"https://www.mee.gov.cn/ywdt/xwfb/202501/t20250124_1101318.shtml","publisher":"生态环境部"},
 {"city":"北京","year":2025,"pm25":27.0,"o3_p90":159,"good_pct":85.2,
  "url":"https://www.mee.gov.cn/ywdt/xwfb/202601/t20260128_1142783.shtml","publisher":"生态环境部"},
 {"city":"上海","year":2024,"pm25":28.0,"o3_p90":144,"good_pct":88.5,
  "url":"https://tjj.sh.gov.cn/tjgb/20250324/a7fe18c6d5c24d66bfca89c5bb4cdcfb.html","publisher":"上海市统计局"},
 {"city":"上海","year":2025,"pm25":26.3,"o3_p90":159,"good_pct":88.5,
  "url":"https://tjj.sh.gov.cn/tjgb/20260330/e0772941e8e041eaaad2df850b44ef98.html","publisher":"上海市统计局"}]
def numbers_present(s,vals):
 return all(str(v) in s for v in vals)
for c in cases:
 try:
  req=urllib.request.Request(c["url"],headers={"User-Agent":"Mozilla/5.0 (RetirementShanghaiAndBeijingOzoneQA/1.0)","Accept":"text/html,*/*"})
  with urllib.request.urlopen(req,timeout=33) as r:b=r.read(1_500_000)
  txt=html.unescape(re.sub(r"<[^>]+>"," ",b.decode("utf-8","replace")))
  c["bytes"]=len(b);c["raw_sha256"]=hashlib.sha256(b).hexdigest()
  c["source_actually_read"]=True
  c["numeric_value_present"]={"pm25":str(c["pm25"]) in txt,
    "o3":str(c["o3_p90"]) in txt,"good_days_pct":str(c["good_pct"]) in txt}
  c["status"]="SOURCE_HAS_ALL_THREE_NUMERICS" if all(c["numeric_value_present"].values()) else "SOURCE_REQUIRES_INDEPENDENT_VALUE_INSPECTION"
 except Exception as e:
  c["status"]="LIVE_SOURCE_BLOCKED";c["source_actually_read"]=False;c["error"]=repr(e)
 print("AIR_YEAR_PAIR",c["city"],c["year"],c["status"],flush=True)
out=[]
for city in ("北京","上海"):
 a,b=sorted([x for x in cases if x["city"]==city],key=lambda x:x["year"])
 out.append({"city":city,"source_2024_status":a["status"],"source_2025_status":b["status"],
             "PM25_2024_ugm3":a["pm25"],"PM25_2025_ugm3":b["pm25"],
             "PM25_change_2025_minus_2024":round(b["pm25"]-a["pm25"],2),
             "O3_p90_2024_ugm3":a["o3_p90"],"O3_p90_2025_ugm3":b["o3_p90"],
             "O3_change_2025_minus_2024":b["o3_p90"]-a["o3_p90"],
             "good_air_days_2024_pct":a["good_pct"],"good_air_days_2025_pct":b["good_pct"],
             "county_residential_exposure_verified":False,
             "all_two_year_values_verified_live":all(x["status"]=="SOURCE_HAS_ALL_THREE_NUMERICS" for x in (a,b))})
result={"schema":"RET_R4_BEIJING_SHANGHAI_YEARPAIR_2024_2025_MULTI_POLLUTANT_V1",
 "generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "reference_cases":cases,"two_city_trends":out,
 "cities_with_two_year_online_value_crosscheck":sum(x["all_two_year_values_verified_live"] for x in out),
 "provisional_counties_in_2025_Beijing_plus_Shanghai":32,
 "source_geography":"MUNICIPALITY_WIDE_ANNUAL_AIR_METRICS_ONLY",
 "no_county_air_monitoring_claim":True,
 "no_fatal_county_exclusions":True,
 "formal_valid_county_screenings":0,
 "quality_note":"Shanghai 2025 O3 p90 rises while PM2.5 falls; avoid declaring comprehensive environmental health safety from PM2.5 alone. Beijing both move down. These comparisons are independent of county residential industrial/transport exposure."}
(OUT/"national_R4_Beijing_Shanghai_2024_2025_air_yearpair.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("R4_SOURCE_YEARPAIR_RESULT",json.dumps({"verified":result["cities_with_two_year_online_value_crosscheck"],
 "trends":out},ensure_ascii=False)[:1800],flush=True)
