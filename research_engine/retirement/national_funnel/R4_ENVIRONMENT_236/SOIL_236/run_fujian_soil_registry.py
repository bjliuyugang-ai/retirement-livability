#!/usr/bin/env python3
"""Extract 2026-06 Fujian official active soil risk-control/restoration list.
First regional source in a 236-row nationwide R4 soil evidence matrix.
A listed contaminated site is a site-specific avoidance signal, NEVER a
county-wide R4 exclusion. Missing site match is NOT a clean-soil finding.
"""
from __future__ import annotations
import csv,hashlib,json,pathlib,re,urllib.request
from collections import Counter,defaultdict
from datetime import datetime,timezone
from bs4 import BeautifulSoup

ROOT=pathlib.Path("research_engine/retirement")
BASE=ROOT/"national_funnel/R4_ENVIRONMENT_236/SOIL_236"
OUT=BASE/"output"
CAN=ROOT/"national_funnel/FINAL_FILTER/runs/42453646573/FINAL_CARRY_FORWARD_AFTER_R1_R2_R3.csv"
URL="https://sthjt.fujian.gov.cn/zwgk/ywxx/wrfz/202607/t20260723_7191457.htm"
UA="Mozilla/5.0 (compatible; R4National236EnvironmentalEvidence/1.0)"
def save_csv(path,rows,fields=None):
 path.parent.mkdir(parents=True,exist_ok=True)
 if not rows and not fields:return
 if fields is None:fields=list(rows[0])
 with path.open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 with CAN.open(encoding="utf-8-sig",newline="") as f:
  candidates=list(csv.DictReader(f))
 if len(candidates)!=236 or len({x["code"] for x in candidates})!=236:raise RuntimeError("CANONICAL_236_NOT_FOUND")
 fujian=[x for x in candidates if x["code"].startswith("35")]
 if len(fujian)!=26:raise RuntimeError("FUJIAN_26_EXPECTED_GOT_"+str(len(fujian)))
 req=urllib.request.Request(URL,headers={"User-Agent":UA,"Accept-Language":"zh-CN,zh;q=0.9"})
 with urllib.request.urlopen(req,timeout=90) as resp:
  raw=resp.read(2_000_000)
  ctype=resp.headers.get("Content-Type","")
 # Trust source's UTF-8 or use page header; require decoded Chinese labels.
 data=raw.decode("utf-8","replace")
 if "福建省建设用地土壤污染风险管控和修复名录" not in data:raise RuntimeError("PAGE_CONTENT_NOT_EXPECTED")
 soup=BeautifulSoup(data,"html.parser")
 tables=soup.find_all("table")
 registries=[]
 for t in tables:
  tx=t.get_text(" ",strip=True)
  if "地块名称" not in tx:continue
  trs=t.find_all("tr")
  parsed=[]
  for tr in trs:
   cells=[re.sub(r"\s+"," ",cell.get_text(" ",strip=True)).strip() for cell in tr.find_all(["td","th"],recursive=False)]
   if cells and re.fullmatch(r"\d{1,3}",cells[0].strip()) and len(cells)>=5:
    parsed.append(cells)
  if parsed:registries.append({"html_pos":data.find(str(t)[:120]),"rows":parsed,"header":tx[:200]})
 # Depending on CMS table splitting, first registry table is active; next
 # registry is the removed-sites appendix. Neither can be mixed.
 if not registries:raise RuntimeError("ACTIVE_SOIL_SITE_TABLE_NOT_EXTRACTED")
 active=registries[0]["rows"]
 if len(active)<8:raise RuntimeError("ACTIVE_SOIL_SITE_SUSPICIOUSLY_SHORT "+str(len(active)))
 # Expected structure: index, site, city, address, four-boundary description,
 # area, owner, stage, goal, preparer, contractor, client, inclusion date, remarks.
 source=[]
 for cols in active:
  row={
   "index":cols[0],"site_name":cols[1] if len(cols)>1 else "",
   "city":cols[2] if len(cols)>2 else "",
   "address":cols[3] if len(cols)>3 else "",
   "boundary_description":cols[4] if len(cols)>4 else "",
   "area_m2":cols[5] if len(cols)>5 else "",
   "owner":cols[6] if len(cols)>6 else "",
   "risk_control_stage":cols[7] if len(cols)>7 else "",
   "remediation_goal":cols[8] if len(cols)>8 else "",
   "inclusion_date":cols[-2] if len(cols)>=12 else "",
   "source_url":URL,
   "source_date":"2026-07-21","registry_effective":"2026-06",
   "legal_site_effect":"LISTED_SITE_NOT_RESIDENTIAL_DEVELOPMENT_ELIGIBLE_UNTIL_REMOVED"
  }
  source.append(row)
 def matching_site(c,r):
  # Conservative explicit candidate county name in address/site string only.
  name=c["name"]
  name_short=re.sub(r"(区|县|市)$","",name)
  full=r["site_name"]+" "+r["address"]
  if (len(name_short)>=3 and name in full) or (len(name_short)>=3 and name_short in full):
   # Avoid common substring trap: e.g. "安宁" within unrelated names.
   return True
  return False
 matched=defaultdict(list)
 for site in source:
  matches=[c for c in fujian if matching_site(c,site)]
  site["matching_candidate_codes"]=";".join(c["code"] for c in matches)
  site["matching_candidate_names"]=";".join(c["name"] for c in matches)
  site["location_match_status"]="TEXTUAL_COUNTY_MATCH_PROVISIONAL" if len(matches)==1 else (
   "MULTIPLE_COUNTY_TEXT_MATCH_NEEDS_REVIEW" if len(matches)>1 else "NO_COUNTY_NAME_MATCH_NEEDS_LOCAL_GEOCODING")
  for c in matches:matched[c["code"]].append(site)
 matrix=[]
 for c in candidates:
  if c["code"].startswith("35"):
   hit=matched.get(c["code"],[])
   status="ACTIVE_OFFICIAL_SOIL_SITE_TEXT_MATCH_REQUIRES_POLYGON" if hit else "NO_MATCH_IN_ACTIVE_SOURCE_NOT_PROOF_OF_NO_SITES"
   evidence_status="FUJIAN_ACTIVE_REGISTRY_FETCHED_PROVISIONAL_TEXT_MATCH"
  else:
   hit=[];status="PENDING_PROVINCE_SOIL_ACTIVE_REGISTRY";evidence_status="PENDING_SOIL_SOURCE"
  matrix.append({
   "code":c["code"],"name":c["name"],"province_code":c["code"][:2],
   "R1_status":c["R1_next_round_status"],
   "official_soil_risk_registry_source_status":evidence_status,
   "active_soil_site_text_match_status":status,
   "active_soil_site_text_match_count":len(hit),
   "active_soil_site_names":"；".join(x["site_name"] for x in hit),
   "active_soil_site_addresses":"；".join(x["address"] for x in hit),
   "active_soil_site_remediation_stages":"；".join(x["risk_control_stage"] for x in hit),
   "soil_site_source_url":URL if c["code"].startswith("35") else "",
   "site_specific_avoidance":"PENDING_PRECISE_SITE_FOOTPRINT" if hit else "NOT_ESTABLISHED",
   "residential_site_distance_verified":"NO",
   "county_level_hard_exclusion":"NO",
   "next_action":"Geocode official listed land parcel, crosscheck site boundaries and actual residential locations; do not exclude county." if hit else "Fetch provincial active/removal soil registry, official parcel boundary and local contaminated site register; no match means pending."
  })
 save_csv(OUT/"NATIONAL_236_SOIL_CONTAMINATED_SITE_CANDIDATE_MATRIX.csv",matrix)
 save_csv(OUT/"FUJIAN_2026_06_SOIL_ACTIVE_SITES_OFFICIAL_SOURCE.csv",source)
 summary={
  "schema":"RETIREMENT_R4_NATIONAL_236_SOIL_SITE_REGISTRY_BATCH01",
  "created_at_utc":datetime.now(timezone.utc).isoformat(),
  "candidate_count":236,"source_province":"福建省","candidate_count_in_source_province":26,
  "source_url":URL,"source_date":"2026-07-21","registry_date":"2026-06",
  "page_sha256":hashlib.sha256(raw).hexdigest(),"page_bytes":len(raw),
  "html_tables_found":len(tables),"registry_tables_with_data":len(registries),
  "active_site_rows":len(source),"fujian_candidate_units_with_text_matched_sites":sum(bool(matched.get(c["code"])) for c in fujian),
  "fujian_candidate_units_without_matched_sites":sum(not matched.get(c["code"]) for c in fujian),
  "nonfujian_candidate_pending":210,
  "candidate_matched_sites":[{"code":c["code"],"name":c["name"],"sites":[{"name":x["site_name"],"address":x["address"],"stage":x["risk_control_stage"]} for x in matched[c["code"]]]} for c in fujian if matched.get(c["code"])],
  "unmatched_sites":sum(x["location_match_status"]=="NO_COUNTY_NAME_MATCH_NEEDS_LOCAL_GEOCODING" for x in source),
  "formal_R4_exclusions":0,"candidate_count_remaining":236,
  "site_level_rule":"Active restricted parcel must not be treated as eligible for residential development until officially removed. This is parcel-specific, not automatic removal of a county or other safely located residential areas.",
  "source_scope_limit":["Only Fujian active 2026-06 registry is integrated in this batch. All other provinces pending.",
    "Text match is preliminary; multiple or absent county string is not evidence of no sites.",
    "Source has separate removed-site appendix and must not be mixed with active list.",
    "No address geocoding/site-candidate residential polygon overlay has yet been completed."]}
 (OUT/"NATIONAL_236_SOIL_BATCH01_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("SOIL_BATCH01",json.dumps({k:summary[k] for k in ("candidate_count","active_site_rows","fujian_candidate_units_with_text_matched_sites","fujian_candidate_units_without_matched_sites","unmatched_sites","formal_R4_exclusions")},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
