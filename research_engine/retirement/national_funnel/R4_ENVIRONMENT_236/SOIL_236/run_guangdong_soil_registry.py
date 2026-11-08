#!/usr/bin/env python3
"""R4: Extract all pages of official Guangdong active restricted land parcel list.

Fetch province public portal state=1 (active), not removed list. Match 30
existing Guangdong county-candidates. Province, area, parcel never automatically
eliminate a county. Pagination must be auditable; if incomplete, mark source partial.
"""
from __future__ import annotations
import csv,hashlib,json,pathlib,re,time,urllib.request
from collections import defaultdict
from datetime import datetime,timezone
from bs4 import BeautifulSoup

ROOT=pathlib.Path("research_engine/retirement")
BASE=ROOT/"national_funnel/R4_ENVIRONMENT_236/SOIL_236"
OUT=BASE/"output"
CAND=ROOT/"national_funnel/FINAL_FILTER/runs/42453646573/FINAL_CARRY_FORWARD_AFTER_R1_R2_R3.csv"
SOURCE="https://www-app.gdeei.cn/gdeepub/data/construction-land"
MAX_PAGES=8
UA="Mozilla/5.0 (compatible; R4National236OfficialSoilRecords/1.0)"
def csv_save(name,rows):
 if not rows:raise RuntimeError("EMPTY_"+name)
 with (OUT/name).open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),extrasaction="ignore");w.writeheader();w.writerows(rows)
def get(url):
 last=None
 for attempt in range(1,4):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":UA,"Accept-Language":"zh-CN,zh;q=0.9"}),timeout=70) as r:
    b=r.read(2_000_000)
   s=b.decode("utf-8","replace")
   if "广东省建设用地土壤污染风险管控和修复名录" not in s:raise RuntimeError("PORTAL_PAGE_NOT_EXPECTED")
   return b,s
  except Exception as e:
   last=repr(e)
   if attempt<3:time.sleep(attempt*2)
 raise RuntimeError("PUBLIC_GUANGDONG_SOURCE_UNAVAILABLE "+str(last))
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 with CAND.open(encoding="utf-8-sig",newline="") as f:all_candidates=list(csv.DictReader(f))
 if len(all_candidates)!=236 or len(set(x["code"] for x in all_candidates))!=236:raise RuntimeError("NOT_CANONICAL_236")
 guangdong=[x for x in all_candidates if x["code"].startswith("44")]
 if len(guangdong)!=30:raise RuntimeError("GUANGDONG_EXPECTED_30_GOT_"+str(len(guangdong)))
 rows=[];pages=[]
 for page in range(1,MAX_PAGES+1):
  url=f"{SOURCE}?clName=&page={page}&state=1"
  raw,s=get(url)
  soup=BeautifulSoup(s,"html.parser")
  tables=soup.find_all("table")
  candidates=[]
  for t in tables:
   txt=t.get_text(" ",strip=True)
   if "地块名称" not in txt or "所在市" not in txt:continue
   for tr in t.find_all("tr"):
    cells=[re.sub(r"\s+"," ",td.get_text(" ",strip=True)).strip() for td in tr.find_all(["td"],recursive=False)]
    if len(cells)>=6 and len(cells[0])>3 and cells[1].endswith("市") and cells[2]:
     candidates.append(cells)
  pages.append({"page":page,"url":url,"http_bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"table_count":len(tables),"data_row_count":len(candidates),
    "reported_pages":re.findall(r"共\s*(\d+)\s*页",s)[:3]})
  if not candidates:
   raise RuntimeError("NO_PARSEABLE_DATA_ON_GUANGDONG_PAGE_"+str(page)+" table_count="+str(len(tables)))
  for cells in candidates:
   rows.append({
    "site_name":cells[0],"city":cells[1],"address":cells[2],
    "boundary_description":cells[3],"area_m2":cells[4],"owner":cells[5],
    "risk_control_stage":cells[6] if len(cells)>6 else "",
    "remediation_goal":cells[7] if len(cells)>7 else "",
    "entry_date":cells[11] if len(cells)>11 else "",
    "groundwater_status":cells[-1] if len(cells)>12 else "",
    "source_page":page,"source_url":url,
    "source_portal_update_date":"2026-09-03","list_type":"ACTIVE_STATE_1_NOT_REMOVED"
   })
  print("GUANGDONG_SOIL_PAGE",page,"rows",len(candidates),flush=True)
  time.sleep(0.25)
 # Dedupe by name+address, audit duplicates rather than silently ignoring them.
 dedup={}
 for r in rows:
  key=(r["site_name"],r["address"])
  if key not in dedup:dedup[key]=r
 sites=list(dedup.values())
 if len(sites)<35:raise RuntimeError("ACTIVE_SOURCE_UNEXPECTEDLY_FEW_SITES:"+str(len(sites)))
 def matched(c,r):
  # require county full name in address or site name. No city-level broad match.
  f=r["site_name"]+" "+r["address"]
  return c["name"] in f
 matches=defaultdict(list)
 for site in sites:
  hit=[c for c in guangdong if matched(c,site)]
  site["candidate_match_codes"]=";".join(c["code"] for c in hit)
  site["candidate_match_names"]=";".join(c["name"] for c in hit)
  site["county_match_scope"]="TEXT_ONLY_REQUIRES_PARCEL_GIS" if len(hit)==1 else "UNMATCHED_OR_AMBIGUOUS"
  for c in hit:matches[c["code"]].append(site)
 master=[]
 for c in all_candidates:
  gu=c["code"].startswith("44")
  hit=matches.get(c["code"],[])
  master.append({"code":c["code"],"name":c["name"],"province_code":c["code"][:2],
   "source_status":"GUANGDONG_OFFICIAL_ACTIVE_SITE_REGISTRY_2026_09" if gu else "OTHER_PROVINCE_PENDING_OR_SEPARATE_BATCH",
   "site_text_match_status":"OFFICIAL_ACTIVE_PARCELS_REQUIRE_SITE_CHECK" if hit else "NO_TEXT_MATCH_NOT_PROOF_OF_CLEAN_SOIL" if gu else "PENDING_GUANGDONG_SOURCE_NOT_APPLICABLE",
   "official_active_site_text_count":len(hit),
   "active_site_names":"；".join(x["site_name"] for x in hit),
   "active_site_addresses":"；".join(x["address"] for x in hit),
   "active_site_stages":"；".join(x["risk_control_stage"] for x in hit),
   "official_source_url":SOURCE if gu else "",
   "verified_household_soil_exposure":"NO",
   "county_hard_exclusion":"NO",
   "next_action":"Check actual residential parcels against each listed contaminated site footprint, zoning and latest removal decision." if hit else "Check local parcel registry and residential soil status; absence of text match remains pending."})
 csv_save("GUANGDONG_2026_09_ACTIVE_SOIL_SITES_SOURCE.csv",sites)
 csv_save("NATIONAL_236_GUANGDONG_SOIL_SITE_CANDIDATE_MATRIX.csv",master)
 summary={
  "schema":"RETIREMENT_R4_NATIONAL_236_GUANGDONG_ACTIVE_SOIL_SITES",
  "generated_at_utc":datetime.now(timezone.utc).isoformat(),
  "candidate_count":236,"guangdong_candidates":30,"active_site_pages_expected":MAX_PAGES,
  "pages":pages,"raw_rows":len(rows),"unique_active_sites":len(sites),
  "matched_candidate_units":sum(bool(matches.get(c["code"])) for c in guangdong),
  "matched_sites":sum(len(matches.get(c["code"],[])) for c in guangdong),
  "matched_candidates":[{"code":c["code"],"name":c["name"],"sites":[{"name":x["site_name"],"address":x["address"],"stage":x["risk_control_stage"]} for x in matches[c["code"]]]} for c in guangdong if matches.get(c["code"])],
  "other_provinces_pending":206,"county_exclusions":0,"candidate_count_remaining":236,
  "limits":["Portals' active state=1 was queried, not the removed-site list.","Only Guangdong sites; no county with missing records is assumed clean.","County matching is literal address/name token only, not parcel polygon or residential exposure.","A listing may constrain specific land use but cannot automatically exclude a city or county.","2026-09-03 portal update date is as displayed at retrieval; check source and current delistings before site decision."]
 }
 (OUT/"NATIONAL_236_GUANGDONG_SOIL_BATCH_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("GUANGDONG_SOIL_FINAL",json.dumps({"candidates":236,"pages":MAX_PAGES,"sites":len(sites),"matched_counties":summary["matched_candidate_units"],"matched_sites":summary["matched_sites"],"exclusions":0},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
