#!/usr/bin/env python3
"""R4 environmental-health first pass for exactly the 236 current funnel survivors.

This run performs a 1-km, population-weighted PM2.5/O3 historical exposure screen
(2000-2025) and joins already verified local air/water/industrial/geohazard
evidence. It is NOT a final residential-site assessment and never excludes a
candidate or changes a formal grade. Missing geometry/evidence remains pending.
"""
from __future__ import annotations
import collections, csv, datetime as dt, hashlib, json, math, os, pathlib, re, time, urllib.request
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from shapely.geometry import shape, mapping
from netCDF4 import Dataset

ROOT = pathlib.Path("research_engine/retirement")
FUNNEL = ROOT / "national_funnel"
BASE = FUNNEL / "R4_ENVIRONMENT_236"
CACHE = BASE / "cache"
OUT = BASE / "output"
FINAL_DIR = FUNNEL / "FINAL_FILTER" / "runs" / "42453646573"
CANDIDATES = FINAL_DIR / "FINAL_CARRY_FORWARD_AFTER_R1_R2_R3.csv"
STAGE_SUMMARY = FINAL_DIR / "FINAL_STAGE1_3_SUMMARY.json"
GEOMETRY_URL = "https://raw.githubusercontent.com/zzhonglei/GeoCode-Release/main/contributions/china-admin-boundaries/skill/data/china_county.geojson"
GEOMETRY_SHA256 = "22db6c54b9cb0118ecdcc8a117bf2da4fc24a2229cdba7e6e55dbb5dd56e8246"
POP_URL = "https://data.worldpop.org/GIS/Population/Global_2015_2030/R2024B/2024/0_Mosaicked/v1/1km/unconstrained/global_pop_2024_UC_1km_R2024B_v1.tif"
POP_FILE = "global_pop_2024_UC_1km_R2024B_v1.tif"
PM_OLD_RECORD = 6398971
PM_NEW_RECORD = 21770406
O3_RECORD = 21811088
YEARS = list(range(2000, 2026))
NOW = lambda: dt.datetime.now(dt.timezone.utc).isoformat()

def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def download(url, dest, expected_md5=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if expected_md5 is None or md5_file(dest).lower() == expected_md5.lower():
            return {"status":"REUSED_CACHE","bytes":dest.stat().st_size,"md5":md5_file(dest),"sha256":sha_file(dest),"url":url}
        dest.unlink()
    part = dest.with_suffix(dest.suffix + ".part")
    part.unlink(missing_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent":"Retirement-R4-236-CHAP/1.0","Accept":"*/*"})
    last = None
    for attempt in range(1,4):
        try:
            with urllib.request.urlopen(req, timeout=180) as response, part.open("wb") as f:
                total = response.headers.get("Content-Length")
                copied = 0
                while True:
                    b = response.read(4 * 1024 * 1024)
                    if not b: break
                    f.write(b); copied += len(b)
                    if copied and copied % (16 * 1024 * 1024) < len(b):
                        print("DOWNLOAD_PROGRESS", dest.name, copied, total or "unknown", flush=True)
            actual_md5 = md5_file(part)
            if expected_md5 and actual_md5.lower() != expected_md5.lower():
                raise RuntimeError("MD5_MISMATCH expected="+expected_md5+" got="+actual_md5)
            part.replace(dest)
            return {"status":"DOWNLOADED","bytes":dest.stat().st_size,"md5":actual_md5,"sha256":sha_file(dest),"url":url,"attempt":attempt}
        except Exception as e:
            last = repr(e)
            part.unlink(missing_ok=True)
            print("DOWNLOAD_RETRY",dest.name,attempt,last,flush=True)
            if attempt < 3: time.sleep(attempt * 4)
    raise RuntimeError("DOWNLOAD_FAILED "+dest.name+" "+str(last))

def zenodo_record_files(record_id):
    url = "https://zenodo.org/api/records/" + str(record_id)
    req = urllib.request.Request(url, headers={"User-Agent":"Retirement-R4-236-CHAP/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        payload = json.loads(r.read().decode("utf-8"))
    out = {}
    for item in payload.get("files", []):
        key = item.get("key")
        checksum = str(item.get("checksum") or "")
        md5 = checksum.split(":")[-1] if ":" in checksum else None
        links = item.get("links") or {}
        file_url = links.get("content") or links.get("download") or links.get("self")
        if not file_url and key:
            file_url = "https://zenodo.org/records/"+str(record_id)+"/files/"+key+"?download=1"
        if key:
            out[key] = {"url":file_url,"md5":md5,"size":item.get("size"),"checksum":checksum}
    return payload, out

def get_chap_file(kind, year, records):
    if kind == "PM25":
        record_id = PM_OLD_RECORD if year <= 2021 else PM_NEW_RECORD
        version = "V4"
        name = "CHAP_PM2.5_Y1K_"+str(year)+"_"+version+".nc"
    else:
        record_id = O3_RECORD
        version = "V3"
        name = "CHAP_O3_Y1K_"+str(year)+"_"+version+".nc"
    if record_id not in records:
        meta, files = zenodo_record_files(record_id)
        records[record_id] = {"metadata":{"id":record_id,"doi":meta.get("doi"),"title":meta.get("metadata",{}).get("title")},"files":files}
    f = records[record_id]["files"].get(name)
    if not f:
        raise RuntimeError("CHAP_ANNUAL_FILE_NOT_FOUND "+str(record_id)+" "+name)
    if not f.get("md5"):
        raise RuntimeError("CHAP_FILE_MD5_MISSING "+name)
    dest = CACHE / "chap" / kind / name
    info = download(f["url"], dest, f["md5"])
    info.update({"record_id":record_id,"file_name":name,"expected_size":f.get("size"),"expected_md5":f["md5"]})
    return dest, info

def find_coord(ds, options):
    for name in options:
        if name in ds.variables:
            v = ds.variables[name]
            if v.ndim == 1:
                return name, np.asarray(v[:], dtype="float64")
    raise RuntimeError("NETCDF_COORD_NOT_FOUND "+str(options)+" variables="+str(list(ds.variables.keys())[:30]))

def read_chap_grid(path, pollutant):
    with Dataset(str(path), "r") as ds:
        lat_name, lat = find_coord(ds, ["lat","latitude","Latitude","y"])
        lon_name, lon = find_coord(ds, ["lon","longitude","Longitude","x"])
        candidates = []
        for name, var in ds.variables.items():
            if name in (lat_name,lon_name): continue
            if var.ndim >= 2 and lat_name in var.dimensions and lon_name in var.dimensions:
                candidates.append((name,var))
        if not candidates:
            raise RuntimeError("NETCDF_DATA_VARIABLE_NOT_FOUND "+str(list(ds.variables.keys())[:40]))
        tokens = ["pm2.5","pm25","chap_pm"] if pollutant == "PM25" else ["o3","ozone"]
        chosen = None
        for name,var in candidates:
            low = name.lower()
            if any(t in low for t in tokens):
                chosen = (name,var); break
        if chosen is None:
            chosen = candidates[0]
        var_name, var = chosen
        raw = var[:]
        if np.ma.isMaskedArray(raw):
            arr = np.asarray(raw.astype("float32").filled(np.nan), dtype="float32")
        else:
            arr = np.asarray(raw, dtype="float32")
        arr = np.squeeze(arr)
        if arr.ndim != 2:
            raise RuntimeError("NETCDF_EXPECTED_2D_AFTER_SQUEEZE "+var_name+" "+str(arr.shape))
        if arr.shape == (len(lon),len(lat)):
            arr = arr.T
        if arr.shape != (len(lat),len(lon)):
            raise RuntimeError("NETCDF_GRID_SHAPE_MISMATCH "+var_name+" "+str(arr.shape)+" coords="+str((len(lat),len(lon))))
        # Normalize to north-up rows and west-east columns.
        if len(lat) < 2 or len(lon) < 2:
            raise RuntimeError("NETCDF_GRID_TOO_SMALL")
        dlat = float(np.median(np.diff(lat)))
        dlon = float(np.median(np.diff(lon)))
        if not np.isfinite(dlat) or not np.isfinite(dlon) or abs(dlat) < 1e-8 or abs(dlon) < 1e-8:
            raise RuntimeError("NETCDF_GRID_RESOLUTION_INVALID")
        if dlat > 0:
            lat = lat[::-1]
            arr = arr[::-1,:]
        if dlon < 0:
            lon = lon[::-1]
            arr = arr[:,::-1]
        dy = abs(dlat); dx = abs(dlon)
        left = float(lon[0] - dx/2.0)
        top = float(lat[0] + dy/2.0)
        transform = Affine(dx,0,left,0,-dy,top)
        # Mask fill values and physically impossible retrieval values.
        upper = 600.0 if pollutant == "PM25" else 800.0
        arr[(~np.isfinite(arr)) | (arr < 0) | (arr > upper)] = np.nan
        meta = {
            "variable":var_name,"lat_variable":lat_name,"lon_variable":lon_name,
            "shape":[int(arr.shape[0]),int(arr.shape[1])],
            "lat_min":float(np.nanmin(lat)),"lat_max":float(np.nanmax(lat)),
            "lon_min":float(np.nanmin(lon)),"lon_max":float(np.nanmax(lon)),
            "resolution_degrees":[dx,dy],"transform":list(transform),
            "units":getattr(var,"units","") or "not_declared"
        }
        return arr, transform, meta

def build_population_grid(pop_path, transform, height, width):
    out = np.zeros((height,width), dtype="float32")
    with rasterio.open(pop_path) as src:
        reproject(
            source=rasterio.band(src,1), destination=out,
            src_transform=src.transform, src_crs=src.crs,
            src_nodata=src.nodata, dst_transform=transform,
            dst_crs="EPSG:4326", dst_nodata=0,
            resampling=Resampling.average, init_dest_nodata=True, num_threads=2
        )
    out[~np.isfinite(out)] = 0
    out[out < 0] = 0
    if float(out.sum()) <= 0:
        raise RuntimeError("CHAP_POPULATION_REPROJECTED_SUM_ZERO")
    return out

def build_region(code, name, geometry, transform, height, width, pop_grid):
    dx = transform.a
    dy = -transform.e
    left = transform.c
    top = transform.f
    minx,miny,maxx,maxy = geometry.bounds
    c0 = max(0, int(math.floor((minx-left)/dx)))
    c1 = min(width, int(math.ceil((maxx-left)/dx)))
    r0 = max(0, int(math.floor((top-maxy)/dy)))
    r1 = min(height, int(math.ceil((top-miny)/dy)))
    if c1 <= c0 or r1 <= r0:
        return None
    win_transform = Affine(dx,0,left+c0*dx,0,-dy,top-r0*dy)
    inside = geometry_mask([mapping(geometry)], out_shape=(r1-r0,c1-c0), transform=win_transform, invert=True, all_touched=False)
    weights = pop_grid[r0:r1,c0:c1].copy()
    base = inside & np.isfinite(weights) & (weights > 0)
    if not np.any(base):
        return None
    return {"code":code,"name":name,"r0":r0,"r1":r1,"c0":c0,"c1":c1,"inside":inside,"weights":weights,"base":base,
            "inhabited_cells":int(np.count_nonzero(base)),"population_weight_sum":float(weights[base].sum())}

def weighted_quantile(values, weights, q):
    if len(values)==0 or len(weights)==0: return None
    order=np.argsort(values)
    v=values[order]; w=weights[order]
    total=float(w.sum())
    if total<=0: return None
    c=np.cumsum(w)
    return float(np.interp(q*total,c,v))

def annual_region_stats(arr, region):
    a = arr[region["r0"]:region["r1"],region["c0"]:region["c1"]]
    valid = region["base"] & np.isfinite(a)
    if not np.any(valid): return None, 0.0
    w = region["weights"][valid]
    vals = a[valid]
    total = float(region["weights"][region["base"]].sum())
    coverage = float(w.sum()/total) if total else 0.0
    return float(np.sum(vals*w)/np.sum(w)), coverage

def longterm_region_stats(arr, region, thresholds=None):
    a = arr[region["r0"]:region["r1"],region["c0"]:region["c1"]]
    valid = region["base"] & np.isfinite(a)
    if not np.any(valid): return {}
    vals = a[valid]
    weights = region["weights"][valid]
    result = {
        "p10":weighted_quantile(vals,weights,0.10),
        "p50":weighted_quantile(vals,weights,0.50),
        "p90":weighted_quantile(vals,weights,0.90),
        "valid_population_weight_coverage":float(weights.sum()/region["weights"][region["base"]].sum())
    }
    if thresholds:
        for t in thresholds:
            result["population_share_gt_"+str(t).replace(".","_")] = float(weights[vals>t].sum()/weights.sum())
    return result

def read_candidate_set():
    if not CANDIDATES.exists() or not STAGE_SUMMARY.exists():
        raise RuntimeError("CURRENT_R1_R2_R3_CANONICAL_INPUT_MISSING")
    summary = read_json(STAGE_SUMMARY)
    if summary.get("status") != "COMPLETED_WITH_PENDING" or summary.get("final_count_after_three_climate_batches") != 236:
        raise RuntimeError("CURRENT_FUNNEL_SUMMARY_NOT_236")
    with CANDIDATES.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=236 or len({str(r["code"]).zfill(6) for r in rows})!=236:
        raise RuntimeError("CURRENT_FUNNEL_CANDIDATES_NOT_UNIQUE_236")
    for r in rows:
        r["code"]=str(r["code"]).zfill(6)
    carry=sum(r["R1_next_round_status"]=="CARRY_FORWARD" for r in rows)
    r1_pending=sum(r["R1_next_round_status"]=="PENDING_CONTINUE" for r in rows)
    climate_pending=sum(r["winter_status"]=="PENDING" or r["summer_status"]=="PENDING" for r in rows)
    r1_only=r1_pending-climate_pending
    if (carry,r1_pending,climate_pending,r1_only)!=(178,58,11,47):
        raise RuntimeError("236_PENDING_SPLIT_CHANGED "+str((carry,r1_pending,climate_pending,r1_only)))
    if any((r["winter_status"]=="PENDING" or r["summer_status"]=="PENDING") and r["R1_next_round_status"]!="PENDING_CONTINUE" for r in rows):
        raise RuntimeError("CLIMATE_PENDING_NOT_SUBSET_OF_R1_PENDING")
    return rows, summary, {"input_count":236,"R1_clear_carry_forward":carry,"R1_only_pending":r1_only,"R2_R3_climate_data_pending":climate_pending,"R1_total_pending":r1_pending}

def load_geometry():
    r1p=FUNNEL/"R1"/"cache"/"china_county.geojson"
    p=r1p if r1p.exists() and sha_file(r1p)==GEOMETRY_SHA256 else CACHE/"china_county.geojson"
    if not p.exists() or sha_file(p)!=GEOMETRY_SHA256:
        download(GEOMETRY_URL,p)
    if sha_file(p)!=GEOMETRY_SHA256:
        raise RuntimeError("GEOMETRY_SHA256_MISMATCH")
    doc=json.loads(p.read_text(encoding="utf-8"))
    geo={}
    for feat in doc.get("features",[]):
        props=feat.get("properties") or {}
        code=str(props.get("adcode") or "")
        name=str(props.get("name") or "")
        if len(code)==6 and code.isdigit() and feat.get("geometry"):
            if code in geo: raise RuntimeError("DUPLICATE_GEOMETRY_CODE "+code)
            geo[code]={"name":name,"geometry":shape(feat["geometry"])}
    return geo

def load_population_raster():
    r1p=FUNNEL/"R1"/"cache"/POP_FILE
    p=r1p if r1p.exists() and r1p.stat().st_size >= 100_000_000 else CACHE/POP_FILE
    if not p.exists() or p.stat().st_size < 100_000_000:
        download(POP_URL,p)
    return p

def collect_environment_context(rows):
    bycode={r["code"]:{} for r in rows}
    sources={}
    # Direct 2025 Fujian county air values (not dwelling-level monitoring).
    p=ROOT/"status/Fujian2025_official_R4_county_air_evidence.json"
    if p.exists():
        d=read_json(p); sources["Fujian_2025_county_air"]=d.get("source_url")
        for x in d.get("county_source_records",[]):
            code=str(x.get("candidate_code") or "")
            if code in bycode:
                bycode[code].update({"Fujian_2025_county_PM25_ugm3":x.get("PM25_annual_ugm3"),
                    "Fujian_2025_county_good_air_days_pct":x.get("good_air_days_pct"),
                    "Fujian_2025_county_primary_pollutant":x.get("primary_pollutant_name"),
                    "Fujian_2025_county_air_scope":"OFFICIAL_COUNTY_ANNUAL_NOT_RESIDENTIAL"})
    # 2024-2025 Fujian county PM2.5 trends and city-level ozone context.
    p=ROOT/"status/Fujian2024_2025_air_pollution_two_year_evidence.json"
    if p.exists():
        d=read_json(p); sources["Fujian_2024_2025_air"]=d.get("source_publication_urls")
        for x in d.get("county_twoyear_records",[]):
            code=str(x.get("code") or "")
            if code in bycode:
                bycode[code].update({"Fujian_PM25_2024_ugm3":x.get("PM25_2024"),
                    "Fujian_PM25_2025_ugm3":x.get("PM25_2025"),
                    "Fujian_PM25_change_2025_minus_2024":x.get("PM25_change_2025_minus_2024"),
                    "Fujian_county_air_two_year_scope":"OFFICIAL_COUNTY_ANNUAL_NOT_RESIDENTIAL"})
    # 109 official Fujian raw-water intakes: source-water evidence only.
    p=ROOT/"status/Fujian2025_12_R5_official_raw_water_source_evidence.json"
    if p.exists():
        d=read_json(p); sources["Fujian_2025_12_raw_water"]=d.get("source_URL")
        grouped=collections.defaultdict(list)
        for x in d.get("Fujian_2025_12_source_intakes",[]):
            code=str(x.get("candidate_code") or "")
            if code in bycode: grouped[code].append(x)
        for code,items in grouped.items():
            bycode[code].update({"Fujian_2025_12_raw_water_intake_count":len(items),
                "Fujian_2025_12_raw_water_all_listed_classIII":all(bool(x.get("raw_water_met_classIII_standard")) for x in items),
                "Fujian_2025_12_raw_water_site_names":"；".join(x.get("intake_source_name","") for x in items),
                "Fujian_2025_12_raw_water_scope":"UNTREATED_SOURCE_WATER_NOT_TAP_WATER"})
    # Four validated 2025 tap/finished-water public samples, if any fall inside the 236.
    p=ROOT/"status/R5_2025_crossprovince_7counties_finished_tap_plant_source_evidence.json"
    if p.exists():
        d=read_json(p); sources["cross_province_tap_samples"]="R5_2025_crossprovince_7counties_finished_tap_plant_source_evidence.json"
        for x in d.get("source_records",[]):
            code=str(x.get("county_code") or "")
            if code in bycode and x.get("source_quality")=="HTTP_REAL_AND_TEXT_VERIFIED":
                bycode[code].update({"tap_water_source_scope":x.get("sample_scope"),
                    "tap_water_sample_count":x.get("reported_sample_count"),
                    "tap_water_sample_period":x.get("quarter"),
                    "tap_water_source_url":x.get("source_url"),
                    "tap_water_scope_warning":"SINGLE_PERIOD_NAMED_SAMPLES_NOT_WHOLE_COUNTY"})
    # Targeted public environmental context already retrieved for Mengzi and Panzhihua East.
    p=ROOT/"evidence/stage3_firstbatch_public_environment_evidence_20261107.json"
    if p.exists():
        d=read_json(p); sources["targeted_industrial_hazard_context"]="stage3_firstbatch_public_environment_evidence_20261107.json"
        for x in d.get("units",[]):
            code=str(x.get("candidate_code_unverified") or "")
            if code in bycode:
                bycode[code].update({"targeted_public_environment_case_status":x.get("status"),
                    "targeted_public_environment_case_detail":json.dumps(x,ensure_ascii=False,separators=(",",":")),
                    "targeted_public_environment_case_scope":"PUBLIC_CONTEXT_REQUIRES_RESIDENTIAL_COORDINATE_OVERLAY"})
    # Mengzi 16 published tap observations: retain as a provisional candidate link, not a county certification.
    p=ROOT/"evidence/stage3_mengzi_2026_tapwater_16_site_observations_v1.json"
    if p.exists() and "532503" in bycode:
        d=read_json(p); s=d.get("summary",{})
        bycode["532503"].update({"Mengzi_2026_tap_observations":s.get("records"),
            "Mengzi_2026_tap_sites":s.get("monitored_sites"),
            "Mengzi_2026_tap_reported_listed_limits_pass":s.get("observed_pass_listed_limits"),
            "Mengzi_2026_tap_scope":"PROVISIONAL_MENGZI_LINK_NOT_WHOLE_CITY_OR_HOUSEHOLD_CERTIFICATION",
            "Mengzi_2026_tap_source_urls":"；".join(x.get("url","") for x in d.get("source_metadata",[]))})
    return bycode, sources

def main():
    CACHE.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    started=NOW()
    rows, stage_summary, split = read_candidate_set()
    geo=load_geometry()
    exact=[]; pending_geometry=[]
    for r in rows:
        g=geo.get(r["code"])
        if g and g["name"]==r["name"]:
            exact.append((r,g["geometry"]))
        else:
            pending_geometry.append(r["code"])
    if len(exact)!=227 or len(pending_geometry)!=9:
        raise RuntimeError("CURRENT_236_GEOMETRY_SPLIT_CHANGED "+str((len(exact),len(pending_geometry))))
    pop_path=load_population_raster()

    records={}
    source_meta={}
    pm_arrays={}; o3_arrays={}
    grid_transform=None; grid_shape=None; pop_grid=None
    # Read one annual PM2.5 file to establish the common CHAP grid.
    first_path, first_info=get_chap_file("PM25",2000,records)
    first_arr, transform, grid_meta=read_chap_grid(first_path,"PM25")
    grid_shape=first_arr.shape; grid_transform=transform
    pop_grid=build_population_grid(pop_path,transform,grid_shape[0],grid_shape[1])
    regions={}
    for r,g in exact:
        reg=build_region(r["code"],r["name"],g,transform,grid_shape[0],grid_shape[1],pop_grid)
        if reg: regions[r["code"]]=reg
    if len(regions)!=227:
        raise RuntimeError("INHABITED_GEOMETRY_REGIONS_EXPECTED_227_GOT_"+str(len(regions)))
    print("R4_236_INPUT_LOCK",json.dumps(split,ensure_ascii=False),flush=True)
    print("R4_236_GEOMETRY exact=227 pending=9 CHAP_GRID="+str(grid_shape),flush=True)
    sum_pm=np.zeros(grid_shape,dtype="float32"); count_pm=np.zeros(grid_shape,dtype="uint8")
    sum_o3=np.zeros(grid_shape,dtype="float32"); count_o3=np.zeros(grid_shape,dtype="uint8")
    annual={r["code"]:{"PM25":{},"O3":{},"PM25_coverage":{},"O3_coverage":{}} for r in rows}
    file_audit=[]

    for year in YEARS:
        pth, info = (first_path, first_info) if year==2000 else get_chap_file("PM25",year,records)
        arr, tr, meta=read_chap_grid(pth,"PM25")
        if arr.shape!=grid_shape or list(tr)!=list(grid_transform):
            raise RuntimeError("PM25_GRID_CHANGED_"+str(year))
        valid=np.isfinite(arr)
        sum_pm[valid]+=arr[valid]; count_pm[valid]+=1
        for code,reg in regions.items():
            value,cov=annual_region_stats(arr,reg)
            annual[code]["PM25"][year]=value
            annual[code]["PM25_coverage"][year]=cov
        file_audit.append(info)
        print("R4_PM25_YEAR_DONE",year,"valid_cells",int(valid.sum()),flush=True)
        del arr

    for year in YEARS:
        pth, info=get_chap_file("O3",year,records)
        arr, tr, meta=read_chap_grid(pth,"O3")
        if arr.shape!=grid_shape or list(tr)!=list(grid_transform):
            raise RuntimeError("O3_GRID_CHANGED_"+str(year))
        valid=np.isfinite(arr)
        sum_o3[valid]+=arr[valid]; count_o3[valid]+=1
        for code,reg in regions.items():
            value,cov=annual_region_stats(arr,reg)
            annual[code]["O3"][year]=value
            annual[code]["O3_coverage"][year]=cov
        file_audit.append(info)
        print("R4_O3_YEAR_DONE",year,"valid_cells",int(valid.sum()),flush=True)
        del arr

    pm_long=np.full(grid_shape,np.nan,dtype="float32")
    o3_long=np.full(grid_shape,np.nan,dtype="float32")
    m=count_pm>0; pm_long[m]=sum_pm[m]/count_pm[m]
    m=count_o3>0; o3_long[m]=sum_o3[m]/count_o3[m]
    context, context_sources=collect_environment_context(rows)
    output_rows=[]
    for r in rows:
        code=r["code"]; reg=regions.get(code)
        row={
            "code":code,"name":r["name"],"R1_next_round_status":r["R1_next_round_status"],
            "winter_status":r["winter_status"],"summer_status":r["summer_status"],
            "sunshine_status":r["sunshine_status"],"altitude_status":r["altitude_status"],
            "geometry_status":"EXACT_CODE_NAME_MATCH_PROVISIONAL" if code in regions else "PENDING_GEOMETRY_OR_NAME",
            "air_data_status":"COMPUTED_POPULATION_WEIGHTED_1KM_PROXY" if reg else "PENDING_GEOMETRY_NO_EXCLUSION",
            "inhabited_1km_cells":reg["inhabited_cells"] if reg else "",
            "worldpop_2024_relative_weight_sum":reg["population_weight_sum"] if reg else "",
            "PM25_2000_2025_population_weighted_mean":None,
            "PM25_2023_2025_three_year_mean":None,"PM25_2023_2025_gt30_current_transition":None,"PM25_2023_2025_gt25_2031":None,
            "PM25_2000_2025_cell_p10":None,"PM25_2000_2025_cell_p50":None,"PM25_2000_2025_cell_p90":None,
            "PM25_early_2000_2004_mean":None,"PM25_mid_2011_2020_mean":None,"PM25_recent_2021_2025_mean":None,
            "PM25_recent_minus_early":None,"PM25_years_count_candidate_mean_gt30_current_transition":None,"PM25_years_count_candidate_mean_gt25_2031":None,"PM25_years_count_candidate_mean_gt35_legacy":None,
            "PM25_population_share_longterm_cells_gt15":None,"PM25_population_share_longterm_cells_gt25":None,
            "PM25_population_share_longterm_cells_gt30_current_transition":None,"PM25_population_share_longterm_cells_gt35_legacy":None,
            "O3_2000_2025_population_weighted_mean":None,
            "O3_2000_2025_cell_p10":None,"O3_2000_2025_cell_p50":None,"O3_2000_2025_cell_p90":None,
            "O3_early_2000_2004_mean":None,"O3_mid_2011_2020_mean":None,"O3_recent_2021_2025_mean":None,
            "O3_recent_minus_early":None,
            "PM25_population_coverage_mean_annual":None,"O3_population_coverage_mean_annual":None,
            "R4_formal_exclusion":"NO","formal_grade_change":"NO",
            "air_scope_warning":"1km modelled annual pollutant surface weighted by WorldPop 2024 inhabited-grid proxy; not a dwelling monitor, not a legal compliance determination, and not sufficient alone for exclusion"
        }
        for year in YEARS:
            row["PM25_"+str(year)]=annual[code]["PM25"].get(year)
            row["O3_"+str(year)]=annual[code]["O3"].get(year)
        if reg:
            pm_stats=longterm_region_stats(pm_long,reg,[15,25,30,35])
            o3_stats=longterm_region_stats(o3_long,reg)
            pm_vals=[annual[code]["PM25"].get(y) for y in YEARS]
            o3_vals=[annual[code]["O3"].get(y) for y in YEARS]
            def avg(vals, years):
                x=[annual[code]["PM25"].get(y) for y in years] if vals=="PM25" else [annual[code]["O3"].get(y) for y in years]
                x=[v for v in x if v is not None and np.isfinite(v)]
                return float(np.mean(x)) if x else None
            pm_early=avg("PM25",range(2000,2005)); pm_mid=avg("PM25",range(2011,2021)); pm_recent=avg("PM25",range(2021,2026)); pm_3y=avg("PM25",range(2023,2026))
            o3_early=avg("O3",range(2000,2005)); o3_mid=avg("O3",range(2011,2021)); o3_recent=avg("O3",range(2021,2026))
            pm_mean=avg("PM25",YEARS); o3_mean=avg("O3",YEARS)
            row.update({
                "PM25_2000_2025_population_weighted_mean":pm_mean,
                "PM25_2023_2025_three_year_mean":pm_3y,
                "PM25_2023_2025_gt30_current_transition":(pm_3y>30) if pm_3y is not None else None,
                "PM25_2023_2025_gt25_2031":(pm_3y>25) if pm_3y is not None else None,
                "PM25_2000_2025_cell_p10":pm_stats.get("p10"),"PM25_2000_2025_cell_p50":pm_stats.get("p50"),"PM25_2000_2025_cell_p90":pm_stats.get("p90"),
                "PM25_early_2000_2004_mean":pm_early,"PM25_mid_2011_2020_mean":pm_mid,"PM25_recent_2021_2025_mean":pm_recent,
                "PM25_recent_minus_early":(pm_recent-pm_early) if pm_recent is not None and pm_early is not None else None,
                "PM25_years_count_candidate_mean_gt30_current_transition":sum(1 for y in YEARS if annual[code]["PM25"].get(y) is not None and annual[code]["PM25"][y]>30),
                "PM25_years_count_candidate_mean_gt25_2031":sum(1 for y in YEARS if annual[code]["PM25"].get(y) is not None and annual[code]["PM25"][y]>25),
                "PM25_years_count_candidate_mean_gt35_legacy":sum(1 for y in YEARS if annual[code]["PM25"].get(y) is not None and annual[code]["PM25"][y]>35),
                "PM25_population_share_longterm_cells_gt15":pm_stats.get("population_share_gt_15"),
                "PM25_population_share_longterm_cells_gt25":pm_stats.get("population_share_gt_25"),
                "PM25_population_share_longterm_cells_gt30_current_transition":pm_stats.get("population_share_gt_30"),
                "PM25_population_share_longterm_cells_gt35_legacy":pm_stats.get("population_share_gt_35"),
                "O3_2000_2025_population_weighted_mean":o3_mean,
                "O3_2000_2025_cell_p10":o3_stats.get("p10"),"O3_2000_2025_cell_p50":o3_stats.get("p50"),"O3_2000_2025_cell_p90":o3_stats.get("p90"),
                "O3_early_2000_2004_mean":o3_early,"O3_mid_2011_2020_mean":o3_mid,"O3_recent_2021_2025_mean":o3_recent,
                "O3_recent_minus_early":(o3_recent-o3_early) if o3_recent is not None and o3_early is not None else None,
                "PM25_population_coverage_mean_annual":float(np.mean(list(annual[code]["PM25_coverage"].values()))),
                "O3_population_coverage_mean_annual":float(np.mean(list(annual[code]["O3_coverage"].values())))
            })
        row.update(context.get(code,{}))
        output_rows.append(row)

    fields=[]
    for item in output_rows:
        for key in item.keys():
            if key not in fields: fields.append(key)
    air_csv=OUT/"R4_AIR_236_1KM_2000_2025.csv"
    with air_csv.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(output_rows)
    # A compact summary and explicit scope lock are persisted with the same 236-unit denominator.
    pm_computed=[x["PM25_2000_2025_population_weighted_mean"] for x in output_rows if x["PM25_2000_2025_population_weighted_mean"] is not None]
    o3_computed=[x["O3_2000_2025_population_weighted_mean"] for x in output_rows if x["O3_2000_2025_population_weighted_mean"] is not None]
    summary={
        "schema":"RETIREMENT_R4_ENVIRONMENT_236_CHAP_AIR_FIRST_PASS_V1",
        "status":"AIR_QUALITY_1KM_BATCH_COMPLETED_WITH_GEOMETRY_PENDING",
        "created_at_utc":NOW(),"started_at_utc":started,
        "input_count":236,"candidate_input_sha256":sha_file(CANDIDATES),
        "stage1_3_summary_sha256":sha_file(STAGE_SUMMARY),
        "funnel_split":split,"geometry_exact_match_count":len(exact),
        "geometry_pending_count":len(pending_geometry),"geometry_pending_codes":pending_geometry,
        "air_grid_computed_count":sum(1 for x in output_rows if x["air_data_status"]=="COMPUTED_POPULATION_WEIGHTED_1KM_PROXY"),
        "air_grid_pending_count":sum(1 for x in output_rows if x["air_data_status"]!="COMPUTED_POPULATION_WEIGHTED_1KM_PROXY"),
        "pm25_2000_2025_mean_of_candidate_means":{"min":float(np.min(pm_computed)),"median":float(np.median(pm_computed)),"max":float(np.max(pm_computed))} if pm_computed else None,
        "current_standard_GB3095_2026":{"effective_date":"2026-03-01","2026_to_2030_secondary_annual_PM25_limit_ugm3":30,"from_2031_secondary_annual_PM25_limit_ugm3":25,"official_source_url":"https://www.mee.gov.cn/ywdt/zbft/202602/t20260225_1144479.shtml"},
        "PM25_2023_2025_three_year_proxy_screen":{"computed_count":sum(1 for x in output_rows if x.get("PM25_2023_2025_three_year_mean") is not None),"gt30_current_transition_count":sum(1 for x in output_rows if x.get("PM25_2023_2025_three_year_mean") is not None and x["PM25_2023_2025_three_year_mean"]>30),"gt25_2031_count":sum(1 for x in output_rows if x.get("PM25_2023_2025_three_year_mean") is not None and x["PM25_2023_2025_three_year_mean"]>25)},
        "o3_2000_2025_mean_of_candidate_means":{"min":float(np.min(o3_computed)),"median":float(np.median(o3_computed)),"max":float(np.max(o3_computed))} if o3_computed else None,
        "chap_sources":{
            "PM25_2000_2021":{"record_id":PM_OLD_RECORD,"doi":"10.5281/zenodo.6398971","years":"2000-2021","resolution":"1km annual Y1K V4"},
            "PM25_2022_2025":{"record_id":PM_NEW_RECORD,"doi":"10.5281/zenodo.21770406","years":"2022-2025","resolution":"1km annual Y1K V4"},
            "O3_2000_2025":{"record_id":O3_RECORD,"doi":"10.5281/zenodo.21811088","years":"2000-2025","resolution":"1km annual Y1K V3"}
        },
        "chap_grid":grid_meta,
        "population_source":{"name":"WorldPop 2024 unconstrained 1km population grid","url":POP_URL,"sha256":sha_file(pop_path),"role":"current inhabited-cell weight proxy, not an address/building register"},
        "geometry_source":{"url":GEOMETRY_URL,"sha256":GEOMETRY_SHA256,"status":"THIRD_PARTY_PROVISIONAL_CODED_GEOMETRY"},
        "downloaded_chap_files":file_audit,
        "source_context_counts":{
            "Fujian_2025_county_air_records_in_236":sum(1 for x in output_rows if x.get("Fujian_2025_county_PM25_ugm3") not in (None,"")),
            "Fujian_2025_12_raw_water_counties_in_236":sum(1 for x in output_rows if x.get("Fujian_2025_12_raw_water_intake_count",0)),
            "cross_province_tap_samples_in_236":sum(1 for x in output_rows if x.get("tap_water_source_url")),
            "targeted_industrial_or_hazard_context_cases_in_236":sum(1 for x in output_rows if x.get("targeted_public_environment_case_status")),
            "Mengzi_2026_tap_candidate_context":next((x.get("Mengzi_2026_tap_observations") for x in output_rows if x["code"]=="532503"),None)
        },
        "environment_context_sources":context_sources,
        "annual_air_data_files_count":len(file_audit),
        "method":{
            "spatial_unit":"exact code/name matched provisional county polygons; county is only an indexing unit",
            "grid":"CHAP 1km annual PM2.5 and ground-level O3, population-weighted using WorldPop 2024 1km unconstrained cells",
            "period":"2000-2025 inclusive",
            "statistics":"annual population-weighted mean; 2023-2025 three-year proxy mean; 26-year cell-mean weighted P10/P50/P90; early/mid/recent period means; PM2.5 population share over 15/25/30/35",
            "scope":"screening signal only; no county-wide residential exposure or legal compliance claim",
            "limits":["WorldPop 2024 is a modelled population surface, not a building/address register.",
                "County polygon is a provisional third-party boundary; nine candidates lack exact code/name geometry and remain pending.",
                "A county average can conceal valley/basin/industrial corridor differences; future stage must split actual inhabited residential subareas.",
                "CHAP are model-derived gridded concentration estimates, not official regulatory monitoring at a dwelling.",
                "GB 3095—2026 is effective from 2026-03-01: PM2.5 annual secondary reference is 30 ug/m3 during 2026-2030 and 25 ug/m3 from 2031. The 35 ug/m3 line is retained only as historical GB 3095—2012 context.",
                "The 2023-2025 CHAP three-year mean is a modelled proxy, not the official station-based three-year sliding evaluation under HJ 663—2026.",
                "O3 annual Y1K metric must be interpreted using its dataset definition; do not substitute it for the regulatory MDA8 90th-percentile metric.",
                "No missing data are treated as failures; no R4 exclusions or formal grades are authorized by this batch."]
        },
        "formal_exclusions":0,"formal_grade_changes":0,"all_236_remain_in_funnel":True,
        "output_csv_sha256":sha_file(air_csv)
    }
    write_json(OUT/"R4_ENVIRONMENT_236_SUMMARY.json",summary)
    scope={
        "schema":"RETIREMENT_R4_236_SCOPE_LOCK_V1","locked_at_utc":NOW(),
        "source_final_merge_run_id":"42453646573","input_count":236,
        "membership_csv":"research_engine/retirement/national_funnel/FINAL_FILTER/runs/42453646573/FINAL_CARRY_FORWARD_AFTER_R1_R2_R3.csv",
        "membership_sha256":sha_file(CANDIDATES),
        "split":split,
        "fourth_round_scope":"ALL_236_ONLY",
        "parallel_work_rule":"47 R1-only pending and 11 R2/R3 climate-data pending continue into R4 in parallel with their own evidence supplementation; do not block R4 on these supplements. If a candidate is later reliably excluded by R4, stop unnecessary earlier supplementation. If it passes R4, resume/complete earlier supplementation. Missingness never equals failure.",
        "no_exclusion_from_air_batch":True,
        "formal_exclusions":0,
        "formal_grade_changes":0,
        "R4_status":"AIR_QUALITY_SUBROUND_COMPLETED; WATER_INDUSTRIAL_SOIL_GEOHAZARD_SUBROUNDS_REMAIN_OPEN"
    }
    write_json(OUT/"R4_236_SCOPE_LOCK.json",scope)
    print("R4_236_FINAL",json.dumps({
        "input":236,"R1_clear":178,"R1_only_pending":47,"climate_pending":11,
        "air_computed":summary["air_grid_computed_count"],"air_pending":summary["air_grid_pending_count"],
        "Fujian_air":summary["source_context_counts"]["Fujian_2025_county_air_records_in_236"],
        "Fujian_raw_water":summary["source_context_counts"]["Fujian_2025_12_raw_water_counties_in_236"],
        "industrial_hazard_cases":summary["source_context_counts"]["targeted_industrial_or_hazard_context_cases_in_236"],
        "formal_exclusions":0,"status":summary["status"]
    },ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
