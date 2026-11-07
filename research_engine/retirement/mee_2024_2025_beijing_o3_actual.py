#!/usr/bin/env python3
"""Official MEE HTML 2024 and 2025 annual city air source validation.
Exact Beijing 2024/25 yearly PM2.5, O3 and good-air-day fractions are extracted
from actual MEE publications. The NATIONAL 339-city aggregate is never
transferred to any of the 168 cities or 2847 provisional counties.

O3 for the other 167 MEE priority cities remains MISSING, not inferred.
"""
import csv,datetime,hashlib,json,pathlib,re,urllib.request
from bs4 import BeautifulSoup
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
PMCSV=ROOT/"status/mee_2025_168_official_city_PM25_verified_source.csv"
PMJS=ROOT/"status/mee_2025_168_official_city_PM25_context_evidence.json"
BASE=ROOT/"status/national_R4_2025_168_city_PM25_CONTEXT_ONLY_2847.csv"
def sha(b):return hashlib.sha256(b).hexdigest()
prev=json.loads(PMJS.read_text(encoding="utf-8"))
if not(prev["2025_year_annual_priority_city_sample_count"]==168
 and prev["annex_page_http_verified_count"]==6
 and prev["actual_verified_county_air_quality_screenings"]==0
 and sha(PMCSV.read_bytes())==prev["city_csv_sha256"]
 and sha(BASE.read_bytes())==prev["county_context_csv_sha256"]):
 raise RuntimeError("MEE source and previous 2847 R4 city-context input mismatch")
source={
 "2024":"https://www.mee.gov.cn/ywdt/xwfb/202501/t20250124_1101318.shtml",
 "2025":"https://www.mee.gov.cn/ywdt/xwfb/202601/t20260128_1142783.shtml"}
results={}
for year,url in source.items():
 req=urllib.request.Request(url,headers={"User-Agent":"Retirement2025OfficialMEE_O3HistoricalYearQA/1.0","Accept":"text/html,*/*"})
 with urllib.request.urlopen(req,timeout=65) as r:raw=r.read(1500000)
 if len(raw)<8000:raise RuntimeError("Official annual HTML abnormally short")
 html=BeautifulSoup(raw,"html.parser")
 clean="".join(html.get_text(" ",strip=True).split())
 clean=clean.replace("－","—").replace("–","—").replace("—","—")
 # Explicitly bounded Beijing annual paragraph. No 12-month values from other cities.
 k=clean.find("1—12月，北京市")
 if k<0:raise RuntimeError("Official Beijing annual paragraph missing for "+year)
 segment=clean[k:k+420]
 numbers=[float(x) for x in re.findall(r"浓度为([0-9]+(?:[.][0-9]+)?)微克/立方米",segment)]
 good=re.search(r"优良天数比例为([0-9]+(?:[.][0-9]+)?)%",segment)
 if len(numbers)<2 or not good:raise RuntimeError("Could not extract Beijing PM and O3 and good-day for year "+year+" segment "+segment[:270])
 beijing={"city":"北京市","2025_prefecture_code":"110000",
 "year":int(year),"PM25_ug_m3":numbers[0],"O3_ug_m3":numbers[1],
 "good_air_days_pct":float(good.group(1)), "sample_scope":"BEIJING_MUNICIPALITY_ANNUAL_PUBLISHED",
 "2026_county_residential_air_proven":False}
 nr=clean.find("1—12月，全国339个地级及以上城市PM")
 if nr<0:raise RuntimeError("Official 339-city yearly general paragraph not found "+year)
 ntext=clean[nr:nr+600]
 nation_pm=re.search(r"PM2.5平均浓度为([0-9]+(?:[.][0-9]+)?)微克/立方米",ntext)
 nation_o3=re.search(r"O3平均浓度为([0-9]+(?:[.][0-9]+)?)微克/立方米",ntext)
 # Separate national good-day paragraph
 nk=clean.find("1—12月，全国339个地级及以上城市平均空气质量优良天数比例为")
 nation_good=re.search(r"比例为([0-9]+(?:[.][0-9]+)?)%",clean[nk:nk+140]) if nk>=0 else None
 if not nation_pm or not nation_o3 or not nation_good:raise RuntimeError("National aggregate parse not actual for year "+year)
 national={"national_339_city_PM25_mean_ug_m3":float(nation_pm.group(1)),
    "national_339_city_O3_90pct_mean_ug_m3":float(nation_o3.group(1)),
    "national_339_city_good_days_mean_pct":float(nation_good.group(1)),
    "do_not_use_as_city_observation":True}
 results[year]={"source_url":url,"source_HTML_SHA256":sha(raw),"source_HTML_bytes":len(raw),
     "Beijing_specific":beijing,"national_339_city_AGGREGATE_ONLY":national}
 print("OFFICIAL_MEE_YEAR_PARSED",year,beijing,national,flush=True)
assert results["2024"]["Beijing_specific"]["PM25_ug_m3"]==30.5
assert results["2024"]["Beijing_specific"]["O3_ug_m3"]==171
assert results["2024"]["Beijing_specific"]["good_air_days_pct"]==79.2
assert results["2025"]["Beijing_specific"]["PM25_ug_m3"]==27.0
assert results["2025"]["Beijing_specific"]["O3_ug_m3"]==159
assert results["2025"]["Beijing_specific"]["good_air_days_pct"]==85.2
assert results["2025"]["national_339_city_AGGREGATE_ONLY"]["national_339_city_PM25_mean_ug_m3"]==28.0
assert results["2025"]["national_339_city_AGGREGATE_ONLY"]["national_339_city_O3_90pct_mean_ug_m3"]==138
with BASE.open(encoding="utf-8-sig",newline="") as f:
 rdr=csv.DictReader(f);fields=list(rdr.fieldnames);rows=list(rdr)
if len(rows)!=2847:raise RuntimeError("Missing 2847 original county candidates")
extra=["R4_Beijing_city_2025_O3_context_only","R4_Beijing_city_2024_O3_context_only",
 "R4_Beijing_city_2025_good_days_pct_context_only","R4_city_2024_2025_O3_city_not_residential"]
for k in extra:
 if k in fields:raise RuntimeError("Already has official ozone context field "+k)
fields+=extra
beijingcontext=0
for r in rows:
 if r["R4_official_2025_parent_city_code"]=="110000":
  beijingcontext+=1
  r["R4_Beijing_city_2025_O3_context_only"]=159.0
  r["R4_Beijing_city_2024_O3_context_only"]=171.0
  r["R4_Beijing_city_2025_good_days_pct_context_only"]=85.2
  r["R4_city_2024_2025_O3_city_not_residential"]="TRUE"
 if r["confirmed_exit_round"] or r["formal_grade"] or str(r["valid_county_screening"]).lower()=="true":
  raise RuntimeError("Unauthorized county exclusion or formal grade")
newCSV=OUT/"national_R4_city_PM25_2025_Beijing_O3_2024_2025_2847_CONTEXT_ONLY.csv"
with newCSV.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader();wr.writerows(rows)
report={"schema":"RET_MEE_OFFICIAL_2024_2025_BEIJING_AND_NATIONAL_O3_PM25_SOURCE_V1",
 "asof_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_html_results":results,
 "annual_2025_city_PM25_source_rows_retained":168,
 "annual_city_O3_2025_direct_source_cities":1,
 "annual_city_O3_2024_2025_comparable_city_count":1,
 "remaining_168_key_cities_without_individual_city_O3_sources":167,
 "provisional_counties_with_annual_2025_city_PM25_PARENT_CONTEXT_ONLY":prev["provisional_counties_with_parent_2025_city_pm25_CONTEXT_ONLY"],
 "provisional_Beijing_district_codes_given_MUNICIPAL_CONTEXT_ONLY":beijingcontext,
 "Beijing_2025_vs_2024_PM25_change_ug_m3":-3.5,
 "Beijing_2025_vs_2024_O3_change_ug_m3":-12.0,
 "Beijing_2025_vs_2024_good_days_pct_points":6.0,
 "full_county_candidates_carried_forward":2847,
 "individual_county_residential_PM25_O3_verified":0,
 "formal_valid_county_screenings":0,"confirmed_exclusions":0,
 "prior_national_R4_context_sha256":sha(BASE.read_bytes()),
 "new_national_R4_context_csv_sha256":sha(newCSV.read_bytes()),
 "warnings":["Only Beijing has individually named annual ozone and good-day indicators in the two official HTML text articles","O3 city is 90th percentile of daily max 8-hr averages; not average ozone concentration","Never distribute national or regional O3 average to individual cities","Municipal PM25 and O3 cannot prove individual county or home exposures","Continue R4 ozone and industrial-pollution gaps for remaining 167 cities and residential-level pollutants"]}
(OUT/"mee_official_2024_2025_Beijing_O3_air_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"official_city_O3_data":1,"beijing_district_codes_context_only":beijingcontext,"city_O3_remaining_unknown":167,"formal_valid_county_screenings":0},ensure_ascii=False),flush=True)
