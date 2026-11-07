#!/usr/bin/env python3
"""R5 Fujian provincial environmental bureau monthly named drinking water
SOURCE water monitoring. Exact county code/name; never drinking tap/water supply.
Periods: actual 2025-06, 2025-12, 2026-09 monthly tables. Honest source
and publication date, named sampling intake, river/reservoir/groundwater and
assessment 达标/超标. No local home tap nor 2026 nationwide official county certification.
"""
import collections,csv,datetime,hashlib,io,json,pathlib,re,urllib.parse,urllib.request
from bs4 import BeautifulSoup
import pandas as pd
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
INDEX="https://sthjt.fujian.gov.cn/zwgk/sjfb/hjsj/yyssysz/"
CODEURL="https://raw.githubusercontent.com/yescallop/areacodes/master/data/2025.txt"
R4=ROOT/"status/national_R4_official_Fujian2025_county_PM25_2847.csv"
R4QA=ROOT/"status/Fujian2025_official_R4_county_air_evidence.json"
OLD=ROOT/"status/national_r5_tap_water_evidence.json"
PERIODS=["2025-06","2025-12","2026-09"]
def sha(b):return hashlib.sha256(b).hexdigest()
def req(url,limit=5_000_000):
 r=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; national-retirement-R5-water-data-QA/0.1)","Accept":"text/html,application/json,text/plain,*/*"})
 with urllib.request.urlopen(r,timeout=100) as resp:
  b=resp.read(limit+1);status=resp.status
 if len(b)>limit:raise RuntimeError("Over-size government HTML")
 return b,status
def norm(t):return re.sub(r"\s+","",str(t)).replace("\xa0","")
def matchperiod(text,yyyymm):
 ym=yyyymm.split("-")
 return bool(re.search(ym[0]+r"\s*年\s*0?"+str(int(ym[1]))+r"\s*月",text))
q=json.loads(R4QA.read_text(encoding="utf-8"))
if q["actual_county_source_records_2025_annual"]!=58 or q["formal_valid_county_screenings"]!=0 or sha(R4.read_bytes())!=q["national_R4_register_sha256"]:
 raise RuntimeError("R4 full 2847 predecessor changed")
with R4.open(encoding="utf-8-sig",newline="") as f:
 reader=csv.DictReader(f);fields=list(reader.fieldnames);rows=list(reader)
bycode={x["candidate_code"]:x for x in rows}
if len(rows)!=2847 or len(bycode)!=2847:raise RuntimeError("2847 national roster drift")
old=json.loads(OLD.read_text(encoding="utf-8"))
if old["R5_direct_evidence_counties"]!=1 or old["records"][0]["code"]!="532503":
 raise RuntimeError("Pre-existing Mengzi tap-site record not accounted")
code_raw,_=req(CODEURL,400_000)
cnames={}
for l in code_raw.decode("utf-8-sig").splitlines():
 m=re.fullmatch(r"([0-9]{6})\s+(.+)",l.strip())
 if m:cnames[m.group(1)]=m.group(2)
known={c:n for c,n in cnames.items() if c.startswith("35") and not c.endswith("00")}
index_raw,_=req(INDEX)
ix=BeautifulSoup(index_raw,"lxml")
found={}
for a in ix.select("a[href]"):
 text=norm(a.get_text(" ",strip=True));h=a.get("href","")
 for p in PERIODS:
  if matchperiod(text,p) and "饮用水" in text and "水质" in text:
   url=urllib.parse.urljoin(INDEX,h)
   if p not in found or len(text)>len(found[p]["text"]):found[p]={"url":url,"text":text}
if set(found)!=set(PERIODS):raise RuntimeError("Months not actually found at official source: "+repr(found))
def decode_gov_html(raw):
 # preserve original HTML encoding; bs4 handles meta charset
 soup=BeautifulSoup(raw,"lxml")
 tables=soup.select("table")
 candidates=[]
 for tb in tables:
  head=norm(tb.get_text(" ",strip=True)[:500])
  if "行政区划" in head and "点位名称" in head and "达标" in head:
   candidates.append(tb)
 if not candidates:raise RuntimeError("No table with 行政区划, 点位名称, 达标 heading")
 table=max(candidates,key=lambda tb:len(tb.select("tr")))
 try:
  frames=pd.read_html(io.StringIO(str(table)),flavor="lxml")
  df=max(frames,key=lambda f:len(f))
 except Exception as exc:
  raise RuntimeError("HTML named station table could not be interpreted: "+repr(exc))
 if len(df)<80:raise RuntimeError("Water source table fewer than 80 point rows "+str(len(df)))
 cols=[norm(z if not isinstance(z,tuple) else z[-1]) for z in df.columns]
 # Many official tables use <td> rather than <th> for their header; pandas assigns 0..8.
 if "行政区划" not in cols or "点位名称" not in cols:
  for i in range(min(6,len(df))):
   probe=[norm(x) for x in df.iloc[i].tolist()]
   if "行政区划" in probe and "点位名称" in probe and "序号" in probe:
    cols=probe
    df=df.iloc[i+1:].reset_index(drop=True)
    break
 if "行政区划" not in cols or "点位名称" not in cols:
  raise RuntimeError("Water table headers still unresolved; first rows="+str(df.head(4).values.tolist())[:450])
 return soup,table,df,cols
events=[];source_docs=[];blocked=[]
for p in PERIODS:
 url=found[p]["url"];raw,status=req(url,8_000_000);soup,tb,df,cols=decode_gov_html(raw)
 if "行政区划" not in cols or "点位名称" not in cols:
  raise RuntimeError("Expected table headers missing "+str(cols))
 def field(row,key):
  index=cols.index(key)
  v=row.iloc[index]
  return "" if pd.isna(v) else str(v).strip()
 seqcol=cols.index("序号") if "序号" in cols else 0
 n=0
 for _,r in df.iterrows():
  serial=str(r.iloc[seqcol]).strip()
  if not re.fullmatch(r"\d+(\.0)?",serial):continue
  serial=int(float(serial))
  admin=norm(field(r,"行政区划"));location=norm(field(r,"点位名称"))
  waterclass=norm(field(r,"水源地类型")) if "水源地类型" in cols else ""
  watertype=norm(field(r,"水体类型")) if "水体类型" in cols else ""
  outcome=norm(field(r,"达标情况")) if "达标情况" in cols else ""
  excess=norm(field(r,"超标指标及超标倍数")) if "超标指标及超标倍数" in cols else ""
  if not location or not admin:raise RuntimeError("Missing named water source or admin in published row")
  codes=[c for c,nm in known.items() if nm==admin]
  if len(codes)==1 and codes[0] in bycode:code=codes[0];level="EXACT_COUNTY_CODE_NAME_2025"
  else:
   code=None;level="PREFECTURE_OR_AMBIGUOUS_NO_COUNTY_PROOF"
  # Source water quality is evaluated per intake, NOT household tap.
  event={"month":p,"source_url":url,"source_http_sha256":sha(raw),
         "table_sequence":serial,"admin_source_name":admin,"named_water_intake":location,
         "source_water_type":waterclass,"source_waterbody_type":watertype,
         "assessment_result":outcome,"exceedance_info":excess,
         "candidate_county_code":code,
         "county_match_level":level,"is_drinking_water_source_raw_not_household":True,
         "actual_2026_official_boundary_certified":False}
  if code:events.append(event)
  else:blocked.append(event)
  n+=1
 source_docs.append({"month":p,"url":url,"sha256":sha(raw),"http_status":status,
  "bytes":len(raw),"html_table_rows_raw":len(df),"sequence_records":n,
  "county_named_intake_rows":sum(z["month"]==p for z in events),
  "prefecture_or_unmatched_records":sum(z["month"]==p for z in blocked),
  "table_column_names":cols,"gov_explanation_raw_water_not_tap":"水源水经自来水厂净化处理后方进入居民供水系统"})
 print("R5_OFFICIAL_FUJIAN_MONTH",p,"source_rows",n,"exact_county",source_docs[-1]["county_named_intake_rows"],
       "municipal_unmatched",source_docs[-1]["prefecture_or_unmatched_records"],flush=True)
 if n<90 or n>160:raise RuntimeError("Named monthly water points unexpected count "+str(n))
 if p=="2025-12" and n!=109:raise RuntimeError("Official Dec2025 announced 109 actual source intakes, got "+str(n))
records=events+blocked
if len(records)!=sum(x["sequence_records"] for x in source_docs):
 raise RuntimeError("Source number mismatch")
# Check if a source place becomes noncompliant or disappears; never summarize "all water safe" by county.
by_county=collections.defaultdict(list)
for x in events:by_county[x["candidate_county_code"]].append(x)
unique=set(by_county)
if not 20<=len(unique)<=100:raise RuntimeError("County-source mapping unexpectedly small or huge "+str(len(unique)))
suppcols=["R5_Fujian_source_water_2025_2026_monitored",
 "R5_Fujian_source_water_count_unique_named_sites",
 "R5_Fujian_months_with_named_intake",
 "R5_Fujian_compliance_observed_per_named_intake",
 "R5_Fujian_source_water_not_finished_tap","R5_Fujian_official_source_QA"]
for c in suppcols:
 if c in fields:raise RuntimeError("Would overwrite preexisting column "+c)
fields+=suppcols
prior=set(z["candidate_code"] for z in rows if z["R5_status"]!="NOT_SCREENED")
if prior and prior!={"532503"}:raise RuntimeError("R5 predecessor baseline unexpected "+str(prior))
# Explicitly retain original Mengzi finished tap evidence separately.
if "532503" not in prior:
 r=bycode["532503"];r["R5_status"]="NAMED_TAP_SOURCE_EXISTING_16_SITES_NOT_WHOLE_CITY"
 r["R5_evidence_scope"]="PRIOR_MENGZI_NAMED_TAP_MONITORING_POINTS_NOT_WHOLE_CITY"
 r["cascade_status"]="ACTIVE_PENDING"
new=0
for code,ls in by_county.items():
 row=bycode[code]
 row["R5_Fujian_source_water_2025_2026_monitored"]="TRUE"
 row["R5_Fujian_source_water_count_unique_named_sites"]=len({r["named_water_intake"] for r in ls})
 row["R5_Fujian_months_with_named_intake"]=";".join(sorted({r["month"] for r in ls}))
 row["R5_Fujian_compliance_observed_per_named_intake"]="ALL_REPORTED_COMPLIANT" if all(r["assessment_result"]=="达标" for r in ls) else "SOME_NOT_COMPLIANT_OR_UNCLEAR"
 row["R5_Fujian_source_water_not_finished_tap"]="TRUE"
 row["R5_Fujian_official_source_QA"]="EXACT_2025_HISTORIC_COUNTY_NAME_IN_OFFICIAL_FJ_SOURCE_MONTHLY_TABLE"
 if row["R5_status"]=="NOT_SCREENED":
  row["R5_status"]="COUNTY_NAMED_RAW_WATER_SOURCE_MONTHLY_MONITORING_ONLY"
  row["last_completed_round"]="R5_FUJIAN_RAW_WATER_INTAKE_PARTIAL"
  row["cascade_status"]="ACTIVE_PENDING"
  new+=1
after=sum(r["R5_status"]!="NOT_SCREENED" for r in rows)
if after!=len(unique)+1:raise RuntimeError("Unexpected R5 previous Mengzi preservation "+str((after,len(unique))))
if any(x["confirmed_exit_round"] for x in rows) or any(str(x["valid_county_screening"]).lower()=="true" for x in rows):
 raise RuntimeError("False formal county screening or automatic exclusion")
csvsource=OUT/"R5_Fujian_official_2025_2026_raw_water_named_intake_records.csv"
csvfields=["month","table_sequence","admin_source_name","named_water_intake","source_water_type","source_waterbody_type",
 "assessment_result","exceedance_info","candidate_county_code","county_match_level","source_url","source_http_sha256",
 "is_drinking_water_source_raw_not_household","actual_2026_official_boundary_certified"]
with csvsource.open("w",encoding="utf-8-sig",newline="") as f:
 w=csv.DictWriter(f,fieldnames=csvfields);w.writeheader();w.writerows(records)
national=OUT/"national_R5_Fujian_2025_2026_source_water_2847.csv"
with national.open("w",encoding="utf-8-sig",newline="") as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
report={"schema":"RET_R5_2025_2026_FUJIAN_OFFICIAL_RAW_DRINKING_WATER_SOURCES_NAME_MATCH_QA_V1",
 "asof_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "publisher":"福建省生态环境厅","index_url":INDEX,
 "source_months_selected":PERIODS,"source_month_reports":source_docs,
 "source_named_raw_water_intake_rows_all":len(records),
 "source_named_raw_water_intake_exact_county_records":len(events),
 "source_city_or_other_unmapped_rows":len(blocked),
 "distinct_exact_2025_county_codes_with_official_raw_source_records":len(unique),
 "new_R5_county_source_only_partial_counties":new,
 "prior_2026_Mengzi_named_finished_tap_site_counties":1,
 "R5_total_source_or_tap_named_site_partial_counties":after,
 "R5_unknown_candidate_counties":2847-after,
 "R5_fujian_observation_types_not_tap":"集中式饮用水水源（取水口），按GB3838Ⅲ类或地下水GB/T14848Ⅲ类评价；非自来水厂出厂水或居民末梢水",
 "underlying_exact_county_codes":sorted(unique),
 "compliance_reported_by_named_intake":dict(collections.Counter(x["assessment_result"] for x in records)),
 "county_source_detail_records":events,"not_county_identity_records":blocked,
 "source_2025_historic_code_sha256":sha(code_raw),
 "source_R4_national_input_sha256":sha(R4.read_bytes()),
 "source_previous_Mengzi_tap_summary_sha256":sha(OLD.read_bytes()),
 "CSV_named_points_sha256":sha(csvsource.read_bytes()),
 "CSV_national_2847_sha256":sha(national.read_bytes()),
 "formal_valid_county_screenings":0,"confirmed_exclusions":0,"all_carry_forward":2847,
 "official_2026_country_wide_roster_verified":False,
 "limitations":["Official reporting for a named RAW drinking-water-source intake is NOT a finished tap/supply-pipe/water at home test",
 "Without supply-network spatial polygon, source water could serve multiple districts and does not prove dwelling exposure",
 "Exact source table county name is code-joined only at 2025 historical roster and pending 2026 official reconciliation",
 "Missing counties and city-level intakes remain unknown, no imputation or exclusion",
 "Only published compliance assessments, NOT all per-pollutant concentration numerics unless explicitly present"]}
out=OUT/"R5_Fujian_2025_2026_official_raw_source_evidence.json"
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["source_named_raw_water_intake_rows_all","source_named_raw_water_intake_exact_county_records",
 "source_city_or_other_unmapped_rows","distinct_exact_2025_county_codes_with_official_raw_source_records",
 "new_R5_county_source_only_partial_counties","R5_total_source_or_tap_named_site_partial_counties",
 "R5_unknown_candidate_counties","compliance_reported_by_named_intake"]},ensure_ascii=False),flush=True)
