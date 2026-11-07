#!/usr/bin/env python3
"""NASA POWER 1991-2020 explicit CUSTOM point climatology for 30 historic
county-polygon anchors, both T2M_MAX_AVG and T2M_MIN_AVG per request.

Regional climatology silently uses 2001-2025: DO NOT use for baseline.
Source crosswalk: 2017 historic geoboundaries + secondary 2025 names; never
official 2026 proof. NASA MERRA2 native grid not local residence; all formal
county grades 0, no automatic exclusions on preference threshold.
"""
import csv,datetime,hashlib,json,math,pathlib,time,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
RAW=OUT/"nasa_point_1991_2020_original";RAW.mkdir(parents=True,exist_ok=True)
CROSS=ROOT/"status/r1_expand_strict_crosswalk.json"
PRIOR=ROOT/"status/national_r5_tap_water_batch.csv"
PRIOR_SUM=ROOT/"status/national_r5_tap_water_evidence.json"
REGION=ROOT/"status/nasa_regional_schema_inspection.json"
def hashbytes(b):return hashlib.sha256(b).hexdigest()
a=json.loads(CROSS.read_text(encoding="utf-8"));old=json.loads(PRIOR_SUM.read_text(encoding="utf-8"))
reg=json.loads(REGION.read_text(encoding="utf-8"))
# Regional NASA HEADER actual 20010101..20251231, despite start/end 1991..2020.
if not (reg["regional_header"].get("start")=="20010101" and reg["regional_header"].get("end")=="20251231"):
 raise RuntimeError("Do not assume fixed NASA regional vintage; source semantics changed, re-review!")
if a["sampled_count"]!=30 or old["R5_carry_forward"]!=2847:raise RuntimeError("Unverified national R5/crosswalk input")
if hashbytes(PRIOR.read_bytes())!=old["CSV_sha256"]:raise RuntimeError("Prior 2847 national ledger checksum mismatch")
with PRIOR.open(encoding="utf-8-sig",newline="") as f:
 dr=csv.DictReader(f);fields=list(dr.fieldnames);rows=list(dr)
bycode={r["candidate_code"]:r for r in rows}
if len(rows)!=2847 or len(bycode)!=2847:raise RuntimeError("National denominator mismatch")
targets=a["selected_30"]
COLS=["R1_NASA_custom_1991_2020_winter_tmax_c",
 "R1_NASA_custom_1991_2020_summer_tmax_c",
 "R1_NASA_custom_1991_2020_winter_tmin_c",
 "R1_NASA_custom_1991_2020_summer_tmin_c",
 "R1_NASA_point_raw_sha256",
 "R1_NASA_vs_ERA5_winter_tmax_diff_c",
 "R1_NASA_vs_ERA5_summer_tmax_diff_c",
 "R1_NASA_vs_ERA5_conflict_ge3c",
 "R1_NASA_native_grid_elevation_m",
 "R1_NASA_model_status"]
for col in COLS:
 if col in fields:raise RuntimeError("Duplicate model field "+col)
fields+=COLS
def get(p):
 args={"latitude":p["latitude_2017_polygon_interior"],
 "longitude":p["longitude_2017_polygon_interior"],
 "community":"SB","parameters":"T2M_MAX_AVG,T2M_MIN_AVG",
 "format":"JSON","start":1991,"end":2020}
 url="https://power.larc.nasa.gov/api/temporal/climatology/point?"+urllib.parse.urlencode(args,safe=",")
 req=urllib.request.Request(url,headers={"User-Agent":"RetirementNASA1991HistoricalClimatology/1.0","Accept":"application/json"})
 for retry in range(2):
  try:
   with urllib.request.urlopen(req,timeout=75) as r:b=r.read()
   return url,b
  except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as ex:
   if isinstance(ex,urllib.error.HTTPError) and ex.code not in [429,500,502,503,504]:raise
   if retry:raise
   time.sleep(8)
def avg(vals,months):
 w={"JAN":31,"FEB":28.25,"MAR":31,"APR":30,"MAY":31,"JUN":30,"JUL":31,
 "AUG":31,"SEP":30,"OCT":31,"NOV":30,"DEC":31}
 return round(sum(float(vals[x])*w[x] for x in months)/sum(w[x] for x in months),3)
success=[];failure=[]
for i,p in enumerate(targets,1):
 try:
  url,raw=get(p)
  data=json.loads(raw)
  header=data.get("header",{})
  stated_range=str(header.get("range",""))
  if "1991" not in stated_range or "2020" not in stated_range:
   raise ValueError("BAD_NASA_POINT_PERIOD_REJECTED:"+stated_range)
  for key,value in [("start",header.get("start")),("end",header.get("end"))]:
   if value is not None and not(str(value).startswith("1991") if key=="start" else str(value).startswith("2020")):
    raise ValueError("BAD_NASA_POINT_HEADER_"+key+":"+str(value))
  params=(data.get("properties") or {}).get("parameter") or {}
  for key in ["T2M_MAX_AVG","T2M_MIN_AVG"]:
   months=params.get(key)
   if not isinstance(months,dict):raise ValueError("NASA combined-parameter response missing "+key)
   needed=["DEC","JAN","FEB","JUN","JUL","AUG","SEP"]
   if not all(k in months and months[k] is not None and -80<float(months[k])<70 for k in needed):
    raise ValueError("NASA monthly period incomplete: "+key)
  tmax=params["T2M_MAX_AVG"];tmin=params["T2M_MIN_AVG"]
  tmax_winter=avg(tmax,["DEC","JAN","FEB"])
  tmax_summer=avg(tmax,["JUN","JUL","AUG","SEP"])
  tmin_winter=avg(tmin,["DEC","JAN","FEB"])
  tmin_summer=avg(tmin,["JUN","JUL","AUG","SEP"])
  geo=data.get("geometry") or {}
  loc=geo.get("coordinates") or []
  if len(loc)<2:raise ValueError("NASA point geometry absent")
  requested=[p["latitude_2017_polygon_interior"],p["longitude_2017_polygon_interior"]]
  if abs(float(loc[1])-requested[0])>1 or abs(float(loc[0])-requested[1])>1:
   raise ValueError("NASA returned grid too distant from requested historical anchor")
  code=p["county_code"];r=bycode[code]
  if r["candidate_name"]!=p["county_2025_name"]:raise RuntimeError("County names do not match")
  was_scanned=r["R1_status"]!="NOT_SCREENED"
  prior_w=float(r["R1_winter_max_mean_c"]) if r["R1_winter_max_mean_c"] else None
  prior_s=float(r["R1_summer_jun_sep_max_mean_c"]) if r["R1_summer_jun_sep_max_mean_c"] else None
  wdiff=round(tmax_winter-prior_w,3) if prior_w is not None else None
  sdiff=round(tmax_summer-prior_s,3) if prior_s is not None else None
  conflict=bool((wdiff is not None and abs(wdiff)>=3) or (sdiff is not None and abs(sdiff)>=3))
  r["R1_NASA_custom_1991_2020_winter_tmax_c"]=tmax_winter
  r["R1_NASA_custom_1991_2020_summer_tmax_c"]=tmax_summer
  r["R1_NASA_custom_1991_2020_winter_tmin_c"]=tmin_winter
  r["R1_NASA_custom_1991_2020_summer_tmin_c"]=tmin_summer
  r["R1_NASA_point_raw_sha256"]=hashbytes(raw)
  r["R1_NASA_vs_ERA5_winter_tmax_diff_c"]=wdiff if wdiff is not None else ""
  r["R1_NASA_vs_ERA5_summer_tmax_diff_c"]=sdiff if sdiff is not None else ""
  r["R1_NASA_vs_ERA5_conflict_ge3c"]="TRUE" if conflict else "FALSE"
  r["R1_NASA_native_grid_elevation_m"]=loc[2] if len(loc)>2 else ""
  r["R1_NASA_model_status"]="INDEPENDENT_MODEL_DISAGREEMENT_PENDING" if conflict else "MODEL_POINT_PRELIMINARY_NOT_CMA"
  if not was_scanned:
   r["R1_status"]="SCANNED_NASA_MONTHLY_TMAX_TMIN_ONLY_MISSING_HOT_DAY_EXTREMES"
   r["R1_evidence_scope"]="NASA_MERRA2_POINT_IN_2017_HISTORIC_POLYGON"
   r["R1_missing_parameters"]="HOT_GE35_DAYS;CONTINUOUS_EXTREMES;RESIDENTIAL_AND_STATION_QA;2026_ADMIN_ROSTER"
   r["last_completed_round"]="R1_NASA_1991_2020_MONTHLY_GRID_ONLY"
   r["cascade_status"]="ACTIVE_PENDING"
  path=RAW/(code+"_NASA_CUSTOM_1991_2020.json")
  path.write_bytes(raw)
  success.append({"county":p["county_2025_name"],"code":code,"requested":requested,
     "actual_model_grid":[float(loc[1]),float(loc[0])],
     "model_grid_elevation_m":loc[2] if len(loc)>2 else None,
     "source_url":url,"source_raw_sha256":hashbytes(raw),
     "header_range":stated_range,
     "previous_ERA5_data":was_scanned,"NASA_winter_tmax_c":tmax_winter,
     "NASA_summer_tmax_c":tmax_summer,"NASA_winter_tmin_c":tmin_winter,
     "NASA_summer_tmin_c":tmin_summer,
     "NASA_minus_ERA5_winter_c":wdiff,"NASA_minus_ERA5_summer_c":sdiff,
     "model_conflict_ge3c":conflict,"formal_grade":None,
     "residential_elevation_verified":False,
     "official_2026_code_verified":False})
  print("NASA1991_SUCCESS",i,code,p["county_2025_name"],"winter",tmax_winter,
        "ERA5_conflict",conflict,flush=True)
 except Exception as e:
  failure.append({"code":p["county_code"],"county":p["county_2025_name"],"error":repr(e)})
  print("NASA1991_FAIL",i,p["county_code"],repr(e),flush=True)
 time.sleep(0.6)
if len(success)+len(failure)!=30:raise RuntimeError("Missing or duplicated requests")
new=sum(not x["previous_ERA5_data"] for x in success)
comparisons=[x for x in success if x["previous_ERA5_data"]]
covered=sum(r["R1_status"]!="NOT_SCREENED" for r in rows)
if covered!=22+new:raise RuntimeError("R1 genuine evidence count incorrect")
if any(r["confirmed_exit_round"] for r in rows) or any(str(r["valid_county_screening"]).lower()=="true" for r in rows):
 raise RuntimeError("No confirmed fatal / formal grade exists")
for r in rows:
 if r["R5_status"] not in ("NOT_SCREENED","NAMED_CITY_TAP_MONITORING_POINTS_ONLY_PENDING_BUILDING_QA"):
  raise RuntimeError("Prior R5 status changed")
outcsv=OUT/"national_R1_NASA_CUSTOM_1991_2020_30_point_evidence.csv"
with outcsv.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader();wr.writerows(rows)
res={"schema":"RET_NASA_POWER_REAL_CUSTOM_1991_2020_30_HISTORIC_COUNTIES_V1",
 "asof_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "scope":"30 nonofficial 2017 historic polygon and 2025 secondary code anchors, NOT current residential municipalities",
 "requested":30,"successful_1991_2020_TMAX_AND_TMIN_MODEL_POINTS":len(success),
 "failed_or_mismatched":len(failure),"source_failed_candidates":failure,
 "already_ERA5_with_NASA_comparison_count":len(comparisons),
 "new_R1_NASA_secondary_model_counties":new,
 "NASA_ERA5_conflict_ge3c_count":sum(x["model_conflict_ge3c"] for x in comparisons),
 "R1_counties_with_any_partial_climate_point_evidence":covered,
 "R1_not_scanned":2847-covered,"R1_carry_forward_to_R2":2847,
 "formal_valid_county_screenings":0,"confirmed_exclusions":0,
 "region_endpoint_period_rejected":"NASA regional output header 2001-2025 despite requested 1991-2020; excluded",
 "source_URI":"https://power.larc.nasa.gov/api/temporal/climatology/point",
 "source_model":"NASA POWER MERRA2 custom point normals 1991-2020, NOT CMA official",
 "original_before_csv_sha256":hashbytes(PRIOR.read_bytes()),
 "output_csv_sha256":hashbytes(outcsv.read_bytes()),
 "county_results":success,
 "cautions":["Monthly climatology does not provide >=35C days or consecutive hazard spells",
 "NASA native grid elevation may differ from dwelling, city or ERA5 grid elevation",
 "Model disagreement >=3C requires independent station arbitration, NEVER automatic exclusion",
 "Official 2026 nationwide current administrative code alignment unfinished",
 "Previous R2-R5 statuses preserved; no false formal grades"]}
path=OUT/"national_R1_NASA_CUSTOM_30_result.json"
path.write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:res[k] for k in ["requested","successful_1991_2020_TMAX_AND_TMIN_MODEL_POINTS",
 "failed_or_mismatched","already_ERA5_with_NASA_comparison_count",
 "new_R1_NASA_secondary_model_counties","NASA_ERA5_conflict_ge3c_count",
 "R1_counties_with_any_partial_climate_point_evidence","R1_not_scanned"]},ensure_ascii=False),flush=True)
if new==0:raise SystemExit(2)
