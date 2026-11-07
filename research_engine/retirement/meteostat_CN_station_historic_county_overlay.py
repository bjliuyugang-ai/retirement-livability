#!/usr/bin/env python3
"""Real point-in-polygon of 70 long-coverage CN Meteostat stations against
historical 2017 geoBoundaries CHN ADM3 polygons.

Strict only: exact polygon shapeID -> prior archived 12 + 30 unique Chinese-code
candidate crosswalks. Unmapped polygons retain English shapeName/ID, not guess
new administrative codes. 2026 official county identity remains unverified.
"""
import csv,datetime,hashlib,json,pathlib,urllib.request
from shapely.geometry import shape,Point
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/"status/meteostat_CN_1991_2020_station_candidate_normals.json"
CROSS=ROOT/"status/r1_expand_strict_crosswalk.json"
BASE=pathlib.Path("retirement-climate-pilot/status/latest-adcode-probe.json")
def digest(b):return hashlib.sha256(b).hexdigest()
src=json.loads(SRC.read_text(encoding="utf-8"))
cross=json.loads(CROSS.read_text(encoding="utf-8"))
orig=json.loads(BASE.read_text(encoding="utf-8"))
sites=[x for x in src["CN_1991_2020_candidate_station_normals"] if x["full30_yr_candidate_ge300months_everymonth_ge20"]]
if len(sites)!=70 or len(cross["selected_30"])!=30 or len(orig["candidate_links"])!=12:
 raise RuntimeError("Frozen 70 CN stations or 42 prior historic county candidates not found")
shape_codes={}
def add_id(shapeid,code,name,kind):
 if shapeid is None:raise RuntimeError("Missing historic shape ID")
 val=(str(code),str(name),kind)
 if shapeid in shape_codes and shape_codes[shapeid][0]!=val[0]:
  raise RuntimeError("Two county codes mapped to same historic shape: "+str(shapeid))
 shape_codes[shapeid]=val
for x in orig["candidate_links"]:
 add_id(x["polygon_shape_id"],x["candidate_code"],x["archival_county_chinese"],"EXISTING_12_HISTORIC_CROSSWALK")
for x in cross["selected_30"]:
 add_id(x["shape_id_2017"],x["county_code"],x["county_2025_name"],"DISTRIBUTED_30_HISTORIC_CROSSWALK")
url=cross["source_2017_geojson_url"]
request=urllib.request.Request(url,headers={"User-Agent":"RetirementCNStationCountySpatialQA/1.0"})
with urllib.request.urlopen(request,timeout=140) as r:raw=r.read()
if digest(raw)!=cross["geometry_sha256"]:
 raise RuntimeError("Historical polygon geometry source SHA drift; cannot silently join changing boundaries")
geo=json.loads(raw);features=geo["features"]
if len(features)!=cross["feature_count"]:raise RuntimeError("Historical ADM3 feature count changed")
shapes=[]
for f in features:
 g=shape(f["geometry"])
 if g.is_empty:continue
 props=f.get("properties") or {}
 shapes.append((g.bounds,g,props.get("shapeID"),props.get("shapeName"),g.is_valid))
out=[]
for station in sites:
 pt=Point(float(station["longitude"]),float(station["latitude"]))
 candidates=[]
 for box,g,sid,name,valid in shapes:
  if not valid:continue
  if box[0]<=pt.x<=box[2] and box[1]<=pt.y<=box[3] and g.covers(pt):
   candidates.append((sid,name))
 selected=candidates[0] if len(candidates)==1 else (None,None)
 code=shape_codes.get(selected[0]) if selected[0] else None
 out.append({"station_id":station["station_id"],"CN_country_code":"CN",
 "station_latitude":station["latitude"],"station_longitude":station["longitude"],
 "station_elevation_m":station["altitude_m"],
 "months_both_tmax_tmin_obs_class":station["months_both_tmax_tmin_observation_class"],
 "winter_mean_daily_max_c":station["winter_dec_feb_mean_daily_max_c"],
 "summer_mean_daily_max_c":station["summer_jun_sep_mean_daily_max_c"],
 "winter_mean_daily_min_c":station["winter_dec_feb_mean_daily_min_c"],
 "summer_mean_daily_min_c":station["summer_jun_sep_mean_daily_min_c"],
 "historical_2017_polygon_matches":len(candidates),
 "historical_2017_polygon_id":selected[0],
 "historical_2017_polygon_english_name":selected[1],
 "candidate_2025_county_code":code[0] if code else None,
 "candidate_2025_county_chinese_name":code[1] if code else None,
 "code_crosswalk_2017_quality":code[2] if code else "HISTORICAL_SHAPE_CODE_UNMAPPED",
 "station_location_in_hist_boundary_verified":len(candidates)==1,
 "2026_official_current_county_code_verified":False,
 "residential_microclimate_verified":False,
 "county_climate_grade":None,"county_exclusion_authorized":False,
 "ambiguous_polygon_shape_matches":[{"id":sid,"name":nm} for sid,nm in candidates] if len(candidates)!=1 else []})
unique=sum(q["historical_2017_polygon_matches"]==1 for q in out)
codes={q["candidate_2025_county_code"] for q in out if q["candidate_2025_county_code"]}
if len(out)!=70 or unique<30:raise RuntimeError("Unreasonably low exact GIS station-point coverage: "+str(unique))
path=OUT/"meteostat_70_CN_station_to_historic_county_spatial.csv"
headers=["station_id","CN_country_code","station_latitude","station_longitude","station_elevation_m",
 "months_both_tmax_tmin_obs_class","winter_mean_daily_max_c","summer_mean_daily_max_c",
 "winter_mean_daily_min_c","summer_mean_daily_min_c","historical_2017_polygon_matches",
 "historical_2017_polygon_id","historical_2017_polygon_english_name",
 "candidate_2025_county_code","candidate_2025_county_chinese_name",
 "code_crosswalk_2017_quality","station_location_in_hist_boundary_verified",
 "2026_official_current_county_code_verified","residential_microclimate_verified"]
with path.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=headers);wr.writeheader()
 for x in out:wr.writerow({k:x[k] for k in headers})
report={"schema":"RET_MSTA_70_CN_STATION_REAL_2017_COUNTY_PIP_V1",
 "at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "input_CN_1991_2020_long_stations":70,"historical_2017_ADM3_polygons":len(shapes),
 "historical_geometry_sha256":digest(raw),
 "source_stations_sha256":digest(SRC.read_bytes()),
 "source_crosswalk_sha256":digest(CROSS.read_bytes()),
 "strict_station_in_unique_2017_polygon_count":unique,
 "outside_or_ambiguous_polygon_count":70-unique,
 "station_to_previously_known_hist_county_code_count":sum(q["candidate_2025_county_code"] is not None for q in out),
 "distinct_known_hist_candidate_county_codes":len(codes),
 "unmapped_historic_polygon_english_name_stations":sum(q["historical_2017_polygon_matches"]==1 and q["candidate_2025_county_code"] is None for q in out),
 "known_candidate_code_records":sorted(codes),
 "station_records":out,
 "CSV_sha256":digest(path.read_bytes()),
 "formal_valid_county_screenings":0,"official_national_2026_roster_verified":False,
 "limitations":["2017 polygons historic, 2025 third-party code links and 2026 official register remain distinct",
 "Station locations in polygon are more grounded than nearest station; still not residential",
 "Seventy stations are not seventy distinct counties, station time series are 300+/360 months not formal CMA normals",
 "Unmapped polygon identity is NOT proof of absent province or county, keep for later crosswalk",
 "MERRA2 NASA climatology quarantined; no automatic grades or exclusions"]}
outpath=OUT/"meteostat_70_CN_station_to_historic_county_spatial.json"
outpath.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["input_CN_1991_2020_long_stations",
 "historical_2017_ADM3_polygons","strict_station_in_unique_2017_polygon_count",
 "station_to_previously_known_hist_county_code_count",
 "distinct_known_hist_candidate_county_codes",
 "unmapped_historic_polygon_english_name_stations"]},ensure_ascii=False),flush=True)
