#!/usr/bin/env python3
"""R3 real station-elevation and existing 36 DEM points crosswalk over 2847.

201 physically source-vetted China weather stations within 198 coded county
candidates, plus 12 previous DEM sampled pilot counties (5 overlap) => 205
distinct county candidates with some R3 point-elevation context.
NEVER infer residential altitude, A/B/C/D or whole county disqualification
from a station or three interior elevation samples.
"""
import collections,csv,datetime,hashlib,json,pathlib
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
STATION=ROOT/"status/meteostat_CN_226_R1_tiered_expansion_evidence.json"
DEM=ROOT/"status/national_r3_first_real_batch_evidence.json"
SOURCE=ROOT/"status/national_R1R2_joint_2847_evidence_and_missingness.csv"
SUM=ROOT/"status/national_R1R2_joint_missingness_evidence.json"
def sha(b):return hashlib.sha256(b).hexdigest()
sta=json.loads(STATION.read_text(encoding="utf-8"))
dem=json.loads(DEM.read_text(encoding="utf-8"))
summary=json.loads(SUM.read_text(encoding="utf-8"))
if not(sta["original_226_observational_temperature_stations"]==226 and
 sta["reproduced_69_long_station_identity_and_geometry_accepted"]==69 and
 sta["interim_stations_spatially_accepted"]==132 and
 dem["R3_DEM_three_point_counties"]==12 and dem["DEM_total_samples"]==36 and
 summary["R1_any_history_station_point_counties"]==214 and
 summary["R2_any_history_precip_or_sun_point_counties"]==199):
 raise RuntimeError("R3 source preflight mismatch")
if sha(SOURCE.read_bytes())!=summary["output_sha256"]["national_csv"]:
 raise RuntimeError("Source national R1R2 joint SHA drift")
with SOURCE.open(encoding="utf-8-sig",newline="") as f:
 reader=csv.DictReader(f);fields=list(reader.fieldnames);rows=list(reader)
bycode={r["candidate_code"]:r for r in rows}
if len(rows)!=2847 or len(bycode)!=2847:raise RuntimeError("No unique 2847 county candidates")
entries=collections.defaultdict(list)
for r in sta["station_details"]:
 if not (r["accept_for_long_period_R1"] or r["accept_for_interim_partial_R1"]):continue
 code=r["coded_candidate_code"]
 if code not in bycode or bycode[code]["candidate_name"]!=r["coded_candidate_name"]:
  raise RuntimeError("Source station historic code-name collision "+str((code,r["coded_candidate_name"])))
 h=r["station_elevation_m"]
 if h is None or h< -300 or h>8000:raise RuntimeError("Nonphysical station elevation "+str((code,h)))
 entries[code].append(r)
station_codes=set(entries)
if len(station_codes)!=198 or sum(map(len,entries.values()))!=201:
 raise RuntimeError("Expected 198 county codes and 201 distinct station source sites")
dem_bycode={str(r["candidate_code"]):r for r in dem["R3_records"]}
if len(dem_bycode)!=12:raise RuntimeError("DEM 12 distinct candidate counties expected")
both=station_codes & set(dem_bycode)
union=station_codes | set(dem_bycode)
if len(both)!=5 or len(union)!=205:raise RuntimeError("Station DEM region overlap changed")
extra=["R3_evidence_scope","R3_meteostat_alt_station_count","R3_meteostat_station_ids",
 "R3_meteostat_elev_min_m","R3_meteostat_elev_max_m",
 "R3_meteostat_elev_span_m","R3_station_elev_band_observation_only",
 "R3_station_elevation_ge2000_count",
 "R3_meteostat_station_location_latlons",
 "R3_station_vs_DEM_ranges_overlap",
 "R3_multi_station_large_altitude_gap",
 "R3_actual_residential_altitude_verified",
 "R3_2026_official_county_boundary_verified","R3_residential_microclimate_grade"]
for k in extra:
 if k in fields:raise RuntimeError("R3 would overwrite existing source column "+k)
fields+=extra
bandcounts=collections.Counter();conflicts=[]
records=[]
for code,xx in sorted(entries.items()):
 rr=bycode[code]
 stationheights=[int(x["station_elevation_m"]) for x in xx]
 mn,mx=min(stationheights),max(stationheights)
 def flag(v):
  if v<=1500:return "STATION_POINT_LE1500M"
  if v<=1800:return "STATION_POINT_1500_TO1800M"
  if v<=2000:return "STATION_POINT_1800_TO2000M"
  return "STATION_POINT_GT2000M"
 bands=[flag(h) for h in stationheights]
 if len(set(bands))>1:bandlabel="MULTIPLE_STATION_ALTITUDE_BANDS"
 else:bandlabel=bands[0]
 bandcounts[bandlabel]+=1
 rr["R3_meteostat_alt_station_count"]=len(xx)
 rr["R3_meteostat_station_ids"]=";".join(x["station_id"] for x in xx)
 rr["R3_meteostat_elev_min_m"]=mn
 rr["R3_meteostat_elev_max_m"]=mx
 rr["R3_meteostat_elev_span_m"]=mx-mn
 rr["R3_station_elev_band_observation_only"]=bandlabel
 rr["R3_station_elevation_ge2000_count"]=sum(h>2000 for h in stationheights)
 rr["R3_meteostat_station_location_latlons"]=";".join(str(x["station_lat"])+","+str(x["station_lon"]) for x in xx)
 rr["R3_multi_station_large_altitude_gap"]="YES_REVIEW_SITE_GEOMETRY" if mx-mn>=300 else "NO_LARGE_INTRA_STATION_SPAN"
 rr["R3_actual_residential_altitude_verified"]="FALSE"
 rr["R3_2026_official_county_boundary_verified"]="FALSE"
 rr["R3_residential_microclimate_grade"]="NOT_AUTHORIZED_FROM_STATION_ALTITUDE"
 demitem=dem_bycode.get(code)
 if demitem:
  # do not confuse a 3-point county DEM range with dwelling elevation.
  overlap=not(mx<demitem["min_m"] or mn>demitem["max_m"])
  rr["R3_station_vs_DEM_ranges_overlap"]="YES_EXPLORATORY" if overlap else "NO_HIGH_SPATIAL_HETEROGENEITY_REVIEW"
  if not overlap:conflicts.append({"code":code,"name":rr["candidate_name"],"station_min":mn,"station_max":mx,
                                  "dem_min":demitem["min_m"],"dem_max":demitem["max_m"]})
 else:rr["R3_station_vs_DEM_ranges_overlap"]="DEM_NOT_MEASURED"
 if rr["R3_status"]=="NOT_SCREENED":
  rr["R3_status"]="OBS_STATION_ELEVATION_POINT_ONLY_NOT_RESIDENTIAL_GRADE"
  rr["last_completed_round"]="R3_METEOSTAT_STATION_ELEVATION_PARTIAL"
  rr["R3_evidence_scope"]="SOURCE_VETTED_STATION_METADATA_AND_THIRD_PARTY_CODED_GIS"
  rr["R3_missing_parameters"]="ACTUAL_RESIDENCE_ALTITUDE;WITHIN_COUNTY_LOW_VALLEY;DEM_POLYGON_SPREAD;GEOHAZARD;OFFICIAL_2026_BOUNDARY"
  rr["cascade_status"]="ACTIVE_PENDING"
  rr["missing_parameter_list"]=(rr["missing_parameter_list"] or "")+";R3_STATION_ELEVATION_NOT_RESIDENTIAL"
 elif not (code in dem_bycode):raise RuntimeError("Unexpected preexisting R3 status "+code)
 records.append({"candidate_code":code,"county_name":rr["candidate_name"],
  "station_ids":[x["station_id"] for x in xx],
  "station_locations":[{"lat":x["station_lat"],"lon":x["station_lon"],"elev_m":x["station_elevation_m"],
    "R1_monthly_observation_count":x["obs_month_count_in_1991_2020_range"],
    "source_quality":x["station_source_quality_status"]} for x in xx],
  "min_m":mn,"max_m":mx,"station_elevation_band":bandlabel,
  "previous_dem_sample_3_points":demitem["historical_polygon_dem_points"] if demitem else None,
  "full_residential_altitude_grade_authorized":False})
total=sum(r["R3_status"]!="NOT_SCREENED" for r in rows)
if total!=205:raise RuntimeError("R3 coverage must equal union 205, actually "+str(total))
if any(r["confirmed_exit_round"] for r in rows) or any(str(r["valid_county_screening"]).lower()=="true" for r in rows):
 raise RuntimeError("R3 has unauthorized elimination or grading")
outcsv=OUT/"national_R3_201_station_36DEM_2847_missing_and_altitude.csv"
with outcsv.open("w",encoding="utf-8-sig",newline="") as f:
 writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
qa={"schema":"RET_NATIONAL_R3_STATION_ALTITUDE_201OBS_36DEM_POINTS_205_COUNTY_CANDIDATES_V1",
 "at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_226_station_json_sha256":sha(STATION.read_bytes()),
 "source_36DEM_summary_sha256":sha(DEM.read_bytes()),
 "source_R1R2_national_csv_sha256":sha(SOURCE.read_bytes()),
 "national_provisional_input":2847,
 "station_altitude_point_records":201,"station_altitude_distinct_county_candidates":198,
 "existing_dem_sample_counties":12,"existing_dem_points":36,
 "station_and_dem_same_code_counties":5,
 "distinct_county_candidates_with_ANY_station_or_dem_R3_point_evidence":total,
 "R3_unknown_no_elevation_points_counties":2847-total,
 "confirmed_exclusions":0,"formal_valid_county_screenings":0,
 "2026_official_county_shapes_verified":0,"actual_residence_altitude_verified":0,
 "station_band_counts":dict(bandcounts),
 "multi_station_altitude_spread_ge300_counties":sum(r.get("R3_multi_station_large_altitude_gap")=="YES_REVIEW_SITE_GEOMETRY" for r in rows),
 "station_vs_DEM_nonoverlap_candidate_counties":conflicts,
 "station_level_records":records,
 "national_CSV_sha256":sha(outcsv.read_bytes()),
 "key_limits":["Station elevation is a weather instrument altitude, not townhall nor dwelling",
 "GLO90 Copernicus sampled 3 points are NOT a full county elevation map",
 "Master V1.2 1500/1800/2000 metre band applies to ACTUAL RESIDENTIAL ELEVATION, not source station",
 "Historic 2017 county geometry and third-party coded modern polygons do not establish certified 2026 current boundary",
 "Even high-altitude station does not justify elimination if lower habitable valley might exist"]}
(OUT/"national_R3_station_elevations_actual_evidence.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"R3_station_point_counties":198,"R3_DEM_previous_counties":12,
 "R3_overlap":5,"R3_unique_counties":total,"R3_missing":2847-total,
 "source_stations":201,"multi_station_large_altitude_gap":qa["multi_station_altitude_spread_ge300_counties"],
 "station_vs_DEM_source_mismatch":len(conflicts),"point_altitude_reference_bands":qa["station_band_counts"],
 "confirmed_exits":0,"formal_valid_county_screenings":0},ensure_ascii=False),flush=True)
