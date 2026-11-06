#!/usr/bin/env python3
"""Link 12 verified historical point-in-polygon hits to *archival* adcode candidates.

Open-source historical code snapshot is NOT the official 2026 register.
Bilingual target labels are explicit research hypotheses, not automatic proof.
Never increments valid_county_screenings or issues formal grades.
"""
import datetime, hashlib, json, pathlib, urllib.request
P=pathlib.Path("retirement-climate-pilot/output");P.mkdir(parents=True,exist_ok=True)
SPATIAL=pathlib.Path("retirement-climate-pilot/status/latest-spatial-probe.json")
ROOT="https://raw.githubusercontent.com/modood/Administrative-divisions-of-China/master/dist/"
# (site, expected polygon name, province code, prefecture code, archival Chinese county name)
TARGETS=[
 ("Haikou","Meilan District","46","4601","美兰区"),
 ("Kunming","Wuhua District","53","5301","五华区"),
 ("Xiamen","Siming District","35","3502","思明区"),
 ("Panzhihua","Dong District","51","5104","东区"),
 ("Mengzi","Mengzi City","53","5325","蒙自市"),
 ("Jinghong","Jinghong","53","5328","景洪市"),
 ("Guilin","Xiangshan District","45","4503","象山区"),
 ("Quanzhou","Fengze District","35","3505","丰泽区"),
 ("Dali","Dali City","53","5329","大理市"),
 ("Guiyang","Guanshanhu District","52","5201","观山湖区"),
 ("Nanning","Qingxiu District","45","4501","青秀区"),
 ("Sanya","Jiyang District","46","4602","吉阳区")]
def download(filename):
    url=ROOT+filename
    req=urllib.request.Request(url,headers={"User-Agent":"retirement-adcode-assault/0.1"})
    with urllib.request.urlopen(req,timeout=90) as r: b=r.read()
    return json.loads(b),hashlib.sha256(b).hexdigest(),len(b)
result={"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"status":"UNEXECUTED","stage":"ARCHIVAL_CANDIDATE_CODES_ONLY","valid_county_screenings":0,
"official_code_verified":0,"matched_current_counties":0,
"warning":"2017 historical polygons and third-party archival codes. Bilingual matching manually specified and not officially verified. No county suitability conclusions."}
try:
    spatial=json.loads(SPATIAL.read_text(encoding="utf-8"))
    if spatial.get("status")!="PASS_HISTORIC_POINT_IN_POLYGON":raise RuntimeError("Prior spatial engineering evidence not passed")
    points={p["site"]:p for p in spatial["point_hits"]}
    if len(points)!=12:raise RuntimeError("Source point count !=12")
    areas,asha,abytes=download("areas.json")
    cities,csha,cbytes=download("cities.json")
    provinces,psha,pbytes=download("provinces.json")
    if not 2500<=len(areas)<=3500 or not 300<=len(cities)<=450:raise RuntimeError("Unexpected administrative source counts")
    if len({x["code"] for x in areas})!=len(areas):raise RuntimeError("Duplicate archival county codes")
    city_codes={x["code"]:x for x in cities}
    province_codes={x["code"]:x for x in provinces}
    links=[]
    for site,polygon_name,province_code,city_code,county_name in TARGETS:
        point=points[site]
        poly=point.get("polygons",[])
        if len(poly)!=1 or poly[0].get("shapeName")!=polygon_name:
            raise RuntimeError("Historical polygon mismatch: "+site)
        if city_code not in city_codes or province_code not in province_codes:
            raise RuntimeError("Missing administrative parent: "+site)
        if city_codes[city_code].get("provinceCode")!=province_code:
            raise RuntimeError("Invalid parent relationship: "+site)
        candidates=[a for a in areas if a["name"]==county_name and a["provinceCode"]==province_code and a["cityCode"]==city_code]
        links.append({"site":site,"polygon_english":polygon_name,"archival_county_chinese":county_name,
            "province_code":province_code,"prefecture_code":city_code,
            "candidate_count":len(candidates),"candidate_code":candidates[0]["code"] if len(candidates)==1 else None,
            "candidate_status":"UNVERIFIED_ARCHIVAL_MATCH","polygon_shape_id":poly[0].get("shapeID"),
            "official_2026_confirmed":False,"microclimate_exception_checked":False})
    result.update({"raw_area_count":len(areas),"raw_city_count":len(cities),"raw_province_count":len(provinces),
      "areas_url":ROOT+"areas.json","areas_sha256":asha,"areas_bytes":abytes,
      "cities_sha256":csha,"provinces_sha256":psha,
      "candidate_links":links,
      "candidate_unique_count":sum(x["candidate_count"]==1 for x in links),
      "candidate_unmatched_count":sum(x["candidate_count"]==0 for x in links),
      "candidate_ambiguous_count":sum(x["candidate_count"]>1 for x in links),
      "historic_polygon_source_sha256":spatial["geometry_sha256"],
      "status":"PASS_ARCHIVAL_CODE_CANDIDATES" if all(x["candidate_count"]==1 for x in links) else "CANDIDATES_INCOMPLETE"})
except Exception as e:
    result.update({"status":"BLOCKED_WITH_EVIDENCE","error":repr(e)})
(P/"adcode_probe.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in result.items() if k!="candidate_links"},ensure_ascii=False))
if result["status"]!="PASS_ARCHIVAL_CODE_CANDIDATES":raise SystemExit(2)
