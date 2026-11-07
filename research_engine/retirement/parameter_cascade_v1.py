#!/usr/bin/env python3
"""User-approved R0-R5 parameter-by-parameter screening cascade prototype.

Runs on 4 historically matched counties and frozen 11 ERA5 points. This is an
execution-mechanism validation, NOT 4 formally valid nationwide county screens.
Proven fatal exits require all eight explicit proof gates and preserve history.
"""
import csv,datetime,hashlib,json,pathlib

ROOT=pathlib.Path("research_engine/retirement")
OUT=ROOT/"output"
OUT.mkdir(parents=True,exist_ok=True)
FIRST=ROOT/"status/latest-first-batch-prescreen.json"
ANCHOR=ROOT/"status/stage3_firstbatch_residential_anchor_audit_v1.json"
WATER=ROOT/"evidence/stage3_mengzi_2026_tapwater_16_site_observations_v1.json"
RULES=pathlib.Path("research_assets/retirement/STAGED_PARAMETER_CASCADE_V1.0_20261107.md")
ROUND_ORDER=[
 ("R1","temperature_extremes"),
 ("R2","sunshine_humidity_rain"),
 ("R3","actual_residence_altitude_local_exception"),
 ("R4","air_industry_historical_pollution"),
 ("R5","tapwater_natural_hazards")]
FATAL_REQUIRED=["approved_rule_id","evidence_refs","credible_source",
                "residential_spatial_scope_verified","duration_or_permanence_verified",
                "mitigation_and_local_exceptions_reviewed","irreversible_or_not_feasibly_compensable",
                "reinstatement_condition"]

def hashfile(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verified_fatal(event):
    if not event or event.get("indicator_status")!="VERIFIED_FATAL":return False
    if not all(k in event for k in FATAL_REQUIRED):return False
    if not isinstance(event["evidence_refs"],list) or not event["evidence_refs"]:return False
    if not isinstance(event["approved_rule_id"],str) or not event["approved_rule_id"].strip():return False
    if not isinstance(event["reinstatement_condition"],str) or not event["reinstatement_condition"].strip():return False
    for key in ["credible_source","residential_spatial_scope_verified",
                "duration_or_permanence_verified","mitigation_and_local_exceptions_reviewed",
                "irreversible_or_not_feasibly_compensable"]:
        if event.get(key) is not True:return False
    return True

def test_guards():
    event={"indicator_status":"VERIFIED_FATAL","approved_rule_id":"SYNTHETIC_QA_HARD_RULE",
       "evidence_refs":["SYNTHETIC_ONLY"],"credible_source":True,
       "residential_spatial_scope_verified":True,"duration_or_permanence_verified":True,
       "mitigation_and_local_exceptions_reviewed":True,
       "irreversible_or_not_feasibly_compensable":True,
       "reinstatement_condition":"new independent evidence overturns prior risk"}
    assert verified_fatal(event),"Expected fully evidenced fatal"
    for k in FATAL_REQUIRED:
        bad=dict(event);bad.pop(k)
        assert not verified_fatal(bad),"Missing gate must prevent exclusion: "+k
    assert not verified_fatal({"indicator_status":"PREFERENCE_MISMATCH"}),"Preferences cannot kill"
    assert not verified_fatal({"indicator_status":"MISSING"}),"Unknown cannot kill"
    return "10 synthetic checks passed; tests do not assert real county elimination"

def measure(row,round_id,anchors,water):
    key=row["site"];matched=row["points_meeting_three_climate_preferences"]
    points=row["point_count_used"]
    if round_id=="R1":
        winter=row["winter_daytime_max_range_c"];summer=row["summer_daytime_max_range_c"]
        return {"indicator_status":"PREFERENCE_MISMATCH" if not (18<=winter[0] and winter[1]<=25 and 25<=summer[0] and summer[1]<=29) else "PASS_SUPPORTED",
          "evidence_type":"1991-2020_ERA5_MODEL_POINT_NOT_RESIDENCE",
          "values":{"winter_mean_daily_max_c_range":winter,"summer_mean_daily_max_c_range":summer,
                    "points_checked":points,"nonofficial_geography":True},
          "missing_fields":["site-specific 1991-2020 station normals","actual residential locations",
            "continuous hot/cold stress episodes",">=35C annual days"],
          "source_refs":[str(FIRST)],
          "reason":"One or more modeled grid points miss an ideal preference band; not a verified whole-county exclusion"}
    if round_id=="R2":
        return {"indicator_status":"MISSING",
          "evidence_type":"partial_ERA5_model_humidity_only",
          "values":{"ERA5_annual_relative_humidity_pct_range":row["humidity_range_pct"],
            "number_of_climate_preference_matches":matched},
          "missing_fields":["reliable yearly and winter sunshine from observed station",
             "verified wet-day/continuous overcast counts","rainfall base-period validation",
             "site-calibrated relative humidity and dewpoint"],
          "source_refs":[str(FIRST)],
          "reason":"Model humidity does not stand in for independent observed sunshine, wet days or residential humidity"}
    if round_id=="R3":
        return {"indicator_status":"MISSING",
           "evidence_type":"three DEM samples in historic county polygon, not confirmed residential buildings",
           "values":{"sample_dem_span_m":row["geometric_dem_span_m"],"geography_exception_required":True},
           "missing_fields":["site-specific real residential altitude","river-valley/plateau/urban-subdistrict exception map",
             "sample-to-polygon/ERA5 grid-independent QA"],
           "source_refs":[str(FIRST)],
           "reason":"One high DEM sample is not a basis for excluding a whole county"}
    if round_id=="R4":
        context=next((a for a in anchors.get("units",[]) if a["county"]==row["county"]),None)
        return {"indicator_status":"MISSING",
           "evidence_type":"city-scale public context only" if context else "no local environment evidence",
           "values":{"public_source_context_available":bool(context)},
           "missing_fields":["site-specific multi-year PM2.5 and ozone","industrial source-to-residence distance and wind",
             "historical contaminated land survey"],
           "source_refs":[str(ANCHOR)] if context else [],
           "reason":"City-wide air figures or industrial remediation notices do not prove residential exposure"}
    if round_id=="R5":
        is_mz=key=="Mengzi"
        anchors_count=sum(len(a["focused_residential_anchors"]) for a in anchors["units"] if a["county"]==row["county"])
        return {"indicator_status":"MISSING",
           "evidence_type":"partial official tap-sampling at named points" if is_mz else "no verified site-level complete tap data",
           "values":{"named_test_anchors":anchors_count,"2026_q1_q3_monitored_site_records":water["summary"]["records"] if is_mz else 0},
           "missing_fields":["actual building water supply connection and full drinking-water indicators",
             "on-site flood and landslide hazards","seismic and extreme-weather avoidability",
             "2026 officially verified administrative identity"],
           "source_refs":[str(ANCHOR),str(WATER)] if is_mz else ([str(ANCHOR)] if anchors_count else []),
           "reason":"Limited monitoring samples and municipal source quality cannot close all residential safety gates"}
    raise ValueError("unknown round "+round_id)

def run():
    first=json.loads(FIRST.read_text(encoding="utf-8"))
    anchors=json.loads(ANCHOR.read_text(encoding="utf-8"))
    water=json.loads(WATER.read_text(encoding="utf-8"))
    if (first.get("preliminary_point_records")!=11 or
        first.get("stage3_preliminary_county_units")!=4 or
        first.get("valid_county_screenings")!=0 or
        anchors["summary"]["valid_county_screenings"]!=0):
        raise RuntimeError("Pilot evidence scope or formal-data guard mismatched")
    base=first["county_rows"]
    if len({r["archival_code"] for r in base})!=4:raise RuntimeError("Duplicate county key")
    items={}
    for row in base:
        key=row["archival_code"]
        items[key]={"geography_id":"HISTORIC_COUNTY_CANDIDATE_"+key,
          "county":row["county"],"archival_candidate_code":key,
          "official_2026_county_code_verified":False,
          "existing_master_provisional_grade_unchanged":row["prior_master_provisional_grade"],
          "formal_grade":None,"formal_county_screening_valid":False,
          "queue_status":"ACTIVE_PENDING","exit_round":None,"exit_reason":None,
          "exit_evidence":[],"reinstatement_condition":None,"rounds":{},
          "missing_parameters":[],"conflicting_parameters":[],
          "prior_stage3_preliminary":row["stage3_first_batch_preliminary"],
          "evidence_quality":"EXPLORATORY_NOT_RESIDENTIAL",
          "local_exception_review_status":"NOT_COMPLETE"}
    active=list(items.keys());logs=[];exclusions=[]
    for round_id,param in ROUND_ORDER:
        n_in=len(active);next_active=[];new_excluded=0;n_pending=0
        for key in active:
            row=next(x for x in base if x["archival_code"]==key)
            r=measure(row,round_id,anchors,water)
            record={**r,"round":round_id,"parameter":param,"verified_fatal_claim":False}
            items[key]["rounds"][round_id]=record
            items[key]["missing_parameters"].extend(
                [round_id+":"+x for x in r["missing_fields"]])
            if verified_fatal(r):
                record["verified_fatal_claim"]=True
                items[key]["queue_status"]="EXCLUDED_THIS_ROUND"
                items[key]["exit_round"]=round_id
                items[key]["exit_reason"]=r["reason"]
                items[key]["exit_evidence"]=r["evidence_refs"]
                items[key]["reinstatement_condition"]=r["reinstatement_condition"]
                exclusions.append({"county":items[key]["county"],"exit_round":round_id,
                    "reason":r["reason"],"evidence":r["evidence_refs"],
                    "reinstatement_condition":r["reinstatement_condition"]})
                new_excluded+=1
            else:
                next_active.append(key)
                if r["missing_fields"] or r["indicator_status"] in ["MISSING","CONFLICT","PREFERENCE_MISMATCH"]:
                    items[key]["queue_status"]="ACTIVE_PENDING";n_pending+=1
                else:items[key]["queue_status"]="ACTIVE_RETAIN"
        if n_in!=len(next_active)+new_excluded:raise RuntimeError("Cascade conservation failure")
        logs.append({"round":round_id,"parameter":param,"input":n_in,
            "new_verified_exits":new_excluded,"carry_forward":len(next_active),
            "carry_forward_pending":n_pending,
            "total_cumulative_exits":len(exclusions),
            "missing_does_not_stop_other_counties":True})
        active=next_active
    for item in items.values():
        if item["queue_status"]!="EXCLUDED_THIS_ROUND":
            item["queue_status"]="FINAL_PENDING_USER_REVIEW"
    if len(active)+len(exclusions)!=len(items):raise RuntimeError("Pilot conservation failed")
    output={"schema":"RET_STAGED_PARAMETER_CASCADE_V1",
     "generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
     "scope":"11 existing exploratory points, 4 historic candidate counties, method-validation only",
     "user_decision":"Continue each parameter round despite missing data; verified fatal cases leave future routine collection; final unknowns remain for user decision",
     "official_national_coverage_count":0,"valid_county_screenings":0,"formal_grades_changed":0,
     "input_units":len(items),"surviving_candidate_units":len(active),
     "verified_exclusions":len(exclusions),"pending_units":sum(x["queue_status"]=="FINAL_PENDING_USER_REVIEW" for x in items.values()),
     "round_summary":logs,"excluded_archive":exclusions,
     "missing_parameter_count":sum(len(x["missing_parameters"]) for x in items.values()),
     "evidence_input_hashes":{str(p):hashfile(p) for p in [FIRST,ANCHOR,WATER,RULES]},
     "hard_exclusion_gate_regression":test_guards(),
     "records":list(items.values()),"limitations":[
       "All 4 sampled counties are retained pending because no formally certified unmitigable exclusion was evidenced",
       "This test does not replace 20 existing provisional Master grades",
       "ERA5 preference mismatches are not D verdicts and cannot exclude residential areas",
       "Administrative national coverage, microclimate exception checks and official station verification remain open"
     ]}
    out=OUT/"staged_parameter_cascade_v1.json"
    out.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    csvpath=OUT/"staged_parameter_cascade_v1.csv"
    cols=["geography_id","county","archival_candidate_code","existing_master_provisional_grade_unchanged",
          "R1","R2","R3","R4","R5","queue_status","exit_round","exit_reason","reinstatement_condition",
          "missing_parameters","formal_grade","formal_county_screening_valid"]
    with csvpath.open("w",encoding="utf-8-sig",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=cols);wr.writeheader()
        for v in output["records"]:
            d={k:v.get(k) for k in cols}
            for r,_ in ROUND_ORDER:d[r]=v["rounds"][r]["indicator_status"] if r in v["rounds"] else "SKIPPED_EARLIER_VERIFIED_EXIT"
            d["missing_parameters"]="; ".join(v["missing_parameters"])
            wr.writerow(d)
    print(json.dumps({"status":"CASCADE_PILOT_PASS","input":len(items),"rounds":len(logs),
          "retained":len(active),"excluded_verified":len(exclusions),"pending":output["pending_units"],
          "missing_parameter_entries":output["missing_parameter_count"],
          "formal":output["valid_county_screenings"]},ensure_ascii=False))
if __name__=="__main__":run()
