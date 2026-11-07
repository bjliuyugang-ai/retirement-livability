#!/usr/bin/env python3
"""Verify 2025 named urban/rural tap and treated-water monitoring in 7 counties.
County attachment requires actual local government document, site type/date,
historical 2025 exact code/name, source HTTP SHA. Keep existing 56 raw-source
Fujian counties + Mengzi historical tap records. NO formal county grading.
"""
import csv,datetime,hashlib,json,pathlib,re,urllib.request
from bs4 import BeautifulSoup
import fitz
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/"status/national_R5_Fujian2025_12_109_official_source_intakes_2847.csv"
PRE=ROOT/"status/Fujian2025_12_R5_official_raw_water_source_evidence.json"
NAMES=ROOT/"evidence/mirror_2025_adcodes.txt"
def sha(b):return hashlib.sha256(b).hexdigest()
previous=json.loads(PRE.read_text(encoding="utf-8"))
if not(previous["all_official_source_intake_sites"]==109 and previous["R5_total_partial_counties"]==57 and previous["formal_valid_county_screenings"]==0 and sha(BASE.read_bytes())==previous["national_R5_csv_sha256"]):raise RuntimeError("R5 prior 57 county reference SHA drift")
with BASE.open(encoding="utf-8-sig",newline="") as f:
 rd=csv.DictReader(f);fields=list(rd.fieldnames);rows=list(rd)
bycode={r["candidate_code"]:r for r in rows}
if len(bycode)!=2847:raise RuntimeError("2847 not preserved")
archive={}
for line in NAMES.read_text(encoding="utf-8").splitlines():
 m=re.fullmatch(r"([0-9]{6})\s+(.+)",line.strip())
 if m:archive[m.group(1)]=m.group(2)
targets=[
 ("210921","阜新蒙古族自治县","RESIDENTIAL_TAP_39_HOUSEHOLDS",39,"2025-Q4","HTML","https://www.fmx.gov.cn/content/2025/1026468.html",["39户居民家","末梢水","第四季度","达标"]),
 ("152222","科尔沁右翼中旗","CITY_RURAL_TAP_15_POINTS",15,"2025-Q4","HTML","https://kyzq.gov.cn/kyzq/2026-01/12/article_2026011209302315368.html",["15个监测点","15份","末梢水","合格"]),
 ("431202","鹤城区","CITY_TAP_25_POINTS",25,"2025-Q4","HTML","https://www.huaihua.gov.cn/huaihua/c131729/202601/5ca0af424de7481db6c17322795f5792.shtml",["鹤城区","25个末梢水监测点","36项常规指标","均符合"]),
 ("330203","海曙区","COUNTY_GOV_TAP_PARAMETER_COMPLIANCE_UNSPECIFIED_SAMPLES",None,"2025-Q4","HTML","https://www.haishu.gov.cn/col/col1229100498/art/2026/art_8b0bf46fd8f548b09632dfd61dbbb0dc.html",["用户水龙头","第四季度","监测指标合格率","总大肠菌群","砷"]),
 ("533401","香格里拉市","TREATED_WATER_TWO_PLANT_OUTLETS",2,"2025-Q4","HTML","https://www.xianggelila.gov.cn/zfxxgk_xglls_wsjkj/fdzdgknr/tzgg/202511/20251119_234730.html",["第一水厂出厂水","第二水厂出厂水","浑浊度","总大肠菌群"]),
 ("350505","泉港区","TAP_10_AND_PLANT_2",12,"2025-Q3","PDF","https://www.qg.gov.cn/zwgk/zdxxgk/ylws/202509/P020250905291099889064.pdf",["泉港区","2025年7月29日","12份","管网末梢水","出厂水"]),
 ("150204","青山区","TAP_AND_TREATED_WATER_NUMERICAL_TABLE",None,"2025-Q4","PDF","https://www.qsq.gov.cn/rmt/userfiles/95a6c41850cb48e0a1dcd08b0441d1d8/cxfj/cms/documentAct/cmsDocument/2025/12/20251210112956885.pdf",["青山区","2025年第四季度","菌落总数","浑浊度"])
]
output=[]
for code,name,kind,number,period,fmt,url,keys in targets:
 if archive.get(code)!=name or bycode[code]["candidate_name"]!=name:raise RuntimeError("County code conflict "+code)
 o={"county_code":code,"county_name":name,"sample_scope":kind,"reported_sample_count":number,"quarter":period,"format":fmt,"source_url":url,"source_authority":"LOCAL_GOV_OR_LOCAL_HEALTH_DEPARTMENT","source_quality":"NOT_TESTED","2026_official_administrative_code_verified":False}
 try:
  request=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; provincial-R5-source-QA/1.0)","Accept":"text/html,application/pdf,*/*"})
  with urllib.request.urlopen(request,timeout=65) as r:raw=r.read(8_000_001)
  if len(raw)>8_000_000:raise RuntimeError("Document too large")
  if fmt=="PDF":
   if not raw.startswith(b"%PDF"):raise RuntimeError("Not a PDF response")
   pdf=fitz.open(stream=raw,filetype="pdf")
   content="\n".join(z.get_text("text") for z in pdf)
   o["pdf_pages"]=len(pdf)
  else:content=BeautifulSoup(raw,"lxml").get_text(" ",strip=True)
  clean=re.sub(r"\s+","",content)
  misses=[k for k in keys if re.sub(r"\s+","",k) not in clean]
  o.update({"source_bytes":len(raw),"source_sha256":sha(raw),"body_extracted_characters":len(content),"missing_verification_terms":misses,"source_quality":"HTTP_REAL_AND_TEXT_VERIFIED" if not misses else "SOURCE_TERMS_INCOMPLETE_HOLD","sample_is_not_whole_county_drinking_water_grade":True})
 except Exception as e:
  o.update({"source_quality":"SOURCE_FAILED","source_error":repr(e)})
 output.append(o)
 print("R5_REAL_FINISHED_TAP_PROBE",code,name,o["source_quality"],o.get("source_bytes"),o.get("missing_verification_terms"),flush=True)
good=[x for x in output if x["source_quality"]=="HTTP_REAL_AND_TEXT_VERIFIED"]
coladd=["R5_finished_water_observation_type","R5_finished_water_sample_count","R5_finished_water_sampling_quarter","R5_finished_water_official_URL","R5_finished_water_evidence_strength"]
for c in coladd:
 if c in fields:raise RuntimeError("Would overwrite historical field "+c)
fields+=coladd
baseline={r["candidate_code"] for r in rows if r["R5_status"]!="NOT_SCREENED"}
if len(baseline)!=57:raise RuntimeError("Source 57 county R5 data missing")
new=upgrade=0
for x in good:
 r=bycode[x["county_code"]]
 r["R5_finished_water_observation_type"]=x["sample_scope"]
 r["R5_finished_water_sample_count"]=x["reported_sample_count"] if x["reported_sample_count"] is not None else ""
 r["R5_finished_water_sampling_quarter"]=x["quarter"]
 r["R5_finished_water_official_URL"]=x["source_url"]
 r["R5_finished_water_evidence_strength"]="OFFICIAL_SINGLE_QUARTER_NAMED_FINISHED_WATER_LOCAL_CONTEXT_ONLY"
 if r["R5_status"]=="NOT_SCREENED":
  r["R5_status"]="COUNTY_NAMED_TAP_OR_TREATED_WATER_PARTIAL"
  r["cascade_status"]="ACTIVE_PENDING"
  r["last_completed_round"]="R5_2025_FINISHED_TAP_WATER_SITE_PARTIAL"
  new+=1
 else:upgrade+=1
count=sum(x["R5_status"]!="NOT_SCREENED" for x in rows)
if count!=57+new:raise RuntimeError("R5 previous 57 baseline not preserved")
if any(x["confirmed_exit_round"] for x in rows) or any(str(x["valid_county_screening"]).lower()=="true" for x in rows):raise RuntimeError("Unjustified R5 fatal status")
csvpath=OUT/"national_R5_2025_7district_finished_water_source_partial_2847.csv"
with csvpath.open("w",encoding="utf-8-sig",newline="") as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
summary={"schema":"RET_R5_REAL_2025_SEVEN_COUNTY_OR_DISTRICT_TAP_AND_TREATED_WATER_QA_V1",
 "asof_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "sources_attempted":7,"source_count_validated":len(good),"source_count_blocked":7-len(good),
 "source_records":output,"new_R5_counties_with_finished_water_sample_evidence":new,
 "prior_R5_counties_upgraded_to_finished_water_sample_evidence":upgrade,
 "all_source_or_finished_partial_county_evidence_after":count,
 "R5_no_named_site_evidence_counties":2847-count,"all_carry_forward":2847,
 "source_previous_57_R5_csv_sha256":sha(BASE.read_bytes()),
 "national_output_csv_sha256":sha(csvpath.read_bytes()),
 "formal_valid_county_screenings":0,"confirmed_exclusions":0,
 "notes":["2025 site/household tap and factory outlet single-quarter tests, not every dwelling",
 "Plant outlet is NOT downstream network tap water","Unpublished pollutant concentrations cannot be inferred from pass/fail",
 "The county code is 2025 historical provisional; 2026 legal county geometry not independently certified","No automatic R5 grade or county exclusion"]}
(OUT/"R5_2025_crossprovince_7counties_finished_tap_plant_source_evidence.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:summary[k] for k in ["source_count_validated","source_count_blocked","new_R5_counties_with_finished_water_sample_evidence","prior_R5_counties_upgraded_to_finished_water_sample_evidence","all_source_or_finished_partial_county_evidence_after","R5_no_named_site_evidence_counties"]},ensure_ascii=False),flush=True)
if not good:raise SystemExit(2)
