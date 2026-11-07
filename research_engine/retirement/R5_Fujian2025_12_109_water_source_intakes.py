#!/usr/bin/env python3
"""Extract actual December 2025 109 official Fujian centralized drinking water
SOURCE intake monitoring records with pass/fail. These are RAW WATER
before treatment, never household tap water, never zero contaminants.

Link exact 2025 provisional county code ONLY for county/county-city named
administrative units. Nine prefecture city rows remain city-level context.
Missing county source record NOT unsafe and NOT screening exclusion.
"""
import collections,csv,datetime,hashlib,json,pathlib,re,urllib.request
from bs4 import BeautifulSoup
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
URL="https://sthjt.fujian.gov.cn/zwgk/sjfb/hjsj/yyssysz/202601/t20260126_7085249.htm"
PRIOR=ROOT/"status/national_R4_official_Fujian2025_county_PM25_2847.csv"
def sha(b):return hashlib.sha256(b).hexdigest()
def clean(t):return re.sub(r"\s+","",t).replace("\u3000","")
req=urllib.request.Request(URL,headers={"User-Agent":"Retirement-Fujian-2025-Water-Source-Site-QA/1.0"})
with urllib.request.urlopen(req,timeout=100) as r:raw=r.read(7_000_000)
soup=BeautifulSoup(raw.decode("utf-8","replace"),"html.parser")
text=soup.get_text(" ",strip=True)
if not("2025年12月" in text and "109个" in text and "达标" in text):
 raise RuntimeError("Official month and 109 source location validation failed")
entries=[]
for tb in soup.find_all("table"):
 for tr in tb.find_all("tr"):
  cs=[clean(t.get_text(" ",strip=True)) for t in tr.find_all(["td","th"],recursive=False)]
  if len(cs)>=7 and cs[0].isdigit() and cs[1]=="福建省" and cs[6] in ("达标","不达标","超标"):
   entries.append({"index":int(cs[0]),"province":cs[1],"admin_name":cs[2],
    "intake_source_name":cs[3],"source_type":cs[4],"waterbody_type":cs[5],
    "raw_water_met_classIII_standard":cs[6]=="达标",
    "source_status_original":cs[6],"exceedance":cs[7] if len(cs)>=8 else "",
    "sample_month":"2025-12","source_URL":URL})
if len(entries)!=109 or len(set(x["index"] for x in entries))!=109:
 raise RuntimeError("Source table should return exactly 109 intake samples, got "+str(len(entries)))
with PRIOR.open(encoding="utf-8-sig",newline="") as f:
 reader=csv.DictReader(f);fields=list(reader.fieldnames);rows=list(reader)
if len(rows)!=2847:raise RuntimeError("Nationwide 2847 R4 ledger missing")
index=collections.defaultdict(list)
for row in rows:
 if row["candidate_code"].startswith("35"):index[row["candidate_name"]].append(row)
matched=[];city_context=[];unresolved=[]
bycode=collections.defaultdict(list)
for site in entries:
 name=site["admin_name"];matches=index.get(name) or []
 if len(matches)==1:
  id=matches[0]["candidate_code"]
  site["candidate_code"]=id;site["link_quality"]="EXACT_COUNTY_NAME_FJ35_2025"
  matched.append(site);bycode[id].append(site)
 elif name in ["福州市","厦门市","漳州市","泉州市","三明市","莆田市","南平市","龙岩市","宁德市","平潭区"]:
  site["candidate_code"]=None;site["link_quality"]="PREFECTURE_OR_SPECIAL_CITY_CONTEXT_ONLY"
  city_context.append(site)
 else:
  site["candidate_code"]=None;site["link_quality"]="NAME_UNMATCHED_NO_FALSE_JOIN"
  unresolved.append(site)
if len(matched)+len(city_context)+len(unresolved)!=109:raise RuntimeError("Sites not conserved")
fields2=fields+["R5_Fujian2025_12_official_raw_source_site_count",
 "R5_Fujian2025_12_raw_source_all_met_classIII","R5_Fujian2025_12_raw_source_names",
 "R5_Fujian2025_12_source_url","R5_Fujian2025_12_household_tap_verified"]
new=0
for code,sources in bycode.items():
 row=next(r for r in rows if r["candidate_code"]==code)
 row["R5_Fujian2025_12_official_raw_source_site_count"]=len(sources)
 row["R5_Fujian2025_12_raw_source_all_met_classIII"]="TRUE" if all(s["raw_water_met_classIII_standard"] for s in sources) else "FALSE"
 row["R5_Fujian2025_12_raw_source_names"]=";".join(s["intake_source_name"] for s in sources)
 row["R5_Fujian2025_12_source_url"]=URL
 row["R5_Fujian2025_12_household_tap_verified"]="FALSE"
 if row["R5_status"]=="NOT_SCREENED":
  row["R5_status"]="FUJIAN_2025_12_OFFICIAL_SOURCE_INTAKE_PASSFAIL_ONLY"
  row["R5_evidence_scope"]="SOURCE_RAW_WATER_NOT_TREATED_OR_RESIDENTIAL_ENDPOINT"
  row["R5_missing_parameters"]="TREATED_WATER_QUALITY;HOUSEHOLD_TAP_ENDPOINT;INDUSTRIAL_LEGACY_POLLUTION;LONG_HISTORY"
  row["last_completed_round"]="R5_FJ_2025_12_SOURCE_MONITORING_PARTIAL"
  row["cascade_status"]="ACTIVE_PENDING"
  new+=1
total=sum(r["R5_status"]!="NOT_SCREENED" for r in rows)
if any(r["confirmed_exit_round"] for r in rows) or any(str(r["valid_county_screening"]).lower()=="true" for r in rows):
 raise RuntimeError("R5 accidental formal exclusions")
nat=OUT/"national_R5_Fujian2025_12_109_official_source_intakes_2847.csv"
with nat.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=fields2);wr.writeheader();wr.writerows(rows)
csvout=OUT/"Fujian2025_12_109_official_intake_sources.csv"
with csvout.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=list(entries[0].keys()));wr.writeheader();wr.writerows(entries)
report={"schema":"RET_R5_FUJIAN2025_12_109_GOV_RAW_WATER_INTAKE_SITES_V1",
 "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_URL":URL,"source_publisher":"福建省生态环境厅",
 "source_release_date":"2026-01-23","sampling_month":"2025-12",
 "source_html_sha256":sha(raw),"source_bytes":len(raw),
 "all_official_source_intake_sites":109,
 "source_raw_water_sites_meeting_classIII":sum(x["raw_water_met_classIII_standard"] for x in entries),
 "sites_exact_county_code_matched":len(matched),
 "sites_prefecture_city_context_only":len(city_context),
 "sites_unresolved_no_false_join":len(unresolved),
 "distinct_actual_county_code_source_evidence":len(bycode),
 "new_R5_partial_source_water_counties":new,
 "R5_total_partial_counties":total,"R5_not_scanned":2847-total,
 "official_household_tap_endpoints_verified":0,
 "source_of_water_is_NOT_finished_treated_water":True,
 "Fujian_2025_12_source_intakes":entries,"source_unmatched_sites":unresolved,
 "new_R5_county_code_ids":sorted([k for k,ss in bycode.items() if ss]),
 "source_national_R4_sha256":sha(PRIOR.read_bytes()),
 "national_R5_csv_sha256":sha(nat.read_bytes()),
 "intake_sites_csv_sha256":sha(csvout.read_bytes()),
 "formal_valid_county_screenings":0,"confirmed_county_exclusions":0,
 "source_semantics":"Raw untreated water sampled at intake or nearby source within about 100m, classIII pass/fail; NOT bottled water, treatment plant output or tap water; 109/109 pass does not prove zero heavy metal or residential safety."}
(OUT/"Fujian2025_12_R5_official_raw_water_source_evidence.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["all_official_source_intake_sites",
 "source_raw_water_sites_meeting_classIII","sites_exact_county_code_matched",
 "sites_prefecture_city_context_only","sites_unresolved_no_false_join",
 "distinct_actual_county_code_source_evidence","new_R5_partial_source_water_counties",
 "R5_total_partial_counties","R5_not_scanned"]},ensure_ascii=False),flush=True)
