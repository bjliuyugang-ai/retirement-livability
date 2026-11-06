#!/usr/bin/env python3
"""Two-source nonofficial polygon cross-check for existing 12 climate points.

Purpose: reproducible county geometry-to-code QA, not formal administrative or
climate suitability verification. DataV-derived polygon datum/vintage not independently
confirmed; WGS84 vs GCJ02 offsets and local elevations remain unknown.
"""
import csv,datetime,hashlib,json,math,pathlib,urllib.parse,urllib.request
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
SITES=[
 ("Haikou","海口市","460108",20.04,110.35,"8885207028122ddba96972505fc30aa574f2495c"),
 ("Kunming","昆明市","530102",25.04,102.71,"4aaef4d04b8f39f5c2e43fb185cdfac90f892ce8"),
 ("Xiamen","厦门市","350203",24.48,118.09,"3bfa941f0236b1ab48eb51dd1095d643bfd88ca4"),
 ("Panzhihua","攀枝花市","510402",26.58,101.72,"5760b0e49c1219da9b09e08ad92e5e3435fc3dd6"),
 ("Mengzi","红河哈尼族彝族自治州","532503",23.37,103.39,"be6456f23ab81b1ba266c5cd03d9b996004e2114"),
 ("Jinghong","西双版纳傣族自治州","532801",22.01,100.80,"5e6b1e9beb39e828009a9913c75b48e22e43099e"),
 ("Guilin","桂林市","450304",25.27,110.29,"1f1f7c440b80fdada8a589d414d1f3e28bb4a4c7"),
 ("Quanzhou","泉州市","350503",24.87,118.68,"ad4647f72880c95ffc22e719273dbc0563d8156b"),
 ("Dali","大理白族自治州","532901",25.61,100.27,"ffd024ccc97ebb0ec01c24acd468e4a9de069f0d"),
 ("Guiyang","贵阳市","520115",26.65,106.63,"f671dbcdf7b2306eb69dbb72f8b036028a5b0db9"),
 ("Nanning","南宁市","450103",22.82,108.37,"2cc72d74cbc2d32f586b0bff674da45076d9a459"),
 ("Sanya","三亚市","460203",18.25,109.51,"e6e62af2a916b4cdea1b5b038578f33be7f204a8")]
BASE="https://raw.githubusercontent.com/zhChuXiao/ChinaGeoJson/master/citys/"
ROSTER=ROOT/"evidence/provisional_counties_2026_06.csv"
OLD=pathlib.Path("retirement-climate-pilot/status/latest-spatial-probe.json")
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"retirement-geometry-code-audit/1.0"})
    with urllib.request.urlopen(req,timeout=80) as r:return r.read()
def hashgit(blob):return hashlib.sha1(("blob "+str(len(blob))+"\0").encode()+blob).hexdigest()
def ring(lon,lat,vertices):
    hit=False;j=len(vertices)-1
    for i,(x,y,*_) in enumerate(vertices):
        x0,y0=vertices[j][:2]
        if (y0>lat)!=(y>lat) and lon<(x-x0)*(lat-y0)/(y-y0)+x0:hit=not hit
        j=i
    return hit
def polygon(lon,lat,rings):
    return bool(rings) and ring(lon,lat,rings[0]) and not any(ring(lon,lat,r) for r in rings[1:])
def contains(lon,lat,geom):
    kind=geom.get("type");xy=geom.get("coordinates",[])
    return polygon(lon,lat,xy) if kind=="Polygon" else any(polygon(lon,lat,p) for p in xy) if kind=="MultiPolygon" else False
result={"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status":"UNEXECUTED","stage":"DUAL_NONOFFICIAL_BOUNDARY_IDENTITY_QA",
        "official_polygon_verified":False,"official_2026_county_roster_verified":False,
        "valid_county_screenings":0,"county_climate_grade_count":0,
        "limitations":["GeoJSON current vintage and CRS must be independently verified; potential GCJ02-WGS84 offset.",
          "One urban point does not characterize mountainous/coastal/valley counties.",
          "Source has not been checked against latest formal administrative boundary.",
          "Residential elevation, humidity/dewpoint, climate representativeness, air, water and risk are not complete."]}
try:
    with ROSTER.open(encoding="utf-8-sig",newline="") as f:roster={r["code"]:r for r in csv.DictReader(f)}
    if len(roster)!=2847:raise ValueError("Provisional code roster count mismatch")
    old=json.loads(OLD.read_text(encoding="utf-8"))
    if old.get("status")!="PASS_HISTORIC_POINT_IN_POLYGON":raise ValueError("Prior historical polygon evidence missing")
    historic={p["site"]:p for p in old["point_hits"]}
    allhits=[];src=[];feature_total=0
    for site,city,code,lat,lon,blobsha in SITES:
        url=BASE+urllib.parse.quote(city)+".json"
        b=fetch(url)
        actual_git=hashgit(b)
        if actual_git!=blobsha:raise RuntimeError("Pinned source changed "+site+" expected "+blobsha+" got "+actual_git)
        d=json.loads(b)
        if d.get("type")!="FeatureCollection":raise ValueError("Not a GeoJSON collection: "+city)
        features=d.get("features",[])
        feature_total+=len(features)
        hits=[{"code":str(f["properties"].get("adcode")),"name":f["properties"].get("name"),
               "center":f["properties"].get("center")} for f in features
               if f.get("geometry") and contains(lon,lat,f["geometry"])]
        valid=code in roster and len(hits)==1 and hits[0]["code"]==code and historic[site]["historic_polygon_hits"]==1
        allhits.append({"site":site,"expected_county_code":code,"raw_point_lat":lat,"raw_point_lon":lon,
            "polygon_count_for_city":len(features),"hits":hits,"source_git_blob_sha":actual_git,
            "roster_code_present":code in roster,
            "two_nonofficial_geometry_sources_agree":bool(valid),
            "county_climate_status":"NOT_SCREENED","residence_elevation":"UNKNOWN",
            "terrain_microclimate_exception":"UNASSESSED","humidity_and_dewpoint":"UNASSESSED",
            "national_official_boundary_verified":False})
        src.append({"url":url,"git_blob_sha":actual_git,"source_file":city+".json"})
    result.update({"status":"PASS_SECOND_BOUNDARY_CODE_QA" if len(allhits)==12 and all(h["two_nonofficial_geometry_sources_agree"] for h in allhits) and feature_total>=100 else "PARTIAL_QA",
      "site_count":len(allhits),"unique_expected_hits":sum(h["two_nonofficial_geometry_sources_agree"] for h in allhits),
      "source_geojson_features":feature_total,"source_files":len(src),"source_refs":src,"point_checks":allhits,
      "provisional_roster_count":len(roster)})
except Exception as e:
    result.update({"status":"BLOCKED_WITH_EVIDENCE","error":repr(e)})
(OUT/"county_geometry_qa.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in result.items() if k not in ("point_checks","source_refs")},ensure_ascii=False))
if result["status"]!="PASS_SECOND_BOUNDARY_CODE_QA":raise SystemExit(2)
