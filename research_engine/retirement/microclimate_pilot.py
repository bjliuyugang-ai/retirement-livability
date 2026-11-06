#!/usr/bin/env python3
"""1991-2020 ERA5 moisture + Copernicus GLO-90 elevation sensitivity at 12 county-linked points.

No CMA claim. Sampled polygon interior points are exploratory; they are not
residential sites or an exhaustive terrain/microclimate map. NO county grades.
"""
import datetime,hashlib,json,math,pathlib,statistics,time,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path("research_engine/retirement")
OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
GEOM=ROOT/"status/latest-county-geometry-qa.json"
SITES=[
 ("Haikou","海口市","460108","8885207028122ddba96972505fc30aa574f2495c"),
 ("Kunming","昆明市","530102","4aaef4d04b8f39f5c2e43fb185cdfac90f892ce8"),
 ("Xiamen","厦门市","350203","3bfa941f0236b1ab48eb51dd1095d643bfd88ca4"),
 ("Panzhihua","攀枝花市","510402","5760b0e49c1219da9b09e08ad92e5e3435fc3dd6"),
 ("Mengzi","红河哈尼族彝族自治州","532503","be6456f23ab81b1ba266c5cd03d9b996004e2114"),
 ("Jinghong","西双版纳傣族自治州","532801","5e6b1e9beb39e828009a9913c75b48e22e43099e"),
 ("Guilin","桂林市","450304","1f1f7c440b80fdada8a589d414d1f3e28bb4a4c7"),
 ("Quanzhou","泉州市","350503","ad4647f72880c95ffc22e719273dbc0563d8156b"),
 ("Dali","大理白族自治州","532901","ffd024ccc97ebb0ec01c24acd468e4a9de069f0d"),
 ("Guiyang","贵阳市","520115","f671dbcdf7b2306eb69dbb72f8b036028a5b0db9"),
 ("Nanning","南宁市","450103","2cc72d74cbc2d32f586b0bff674da45076d9a459"),
 ("Sanya","三亚市","460203","e6e62af2a916b4cdea1b5b038578f33be7f204a8")]
def fetch(url,max_attempts=4):
    req=urllib.request.Request(url,headers={"User-Agent":"retirement-microclimate-QA/0.1"})
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(req,timeout=100) as r:return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in [429,500,502,503,504] or attempt==max_attempts-1:raise
            time.sleep(min(10*(attempt+1),30))
        except (urllib.error.URLError,TimeoutError):
            if attempt==max_attempts-1:raise
            time.sleep(4*(attempt+1))
def blobsha(b):return hashlib.sha1(("blob "+str(len(b))+"\0").encode()+b).hexdigest()
def in_ring(lon,lat,vertices):
    hit=False
    for i in range(len(vertices)):
        x0,y0=vertices[i-1][:2];x1,y1=vertices[i][:2]
        if (y0>lat)!=(y1>lat) and lon<(x1-x0)*(lat-y0)/(y1-y0)+x0:hit=not hit
    return hit
def inside(lon,lat,geom):
    def one(p):return bool(p) and in_ring(lon,lat,p[0]) and not any(in_ring(lon,lat,h) for h in p[1:])
    return one(geom["coordinates"]) if geom["type"]=="Polygon" else any(one(p) for p in geom["coordinates"])
def rings(geom):
    if geom["type"]=="Polygon":return geom["coordinates"]
    return [ring for poly in geom["coordinates"] for ring in poly]
def spread_points(anchor,geom):
    vertices=[xy for ring in rings(geom) for xy in ring]
    west,east=min(x[0] for x in vertices),max(x[0] for x in vertices)
    south,north=min(x[1] for x in vertices),max(x[1] for x in vertices)
    candidates=[]
    for xi in range(1,10):
        for yi in range(1,10):
            lon=west+(east-west)*xi/10;lat=south+(north-south)*yi/10
            if inside(lon,lat,geom):
                candidates.append((round(lat,5),round(lon,5)))
    p=[anchor]
    def approx_km(a,b):
        return math.hypot((a[0]-b[0])*111.2,(a[1]-b[1])*111.2*math.cos(math.radians((a[0]+b[0])/2)))
    for _ in range(2):
        remaining=[x for x in candidates if x not in p]
        if not remaining:break
        picked=max(remaining,key=lambda x:min(approx_km(x,y) for y in p))
        p.append(picked)
    return p
def moisture(site,lat,lon):
    args={"latitude":lat,"longitude":lon,"start_date":"1991-01-01","end_date":"2020-12-31",
      "daily":"relative_humidity_2m_mean,dew_point_2m_mean","timezone":"Asia/Shanghai","models":"era5"}
    url="https://archive-api.open-meteo.com/v1/archive?"+urllib.parse.urlencode(args)
    b=fetch(url)
    d=json.loads(b)["daily"];times=d["time"]
    fields=["relative_humidity_2m_mean","dew_point_2m_mean"]
    if not 10950<=len(times)<=10960:raise RuntimeError("Incomplete 30yr ERA5 daily record "+site+" "+str(len(times)))
    nums={}
    for key in fields:
        if len(d[key])!=len(times):raise ValueError("Time/values length mismatch "+site)
        valid=[v for v in d[key] if v is not None]
        if len(valid)<.99*len(times):raise ValueError("Missing humidity/dewpoint >1% "+site)
        nums["mean_"+key]=round(statistics.mean(valid),2)
        for label,months in [("winter",[12,1,2]),("summer",[6,7,8])]:
            chosen=[v for date,v in zip(times,d[key]) if v is not None and int(date[5:7]) in months]
            nums[label+"_"+key]=round(statistics.mean(chosen),2)
    nums.update({"raw_rows":len(times),"raw_sha256":hashlib.sha256(b).hexdigest(),"url":url})
    return nums
res={"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "status":"PENDING","kind":"POINT_MOISTURE_AND_COPERNICUS_DEM_SPATIAL_VARIABILITY_EXPLORATION",
 "valid_county_screenings":0,"official_county_codes_verified":0,
 "weather_model":"ERA5 via Open-Meteo historical API, 1991-2020; NOT CMA normals",
 "dem_source":"Copernicus DEM GLO-90 2021 via Open-Meteo elevation API, 90m resolution",
 "cautions":["Polygon source vintage, CRS and precision not independently established; possible GCJ02/WGS84 spatial mismatch.",
 "Terrain points sampled algorithmically inside nonofficial county polygon; no residential site represented.",
 "DEM range from 3 points is a LOW-BOUND heuristic, not true full county elevation range.",
 "ERA5 0.25deg grids may not resolve local valleys/mountains; no point-derived formal county suitability.",
 "Humidity/dewpoint missing or rate limits must remain explicitly pending, not silently imputed.",
 "No 2026 official boundary/adcode complete verification, no approved hard exclusion criteria."]}
try:
    ge=json.loads(GEOM.read_text(encoding="utf-8"))
    if ge.get("status")!="PASS_SECOND_BOUNDARY_CODE_QA":raise RuntimeError("Previous geometry QA not accepted")
    original={d["site"]:d for d in ge["point_checks"]}
    sites=[];allcoords=[]
    for site,city,code,pinned in SITES:
        data=fetch("https://raw.githubusercontent.com/zhChuXiao/ChinaGeoJson/master/citys/"+urllib.parse.quote(city)+".json")
        if blobsha(data)!=pinned:raise RuntimeError("Source hash mismatch "+city)
        citygeo=json.loads(data)
        matching=[f for f in citygeo["features"] if str(f["properties"]["adcode"])==code]
        if len(matching)!=1:raise RuntimeError("Nonunique county polygon "+site)
        anchor=(original[site]["raw_point_lat"],original[site]["raw_point_lon"])
        if not inside(anchor[1],anchor[0],matching[0]["geometry"]):raise RuntimeError("Anchor outside polygon "+site)
        points=spread_points(anchor,matching[0]["geometry"])
        if len(points)!=3:raise RuntimeError("Could not sample 3 independent interior points "+site)
        rec={"site":site,"candidate_county_code":code,"points":[{"latitude":a,"longitude":b,"role":("original_climate_point" if i==0 else "geometry_interior_sample_"+str(i))} for i,(a,b) in enumerate(points)],
          "sample_count":len(points),"geometry_blob_sha":pinned,"humidity_status":"PENDING","terrain_exception_review":"PENDING",
          "formal_county_screening_status":"NOT_SCREENED"}
        sites.append(rec);allcoords.extend(points)
    if len(allcoords)!=36:raise RuntimeError("Expected 36 lat/lon points")
    elurl="https://api.open-meteo.com/v1/elevation?"+urllib.parse.urlencode(
       {"latitude":",".join(str(x[0]) for x in allcoords),"longitude":",".join(str(x[1]) for x in allcoords)})
    eb=fetch(elurl)
    elevations=json.loads(eb)["elevation"]
    if len(elevations)!=36:raise RuntimeError("Invalid DEM response count")
    if any(v is None for v in elevations):raise RuntimeError("Missing DEM elevation value")
    res["elevation_raw_sha256"]=hashlib.sha256(eb).hexdigest()
    res["elevation_request_url"]=elurl
    res["dem_points_loaded"]=len(elevations)
    for i,rec in enumerate(sites):
        e=[float(v) for v in elevations[i*3:i*3+3]]
        for p,meters in zip(rec["points"],e):p["copernicus_glo90_elevation_m"]=meters
        rec["sample_dem_min_m"]=min(e);rec["sample_dem_max_m"]=max(e)
        rec["sample_dem_span_m"]=round(max(e)-min(e),2)
        rec["terrain_exception_review"]="REQUIRES_LOCAL_TERRAIN_CHECK" if max(e)-min(e)>=300 else "STILL_REQUIRED_SPATIAL_QA"
        if any(v>=2000 for v in e):rec["high_elevation_point_present"]=True
        else:rec["high_elevation_point_present"]=False
        try:
            m=moisture(rec["site"],rec["points"][0]["latitude"],rec["points"][0]["longitude"])
            rec["humidity_era5"]=m
            rec["humidity_status"]="EXPLORATORY_DATA_LOADED"
        except Exception as e:
            rec["humidity_status"]="BLOCKED_WITH_EVIDENCE"
            rec["humidity_error"]=repr(e)
        time.sleep(2)
    res.update({"status":"PASS_ELEVATION_SENSITIVITY" if all("sample_dem_span_m" in r for r in sites) else "BLOCKED_WITH_EVIDENCE",
       "sites_count":len(sites),"humidity_sites_loaded":sum(r["humidity_status"]=="EXPLORATORY_DATA_LOADED" for r in sites),
       "humidity_sites_failed":sum(r["humidity_status"]!="EXPLORATORY_DATA_LOADED" for r in sites),
       "terrain_variability_flagged":sum(r["terrain_exception_review"]=="REQUIRES_LOCAL_TERRAIN_CHECK" for r in sites),
       "points":sites})
except Exception as e:
    res.update({"status":"BLOCKED_WITH_EVIDENCE","error":repr(e)})
(OUT/"microclimate_pilot.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in res.items() if k!="points"},ensure_ascii=False))
if res["status"]!="PASS_ELEVATION_SENSITIVITY":raise SystemExit(2)
