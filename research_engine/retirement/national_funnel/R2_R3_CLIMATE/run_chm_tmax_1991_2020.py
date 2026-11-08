#!/usr/bin/env python3
"""National first-pass winter/summer screening from CHM_Tmax v2 daily Tmax.

Fit-for-purpose scope:
- 0.1-degree daily Tmax, 1991-2020
- monthly climatological mean of daily Tmax
- mean annual number of days with Tmax >= 35 C
- county zonal summaries and conservative first-pass screening
This is a broad national filter, not a site-level microclimate assessment.
"""
from __future__ import annotations
import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
import time
import urllib.request
import urllib.error
import zipfile

import numpy as np
import netCDF4
from affine import Affine
from rasterio.features import geometry_mask
from shapely.geometry import mapping, shape

ROOT = pathlib.Path("research_engine/retirement")
BASE = ROOT / "national_funnel" / "R2_R3_CLIMATE"
WORK = pathlib.Path("work_chm_tmax_1991_2020")
OUT = BASE / "output"
ROSTER = ROOT / "evidence" / "provisional_counties_2026_06.csv"
GEOMETRY_URL = "https://raw.githubusercontent.com/zzhonglei/GeoCode-Release/main/contributions/china-admin-boundaries/skill/data/china_county.geojson"
GEOMETRY_SHA256 = "22db6c54b9cb0118ecdcc8a117bf2da4fc24a2229cdba7e6e55dbb5dd56e8246"
ZENODO_RECORD = "https://zenodo.org/records/22097524"
ZENODO_DOI = "10.5281/zenodo.22097524"
YEARS = range(1991, 2021)
HOT_THRESHOLD_C = 35.0
WINTER_LIMIT_C = 10.0
SUMMER_MONTH_LIMIT_C = 32.0
HOT_DAYS_LIMIT = 30.0
MIN_VALID_DAYS_PER_YEAR = 330
MIN_VALID_MONTH_YEARS = 20
UA = "Mozilla/5.0 RetirementLivability-ClimateScreen/1.0"

FILES = [
    {"name":"CHM_Tmax_1990_1999.zip","md5":"c466c294cd5f0b6bec7d08fe222ed68f","bytes":773381227},
    {"name":"CHM_Tmax_2000_2009.zip","md5":"8817ae160d725045be69fd1a1dee3aca","bytes":774490068},
    {"name":"CHM_Tmax_2010_2019.zip","md5":"dacbd3144865376ed089e15f9e787fca","bytes":774600000},
    {"name":"CHM_Tmax_2020_2022.zip","md5":"082c8e5d9e6199fdd931bb4f839f37d9","bytes":232500000},
]

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def sha256_file(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def download_file(url, path, expected_bytes, expected_md5):
    path.parent.mkdir(parents=True,exist_ok=True)
    part=path.with_suffix(path.suffix+".part")
    last=None
    for attempt in range(1,4):
        offset=part.stat().st_size if part.exists() else 0
        headers={"User-Agent":UA,"Accept":"*/*"}
        if offset:
            headers["Range"]=f"bytes={offset}-"
        try:
            req=urllib.request.Request(url,headers=headers)
            with urllib.request.urlopen(req,timeout=300) as r:
                status=r.status
                mode="ab" if offset and status==206 else "wb"
                if mode=="wb":
                    offset=0
                with part.open(mode) as f:
                    while True:
                        block=r.read(4*1024*1024)
                        if not block:break
                        f.write(block)
            size=part.stat().st_size
            if size!=expected_bytes:
                raise RuntimeError(f"SIZE_MISMATCH expected={expected_bytes} actual={size}")
            h=hashlib.md5()
            with part.open("rb") as f:
                for b in iter(lambda:f.read(8*1024*1024),b""):
                    h.update(b)
            digest=h.hexdigest()
            if digest.lower()!=expected_md5.lower():
                raise RuntimeError(f"MD5_MISMATCH expected={expected_md5} actual={digest}")
            part.replace(path)
            return {"status":"DOWNLOADED","bytes":size,"md5":digest,"http_status":status,"attempt":attempt}
        except Exception as e:
            last=f"{type(e).__name__}: {e}"
            if attempt==3:break
            time.sleep(attempt*5)
    raise RuntimeError("DOWNLOAD_FAILED "+last)

def load_roster():
    with ROSTER.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=2847:
        raise RuntimeError(f"ROSTER_COUNT_EXPECTED_2847_GOT_{len(rows)}")
    return rows

def load_geometry(cache_dir):
    p=cache_dir/"china_county.geojson"
    if not p.exists() or sha256_file(p)!=GEOMETRY_SHA256:
        req=urllib.request.Request(GEOMETRY_URL,headers={"User-Agent":UA})
        with urllib.request.urlopen(req,timeout=120) as r:
            p.write_bytes(r.read())
    digest=sha256_file(p)
    if digest!=GEOMETRY_SHA256:
        raise RuntimeError("GEOMETRY_SHA256_MISMATCH "+digest)
    doc=json.loads(p.read_text(encoding="utf-8"))
    out={}
    for feature in doc.get("features",[]):
        props=feature.get("properties") or {}
        code=str(props.get("adcode") or "")
        name=str(props.get("name") or "")
        if len(code)==6 and code.isdigit():
            out[code]={"name":name,"geometry":feature.get("geometry")}
    return out,{"url":GEOMETRY_URL,"sha256":digest,"feature_count":len(doc.get("features",[])),"coded_count":len(out),"status":"PROVISIONAL_THIRD_PARTY_CODED_GEOMETRY"}

def extract_nc(archive, work_dir):
    with zipfile.ZipFile(archive) as z:
        members=[x for x in z.infolist() if x.filename.lower().endswith(".nc")]
        if len(members)!=1:
            raise RuntimeError(f"EXPECTED_ONE_NETCDF_MEMBER_GOT_{len(members)}")
        member=members[0]
        out=work_dir/pathlib.Path(member.filename).name
        with z.open(member) as src, out.open("wb") as dst:
            while True:
                b=src.read(8*1024*1024)
                if not b:break
                dst.write(b)
        return out,{"member":member.filename,"uncompressed_bytes":member.file_size}

def process_all_files():
    cache_dir=WORK/"cache"
    cache_dir.mkdir(parents=True,exist_ok=True)
    monthly_sum=None
    monthly_count=None
    annual_hot_sum=None
    annual_valid_years=None
    annual_years_over30=None
    grid_lat=None
    grid_lon=None
    file_evidence=[]
    processed_years=[]
    for file_meta in FILES:
        archive_name=file_meta["name"]
        archive=cache_dir/archive_name
        url=f"https://zenodo.org/records/22097524/files/{archive_name}?download=1"
        print(f"CHM_DOWNLOAD_START {archive_name}",flush=True)
        dl=download_file(url,archive,file_meta["bytes"],file_meta["md5"])
        nc_path,zip_meta=extract_nc(archive,cache_dir)
        print(f"CHM_EXTRACTED {archive_name} bytes={zip_meta['uncompressed_bytes']}",flush=True)
        with netCDF4.Dataset(nc_path,"r") as ds:
            lat=np.asarray(ds.variables["lat"][:],dtype=np.float64)
            lon=np.asarray(ds.variables["lon"][:],dtype=np.float64)
            if grid_lat is None:
                grid_lat=lat
                grid_lon=lon
                shape2=(len(lat),len(lon))
                monthly_sum=np.zeros((12,*shape2),dtype=np.float64)
                monthly_count=np.zeros((12,*shape2),dtype=np.uint16)
                annual_hot_sum=np.zeros(shape2,dtype=np.float32)
                annual_valid_years=np.zeros(shape2,dtype=np.uint8)
                annual_years_over30=np.zeros(shape2,dtype=np.uint8)
            else:
                if len(lat)!=len(grid_lat) or len(lon)!=len(grid_lon) or not np.allclose(lat,grid_lat) or not np.allclose(lon,grid_lon):
                    raise RuntimeError("CHM_GRID_COORDINATES_CHANGED_BETWEEN_FILES")
            tvar=ds.variables["Tmax"]
            if getattr(tvar,"units","").replace(" ","").lower() not in ("°c","degc","degree_celsius","degrees_celsius","c"):
                raise RuntimeError("UNEXPECTED_TMAX_UNITS "+str(getattr(tvar,"units",None)))
            tvals=ds.variables["time"][:]
            dates=netCDF4.num2date(tvals,ds.variables["time"].units,calendar=getattr(ds.variables["time"],"calendar","standard"))
            groups={}
            for i,d in enumerate(dates):
                y=int(d.year)
                if y in YEARS:
                    groups.setdefault((y,int(d.month)),[]).append(i)
            years_here=sorted({y for y,m in groups})
            for y in years_here:
                year_hot=np.zeros(shape2,dtype=np.uint16)
                year_valid=np.zeros(shape2,dtype=np.uint16)
                for m in range(1,13):
                    idxs=groups.get((y,m),[])
                    if not idxs:
                        continue
                    if idxs[-1]-idxs[0]+1==len(idxs):
                        arr=np.ma.asarray(tvar[idxs[0]:idxs[-1]+1,:,:])
                    else:
                        arr=np.ma.asarray(tvar[idxs,:,:])
                    data=np.asarray(arr.filled(np.nan),dtype=np.float32)
                    valid=np.isfinite(data)
                    monthly_sum[m-1]+=np.where(valid,data,0.0).sum(axis=0,dtype=np.float64)
                    monthly_count[m-1]+=valid.sum(axis=0,dtype=np.uint16)
                    year_hot+=((data>=HOT_THRESHOLD_C)&valid).sum(axis=0,dtype=np.uint16)
                    year_valid+=valid.sum(axis=0,dtype=np.uint16)
                good=year_valid>=MIN_VALID_DAYS_PER_YEAR
                annual_hot_sum[good]+=year_hot[good].astype(np.float32)
                annual_valid_years[good]+=1
                annual_years_over30[good]+=(year_hot[good]>HOT_DAYS_LIMIT).astype(np.uint8)
                processed_years.append(y)
                print(f"CHM_YEAR_DONE {y} valid_grid_cells={int(good.sum())}",flush=True)
        file_evidence.append({"file":archive_name,"download":dl,"netcdf":zip_meta,"years_processed":years_here})
        archive.unlink(missing_ok=True)
        nc_path.unlink(missing_ok=True)
    if sorted(set(processed_years))!=list(YEARS):
        raise RuntimeError(f"YEAR_COVERAGE_INCOMPLETE {sorted(set(processed_years))}")
    month_ok=monthly_count>=MIN_VALID_MONTH_YEARS*28
    month_mean=np.divide(monthly_sum,monthly_count,out=np.full_like(monthly_sum,np.nan),where=month_ok)
    any_month=np.isfinite(month_mean)
    coldest=np.min(np.where(any_month,month_mean,np.inf),axis=0).astype(np.float32)
    hottest=np.max(np.where(any_month,month_mean,-np.inf),axis=0).astype(np.float32)
    coldest[~np.isfinite(coldest)]=np.nan
    hottest[~np.isfinite(hottest)]=np.nan
    hot_days=np.divide(annual_hot_sum,annual_valid_years,out=np.full_like(annual_hot_sum,np.nan),where=annual_valid_years>=20)
    hot_year_share=np.divide(annual_years_over30,annual_valid_years,out=np.full_like(annual_hot_sum,np.nan),where=annual_valid_years>=20)
    return {
        "lat":grid_lat,"lon":grid_lon,"coldest":coldest,"hottest":hottest,
        "hot_days":hot_days,"hot_year_share":hot_year_share,
        "monthly_count_min":int(monthly_count.min()),"monthly_count_max":int(monthly_count.max()),
        "annual_valid_years_min":int(annual_valid_years.min()),"annual_valid_years_max":int(annual_valid_years.max()),
        "files":file_evidence,"processed_years":sorted(set(processed_years))
    }

def pct(vals,q):
    vals=np.asarray(vals,dtype=np.float64)
    vals=vals[np.isfinite(vals)]
    return float(np.percentile(vals,q)) if vals.size else None

def zonal_county_metrics(roster,geo,grid):
    lat=np.asarray(grid["lat"])
    lon=np.asarray(grid["lon"])
    cold=np.asarray(grid["coldest"])
    hot=np.asarray(grid["hottest"])
    days=np.asarray(grid["hot_days"])
    share=np.asarray(grid["hot_year_share"])
    if lat[0]<lat[-1]:
        lat=lat[::-1]; cold=cold[::-1,:]; hot=hot[::-1,:]; days=days[::-1,:]; share=share[::-1,:]
    if lon[0]>lon[-1]:
        lon=lon[::-1]; cold=cold[:,::-1]; hot=hot[:,::-1]; days=days[:,::-1]; share=share[:,::-1]
    dx=float(np.median(np.abs(np.diff(lon))))
    dy=float(np.median(np.abs(np.diff(lat))))
    rows=[]
    for i,r in enumerate(roster,1):
        code=str(r["code"]); name=str(r["name"])
        g=geo.get(code)
        row={"code":code,"name":name,"geometry_status":"PENDING","grid_cell_count":0,"geometry_method":"CELL_CENTRE"}
        if not g or g["name"]!=name or not g["geometry"]:
            row["geometry_status"]="PENDING_GEOMETRY_OR_NAME_MISMATCH"
            rows.append(row); continue
        geom=shape(g["geometry"])
        if not geom.is_valid:
            geom=geom.buffer(0)
        if geom.is_empty or not geom.is_valid:
            row["geometry_status"]="PENDING_INVALID_GEOMETRY"
            rows.append(row); continue
        minx,miny,maxx,maxy=geom.bounds
        ri=np.flatnonzero((lat>=miny-dy)&(lat<=maxy+dy))
        ci=np.flatnonzero((lon>=minx-dx)&(lon<=maxx+dx))
        if not ri.size or not ci.size:
            row["geometry_status"]="PENDING_OUTSIDE_GRID"
            rows.append(row); continue
        r0,r1=int(ri[0]),int(ri[-1]+1)
        c0,c1=int(ci[0]),int(ci[-1]+1)
        transform=Affine(dx,0,float(lon[c0]-dx/2),0,-dy,float(lat[r0]+dy/2))
        mask=geometry_mask([mapping(geom)],out_shape=(r1-r0,c1-c0),transform=transform,invert=True,all_touched=False)
        if not mask.any():
            ix=int(np.abs(lon-geom.centroid.x).argmin())
            iy=int(np.abs(lat-geom.centroid.y).argmin())
            mask=np.zeros((r1-r0,c1-c0),dtype=bool)
            if r0<=iy<r1 and c0<=ix<c1:
                mask[iy-r0,ix-c0]=True
            row["geometry_method"]="NEAREST_GRID_CELL_FALLBACK"
        row["grid_cell_count"]=int(mask.sum())
        cv=cold[r0:r1,c0:c1][mask]
        hv=hot[r0:r1,c0:c1][mask]
        dv=days[r0:r1,c0:c1][mask]
        sv=share[r0:r1,c0:c1][mask]
        row.update({
            "winter_valid_cells":int(np.isfinite(cv).sum()),
            "winter_coldest_month_tmax_p10":pct(cv,10),
            "winter_coldest_month_tmax_p50":pct(cv,50),
            "winter_coldest_month_tmax_p90":pct(cv,90),
            "summer_valid_cells":int(np.isfinite(hv).sum()),
            "summer_hottest_month_tmax_p10":pct(hv,10),
            "summer_hottest_month_tmax_p50":pct(hv,50),
            "summer_hottest_month_tmax_p90":pct(hv,90),
            "hot_days_valid_cells":int(np.isfinite(dv).sum()),
            "mean_annual_days_tmax_ge35_p10":pct(dv,10),
            "mean_annual_days_tmax_ge35_p50":pct(dv,50),
            "mean_annual_days_tmax_ge35_p90":pct(dv,90),
            "share_years_annual_hot_days_gt30_p50":pct(sv,50),
        })
        row["geometry_status"]="MATCH"
        if row["geometry_method"]=="NEAREST_GRID_CELL_FALLBACK" or row["grid_cell_count"]<=1:
            row["confidence"]="LOW"
        elif row["grid_cell_count"]<5:
            row["confidence"]="MEDIUM"
        else:
            row["confidence"]="HIGH"
        rows.append(row)
        if i%300==0 or i==len(roster):
            print(f"CHM_ZONAL_PROGRESS {i}/{len(roster)}",flush=True)
    return rows

def classify(rows):
    for r in rows:
        if r.get("geometry_status")!="MATCH":
            r["winter_status"]="PENDING"
            r["summer_status"]="PENDING"
            r["winter_reason"]="GEOMETRY_PENDING"
            r["summer_reason"]="GEOMETRY_PENDING"
            continue
        n=int(r.get("grid_cell_count") or 0)
        winter_p=r.get("winter_coldest_month_tmax_p90")
        summer_p=r.get("summer_hottest_month_tmax_p10")
        hotdays_p=r.get("mean_annual_days_tmax_ge35_p10")
        if n<5:
            winter_p=r.get("winter_coldest_month_tmax_p50")
            summer_p=r.get("summer_hottest_month_tmax_p50")
            hotdays_p=r.get("mean_annual_days_tmax_ge35_p50")
        if winter_p is None:
            r["winter_status"]="PENDING"; r["winter_reason"]="NO_VALID_WINTER_METRIC"
        elif winter_p<WINTER_LIMIT_C:
            r["winter_status"]="EXCLUDE"; r["winter_reason"]="COLD_MONTH_MEAN_DAILY_TMAX_BELOW_10C"
        else:
            r["winter_status"]="PASS"; r["winter_reason"]="NOT_CLEARED_BY_WINTER_HARD_SCREEN"
        summer_fail=[]
        if summer_p is not None and summer_p>=SUMMER_MONTH_LIMIT_C:
            summer_fail.append("HOTTEST_MONTH_MEAN_DAILY_TMAX_GE_32C")
        if hotdays_p is not None and hotdays_p>HOT_DAYS_LIMIT:
            summer_fail.append("MEAN_ANNUAL_TMAX_GE35_DAYS_GT30")
        if summer_fail:
            r["summer_status"]="EXCLUDE"; r["summer_reason"]=";".join(summer_fail)
        elif summer_p is None or hotdays_p is None:
            r["summer_status"]="PENDING"; r["summer_reason"]="INCOMPLETE_SUMMER_METRICS"
        else:
            r["summer_status"]="PASS"; r["summer_reason"]="NOT_CLEARED_BY_SUMMER_HARD_SCREEN"

def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        w.writeheader();w.writerows(rows)

def main():
    started=now()
    WORK.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    roster=load_roster()
    geo,geo_meta=load_geometry(WORK)
    grid=process_all_files()
    rows=zonal_county_metrics(roster,geo,grid)
    classify(rows)
    winter_excluded=[r for r in rows if r["winter_status"]=="EXCLUDE"]
    winter_carry=[r for r in rows if r["winter_status"]!="EXCLUDE"]
    summer_excluded=[r for r in winter_carry if r["summer_status"]=="EXCLUDE"]
    final_carry=[r for r in winter_carry if r["summer_status"]!="EXCLUDE"]
    write_csv(OUT/"R2_R3_CLIMATE_METRICS_ALL_2847.csv",rows)
    write_csv(OUT/"R2_WINTER_EXCLUDED.csv",winter_excluded)
    write_csv(OUT/"R2_WINTER_CARRY_FORWARD.csv",winter_carry)
    write_csv(OUT/"R3_SUMMER_EXCLUDED_AFTER_WINTER.csv",summer_excluded)
    write_csv(OUT/"R3_SUMMER_CARRY_FORWARD_AFTER_WINTER.csv",final_carry)
    summary={
        "schema":"RETIREMENT_CHM_TMAX_R2_R3_SCREEN_V1",
        "status":"COMPLETED_WITH_PENDING",
        "started_at_utc":started,"completed_at_utc":now(),
        "input_count":len(roster),
        "source":{"name":"CHM_Tmax v2","record":ZENODO_RECORD,"doi":ZENODO_DOI,"period":"1991-2020","resolution":"0.1 degree","variable":"daily Tmax","units":"degree C","method":"station-based angular-distance weighting with altitude considered"},
        "source_files":grid["files"],
        "processed_years":grid["processed_years"],
        "grid":{"lat_count":len(grid["lat"]),"lon_count":len(grid["lon"]),"lat_min":float(np.min(grid["lat"])),"lat_max":float(np.max(grid["lat"])),"lon_min":float(np.min(grid["lon"])),"lon_max":float(np.max(grid["lon"]))},
        "geometry":geo_meta,
        "thresholds":{"winter_coldest_month_mean_daily_tmax_below_c":WINTER_LIMIT_C,"summer_hottest_month_mean_daily_tmax_ge_c":SUMMER_MONTH_LIMIT_C,"mean_annual_days_daily_tmax_ge35_gt":HOT_DAYS_LIMIT},
        "aggregation_policy":"For counties with >=5 0.1-degree grid cells, winter exclusion requires p90 of cell coldest-month means <10C; summer exclusion requires p10 of cell hottest-month means >=32C or p10 of mean annual >=35C days >30. Counties with <5 cells use median. This conservative area-based screen avoids excluding a county because of a small local pocket; later work can split promising counties into residential subareas.",
        "winter":{"excluded_count":len(winter_excluded),"carry_forward_count":len(winter_carry),"pending_count":sum(r["winter_status"]=="PENDING" for r in rows)},
        "summer_after_winter":{"excluded_count":len(summer_excluded),"carry_forward_count":len(final_carry),"pending_count":sum(r["summer_status"]=="PENDING" for r in final_carry)},
        "r1_merge":"NOT_APPLIED_YET; this climate computation covers all 2,847 roster units so it can be merged with the current R1 output without rerunning the 30-year climate extraction.",
        "data_quality":"FIT_FOR_PURPOSE; 0.1-degree daily Tmax is sufficient for national first-pass screening, not for final neighborhood/site selection."
    }
    (OUT/"R2_R3_CLIMATE_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
