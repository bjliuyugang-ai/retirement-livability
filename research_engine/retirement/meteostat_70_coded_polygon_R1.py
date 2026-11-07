#!/usr/bin/env python3
"""Crosscheck 70 Chinese source-vetted 1991-2020 climate stations against
independent SIX-DIGIT-CODED county polygons.

Source: GeoCode-Release third-party packaged Tianditu map data, NOT an officially
certified 2026 Ministry of Civil Affairs county roster. The snapshot/vintage is
not established by this script. All 2017 historical geometry and 2025 name
mismatches are surfaced; sources with conflicting code remain HOLD.

Final R1 evidence is STATION_POINT_PARTIAL, NOT residence-wide climate and not
formal A/B/C/D rating; no county excluded for gaps or climate preferences.
"""
import collections,csv,datetime,hashlib,json,pathlib,re,urllib.request
from shapely.geometry import shape,Point
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
S=ROOT/"status/meteostat_CN_1991_2020_station_candidate_normals.json"
H=ROOT/"status/meteostat_70_CN_station_to_historic_county_spatial.json"
V2=ROOT/"status/r1_expand_strict_crosswalk_v2_fixed.json"
PREV=ROOT/"status/national_r5_tap_water_batch.csv"
PREVSUM=ROOT/"status/national_r5_tap_water_evidence.json"
MIRROR=ROOT/"evidence/mirror_2025_adcodes.txt"
URL="https://raw.githubusercontent.com/zzhonglei/GeoCode-Release/main/contributions/china-admin-boundaries/skill/data/china_county.geojson"
def sha(data):return hashlib.sha256(data).hexdigest()
raw_docs={}
for label,p in [("stations",S),("history",H),("crosswalk_v2",V2),("prior_national",PREVSUM)]:
 raw_docs[label]=json.loads(p.read_text(encoding="utf-8"))
station=raw_docs["stations"];history=raw_docs["history"];v2=raw_docs["crosswalk_v2"];previous=raw_docs["prior_national"]
longstations=[x for x in station["CN_1991_2020_candidate_station_normals"] if x["full30_yr_candidate_ge300months_everymonth_ge20"]]
hist_byid={str(x["station_id"]):x for x in history["station_records"]}
historic_code_byshape={str(x["shape_id_2017"]):str(x["county_code"]) for x in v2["all_unique_historic_county_matches"]}
if not(len(longstations)==70 and len(hist_byid)==70 and v2["unique_historic_name_crosswalk_matches"]>=1800 and previous["R5_carry_forward"]==2847):
 raise RuntimeError("Predecessor input count or version mismatch")
if sha(PREV.read_bytes())!=previous["CSV_sha256"]:raise RuntimeError("Old R5 2847 CSV source digest changed")
with PREV.open(encoding="utf-8-sig",newline="") as f:
 rd=csv.DictReader(f);priorfields=list(rd.fieldnames);priorrows=list(rd)
bycode={x["candidate_code"]:x for x in priorrows}
if len(priorrows)!=2847 or len(bycode)!=2847:raise RuntimeError("R0 2847 ledger missing")
archive={}
for line in MIRROR.read_text(encoding="utf-8").splitlines():
 if line.strip():
  fields=line.split(maxsplit=1)
  if len(fields)==2:archive[fields[0]]=fields[1]
if len(archive)<2800:raise RuntimeError("2025 mirror too small")
req=urllib.request.Request(URL,headers={"User-Agent":"retirement-cn-70-station-coded-county-crosscheck/1.0","Accept":"application/geo+json,application/json"})
with urllib.request.urlopen(req,timeout=120) as rr:raw=rr.read()
if not(1_000_000<=len(raw)<=90_000_000):raise RuntimeError("Coded county GeoJSON unexpected bytes "+str(len(raw)))
data=json.loads(raw)
features=data.get("features") or []
if not 2500<=len(features)<=3500:raise RuntimeError("Not nationwide county-like spatial layer "+str(len(features)))
polygons=[];seen_codes=collections.Counter();examples=[]
for f in features:
 prop=f.get("properties") or {}
 code=str(prop.get("adcode") or "")
 name=str(prop.get("name") or "")
 if not re.fullmatch(r"\\d{6}",code):
  raise RuntimeError("County geometry missing six-digit adcode "+str(prop)[:100])
 # Codes may repeat across multi polygons if source has nonunique attributes.
 g=shape(f["geometry"])
 if g.is_empty:continue
 seen_codes[code]+=1
 polygons.append((g.bounds,g,code,name,g.is_valid))
 if len(examples)<6:examples.append({"adcode":code,"name":name,"geom_type":g.geom_type,"geometry_valid":g.is_valid})
if not 2500<=len(polygons)<=3500:raise RuntimeError("No usable polygons")
stationrows=[];nohits=[];code_consistent=[];disagreements=[];ambig=[]
for p in longstations:
 sid=str(p["station_id"])
 hist=hist_byid[sid]
 pt=Point(float(p["longitude"]),float(p["latitude"]))
 found=[]
 for box,g,code,name,valid in polygons:
  if box[0]<=pt.x<=box[2] and box[1]<=pt.y<=box[3]:
   try:
    if g.covers(pt):found.append({"code":code,"name":name,"geometry_valid":valid})
   except Exception:pass
 codes=list(dict.fromkeys(x["code"] for x in found))
 result=found[0] if len(codes)==1 and len(found)==1 else None
 proposed_code=result["code"] if result else None
 proposed_name=result["name"] if result else None
 old_shape=hist["historical_2017_polygon_id"]
 old_code=historic_code_byshape.get(str(old_shape))
 name_in_mirror=archive.get(proposed_code)
 code_exists_in_provisional=proposed_code in bycode if proposed_code else False
 name_match=(name_in_mirror==proposed_name and (not code_exists_in_provisional or bycode[proposed_code]["candidate_name"]==proposed_name)) if proposed_code else False
 old_crosswalk_conflict=bool(old_code and proposed_code and old_code!=proposed_code)
 if not result:status="NO_UNIQUE_CODED_GIS_POLYGON"
 elif not code_exists_in_provisional:status="CODE_NOT_IN_PROVISIONAL_2847"
 elif not name_match:status="CODE_NAME_MISMATCH_WITH_2025_ROSTER"
 elif old_crosswalk_conflict:status="HISTORIC_2017_V2_CODE_DISAGREEMENT"
 elif not result["geometry_valid"]:status="CODED_GEOMETRY_INVALID"
 else:status="PROVISIONAL_CODED_POLYGON_AND_NAME_CONCORDANT"
 z={"station_id":sid,"latitude":p["latitude"],"longitude":p["longitude"],
 "station_elevation_m":p["altitude_m"],"tmax_tmin_observation_months":p["months_both_tmax_tmin_observation_class"],
 "source_station_country":"CN","winter_tmax_monthly_mean_c":p["winter_dec_feb_mean_daily_max_c"],
 "summer_tmax_monthly_mean_c":p["summer_jun_sep_mean_daily_max_c"],
 "winter_tmin_monthly_mean_c":p["winter_dec_feb_mean_daily_min_c"],
 "summer_tmin_monthly_mean_c":p["summer_jun_sep_mean_daily_min_c"],
 "provider_summary":p["observed_provider_counts"],
 "2017_historic_shape_id":old_shape,"2017_historic_shape_name":hist["historical_2017_polygon_english_name"],
 "2017_historic_v2_tentative_code":old_code,
 "coded_geometry_matching_features":len(found),"coded_geometry_all_hits":found,
 "2026_candidate_county_code":proposed_code,"coded_geometry_name":proposed_name,
 "2025_archive_county_name":name_in_mirror,
 "2025_roster_county_name":bycode[proposed_code]["candidate_name"] if code_exists_in_provisional else None,
 "source_quality_gate":status,"can_add_county_R1_station_evidence":status=="PROVISIONAL_CODED_POLYGON_AND_NAME_CONCORDANT",
 "historical_vs_coded_county_agree":bool(old_code and old_code==proposed_code),
 "2026_official_county_verification":False,"actual_residential_site_verified":False,
 "formal_grade":None,"fatal_county_exclusion":False}
 stationrows.append(z)
 if z["can_add_county_R1_station_evidence"]:code_consistent.append(z)
 else:disagreements.append(z)
 if not found:nohits.append(sid)
 if len(found)>1:ambig.append(sid)
byct=collections.defaultdict(list)
for x in code_consistent:byct[x["2026_candidate_county_code"]].append(x)
candidate_codes=set(byct)
existing_codes={r["candidate_code"] for r in priorrows if r["R1_status"]!="NOT_SCREENED"}
new_codes=sorted(candidate_codes-existing_codes)
# New evidence is provisional model-independent station point data only.
cols=priorfields+["R1_meteostat_station_ids","R1_meteostat_observation_months_min",
 "R1_meteostat_winter_tmax_station_c","R1_meteostat_summer_tmax_station_c",
 "R1_meteostat_winter_tmin_station_c","R1_meteostat_summer_tmin_station_c",
 "R1_meteostat_code_geospatial_QA","R1_meteostat_source","R1_meteostat_official_county_verified"]
for code,xx in byct.items():
 r=bycode[code]
 # Retain old ERA5 values if they exist, never quietly replace with independent station data.
 r["R1_meteostat_station_ids"]=";".join(sorted(x["station_id"] for x in xx))
 r["R1_meteostat_observation_months_min"]=min(x["tmax_tmin_observation_months"] for x in xx)
 r["R1_meteostat_winter_tmax_station_c"]=round(sum(x["winter_tmax_monthly_mean_c"] for x in xx)/len(xx),3)
 r["R1_meteostat_summer_tmax_station_c"]=round(sum(x["summer_tmax_monthly_mean_c"] for x in xx)/len(xx),3)
 r["R1_meteostat_winter_tmin_station_c"]=round(sum(x["winter_tmin_monthly_mean_c"] for x in xx)/len(xx),3)
 r["R1_meteostat_summer_tmin_station_c"]=round(sum(x["summer_tmin_monthly_mean_c"] for x in xx)/len(xx),3)
 r["R1_meteostat_code_geospatial_QA"]="THIRD_PARTY_SIX_DIGIT_POLYGON_WITH_2025_NAME_MIRROR_CONCORDANT"
 r["R1_meteostat_source"]="METEOSTAT_1991_2020_OBS_SOURCE_FILTERED_300_MONTHS"
 r["R1_meteostat_official_county_verified"]="FALSE"
 if code in new_codes:
  if r["R1_status"]!="NOT_SCREENED":raise RuntimeError("New county already has climate evidence unexpectedly")
  r["R1_status"]="STATION_30YEAR_OBS_POINT_PARTIAL_PENDING_RESIDENTIAL_AND_CODE_QA"
  r["R1_evidence_scope"]="CODED_POLYGON_STATION_LOCATION_NOT_RESIDENCE"
  r["R1_missing_parameters"]="HOT_GE35_DAYS;CONTINUOUS_EXTREMES;HUMIDITY;RESIDENTIAL_MICROCLIMATE;OFFICIAL_2026_CODE_AND_BOUNDARY_QA"
  r["R1_spatial_flag"]="THIRD_PARTY_GEOJSON_ONLY_2026_OFFICIAL_UNVERIFIED"
  r["last_completed_round"]="R1_STATION_1991_2020_PRELIMINARY"
  r["cascade_status"]="ACTIVE_PENDING"
  r["missing_parameter_list"]="R1_STATION_TO_RESIDENCE_QA_OPEN;R2_R5_MISSING;2026_ADMIN_SOURCE_OPEN"
after=sum(x["R1_status"]!="NOT_SCREENED" for x in priorrows)
if after!=len(existing_codes)+len(new_codes):raise RuntimeError("New county R1 station coverage incorrectly counted")
if any(r["confirmed_exit_round"] for r in priorrows) or any(str(r["valid_county_screening"]).lower()=="true" for r in priorrows):
 raise RuntimeError("Premature county exclusion/formal grade")
overlay=OUT/"national_R1_meteostat_coded_county_candidate_overlay_2847.csv"
with overlay.open("w",encoding="utf-8-sig",newline="") as f:
 writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader();writer.writerows(priorrows)
stationcsv=OUT/"meteostat_70_station_coded_county_spatial_QA.csv"
fields2=["station_id","latitude","longitude","station_elevation_m","tmax_tmin_observation_months",
 "2017_historic_shape_id","2017_historic_shape_name","2017_historic_v2_tentative_code",
 "coded_geometry_matching_features","2026_candidate_county_code","coded_geometry_name",
 "2025_archive_county_name","2025_roster_county_name",
 "source_quality_gate","can_add_county_R1_station_evidence",
 "historical_vs_coded_county_agree","2026_official_county_verification","actual_residential_site_verified",
 "winter_tmax_monthly_mean_c","summer_tmax_monthly_mean_c"]
with stationcsv.open("w",encoding="utf-8-sig",newline="") as f:
 writer=csv.DictWriter(f,fieldnames=fields2);writer.writeheader()
 for row in stationrows:writer.writerow({k:row.get(k) for k in fields2})
report={"schema":"RET_CN_STATION_70_CODED_COUNTY_POLYGON_AND_R1_OVERLAY_V1",
 "created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "coded_geodata_URL":URL,"coded_geodata_sha256":sha(raw),"coded_geodata_byte_count":len(raw),
 "coded_geo_features":len(features),"coded_geometry_parsed":len(polygons),
 "coded_geometry_distinct_codes":len(seen_codes),"coded_geometry_duplicate_codes":{k:v for k,v in seen_codes.items() if v>1},
 "coded_geometry_samples":examples,"provenance":"Third-party packaged Tianditu map source; official county code and date not independently certified",
 "source_station_json_sha256":sha(S.read_bytes()),
 "source_2017_geojson_station_QA_sha256":sha(H.read_bytes()),
 "source_2017_2025_crosswalk_v2_sha256":sha(V2.read_bytes()),
 "source_2025_roster_sha256":sha(MIRROR.read_bytes()),
 "source_national_R5_ledger_sha256":sha(PREV.read_bytes()),
 "input_1991_2020_long_observation_stations":70,
 "station_in_exactly_one_coded_polygon":sum(x["coded_geometry_matching_features"]==1 for x in stationrows),
 "station_outside_all_coded_polygons":len(nohits),
 "station_ambiguous_multiple_polygons":len(ambig),
 "station_provisional_code_geoposition_and_name_accepted":len(code_consistent),
 "station_unresolved_due_to_code_or_identity":len(disagreements),
 "accepted_distinct_provisional_counties":len(byct),
 "accepted_distinct_provisional_counties_with_prior_ERA5":len(set(byct)&existing_codes),
 "new_provisional_counties_with_station_point_temperature":len(new_codes),
 "total_provisional_counties_with_any_R1_point_temperature":after,
 "R1_remaining_unscanned_counties":2847-after,
 "all_2847_continue_to_R2":2847,"formal_valid_county_screenings":0,
 "official_current_2026_county_roster_verified":False,
 "confirmed_fatal_county_exclusions":0,
 "station_source_quality_counts":dict(collections.Counter(x["source_quality_gate"] for x in stationrows)),
 "new_code_ids":new_codes,
 "station_records":stationrows,
 "output_station_csv_sha256":sha(stationcsv.read_bytes()),
 "output_national_overlay_csv_sha256":sha(overlay.read_bytes()),
 "limitations":["Third-party coded polygons are not official 2026 boundaries or official roster",
 "A code+name match is provisional; residential elevation, site geology, urban pollution, 30-year climate outliers not validated",
 "Station dataset 300+ months with >=20 observations each calendar month, not complete 360 months or CMA certificated normals",
 "Historical 2017 shape and current coded boundary disagreement kept as HOLD",
 "No missing data or unsuitable comfort preference authorizes exclusion"]}
outpath=OUT/"meteostat_70_station_coded_county_spatial_QA.json"
outpath.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["coded_geo_features","coded_geometry_distinct_codes","input_1991_2020_long_observation_stations",
 "station_in_exactly_one_coded_polygon","station_provisional_code_geoposition_and_name_accepted",
 "station_unresolved_due_to_code_or_identity","accepted_distinct_provisional_counties",
 "new_provisional_counties_with_station_point_temperature",
 "total_provisional_counties_with_any_R1_point_temperature",
 "R1_remaining_unscanned_counties","station_source_quality_counts"]},ensure_ascii=False),flush=True)
