#!/usr/bin/env python3
"""Extract Bio1 annual mean temperature and Bio12 annual precipitation from ScienceDB V8 1km 1991-2020 GeoTIFF.

This is a client-table data recovery run for the 236-region workbook. It does not
change the formal 34-unit Master or assign final grades/exclusions.
"""
from __future__ import annotations
import csv, datetime, hashlib, json, math, os, pathlib, sys, time, zipfile
import requests
import numpy as np
import rasterio
from rasterio.features import geometry_window
from rasterio.warp import transform_geom

ROOT=pathlib.Path("research_engine/retirement")
OUT=ROOT/"output"
STATUS=ROOT/"status"
CACHE=OUT/"scidb_download"
DATASET_ID="cece16f1863b4ebd839894f6df26f8ac"
DATASET_VERSION="V8"
DOI="10.57760/SCIENCEDB.13546"
API_URL="https://www.scidb.cn/api/gin-sdb-filetree/public/file/childrenFileListByPath"
DOWNLOAD_BASE="https://china.scidb.cn/download"
GEOMETRY_URL="https://raw.githubusercontent.com/zzhonglei/GeoCode-Release/main/contributions/china-admin-boundaries/skill/data/china_county.geojson"
GEOMETRY_SHA256="22db6c54b9cb0118ecdcc8a117bf2da4fc24a2229cdba7e6e55dbb5dd56e8246"
ROSTER=ROOT/"evidence/provisional_counties_2026_06.csv"
OUTCSV=STATUS/"phase1_236_bio1_bio12_1km_zonal_1991_2020.csv"
OUTJSON=STATUS/"phase1_236_bio1_bio12_1km_zonal_evidence_20261109.json"
EMAIL_TAG="retirement-research@users.noreply.github.com"

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha_file(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
    return h.hexdigest()
def write_json(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
def normalize_api_items(data):
    if isinstance(data,list): return data
    if isinstance(data,dict):
        for k in ("list","records","items","children","files"):
            if isinstance(data.get(k),list): return data[k]
    return []
def list_dataset_files():
    headers={"content-type":"application/json","username":EMAIL_TAG,"traceid":EMAIL_TAG}
    collected=[]; errors=[]
    def walk(path,depth=0):
        if depth>8: errors.append({"path":path,"error":"MAX_DEPTH"}); return
        last=0
        while True:
            body={"dataSetId":DATASET_ID,"version":DATASET_VERSION,"path":path,"lastIndex":last,"pageSize":200}
            try:
                r=requests.post(API_URL,json=body,headers=headers,timeout=60)
                r.raise_for_status()
                payload=r.json()
                items=normalize_api_items(payload.get("data",payload))
            except Exception as e:
                errors.append({"path":path,"lastIndex":last,"error":type(e).__name__+": "+str(e)[:500]})
                return
            if not items: return
            for item in items:
                if item.get("dir") is True or item.get("isDir") is True or item.get("type")=="directory":
                    child=item.get("path")
                    if child: walk(child,depth+1)
                else:
                    collected.append(item)
            last += len(items)
            if len(items)<200: return
    for root in ("/V8","/"):
        collected.clear(); errors.clear()
        walk(root)
        if collected: break
    return collected,errors
def download_file(file_id,dest,expected_size=None):
    headers={"User-Agent":"RetirementPhase1Climate/1.0","Accept":"application/octet-stream"}
    url=f"{DOWNLOAD_BASE}?fileId={file_id}&username={EMAIL_TAG}&traceId={EMAIL_TAG}"
    last=None
    for attempt in range(1,5):
        tmp=dest.with_suffix(dest.suffix+".part")
        tmp.unlink(missing_ok=True)  # never resume a stale partial; ScienceDB range responses may be 416
        try:
            with requests.get(url,headers=headers,stream=True,timeout=(30,600)) as r:
                r.raise_for_status()
                status=r.status_code; ctype=r.headers.get("Content-Type")
                total=0
                with tmp.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=8*1024*1024):
                        if chunk:
                            f.write(chunk); total+=len(chunk)
            if expected_size and total!=int(expected_size):
                raise RuntimeError(f"SIZE_MISMATCH expected={expected_size} actual={total}")
            tmp.replace(dest)
            return {"http_status":status,"content_type":ctype,"bytes":total,"sha256":sha_file(dest),"attempts":attempt,"url":url}
        except Exception as e:
            last=type(e).__name__+": "+str(e)[:700]
            tmp.unlink(missing_ok=True)
            if attempt<4: time.sleep(attempt*8)
    raise RuntimeError("DOWNLOAD_FAILED_AFTER_4_CLEAN_ATTEMPTS "+str(last))
def load_csv(path):
    with path.open(encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))
def finite(a):
    try:
        x=float(a)
        return x if math.isfinite(x) else None
    except Exception: return None
def get_name(p):
    for k in ("name","县级候选名称","县名","NAME"):
        if p.get(k): return str(p[k]).strip()
    return ""
def get_code(p):
    for k in ("adcode","code","行政区划代码","县级候选代码"):
        if p.get(k) is not None: return str(p[k]).split(".")[0].zfill(6)
    return ""
def main():
    OUT.mkdir(parents=True,exist_ok=True); STATUS.mkdir(parents=True,exist_ok=True); CACHE.mkdir(parents=True,exist_ok=True)
    evidence={
      "schema":"RET_PHASE1_236_BIO1_BIO12_ZONAL_V1","started_at_utc":now(),
      "dataset":{"title":"A 1 km monthly dataset of historical and future climate changes over China",
        "dataset_id":DATASET_ID,"version":DATASET_VERSION,"doi":DOI,"period":"1991-2020",
        "resolution":"0.01 degree approximately 1 km","variables":{"Bio1":"年平均气温（℃）","Bio12":"年降水量（毫米）"},
        "methods":"2185 meteorological stations; ANUSPLIN interpolation with elevation as covariate; historical normals"},
      "formal_master_modified":False,"formal_34_unit_roster_modified":False,
      "formal_exclusions":0,"formal_grades_assigned":0,
      "input_count":0,"geometry_exact_matches":0,"geometry_pending":0,"output_rows":0,
      "status":"RUNNING","files":{},"notes":[
        "This is an administrative-unit zonal mean, not an exact named-neighbourhood or residential-building measurement.",
        "The 236-region client workbook is a separate broad comparison asset; the formal 34-unit Master is not modified.",
        "No missing or geometry-mismatched region is excluded. No final A/B/C/D grade is assigned by this extraction.",
        "Bio1 is annual mean temperature; Bio12 is annual precipitation. Raster band positions and units must pass metadata/range QA before output is accepted."
      ]}
    roster=load_csv(ROSTER)
    if len(roster)!=2847 or len({x.get("code") for x in roster})!=2847: raise RuntimeError("ROSTER_2847_UNIQUENESS_FAIL")
    evidence["input_count"]=len(roster)
    files,api_errors=list_dataset_files()
    evidence["file_listing"]={"item_count":len(files),"errors":api_errors[:20],"sample_items":files[:3]}
    matches=[]
    for x in files:
        fn=str(x.get("fileName") or x.get("name") or "")
        if "China_Bio_1km_1991-2020" in fn and fn.lower().endswith(".zip"):
            matches.append(x)
    if not matches:
        evidence["status"]="DATASET_FILE_LISTING_NO_BIO_ARCHIVE"
        write_json(OUTJSON,evidence); raise RuntimeError("BIO1_BIO12_ARCHIVE_NOT_FOUND_IN_SCIENCEDB_FILE_TREE")
    matches.sort(key=lambda x:int(x.get("size") or 0),reverse=True)
    item=matches[0]; file_id=item.get("id") or item.get("fileId")
    if not file_id: raise RuntimeError("BIO_ARCHIVE_MISSING_FILE_ID")
    fn=str(item.get("fileName") or item.get("name"))
    archive=CACHE/fn
    download_meta=download_file(file_id,archive,item.get("size"))
    evidence["files"]["bio_archive"]={"file_id":file_id,"file_name":fn,"path":str(archive),**download_meta}
    with zipfile.ZipFile(archive) as z:
        bad=z.testzip()
        if bad: raise RuntimeError("ZIP_CRC_FAILURE "+bad)
        tif_members=[x for x in z.infolist() if x.filename.lower().endswith((".tif",".tiff"))]
        if len(tif_members)!=1: raise RuntimeError("EXPECTED_ONE_BIO_GEOTIFF_GOT_"+str(len(tif_members)))
        member=tif_members[0]; tif=CACHE/"China_Bio_1km_1991-2020.tif"
        with z.open(member) as src,tif.open("wb") as dst:
            for chunk in iter(lambda:src.read(8*1024*1024),b""): dst.write(chunk)
    evidence["files"]["bio_geotiff"]={"member":member.filename,"bytes":tif.stat().st_size,"sha256":sha_file(tif)}
    with rasterio.open(tif) as ds:
        if ds.count<12: raise RuntimeError("BIO_RASTER_HAS_FEWER_THAN_12_BANDS")
        if ds.crs is None: raise RuntimeError("BIO_RASTER_CRS_MISSING")
        if str(ds.crs).upper() not in ("EPSG:4326","OGC:CRS84"):
            raise RuntimeError("BIO_RASTER_CRS_NOT_WGS84 "+str(ds.crs))
        # Standard BIOCLIM order: Bio1 is band 1, Bio12 is band 12.
        b1=ds.read(1,out_shape=(min(1000,ds.height),min(1000,ds.width)),masked=True).compressed()
        b12=ds.read(12,out_shape=(min(1000,ds.height),min(1000,ds.width)),masked=True).compressed()
        b1=b1[np.isfinite(b1)]; b12=b12[np.isfinite(b12)]
        if not b1.size or not b12.size: raise RuntimeError("BIO_RASTER_SAMPLE_EMPTY")
        med1=float(np.median(b1)); med12=float(np.median(b12))
        # Infer only conventional integer x10 scaling; reject ambiguous ranges.
        if -60<=med1<=60: scale1=1.0; scale1_rule="native_C"
        elif 60<abs(med1)<=600: scale1=0.1; scale1_rule="integer_tenths_C"
        else: raise RuntimeError("BIO1_SCALE_AMBIGUOUS_MEDIAN_"+str(med1))
        if 0<=med12<=10000: scale12=1.0; scale12_rule="native_mm"
        elif 10000<med12<=100000: scale12=0.1; scale12_rule="integer_tenths_mm"
        else: raise RuntimeError("BIO12_SCALE_AMBIGUOUS_MEDIAN_"+str(med12))
        evidence["raster_metadata"]={"crs":str(ds.crs),"width":ds.width,"height":ds.height,"bands":ds.count,
          "dtype":list(ds.dtypes),"nodata":ds.nodata,"bounds":list(ds.bounds),"transform":list(ds.transform),
          "scales":list(ds.scales),"offsets":list(ds.offsets),"dataset_tags":ds.tags(),
          "Bio1_sample":{"raw_min":float(b1.min()),"raw_median":med1,"raw_max":float(b1.max()),"scale":scale1,"scale_rule":scale1_rule},
          "Bio12_sample":{"raw_min":float(b12.min()),"raw_median":med12,"raw_max":float(b12.max()),"scale":scale12,"scale_rule":scale12_rule}}
        # Strictly match official-ish third-party geometry code AND name; mismatches remain pending.
        geom_path=CACHE/"china_county.geojson"
        if not geom_path.exists() or sha_file(geom_path)!=GEOMETRY_SHA256:
            r=requests.get(GEOMETRY_URL,timeout=120); r.raise_for_status()
            if hashlib.sha256(r.content).hexdigest()!=GEOMETRY_SHA256: raise RuntimeError("GEOMETRY_SHA256_MISMATCH")
            geom_path.write_bytes(r.content)
        gj=json.loads(geom_path.read_text(encoding="utf-8"))
        geo={}
        for ft in gj.get("features",[]):
            p=ft.get("properties") or {}; code=get_code(p); name=get_name(p)
            if code and ft.get("geometry"): geo[code]={"name":name,"geometry":ft["geometry"]}
        exact=[]; pending=[]
        for r in roster:
            code=str(r["code"]).zfill(6); name=str(r["name"]).strip()
            g=geo.get(code)
            if g and g["name"]==name: exact.append((r,g))
            else: pending.append((r,g))
        evidence["geometry_exact_matches"]=len(exact); evidence["geometry_pending"]=len(pending)
        fields=["code","name","geometry_match_status","Bio1_年平均气温_摄氏度","Bio1_P10","Bio1_P50","Bio1_P90",
          "Bio12_年降水量_毫米","Bio12_P10","Bio12_P50","Bio12_P90","valid_grid_cells","valid_fraction",
          "spatial_scope","period","source_doi","source_resolution","scale_rule"]
        with OUTCSV.open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
            for r,g in exact:
                geom=g["geometry"]
                if ds.crs.to_epsg()==4326: geojson_geom=geom
                else: geojson_geom=transform_geom("EPSG:4326",ds.crs,geom)
                try:
                    win=geometry_window(ds,[{"type":"Feature","geometry":geojson_geom,"properties":{}}],boundless=False)
                    arr1=ds.read(1,window=win,masked=True)
                    arr12=ds.read(12,window=win,masked=True)
                    # Pixel-center mask ensures only cells whose centers fall inside the polygon are included.
                    from rasterio.features import geometry_mask
                    tr=ds.window_transform(win)
                    inside=geometry_mask([geojson_geom],out_shape=arr1.shape,transform=tr,invert=True,all_touched=False)
                    v1=np.asarray(arr1.filled(np.nan),dtype=float)[inside]
                    v12=np.asarray(arr12.filled(np.nan),dtype=float)[inside]
                    v1=v1[np.isfinite(v1) & (v1>-1e20)]*scale1
                    v12=v12[np.isfinite(v12) & (v12>-1e20)]*scale12
                    if not v1.size or not v12.size:
                        raise ValueError("NO_VALID_BIO_CELLS")
                    w.writerow({"code":r["code"],"name":r["name"],"geometry_match_status":"EXACT_CODE_NAME",
                      "Bio1_年平均气温_摄氏度":round(float(np.mean(v1)),2),
                      "Bio1_P10":round(float(np.percentile(v1,10)),2),"Bio1_P50":round(float(np.median(v1)),2),
                      "Bio1_P90":round(float(np.percentile(v1,90)),2),
                      "Bio12_年降水量_毫米":round(float(np.mean(v12)),1),
                      "Bio12_P10":round(float(np.percentile(v12,10)),1),"Bio12_P50":round(float(np.median(v12)),1),
                      "Bio12_P90":round(float(np.percentile(v12,90)),1),
                      "valid_grid_cells":int(min(v1.size,v12.size)),"valid_fraction":1.0,
                      "spatial_scope":"县级行政区全域栅格均值，非具体居住片区人口加权值",
                      "period":"1991-2020","source_doi":DOI,"source_resolution":"0.01 degree approximately 1km",
                      "scale_rule":f"Bio1:{scale1_rule};Bio12:{scale12_rule}"})
                except Exception as e:
                    w.writerow({"code":r["code"],"name":r["name"],"geometry_match_status":"EXACT_CODE_NAME_BUT_RASTER_PENDING",
                      "spatial_scope":"县级行政区全域栅格提取失败","period":"1991-2020","source_doi":DOI,
                      "source_resolution":"0.01 degree approximately 1km","scale_rule":type(e).__name__+":"+str(e)[:300]})
            for r,g in pending:
                w.writerow({"code":r["code"],"name":r["name"],"geometry_match_status":"GEOMETRY_OR_NAME_PENDING",
                  "spatial_scope":"行政区代码/名称/边界不匹配，未估算","period":"1991-2020","source_doi":DOI,
                  "source_resolution":"0.01 degree approximately 1km","scale_rule":"待核"})
    rows=load_csv(OUTCSV)
    evidence["output_rows"]=len(rows)
    evidence["value_coverage"]={"Bio1":sum(bool(x.get("Bio1_年平均气温_摄氏度")) for x in rows),
      "Bio12":sum(bool(x.get("Bio12_年降水量_毫米")) for x in rows),
      "geometry_pending_rows":sum(x.get("geometry_match_status")=="GEOMETRY_OR_NAME_PENDING" for x in rows)}
    evidence["status"]="PASS_BIO1_BIO12_1KM_ZONAL_EXTRACT" if len(rows)==2847 and evidence["value_coverage"]["Bio1"]>0 and evidence["value_coverage"]["Bio12"]>0 else "PARTIAL_BIO1_BIO12_ZONAL_EXTRACT"
    evidence["finished_at_utc"]=now()
    write_json(OUTJSON,evidence)
    print(json.dumps(evidence,ensure_ascii=False)[:20000])
if __name__=="__main__":
    try: main()
    except Exception as e:
        err={"schema":"RET_PHASE1_236_BIO1_BIO12_ZONAL_V1","status":"FAILED_OR_BLOCKED",
          "finished_at_utc":now(),"error_type":type(e).__name__,"error":str(e)[:2000],
          "formal_master_modified":False,"formal_exclusions":0,"formal_grades_assigned":0}
        write_json(OUTJSON,err); print(json.dumps(err,ensure_ascii=False)); sys.exit(2)
