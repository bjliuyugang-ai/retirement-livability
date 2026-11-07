#!/usr/bin/env python3
"""Extract REAL province-issued 2025 full-year air-quality county data from
Fujian Department of Ecology and Environment dated 2026-01-23.

58 county-level annual PM2.5, good air-day percentage and AQ composite index
from Annex 4, plus nine prefecture cities + Pingtan 2025 annual PM2.5 and O3.
Do NOT substitute "primary pollutant Ozone" as numeric O3.
Join 58 to exactly ONE historical 2025 provisional code each (Fujian '35').
County-level monitoring result NOT dwelling air, city table NOT all constituent
counties. No exclusion/grade; preserve other 2,847 rows and R1/R2/R3.
"""
import collections,csv,datetime,hashlib,json,pathlib,re,urllib.request
from bs4 import BeautifulSoup
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
URL="https://sthjt.fujian.gov.cn/zwgk/ywxx/kjjc/202601/t20260126_7085242.htm"
PREV=ROOT/"status/national_R3_205_station_dem_altitude_partial_2847.csv"
R3=ROOT/"status/national_R3_205_station_dem_altitude_source_evidence.json"
R4_STATUS_CANDIDATE=ROOT/"status/national_R4_air_pollution_batch.csv"
def sha(b):return hashlib.sha256(b).hexdigest()
def clean(t):return re.sub(r"\\s+","",t).replace("\u3000","").replace("₂","2").replace("₃","3").replace("₂.₅","2.5")
def request():
 req=urllib.request.Request(URL,headers={"User-Agent":"RetirementFujianOfficialAirMonitoring2025/1.0","Accept":"text/html,application/xhtml+xml"})
 with urllib.request.urlopen(req,timeout=100) as r:b=r.read(7_000_000);charset=r.headers.get_content_charset() or "utf-8"
 return b,b.decode(charset,"replace")
raw,html=request()
raw_sha=sha(raw)
soup=BeautifulSoup(html,"html.parser")
# Find all HTML tables and retain their raw tr cells; avoid treating monthly Annex 3
# as full-year Annex 4. The desired table contains 58 distinct exact county names.
tables=[]
for table in soup.find_all("table"):
 rows=[]
 for tr in table.find_all("tr"):
  cells=[clean(td.get_text(" ",strip=True)) for td in tr.find_all(["td","th"],recursive=False)]
  if cells:rows.append(cells)
 tables.append(rows)
def parse_float(t):
 if not re.fullmatch(r"\\d+(?:\\.\\d+)?",t):raise ValueError("Invalid numeric cell "+repr(t))
 return float(t)
def parse_annex4(rows):
 out=[]
 for cells in rows:
  if len(cells)<4:continue
  possible=[(i,text) for i,text in enumerate(cells) if re.fullmatch(r"[^0-9]{2,16}(区|县|市)",text)]
  for i,name in possible:
   rest=cells[i+1:]
   if len(rest)<4:continue
   if not re.fullmatch(r"\\d+(?:\\.\\d+)?",rest[0]):continue
   if not re.fullmatch(r"\\d+(?:\\.\\d+)?",rest[1]):continue
   if not re.fullmatch(r"\\d+(?:\\.\\d+)?",rest[2]):continue
   days,idx,pm=map(parse_float,rest[:3])
   if 70<=days<=100 and 0.5<=idx<=10 and 0<=pm<=150:
    out.append({"county_name":name,"good_air_days_pct":days,"comprehensive_air_index":idx,
       "PM25_annual_ugm3":pm,"primary_pollutant_name":rest[3]})
   break
 return out
candidates=[{"table_number":i,"rows":parse_annex4(tb),"raw_row_count":len(tb)} for i,tb in enumerate(tables)]
candidates.sort(key=lambda x:len(x["rows"]),reverse=True)
if not candidates:raise RuntimeError("Official HTML contains no tables")
candidates_table_sizes=[{"table":c["table_number"],"rows":len(c["rows"]),"raw":c["raw_row_count"]} for c in candidates]
# Do not accept 2025 December (monthly) even if both tables have 58:
# locate the *last* 58-county table, corroborated by annual textual heading.
candidates58=[z for z in candidates if len(z["rows"])==58]
if not candidates58:raise RuntimeError("Cannot uniquely parse Fujian full-year 58 county table: "+str(candidates_table_sizes))
target=max(candidates58,key=lambda z:z["table_number"])
county=target["rows"]
if len(set(x["county_name"] for x in county))!=58:raise RuntimeError("Duplicate Fujian county names in full-year table")
text=soup.get_text(" ",strip=True)
if not("2025年1" in text and "58个县级城市" in text and "2026-01-23" in text):
 raise RuntimeError("Official source does not support 2025 58 county annual vintage")
# City-level annual 2025 table: locate last table containing PM2.5, O3 and 9 prefecture city + Pingtan.
citytable=[]
for i,rows in enumerate(tables):
 vals=[]
 for cells in rows:
  if len(cells)<9:continue
  for ix,nm in enumerate(cells):
   if nm in ["福州市","厦门市","漳州市","泉州市","三明市","莆田市","南平市","龙岩市","宁德市","平潭区"]:
    after=cells[ix+1:]
    # index, good days, SO2, NO2, PM10, PM25, CO, O3, primary
    if len(after)>=8:
     try:
      good=float(after[1]);pm25=float(after[5]);o3=float(after[7])
      if not(0<=good<=100 and 0<=pm25<150 and 0<=o3<350):continue
      vals.append({"city":nm,"good_air_days_pct":good,"PM25_annual_ugm3":pm25,
        "O3_daily_max8h_p90_ugm3":o3,"source_city_table_index":i})
     except (ValueError,IndexError):pass
    break
 if len(vals)>=9:citytable.append((i,vals))
city_annual=max(citytable,key=lambda x:x[0])[1] if citytable else []
# Interpret 2025 city results as regional reference only; no county number multiplication.
with PREV.open(encoding="utf-8-sig",newline="") as f:
 rd=csv.DictReader(f);fieldnames=list(rd.fieldnames);rows=list(rd)
bycode={r["candidate_code"]:r for r in rows}
if len(rows)!=2847:raise RuntimeError("National R3 ledger missing 2847 rows")
fujian=collections.defaultdict(list)
for r in rows:
 if r["candidate_code"].startswith("35"):fujian[r["candidate_name"]].append(r)
extra=["R4_FJ2025_county_PM25_annual_ugm3","R4_FJ2025_county_good_air_days_pct",
 "R4_FJ2025_county_composite_index","R4_FJ2025_county_primary_pollutant",
 "R4_FJ2025_O3_numeric_value","R4_FJ2025_source_url",
 "R4_FJ2025_central_station_not_residence","R4_FJ2025_source_vintage"]
for x in extra:
 if x in fieldnames:raise RuntimeError("R4 field already present "+x)
fieldnames+=extra
joined=[];unmapped=[];duplicated=[];new_count=0
for x in county:
 candidates=fujian[x["county_name"]]
 if len(candidates)!=1:
  (unmapped if len(candidates)==0 else duplicated).append({"name":x["county_name"],"codes":[z["candidate_code"] for z in candidates]})
  continue
 r=candidates[0]
 code=r["candidate_code"]
 r["R4_FJ2025_county_PM25_annual_ugm3"]=x["PM25_annual_ugm3"]
 r["R4_FJ2025_county_good_air_days_pct"]=x["good_air_days_pct"]
 r["R4_FJ2025_county_composite_index"]=x["comprehensive_air_index"]
 r["R4_FJ2025_county_primary_pollutant"]=x["primary_pollutant_name"]
 r["R4_FJ2025_O3_numeric_value"]="" # county Annex 4 lacks numeric ozone
 r["R4_FJ2025_source_url"]=URL
 r["R4_FJ2025_central_station_not_residence"]="TRUE"
 r["R4_FJ2025_source_vintage"]="2025_01_01_TO_2025_12_31"
 # preserve prior real R4 entries if any
 if r["R4_status"]=="NOT_SCREENED":
  r["R4_status"]="FJ_OFFICIAL_2025_COUNTY_PM25_AND_AIR_QUALITY_PARTIAL_NO_NUMERIC_OZONE"
  r["R4_evidence_scope"]="OFFICIAL_FUJIAN_COUNTY_CITY_ANNUAL_NOT_RESIDENTIAL_MICROSITE"
  r["R4_missing_parameters"]="O3_QUANTITATIVE_COUNTY;MULTIYEAR_PM25;INDUSTRIAL_EMISSIONS;LOCAL_RESIDENTIAL_AIR;2026_COUNTY_AUTHENTICATION"
  r["cascade_status"]="ACTIVE_PENDING"
  r["last_completed_round"]="R4_FJ2025_ANNUAL_COUNTY_PM25_PARTIAL"
  new_count+=1
 joined.append({**x,"candidate_code":code,"name_in_provisional_roster":r["candidate_name"],
 "source":URL,"annual_2025_official_provincial_data":True,"numerical_O3_2025_county":None,
 "county_residential_exposure_verified":False,"formal_grade":None})
existing_total=sum(r["R4_status"]!="NOT_SCREENED" for r in rows)
if not 45<=len(joined)<=58:raise RuntimeError("Unexpectedly poor 2025 Fujian 58 county code match "+str(len(joined))+" / "+str((unmapped,duplicated))[:1000])
if existing_total<new_count:raise RuntimeError("R4 status reconciliation failed")
if any(r["confirmed_exit_round"] for r in rows) or any(str(r["valid_county_screening"]).lower()=="true" for r in rows):
 raise RuntimeError("Unauthorized formal R4 rating or elimination")
national=OUT/"national_R4_official_Fujian2025_county_PM25_2847.csv"
with national.open("w",encoding="utf-8-sig",newline="") as f:
 writer=csv.DictWriter(f,fieldnames=fieldnames);writer.writeheader();writer.writerows(rows)
single=OUT/"Fujian_2025_58_county_air_PM25_source_matched.csv"
with single.open("w",encoding="utf-8-sig",newline="") as f:
 cols=["candidate_code","county_name","good_air_days_pct","comprehensive_air_index","PM25_annual_ugm3","primary_pollutant_name","source"]
 w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
 for x in joined:w.writerow({k:x[k] for k in cols})
report={"schema":"RET_R4_FUJIAN_OFFICIAL_2025_COUNTY_AIR_QA_V1",
 "asof_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "publisher":"福建省生态环境厅","published_date":"2026-01-23",
 "source_url":URL,"source_html_sha256":raw_sha,"source_html_bytes":len(raw),
 "source_2025_annual_county_table_index":target["table_number"],
 "all_html_table_row_count_candidates":candidates_table_sizes,
 "actual_county_source_records_2025_annual":58,
 "actual_county_code_name_matched_to_provisional_2847":len(joined),
 "county_name_unmapped":unmapped,"county_name_ambiguous":duplicated,
 "new_R4_partial_counties":new_count,"R4_total_partial_counties":existing_total,
 "R4_remaining_not_scanned_counties":2847-existing_total,
 "Fujian_2025_annual_city_level_PM25_O3_numeric_records":len(city_annual),
 "Fujian_city_source_records":city_annual,
 "county_source_records":joined,
 "parameter_semantics":{"PM25":"2025 annual mean μg/m3","good_days":"2025 percent",
 "O3_city":"2025 annual O3 MDA8 P90 μg/m3 if numeric city table",
 "O3_county":"NOT REPORTED NUMERICALLY in province county table; pollutant name only"},
 "historical_2025_roster_vs_actual_2026_legal_code_unchanged":True,
 "county_ozone_numeric_source_coverage":0,
 "full_2026_current_codes_officially_verified":False,
 "formal_valid_county_screenings":0,"confirmed_county_exclusions":0,
 "source_national_previous_sha256":sha(PREV.read_bytes()),
 "national_R4_register_sha256":sha(national.read_bytes()),
 "Fujian_58_county_csv_sha256":sha(single.read_bytes()),
 "limitations":["County city monitor measures represent urban monitoring network not every residential site",
 "City-scale 9+1 table ozone and PM2.5 not mapped to individual counties without exact county monitoring",
 "One 2025 year does not establish long-term 1991-2020 climate or multi-year pollutant persistence",
 "Ozone named primary pollutant does not constitute a numeric O3 measurement",
 "No official current national county roster certification; no fatal elimination by arbitrary PM2.5 thresholds"]}
out=OUT/"Fujian2025_official_R4_county_air_evidence.json"
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["actual_county_source_records_2025_annual","actual_county_code_name_matched_to_provisional_2847",
 "new_R4_partial_counties","R4_total_partial_counties",
 "R4_remaining_not_scanned_counties",
 "Fujian_2025_annual_city_level_PM25_O3_numeric_records","county_ozone_numeric_source_coverage"]},ensure_ascii=False),flush=True)
