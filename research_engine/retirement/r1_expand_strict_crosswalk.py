#!/usr/bin/env python3
"""Derive a strictly unique historical 2017 county-polygon / 2025 Chinese-code
crosswalk with explicit provisional status, and select distributed R1 anchors.

DOES NOT establish official 2026 county membership nor residential coordinates.
No approximate/fuzzy crosswalk allowed; no silent geographic mismatch allowed.
"""
import collections,datetime,hashlib,json,pathlib,re,urllib.request
from pypinyin import lazy_pinyin
ROOT=pathlib.Path("research_engine/retirement")
OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
MIRROR=ROOT/"evidence/mirror_2025_adcodes.txt"
R1=ROOT/"status/national_r1_first_real_batch_evidence.json"
METADATA_URL="https://www.geoboundaries.org/api/current/gbOpen/CHN/ADM3/"
SUFFIXES=["特别行政区","自治县","自治旗","林区","矿区","左旗","右旗","地区","市","区","县","旗"]
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"retirement-unique-provisional-county-crosswalk/0.1"})
    with urllib.request.urlopen(req,timeout=130) as r:b=r.read()
    return json.loads(b),hashlib.sha256(b).hexdigest(),len(b)
def cn_key(name):
    x=str(name).strip()
    for tail in SUFFIXES:
        if x.endswith(tail):x=x[:-len(tail)];break
    return re.sub("[^a-z]","", "".join(lazy_pinyin(x)).lower())
def en_key(name):
    x=str(name).lower()
    x=re.sub(r"\\([^)]*\\)","",x)
    x=re.sub(r"\\b(autonomous|county|district|city|banner|region|area|special|administrative|prefecture|subdistrict|township|municipality)\\b","",x)
    return re.sub("[^a-z]","",x)
def ring_contains(lon,lat,ring):
    inside=False
    for j in range(len(ring)):
        a=ring[j-1];b=ring[j]
        x1,y1=a[:2];x2,y2=b[:2]
        if (y1>lat)!=(y2>lat) and lon<(x2-x1)*(lat-y1)/(y2-y1)+x1:
            inside=not inside
    return inside
def in_pol(lon,lat,poly):
    if not poly or not ring_contains(lon,lat,poly[0]):return False
    return not any(ring_contains(lon,lat,h) for h in poly[1:])
def polys(geom):
    typ=geom.get("type")
    if typ=="Polygon":return [geom["coordinates"]]
    if typ=="MultiPolygon":return geom["coordinates"]
    return []
def anchor(geom):
    polygons=polys(geom)
    if not polygons:raise ValueError("Invalid geometry")
    def area(ring):
        return abs(sum(ring[i-1][0]*ring[i][1]-ring[i][0]*ring[i-1][1] for i in range(len(ring))))/2
    poly=max(polygons,key=lambda p:area(p[0]))
    ring=poly[0];lon=[pt[0] for pt in ring];lat=[pt[1] for pt in ring]
    midx=(min(lon)+max(lon))/2;midy=(min(lat)+max(lat))/2
    # First try box middle, then dense deterministic interior grid, then triangle interpolation.
    candidates=[(midx,midy)]
    for k in range(21):
        for j in range(21):
            candidates.append((min(lon)+(j+0.5)*(max(lon)-min(lon))/21,
                               min(lat)+(k+0.5)*(max(lat)-min(lat))/21))
    valid=[(x,y) for x,y in candidates if in_pol(x,y,poly)]
    if not valid:raise ValueError("No polygon-interior representative point")
    x,y=min(valid,key=lambda z:(z[0]-midx)**2+(z[1]-midy)**2)
    if not(73<=x<=136 and 17<=y<=55):raise ValueError("Unrealistic China mainland coordinate")
    return round(y,5),round(x,5)
orig=json.loads(R1.read_text(encoding="utf-8"))
already={x["candidate_county_code"] for x in orig["county_era5_climate_records"]}
raw=MIRROR.read_text(encoding="utf-8").splitlines()
codes={a:b for a,b in (r.split(maxsplit=1) for r in raw if r.strip()) if a[-2:]!="00"}
if len(codes)!=2845:raise RuntimeError("Incorrect 2025 mirror")
keys=collections.defaultdict(list)
for code,cn in codes.items():
    s=cn_key(cn)
    if s:keys[s].append((code,cn))
meta,meta_sha,_=get(METADATA_URL)
if str(meta.get("boundaryYearRepresented"))!="2017":raise ValueError("Boundary year changed")
url=meta.get("simplifiedGeometryGeoJSON") or meta["gjDownloadURL"]
geo,geom_sha,geom_bytes=get(url)
features=geo.get("features",[])
if not 2000<=len(features)<=4000:raise RuntimeError("Unexpected historic feature count")
pinyin_counts=collections.Counter(en_key(f["properties"].get("shapeName","")) for f in features)
matches=[];unmatched=0;ambiguous=0
for f in features:
    props=f.get("properties") or {};nm=props.get("shapeName","")
    key=en_key(nm);options=keys.get(key,[])
    if not key or not options:unmatched+=1;continue
    if len(options)!=1 or pinyin_counts[key]!=1:ambiguous+=1;continue
    code,chinese=options[0]
    if code in already:continue
    try:lat,lon=anchor(f["geometry"])
    except Exception:unmatched+=1;continue
    matches.append({"county_code":code,"county_2025_name":chinese,
      "shape_name_2017":nm,"shape_id_2017":props.get("shapeID"),
      "latitude_2017_polygon_interior":lat,"longitude_2017_polygon_interior":lon,
      "province_prefix":code[:2],"crosswalk_quality":"UNIQUE_NAME_EXACT_PINYIN_PROVISIONAL_ONLY",
      "shape_2017_official_2026":False,
      "residential_location_confirmed":False})
if len({r["county_code"] for r in matches})!=len(matches):raise RuntimeError("Crosswalk code collision")
# Favor widest mainland provincial coverage before second entry in same province.
groups=collections.defaultdict(list)
for m in matches:
    groups[m["province_prefix"]].append(m)
for k in groups:
    groups[k].sort(key=lambda z:hashlib.sha256(z["county_code"].encode()).hexdigest())
selected=[]
for depth in range(3):
    for province in sorted(groups):
        if depth<len(groups[province]) and len(selected)<30:
            selected.append(groups[province][depth])
if len(selected)<12:raise RuntimeError("Too few exact unique joined county anchors: "+str(len(selected)))
result={"schema":"RET_R1_EXPAND_HISTORIC_STRICT_CROSSWALK_V1",
 "generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_2017_metadata_url":METADATA_URL,"metadata_sha256":meta_sha,
 "source_2017_geojson_url":url,"geometry_sha256":geom_sha,
 "geometry_bytes":geom_bytes,"feature_count":len(features),
 "2025_mirror_source":str(MIRROR),"2025_mirror_sha256":hashlib.sha256(MIRROR.read_bytes()).hexdigest(),
 "unique_historic_name_crosswalk_matches":len(matches),
 "no_match":unmatched,"ambiguous_name":ambiguous,
 "sampled_count":len(selected),"sampled_province_prefix_count":len({x["province_prefix"] for x in selected}),
 "existing_R1_point_codes_excluded":len(already),
 "official_2026_code_verified":0,"residential_units_verified":0,
 "selected_30":selected,
 "limitations":["GeoBoundaries ADM3 year 2017 may not reflect 2026 subdivisions",
 "Chinese 2025 mirror is nonofficial; pinyin exact match does not establish legal code identity",
 "Computed polygon interior is not verified actual residential area",
 "All climate measurements exploratory only; never justify county-wide elimination without exceptions"]}
path=OUT/"r1_expand_strict_crosswalk.json";path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:result[k] for k in ["feature_count","unique_historic_name_crosswalk_matches","no_match","ambiguous_name","sampled_count","sampled_province_prefix_count"]},ensure_ascii=False),flush=True)
