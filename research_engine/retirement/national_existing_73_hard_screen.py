#!/usr/bin/env python3
"""Apply the user's confirmed Phase-1 hard lines to the existing 73-candidate
1991-2020 longer-source climate cohort and join existing 205-point altitude
evidence. This is a conservative signal screen, not a residential-site grade.
"""
from __future__ import annotations
import csv, json, hashlib, datetime, pathlib, collections

ROOT=pathlib.Path("research_engine/retirement")
STATUS=ROOT/"status"
CLIMATE=STATUS/"national_73_longer_R1_R2_climate_ideal_preference_triage.csv"
ALTITUDE=STATUS/"national_R3_205_station_dem_point_evidence.csv"
OUTCSV=STATUS/"national_73_existing_evidence_hard_screen_20261108.csv"
OUTALT=STATUS/"national_205_altitude_point_hardline_review_20261108.csv"
OUTJSON=STATUS/"national_73_existing_evidence_hard_screen_20261108.json"

WINTER_LIMIT=10.0
SUMMER_LIMIT=32.0
SUN_LIMIT=1800.0
ALTITUDE_LIMIT=2000.0

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def read_csv(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def number(v):
    if v is None or str(v).strip()=="": return None
    x=float(v)
    if x!=x or abs(x)==float("inf"): return None
    return x

def json_numbers(v):
    if not v or str(v).strip()=="": return []
    x=json.loads(v)
    if not isinstance(x,list): raise RuntimeError("Expected JSON array in altitude evidence")
    return [float(z) for z in x if z is not None]

def main():
    climate=read_csv(CLIMATE)
    altitude=read_csv(ALTITUDE)
    if len(climate)!=73 or len({r["candidate_code"] for r in climate})!=73:
        raise RuntimeError("73-candidate source count/uniqueness check failed")
    if len(altitude)!=205 or len({r["candidate_code"] for r in altitude})!=205:
        raise RuntimeError("205-point altitude source count/uniqueness check failed")
    alt_by={r["candidate_code"]:r for r in altitude}
    if not all(r["candidate_code"] in alt_by for r in climate):
        raise RuntimeError("A 73-candidate climate row has no altitude join")
    result=[]
    counts=collections.Counter()
    trigger_codes=set()
    altitude_codes=set()
    for r in climate:
        code=r["candidate_code"]
        a=alt_by[code]
        winter=number(r.get("winter_12_2_daily_high_c"))
        summer=number(r.get("summer_6_9_daily_high_c"))
        sunshine=number(r.get("annual_sun_hours"))
        winter_hit=winter is not None and winter<WINTER_LIMIT
        summer_hit=summer is not None and summer>=SUMMER_LIMIT
        sun_hit=sunshine is not None and sunshine<SUN_LIMIT
        station_alt=json_numbers(a.get("station_point_elevation_m"))
        dem_alt=json_numbers(a.get("dem_three_point_sample_elevations_m"))
        point_alts=station_alt+dem_alt
        altitude_hit=any(x>ALTITUDE_LIMIT for x in point_alts)
        climate_hits=[]
        if winter_hit: climate_hits.append("WINTER_LT_10C")
        if summer_hit: climate_hits.append("SUMMER_GE_32C")
        if sun_hit: climate_hits.append("SUNSHINE_LT_1800H")
        if climate_hits: trigger_codes.add(code)
        if altitude_hit: altitude_codes.add(code)
        all_three=all(x is not None for x in [winter,summer,sunshine])
        if climate_hits:
            classification="PRELIMINARY_CLIMATE_HARD_LINE_TRIGGER"
        elif altitude_hit:
            classification="RESIDENTIAL_ALTITUDE_SITE_CHECK_REQUIRED"
        elif not all_three:
            classification="PENDING_MISSING_CLIMATE_PARAMETER"
        else:
            classification="NO_TRIGGER_IN_THREE_MEASURED_CLIMATE_PARAMETERS"
        result.append({
            "candidate_code":code,"candidate_name":r["county"],
            "evidence_tier":"1991-2020 longer source; station observation or ERA5 point, source preserved",
            "winter_dec_feb_mean_daily_max_c":winter,"winter_threshold_c":WINTER_LIMIT,
            "winter_hardline_signal":winter_hit,"winter_source":r.get("winter_source",""),
            "summer_jun_sep_mean_daily_max_c":summer,"summer_threshold_c":SUMMER_LIMIT,
            "summer_hardline_signal":summer_hit,"summer_source":r.get("summer_source",""),
            "annual_sunshine_hours":sunshine,"sunshine_threshold_hours":SUN_LIMIT,
            "sunshine_hardline_signal":sun_hit,"sunshine_source":r.get("sun_source",""),
            "station_point_altitudes_m":json.dumps(station_alt,ensure_ascii=False),
            "dem_sample_altitudes_m":json.dumps(dem_alt,ensure_ascii=False),
            "altitude_point_over_2000m_signal":altitude_hit,
            "residential_altitude_verified":a.get("residential_elevation_verified","False"),
            "hardline_parameters_triggered":";".join(climate_hits),
            "first_pass_classification":classification,
            "formal_region_exclusion":False,
            "why_not_formal":"Station/grid/DEM points are not yet verified as the actual residential micro-area; winter/summer fields are multi-month means, so threshold crossings are one-sided conservative signals. Confirm exact residential site before final removal.",
            "missing_or_next_check":";".join([x for x,missing in [
                ("SUNSHINE",sunshine is None),("RESIDENTIAL_SITE_TEMPERATURE",True),
                ("RESIDENTIAL_ALTITUDE",a.get("residential_elevation_verified","False")!="True"),
                ("DAILY_GE35_DAYS",True),("OFFICIAL_BOUNDARY_AND_MICROCLIMATE",True)] if missing])
        })
        counts[classification]+=1
    if len(result)!=73: raise RuntimeError("Output cohort cardinality changed")
    cols=list(result[0])
    with OUTCSV.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(result)

    alt_out=[]
    all_high=[]
    for a in altitude:
        station_alt=json_numbers(a.get("station_point_elevation_m"))
        dem_alt=json_numbers(a.get("dem_three_point_sample_elevations_m"))
        vals=station_alt+dem_alt
        over=[x for x in vals if x>ALTITUDE_LIMIT]
        if over: all_high.append(a["candidate_code"])
        alt_out.append({
            "candidate_code":a["candidate_code"],"candidate_name":a["candidate_name"],
            "station_point_altitudes_m":json.dumps(station_alt,ensure_ascii=False),
            "dem_three_point_altitudes_m":json.dumps(dem_alt,ensure_ascii=False),
            "point_min_m":min(vals) if vals else None,"point_max_m":max(vals) if vals else None,
            "point_over_2000m":bool(over),"over_2000m_values":json.dumps(over,ensure_ascii=False),
            "residential_elevation_verified":a.get("residential_elevation_verified","False"),
            "interpretation":"POINT_WARNING_ONLY; not county-wide or residential-site exclusion"
        })
    with OUTALT.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(alt_out[0]));w.writeheader();w.writerows(alt_out)

    full=[x for x in result if x["annual_sunshine_hours"] is not None]
    climate_clear=[x for x in full if not (x["winter_hardline_signal"] or x["summer_hardline_signal"] or x["sunshine_hardline_signal"])]
    no_climate_hit_sun_missing=[x for x in result if x["annual_sunshine_hours"] is None and not x["winter_hardline_signal"] and not x["summer_hardline_signal"]]
    climate_union=len(trigger_codes)
    combined=len(trigger_codes|altitude_codes)
    summary={
        "schema":"RET_PHASE1_EXISTING_73_CANDIDATE_HARDLINE_SIGNAL_SCREEN_V1",
        "created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "action_id":"RET-CASCADE-NATIONAL-73-EXISTING-EVIDENCE-HARD-SCREEN-018",
        "input_climate_count":len(climate),"input_altitude_point_count":len(altitude),
        "thresholds":{"winter_cold_season_mean_daily_max_lt_c":WINTER_LIMIT,
          "summer_warm_season_mean_daily_max_ge_c":SUMMER_LIMIT,
          "annual_sunshine_lt_hours":SUN_LIMIT,"residential_altitude_gt_m":ALTITUDE_LIMIT},
        "metric_logic":"Winter Dec-Feb mean of monthly mean daily maximum below 10C proves at least one winter month is below the line; summer Jun-Sep mean at or above 32C proves at least one summer month reaches the line. These are conservative one-sided triggers; non-trigger is not a pass for the coldest/hottest month.",
        "source_sha256":{"climate_73":sha(CLIMATE),"altitude_205":sha(ALTITUDE)},
        "climate_hardline_counts":{
          "winter_below_10c":sum(x["winter_hardline_signal"] for x in result),
          "summer_at_or_above_32c":sum(x["summer_hardline_signal"] for x in result),
          "sunshine_below_1800h":sum(x["sunshine_hardline_signal"] for x in result),
          "union_any_climate_hardline_signal":climate_union},
        "altitude_point_counts":{"all_205_points_over_2000m":len(all_high),
          "within_73_cohort_over_2000m":len(altitude_codes),
          "within_73_cohort_altitude_only_no_climate_trigger":len(altitude_codes-trigger_codes)},
        "cohort_outcomes":{"climate_all_three_parameters_measured":len(full),
          "no_climate_hardline_signal_among_complete":len(climate_clear),
          "no_known_climate_trigger_but_sunshine_missing":len(no_climate_hit_sun_missing),
          "union_climate_or_altitude_point_warning":combined,
          "formal_region_exclusions":0},
        "preliminary_climate_trigger_candidates":[{"code":x["candidate_code"],"name":x["candidate_name"],
          "triggers":x["hardline_parameters_triggered"]} for x in result if x["hardline_parameters_triggered"]],
        "altitude_only_review_candidates":[{"code":x["candidate_code"],"name":x["candidate_name"],
          "station_altitudes_m":x["station_point_altitudes_m"],"dem_altitudes_m":x["dem_sample_altitudes_m"]}
          for x in result if x["altitude_point_over_2000m_signal"] and not x["hardline_parameters_triggered"]],
        "complete_climate_no_trigger_candidates":[{"code":x["candidate_code"],"name":x["candidate_name"]}
          for x in climate_clear],
        "missing_sunshine_no_other_climate_trigger":[{"code":x["candidate_code"],"name":x["candidate_name"]}
          for x in no_climate_hit_sun_missing],
        "all_2847_national_candidates_carry_forward":True,
        "formal_valid_county_screenings":0,"confirmed_county_exclusions":0,
        "interpretation":"This batch is an actual hard-line signal application to the 73 strongest longer-source R1/R2 candidates, not a complete national or residential-site certification. The 56 climate-hit cohort members should leave the relevant sample shortlist once the same signal is confirmed at the intended residential micro-area; they are not put in D. Three additional altitude-only cases require residential elevation separation. Missing values remain PENDING, never D or fail.",
        "limitations":["The cohort is 73 higher-evidence county candidates, not the full national candidate pool.",
          "Winter and summer are multi-month averages of mean daily maximum; they only provide one-sided conservative triggers for coldest/hottest-month lines.",
          "Station/grid/DEM points are not verified residential micro-areas; high altitude at one point cannot eliminate an entire county or basin.",
          "Annual sunshine is unavailable for some candidates; missing is PENDING.",
          "Daily >=35C day count, actual residential altitude, pollution, water and disaster risk remain separate checks.",
          "No formal county grade or irreversible region exclusion is made in this run."]
    }
    OUTJSON.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","climate_candidates":len(result),
      "winter_lt10":summary["climate_hardline_counts"]["winter_below_10c"],
      "summer_ge32":summary["climate_hardline_counts"]["summer_at_or_above_32c"],
      "sun_lt1800":summary["climate_hardline_counts"]["sunshine_below_1800h"],
      "climate_union":climate_union,"altitude_over2000_all205":len(all_high),
      "altitude_over2000_within73":len(altitude_codes),"combined_signals":combined,
      "complete_climate_no_trigger":len(climate_clear),
      "missing_sun_no_other_trigger":len(no_climate_hit_sun_missing),
      "formal_exclusions":0},ensure_ascii=False),flush=True)

if __name__=="__main__": main()
