#!/usr/bin/env python3
"""First nationwide R4 industrial permit screen over ALL 236 carry-forward county units.

Public MEE permit portal, city-level industry-filtered queries (not registration DB).
It ALWAYS reports coverage/truncation by province/city/industry. Industry or permit
presence does not imply pollution exposure, wrongdoing or a hard-exclusion.
Only 236 candidates are matched; all remain in the fourth-round funnel.
"""
from __future__ import annotations
import csv, hashlib, html, http.cookiejar, json, os, pathlib, re, sys, time
import urllib.error, urllib.parse, urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from shapely.geometry import shape, Point

ROOT=pathlib.Path("research_engine/retirement")
BASE=ROOT/"national_funnel/R4_ENVIRONMENT_236/NATIONAL_PERMIT_236"
OUT=BASE/"output"
CAND=ROOT/"national_funnel/FINAL_FILTER/runs/42453646573/FINAL_CARRY_FORWARD_AFTER_R1_R2_R3.csv"
GEO_URL="https://raw.githubusercontent.com/zzhonglei/GeoCode-Release/main/contributions/china-admin-boundaries/skill/data/china_county.geojson"
GEO_SHA="22db6c54b9cb0118ecdcc8a117bf2da4fc24a2229cdba7e6e55dbb5dd56e8246"
HOST="https://permit.mee.gov.cn"
PAGE=HOST+"/perxxgkinfo/syssb/xkgg/xkgg!licenseInformation.action"
REGION=HOST+"/perxxgkinfo/syssb/xkgg/xkgg!getRegions.action"
UA="Mozilla/5.0 (compatible; R4National236PublicEnvironmentalEvidence/1.0)"
# The codes are confirmed industry classifications on the MEE portal.
# They are deliberately chosen high-relevance *screening* groups, not all industries.
CATEGORIES=[
  ("C26","化学原料和化学制品制造业","CHEMICAL"),
  ("C32","有色金属冶炼和压延加工业","NONFERROUS"),
  ("N7724","危险废物治理","HAZARDOUS_WASTE"),
  ("C25","石油、煤炭及其他燃料加工业","FUELS_COKE"),
  ("C30","非金属矿物制品业","NONMETALLIC"),
  ("C31","黑色金属冶炼和压延加工业","FERROUS"),
  ("D44","电力、热力生产和供应业","POWER_HEAT"),
  ("C22","造纸和纸制品业","PAPER")
]
MAX_PAGES_PER_CATEGORY=int(os.environ.get("MAX_PAGES_PER_CATEGORY","3"))
MAX_DETAIL_PER_CITY=int(os.environ.get("MAX_DETAIL_PER_CITY","10"))
WORKERS=min(5,max(1,int(os.environ.get("R4_WORKERS","4"))))
FAIL_RETRIES=2
RUN_UTC=datetime.now(timezone.utc).isoformat()
def safe_write(name, obj):
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def csv_write(name,rows,fields=None):
 OUT.mkdir(parents=True,exist_ok=True)
 fields=fields or list(rows[0]) if rows else (fields or [])
 with (OUT/name).open("w",encoding="utf-8-sig",newline="") as f:
  if not fields:return
  w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)
def parse_cands():
 with CAND.open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
 if len(rows)!=236 or len(set(r["code"] for r in rows))!=236:raise RuntimeError("INPUT_NOT_EXACTLY_236_UNIQUE")
 carry=Counter(r["R1_next_round_status"] for r in rows)
 climate_pending=sum(r["winter_status"]=="PENDING" or r["summer_status"]=="PENDING" for r in rows)
 if carry["CARRY_FORWARD"]!=178 or carry["PENDING_CONTINUE"]!=58 or climate_pending!=11:
  raise RuntimeError("R1_R2_R3_CARRY_SPLIT_CHANGED "+str((carry,climate_pending)))
 return rows
class HTMLRows(HTMLParser):
 def __init__(self):
  super().__init__();self.rows=[];self.row=None;self.cell=None;self.anchor=None;self.hidden={}
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=="tr":self.row={"cells":[],"links":[]}
  elif tag=="td" and self.row is not None:self.cell=""
  elif tag=="a" and self.row is not None:self.anchor={"href":a.get("href"),"text":""}
  elif tag=="input" and a.get("name") and a.get("value"):self.hidden[a["name"]]=a["value"]
 def handle_data(self,data):
  if self.cell is not None:self.cell+=" ".join(data.split())
  if self.anchor is not None:self.anchor["text"]+=" ".join(data.split())
 def handle_endtag(self,tag):
  if tag=="td" and self.cell is not None and self.row is not None:
   self.row["cells"].append(self.cell.strip());self.cell=None
  elif tag=="a" and self.anchor is not None and self.row is not None:
   self.row["links"].append(self.anchor);self.anchor=None
  elif tag=="tr" and self.row is not None:
   if self.row["cells"]:self.rows.append(self.row)
   self.row=None
def permit_rows(body):
 p=HTMLRows();p.feed(body)
 rows=[]
 for x in p.rows:
  cells=x["cells"]
  if len(cells)<8 or cells[2]=="许可证编号" or not re.match(r"^[A-Za-z0-9]{8,}",cells[2]):continue
  href=next((v.get("href") for v in x["links"] if v.get("href") and "dataid=" in v["href"]),None)
  if not href:continue
  rows.append({"province_name":cells[0],"city_name":cells[1],"permit_no":cells[2],
   "company":cells[3],"industry":cells[4],"validity":cells[5],"issued":cells[6],
   "management":cells[7],"detail_url":urllib.parse.urljoin(HOST,href)})
 pages=re.findall(r"共\s*([\d,]+)\s*页",body)
 count=int(pages[-1].replace(",","")) if pages else None
 return rows,count,p.hidden
def make_client():
 jar=http.cookiejar.CookieJar()
 opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
 def request(url,data=None,timeout=45):
  payload=urllib.parse.urlencode(data).encode("utf-8") if data is not None else None
  headers={"User-Agent":UA,"Accept":"text/html,application/json,*/*","Accept-Language":"zh-CN,zh;q=0.9",
           "Referer":PAGE}
  if payload is not None:
   headers["Content-Type"]="application/x-www-form-urlencoded; charset=UTF-8";headers["Origin"]=HOST
  last=None
  for attempt in range(FAIL_RETRIES+1):
   try:
    with opener.open(urllib.request.Request(url,data=payload,headers=headers),timeout=timeout) as response:
     b=response.read(8_000_000)
     if len(b)<20:raise RuntimeError("RESPONSE_TOO_SHORT "+str(len(b)))
     # Low-volume delay for public portal.
     time.sleep(0.12)
     return b.decode("utf-8","replace")
   except Exception as exc:
    last=repr(exc)
    if attempt<FAIL_RETRIES:time.sleep(1.5*(attempt+1))
  raise RuntimeError("PUBLIC_READ_ERROR "+str(last))
 return request
def get_json(body):
 body=body.lstrip("\ufeff").strip()
 if body.startswith("/**/"):body=body[4:].strip()
 return json.loads(body)
def region_map():
 req=make_client()
 req(PAGE)
 provinces=get_json(req(REGION,{"parentCode":"000000000000"}))["regions"]
 prov={x["regioncode"][:2]:x for x in provinces}
 out={}
 for pcode, pobj in prov.items():
  try:
   cities=get_json(req(REGION,{"parentCode":pobj["regioncode"]}))["regions"]
   out[pcode]={"province":pobj,"cities":cities}
  except Exception as e:
   out[pcode]={"province":pobj,"cities":[],"error":repr(e)}
 return out
def get_form(req):
 body=req(PAGE)
 parser=HTMLRows();parser.feed(body)
 return parser.hidden.get("tempReportKey","")
def query(req,province_code,city_code,category_id,category_label,page,token):
 form={"page.pageNo":str(page),"page.orderBy":"","page.order":"",
  "tempReportKey":token,"registerentername":"","xkznum":"",
  "treadname":category_label,"treadcode":category_id,
  "publishtime":"","province":province_code,"city":city_code or "","management":""}
 return permit_rows(req(PAGE,form))
def run_city(group,region):
 result={"city_group":group["city_group"],"candidate_codes":group["codes"],
         "candidate_names":group["names"],"province_code":group["province_code"],
         "queried_city_name":"","query_level":"CITY","category_results":[],"permit_rows":[],"errors":[]}
 province=region.get(group["province_code"])
 if not province:
  result["errors"].append("PROVINCE_CODE_NOT_RESOLVED")
  result["status"]="PENDING_MAPPING";return result
 p=province["province"]
 city=next((x for x in province["cities"] if x["regioncode"][:4]==group["city_group"]),None)
 if city is None:
  result["status"]="PENDING_CITY_MAPPING"
  result["errors"].append("CITY_CODE_NOT_RESOLVED_NO_BROAD_PROVINCE_SUBSTITUTION")
  return result
 result["queried_city_name"]=city["regionname"]
 req=make_client()
 try:token=get_form(req)
 except Exception as e:
  result["status"]="PENDING_PUBLIC_ENDPOINT";result["errors"].append(repr(e));return result
 seen={}
 for cid,label,family in CATEGORIES:
  record={"industry_code":cid,"label":label,"family":family,"pages_reported":None,
          "pages_fetched":0,"returned_rows":0,"complete":False,
          "query_status":"PENDING","errors":[]}
  try:
   first, pagecount,hidden=query(req,p["regioncode"],city["regioncode"],cid,label,1,token)
   record["pages_reported"]=pagecount
   allrows=list(first);record["pages_fetched"]=1
   if pagecount is None:
    record["query_status"]="PENDING_PAGINATION_UNVERIFIED"
   elif pagecount<=MAX_PAGES_PER_CATEGORY:
    record["query_status"]="COMPLETE_PAGES_REQUESTED"
   else:
    record["query_status"]="TRUNCATED_MAX_PAGES"
   upper=min(MAX_PAGES_PER_CATEGORY,max(1,pagecount or 1))
   for page in range(2,upper+1):
    try:
     more,n,hidden=query(req,p["regioncode"],city["regioncode"],cid,label,page,token)
     allrows+=more;record["pages_fetched"]+=1
    except Exception as e:
     record["errors"].append("PAGE_"+str(page)+":"+repr(e))
     record["query_status"]="PARTIAL_PAGE_REQUEST_FAILED";break
   record["returned_rows"]=len(allrows)
   record["complete"]=pagecount is not None and record["pages_fetched"]>=max(1,pagecount) and not record["errors"]
   # Industry family filter is verified for C3211/N7724 on the portal, but
   # broad parent codes require independent exact taxonomy validation.
   record["classification_scope"]="PORTAL_CATEGORY_QUERY_NOT_COMPLETE_CITY_INVENTORY"
   for x in allrows:
    key=x["permit_no"]
    if key not in seen:
     x.update({"query_city_group":group["city_group"],"query_city_name":city["regionname"],
       "query_province_code":group["province_code"],"matched_industry_query_codes":[]})
     seen[key]=x
    if cid not in seen[key]["matched_industry_query_codes"]:seen[key]["matched_industry_query_codes"].append(cid)
  except Exception as e:
   record["query_status"]="PENDING_QUERY_FAILED";record["errors"].append(repr(e))
  result["category_results"].append(record)
 result["permit_rows"]=list(seen.values())
 result["status"]="QUERIED_WITH_PARTIAL_OR_COMPLETE_CATEGORY_RESULTS" if any(x["pages_fetched"] for x in result["category_results"]) else "PENDING_ALL_QUERIES_FAILED"
 print("CITY_DONE",group["city_group"],result["queried_city_name"],"permits",len(seen),"scopes",Counter(x["query_status"] for x in result["category_results"]),flush=True)
 return result
def geoms():
 req=urllib.request.Request(GEO_URL,headers={"User-Agent":UA})
 with urllib.request.urlopen(req,timeout=90) as r:b=r.read()
 actual=hashlib.sha256(b).hexdigest()
 if actual!=GEO_SHA:raise RuntimeError("GEO_HASH_MISMATCH_"+actual)
 data=json.loads(b.decode("utf-8"))
 areas={}
 for feat in data.get("features",[]):
  props=feat.get("properties") or {};code=str(props.get("adcode") or "")
  if len(code)==6 and feat.get("geometry"):areas[code]={"name":props.get("name"),"geometry":shape(feat["geometry"])}
 return areas
def detail_one(x):
 req=make_client()
 try:
  body=req(x["detail_url"],timeout=45)
  lon=re.search(r'id="longitude"\s+value="([^"]+)"',body)
  lat=re.search(r'id="latitude"\s+value="([^"]+)"',body)
  text_content=re.sub(r"<[^>]*>"," ",body)
  text_content=html.unescape(re.sub(r"\s+"," ",text_content))
  def field(label,until):
   m=re.search(re.escape(label)+r"\s*(.*?)\s*"+re.escape(until),text_content)
   return m.group(1).strip() if m else ""
  return {**x,
   "facility_lon":float(lon.group(1)) if lon else None,
   "facility_lat":float(lat.group(1)) if lat else None,
   "plant_address":field("生产经营场所地址：","行业类别："),
   "plant_industry":field("行业类别：","所在地区："),
   "admin_region":field("所在地区：","发证机关："),
   "air_pollutant_list":field("大气主要污染物种类：","大气污染物排放规律："),
   "water_pollutant_list":field("废水主要污染物种类：","废水污染物排放规律："),
   "detail_status":"PUBLIC_DETAIL_FETCHED","error":""}
 except Exception as e:return {**x,"facility_lon":None,"facility_lat":None,"detail_status":"PENDING_DETAIL_FETCH","error":repr(e)}
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 candidates=parse_cands()
 grouped=defaultdict(list)
 for r in candidates:grouped[r["code"][:4]].append(r)
 groups=[{"city_group":g,"codes":[r["code"] for r in rs],"names":[r["name"] for r in rs],"province_code":g[:2]} for g,rs in sorted(grouped.items())]
 if len(groups)!=61 or len(set(r["code"][:2] for r in candidates))!=13:raise RuntimeError("NATIONAL_GROUP_MEMBERSHIP_CHANGED")
 print("NATIONAL_SCOPE",json.dumps({"candidates":236,"city_groups":len(groups),"provinces":13,"categories":len(CATEGORIES)},ensure_ascii=False),flush=True)
 regions=region_map()
 all_city=[]
 with ThreadPoolExecutor(max_workers=WORKERS) as ex:
  futs={ex.submit(run_city,g,regions):g for g in groups}
  for f in as_completed(futs):
   g=futs[f]
   try:r=f.result()
   except Exception as e:r={"city_group":g["city_group"],"candidate_codes":g["codes"],"status":"PENDING_WORKER_ERROR","errors":[repr(e)],"category_results":[],"permit_rows":[]}
   all_city.append(r)
 # Stage 1 immutable city query coverage table, even if later geospatial detail fails.
 all_city.sort(key=lambda x:x["city_group"])
 category_rows=[]
 all_permits={}
 for city in all_city:
  for r in city.get("category_results",[]):
   category_rows.append({"city_group":city["city_group"],"city_name":city.get("queried_city_name",""),
    "candidate_codes":";".join(city["candidate_codes"]),**r,"errors":";".join(r.get("errors",[]))})
  for p in city.get("permit_rows",[]):
   if p["permit_no"] not in all_permits:all_permits[p["permit_no"]]=p
 csv_write("NATIONAL_236_PERMIT_CITY_INDUSTRY_COVERAGE.csv",category_rows)
 # Select a small number of high-relevance public detail pages per city group.
 # Not a complete emitter inventory; company coordinates must be independently verified.
 selected=[]
 for city in all_city:
  candidates_in_city=city.get("permit_rows",[])
  priority=lambda x:(0 if ("重点管理" in x.get("management","")) else 1,
    0 if any(t in x.get("industry","")+x.get("company","") for t in
      ("危险废物","有色金属","铜冶炼","铅","锌","化工","化学","煤焦","冶炼","水泥")) else 1,
    x.get("permit_no",""))
  selected.extend(sorted(candidates_in_city,key=priority)[:MAX_DETAIL_PER_CITY])
 # Avoid duplicate lookup for licensing id across different industry query classes.
 unique={p["permit_no"]:p for p in selected}
 areas=geoms()
 candidate_areas={r["code"]:areas.get(r["code"]) for r in candidates}
 details=[]
 with ThreadPoolExecutor(max_workers=WORKERS) as ex:
  for f in as_completed([ex.submit(detail_one,p) for p in unique.values()]):
   details.append(f.result())
 detail_per_county=defaultdict(list)
 for p in details:
  lon,lat=p.get("facility_lon"),p.get("facility_lat")
  if lon is None or lat is None:
   p["county_point_match_status"]="PENDING_COORDINATES";p["candidate_code"]=""
   continue
  pt=Point(lon,lat);matched=[]
  for code,g in candidate_areas.items():
   if g and g["name"]==next(r["name"] for r in candidates if r["code"]==code) and g["geometry"].covers(pt):matched.append(code)
  p["candidate_code"]=matched[0] if len(matched)==1 else ""
  p["county_point_match_status"]="PROVISIONAL_EXACT_COUNTY_POLYGON" if len(matched)==1 else "OUTSIDE_CANDIDATES_OR_BOUNDARY_PENDING"
  if p["candidate_code"]:detail_per_county[p["candidate_code"]].append(p)
 codes_with_geom=sum(1 for g in candidate_areas.values() if g)
 rows=[]
 city_index={x["city_group"]:x for x in all_city}
 for c in candidates:
  group=c["code"][:4];city=city_index[group]; hits=detail_per_county.get(c["code"],[])
  cats=city.get("category_results",[])
  failed=sum(not x.get("complete",False) for x in cats)
  rows.append({"code":c["code"],"name":c["name"],
   "R1_status":c["R1_next_round_status"],"winter_status":c["winter_status"],"summer_status":c["summer_status"],
   "R4_included":"YES","permit_query_city_group":group,
   "permit_query_city_name":city.get("queried_city_name",""),
   "permit_query_city_status":city["status"],
   "permit_category_queries_attempted":len(cats),
   "permit_category_queries_complete":sum(x.get("complete",False) for x in cats),
   "permit_category_queries_partial_or_pending":failed,
   "city_queried_permit_count":len(city.get("permit_rows",[])),
   "geospatial_county_polygon_status":"PROVISIONAL_MATCH" if candidate_areas[c["code"]] else "PENDING_GEOMETRY",
   "facility_details_matched_to_candidate":len(hits),
   "facility_names":"；".join(p["company"] for p in hits),
   "permit_licenses":"；".join(p["permit_no"] for p in hits),
   "industry_names":"；".join(sorted(set(p.get("plant_industry") or p["industry"] for p in hits))),
   "air_pollutant_lists":"；".join(sorted(set(p.get("air_pollutant_list","") for p in hits if p.get("air_pollutant_list")))),
   "water_pollutant_lists":"；".join(sorted(set(p.get("water_pollutant_list","") for p in hits if p.get("water_pollutant_list")))),
   "industrial_risk_assessment":"SCREENING_REQUIRES_RESIDENTIAL_OVERLAY" if hits else "NO_MATCH_IN_LIMITED_SAMPLE_NOT_EVIDENCE_OF_ABSENCE",
   "formal_R4_exclusion":"NO",
   "previous_pending_still_in_R4":"YES" if c["R1_next_round_status"]=="PENDING_CONTINUE" else "NO",
   "evidence_scope":"Official public city-level permits, industry-filtered and capped at "+str(MAX_PAGES_PER_CATEGORY)+" pages per category; at most "+str(MAX_DETAIL_PER_CITY)+" sampled details per city; not complete enterprise census or confirmed residential exposure."})
 csv_write("NATIONAL_236_PERMIT_INDUSTRIAL_CANDIDATE_MATRIX.csv",rows)
 facility_fields=["candidate_code","company","permit_no","query_city_group","query_city_name","industry","plant_industry","plant_address","admin_region","facility_lon","facility_lat","management","issued","validity","air_pollutant_list","water_pollutant_list","detail_status","county_point_match_status","error","detail_url"]
 csv_write("NATIONAL_236_PERMIT_FACILITY_DETAIL_SAMPLE.csv",details,facility_fields)
 sumry={"schema":"RETIREMENT_R4_236_OFFICIAL_PERMIT_NATIONAL_BATCH_V1",
  "created_at_utc":RUN_UTC,"completed_at_utc":datetime.now(timezone.utc).isoformat(),
  "candidate_count":236,"provinces":13,"municipal_code_groups":61,
  "city_groups_with_queries":sum(bool(x.get("category_results")) for x in all_city),
  "city_groups_pending_mapping":sum(x["status"]=="PENDING_CITY_MAPPING" for x in all_city),
  "city_groups_other_pending":sum(x["status"] in ("PENDING_PUBLIC_ENDPOINT","PENDING_WORKER_ERROR","PENDING_ALL_QUERIES_FAILED","PENDING_MAPPING") for x in all_city),
  "industry_filter_codes":[x[0] for x in CATEGORIES],
  "industry_queries_completed":sum(x.get("complete",False) for x in category_rows),
  "industry_queries_partial_or_pending":sum(not x.get("complete",False) for x in category_rows),
  "industry_page_cap_per_city_category":MAX_PAGES_PER_CATEGORY,
  "detail_sample_cap_per_city":MAX_DETAIL_PER_CITY,
  "city_level_distinct_licences_returned":len(all_permits),
  "detail_page_requests":len(details),
  "detail_pages_success":sum(x["detail_status"]=="PUBLIC_DETAIL_FETCHED" for x in details),
  "facility_sample_with_candidate_polygon_match":sum(bool(x.get("candidate_code")) for x in details),
  "candidate_units_with_sampled_facilities":sum(bool(x["facility_details_matched_to_candidate"]) for x in rows),
  "candidate_units_with_provisional_geometry":sum(bool(candidate_areas[c["code"]]) for c in candidates),
  "candidate_units_pending_geometry":236-codes_with_geom,
  "formal_R4_exclusions":0,"formal_grade_changes":0,"candidate_units_remaining":236,
  "run_notes":["All 236 county candidates remain in R4 regardless of previous 47/11 pending split.",
   "Permit category retrieval is city-level; absence in sample does not establish lack of local industrial sources.",
   "Truncated categories are explicit pending, not complete.",
   "Permit coordinates are facility points; neither permit holding nor a pollutant list proves residential exposure, actual discharge magnitude or violation.",
   "Only direct location-matched facilities are attributed to candidate counties; no city-level records are mislabeled county-specific.",
   "No automated hard exclusions or grading is permitted from this batch."],
  "sources":{"official_public_portal":PAGE,"public_region_api":REGION,"candidate_file":str(CAND),"candidate_boundary":GEO_URL,"candidate_boundary_sha256":GEO_SHA},
  "city_status":[{"city_group":x["city_group"],"city_name":x.get("queried_city_name",""),
     "candidate_units":len(x["candidate_codes"]),"status":x["status"],
     "record_sample":len(x.get("permit_rows",[])),"errors":x.get("errors",[])} for x in all_city]}
 safe_write("NATIONAL_236_PERMIT_BATCH_SUMMARY.json",sumry)
 print("NATIONAL_R4_PERMIT_FINAL",json.dumps({k:sumry[k] for k in
   ["candidate_count","city_groups_with_queries","city_groups_pending_mapping","industry_queries_completed","industry_queries_partial_or_pending","city_level_distinct_licences_returned","detail_pages_success","facility_sample_with_candidate_polygon_match","candidate_units_with_sampled_facilities","candidate_units_remaining"]},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
