#!/usr/bin/env python3
"""R4 honest 2025 OFFICIAL MUNICIPAL annual PM2.5/O3/good-days to county
candidate *CONTEXT*, not a county residential pollution observation.
Follow 2025 mainland + 2026 two provisional roster: 2847 preserved. Distinct
province aggregate contextual records never become county-level measurements.
"""
import collections,csv,datetime,hashlib,html,json,pathlib,re,urllib.request
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/"status/national_R3_205_station_dem_altitude_partial_2847.csv"
PRIOR=ROOT/"status/national_R3_205_station_dem_altitude_source_evidence.json"
OLDER=ROOT/"status/national_r4_city_context_evidence.json"
def sha(b):return hashlib.sha256(b).hexdigest()
p=json.loads(PRIOR.read_text(encoding="utf-8"));old=json.loads(OLDER.read_text(encoding="utf-8"))
if not (p["total_R3_partial_point_evidence_counties"]==205 and
 p["R1_any_partial_retained"]==214 and p["R2_any_partial_retained"]==199
 and p["all_carry_forward"]==2847 and old["R4_city_context_counties"]==2):
 raise RuntimeError("R4 preceding source provenance violated")
if sha(SOURCE.read_bytes())!=p["output_national_csv_sha256"]:raise RuntimeError("R3 canonical SHA changed")
with SOURCE.open(encoding="utf-8-sig",newline="") as f:
 rd=csv.DictReader(f);cols=list(rd.fieldnames);rows=list(rd)
if len(rows)!=2847 or len({r["candidate_code"] for r in rows})!=2847:raise RuntimeError("2025/2026 2847 roster changed")
for n in ["R4_2025_municipal_context_PM25_ugm3","R4_2025_municipal_context_O3_ugm3",
"R4_2025_municipal_context_good_air_day_percent","R4_2025_municipal_context_good_air_days",
"R4_2025_municipal_2025_source_url","R4_2025_province_context_PM25_ugm3",
"R4_2025_province_context_O3_ugm3","R4_2025_province_good_days_pct",
"R4_2025_province_source_url","R4_air_2025_geographic_evidence_scope",
"R4_2025_annual_2026_official_county_boundaries_certified",
"R4_air_current_residential_PM25_and_O3_verified"]:
 if n in cols:raise RuntimeError("Cannot overwrite existing R4 source field "+n)
 cols.append(n)
# Government city/municipality sources with precisely named annual sources.
municipal={
 "11":{"label":"北京市","pm25":27.0,"o3":159.0,"good_days_percent":85.2,
 "url":"https://www.mee.gov.cn/ywdt/xwfb/202601/t20260128_1142783.shtml","url_keyword":"27.0","source_level":"MEE_OFFICIAL_BEIJING_2025_AIR"},
 "12":{"label":"天津市","pm25":36.2,"o3":None,"good_days_percent":77.0,
 "url":"https://www.tj.gov.cn/sy/xwfbh/xwfbh_210907/202606/t20260604_7311610.html","url_keyword":"36.2","source_level":"TIANJIN_2025_ECOENV_OFFICIAL_PRESS"},
 "31":{"label":"上海市","pm25":26.3,"o3":159.0,"good_days_percent":88.5,
 "url":"https://tjj.sh.gov.cn/tjgb/20260330/e0772941e8e041eaaad2df850b44ef98.html","url_keyword":"26.3","source_level":"SHANGHAI_STATS_2025_OFFICIAL"},
 "50":{"label":"重庆市","pm25":31.0,"o3":None,"good_days_percent":None,"good_days_count":339,
 "url":"https://www.sthjj.cq.gov.cn/zwgk_249/xwfb_67131/202606/t20260615_15753047.html","url_keyword":"31","source_level":"CHONGQING_ECOENV_OFFICIAL_2025_PRESS"}}
# Cross-province figures are province aggregates, NOT a city, county nor dwelling.
provinces={
 "53":{"label":"云南省","pm25":20.4,"o3":118,"good_days_percent":98.9,
 "url":"https://www.ynrd.gov.cn/html/2026/szyw2025_0401/4045337.html?show=2025new","url_keyword":"20.4","source_level":"YUNNAN_2025_STATISTICS_OFFICIAL_16_SEATS_AGGREGATE"},
 "32":{"label":"江苏省","pm25":31.3,"o3":None,"good_days_percent":83.8,
 "url":"https://www.js.gov.cn/art/2026/6/30/art_46548_342.html","url_keyword":"31.3","source_level":"JIANGSU_2025_ECOENV_OFFICIAL_PROVINCE"},
 "51":{"label":"四川省","pm25":28.5,"o3":None,"good_days_percent":88.7,
 "url":"https://www.scjjrb.com/2026/02/05/99456445.html","url_keyword":"28.5","source_level":"SICHUAN_ECOENV_OFFICIAL_PRESS_MEDIA_TRANSCRIPT"},
 "46":{"label":"海南省","pm25":11.8,"o3":None,"good_days_percent":98.8,
 "url":"https://www.hnntv.cn/info/article/539/539349.html","url_keyword":"11.8","source_level":"HAINAN_ECOENV_OFFICIAL_PRESS_CCTV_REPORTED_SAND_ADJUSTED"}}
# Guard actual access; a source unavailable cannot become a record by assertion.
def fetch_verify(x):
 try:
  req=urllib.request.Request(x["url"],headers={"User-Agent":"Mozilla/5.0 (RetirementEvidenceR4/1.0)","Accept":"text/html,*/*"})
  with urllib.request.urlopen(req,timeout=35) as response:
   body=response.read(2_000_001)
  txt=html.unescape(re.sub("<[^>]+>"," ",body.decode("utf-8","replace")))
  # A government source must mention seeded annual data (exact decimals).
  if x["url_keyword"] not in txt:raise ValueError("Source page fetched but seeded 2025 metric not present")
  return {"status":"SOURCE_RETRIEVED_WITH_YEAR_METRIC","sha256":sha(body),"bytes":len(body)}
 except Exception as ex:
  return {"status":"SOURCE_FETCH_OR_VALUE_QA_FAILED","error":repr(ex)}
checks={c:fetch_verify(x) for c,x in {**{"municipal_"+k:v for k,v in municipal.items()},**{"province_"+k:v for k,v in provinces.items()}}.items()}
print("R4_SOURCE_RESULTS",json.dumps({k:v["status"] for k,v in checks.items()},ensure_ascii=False),flush=True)
municipal_source={k:v for k,v in municipal.items() if checks["municipal_"+k]["status"]=="SOURCE_RETRIEVED_WITH_YEAR_METRIC"}
province_source={k:v for k,v in provinces.items() if checks["province_"+k]["status"]=="SOURCE_RETRIEVED_WITH_YEAR_METRIC"}
# Four direct-governed cities are citywide area data (not county level); map to district city environment context.
counters=collections.Counter();per_city=collections.Counter();per_prov=collections.Counter();existing=0
for row in rows:
 code=row["candidate_code"];pref=code[:2]
 if row["R4_status"]!="NOT_SCREENED":existing+=1
 if pref in municipal_source:
  z=municipal_source[pref]
  row["R4_2025_municipal_context_PM25_ugm3"]=z["pm25"]
  row["R4_2025_municipal_context_O3_ugm3"]=z["o3"] if z.get("o3") is not None else ""
  row["R4_2025_municipal_context_good_air_day_percent"]=z["good_days_percent"] if z.get("good_days_percent") is not None else ""
  row["R4_2025_municipal_context_good_air_days"]=z.get("good_days_count") if z.get("good_days_count") is not None else ""
  row["R4_2025_municipal_2025_source_url"]=z["url"]
  row["R4_air_2025_geographic_evidence_scope"]="2025_WHOLE_MUNICIPALITY_CITYWIDE_CONTEXT_NOT_DISTRICT_OR_RESIDENCE"
  if row["R4_status"]=="NOT_SCREENED":
   row["R4_status"]="WHOLE_MUNICIPALITY_AIR_2025_CONTEXT_ONLY"
   row["R4_evidence_scope"]="CITYWIDE_2025_PM25_OR_O3_NOT_LOCAL_EXPOSURE"
   row["R4_missing_parameters"]="DISTRICT_INDUSTRIAL_SOURCE;PM25_AND_O3_SITE_MONITORING;AIR_QUALITY_EXPOSURE_NEAR_RESIDENCE"
   row["cascade_status"]="ACTIVE_PENDING";row["last_completed_round"]="R4_CITYWIDE_MUNICIPAL_CONTEXT"
   counters["new_municipal_city_context_counties"]+=1
  per_city[pref]+=1
 elif pref in province_source:
  z=province_source[pref]
  row["R4_2025_province_context_PM25_ugm3"]=z["pm25"]
  row["R4_2025_province_context_O3_ugm3"]=z["o3"] if z.get("o3") is not None else ""
  row["R4_2025_province_good_days_pct"]=z["good_days_percent"]
  row["R4_2025_province_source_url"]=z["url"]
  row["R4_air_2025_geographic_evidence_scope"]="PROVINCE_AVERAGE_CONTEXT_ONLY_COUNTY_R4_REMAINS_UNSCANNED"
  counters["province_context_county_rows_not_measured"]+=1
  per_prov[pref]+=1
 else:
  row["R4_air_2025_geographic_evidence_scope"]="NO_NEW_RELIABLE_2025_SOURCE"
 row["R4_2025_annual_2026_official_county_boundaries_certified"]="FALSE"
 row["R4_air_current_residential_PM25_and_O3_verified"]="FALSE"
if existing!=2:raise RuntimeError("Prior real R4 counted 2 city context counties unexpectedly "+str(existing))
after=sum(r["R4_status"]!="NOT_SCREENED" for r in rows)
if after!=2+counters["new_municipal_city_context_counties"]:raise RuntimeError("R4 city-source status conservation")
if any(r["confirmed_exit_round"] for r in rows) or any(str(r["valid_county_screening"]).lower()=="true" for r in rows):
 raise RuntimeError("Unauthorized formal screen or fatal county elimination")
out=OUT/"national_R4_2025_verified_city_province_air_context_2847.csv"
with out.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=cols);wr.writeheader();wr.writerows(rows)
report={"schema":"RET_NATIONAL_R4_2025_OFFICIAL_CITY_PROVINCE_SOURCE_SCOPE_CONTEXT_V1",
"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"historic_2025_2026_provisional_counties":2847,
"source_R3_2847_sha256":sha(SOURCE.read_bytes()),
"2025_official_municipal_sources_verified":len(municipal_source),
"2025_provincial_source_aggregates_verified":len(province_source),
"actual_online_HTTP_and_metric_checks":checks,
"new_R4_counties_with_MUNICIPAL_CONTEXT_NOT_COUNTY_MONITORING":counters["new_municipal_city_context_counties"],
"previous_R4_city_context_counties":2,
"R4_city_or_municipal_context_counties":after,
"R4_not_scanned_counties":2847-after,
"province_only_context_mapped_candidate_rows_not_counted_R4_measured":counters["province_context_county_rows_not_measured"],
"municipality_code_prefix_count":dict(per_city),"province_aggregate_candidate_prefix_count":dict(per_prov),
"source_items":[{"scope":"2025 municipality","prefix":k,**v,"fetch_check":checks["municipal_"+k]} for k,v in municipal.items()]+[
 {"scope":"2025 province aggregate not county measured","prefix":k,**v,"fetch_check":checks["province_"+k]} for k,v in provinces.items()],
"source_level_warning":"Municipal/source annual PM2.5 and O3 are not district observations and do not establish home exposure; province aggregates are not counted R4 county measured.",
"R1_partial_evidence_retained":214,"R2_partial_evidence_retained":199,"R3_partial_elevation_point_retained":205,
"all_2847_continue":2847,"confirmed_county_exclusions":0,
"formal_valid_county_screenings":0,"official_2026_administrative_geometry_verified":False,
"output_national_CSV_sha256":sha(out.read_bytes())}
(OUT/"national_R4_2025_official_air_city_province_scope_evidence.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("R4_REAL_EVIDENCE",json.dumps({"municipal_sources":len(municipal_source),
 "province_sources":len(province_source),"new_municipal_county_context":report["new_R4_counties_with_MUNICIPAL_CONTEXT_NOT_COUNTY_MONITORING"],
 "R4_partial_city_context_total":after,"R4_unknown":2847-after,
 "prov_aggregate_context_only":report["province_only_context_mapped_candidate_rows_not_counted_R4_measured"]},ensure_ascii=False),flush=True)
