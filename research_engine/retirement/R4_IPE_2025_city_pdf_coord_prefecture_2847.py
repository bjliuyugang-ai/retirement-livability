#!/usr/bin/env python3
"""Read actual 2025 Blue Map annual city pollution PDF, independently tag source
quality and join only strictly matched prefectural city names/2025 codes to
provisional 2847 candidate counties.

This is SECONDARY monitoring-derived 2025 urban background, not MEE-certified
data, county-specific exposure, residential pollution, legal code proof, or
permission to fail a county under frozen stage-one thresholds.
"""
import collections,csv,datetime,difflib,hashlib,json,pathlib,re,urllib.request
import fitz
ROOT=pathlib.Path("research_engine/retirement")
OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
SOURCE="https://pdf.dfcfw.com/pdf/H3_AP202601071816825617_1.pdf?1767856554000.pdf="
CODES_URL="https://raw.githubusercontent.com/yescallop/areacodes/master/data/2025.txt"
INPUT=ROOT/"status/national_R3_205_station_dem_altitude_partial_2847.csv"
R3=ROOT/"status/national_R3_205_station_dem_altitude_source_evidence.json"
PDF_SHA="54c333be177c5bd6e345a698f1a7ca4823fcadf9f1c33ec045314b43b4507edd"
PROVINCES={"北京":"11","天津":"12","河北":"13","山西":"14","内蒙古":"15","辽宁":"21",
"吉林":"22","黑龙江":"23","上海":"31","江苏":"32","浙江":"33","安徽":"34",
"福建":"35","江西":"36","山东":"37","河南":"41","湖北":"42","湖南":"43",
"广东":"44","广西":"45","海南":"46","重庆":"50","四川":"51","贵州":"52",
"云南":"53","西藏":"54","陕西":"61","甘肃":"62","青海":"63","宁夏":"64","新疆":"65"}
ALIASES={"新福":"新疆","宁":"宁夏","广西壮族自治区":"广西","新疆维吾尔自治区":"新疆"}
def sha(b):return hashlib.sha256(b).hexdigest()
def get(url,lim):
 req=urllib.request.Request(url,headers={"User-Agent":"RetirementR4AnnualSecondaryNumericQA/1.0"})
 with urllib.request.urlopen(req,timeout=120) as r:b=r.read(lim+1)
 if len(b)>lim:raise RuntimeError("Oversized source")
 return b
r3=json.loads(R3.read_text(encoding="utf-8"))
if r3["total_R3_partial_point_evidence_counties"]!=205 or r3["formal_valid_county_screenings"]!=0 or sha(INPUT.read_bytes())!=r3["output_national_csv_sha256"]:
 raise RuntimeError("V1.6 R3 source and 2847 ledger SHA mismatch")
with INPUT.open(encoding="utf-8-sig",newline="") as f:
 dr=csv.DictReader(f);fields=list(dr.fieldnames);rows=list(dr)
if len(rows)!=2847 or len({x["candidate_code"] for x in rows})!=2847:
 raise RuntimeError("National county register not 2847")
pdfraw=get(SOURCE,10_000_000)
if sha(pdfraw)!=PDF_SHA:raise RuntimeError("SECONDARY_PDF_SOURCE_VINTAGE_CHANGED")
pdf=OUT/"IPE_BlueMap_2025_air_city_original.pdf";pdf.write_bytes(pdfraw)
doc=fitz.open(str(pdf))
if len(doc)!=12:raise RuntimeError("Expected verified 12-page PDF")
allrows=[]
for page in range(3,len(doc)):
 words=doc[page].get_text("words")
 o3=[x for x in words if 409<x[0]<452 and x[1]>95 and re.fullmatch(r"[0-9]{2,3}",x[4].strip()) and 70<=int(x[4])<=300]
 cities=[x for x in words if 123<x[0]<190 and x[1]>95 and not re.search(r"[0-9]",x[4]) and x[4]!="城市"]
 provinces=[x for x in words if 79<x[0]<125 and x[1]>95 and not re.search(r"[0-9]",x[4]) and x[4]!="省区市"]
 tmax=[x for x in words if 190<x[0]<225 and x[1]>95 and re.fullmatch(r"[0-9]{1,3}\.[0-9]",x[4].strip()) and 4<=float(x[4])<130]
 def nearest(items,y):
  if not items:return None,99
  x=min(items,key=lambda z:abs((z[1]+z[3])/2-y))
  return x,round(abs((x[1]+x[3])/2-y),2)
 for pos,x in enumerate(o3,1):
  cy=(x[1]+x[3])/2
  city,dc=nearest(cities,cy-4);prov,dp=nearest(provinces,cy-4);pm,dt=nearest(tmax,cy)
  name=city[4] if city else ""
  p_raw=prov[4] if prov else ""
  if name in ("北京","天津","上海","重庆"):p_raw=name
  p_name=ALIASES.get(p_raw,p_raw)
  item={"PDF_page":page+1,"PDF_row":pos,"city_raw":name,"province_raw":p_raw,
     "province_match_name":p_name,"city_label_gap":dc,"province_label_gap":dp,
     "pm25_numeric_gap":dt,"PM25_annual_2025_ug_m3":float(pm[4]) if pm and dt<=9 else None,
     "O3_8h_90percentile_2025_ug_m3":int(x[4]),
     "original_O3_token":x[4],
     "raw_extraction_quality":"CITY_TEXT_AMBIGUOUS" if dc>8 else "POSITION_MATCHED",
     "source_comparability":"UNREVIEWED_BLUE_MAP_MONITOR_DAILY_DERIVED_2025"}
  allrows.append(item)
if len(allrows)!=338:raise RuntimeError("339-city monitoring report with unexpected PDF extracted 2025 row count "+str(len(allrows)))
codes_txt=get(CODES_URL,400_000)
source_codes={}
for line in codes_txt.decode("utf-8-sig").splitlines():
 m=re.fullmatch(r"([0-9]{6})\s+(.+)",line.strip())
 if not m:raise RuntimeError("Unparseable 2025 historical code")
 source_codes[m[1]]=m[2]
if len(source_codes)!=3212:raise RuntimeError("Year2025 historical code source size changed")
pref={c:n for c,n in source_codes.items() if c.endswith("00") and not c.endswith("0000")}
def is_strict_name(raw,official):
 if not raw or len(raw)<2:return False
 # Unique *exact* prefecture prefix. '海南州' -> '海南' in Qinghai, exact jurisdiction
 # label still only a city aggregate.
 raw=raw[:-1] if raw.endswith("州") else raw
 return official==raw or official.startswith(raw)
mapped=[];blocked=[]
for line in allrows:
 prov2=PROVINCES.get(line["province_match_name"])
 line["source_2025_history_province_prefix"]=prov2 or ""
 if line["raw_extraction_quality"]!="POSITION_MATCHED" or not prov2:
  line["mapping_status"]="HOLD_OCR_CITY_LABEL_OR_PROVINCE";blocked.append(line);continue
 name=line["city_raw"]
 if name in ("北京","天津","上海","重庆"):
  code=prov2+"0000";cands=[(code,source_codes.get(code))]
 else:
  cands=[(c,n) for c,n in pref.items() if c[:2]==prov2 and is_strict_name(name,n)]
  if not cands and prov2 in ("65","46"):
   cands=[(c,n) for c,n in source_codes.items() if c[:2]==prov2 and not c.endswith("00") and
     (n==name+"市" or n==name) and c[:4] in ("6590","4690")]
 if len(cands)!=1 or not cands[0][1]:
  line["mapping_status"]="HOLD_NO_UNIQUE_EXACT_PREFECTURAL_CODE"
  line["suggested_codes"]=[c for c,n in cands][:8]
  blocked.append(line);continue
 code,official=cands[0]
 line["prefectural_or_direct_admin_code_2025"]=code
 line["prefectural_2025_official_history_name"]=official
 line["mapping_status"]="STRICT_HISTORIC_2025_PROVINCE_CITY_NAME"
 mapped.append(line)
# Disallow duplicate derived prefecture code: source may contain duplicate label
assigned=[x["prefectural_or_direct_admin_code_2025"] for x in mapped]
dupe=[x for x,n in collections.Counter(assigned).items() if n>1]
if dupe:
 for x in mapped:
  if x["prefectural_or_direct_admin_code_2025"] in dupe:
   x["mapping_status"]="HOLD_DUPLICATE_PREFECTURE_2025"
 blocked.append(x)
 mapped=[x for x in mapped if x["mapping_status"]=="STRICT_HISTORIC_2025_PROVINCE_CITY_NAME"]
valid_bycode={x["prefectural_or_direct_admin_code_2025"]:x for x in mapped}
extra=["R4_secondary_city_background_2025_code","R4_secondary_city_background_2025_name",
 "R4_secondary_city_annual_PM25_ug_m3","R4_secondary_city_O3_8H_p90_ug_m3",
 "R4_air_evidence_level","R4_source_quality","R4_current_residential_air_tested"]
for col in extra:
 if col in fields:raise RuntimeError("Refuse to overwrite previous R4 ledger field "+col)
fields+=extra
matched_county=0;new_R4=0;missing_PM25=0
for x in rows:
 code=x["candidate_code"];pcode=code[:4]+"00"
 if code[:2] in ("11","12","31","50"):pcode=code[:2]+"0000"
 # One directly-administered prefecture-like city may be an identical county code
 data=valid_bycode.get(pcode) or valid_bycode.get(code)
 if data is None:continue
 matched_county+=1
 x["R4_secondary_city_background_2025_code"]=data["prefectural_or_direct_admin_code_2025"]
 x["R4_secondary_city_background_2025_name"]=data["prefectural_2025_official_history_name"]
 x["R4_secondary_city_annual_PM25_ug_m3"]=data["PM25_annual_2025_ug_m3"] if data["PM25_annual_2025_ug_m3"] is not None else ""
 x["R4_secondary_city_O3_8H_p90_ug_m3"]=data["O3_8h_90percentile_2025_ug_m3"]
 x["R4_air_evidence_level"]="SECONDARY_PREFECTURE_CITY_CONTEXT_NOT_COUNTY_OR_RESIDENCE"
 x["R4_source_quality"]="UNOFFICIAL_NOT_EFFECTIVENESS_REVIEWED"
 x["R4_current_residential_air_tested"]="FALSE"
 if data["PM25_annual_2025_ug_m3"] is None:missing_PM25+=1
 if x["R4_status"]=="NOT_SCREENED":
  x["R4_status"]="SECONDARY_CITY_AIR_2025_PM25_O3_CONTEXT_PENDING_COUNTY_MEASUREMENTS"
  x["cascade_status"]="ACTIVE_PENDING"
  x["last_completed_round"]="R4_PREFECTURE_AIR_BACKGROUND_PARTIAL"
  new_R4+=1
after_R4=sum(x["R4_status"]!="NOT_SCREENED" for x in rows)
if after_R4!=2+new_R4:raise RuntimeError("Prior two R4 regional records were overwritten or counts changed")
if any(x["confirmed_exit_round"] for x in rows) or any(str(x["valid_county_screening"]).lower()=="true" for x in rows):
 raise RuntimeError("Premature county elimination or formal grade")
def emit(path,records,columns):
 with path.open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore")
  w.writeheader();w.writerows(records)
sourcecsv=OUT/"R4_2025_China_city_air_338_raw_sourceQA.csv"
cols=list(allrows[0])
if "prefectural_or_direct_admin_code_2025" not in cols:cols+=["prefectural_or_direct_admin_code_2025","prefectural_2025_official_history_name","mapping_status"]
else:cols+=[x for x in ["mapping_status"] if x not in cols]
emit(sourcecsv,allrows,cols)
countyout=OUT/"national_R4_2025_secondary_prefectural_air_2847.csv"
emit(countyout,rows,fields)
report={"schema":"RET_R4_2025_SECONDARY_338_CITY_PM25_O3_COORDINATE_AND_ADMIN_CODE_QA_V1",
 "at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_pdf_URL":SOURCE,"source_pdf_sha256":sha(pdfraw),"source_2025_code_URI":CODES_URL,
 "source_2025_code_sha256":sha(codes_txt),
 "source_R3_2847_sha256":sha(INPUT.read_bytes()),
 "source_classification":"IPE Blue Map 2025 city ambient pollutant compilation from publicly monitored daily city data, UNREVIEWED, not MEE official annual city data",
 "source_year":2025,"scope_not_official_county":True,
 "PDF_pages":len(doc),"actual_source_city_rows":len(allrows),
 "source_rows_PM25_numeric":sum(x["PM25_annual_2025_ug_m3"] is not None for x in allrows),
 "source_rows_O3_numeric":len(allrows),
 "strict_unique_prefecture_or_direct_city_rows":len(mapped),
 "source_rows_missing_or_ambiguous_prefecture_match":len(blocked),
 "accepted_new_city_names":sorted(x["prefectural_2025_official_history_name"] for x in mapped),
 "blocked_city_rows":blocked,
 "new_R4_prefectural_secondary_background_counties":new_R4,
 "R4_counties_with_any_source_context_after":after_R4,
 "R4_unscanned":2847-after_R4,
 "counties_with_source_city_2025_context":matched_county,
 "counties_with_source_city_PM25_missing_but_O3_available":missing_PM25,
 "source_numeric_2025_unreviewed_warning":True,
 "MEE_2025_published_339_city_mean_PM25_ug_m3":28.0,
 "MEE_2025_published_339_city_O3_8H_p90_ug_m3":138,
 "MEE_public_reference":"https://www.mee.gov.cn/ywdt/xwfb/202601/t20260128_1142783.shtml",
 "MEE_2025_yearly_339_city_scope_IS_DIFFERENT_FROM_338_IPE_SOURCE":True,
 "source_rows_csv_sha256":sha(sourcecsv.read_bytes()),
 "national_R4_csv_sha256":sha(countyout.read_bytes()),
 "R1_partial_retained":214,"R2_partial_retained":199,"R3_partial_retained":205,
 "formal_valid_county_screenings":0,"confirmed_exclusions":0,"carry_forward":2847,
 "limits":["2025 reported city data is third-party aggregated and explicitly '未经有效性审核'; not substitute for official MEE annual city pollutant data",
 "O3 statistic is daily maximum 8h 90th percentile, not average hourly ozone",
 "Mapped county receives its parent-city background proxy ONLY, not measured local county or residential pollution",
 "PDF has 338 table rows, official MEE reports 339 city coverage; missing source item not imputed",
 "Ambiguous city labels and missing PM values are kept missing, never invented",
 "All 2847 counties remain candidates and formal ratings stay unchanged"]}
reportfile=OUT/"R4_2025_city_air_actual_data_and_mapping_evidence.json"
reportfile.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["actual_source_city_rows","source_rows_PM25_numeric",
 "source_rows_O3_numeric","strict_unique_prefecture_or_direct_city_rows",
 "source_rows_missing_or_ambiguous_prefecture_match",
 "counties_with_source_city_2025_context",
 "new_R4_prefectural_secondary_background_counties",
 "R4_counties_with_any_source_context_after","R4_unscanned"]},ensure_ascii=False),flush=True)
