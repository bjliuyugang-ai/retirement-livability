#!/usr/bin/env python3
"""Real NASA POWER 1991-2020 gridded regional Tmax climatology for 30
strict historic county anchors in 16 province prefixes.

Regional requests by 8x8 degree tile (one call covers many grid cells).
Preserve previously measured ERA5. NEVER assert NASA is CMA, certified
current county, local residential temperature or whole-county exclusion.
No R1-R5 formal county grades.
"""
import collections,csv,datetime,hashlib,json,math,pathlib,time,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
CROSS=ROOT/"status/r1_expand_strict_crosswalk.json"
INCSV=ROOT/"status/national_r1_expanded.csv"
PREV=ROOT/"status/national_r1_expanded_summary.json"
SCHEMA=ROOT/"status/nasa_regional_schema_inspection.json"
def digest(b):return hashlib.sha256(b).hexdigest()
a=json.loads(CROSS.read_text(encoding="utf-8"));b=json.loads(PREV.read_text(encoding="utf-8"))
sc=json.loads(SCHEMA.read_text(encoding="utf-8"))
if not(a["sampled_count"]==30 and a["sampled_province_prefix_count"]==16 and
 b["cumulative_R1_point_data_counties"]==22 and b["R1_not_scanned"]==2825 and
 sc["feature_count"]==15 and sc["regional_parameters"]["T2M_MAX_AVG"]["units"]=="C"):
 raise RuntimeError("Source preflight failed")
if digest(INCSV.read_bytes())!=b["output_csv_sha256"]:raise RuntimeError("Previous R1 CSV hash mismatch")
with INCSV.open(encoding="utf-8-sig",newline="") as f:
 rd=csv.DictReader(f);fields=list(rd.fieldnames);rows=list(rd)
bycode={x["candidate_code"]:x for x in rows}
if len(rows)!=2847 or len(bycode)!=2847:raise RuntimeError("National county input count changed")
targets=a["selected_30"]
groups=collections.defaultdict(list)
for p in targets:
 lat=p["latitude_2017_polygon_interior"];lon=p["longitude_2017_polygon_interior"]
 group=(math.floor(lat/8)*8,math.floor(lon/8)*8)
 groups[group].append(p)
result={"schema":"RET_R1_NASA_REGIONAL_MODEL_30_ANCHORS_V1",
 "at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source":"NASA POWER 1991-2020 T2M_MAX_AVG regional gridded climatology, NASA MERRA2/POWER, not CMA",
 "input_historic_anchor_count":30,"distinct_province_prefixes":16,
 "source_crosswalk_sha256":digest(CROSS.read_bytes()),
 "prior_national_r1_sha256":digest(INCSV.read_bytes()),
 "NASA_request_8x8_tiles":len(groups),"tile_results":[],"records":[],"failures":[],
 "model_conflict_threshold_c":3.0,"confirmed_county_exclusions":0,
 "formal_valid_county_screenings":0,"official_2026_county_code_verifications":0,
 "notes":["Regional samples use modeled grid altitude; may differ from actual residential elevation",
 "Only monthly averaged daily maximum. Hot days>=35 and longest spells are NOT available from these climatologies",
 "ANN provided by API is ignored; annual maxima and monthly average cannot be assumed equivalent",
 "Do not overwrite ERA5: independent model divergence should be tracked and treated as conflict"]}
def get(lat,lon):
 params={"parameters":"T2M_MAX_AVG","community":"SB",
 "longitude-min":str(lon),"longitude-max":str(lon+8),
 "latitude-min":str(lat),"latitude-max":str(lat+8),"format":"JSON",
 "start":"1991","end":"2020"}
 url="https://power.larc.nasa.gov/api/temporal/climatology/regional?"+urllib.parse.urlencode(params)
 request=urllib.request.Request(url,headers={"User-Agent":"RetirementR1NASARegionalAudit/1.0","Accept":"application/json"})
 for attempt in range(2):
  try:
   with urllib.request.urlopen(request,timeout=100) as resp:raw=resp.read()
   return url,raw
  except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as exc:
   if isinstance(exc,urllib.error.HTTPError) and exc.code not in [429,500,502,503,504]:
    raise
   if attempt:raise
   time.sleep(8)
def monthmean(vals,months):
 mdays={"JAN":31,"FEB":28.25,"MAR":31,"APR":30,"MAY":31,"JUN":30,
 "JUL":31,"AUG":31,"SEP":30,"OCT":31,"NOV":30,"DEC":31}
 return round(sum(float(vals[k])*mdays[k] for k in months)/sum(mdays[k] for k in months),3)
for i,((minlat,minlon),pts) in enumerate(sorted(groups.items()),1):
 tile={"index":i,"lat_min":minlat,"lon_min":minlon,"requested_anchors":len(pts)}
 try:
  url,raw=get(minlat,minlon);payload=json.loads(raw)
  features=payload.get("features",[])
  if not features or not isinstance(features,list):raise ValueError("No actual NASA grid features")
  title=str(payload.get("header",{}).get("range",""))
  if "1991" not in title or "2020" not in title:raise ValueError("Wrong NASA climatology period "+title)
  if "T2M_MAX_AVG" not in payload.get("parameters",{}):raise ValueError("Not average daily maximum")
  grid=[]
  for f in features:
   coords=(f.get("geometry") or {}).get("coordinates") or []
   vals=((f.get("properties") or {}).get("parameter") or {}).get("T2M_MAX_AVG")
   if len(coords)<2 or not isinstance(vals,dict):continue
   if not all(k in vals and vals[k] is not None and -80<float(vals[k])<70 for k in ["JAN","FEB","MAR","JUN","JUL","AUG","SEP","DEC"]):
    continue
   grid.append({"latitude":float(coords[1]),"longitude":float(coords[0]),
                "model_elevation_m":float(coords[2]) if len(coords)>2 else None,
                "months":vals})
  if not grid:raise ValueError("No valid climate grid values")
  tile.update({"status":"REGIONAL_GRID_RETURNED","grid_points":len(grid),"raw_sha256":digest(raw),"raw_bytes":len(raw),"url":url})
  for pt in pts:
   lat=pt["latitude_2017_polygon_interior"];lon=pt["longitude_2017_polygon_interior"]
   nearest=min(grid,key=lambda g:(g["latitude"]-lat)**2 + ((g["longitude"]-lon)*math.cos(math.radians(lat)))**2)
   dlat=abs(nearest["latitude"]-lat);dlon=abs(nearest["longitude"]-lon)
   if dlat>0.75 or dlon>0.9:raise ValueError("NASA grid too distant from anchor: "+pt["county_code"]+":"+str((dlat,dlon)))
   vals=nearest["months"]
   winter=monthmean(vals,["DEC","JAN","FEB"])
   summer=monthmean(vals,["JUN","JUL","AUG","SEP"])
   code=pt["county_code"];old=bycode[code]
   era5=float(old["R1_winter_max_mean_c"]) if old["R1_winter_max_mean_c"] else None
   diff=round(winter-era5,3) if era5 is not None else None
   rec={"county_code_candidate":code,"name_2025":pt["county_2025_name"],
       "province_prefix":code[:2],"source_polygon_2017":pt["shape_name_2017"],
       "coordinate_intended":[lat,lon],
       "NASA_native_grid_center":[nearest["latitude"],nearest["longitude"]],
       "NASA_native_grid_elevation_m":nearest["model_elevation_m"],
       "anchor_grid_dlat_degrees":round(dlat,4),"anchor_grid_dlon_degrees":round(dlon,4),
       "NASA_monthly_T2M_MAX_AVG_c":{k:vals[k] for k in ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]},
       "NASA_winter_dec_feb_mean_daily_max_c":winter,
       "NASA_summer_jun_sep_mean_daily_max_c":summer,
       "previous_ERA5_winter_mean_daily_max_c":era5,
       "NASA_minus_ERA5_winter_c":diff,
       "model_conflict_flag":bool(diff is not None and abs(diff)>=3.0),
       "has_prior_ERA5_climate_record":era5 is not None,
       "regional_raw_sha256":digest(raw),"region_request_url":url,
       "data_vintage":"NASA_POWER_CUSTOM_1991_2020",
       "official_county_identity_verified":False,"residential_representativeness_verified":False,
       "can_exclude_this_county":False}
   result["records"].append(rec)
  tile["matched_anchors"]=len(pts)
 except Exception as ex:
  tile.update({"status":"BLOCKED_WITH_EVIDENCE","error":repr(ex)})
  for p in pts:result["failures"].append({"code":p["county_code"],"name":p["county_2025_name"],
                                         "tile":str((minlat,minlon)),"error":repr(ex)})
 result["tile_results"].append(tile)
 print("NASA_TILE",i,"of",len(groups),"status",tile["status"],
       "grid",tile.get("grid_points"),"matched",tile.get("matched_anchors"),flush=True)
 time.sleep(1)
if len(result["records"])+len(result["failures"])!=30:raise RuntimeError("Partial NASA tile loop double-counted a point")
extras=["R1_NASA_winter_mean_daily_max_c","R1_NASA_summer_jun_sep_mean_daily_max_c",
 "R1_NASA_native_grid_center_lat","R1_NASA_native_grid_center_lon",
 "R1_NASA_model_elevation_m","R1_NASA_model_conflict_flag",
 "R1_NASA_vs_ERA5_winter_c","R1_NASA_climate_source"]
for c in extras:
 if c in fields:raise RuntimeError("R1 NASA field already in prior ledger")
fields+=extras
extra=0;comparisons=0;conflicts=0
for rec in result["records"]:
 r=bycode[rec["county_code_candidate"]]
 r["R1_NASA_winter_mean_daily_max_c"]=rec["NASA_winter_dec_feb_mean_daily_max_c"]
 r["R1_NASA_summer_jun_sep_mean_daily_max_c"]=rec["NASA_summer_jun_sep_mean_daily_max_c"]
 r["R1_NASA_native_grid_center_lat"]=rec["NASA_native_grid_center"][0]
 r["R1_NASA_native_grid_center_lon"]=rec["NASA_native_grid_center"][1]
 r["R1_NASA_model_elevation_m"]=rec["NASA_native_grid_elevation_m"]
 r["R1_NASA_model_conflict_flag"]="TRUE" if rec["model_conflict_flag"] else "FALSE"
 r["R1_NASA_vs_ERA5_winter_c"]=rec["NASA_minus_ERA5_winter_c"] if rec["NASA_minus_ERA5_winter_c"] is not None else ""
 r["R1_NASA_climate_source"]="NASA_POWER_MERRA2_1991_2020_REGIONAL_TMAX_AVG"
 if rec["has_prior_ERA5_climate_record"]:
  comparisons+=1;conflicts+=int(rec["model_conflict_flag"])
 else:
  if r["R1_status"]!="NOT_SCREENED":raise RuntimeError("Overwriting non-unknown R1 "+r["candidate_code"])
  r["R1_status"]="SCANNED_NASA_SECONDARY_MODEL_TMAX_ONLY_PENDING_EXTREMES_AND_STATION"
  r["last_completed_round"]="R1_NASA_TMAX_MODEL_PARTIAL"
  r["R1_evidence_scope"]="NASA_NATIVE_GRID_WITH_2017_HISTORIC_COUNTY_ANCHOR"
  r["R1_missing_parameters"]="R1_TMIN_AND_HOT_DAYS;CMA_STATION_1991_2020;RESIDENTIAL_ALTITUDE;2026_COUNTY_ID"
  r["R1_spatial_flag"]="NASA_0.5deg_COARSE_GRID_NOT_RESIDENTIAL"
  r["cascade_status"]="ACTIVE_PENDING"
  extra+=1
actual=sum(x["R1_status"]!="NOT_SCREENED" for x in rows)
if actual!=22+extra:raise RuntimeError("Additional NASA evidence count mismatch")
if any(x["confirmed_exit_round"] for x in rows) or any(str(x["valid_county_screening"]).lower()=="true" for x in rows):
 raise RuntimeError("Unauthorized exclusion/formal screening detected")
if any(x["R2_status"] not in ["NOT_SCREENED","SCANNED_SUN_RAIN_POINT_HUMIDITY_PARTIAL","SCANNED_SUN_RAIN_POINT_HUMIDITY_MISSING"] for x in rows):
 raise RuntimeError("Prior R2 status overwritten")
outcsv=OUT/"national_R1_NASA_secondary_30_anchors.csv"
with outcsv.open("w",encoding="utf-8-sig",newline="") as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
result.update({"new_counties_with_NASA_Tmax_only_R1_evidence":extra,
 "NASA_vs_ERA5_counties_compared":comparisons,"NASA_vs_ERA5_winter_ge3c_conflict_count":conflicts,
 "total_R1_some_point_evidence_counties":actual,
 "R1_total_not_scanned":2847-actual,
 "R1_carry_forward_to_R2":2847,
 "NASA_new_data_does_not_imply_full_R1_temp_extremes_complete":True,
 "real_national_formal_valid_county_screenings":0,
 "output_csv_sha256":digest(outcsv.read_bytes()),
 "status":"REAL_NASA_SECONDARY_MODEL_EXPANSION" if extra>0 else "NO_NEW_COUNTIES"})
(OUT/"national_R1_NASA_secondary_expansion.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":result["status"],"new_NASA_only":extra,
 "measured_by_NASA":len(result["records"]),"failed":len(result["failures"]),
 "ERA5_compared":comparisons,"ERA5_NASA_winter_ge3c_conflicts":conflicts,
 "all_R1_some_evidence":actual,"R1_not_scanned":2847-actual},ensure_ascii=False),flush=True)
