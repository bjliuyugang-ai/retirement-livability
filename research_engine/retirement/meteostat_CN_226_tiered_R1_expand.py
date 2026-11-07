#!/usr/bin/env python3
"""Strict-then-interim Chinese 1991-2020 station source spatial expansion.

Use 226 already source-vetted Meteostat TMAX+TMIN observation-class records.
70 stations meet >=300 months and >=20 each calendar month: LOCKED HIGH CLASS.
Additional stations >=180 months and >=10 each calendar month are interim:
NOT certified 30-year 1991-2020 climatology, no official county grades and
no evidence-based exclusions. Source geometry is two independent historical
2017/coded third-party layers, with 2025 candidate roster strict code+name.
All GIS disagreements quarantined; 70 original accepted must reproduce.
"""
import collections,csv,datetime,hashlib,json,math,pathlib,urllib.request
from shapely.geometry import shape,Point
ROOT=pathlib.Path("research_engine/retirement")
OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
STATIONS=ROOT/"status/meteostat_CN_1991_2020_station_candidate_normals.json"
CROSS=ROOT/"status/r1_expand_strict_crosswalk_v2_fixed.json"
BASE=ROOT/"status/meteostat_70_station_coded_county_spatial_QA.json"
PREV=ROOT/"status/national_R2_meteostat_station_source_2847.csv"
R2S=ROOT/"status/national_R2_meteostat_station_source_evidence.json"
def digest(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text(encoding="utf-8"))
st=load(STATIONS);cross=load(CROSS);prior=load(BASE);r2=load(R2S)
if not(st["CN_stations_with_source_vetted_any"]==226 and
 st["CN_stations_meeting_ge300_both_tmax_tmin_and_20_per_calendar_month"]==70
 and prior["station_provisional_code_geoposition_and_name_accepted"]==69
 and prior["total_provisional_counties_with_any_R1_point_temperature"]==87
 and r2["R2_total_partial_site_counties"]==73
 and r2["formal_valid_county_screenings"]==0):
 raise RuntimeError("Frozen 226/70/69/87/73 sources changed")
if digest(PREV.read_bytes())!=r2["CSV_sha256"]:raise RuntimeError("Latest canonical R2 CSV SHA mismatch")
def fetch(url,expected_hash,limit):
 req=urllib.request.Request(url,headers={"User-Agent":"RetirementRealSourceExtendedCNStationSpatialQA/1.0"})
 with urllib.request.urlopen(req,timeout=160) as resp:raw=resp.read(limit+1)
 if len(raw)>limit or digest(raw)!=expected_hash:
  raise RuntimeError("GIS layer overlimit or source SHA mismatch "+url)
 return json.loads(raw),len(raw)
coded_geom,geo_bytes=fetch(prior["coded_geodata_URL"],prior["coded_geodata_sha256"],32_000_000)
historic,history_bytes=fetch(cross["source_2017_geojson_url"],cross["geometry_sha256"],45_000_000)
if not(len(coded_geom["features"])==2891 and len(historic["features"])==2864):
 raise RuntimeError("GIS polygon count drift")
with PREV.open(encoding="utf-8-sig",newline="") as f:
 rdr=csv.DictReader(f);fields=list(rdr.fieldnames);national=list(rdr)
bycode={r["candidate_code"]:r for r in national}
if len(national)!=2847 or len(bycode)!=2847:raise RuntimeError("National R0 denominator drift")
strong_codes={r["candidate_code"] for r in national if r["R1_status"]!="NOT_SCREENED"}
if len(strong_codes)!=87:raise RuntimeError("Strict R1 previous count not equal 87")
v2={str(x["shape_id_2017"]):str(x["county_code"]) for x in cross["all_unique_historic_county_matches"]}
def make_shapes(features,method):
 out=[]
 for f in features:
  geom=shape(f["geometry"])
  if geom.is_empty:continue
  p=f.get("properties") or {}
  if method=="coded":
   code=str(p.get("adcode") or "")
   name=str(p.get("name") or "")
   out.append((geom.bounds,geom,code,name,bool(geom.is_valid)))
  else:
   out.append((geom.bounds,geom,str(p.get("shapeID")),str(p.get("shapeName")),bool(geom.is_valid)))
 return out
coded=make_shapes(coded_geom["features"],"coded")
historical=make_shapes(historic["features"],"historic")
def locate(point,polys):
 out=[]
 for box,geom,code,name,valid in polys:
  if box[0]<=point.x<=box[2] and box[1]<=point.y<=box[3]:
   try:
    if valid and geom.covers(point):out.append((code,name))
   except Exception:pass
 return out
baseline={str(x["station_id"]):x for x in prior["station_records"]}
if len(baseline)!=70:raise RuntimeError("Original 70 station record count drift")
records=[]
for s in st["CN_1991_2020_candidate_station_normals"]:
 sid=str(s["station_id"]);lat=float(s["latitude"]);lon=float(s["longitude"])
 point=Point(lon,lat)
 hits=locate(point,coded);oldhits=locate(point,historical)
 code=hits[0][0] if len(hits)==1 else None
 name=hits[0][1] if len(hits)==1 else None
 oldsid=oldhits[0][0] if len(oldhits)==1 else None
 oldcode=v2.get(oldsid) if oldsid else None
 match_name=bool(code and code in bycode and bycode[code]["candidate_name"]==name)
 geo_conflict=bool(code and oldcode and code!=oldcode)
 months=int(s["months_both_tmax_tmin_observation_class"])
 minmonth=min(int(v) for v in s["months_in_each_calendar_month"].values())
 complete=months>=300 and minmonth>=20
 interim=months>=180 and minmonth>=10 and not complete
 sparse=months>=60 and minmonth>=3 and not complete and not interim
 if len(hits)!=1:quality="CODED_BOUNDARY_NONUNIQUE_OR_OUTSIDE"
 elif not match_name:quality="CODED_BOUNDARY_NAME_OR_ROSTER_MISMATCH"
 elif len(oldhits)!=1:quality="HISTORIC_BOUNDARY_NONUNIQUE_OR_OUTSIDE"
 elif geo_conflict:quality="2017_HISTORIC_AND_CODED_BOUNDARY_CONFLICT"
 elif complete:quality="FULL_PERIOD_CANDIDATE_LONG_STATION"
 elif interim:quality="INTERIM_15Y_OBSERVATIONS_PENDING_30Y"
 elif sparse:quality="LOW_5Y_OBSERVATIONS_ONLY"
 else:quality="LOW_OBSERVATION_COVERAGE"
 accepted=quality in ("FULL_PERIOD_CANDIDATE_LONG_STATION","INTERIM_15Y_OBSERVATIONS_PENDING_30Y")
 rec={"station_id":sid,"station_lat":lat,"station_lon":lon,
 "station_elevation_m":s["altitude_m"],
 "obs_month_count_in_1991_2020_range":months,
 "min_per_calendar_month_obs_years":minmonth,
 "long_300_and20":complete,"interim_180_and10":interim,
 "low_60_and3":sparse,
 "winter_mean_daily_tmax_c":s["winter_dec_feb_mean_daily_max_c"],
 "summer_mean_daily_tmax_c":s["summer_jun_sep_mean_daily_max_c"],
 "winter_mean_daily_tmin_c":s["winter_dec_feb_mean_daily_min_c"],
 "summer_mean_daily_tmin_c":s["summer_jun_sep_mean_daily_min_c"],
 "source_provider_by_obs_month":s["observed_provider_counts"],
 "coded_gis_polygon_hits":len(hits),"coded_candidate_code":code,
 "coded_candidate_name":name,
 "historical_2017_polygon_hits":len(oldhits),"historical_polygon_shapeid":oldsid,
 "historical_polygon_english_name":oldhits[0][1] if len(oldhits)==1 else None,
 "historic_2025_candidate_code":oldcode,
 "code_name_2025_roster_match":match_name,
 "historic_known_code_conflict":geo_conflict,
 "station_source_quality_status":quality,
 "accept_for_long_period_R1":quality=="FULL_PERIOD_CANDIDATE_LONG_STATION",
 "accept_for_interim_partial_R1":quality=="INTERIM_15Y_OBSERVATIONS_PENDING_30Y",
 "region_identity_official_2026_verified":False,
 "residential_microclimate_verified":False,
 "unqualified_for_formal_county_screening":True}
 if sid in baseline:
  orig=baseline[sid]
  if rec["accept_for_long_period_R1"]!=bool(orig["can_add_county_R1_station_evidence"]):
   raise RuntimeError("Previously accepted 70-station GIS association changed "+sid+":"+quality)
  if rec["accept_for_long_period_R1"] and code!=orig["2026_candidate_county_code"]:
   raise RuntimeError("Existing station county code changed unexpectedly "+sid)
 records.append(rec)
if len(records)!=226:raise RuntimeError("Source filtered station input incomplete")
strong=[z for z in records if z["accept_for_long_period_R1"]]
silver=[z for z in records if z["accept_for_interim_partial_R1"]]
if len(strong)!=69:raise RuntimeError("Strong 70 original mapping reproduction not 69")
bycounty=collections.defaultdict(list)
for z in silver:
 bycounty[z["coded_candidate_code"]].append(z)
silver_codes=set(bycounty)
new_codes=silver_codes-strong_codes
for code,stations in bycounty.items():
 old=bycode[code]
 # Do not replace existing 1991-2020 long-class ERA5/station measurements.
 old["R1_interim_15yr_station_ids"]=";".join(sorted(x["station_id"] for x in stations))
 old["R1_interim_15yr_obs_months_best"]=max(x["obs_month_count_in_1991_2020_range"] for x in stations)
 old["R1_interim_15yr_winter_tmax_approx_station_c"]=next(x["winter_mean_daily_tmax_c"] for x in sorted(stations,key=lambda x:x["obs_month_count_in_1991_2020_range"],reverse=True))
 old["R1_interim_15yr_summer_tmax_approx_station_c"]=next(x["summer_mean_daily_tmax_c"] for x in sorted(stations,key=lambda x:x["obs_month_count_in_1991_2020_range"],reverse=True))
 old["R1_interim_15yr_source_quality"]="OBS_SHORTER_THAN_30_YEAR_BASELINE_NOT_FOR_THRESHOLD"
 old["R1_interim_15yr_geom_quality"]="HIST_2017_AND_CODED_2025_NO_KNOWN_CONFLICT"
 old["R1_interim_15yr_missing_years"]="TRUE"
 old["R1_interim_15yr_official_2026_county_verified"]="FALSE"
 if code in new_codes:
  if old["R1_status"]!="NOT_SCREENED":raise RuntimeError("Interim new station attempted to overwrite prior R1")
  old["R1_status"]="INTERIM_STATION_180MONTH_OBS_SOURCE_PENDING_30Y_BASELINE"
  old["R1_evidence_scope"]="REAL_CN_STATION_MONTHLY_1991_2020_RANGE_BUT_LESS_THAN_30YEAR"
  old["R1_missing_parameters"]="FULL_1991_2020_STATION_YEAR_COVERAGE;DAILY_HOT_DAY_EXTREMES;ALTITUDE_RESIDENCE;OFFICIAL_2026_COUNTY"
  old["R1_spatial_flag"]="2017_VS_CODED_POLYGON_NO_KNOWN_CONFLICT_RESIDENCE_PENDING"
  old["last_completed_round"]="R1_INTERIM_15Y_OBS_SOURCE"
  old["cascade_status"]="ACTIVE_PENDING"
  old["missing_parameter_list"]=(old["missing_parameter_list"] or "")+";R1_30YEAR_REFERENCE_PERIOD_NOT_MET"
extra_cols=["R1_interim_15yr_station_ids","R1_interim_15yr_obs_months_best",
 "R1_interim_15yr_winter_tmax_approx_station_c",
 "R1_interim_15yr_summer_tmax_approx_station_c",
 "R1_interim_15yr_source_quality","R1_interim_15yr_geom_quality",
 "R1_interim_15yr_missing_years","R1_interim_15yr_official_2026_county_verified"]
for k in extra_cols:
 if k in fields:raise RuntimeError("R1 interim column already in input")
fields+=extra_cols
outfile=OUT/"national_R1_226_obs_station_quality_tiers_2847.csv"
with outfile.open("w",encoding="utf-8-sig",newline="") as f:
 writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(national)
stationcsv=OUT/"meteostat_CN_226_station_spatial_period_quality.csv"
col=["station_id","coded_candidate_code","coded_candidate_name","station_lat","station_lon","station_elevation_m","obs_month_count_in_1991_2020_range","min_per_calendar_month_obs_years","winter_mean_daily_tmax_c","summer_mean_daily_tmax_c","winter_mean_daily_tmin_c","summer_mean_daily_tmin_c","historical_polygon_english_name","historic_2025_candidate_code","station_source_quality_status","accept_for_long_period_R1","accept_for_interim_partial_R1","region_identity_official_2026_verified"]
with stationcsv.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=col);wr.writeheader()
 for z in records:wr.writerow({k:z[k] for k in col})
counts=collections.Counter(z["station_source_quality_status"] for z in records)
after=sum(r["R1_status"]!="NOT_SCREENED" for r in national)
if after!=87+len(new_codes):raise RuntimeError("Unexpected interim county R1 status count")
if any(r["confirmed_exit_round"] for r in national) or any(str(r["valid_county_screening"]).lower()=="true" for r in national):
 raise RuntimeError("Unauthorized final county grade/exclusion")
report={"schema":"RET_R1_CN_226_OBSERVATION_LONG_VS_INTERIM_COUNTRY_SPATIAL_SOURCE_QA_V1",
 "asof_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_station_1991_2020_raw_monthly_sha256":st["source_sha256"]["monthly_parquet"],
 "source_226station_record_json_sha256":digest(STATIONS.read_bytes()),
 "source_2017_GIS_SHA256":cross["geometry_sha256"],
 "source_coded_GIS_SHA256":prior["coded_geodata_sha256"],
 "source_national_2847_R2_csv_sha256":digest(PREV.read_bytes()),
 "original_226_observational_temperature_stations":226,
 "original_70_long_period_stations":70,
 "reproduced_69_long_station_identity_and_geometry_accepted":len(strong),
 "interim_180months_and10_eachmonth_observed_stations_eligible":sum(z["interim_180_and10"] for z in records),
 "interim_stations_spatially_accepted":len(silver),
 "interim_15yr_distinct_codes":len(silver_codes),
 "new_interim_only_candidate_counties":len(new_codes),
 "new_interim_county_codes":sorted(new_codes),
 "strict_long_period_or_ERA5_prior_R1_counties_unchanged":87,
 "R1_counties_with_any_real_point_including_short_history":after,
 "R1_counties_still_with_no_interim_or_strict_observation":2847-after,
 "R1_counties_NOT_30yr_complete_from_new_cohort":len(new_codes),
 "R2_old_partial_counties_unchanged":73,
 "station_quality_categories":dict(counts),
 "station_details":records,
 "high_quality_2026_official_county_boundaries_verified":0,
 "formal_valid_county_screenings":0,"confirmed_exclusions":0,
 "official_2026_county_roster_verified":False,
 "output_national_csv_sha256":digest(outfile.read_bytes()),
 "output_station_csv_sha256":digest(stationcsv.read_bytes()),
 "notes":["At least 180 distinct observed months plus every calendar month 10+ distinct years is a DISCOVERY cohort, not official 1991-2020 long-normal; cannot drive fatal winter/summer threshold decisions",
 "1991-2020 is the REQUESTED WINDOW, not confirmation of continuous 30 years for interim sites",
 "70 original strict station GIS outcome must reproduce exactly 69 accepted, 1 conflicting",
 "All new provisional county data is third-party GIS and compiled source, residential microclimate unknown",
 "No formal A/B/C/D, no auto exclusions, 2847 candidate conservation"]}
(OUT/"meteostat_CN_226_R1_tiered_expansion_evidence.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["original_226_observational_temperature_stations",
 "reproduced_69_long_station_identity_and_geometry_accepted",
 "interim_180months_and10_eachmonth_observed_stations_eligible",
 "interim_stations_spatially_accepted","interim_15yr_distinct_codes",
 "new_interim_only_candidate_counties",
 "strict_long_period_or_ERA5_prior_R1_counties_unchanged",
 "R1_counties_with_any_real_point_including_short_history",
 "R1_counties_still_with_no_interim_or_strict_observation",
 "station_quality_categories"]},ensure_ascii=False),flush=True)
