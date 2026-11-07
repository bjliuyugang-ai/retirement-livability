#!/usr/bin/env python3
"""Exploratory nationwide zonal extraction of 1991-2020 1km monthly tasmax.

This is a source-value and spatial-processing pilot for active action
RET-CASCADE-NATIONAL-R1_R2_30YEAR_GRID_SCALE-017. It does NOT produce formal
county screenings, A/B/C/D grades, exclusions, or residential-site claims.
"""
from __future__ import annotations
import csv, datetime, hashlib, json, math, os, pathlib, sys, time, urllib.request, urllib.error, zipfile

ROOT=pathlib.Path("research_engine/retirement")
OUT=ROOT/"output"
STATUS=ROOT/"status"
CACHE=OUT/"scidb_download"
TASK="tasks/6aead9a989808191ad42f80fd4e32bf1/phase1"
ACTION_ID="RET-CASCADE-NATIONAL-R1_R2_30YEAR_GRID_SCALE-017"
DATASET_ID="cece16f1863b4ebd839894f6df26f8ac"
DATASET_VERSION="V8"
FILE_ID="dba1c67431a07f5c3a7d18a83bd876d2"
ARCHIVE_NAME="China_tasmax_1km_1991-2020.zip"
TIF_NAME="China_tasmax_1km_1991-2020.tif"
DOWNLOAD_URL="https://china.scidb.cn/download?fileId="+FILE_ID
GEOMETRY_URL="https://raw.githubusercontent.com/zzhonglei/GeoCode-Release/main/contributions/china-admin-boundaries/skill/data/china_county.geojson"
GEOMETRY_SHA256="22db6c54b9cb0118ecdcc8a117bf2da4fc24a2229cdba7e6e55dbb5dd56e8246"
EXPECTED_ARCHIVE_SHA256="9653ce27adfab762e4e1b6ceed4029c774f3b4779375bf8c61172f787d38280a"
EXPECTED_TIF_SHA256="5446efe7b39c900388172620e9987280bcbbae625c119b9906aba607a9e1523a"
EXPECTED_TIF_BYTES=297478422
ROSTER=ROOT/"evidence/provisional_counties_2026_06.csv"
EXISTING_R1=STATUS/"national_R1_226_obs_station_quality_tiers_2847.csv"
STATIONS=STATUS/"meteostat_70_station_coded_county_spatial_QA.csv"
OUTCSV=STATUS/"scidb_tasmax_1km_2838_county_zonal_1991_2020.csv"
OUTJSON=STATUS/"scidb_tasmax_1km_2838_county_zonal_evidence_20261107.json"
PROGRESS=OUT/"scidb_tasmax_zonal_progress.json"

def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha_file(p:pathlib.Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
    return h.hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
def fetch_bytes(url,timeout=120,max_bytes=40_000_000):
    req=urllib.request.Request(url,headers={"User-Agent":"RetirementNationalGridZonal/1.0","Accept":"*/*"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        b=r.read(max_bytes+1)
        status=r.status
        ctype=r.headers.get("Content-Type")
        clen=r.headers.get("Content-Length")
    if len(b)>max_bytes:raise RuntimeError("DOWNLOAD_EXCEEDS_LIMIT "+url)
    return b,{"http_status":status,"content_type":ctype,"content_length_header":clen,"bytes":len(b)}
def download_large(url,dest,expected_sha=None,expected_size=None):
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():
        size=dest.stat().st_size
        digest=sha_file(dest)
        if (expected_size is None or size==expected_size) and (expected_sha is None or digest==expected_sha):
            return {"reused_existing":True,"bytes":size,"sha256":digest,"http_status":200}
        dest.unlink()
    part=dest.with_suffix(dest.suffix+".part")
    last_error=None
    for attempt in range(1,4):
        offset=part.stat().st_size if part.exists() else 0
        headers={"User-Agent":"RetirementNationalGridZonal/1.0","Accept":"application/octet-stream"}
        if offset:headers["Range"]=f"bytes={offset}-"
        req=urllib.request.Request(url,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=180) as r:
                status=r.status
                if offset and status!=206:
                    offset=0
                    mode="wb"
                else:mode="ab" if offset else "wb"
                with part.open(mode) as f:
                    while True:
                        block=r.read(4*1024*1024)
                        if not block:break
                        f.write(block)
            size=part.stat().st_size
            if expected_size is not None and size!=expected_size:
                raise RuntimeError(f"SIZE_MISMATCH expected={expected_size} got={size}")
            digest=sha_file(part)
            if expected_sha and digest!=expected_sha:raise RuntimeError("SHA256_MISMATCH "+digest)
            part.replace(dest)
            return {"http_status":status,"bytes":size,"sha256":digest,"attempts":attempt}
        except Exception as e:
            last_error=f"{type(e).__name__}: {e}"
            if attempt==3:break
            time.sleep(5*attempt)
    raise RuntimeError("DOWNLOAD_FAILED_AFTER_3_ATTEMPTS "+str(last_error))
def parse_csv(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        rd=csv.DictReader(f);return list(rd.fieldnames or []),list(rd)
def parse_bool(x):return str(x).strip().lower() in ("true","1","yes")
def finite(x):
    try:
        y=float(x)
        return y if math.isfinite(y) else None
    except Exception:return None
def mean_or_none(xs):
    xs=[float(x) for x in xs if x is not None and math.isfinite(float(x))]
    return sum(xs)/len(xs) if xs else None
def status_for(value,lo,hi):
    if value is None:return "NOT_MEASURED"
    if value<lo:return "BELOW_IDEAL_NOT_FATAL"
    if value>hi:return "ABOVE_IDEAL_NOT_FATAL"
    return "WITHIN_IDEAL_TARGET"
def main():
    import numpy as np
    import rasterio
    from rasterio.features import geometry_mask, geometry_window
    from shapely.geometry import shape, mapping

    OUT.mkdir(parents=True,exist_ok=True);STATUS.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    run_id=os.getenv("GITHUB_RUN_ID","MANUAL")
    started=now()
    summary={
      "schema":"RET_SCIDB_TASMAX_1KM_NATIONAL_ZONAL_EVIDENCE_V1",
      "run_id":run_id,"action_id":ACTION_ID,"started_at_utc":started,
      "dataset":{"id":DATASET_ID,"version":DATASET_VERSION,"file_id":FILE_ID,
        "file_name":ARCHIVE_NAME,"period":"1991-2020","variable":"tasmax",
        "variable_semantics":"monthly mean of daily maximum temperature; daily extremes and >=35C day counts are not derivable from these 12 monthly normals",
        "download_url":DOWNLOAD_URL,"license_terms":"not independently verified; exploratory use only"},
      "geometry_source":{"url":GEOMETRY_URL,"sha256_expected":GEOMETRY_SHA256,
        "vintage":"not independently certified","coordinate_reference":"GeoJSON assumed WGS84; independent datum certification pending",
        "status":"THIRD_PARTY_CODED_GEOMETRY_PROVISIONAL"},
      "input_counties":0,"geometry_features":0,"exact_code_name_matches":0,
      "missing_geometry_counties":0,"zonal_stats_counties":0,"complete_12_month_grid_counties":0,
      "new_grid_counties_without_prior_R1_point_evidence":0,
      "station_crosscheck":{},"raster":{},"formal_valid_county_screenings":0,
      "confirmed_county_exclusions":0,"carry_forward_counties":2847,
      "status":"RUNNING","limitations":[
        "This is exploratory grid extraction, not a formal county climate screening or A/B/C/D grade.",
        "2026 official county codes and third-party geometry vintage/datum are not certified.",
        "A county polygon mean cannot replace actual residential-site climate or county internal valley/mountain/coastal exceptions.",
        "Monthly climatology cannot provide daily ET comfort days, >=35C days, heat/cold spell duration, humidity/dewpoint, or consecutive rainy days.",
        "No county is excluded; all 2847 provisional candidates remain in the cascade."
      ]}
    write_json(PROGRESS,{"run_id":run_id,"status":"STARTED","started_at_utc":started,"processed":0})

    roster_fields,roster=parse_csv(ROSTER)
    if len(roster)!=2847 or len({x["code"] for x in roster})!=2847:raise RuntimeError("ROSTER_COUNT_OR_UNIQUENESS_FAIL")
    summary["input_counties"]=len(roster)
    r1_fields,r1rows=parse_csv(EXISTING_R1)
    if "candidate_code" not in r1_fields:raise RuntimeError("EXISTING_R1_MISSING_CANDIDATE_CODE")
    existing_r1=set()
    for r in r1rows:
        code=r.get("candidate_code","")
        tier=str(r.get("R1_status",""))
        if code and tier and tier not in ("NOT_SCREENED","NO_DATA_PENDING",""):existing_r1.add(code)

    geom_path=CACHE/"china_county.geojson"
    if not geom_path.exists() or sha_file(geom_path)!=GEOMETRY_SHA256:
        gb,gmeta=fetch_bytes(GEOMETRY_URL,max_bytes=30_000_000)
        if sha_bytes(gb)!=GEOMETRY_SHA256:raise RuntimeError("GEOMETRY_SHA256_MISMATCH "+sha_bytes(gb))
        geom_path.write_bytes(gb)
    else:gmeta={"reused_existing":True,"bytes":geom_path.stat().st_size}
    geometry_raw=geom_path.read_bytes()
    if sha_bytes(geometry_raw)!=GEOMETRY_SHA256:raise RuntimeError("GEOMETRY_HASH_RECHECK_FAIL")
    geodata=json.loads(geometry_raw.decode("utf-8"))
    features=geodata.get("features") or []
    if len(features)!=2891:raise RuntimeError("GEOMETRY_FEATURE_COUNT_MISMATCH "+str(len(features)))
    geo={}
    for f in features:
        p=f.get("properties") or {}
        code=str(p.get("adcode") or "")
        name=str(p.get("name") or "")
        if len(code)!=6 or not code.isdigit():raise RuntimeError("INVALID_GEOMETRY_ADCODE "+code)
        if code in geo:raise RuntimeError("DUPLICATE_GEOMETRY_CODE "+code)
        geo[code]={"name":name,"geometry":f.get("geometry")}
    exact=[r for r in roster if r["code"] in geo and r["name"]==geo[r["code"]]["name"]]
    missing=[r for r in roster if r["code"] not in geo or r["name"]!=geo[r["code"]]["name"]]
    if len(exact)!=2838 or len(missing)!=9:raise RuntimeError(f"EXPECTED_2838_EXACT_9_PENDING_GOT_{len(exact)}_{len(missing)}")
    summary["geometry_features"]=len(features)
    summary["exact_code_name_matches"]=len(exact)
    summary["missing_geometry_counties"]=len(missing)
    summary["geometry_source"].update({"download_meta":gmeta,"sha256_actual":sha_bytes(geometry_raw),
      "geometry_codes":len(geo),"exact_code_name_match_count":len(exact),
      "missing_or_name_mismatch_count":len(missing)})

    tif=CACHE/TIF_NAME
    archive=CACHE/ARCHIVE_NAME
    if tif.exists() and tif.stat().st_size==EXPECTED_TIF_BYTES and sha_file(tif)==EXPECTED_TIF_SHA256:
        raster_download={"reused_verified_geotiff":True,"geotiff_bytes":tif.stat().st_size,"geotiff_sha256":EXPECTED_TIF_SHA256}
        archive_meta={"archive_sha256":EXPECTED_ARCHIVE_SHA256,"verified_from_prior_run":True}
    else:
        archive_meta=download_large(DOWNLOAD_URL,archive,EXPECTED_ARCHIVE_SHA256,293775088)
        with zipfile.ZipFile(archive) as z:
            bad=z.testzip()
            if bad:raise RuntimeError("ZIP_CRC_FAIL "+bad)
            members=[m for m in z.infolist() if m.filename.lower().endswith((".tif",".tiff"))]
            if len(members)!=1:raise RuntimeError("EXPECTED_ONE_GEOTIFF_MEMBER_GOT_"+str(len(members)))
            member=members[0]
            with z.open(member) as src,tif.open("wb") as dst:
                while True:
                    b=src.read(8*1024*1024)
                    if not b:break
                    dst.write(b)
        if tif.stat().st_size!=EXPECTED_TIF_BYTES:raise RuntimeError("GEOTIFF_SIZE_MISMATCH "+str(tif.stat().st_size))
        if sha_file(tif)!=EXPECTED_TIF_SHA256:raise RuntimeError("GEOTIFF_SHA_MISMATCH")
        raster_download={"reused_verified_geotiff":False,"geotiff_bytes":tif.stat().st_size,"geotiff_sha256":EXPECTED_TIF_SHA256}
        archive.unlink(missing_ok=True)
    station_fields,station_rows=parse_csv(STATIONS)
    if not {"latitude","longitude","can_add_county_R1_station_evidence","winter_tmax_monthly_mean_c","summer_tmax_monthly_mean_c"}.issubset(set(station_fields)):
        raise RuntimeError("STATION_CROSSCHECK_SCHEMA_MISMATCH")
    stations=[r for r in station_rows if parse_bool(r["can_add_county_R1_station_evidence"])]
    station_comparisons={"n_station_candidates":len(stations),"winter_abs_errors":[],"summer_abs_errors":[],"winter_bias":[],"summer_bias":[]}
    with rasterio.open(tif) as ds:
        if ds.count!=12 or ds.crs is None or ds.width!=6165 or ds.height!=3538:
            raise RuntimeError(f"RASTER_SCHEMA_MISMATCH bands={ds.count} size={ds.width}x{ds.height} crs={ds.crs}")
        # Probe finite values across the whole footprint and at station points.
        probe=ds.read(1,out_shape=(min(600,ds.height),min(600,ds.width)),masked=False)
        probe_valid=probe[np.isfinite(probe) & (probe>-1e20) & (probe<1e20)]
        if probe_valid.size<100:raise RuntimeError("RASTER_SAMPLE_HAS_TOO_FEW_FINITE_VALUES "+str(probe_valid.size))
        units=ds.units[0] if ds.units else None
        tags=ds.tags();band_tags=ds.tags(1)
        med=float(np.median(probe_valid))
        if units and any(x in units.lower() for x in ["kelvin","degree_k"," k"]):unit_mode="K_TO_C"
        elif units and any(x in units.lower() for x in ["celsius","degree_c","degc"," c"]):unit_mode="C"
        elif 150<med<350:unit_mode="K_TO_C_INFERRED_FROM_VALUE_RANGE"
        elif -80<med<80:unit_mode="C_INFERRED_FROM_VALUE_RANGE"
        else:raise RuntimeError("UNKNOWN_TASMAX_UNIT_MEDIAN_"+str(med)+"_UNIT_"+str(units))
        def to_c(a):
            return a-273.15 if unit_mode.startswith("K_TO_C") else a
        sample_values=[]
        for r in stations:
            lon=float(r["longitude"]);lat=float(r["latitude"])
            vals=next(ds.sample([(lon,lat)],indexes=list(range(1,13)),masked=True))
            vals=np.asarray(vals.filled(np.nan),dtype=float)
            vals=to_c(vals)
            winter=mean_or_none([vals[11],vals[0],vals[1]])
            summer=mean_or_none([vals[5],vals[6],vals[7],vals[8]])
            obs_w=finite(r["winter_tmax_monthly_mean_c"]);obs_s=finite(r["summer_tmax_monthly_mean_c"])
            if winter is not None and obs_w is not None:
                station_comparisons["winter_abs_errors"].append(abs(winter-obs_w))
                station_comparisons["winter_bias"].append(winter-obs_w)
            if summer is not None and obs_s is not None:
                station_comparisons["summer_abs_errors"].append(abs(summer-obs_s))
                station_comparisons["summer_bias"].append(summer-obs_s)
        for key in ["winter_abs_errors","summer_abs_errors","winter_bias","summer_bias"]:
            arr=station_comparisons[key]
            station_comparisons[key+"_n"]=len(arr)
            station_comparisons[key+"_mean"]=round(float(np.mean(arr)),3) if arr else None
            station_comparisons[key+"_median"]=round(float(np.median(arr)),3) if arr else None
            station_comparisons[key+"_max"]=round(float(np.max(arr)),3) if arr else None
        station_comparisons["interpretation"]="independent station-vs-grid consistency check only; not a formal calibration or pass/fail threshold"
        summary["station_crosscheck"]=station_comparisons
        summary["raster"]={
          "download":raster_download,"archive":archive_meta,"geotiff_sha256":sha_file(tif),
          "crs":str(ds.crs),"width":ds.width,"height":ds.height,"bands":ds.count,
          "dtype":list(ds.dtypes),"nodata":ds.nodata,"bounds":list(ds.bounds),
          "transform":list(ds.transform),"pixel_size_degrees":[abs(ds.transform.a),abs(ds.transform.e)],
          "band_units":list(ds.units) if ds.units else None,"dataset_tags":tags,"band1_tags":band_tags,
          "sample_probe":{"valid_sample_cells":int(probe_valid.size),"sample_min_raw":float(np.min(probe_valid)),
            "sample_max_raw":float(np.max(probe_valid)),"sample_median_raw":med,"unit_interpretation":unit_mode}
        }
        # Build a full 2847-row register. Missing polygons remain in the table as pending.
        month_names=["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]
        fields=["candidate_code","candidate_name","source_class","asof","geometry_match_status",
          "geometry_source","geometry_vintage_verified","official_2026_code_verified",
          "grid_variable","grid_period","grid_resolution_deg","grid_cells_mean_per_month",
          "grid_cells_min_month","grid_valid_fraction_mean","tasmax_winter_dec_feb_mean_c",
          "tasmax_summer_jun_sep_mean_c","tasmax_annual_monthly_mean_c",
          "tasmax_winter_spatial_p10_mean_c","tasmax_winter_spatial_p90_mean_c",
          "tasmax_summer_spatial_p10_mean_c","tasmax_summer_spatial_p90_mean_c",
          "tasmax_summer_spatial_p90_minus_p10_c","winter_ideal_status","summer_ideal_status",
          "R1_grid_status","prior_R1_point_evidence_present","residential_microclimate_verified"]
        for m in month_names:
            fields.extend([f"tasmax_{m}_mean_c",f"tasmax_{m}_spatial_p10_c",f"tasmax_{m}_spatial_p90_c",f"tasmax_{m}_valid_cells"])
        monthly_means={};monthly_p10={};monthly_p90={};monthly_counts={}
        completed=0;no_cells=0;repaired=0;total_inside=0;total_valid=0
        with OUTCSV.open("w",encoding="utf-8-sig",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
            for i,r in enumerate(roster,1):
                code=r["code"];name=r["name"]
                row={k:"" for k in fields}
                row.update({"candidate_code":code,"candidate_name":name,"source_class":r.get("source_class",""),
                  "asof":r.get("asof",""),"geometry_source":"GeoCode-Release third-party coded GeoJSON",
                  "geometry_vintage_verified":"False","official_2026_code_verified":"False",
                  "grid_variable":"tasmax_monthly_mean_daily_max","grid_period":"1991-2020",
                  "grid_resolution_deg":ds.transform.a,"prior_R1_point_evidence_present":str(code in existing_r1),
                  "residential_microclimate_verified":"False"})
                if code not in geo or geo[code]["name"]!=name or not geo[code]["geometry"]:
                    row["geometry_match_status"]="NO_MATCH_GEOMETRY_PENDING"
                    row["R1_grid_status"]="NO_GEOMETRY_PENDING"
                    writer.writerow(row)
                    continue
                row["geometry_match_status"]="EXACT_CODE_NAME_MATCH_PROVISIONAL"
                geom=shape(geo[code]["geometry"])
                if not geom.is_valid:
                    geom=geom.buffer(0);repaired+=1
                if geom.is_empty or not geom.is_valid:
                    row["R1_grid_status"]="INVALID_GEOMETRY_PENDING"
                    writer.writerow(row);continue
                try:
                    window=geometry_window(ds,[mapping(geom)])
                    h=int(window.height);w=int(window.width)
                    if h<=0 or w<=0:raise ValueError("EMPTY_WINDOW")
                    inside=geometry_mask([mapping(geom)],out_shape=(h,w),transform=ds.window_transform(window),invert=True,all_touched=False)
                    inside_count=int(inside.sum())
                    if inside_count==0:raise ValueError("NO_PIXEL_CENTERS_INSIDE_POLYGON")
                except Exception:
                    row["R1_grid_status"]="NO_GRID_CELLS_PENDING"
                    no_cells+=1;writer.writerow(row);continue
                means=[];p10s=[];p90s=[];counts=[];valid_fractions=[]
                for b in range(1,13):
                    masked=ds.read(b,window=window,masked=True)
                    arr=np.asarray(masked.filled(np.nan),dtype=np.float64)
                    arr=to_c(arr)
                    valid=inside & np.isfinite(arr) & (arr>-1e20) & (arr<1e20)
                    vals=arr[valid]
                    if vals.size:
                        means.append(float(np.mean(vals)))
                        p10s.append(float(np.percentile(vals,10)))
                        p90s.append(float(np.percentile(vals,90)))
                    else:
                        means.append(None);p10s.append(None);p90s.append(None)
                    counts.append(int(vals.size));valid_fractions.append(float(vals.size/inside_count))
                    row[f"tasmax_{month_names[b-1]}_mean_c"]=round(means[-1],3) if means[-1] is not None else ""
                    row[f"tasmax_{month_names[b-1]}_spatial_p10_c"]=round(p10s[-1],3) if p10s[-1] is not None else ""
                    row[f"tasmax_{month_names[b-1]}_spatial_p90_c"]=round(p90s[-1],3) if p90s[-1] is not None else ""
                    row[f"tasmax_{month_names[b-1]}_valid_cells"]=counts[-1]
                winter=mean_or_none([means[11],means[0],means[1]])
                summer=mean_or_none([means[5],means[6],means[7],means[8]])
                annual=mean_or_none(means)
                winter10=mean_or_none([p10s[11],p10s[0],p10s[1]])
                winter90=mean_or_none([p90s[11],p90s[0],p90s[1]])
                summer10=mean_or_none([p10s[5],p10s[6],p10s[7],p10s[8]])
                summer90=mean_or_none([p90s[5],p90s[6],p90s[7],p90s[8]])
                complete=sum(x is not None for x in means)==12
                row.update({"grid_cells_mean_per_month":round(float(np.mean(counts)),1),
                  "grid_cells_min_month":min(counts),"grid_valid_fraction_mean":round(float(np.mean(valid_fractions)),4),
                  "tasmax_winter_dec_feb_mean_c":round(winter,3) if winter is not None else "",
                  "tasmax_summer_jun_sep_mean_c":round(summer,3) if summer is not None else "",
                  "tasmax_annual_monthly_mean_c":round(annual,3) if annual is not None else "",
                  "tasmax_winter_spatial_p10_mean_c":round(winter10,3) if winter10 is not None else "",
                  "tasmax_winter_spatial_p90_mean_c":round(winter90,3) if winter90 is not None else "",
                  "tasmax_summer_spatial_p10_mean_c":round(summer10,3) if summer10 is not None else "",
                  "tasmax_summer_spatial_p90_mean_c":round(summer90,3) if summer90 is not None else "",
                  "tasmax_summer_spatial_p90_minus_p10_c":round(summer90-summer10,3) if summer90 is not None and summer10 is not None else "",
                  "winter_ideal_status":status_for(winter,18,25),
                  "summer_ideal_status":status_for(summer,25,29),
                  "R1_grid_status":"MONTHLY_TASMAX_PARTIAL_NOT_FULL_R1_SCREEN" if complete else "PARTIAL_MONTHLY_BANDS_PENDING",
                  "residential_microclimate_verified":"False"})
                writer.writerow(row);completed+=1
                total_inside+=inside_count;total_valid+=sum(counts)
                if complete:
                    monthly_means[code]=means;monthly_p10[code]=p10s;monthly_p90[code]=p90s;monthly_counts[code]=counts
                if i%50==0 or i==len(roster):
                    f.flush()
                    write_json(PROGRESS,{"run_id":run_id,"status":"RUNNING","processed_roster_rows":i,
                      "matched_geometry_counties_with_stats":completed,"missing_geometry":len(missing),
                      "no_grid_cells_or_invalid_geometry":no_cells,"updated_at_utc":now()})
        summary["zonal_stats_counties"]=completed
        summary["complete_12_month_grid_counties"]=len(monthly_means)
        summary["new_grid_counties_without_prior_R1_point_evidence"]=sum(1 for c in monthly_means if c not in existing_r1)
        summary["geometry_repaired_counties"]=repaired
        summary["no_grid_cells_or_invalid_geometry_counties"]=no_cells
        summary["mean_polygon_pixel_centers_inside"]=round(total_inside/max(completed,1),1)
        summary["mean_valid_pixel_cells_per_county_month"]=round(total_valid/max(completed*12,1),1)
        summary["winter_ideal_counts"]=sum(1 for c in monthly_means if status_for(mean_or_none([monthly_means[c][11],monthly_means[c][0],monthly_means[c][1]]),18,25)=="WITHIN_IDEAL_TARGET")
        summary["summer_ideal_counts"]=sum(1 for c in monthly_means if status_for(mean_or_none([monthly_means[c][5],monthly_means[c][6],monthly_means[c][7],monthly_means[c][8]]),25,29)=="WITHIN_IDEAL_TARGET")
        summary["formal_valid_county_screenings"]=0
        summary["confirmed_county_exclusions"]=0
        summary["carry_forward_counties"]=2847
        summary["status"]="PASS_WITH_PROVISIONAL_1KM_TASMAX_ZONAL_DELTA" if len(monthly_means)>=2500 else "PARTIAL_GRID_ZONAL_DELTA"
        summary["completed_at_utc"]=now()
        summary["output_csv"]=str(OUTCSV)
        summary["output_csv_sha256"]=sha_file(OUTCSV)
        summary["progress"]={"exact_geometry_matches":len(exact),"county_rows_written":2847,
          "zonal_stats_counties":completed,"complete_12_month_counties":len(monthly_means)}
        write_json(OUTJSON,summary)
        write_json(PROGRESS,{"run_id":run_id,"status":summary["status"],"processed_roster_rows":2847,
          "matched_geometry_counties_with_stats":completed,"complete_12_month_grid_counties":len(monthly_means),
          "updated_at_utc":now()})
        print(json.dumps({"status":summary["status"],"input_counties":2847,"exact_geometry_matches":2838,
          "zonal_stats_counties":completed,"complete_12_month_grid_counties":len(monthly_means),
          "new_without_prior_R1":summary["new_grid_counties_without_prior_R1_point_evidence"],
          "formal_valid_county_screenings":0,"confirmed_exclusions":0,
          "station_crosscheck":station_comparisons},ensure_ascii=False))
if __name__=="__main__":
    try:main()
    except Exception as e:
        err={"schema":"RET_SCIDB_TASMAX_1KM_NATIONAL_ZONAL_EVIDENCE_V1","run_id":os.getenv("GITHUB_RUN_ID","MANUAL"),
          "action_id":ACTION_ID,"started_at_utc":now(),"status":"FAILED_OR_BLOCKED",
          "error_type":type(e).__name__,"error":str(e)[:3000],
          "formal_valid_county_screenings":0,"confirmed_county_exclusions":0,"carry_forward_counties":2847}
        try:write_json(OUTJSON,err)
        except Exception:pass
        try:
            if not OUTCSV.exists():
                _,fallback_rows=parse_csv(ROSTER)
                with OUTCSV.open("w",encoding="utf-8-sig",newline="") as f:
                    cols=["candidate_code","candidate_name","geometry_match_status","R1_grid_status","official_2026_code_verified","formal_valid_county_screening","county_exclusion"]
                    w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
                    for row in fallback_rows:
                        w.writerow({"candidate_code":row.get("code",""),"candidate_name":row.get("name",""),
                          "geometry_match_status":"NOT_COMPUTED","R1_grid_status":"NO_VERIFIED_GRID_RESULT",
                          "official_2026_code_verified":"False","formal_valid_county_screening":"False","county_exclusion":"False"})
        except Exception:pass
        print(json.dumps(err,ensure_ascii=False))
        sys.exit(2)
