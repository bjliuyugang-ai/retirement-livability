#!/usr/bin/env python3
"""Quarantine unsuitable NASA POWER custom climatology Tmax/MIN_AVG metrics.

Direct same-coordinate 2019-2020 daily vs same-period climatology reveals
climatology MAX_AVG 3-11 C higher than mean of actual daily maxima.
All 30 source records retained with hashes, but 20 new locations are NOT
promoted to R1 scanning; canonical 2847 current ledger unchanged.
"""
import csv,datetime,hashlib,json,pathlib
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
QA=ROOT/"status/nasa_daily_vs_climatology_semantic_QA.json"
RAW=ROOT/"status/national_R1_NASA_CUSTOM_30_result.json"
ORIGINAL=ROOT/"status/national_r5_tap_water_batch.csv"
ORIG_SUM=ROOT/"status/national_r5_tap_water_evidence.json"
def sha(b):return hashlib.sha256(b).hexdigest()
qa=json.loads(QA.read_text(encoding="utf-8"));raw=json.loads(RAW.read_text(encoding="utf-8"))
s=json.loads(ORIG_SUM.read_text(encoding="utf-8"))
if not(qa["semantic_qa_status"]=="INCONSISTENT_EXPECTED_DAILY_EXTREME_AVERAGES"
 and qa["months_with_differences_ge2c"]==4
 and raw["successful_1991_2020_TMAX_AND_TMIN_MODEL_POINTS"]==30
 and raw["new_R1_NASA_secondary_model_counties"]==20
 and raw["already_ERA5_with_NASA_comparison_count"]==10
 and raw["NASA_ERA5_conflict_ge3c_count"]==10
 and s["R5_carry_forward"]==2847 and sha(ORIGINAL.read_bytes())==s["CSV_sha256"]):
 raise RuntimeError("Raw metric QA preconditions not satisfied")
with ORIGINAL.open(encoding="utf-8-sig",newline="") as f:
 reader=csv.DictReader(f);fields=list(reader.fieldnames);rows=list(reader)
bycode={x["candidate_code"]:x for x in rows}
additional=["NASA_original_source_raw_sha256","NASA_original_custom_period_verified",
 "NASA_source_model_quality","NASA_unusable_climate_TMAX_AVG","NASA_unusable_climate_TMIN_AVG",
 "NASA_sameyear_semantic_QA","NASA_winter_model_value_not_accepted_c",
 "NASA_summer_model_value_not_accepted_c"]
for k in additional:
 if k in fields:raise RuntimeError("Unexpected existing NASA QA column "+k)
fields+=additional
for rec in raw["county_results"]:
 code=rec["code"];r=bycode[code]
 if r["candidate_name"]!=rec["county"]:raise RuntimeError("Name changed in historic code crosswalk "+code)
 r["NASA_original_source_raw_sha256"]=rec["source_raw_sha256"]
 r["NASA_original_custom_period_verified"]="TRUE"
 r["NASA_source_model_quality"]="QUARANTINED_UNRESOLVED_SEMANTIC_MISMATCH"
 r["NASA_unusable_climate_TMAX_AVG"]="TRUE"
 r["NASA_unusable_climate_TMIN_AVG"]="TRUE"
 r["NASA_sameyear_semantic_QA"]=str(QA)
 r["NASA_winter_model_value_not_accepted_c"]=rec["NASA_winter_tmax_c"]
 r["NASA_summer_model_value_not_accepted_c"]=rec["NASA_summer_tmax_c"]
 if not rec["previous_ERA5_data"] and r["R1_status"]!="NOT_SCREENED":
  raise RuntimeError("NASA-only source unexpectedly received qualified R1 mark "+code)
counts=sum(x["R1_status"]!="NOT_SCREENED" for x in rows)
if counts!=22 or len(rows)!=2847 or any(x["confirmed_exit_round"] for x in rows):
 raise RuntimeError("R1 canonical record contamination: "+str(counts))
p=OUT/"national_R1_NASA_custom_QUARANTINED_2847_audit.csv"
with p.open("w",encoding="utf-8-sig",newline="") as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
report={"schema":"RET_NASA_POWER_CUSTOM_METRICS_QUARANTINED_V1",
 "at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "same_year_daily_vs_climatology_QA":str(QA),
 "same_year_test_point":"Linan", "same_year_test_period":"2019-2020",
 "observed_direct_max_average_discrepancies_c":[x["difference_clim_minus_daily_max_c"] for x in qa["comparisons"]],
 "same_year_months_compared":[x["month"] for x in qa["comparisons"]],
 "same_year_months_outside_2c_tolerance":qa["months_with_differences_ge2c"],
 "source_custom_point_climatology_requested":30,
 "source_custom_point_climatology_responses_received":30,
 "already_ERA5_sites_compared":10,
 "NASA_ERA5_overlap_ge3c_conflicts":10,
 "NASA_only_data_sites_REJECTED_for_R1_screening":20,
 "new_acceptable_R1_temperature_screenings":0,
 "canonical_R1_exploratory_ERA5_point_counties_retained":22,
 "canonical_R1_not_scanned_counties":2825,
 "provisional_county_candidates":2847,
 "formal_valid_county_screenings":0,
 "confirmed_county_exclusions":0,
 "final_Master_changes":0,
 "quality_status":"QUARANTINED_NASA_CUSTOM_MAXAVG_MINAVG_UNTIL_INDEPENDENT_SEMANTICS_RESOLVED",
 "regional_API_conflict":"Regional response header 2001-2025 ignored requested 1991-2020, excluded earlier",
 "canonical_ledger_input":str(ORIGINAL),
 "canonical_input_sha256":sha(ORIGINAL.read_bytes()),
 "corrected_2847_audit_csv_sha256":sha(p.read_bytes()),
 "source_raw_30_summary":str(RAW),
 "original_raw_source_retrievable_via_run":"42323013085",
 "reason":"At same coordinate and 2019-2020 daily NASA T2M_MAX mean disagreed with NASA climatology T2M_MAX_AVG by 3-11 C. API values cannot be used as direct average daily Tmax or screen thresholds without resolving aggregation and elevation.",
 "next_data_source_priority":"Find official long-term station or independently verified bulk monthly/daily data with explicit daily extremes averaging and county crosswalk."}
out=OUT/"national_R1_NASA_custom_QUARANTINE_evidence.json"
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"quarantined_raw_points":30,"new_R1_accepted":0,
 "R1_ERA5_exploratory_retained":22,"R1_unknown":2825,
 "same_year_differences_c":report["observed_direct_max_average_discrepancies_c"]},ensure_ascii=False),flush=True)
