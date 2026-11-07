#!/usr/bin/env python3
"""R4/R5 independent parameter passes over national 2847 provisional county roster.

R4 uses source-cited 2025 environmental city/region evidence for two already
known counties. R5 uses 16 official Q1/Q3 2026 named tap-water observations in
one county, not dwelling-level complete water quality. Source gaps remain
unscanned, not disqualified. Each invocation processes ONE approved round only.
"""
import csv,datetime,hashlib,json,pathlib,sys
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
if len(sys.argv)!=2 or sys.argv[1] not in ("R4","R5"):raise SystemExit("usage: python national_r4_r5_source_steps.py R4|R5")
round_id=sys.argv[1]
if round_id=="R4":
    source=ROOT/"status/national_r3_first_real_batch.csv"
    prev=ROOT/"status/national_r3_first_real_batch_evidence.json"
    evidence=ROOT/"evidence/stage3_firstbatch_public_environment_evidence_20261107.json"
    gradefield="R4_status"
else:
    source=ROOT/"status/national_r4_city_context_batch.csv"
    prev=ROOT/"status/national_r4_city_context_evidence.json"
    evidence=ROOT/"evidence/stage3_mengzi_2026_tapwater_16_site_observations_v1.json"
    gradefield="R5_status"
before=json.loads(prev.read_text(encoding="utf-8"))
if round_id=="R4":
    if before["R3_carry_forward"]!=2847 or before["R3_DEM_three_point_counties"]!=12:raise RuntimeError("R3 source incomplete")
    expectedsha=before["csv_sha256"]
else:
    if before["R4_carry_forward"]!=2847 or before["R4_city_context_counties"]!=2:raise RuntimeError("R4 source incomplete")
    expectedsha=before["CSV_sha256"]
if sha(source.read_bytes())!=expectedsha:raise RuntimeError("Input R"+round_id+" national CSV digest mismatch")
with source.open(encoding="utf-8-sig",newline="") as f:
    r=csv.DictReader(f);cols=list(r.fieldnames);rows=list(r)
if len(rows)!=2847 or len({x["candidate_code"] for x in rows})!=2847:raise RuntimeError("Nationwide denominator changed")
bycode={x["candidate_code"]:x for x in rows}
src=json.loads(evidence.read_text(encoding="utf-8"))
records=[]
if round_id=="R4":
    added=["R4_city_annual_PM25_ug_m3","R4_city_good_air_day_rate_pct","R4_good_air_rate_source_conflict",
       "R4_2026_environment_source","R4_evidence_scope","R4_local_industrial_exposure_verified",
       "R4_missing_parameters"]
    for unit in src["units"]:
        code=unit["candidate_code_unverified"]
        if code not in bycode:raise RuntimeError("R4 candidate code not in provisional roster")
        row=bycode[code]
        if row["R4_status"]!="NOT_SCREENED":raise RuntimeError("Repeated R4 scan")
        air=unit.get("environment_2025") or unit.get("city_air_2025") or {}
        pm=air.get("pm25_annual_city_ug_m3")
        good=air.get("city_good_air_day_rate_pct")
        conflicting=air.get("air_good_day_rate_conflicting_in_same_document")
        row["R4_status"]="CITY_OR_REGIONAL_CONTEXT_ONLY_PENDING_RESIDENTIAL_QA"
        row["R4_evidence_scope"]="2025_CitywideOrRegional_NotDwelling"
        row["R4_city_annual_PM25_ug_m3"]=pm if pm is not None else ""
        row["R4_city_good_air_day_rate_pct"]=good if good is not None else ""
        row["R4_good_air_rate_source_conflict"]=" / ".join(str(x) for x in conflicting) if conflicting else ""
        row["R4_2026_environment_source"]=(air.get("source") or unit.get("remediation_2026",{}).get("source") or "")
        row["R4_local_industrial_exposure_verified"]="FALSE"
        row["R4_missing_parameters"]="RESIDENTIAL_PM25_O3;INDUSTRIAL_SOURCE_DIRECTION;HISTORIC_CONTAMINATED_LAND;CURRENT_OFFICIAL_CODE"
        row["missing_parameter_list"]="R1_R4_INCOMPLETE_SITE_QA;R5_UNSCANNED;2026_CODE_UNVERIFIED"
        row["cascade_status"]="ACTIVE_PENDING";row["last_completed_round"]="R4_CITY_CONTEXT"
        records.append({"code":code,"county":unit["county"],"annual_city_PM25_ug_m3":pm,
          "city_good_air_day_rate_pct":good,"air_rate_conflicts":conflicting,
          "air_source":air.get("source"),"industrial_source":unit.get("remediation_2026",{}).get("source"),
          "source_quality":"CITY_OR_REGION_ONLY_NOT_RESIDENTIAL",
          "current_city_air_rating_not_inferred":True,
          "confirmed_noncompensable_residential_risk":False})
    expected=2;next_round="R5"
else:
    added=["R5_monitoring_sites","R5_2026_Q1_Q3_official_tap_sample_rows",
       "R5_listed_indicators_within_reported_limits","R5_evidence_scope",
       "R5_full_GB5749_compliance_verified","R5_actual_building_supply_verified",
       "R5_missing_parameters"]
    if(src["summary"]["records"]!=16 or
       src["summary"]["monitored_sites"]!=8 or
       src["summary"]["observed_pass_listed_limits"]!=16):
       raise RuntimeError("Tap monitoring has nonmatching source totals")
    code="532503"
    row=bycode[code]
    if row["R5_status"]!="NOT_SCREENED":raise RuntimeError("Repeated R5 processing")
    row["R5_status"]="NAMED_CITY_TAP_MONITORING_POINTS_ONLY_PENDING_BUILDING_QA"
    row["R5_monitoring_sites"]=8
    row["R5_2026_Q1_Q3_official_tap_sample_rows"]=16
    row["R5_listed_indicators_within_reported_limits"]="16_OF_16_PUBLISHED_ROWS_ONLY"
    row["R5_evidence_scope"]="MONITORING_NAMED_TAP_POINTS_NOT_ACTUAL_HOUSEHOLDS"
    row["R5_full_GB5749_compliance_verified"]="FALSE"
    row["R5_actual_building_supply_verified"]="FALSE"
    row["R5_missing_parameters"]="BUILDING_SECONDARY_WATER_SUPPLY;FULL_GB5749_INDICATORS;FLOOD_AND_GEOHAZARD_MAP;CURRENT_OFFICIAL_CODE"
    row["cascade_status"]="ACTIVE_PENDING";row["last_completed_round"]="R5_NAMED_TAP_SAMPLES_ONLY"
    row["missing_parameter_list"]="R1_R5_ALL_CRITICAL_UNKNOWN_RETAINED_FOR_TARGETED_FOLLOWUP"
    records.append({"code":code,"county":"蒙自市","published_tap_records":16,
        "monitored_named_sites":8,"sampling_dates":["2026-03-02","2026-09-01/2026-09-17"],
        "within_source_table_limits":16,"complete_potable_water_standard_verified":False,
        "residential_building_supply_verified":False,
        "hazard_spatial_overlay_completed":False,"county_climate_grade_authorized":False})
    expected=1;next_round="FINAL_GAP_LIST"
for key in added:
    if key in cols:raise RuntimeError("Round field already exists: "+key)
cols+=added
n=sum(x[gradefield]!="NOT_SCREENED" for x in rows)
pending=sum(x[gradefield]=="NOT_SCREENED" for x in rows)
if n!=expected or pending!=2847-expected:raise RuntimeError("Scan counts do not reconcile")
if any(x["confirmed_exit_round"] for x in rows) or any(x["valid_county_screening"].lower()=="true" for x in rows):
    raise RuntimeError("Unjustified exclusion or formal county grading detected")
name="national_r4_city_context" if round_id=="R4" else "national_r5_tap_water"
csvpath=OUT/(name+"_batch.csv")
with csvpath.open("w",encoding="utf-8-sig",newline="") as f:
 w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
result={"schema":"RET_NATIONAL_"+round_id+"_PARTIAL_CITED_EVIDENCE_V1",
"at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"source_CSV_sha256":expectedsha,"evidence_source":str(evidence),
"evidence_source_sha256":sha(evidence.read_bytes()),
"input":2847,round_id+"_carry_forward":2847,
round_id+"_confirmed_exclusions":0,
round_id+"_unscanned":pending,
round_id+"_direct_evidence_counties":n,
"formal_valid_county_screenings":0,"formal_grade_changes":0,
"source_level":"REGIONAL_OR_NAMED_SITE_NOT_RESIDENTIAL_OR_WHOLE_COUNTY",
"records":records,"CSV_sha256":sha(csvpath.read_bytes()),
"next_parameter_round":next_round,
"limitations":["No missing parameter means exclusion",
 "Citywide/regional environmental quality is not dwelling-level exposure",
 "Named tap monitoring cannot prove whole municipality drinking water safety",
 "All previously recorded errors and source references retained in national ledger"]}
if round_id=="R4":result["R4_city_context_counties"]=n
else:result["R5_named_tap_monitoring_counties"]=n
jsonpath=OUT/(name+"_evidence.json")
jsonpath.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"round":round_id,"with_actual_context":n,"not_scanned":pending,"carry_forward":2847,
"source_scope":result["source_level"],"confirmed_exits":0,"formal":0},ensure_ascii=False),flush=True)
