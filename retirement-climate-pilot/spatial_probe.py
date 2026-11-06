#!/usr/bin/env python3
"""Spatial proof of capability, NOT a current official county screening.
Uses geoBoundaries CHN ADM3 represented year 2017, not 2026 official census.
Geometry-to-point hits are provisional and must not increment valid_county_screenings.
"""
import hashlib,json,pathlib,urllib.request,datetime
ROOT=pathlib.Path("retirement-climate-pilot/output")
ROOT.mkdir(parents=True,exist_ok=True)
META_URL="https://www.geoboundaries.org/api/current/gbOpen/CHN/ADM3/"
POINTS=[("Haikou",20.04,110.35),("Kunming",25.04,102.71),("Xiamen",24.48,118.09),("Panzhihua",26.58,101.72),("Mengzi",23.37,103.39),("Jinghong",22.01,100.80),("Guilin",25.27,110.29),("Quanzhou",24.87,118.68),("Dali",25.61,100.27),("Guiyang",26.65,106.63),("Nanning",22.82,108.37),("Sanya",18.25,109.51)]
def fetch_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"retirement-spatial-pilot/0.1","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=150) as resp:
        blob=resp.read()
    return json.loads(blob),hashlib.sha256(blob).hexdigest(),len(blob)
def in_ring(lon,lat,ring):
    inside=False
    j=len(ring)-1
    for i in range(len(ring)):
        x1,y1=ring[j][:2]; x2,y2=ring[i][:2]
        if (y1>lat)!=(y2>lat) and lon < (x2-x1)*(lat-y1)/(y2-y1)+x1:
            inside=not inside
        j=i
    return inside
def in_poly(lon,lat,poly):
    return bool(poly) and in_ring(lon,lat,poly[0]) and not any(in_ring(lon,lat,hole) for hole in poly[1:])
def contains(lon,lat,geom):
    t=geom.get("type"); c=geom.get("coordinates",[])
    return in_poly(lon,lat,c) if t=="Polygon" else any(in_poly(lon,lat,p) for p in c) if t=="MultiPolygon" else False
result={"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "stage":"HISTORIC_POLYGON_SPATIAL_PROBE_ONLY","source":META_URL,
  "valid_county_screenings":0,"official_code_verified":0,"matched_current_counties":0,
  "warning":"2017 historic polygons and approximate point coordinates; no county suitability, no official adcode or microclimate QA."}
try:
    meta,meta_sha,_=fetch_json(META_URL)
    if str(meta.get("boundaryYearRepresented"))!="2017":
        raise ValueError("Unexpected polygon reference year; review source before accepting")
    url=meta.get("simplifiedGeometryGeoJSON") or meta["gjDownloadURL"]
    geo,source_sha,raw_bytes=fetch_json(url)
    features=geo.get("features",[])
    if not 2000 <= len(features) <= 4000: raise ValueError("Unexpected count of county-like polygons: "+str(len(features)))
    hits=[]
    for name,lat,lon in POINTS:
        found=[]
        for feature in features:
            geom=feature.get("geometry")
            if geom is not None and contains(lon,lat,geom):
                props=feature.get("properties",{})
                found.append({k:props.get(k) for k in ["shapeName","shapeID","shapeISO"]})
        hits.append({"site":name,"latitude":lat,"longitude":lon,"historic_polygon_hits":len(found),"polygons":found,
          "county_code_current":None,"review":"REQUIRES_OFFICIAL_CODE_AND_2026_BOUNDARY_QA"})
    result.update({"status":"PASS_HISTORIC_POINT_IN_POLYGON","boundary_year":meta["boundaryYearRepresented"],
      "boundary_source":meta.get("boundarySource"),"boundary_license":meta.get("boundaryLicense"),
      "geometry_url":url,"raw_bytes":raw_bytes,"geometry_sha256":source_sha,
      "geometry_features_loaded":len(features),"point_sites_requested":len(POINTS),
      "point_sites_unique_polygon_hit":sum(h["historic_polygon_hits"]==1 for h in hits),
      "point_sites_unmatched":sum(h["historic_polygon_hits"]==0 for h in hits),
      "point_sites_ambiguous":sum(h["historic_polygon_hits"]>1 for h in hits),"point_hits":hits})
except Exception as exc:
    result.update({"status":"BLOCKED_WITH_EVIDENCE","error":repr(exc)})
(ROOT/"spatial_probe.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in result.items() if k!="point_hits"},ensure_ascii=False))
if result["status"]!="PASS_HISTORIC_POINT_IN_POLYGON":raise SystemExit(2)
