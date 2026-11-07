#!/usr/bin/env python3
"""Real HTTP boundary lookup for NINE county candidates missing from the
third-party nationwide code-bearing GIS layer: 7 existing in 2025 code
compilation + 2 legally created in 2026.

Probe DataV GeoAtlas standalone {adcode}.json, then parent {adcode}_full.json.
Validate actual response geometry/adcode and record data-vintage/CRS unknowns.
Neither 200 nor a polygon means officially current 2026 certified boundary.
"""
import collections,datetime,hashlib,json,pathlib,urllib.error,urllib.request
from shapely.geometry import shape
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/"status/national_2025_roster_vs_2891_coded_geometry_evidence.json"
S=json.loads(SRC.read_text(encoding="utf-8"))
if S["2025_county_codes_missing_coded_geometry_count"]!=7 or len(S["new_2026_establishment_counties_in_provisional_R0"])!=2:
 raise RuntimeError("Expected 7 historical and 2 newly created counties")
targets=[{"code":x["code"],"name":x["name_2025"],"class":"2025_HISTORICAL_COUNTY"} for x in S["2025_county_codes_missing_coded_geometry"]]+[
 {"code":x["code"],"name":x["name"],"class":"2026_LEGALLY_ESTABLISHED_SECONDARY_CODE"} for x in S["new_2026_establishment_counties_in_provisional_R0"]]
if len(targets)!=9 or len(set(x["code"] for x in targets))!=9:raise RuntimeError("Nine unique county targets missing")
parent={"460302":"460300","460303":"460300","500157":"500000","540481":"540400","540581":"540500",
"653228":"653200","653229":"653200","653132":"653100","659013":"650000"}
base="https://geo.datav.aliyun.com/areas_v3/bound/"
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":"RetirementCountyBoundaryNineFix/0.1","Accept":"application/json,*/*"})
 try:
  with urllib.request.urlopen(req,timeout=30) as r:raw=r.read(14_000_001);status=r.status
  if len(raw)>14_000_000:raise RuntimeError("HTTP data too large for QA")
  return {"status":"HTTP_200","code":status,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"raw":raw}
 except urllib.error.HTTPError as e:return {"status":"HTTP_"+str(e.code),"error":repr(e)}
 except Exception as e:return {"status":"FAILED_"+type(e).__name__,"error":repr(e)}
def features_payload(raw):
 try:data=json.loads(raw)
 except Exception as ex:return [],"INVALID_JSON:"+repr(ex)
 if isinstance(data,dict):
  if data.get("type")=="FeatureCollection":return data.get("features") or [],"FEATURE_COLLECTION"
  if data.get("type")=="Feature":return [data],"FEATURE"
 return [],"UNRECOGNIZED_JSON_STRUCTURE"
def validate(fs,targetcode):
 vals=[]
 for f in fs:
  prop=f.get("properties") or {};c=str(prop.get("adcode") or "")
  g=f.get("geometry")
  if not g:continue
  try:
   geom=shape(g)
   if geom.is_empty:continue
   bounds=[round(float(v),5) for v in geom.bounds]
   near=(70<=bounds[0]<=140 and 0<=bounds[1]<=56 and 70<=bounds[2]<=140 and 0<=bounds[3]<=56)
   vals.append({"feature_code":c,"feature_name":str(prop.get("name") or ""),"geometry_type":geom.geom_type,
    "geom_valid":bool(geom.is_valid),"geom_bounds_lonlat":bounds,"rough_geographic_range":near,"matches_requested_code":c==targetcode})
  except Exception as ex:vals.append({"geom_parse_error":repr(ex),"feature_code":c})
 return vals
results=[];fallback_cache={}
for target in targets:
 code=target["code"];url=base+code+".json";response=get(url)
 record={**target,"direct_url":url,"direct_status":response["status"],
   "direct_error":response.get("error"),"direct_response_sha256":response.get("sha256"),
   "direct_response_bytes":response.get("bytes"),"direct_validated_geometry":False,
   "parent_code":parent[code],"parent_status":None,"parent_direct_feature_code_match":False,
   "parent_candidate_features":[],"current_2026_official_boundary_proof":False}
 if response.get("raw"):
  fs,structure=features_payload(response["raw"])
  record["direct_structure"]=structure
  check=validate(fs,code)
  record["direct_shape_features"]=check[:6]
  good=[x for x in check if x.get("matches_requested_code") and x.get("geom_valid") and x.get("rough_geographic_range")]
  record["direct_validated_geometry"]=len(good)==1 and len(check)==1
  outp=OUT/("datav_county_"+code+".json");outp.write_bytes(response["raw"])
 if not record["direct_validated_geometry"]:
  pp=parent[code]
  if pp not in fallback_cache:
   fallback_cache[pp]=get(base+pp+"_full.json")
   if fallback_cache[pp].get("raw"):
    (OUT/("datav_parent_"+pp+"_full.json")).write_bytes(fallback_cache[pp]["raw"])
  r=fallback_cache[pp]
  record["parent_status"]=r["status"]
  record["parent_response_sha256"]=r.get("sha256")
  record["parent_response_bytes"]=r.get("bytes")
  if r.get("raw"):
   fs,struct=features_payload(r["raw"]);record["parent_structure"]=struct
   candidate=[f for f in fs if str((f.get("properties") or {}).get("adcode") or "")==code]
   checks=validate(candidate,code)
   record["parent_candidate_features"]=checks[:5]
   record["parent_direct_feature_code_match"]=len(checks)==1 and checks[0].get("geom_valid") and checks[0].get("rough_geographic_range")
 record["alternative_coded_geometry_located"]=record["direct_validated_geometry"] or record["parent_direct_feature_code_match"]
 record["boundary_status"]="THIRD_PARTY_LIVE_GEOMETRY_OBTAINED_VINTAGE_UNVERIFIED" if record["alternative_coded_geometry_located"] else "NOT_FOUND_OR_UNVERIFIED_FROM_DATAV"
 results.append(record)
 print("NINE_COUNTY_BOUNDARY_REAL_CHECK",code,target["name"],record["direct_status"],
       "parent",record["parent_status"],"geometry",record["alternative_coded_geometry_located"],flush=True)
confirmed=sum(x["alternative_coded_geometry_located"] for x in results)
report={"schema":"RET_NINE_MISSING_MAINLAND_CODED_COUNTY_BOUNDARIES_REAL_HTTP_QA_V1",
 "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "prior_2025_polygon_diff_sha256":hashlib.sha256(SRC.read_bytes()).hexdigest(),
 "source":"DataV.GeoAtlas /areas_v3/bound/{adcode}.json and {parent}_full.json",
 "input_county_targets":9,"2025_missing_counties":7,"2026_two_new_established":2,
 "distinct_parent_fallback_groups":len(fallback_cache),
 "alternative_live_coded_geometries_located":confirmed,"not_found_or_unverified":9-confirmed,
 "official_2026_boundary_certified_count":0,"source_crs_explicitly_verified":False,
 "full_national_2847_county_status_unchanged":True,"formal_valid_county_screenings":0,
 "target_results":results,
 "limiting_conditions":["Third-party DataV can be outdated: observed geometry alone is not an official legal 2026 boundary",
 "A successful response for parent and requested code must still pass unique feature code and shape QA",
 "No residential site, microclimate, drinking water or hazard data established by administrative polygon",
 "If 2026 new districts have no public boundary, maintain explicit PENDING not invented polygon"]}
(OUT/"nine_missing_county_geoatlas_actual_requests.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"requested":9,"source_recovered":confirmed,"not_found":9-confirmed,
 "by_direct":sum(x["direct_validated_geometry"] for x in results),
 "by_parent":sum(x["parent_direct_feature_code_match"] for x in results)},ensure_ascii=False),flush=True)
