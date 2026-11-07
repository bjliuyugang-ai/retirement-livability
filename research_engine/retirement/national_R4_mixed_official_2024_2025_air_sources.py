#!/usr/bin/env python3
"""Consolidated nationwide source-level R4 environmental evidence register.

Merge 168 MEE official CITY-level 2025 annual PM25 values (parent city context),
official 2024/25 Beijing PM25/O3/good-air-day context, and Fujian Provincial
Ecology Department 58 county-level 2024/25 annual PM25/good-air-day measurements,
plus 10 Fujian municipal O3 pairs. There are NO inferred county O3 values.
County-level official air statistics are NOT home or neighborhood monitoring.
No county exclusions and no formal stage 1 A/B/C/D labels.
"""
import collections,csv,datetime,hashlib,json,pathlib
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/"status/national_R4_city_PM25_2025_Beijing_O3_2024_2025_2847_CONTEXT_ONLY.csv"
BJS=ROOT/"status/mee_official_2024_2025_Beijing_O3_air_QA.json"
CITY=ROOT/"status/mee_2025_168_official_city_PM25_context_evidence.json"
FJ=ROOT/"status/Fujian2024_2025_air_pollution_two_year_evidence.json"
FJ2025=ROOT/"status/Fujian2025_official_R4_county_air_evidence.json"
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_text(encoding="utf-8"))
bj=read(BJS);c=read(CITY);fj=read(FJ);fj25=read(FJ2025)
if not(bj["annual_city_O3_2025_direct_source_cities"]==1 and c["2025_year_annual_priority_city_sample_count"]==168
 and c["provisional_counties_with_parent_2025_city_pm25_CONTEXT_ONLY"]==1510
 and fj["county_twoyear_matched"]==58 and fj["city_twoyear_matched"]==10
 and fj25["actual_county_source_records_2025_annual"]==58
 and sha(BASE.read_bytes())==bj["new_national_R4_context_csv_sha256"]):
 raise RuntimeError("Official source crosswalk or full R4 base changed")
with BASE.open(encoding="utf-8-sig",newline="") as f:
 rd=csv.DictReader(f);fields=list(rd.fieldnames);rows=list(rd)
bycode={r["candidate_code"]:r for r in rows}
if len(rows)!=2847 or len(bycode)!=2847:raise RuntimeError("Official national county evidence count is not 2847")
fjcounty={str(z["code"]):z for z in fj["county_twoyear_records"]}
if len(fjcounty)!=58:raise RuntimeError("Fujian 58 two-year county codes not unique")
fj2025county={str(z["candidate_code"]):z for z in fj25["county_source_records"]}
if len(fj2025county)!=58 or set(fjcounty)!=set(fj2025county):
 raise RuntimeError("Fujian annual county sources do not agree on 58 unique codes")
for code,rec in fjcounty.items():
 if code not in bycode or bycode[code]["candidate_name"]!=rec["name"]:
  raise RuntimeError("Fujian local county named record drift "+code)
 if float(rec["PM25_2025"])!=float(fj2025county[code]["PM25_annual_ugm3"]):
  raise RuntimeError("Fujian two independent 2025 report structures disagree "+code)
fjcity={z["city"]:z for z in fj["city_twoyear_records"]}
if len(fjcity)!=10:raise RuntimeError("Fujian ten city O3 year rows not uniquely represented")
fields_add=["R4_FJ_COUNTY_PM25_2024_ugm3","R4_FJ_COUNTY_PM25_2025_ugm3",
 "R4_FJ_COUNTY_GOOD_DAYS_2024_pct","R4_FJ_COUNTY_GOOD_DAYS_2025_pct",
 "R4_FJ_COUNTY_TWOYEAR_2025minus2024_PM25_ugm3",
 "R4_FJ_COUNTY_2024_2025_official_source",
 "R4_FJ_COUNTY_O3_NUMERIC_NOT_PUBLISHED",
 "R4_OFFICIAL_CITY_O3_2024_upstream_context_only",
 "R4_OFFICIAL_CITY_O3_2025_upstream_context_only",
 "R4_OFFICIAL_CITY_O3_SOURCE_SCOPE_NOT_COUNTY"]
for col in fields_add:
 if col in fields:raise RuntimeError("Combined R4 output collides with prior column "+col)
fields+=fields_add
# City O3 named '平潭区' is NOT a prefecture city code in historical 2025:
# only attach prefecture-named towns when official parent CITY name matches.
fj_pref_city_context=0
county_fj_direct_count=0;county_fj_with_city_o3_context=0;beijing_context_count=0
missing_fj_city_map=[]
for city,obs in fjcity.items():
 if "O3_2024" not in obs or "O3_2025" not in obs:
  raise RuntimeError("Fujian O3 two-year city data absent "+city)
for row in rows:
 code=row["candidate_code"]
 if code in fjcounty:
  v=fjcounty[code]
  county_fj_direct_count+=1
  row["R4_FJ_COUNTY_PM25_2024_ugm3"]=v["PM25_2024"]
  row["R4_FJ_COUNTY_PM25_2025_ugm3"]=v["PM25_2025"]
  row["R4_FJ_COUNTY_GOOD_DAYS_2024_pct"]=v["good_days_2024_pct"]
  row["R4_FJ_COUNTY_GOOD_DAYS_2025_pct"]=v["good_days_2025_pct"]
  row["R4_FJ_COUNTY_TWOYEAR_2025minus2024_PM25_ugm3"]=v["PM25_change_2025_minus_2024"]
  row["R4_FJ_COUNTY_2024_2025_official_source"]=v["source24"]+" ; "+v["source25"]
  row["R4_FJ_COUNTY_O3_NUMERIC_NOT_PUBLISHED"]="TRUE"
  if row["R4_status"]=="NOT_SCREENED":
   row["R4_status"]="FJ_OFFICIAL_COUNTY_ANNUAL_PM25_GOODDAYS_2024_2025_PARTIAL_NOT_RESIDENTIAL"
   row["R4_evidence_scope"]="COUNTY_YEARLY_MONITORING_UNIT_NOT_INDIVIDUAL_RESIDENCE"
   row["R4_missing_parameters"]="COUNTY_O3_NUMERIC;INDUSTRIAL_HISTORIC_EXPOSURE;RESIDENTIAL_LOCATION;2026_OFFICIAL_GEOMETRY"
  else:
   if not row["R4_status"].startswith("FJ_"):raise RuntimeError("Unexpected existing R4 county source intersects Fujian "+code)
 # Only Beijing source city O3 from prior BASE; keep unchanged.
 if row["R4_Beijing_city_2025_O3_context_only"]:
  beijing_context_count+=1
  row["R4_OFFICIAL_CITY_O3_2024_upstream_context_only"]=row["R4_Beijing_city_2024_O3_context_only"]
  row["R4_OFFICIAL_CITY_O3_2025_upstream_context_only"]=row["R4_Beijing_city_2025_O3_context_only"]
  row["R4_OFFICIAL_CITY_O3_SOURCE_SCOPE_NOT_COUNTY"]="BEIJING_MUNICIPALITY_ONLY"
 # Mainland FJ nine prefecture cities have explicit name and code 35xx00;
 # reject district-level Pingtan as not a matching official prefecture.
 city=row["R4_official_2025_parent_city_name"]
 if city and city in fjcity:
  o=fjcity[city]
  row["R4_OFFICIAL_CITY_O3_2024_upstream_context_only"]=o["O3_2024"]
  row["R4_OFFICIAL_CITY_O3_2025_upstream_context_only"]=o["O3_2025"]
  row["R4_OFFICIAL_CITY_O3_SOURCE_SCOPE_NOT_COUNTY"]="FUJIAN_CITY_REPORT_ONLY"
  fj_pref_city_context+=1
  if code in fjcounty:county_fj_with_city_o3_context+=1
 if row["confirmed_exit_round"] or row["formal_grade"] or str(row["valid_county_screening"]).lower()=="true":
  raise RuntimeError("Unauthorized county grade/elimination in R4 combined")
if county_fj_direct_count!=58 or beijing_context_count!=16:raise RuntimeError("Fujian count or Beijing municipal code mapping failed")
# Non-fatal source status count = existing 2 regional + actual 58 county.
count_r4_partial_source=sum(r["R4_status"]!="NOT_SCREENED" for r in rows)
if count_r4_partial_source!=60:raise RuntimeError("Expected 2 old + 58 genuine Fujian R4 partial records, got "+str(count_r4_partial_source))
outcsv=OUT/"national_R4_2847_168city_PM25_58county_PM25_10city_O3_source_layers.csv"
with outcsv.open("w",encoding="utf-8-sig",newline="") as f:
 writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
city_o3_grouped=[]
for name,rec in sorted(fjcity.items()):
 city_o3_grouped.append({"name":name,"O3_2024":rec["O3_2024"],"O3_2025":rec["O3_2025"],
 "PM25_2024":rec["PM25_2024"],"PM25_2025":rec["PM25_2025"],
 "2025_minus_2024_O3":rec["O3_2025"]-rec["O3_2024"],
 "city_not_county_residential":True})
report={"schema":"RET_R4_NATIONAL_MULTISOURCE_2024_2025_CITY_O3_COUNTY_PM25_2847_V1",
 "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_2025_MEE_168_cities_JSON_SHA256":sha(CITY.read_bytes()),
 "source_Beijing_2024_2025_O3_JSON_SHA256":sha(BJS.read_bytes()),
 "source_Fujian_county_2024_2025_JSON_SHA256":sha(FJ.read_bytes()),
 "source_Fujian_county_2025_JSON_SHA256":sha(FJ2025.read_bytes()),
 "source_2847_city_context_base_csv_sha256":sha(BASE.read_bytes()),
 "MEE_2025_168_priority_cities_annual_PM25":168,
 "county_candidates_with_PARENT_city_2025_PM25_BACKGROUND_ONLY":1510,
 "official_Fujian_direct_COUNTY_PM25_good_days_2024_2025_units":58,
 "official_Fujian_named_10_urban_O3_2024_2025_units":10,
 "official_Beijing_city_O3_2024_2025_units":1,
 "all_named_urban_O3_yearly_2024_2025_source_units":11,
 "county_codes_given_Beijing_CITY_O3_only_context":beijing_context_count,
 "county_codes_given_Fujian_CITY_O3_only_context":fj_pref_city_context,
 "Fujian_county_PM25_units_with_city_level_O3_context":county_fj_with_city_o3_context,
 "combined_long_city_or_real_county_R4_partial_source_codes":count_r4_partial_source,
 "actual_county_level_2024_2025_PM25_monitoring_units":58,
 "actual_county_level_numerical_ozone_available":0,
 "direct_RESIDENTIAL_air_quality_counties":0,
 "2026_official_national_current_county_roster_verified":False,
 "Fujian_2025_county_PM25_decreased_count":fj["county_PM25_decreased"],
 "Fujian_2025_county_PM25_increased_count":fj["county_PM25_increased"],
 "Fujian_2025_county_PM25_unchanged_count":fj["county_PM25_unchanged"],
 "Fujian_2025_city_O3_increased_count":fj["city_O3_increased"],
 "Fujian_2025_city_O3_decreased_count":fj["city_O3_decreased"],
 "Fujian_O3_two_year_source_values":city_o3_grouped,
 "output_national_CSV_sha256":sha(outcsv.read_bytes()),
 "all_2847_county_candidates_carried_forward":2847,
 "confirmed_exclusions":0,"formal_valid_county_screenings":0,
 "limitations":[
  "168 named city PM2.5 source cells visually transcribed from six original MEE annual annex image pages and need a second independent digit-by-digit review",
  "Only 58 Fujian county monitoring unit PM2.5 and good-air-day values have numerical 2024 and 2025 official tabular sources; no county ozone numerical values",
  "Fujian city ozone and Beijing annual ozone cannot be used as county/home ozone",
  "Fujian region 2024 vs 2025 PM2.5 and O3 may have different station coverage and should not be interpreted as residential causal effects",
  "Historic 2025 adcodes are source-mapped; current 2026 official polygons and neighborhood industrial pollution are unverified",
  "R4_status records existing 2 non-residential city/region contexts plus 58 Fujian county partial statistical monitors; does NOT mean any county has completed R4"
 ]}
(OUT/"national_R4_168cities_58counties_11urbanO3_composite_evidence.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({k:report[k] for k in ["MEE_2025_168_priority_cities_annual_PM25","county_candidates_with_PARENT_city_2025_PM25_BACKGROUND_ONLY","official_Fujian_direct_COUNTY_PM25_good_days_2024_2025_units","official_Fujian_named_10_urban_O3_2024_2025_units","official_Beijing_city_O3_2024_2025_units","county_codes_given_Fujian_CITY_O3_only_context","Fujian_county_PM25_units_with_city_level_O3_context","combined_long_city_or_real_county_R4_partial_source_codes","confirmed_exclusions"]},ensure_ascii=False),flush=True)
