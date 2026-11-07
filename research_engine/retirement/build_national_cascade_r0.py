#!/usr/bin/env python3
"""Create persistent R0 2847-county *provisional* queue, no climate screening claimed.

The source is a 2025 third-party mirror with two provincial 2026 legal notices;
not an authenticated complete national 2026 official roster.
"""
import csv,datetime,hashlib,json,pathlib
ROOT=pathlib.Path("research_engine/retirement")
OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
INPUT=OUT/"provisional_counties_2026_06.csv"
SUMMARY=OUT/"provisional_roster_summary.json"
if not INPUT.exists() or not SUMMARY.exists():
 raise RuntimeError("Missing generated 2026 provisional roster; run provisional_roster.py first")
summ=json.loads(SUMMARY.read_text(encoding="utf-8"))
if summ.get("status")!="PASS_PROVISIONAL_ROSTER_BUILD" or summ.get("provisional_2026_midyear_count")!=2847:
 raise RuntimeError("Unverified provisional roster")
with INPUT.open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
if len(rows)!=2847 or len({x["code"] for x in rows})!=2847:raise RuntimeError("Wrong R0 national provisional unique count")
if hashlib.sha256(INPUT.read_bytes()).hexdigest()!=summ["csv_sha256"]:raise RuntimeError("Roaster source file SHA mismatch")
cols=["geography_id","candidate_code","candidate_name","admin_vintage","source_class","official_current_code_verified",
      "cascade_status","last_completed_round","R1_status","R2_status","R3_status","R4_status","R5_status",
      "confirmed_exit_round","confirmed_exit_reason","confirmed_exit_evidence",
      "reinstatement_condition","missing_parameter_list","formal_grade","valid_county_screening"]
outrows=[]
for r in rows:
 outrows.append({"geography_id":"PROVISIONAL_COUNTY_"+r["code"],"candidate_code":r["code"],"candidate_name":r["name"],
  "admin_vintage":r["asof"],"source_class":r["source_class"],
  "official_current_code_verified":False,"cascade_status":"ACTIVE_PENDING",
  "last_completed_round":"R0_PROVISIONAL_INVENTORY_ONLY",
  "R1_status":"NOT_SCREENED","R2_status":"NOT_SCREENED","R3_status":"NOT_SCREENED",
  "R4_status":"NOT_SCREENED","R5_status":"NOT_SCREENED",
  "confirmed_exit_round":"","confirmed_exit_reason":"","confirmed_exit_evidence":"",
  "reinstatement_condition":"",
  "missing_parameter_list":"R1_R5_CLIMATE_AND_ENVIRONMENT_UNSCANNED;OFFICIAL_2026_CODE_UNVERIFIED",
  "formal_grade":"","valid_county_screening":False})
p=OUT/"national_cascade_r0_provisional.csv"
with p.open("w",encoding="utf-8-sig",newline="") as f:
 w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(outrows)
d={"schema":"RET_NATIONAL_STAGED_FILTER_R0_V1","generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "input_source":"research_engine/retirement/output/provisional_counties_2026_06.csv",
 "input_sha256":summ["csv_sha256"],"output_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
 "pilot_scope":"PROVISIONAL_NATIONAL_R0_2026_06",
 "candidate_count":len(outrows),"unscanned_parameter_counties":len(outrows),
 "verified_exclusions":0,"formal_valid_county_screenings":0,
 "2026_official_national_county_roster_verified":False,
 "eligible_for_exploratory_R1":True,
 "R1_rule":"only actual climate evidence creates R1 scanning outcomes; NOT_SCREENED must never be treated as MISSING_SCREENED or effective national coverage",
 "future_round_rule":"each R(n+1) input must equal prior R(n) carry-forward, excluding only verified fatal with audited exception and source",
 "note":"Only an administrative candidate queue, not valid climate screening. Missing values are carried to later rounds, not eliminated, and cannot be conflated with scanned-unresolved records."}
(OUT/"national_cascade_r0_summary.json").write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(d,ensure_ascii=False))
