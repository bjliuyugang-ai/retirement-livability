#!/usr/bin/env python3
"""Focused one-shot residential-settlement Bio1/Bio12 extraction for 236 retirement candidates.

Uses the already validated ScienceDB 1-km 1991-2020 Bio1/Bio12 raster, OSM
Nominatim settlement/administrative-seat geocoding, WorldPop 2024 1-km population
weights, and exact point-in-polygon checks. It does NOT assign final A-D grades
or exclusions. County-wide means are not used as residential proxies.
"""
from __future__ import annotations
import csv,datetime,hashlib,json,math,pathlib,re,sys,time,zipfile
import requests,subprocess
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import shape,Point
from shapely.prepared import prep

ROOT=pathlib.Path("research_engine/retirement")
STATUS=ROOT/"status"; OUT=ROOT/"output"; CACHE=OUT/"phase1_residential_cache"
ROSTER=ROOT/"evidence/provisional_counties_2026_06.csv"
CODES=ROOT/"evidence/phase1_236_target_codes_20261109.csv"
REFS=ROOT/"evidence/phase1_236_residential_references_20261109.csv"
GEOM_URL="https://raw.githubusercontent.com/zzhonglei/GeoCode-Release/main/contributions/china-admin-boundaries/skill/data/china_county.geojson"
GEOM_SHA="22db6c54b9cb0118ecdcc8a117bf2da4fc24a2229cdba7e6e55dbb5dd56e8246"
BIO_URL="https://china.scidb.cn/download?fileId=e4a842317c8dc59e2b177e1496bdf3c4&username=retirement-research@users.noreply.github.com&traceId=retirement-research@users.noreply.github.com"
BIO_SHA="da73a547a146c38f295f190fa71adf4367d884cabebf8f50f2c0341b40769c6c"
BIO_MEMBERS={"bio1":"China_Bio1_1km_1991-2020.tif","bio12":"China_Bio12_1km_1991-2020.tif"}
WORLDPOP_API="https://api.worldpop.org/v3/countries/CHN/files?year=2024"
OUTCSV=STATUS/"phase1_236_residential_bio1_bio12_1991_2020.csv"
OUTJSON=STATUS/"phase1_236_residential_bio1_bio12_evidence_20261109.json"
CACHE.mkdir(parents=True,exist_ok=True); STATUS.mkdir(parents=True,exist_ok=True)

PROVINCE={"11":"北京市","12":"天津市","13":"河北省","14":"山西省","15":"内蒙古自治区","21":"辽宁省","22":"吉林省","23":"黑龙江省","31":"上海市","32":"江苏省","33":"浙江省","34":"安徽省","35":"福建省","36":"江西省","37":"山东省","41":"河南省","42":"湖北省","43":"湖南省","44":"广东省","45":"广西壮族自治区","46":"海南省","50":"重庆市","51":"四川省","52":"贵州省","53":"云南省","54":"西藏自治区","61":"陕西省","62":"甘肃省","63":"青海省","64":"宁夏回族自治区","65":"新疆维吾尔自治区"}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()
def get(url,headers=None,stream=False,timeout=180):
 r=requests.get(url,headers=headers or {"User-Agent":"RetirementPhase1ResidentialClimate/1.0 (research)"},stream=stream,timeout=timeout)
 r.raise_for_status();return r
def download(url,path,expected_sha=None):
 if path.exists() and (expected_sha is None or sha(path)==expected_sha):return {"reused":True,"bytes":path.stat().st_size,"sha256":sha(path)}
 tmp=path.with_suffix(path.suffix+".part");tmp.unlink(missing_ok=True)
 with get(url,stream=True,timeout=600) as r, tmp.open("wb") as f:
  for chunk in r.iter_content(8*1024*1024):
   if chunk:f.write(chunk)
 digest=sha(tmp)
 if expected_sha and digest!=expected_sha:raise RuntimeError("SHA256 mismatch "+digest)
 tmp.replace(path);return {"reused":False,"bytes":path.stat().st_size,"sha256":digest}
def readcsv(p):
 with open(p,encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def province(code):return PROVINCE.get(str(code)[:2],"")
def clean_name(n):
 return re.sub(r"(特别行政区|维吾尔自治区|壮族自治区|回族自治区|自治区|自治县|自治州|市|县|区|旗)$","",n)
def weighted_percentile(values,weights,q):
 idx=np.argsort(values);v=np.asarray(values)[idx];w=np.asarray(weights)[idx]
 c=np.cumsum(w);return float(v[np.searchsorted(c,q*c[-1],side="left")])
def geocode(code,name,poly,cache,reference):
 if code in cache:return cache[code]
 prov=province(code)
 if not prov:cache[code]={"status":"NO_PROVINCE_MAPPING"};return cache[code]
 reftext=(reference.get("residential_reference") or "").strip()
 generic=("尚未精确定位住宅" in reftext) or reftext.startswith(("县城／城区","县城/城区"))
 targets=[]
 if reftext and not generic:
  raw=re.split(r"[；;/／]",reftext,maxsplit=1)[0].strip()
  raw=re.sub(r"（[^）]*）|\([^)]*\)","",raw).strip()
  for phrase in ("参考样点","成熟居住片区","成熟住区","附近","周边","样点","参考值","参考"):
   raw=raw.replace(phrase,"")
  raw=raw.strip(" /／；;，,")
  if len(raw)>=2:targets.append((raw,"NAMED_RESIDENTIAL_REFERENCE"))
 targets += [(name+"人民政府","COUNTY_SEAT_PROXY"),(name,"SETTLEMENT_NAME")]
 attempts=[]
 for q,role in targets:
  params={"format":"jsonv2","q":q+", "+prov+", China","countrycodes":"cn","limit":10,"addressdetails":1,"accept-language":"zh-CN"}
  if role=="SETTLEMENT_NAME":params["featuretype"]="settlement"
  try:
   rr=requests.get("https://nominatim.openstreetmap.org/search",params=params,headers={"User-Agent":"RetirementLivabilityResearch/1.0 (retirement-research@users.noreply.github.com)","Accept-Language":"zh-CN"},timeout=60)
   rr.raise_for_status();results=rr.json()
  except Exception as e:
   attempts.append({"query":q,"error":repr(e)});time.sleep(1.2);continue
  time.sleep(1.1)
  accepted=[]
  for x in results:
   cls=x.get("class","");typ=x.get("type","")
   if cls=="boundary" and typ=="administrative":continue
   if cls not in ("place","amenity","building","office","railway","tourism") and typ not in ("town","city","village","hamlet","suburb","neighbourhood","townhall","administrative"):
    continue
   try:pt=Point(float(x["lon"]),float(x["lat"]))
   except Exception:continue
   if not poly.covers(pt):continue
   score=0
   if role=="NAMED_RESIDENTIAL_REFERENCE":score+=10
   if cls=="place":score+=4
   if typ in ("town","city","village","suburb","neighbourhood"):score+=3
   if typ in ("townhall","government"):score+=2
   score+=float(x.get("importance") or 0)
   accepted.append((score,x))
  attempts.append({"query":q,"role":role,"result_count":len(results),"accepted_inside_polygon":len(accepted)})
  if accepted:
   accepted.sort(key=lambda z:z[0],reverse=True)
   score,x=accepted[0]
   out={"status":"GEOCODED_POINT_IN_EXACT_COUNTY_POLYGON","role":role,"query":q,"lat":float(x["lat"]),"lon":float(x["lon"]),
    "osm_type":x.get("osm_type"),"osm_id":x.get("osm_id"),"class":x.get("class"),"type":x.get("type"),"importance":x.get("importance"),
    "display_name":x.get("display_name",""),"address":x.get("address") or {},"score":score,"attempts":attempts}
   cache[code]=out;return out
 out={"status":"GEOCODE_PENDING","attempts":attempts};cache[code]=out;return out
def persist_checkpoint(rows,cache_path,cache):
 fields=sorted({k for row in rows for k in row})
 with OUTCSV.open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 cache_path.write_text(json.dumps(cache,ensure_ascii=False,indent=2),encoding="utf-8")
 # Force-add ignored status/cache outputs so partial work survives a runner interruption.
 subprocess.run(["git","add","-f",OUTCSV.as_posix(),cache_path.as_posix()],check=True)
 if subprocess.run(["git","diff","--cached","--quiet"]).returncode!=0:
  subprocess.run(["git","config","user.name","github-actions[bot]"],check=True)
  subprocess.run(["git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com"],check=True)
  subprocess.run(["git","commit","-m",f"Checkpoint residential climate extraction {len(rows)}/236"],check=True)
  subprocess.run(["git","pull","--rebase","origin","main"],check=True)
  subprocess.run(["git","push","origin","HEAD:main"],check=True)
def main():
 started=now()
 codes=[x["code"].zfill(6) for x in readcsv(CODES)]
 refs={x["code"].zfill(6):x for x in readcsv(REFS)}
 if len(codes)!=236 or len(set(codes))!=236:raise RuntimeError("236 target roster count/uniqueness failed")
 if len(refs)!=236 or set(refs)!=set(codes):raise RuntimeError("Residential-reference file does not exactly match frozen 236-code roster")
 roster={x["code"].zfill(6):x["name"] for x in readcsv(ROSTER)}
 geo_path=CACHE/"china_county.geojson"
 download(GEOM_URL,geo_path,GEOM_SHA)
 geo=json.loads(geo_path.read_text(encoding="utf-8"))
 polys={}
 for f in geo["features"]:
  p=f.get("properties") or {};c=str(p.get("adcode") or "").zfill(6)
  if c in codes and f.get("geometry"):geom=shape(f["geometry"]);polys[c]={"name":str(p.get("name") or ""),"shape":prep(geom),"geometry":geom}
 # Original source archive, already verified in the preceding source-QA run.
 archive=CACHE/"China_Bio_1km_1991-2020.zip"
 download(BIO_URL,archive,BIO_SHA)
 with zipfile.ZipFile(archive) as z:
  if z.testzip():raise RuntimeError("ScienceDB Bio archive CRC error")
  members=set(z.namelist())
  for key,member in BIO_MEMBERS.items():
   if member not in members:raise RuntimeError("Missing expected raster member "+member)
   target=CACHE/(key+".tif")
   if not target.exists():
    with z.open(member) as src,target.open("wb") as dst:
     for b in iter(lambda:src.read(8*1024*1024),b""):dst.write(b)
 # Download 2024 WorldPop 1km population raster via official API.
 wp=get(WORLDPOP_API,timeout=60).json()
 pop_url=((wp.get("population") or {}).get("1km"))
 if not pop_url:raise RuntimeError("WorldPop API did not return population.1km URL: "+json.dumps(wp)[:2000])
 pop_path=CACHE/"worldpop_CHN_2024_1km.tif";download(pop_url,pop_path)
 cache_path=CACHE/"nominatim_geocode_cache.json"
 cache=json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
 rows=[];geocoded=0;pending=[];all_attempts=0
 with rasterio.open(CACHE/"bio1.tif") as b1,rasterio.open(CACHE/"bio12.tif") as b12,rasterio.open(pop_path) as pop:
  if b1.crs!=b12.crs or b1.transform!=b12.transform:raise RuntimeError("Bio1/Bio12 grid alignment failed")
  if b1.crs.to_epsg()!=4326 or pop.crs.to_epsg()!=4326:raise RuntimeError("Unexpected raster CRS")
  for i,code in enumerate(codes,1):
   name=roster.get(code) or refs[code].get("region","").split("·")[-1]
   if not name:rows.append({"code":code,"name":"","status":"CODE_NOT_IN_ROSTER","residential_reference":refs[code].get("residential_reference","")});continue
   if code not in polys:
    rows.append({"code":code,"name":name,"status":"GEOMETRY_PENDING_NO_EXACT_CODE_NAME_POLYGON"});pending.append(code);continue
   poly=polys[code]["shape"]
   g=geocode(code,name,poly,cache,refs[code])
   if g["status"]!="GEOCODED_POINT_IN_EXACT_COUNTY_POLYGON":
    rows.append({"code":code,"name":name,"status":g["status"],"geocode_attempts":json.dumps(g.get("attempts",[]),ensure_ascii=False)})
    pending.append(code)
    cache_path.write_text(json.dumps(cache,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PENDING",i,code,name,flush=True);continue
   geocoded+=1;lat,lon=g["lat"],g["lon"]
   # Use WorldPop's own 1-km grid as the population-weighting base; sample climate at each inhabited cell center.
   delta_lat=5.0/111.2;delta_lon=5.0/(111.2*max(0.2,math.cos(math.radians(lat))))
   pwin=from_bounds(lon-delta_lon,lat-delta_lat,lon+delta_lon,lat+delta_lat,transform=pop.transform)
   pwin=pwin.round_offsets().round_lengths()
   pa=pop.read(1,window=pwin,masked=True);ptr=pop.window_transform(pwin)
   rr,cc=np.indices(pa.shape);px=ptr.c+(cc+0.5)*ptr.a;py=ptr.f+(rr+0.5)*ptr.e
   dist=np.sqrt(((py-lat)*111.2)**2+((px-lon)*111.2*math.cos(math.radians(lat)))**2)
   pvals=np.asarray(pa.filled(0),dtype=float)
   candidates=(dist<=5.0)&(~np.ma.getmaskarray(pa))&(pvals>0)
   local_geom=polys[code]["geometry"]
   coords=[];population_weights=[]
   for pr,pc in zip(*np.where(candidates)):
    x=float(px[pr,pc]);y=float(py[pr,pc])
    if local_geom.covers(Point(x,y)):
     coords.append((x,y));population_weights.append(float(pvals[pr,pc]))
   weights_all=np.asarray(population_weights,dtype=float)
   allpop=float(weights_all.sum())
   if coords:
    vals1=np.asarray([v[0] for v in b1.sample(coords)],dtype=float)
    vals12=np.asarray([v[0] for v in b12.sample(coords)],dtype=float)
    good=np.isfinite(vals1)&np.isfinite(vals12)&(vals1>-100)&(vals12>-100)
   else:
    vals1=np.asarray([],dtype=float);vals12=np.asarray([],dtype=float);good=np.asarray([],dtype=bool)
   valid_pop_sum=float(weights_all[good].sum()) if len(weights_all) else 0.0
   coverage=valid_pop_sum/allpop if allpop>0 else 0.0
   vals1=vals1[good];vals12=vals12[good];weights=weights_all[good]
   if len(weights):
    tmean=float(np.average(vals1,weights=weights));pmean=float(np.average(vals12,weights=weights))
    t10,t50,t90=[weighted_percentile(vals1,weights,q) for q in (.1,.5,.9)]
    p10,p50,p90=[weighted_percentile(vals12,weights,q) for q in (.1,.5,.9)]
   else:tmean=pmean=t10=t50=t90=p10=p50=p90=None
   nearest_t=nearest_p=None
   try:
    nearest_t=float(next(b1.sample([(lon,lat)]))[0]);nearest_p=float(next(b12.sample([(lon,lat)]))[0])
    if not math.isfinite(nearest_t) or nearest_t<-100:nearest_t=nearest_p=None
   except Exception:pass
   if len(weights)>=5 and coverage>=.9 and valid_pop_sum>=500:
    quality="HIGH_LOCAL_POPULATION_WEIGHTED"
   elif len(weights)>=2 and coverage>=.75:
    quality="MEDIUM_LOCAL_POPULATION_WEIGHTED"
   else:quality="LOW_OR_INSUFFICIENT_LOCAL_POPULATION_COVERAGE"
   rows.append({"code":code,"name":name,"status":"LOCAL_SETTLEMENT_GRID_EXTRACTED","residential_reference":refs[code].get("residential_reference",""),"original_altitude":refs[code].get("original_altitude",""),
    "geocode_role":g["role"],"geocode_query":g["query"],"latitude":lat,"longitude":lon,"geocode_class":g["class"],"geocode_type":g["type"],
    "geocode_display_name":g["display_name"],"osm_type":g["osm_type"],"osm_id":g["osm_id"],
    "local_radius_km":5,"Bio1_年平均气温_℃_人口加权":round(tmean,2) if tmean is not None else "",
    "Bio1_P10":round(t10,2) if t10 is not None else "","Bio1_P50":round(t50,2) if t50 is not None else "","Bio1_P90":round(t90,2) if t90 is not None else "",
    "Bio12_年降水_mm_人口加权":round(pmean,1) if pmean is not None else "",
    "Bio12_P10":round(p10,1) if p10 is not None else "","Bio12_P50":round(p50,1) if p50 is not None else "","Bio12_P90":round(p90,1) if p90 is not None else "",
    "nearest_grid_Bio1":round(nearest_t,2) if nearest_t is not None else "","nearest_grid_Bio12":round(nearest_p,1) if nearest_p is not None else "",
    "valid_climate_cells":int(len(weights)),"population_2024_within_5km":round(allpop,1),"population_with_valid_climate":round(valid_pop_sum,1),
    "population_coverage":round(coverage,4),"data_quality":quality,"period":"1991—2020","climate_source_doi":"10.57760/SCIENCEDB.13546",
    "population_source_doi":"10.5258/SOTON/WP00840","spatial_scope":"以原始指定居住片区或县城代理点为中心5km范围，WorldPop 2024原生1km人口栅格加权Bio1/Bio12；仅统计目标行政区内人口栅格，不等于全县均值"})
   print("EXTRACTED",i,code,name,quality,"cells",len(weights),"coverage",round(coverage,3),flush=True)
   if i%10==0: persist_checkpoint(rows,cache_path,cache)
   time.sleep(1.1)
 persist_checkpoint(rows,cache_path,cache)
 # Ensure one and only one output row per requested code.
 if len(rows)!=236 or len({x["code"] for x in rows})!=236:raise RuntimeError("Output 236 row uniqueness failed")
 fields=sorted({k for r in rows for k in r})
 with OUTCSV.open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 counts={"requested":236,"local_settlement_extracted":sum(x.get("status")=="LOCAL_SETTLEMENT_GRID_EXTRACTED" for x in rows),
  "named_residential_reference":sum(x.get("geocode_role")=="NAMED_RESIDENTIAL_REFERENCE" for x in rows),
  "county_seat_proxy":sum(x.get("geocode_role")=="COUNTY_SEAT_PROXY" for x in rows),
  "high":sum(x.get("data_quality")=="HIGH_LOCAL_POPULATION_WEIGHTED" for x in rows),
  "medium":sum(x.get("data_quality")=="MEDIUM_LOCAL_POPULATION_WEIGHTED" for x in rows),
  "low":sum(x.get("data_quality")=="LOW_OR_INSUFFICIENT_LOCAL_POPULATION_COVERAGE" for x in rows),
  "geometry_pending":sum(x.get("status","").startswith("GEOMETRY_PENDING") for x in rows),
  "geocode_pending":sum(x.get("status")=="GEOCODE_PENDING" for x in rows),
  "bio1_values":sum(x.get("Bio1_年平均气温_℃_人口加权") not in ("",None) for x in rows),
  "bio12_values":sum(x.get("Bio12_年降水_mm_人口加权") not in ("",None) for x in rows)}
 report={"schema":"RET_PHASE1_236_RESIDENTIAL_BIO1_BIO12_LOCAL_EXTRACTION_V1","started_at_utc":started,"finished_at_utc":now(),
  "mode":"ONE_SHOT_CONCENTRATED_BATCH_NOT_HOURLY_AUTOMATION","input_codes_sha256":sha(CODES),"residential_references_sha256":sha(REFS),"target_count":236,"counts":counts,
  "sources":{"Bio1_Bio12":"ScienceDB DOI 10.57760/SCIENCEDB.13546; 1km; 1991—2020; separate Bio1/Bio12 GeoTIFFs",
   "population":"WorldPop 2024 China native 1km constrained population raster; DOI 10.5258/SOTON/WP00840",
   "geocoder":"OpenStreetMap Nominatim; named residential override where present, otherwise county/town government or settlement proxy",
   "geometry":"Third-party coded 2025 county polygons; exact code/name match required"},
  "method":{"point_buffer":"5km radius around the original named residential reference or explicitly marked county-seat proxy; cells clipped to exact candidate polygon","weighting":"WorldPop native 1km population-grid cell counts; Bio1/Bio12 sampled at those population-cell centers",
   "metrics":"population-weighted mean and weighted P10/P50/P90; valid population coverage correctly calculated",
   "confidence":"HIGH >=5 valid inhabited climate cells and >=90% population coverage and >=500 residents; MEDIUM >=2 cells and >=75% coverage; else LOW"},
  "limitations":["OSM geocoding does not prove actual chosen residential block; results are settlement-proxy climate and must be checked against source altitude and historical station data.",
   "A county-seat proxy is not a specific residential neighborhood; geocode role is preserved for review.",
   "No final A/B/C/D grades or formal exclusions are assigned by this extraction.",
   "Nine exact boundary/code mismatches remain pending; they are not imputed."],
  "files":{"csv":OUTCSV.as_posix(),"csv_sha256":sha(OUTCSV),"geocode_cache":cache_path.as_posix()},
  "formal_exclusions":0,"official_master_overwrite":False}
 OUTJSON.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":
 try:main()
 except Exception as e:
  err={"schema":"RET_PHASE1_236_RESIDENTIAL_BIO1_BIO12_LOCAL_EXTRACTION_V1","status":"FAILED_OR_BLOCKED","error_type":type(e).__name__,"error":str(e)[:3000],"formal_exclusions":0,"official_master_overwrite":False,"at_utc":now()}
  OUTJSON.write_text(json.dumps(err,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  print(json.dumps(err,ensure_ascii=False),flush=True);sys.exit(2)
