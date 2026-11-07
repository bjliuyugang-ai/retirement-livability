#!/usr/bin/env python3
"""Real Fujian 2025 February and December centralized DRINKING-WATER SOURCE
intake monitoring in 109-site provincial source monthly reports.

This is UNPROCESSED source water at intake, not plant outlet and not residential
tap endpoint. Reports source-specific '达标', not numerical 29/62 lab parameter
values. Exact county-name crosswalk only; names of prefectural cities remain
city contextual evidence and are never allocated across all districts.

No missing status => safe/unsafe decision. No exclusions or formal grades.
"""
import collections,csv,datetime,hashlib,json,pathlib,urllib.request
from bs4 import BeautifulSoup
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
NAT=ROOT/"status/national_R4_official_Fujian2025_county_PM25_2847.csv"
FJ=ROOT/"status/Fujian2025_official_R4_county_air_evidence.json"
def sha(b):return hashlib.sha256(b).hexdigest()
fj=json.loads(FJ.read_text(encoding="utf-8"))
if not(fj["actual_county_source_records_2025_annual"]==58 and fj["formal_valid_county_screenings"]==0):
 raise RuntimeError("FJ county air predecessor not full or verified")
if sha(NAT.read_bytes())!=fj["national_R4_register_sha256"]:
 raise RuntimeError("R5 base full national registry SHA changed unexpectedly")
with NAT.open(encoding="utf-8-sig",newline="") as f:
 rd=csv.DictReader(f);fields=list(rd.fieldnames);rows=list(rd)
if len(rows)!=2847 or len({r["candidate_code"] for r in rows})!=2847:
 raise RuntimeError("National R5 input 2847 counts not preserved")
fj_byname=collections.defaultdict(list)
bycode={r["candidate_code"]:r for r in rows}
for row in rows:
 if row["candidate_code"].startswith("35"):fj_byname[row["candidate_name"]].append(row["candidate_code"])
reports={
 "2025-02":"https://sthjt.fujian.gov.cn/zwgk/sjfb/hjsj/yyssysz/202504/t20250402_6795837.htm",
 "2025-12":"https://sthjt.fujian.gov.cn/zwgk/sjfb/hjsj/yyssysz/202601/t20260126_7085249.htm"}
all_records=[];sources=[]
for month,url in reports.items():
 req=urllib.request.Request(url,headers={"User-Agent":"RetirementProvincialCountyWaterSOURCE2025Audit/1.0","Accept":"text/html,*/*"})
 with urllib.request.urlopen(req,timeout=90) as resp:raw=resp.read(2_000_000)
 if len(raw)<10000:raise RuntimeError("FJ raw water official HTML too short "+month)
 soup=BeautifulSoup(raw,"html.parser")
 target=None;cols=None
 for table in soup.find_all("table"):
  rr=table.find_all("tr")
  if not rr:continue
  hdr="|".join(cell.get_text(" ",strip=True) for cell in rr[0].find_all(["td","th"]))
  if "行政区划" in hdr and "点位名称" in hdr and "达标情况" in hdr:
   target=rr;cols=hdr;break
 if target is None:raise RuntimeError("Could not find raw source table columns "+month)
 extracted=[]
 for tr in target[1:]:
  vals=[t.get_text(" ",strip=True).replace("\xa0","") for t in tr.find_all(["td","th"])]
  if len(vals)<7 or not vals[0].strip().isdigit():continue
  z={"month":month,"index_in_month":int(vals[0]),"province":vals[1],"administrative_area":vals[2],
  "intake_source_name":vals[3],"source_water_type":vals[4],"water_body_type":vals[5],
  "reported_quality_conclusion":vals[6],
  "exceedance_indicator":vals[7] if len(vals)>7 else "",
  "source_url":url,"source_html_SHA256":sha(raw),
  "monitoring_stage":"RAW_WATER_AT_SOURCE_OR_INTAKE_NOT_TREATED_NOT_TAP"}
  if z["province"]!="福建省":raise RuntimeError("Not Fujian record "+str(z))
  extracted.append(z)
 if len(extracted)<90 or len(extracted)>130:raise RuntimeError("Expected ~109 source water intake sites, got "+str(len(extracted))+" month "+month)
 if len({x["index_in_month"] for x in extracted})!=len(extracted):
  raise RuntimeError("Duplicate row index in "+month)
 all_records.extend(extracted)
 sources.append({"month":month,"URL":url,"original_HTML_SHA256":sha(raw),"original_HTML_bytes":len(raw),
 "source_rows":len(extracted),"reported_dabiao_sites":sum(x["reported_quality_conclusion"]=="达标" for x in extracted),
 "county_names_n":len(set(x["administrative_area"] for x in extracted))})
 print("ACTUAL_FJ_RAW_WATER_SOURCE_MONTH",month,len(extracted),sources[-1]["reported_dabiao_sites"],flush=True)
# Prefer no numeric 2025 R5 values if not provided by source table.
county_points=collections.defaultdict(list);city_context=[];ambiguous=[];unknown=[]
for x in all_records:
 potential=fj_byname.get(x["administrative_area"],[])
 if len(potential)==1:county_points[potential[0]].append(x)
 elif len(potential)>1:ambiguous.append(x)
 else:
  if x["administrative_area"].endswith("市") or "实验区" in x["administrative_area"]:
   city_context.append(x)
  else:unknown.append(x)
if ambiguous:raise RuntimeError("Ambiguous county-level intake name source, no guessing")
if not county_points:raise RuntimeError("No county-level exact raw source water points linked")
extra=["R5_FJ_2025Feb_raw_intake_point_count","R5_FJ_2025Dec_raw_intake_point_count",
 "R5_FJ_2025Feb_raw_source_dabiao_count","R5_FJ_2025Dec_raw_source_dabiao_count",
 "R5_FJ_source_raw_water_not_tap","R5_FJ_source_provenance"]
for k in extra:
 if k in fields:raise RuntimeError("Prior county register already has R5 source field "+k)
fields+=extra
new=0;prior_existing=0
point_details=[]
for code,points in county_points.items():
 county=bycode[code]
 c2=[x for x in points if x["month"]=="2025-02"];c12=[x for x in points if x["month"]=="2025-12"]
 county["R5_FJ_2025Feb_raw_intake_point_count"]=len(c2)
 county["R5_FJ_2025Dec_raw_intake_point_count"]=len(c12)
 county["R5_FJ_2025Feb_raw_source_dabiao_count"]=sum(z["reported_quality_conclusion"]=="达标" for z in c2)
 county["R5_FJ_2025Dec_raw_source_dabiao_count"]=sum(z["reported_quality_conclusion"]=="达标" for z in c12)
 county["R5_FJ_source_raw_water_not_tap"]="TRUE"
 county["R5_FJ_source_provenance"]=";".join(reports.values())
 if county["R5_status"]=="NOT_SCREENED":
  county["R5_status"]="FJ_OFFICIAL_2025_RAW_DRINKING_WATER_SOURCE_INTAKE_MONITORING_NOT_TAP"
  county["R5_evidence_scope"]="RAW_WATER_SOURCE_INTAKE_NEITHER_TREATED_PLANT_OUTLET_NOR_RESIDENTIAL_TAP"
  county["R5_missing_parameters"]="TREATED_PLANT_WATER;NETWORK_ENDPOINT_MICROBIOLOGY_METALS;2026_LOCAL_WATER_ROUTE;INDUSTRIAL_HISTORIC_POLLUTION"
  new+=1
 else:prior_existing+=1
 point_details.append({"county_code":code,"county_name":county["candidate_name"],
  "Feb_points":len(c2),"Dec_points":len(c12),
  "Feb_reported_dabiao":county["R5_FJ_2025Feb_raw_source_dabiao_count"],
  "Dec_reported_dabiao":county["R5_FJ_2025Dec_raw_source_dabiao_count"],
  "source_type":"WATER_SOURCE_INTAKE_ONLY", "county_residential_tap_verified":False,
  "raw_intake_site_records":points})
if any(r["confirmed_exit_round"] or r["formal_grade"] or str(r["valid_county_screening"]).lower()=="true" for r in rows):
 raise RuntimeError("R5 water source excluded or graded county")
out=OUT/"national_R5_FJ_2025_FebDec_raw_source_county_2847.csv"
with out.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader();wr.writerows(rows)
pointcsv=OUT/"FJ_2025_FebDec_109_water_source_intake_rows.csv"
with pointcsv.open("w",encoding="utf-8-sig",newline="") as f:
 cols=list(all_records[0]);wr=csv.DictWriter(f,fieldnames=cols);wr.writeheader();wr.writerows(all_records)
total_r5_partial=sum(r["R5_status"]!="NOT_SCREENED" for r in rows)
report={"schema":"RET_FUJIAN_2025_FEB_DEC_109_WATER_SOURCE_INTAKES_RAW_NOT_TAP_V1",
 "asof_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "official_publisher":"福建省生态环境厅",
 "official_sources":sources,
 "monthly_original_raw_water_intake_rows_total":len(all_records),
 "county_monitoring_point_records":sum(len(v) for v in county_points.values()),
 "city_aggregate_source_point_records_not_assigned_to_counties":len(city_context),
 "unknown_administrative_source_names":sorted(set(x["administrative_area"] for x in unknown)),
 "unknown_administrative_source_site_rows":len(unknown),
 "ambiguous_name_sites_not_assigned":len(ambiguous),
 "distinct_2025_county_code_with_source_intake":len(county_points),
 "new_R5_county_source_intake_evidence_codes":new,
 "R5_prior_partial_codes_with_more_source_intakes":prior_existing,
 "R5_total_partial_evidence_counties_from_old_and_new":total_r5_partial,
 "full_county_candidates_carried_forward":2847,
 "source_quality_stage":"MONITORED_RAW_SURFACE_OR_GROUND_WATER_SOURCE_NOT_PLANT_OUTLET_NOT_NETWORK_TAP",
 "county_evidence_details":sorted(point_details,key=lambda x:x["county_code"]),
 "city_only_unmapped_point_details":city_context,
 "city_name_ambiguous_point_details":ambiguous,
 "source_national_R4_register_sha256":sha(NAT.read_bytes()),
 "all_source_point_csv_sha256":sha(pointcsv.read_bytes()),
 "full_national_R5_register_sha256":sha(out.read_bytes()),
 "treated_water_monitoring_units_acquired":0,
 "residential_tap_2025_water_quality_units_verified":0,
 "formal_valid_county_screenings":0,
 "confirmed_exclusions":0,
 "source_status":"ACTUAL_PROVINCE_OFFICIAL_TWO_MONTHS_RAW_WATER_SOURCE_SITE_MONITORING",
 "limitations":[
  "Site 达标 refers to source intake raw water under GB 3838 III or GB/T 14848 III; NEVER GB 5749 household drinking tap compliance",
  "Raw-source location may supply multiple counties and waterworks; the administrative area is a monitor label not a geographic water distribution footprint",
  "Two months are not annual or long-term safety proof; no chemical indicator concentrations supplied in source table",
  "City-area records are kept as city context, not distributed among county children",
  "No county grade, exclusion, or household safe-water claim; 2026 official current jurisdiction map still unverified"]}
(OUT/"FJ_2025_FebDec_official_raw_drinking_water_source_evidence.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({k:report[k] for k in ["monthly_original_raw_water_intake_rows_total",
 "county_monitoring_point_records","city_aggregate_source_point_records_not_assigned_to_counties",
 "distinct_2025_county_code_with_source_intake",
 "new_R5_county_source_intake_evidence_codes",
 "R5_total_partial_evidence_counties_from_old_and_new",
 "residential_tap_2025_water_quality_units_verified"]},ensure_ascii=False),flush=True)
