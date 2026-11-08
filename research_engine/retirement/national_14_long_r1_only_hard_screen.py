#!/usr/bin/env python3
"""Screen the remaining 14 long-period R1 candidates and consolidate all 214 R1 candidates."""
from __future__ import annotations
import csv,json,hashlib,datetime,pathlib,collections
S=pathlib.Path("research_engine/retirement/status")
OVERLAY=S/"national_R1_meteostat_coded_county_candidate_overlay_2847.csv"
LONG73=S/"national_73_longer_R1_R2_climate_ideal_preference_triage.csv"
SCREEN73=S/"national_73_existing_evidence_hard_screen_20261108.csv"
SHORT127=S/"national_127_short_history_R1_hard_screen_20261108.csv"
SHORTSUN=S/"national_126_short_history_R2_sunshine_review_20261108.csv"
ALT205=S/"national_205_altitude_point_hardline_review_20261108.csv"
OUT14=S/"national_14_long_R1_only_hard_screen_20261108.csv"
OUT214=S/"national_214_R1_all_evidence_hard_screen_20261108.csv"
OUTJSON=S/"national_214_R1_hardline_signal_rollup_20261108.json"
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def rd(p):
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def num(v):
 if v is None or str(v).strip()=="":return None
 x=float(v)
 return x if x==x and abs(x)!=float("inf") else None
def main():
 overlay=rd(OVERLAY);long73=rd(LONG73);screen73=rd(SCREEN73);short127=rd(SHORT127)
 shortsun=rd(SHORTSUN);alt205=rd(ALT205)
 sunby={x["candidate_code"]:x for x in shortsun}
 longcodes={x["candidate_code"] for x in long73}
 observed=[x for x in overlay if x.get("R1_status") not in ("","NOT_SCREENED")]
 remain=[x for x in observed if x["candidate_code"] not in longcodes]
 if len(observed)!=87 or len(remain)!=14:raise RuntimeError(f"Expected 87 observed R1, 14 remaining; got {len(observed)}/{len(remain)}")
 # All 14 must be disjoint from the 127 short-history R1 candidates.
 shortcodes={x["candidate_code"] for x in short127}
 if len(shortcodes)!=127 or shortcodes&longcodes or shortcodes&{x["candidate_code"] for x in remain}:
  raise RuntimeError("R1 cohort disjointness/cardinality check failed")
 altby={x["candidate_code"]:x for x in alt205}
 out14=[]
 for x in remain:
  station_w=num(x.get("R1_meteostat_winter_tmax_station_c"))
  station_s=num(x.get("R1_meteostat_summer_tmax_station_c"))
  era_w=num(x.get("R1_winter_max_mean_c"))
  era_s=num(x.get("R1_summer_jun_sep_max_mean_c"))
  w=station_w if station_w is not None else era_w
  s=station_s if station_s is not None else era_s
  wh=w is not None and w<10
  sh=s is not None and s>=32
  a=altby.get(x["candidate_code"])
  altwarn=(a is not None and a.get("point_over_2000m")=="True")
  out14.append({
   "candidate_code":x["candidate_code"],"candidate_name":x["candidate_name"],
   "R1_evidence_scope":x.get("R1_evidence_scope"),
   "source_type":"METEOSTAT_30Y_STATION" if station_w is not None else "ERA5_1991_2020_INTERIOR_GRID_POINT",
   "station_ids":x.get("R1_meteostat_station_ids"),
   "observed_months":num(x.get("R1_meteostat_observation_months_min")),
   "winter_dec_feb_mean_daily_tmax_c":w,"winter_lt10_signal":wh,
   "summer_jun_sep_mean_daily_tmax_c":s,"summer_ge32_signal":sh,
   "altitude_point_over2000m_warning":altwarn,
   "annual_sunshine_hours":num(x.get("R2_annual_sunshine_hours")),
   "sunshine_lt1800_signal":num(x.get("R2_annual_sunshine_hours")) is not None and num(x.get("R2_annual_sunshine_hours"))<1800,
   "hardline_signal":";".join([k for k,b in [("WINTER_LT_10C",wh),("SUMMER_GE_32C",sh)] if b]),
   "preliminary_classification":"PRELIMINARY_TEMPERATURE_HARDLINE_SIGNAL" if wh or sh else "NO_TEMPERATURE_TRIGGER_SUNSHINE_PENDING",
   "formal_region_exclusion":False,
   "note":"Station/ERA5 point is not a verified residential micro-area; no sunshine evidence for most R1-only cases; one-sided threshold signal only."
  })
 with OUT14.open("w",encoding="utf-8-sig",newline="") as f:
  wr=csv.DictWriter(f,fieldnames=list(out14[0]));wr.writeheader();wr.writerows(out14)
 # Normalize 73 long + 127 short + 14 remaining into a 214-row R1 evidence register.
 allrows=[]
 for x in screen73:
  w=num(x.get("winter_dec_feb_mean_daily_max_c"));s=num(x.get("summer_jun_sep_mean_daily_max_c"));sun=num(x.get("annual_sunshine_hours"))
  allrows.append({"candidate_code":x["candidate_code"],"candidate_name":x["candidate_name"],
   "history_tier":"LONGER_SOURCE_1991_2020_STATION_OR_ERA5_PARTIAL",
   "winter_mean_daily_tmax_c":w,"winter_lt10_signal":bool(x.get("winter_hardline_signal")=="True"),
   "summer_mean_daily_tmax_c":s,"summer_ge32_signal":bool(x.get("summer_hardline_signal")=="True"),
   "annual_sunshine_hours":sun,"sunshine_lt1800_signal":bool(x.get("sunshine_hardline_signal")=="True"),
   "altitude_point_over2000m_warning":bool(x.get("altitude_point_over2000m_signal")=="True"),
   "source_scope":x.get("evidence_tier"),"formal_region_exclusion":False})
 for x in short127:
  allrows.append({"candidate_code":x["candidate_code"],"candidate_name":x["candidate_name"],
   "history_tier":"INTERIM_180_MONTHS_NOT_FULL_30_YEAR",
   "winter_mean_daily_tmax_c":num(x.get("winter_dec_feb_mean_daily_tmax_c")),
   "winter_lt10_signal":bool(x.get("winter_lt10_signal")=="True"),
   "summer_mean_daily_tmax_c":num(x.get("summer_jun_sep_mean_daily_tmax_c")),
   "summer_ge32_signal":bool(x.get("summer_ge32_signal")=="True"),
   "annual_sunshine_hours":num(sunby.get(x["candidate_code"],{}).get("sunshine_annual_hours_interim")),
   "sunshine_lt1800_signal":bool(sunby.get(x["candidate_code"],{}).get("sunshine_lt1800_signal")=="True"),
   "altitude_point_over2000m_warning":bool(x.get("altitude_point_over2000m_warning")=="True"),
   "source_scope":"Meteostat interim station observations; 180+ months with monthly coverage gate",
   "formal_region_exclusion":False})
 for x in out14:
  allrows.append({"candidate_code":x["candidate_code"],"candidate_name":x["candidate_name"],
   "history_tier":"LONGER_R1_ONLY_STATION_OR_ERA5_PARTIAL",
   "winter_mean_daily_tmax_c":x["winter_dec_feb_mean_daily_tmax_c"],
   "winter_lt10_signal":x["winter_lt10_signal"],
   "summer_mean_daily_tmax_c":x["summer_jun_sep_mean_daily_tmax_c"],
   "summer_ge32_signal":x["summer_ge32_signal"],
   "annual_sunshine_hours":x["annual_sunshine_hours"],
   "sunshine_lt1800_signal":x["sunshine_lt1800_signal"],
   "altitude_point_over2000m_warning":x["altitude_point_over2000m_warning"],
   "source_scope":x["R1_evidence_scope"],"formal_region_exclusion":False})
 if len(allrows)!=214 or len({x["candidate_code"] for x in allrows})!=214:
  raise RuntimeError(f"Expected 214 unique R1 candidates, got {len(allrows)}/{len({x['candidate_code'] for x in allrows})}")
 with OUT214.open("w",encoding="utf-8-sig",newline="") as f:
  wr=csv.DictWriter(f,fieldnames=list(allrows[0]));wr.writeheader();wr.writerows(allrows)
 w=sum(x["winter_lt10_signal"] for x in allrows)
 s=sum(x["summer_ge32_signal"] for x in allrows)
 su=sum(x["sunshine_lt1800_signal"] for x in allrows)
 climate=[x for x in allrows if x["winter_lt10_signal"] or x["summer_ge32_signal"] or x["sunshine_lt1800_signal"]]
 alt=[x for x in allrows if x["altitude_point_over2000m_warning"]]
 sun_measured=sum(x["annual_sunshine_hours"] is not None for x in allrows)
 summary={
  "schema":"RET_PHASE1_ALL_214_R1_CANDIDATES_HARDLINE_SIGNAL_ROLLUP_V1",
  "created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "action_id":"RET-CASCADE-NATIONAL-14-LONG-R1-ONLY-AND-214-ROLLUP-020",
  "source_sha256":{"national_R1_overlay_2847":sha(OVERLAY),"long_R1R2_73":sha(LONG73),
   "screened_long73":sha(SCREEN73),"short_R1_127":sha(SHORT127),"short_R2_sunshine_126":sha(SHORTSUN),
   "altitude_205":sha(ALT205)},
  "cohort":{"long_R1R2_screened":73,"short_R1_screened":127,"remaining_long_R1_only":14,
   "all_R1_candidates_screened":len(allrows),"unique_codes":len({x["candidate_code"] for x in allrows})},
  "remaining_14_counts":{"winter_lt10":sum(x["winter_lt10_signal"] for x in out14),
   "summer_ge32":sum(x["summer_ge32_signal"] for x in out14),
   "temperature_union_signal":sum(x["winter_lt10_signal"] or x["summer_ge32_signal"] for x in out14),
   "no_temperature_trigger":sum(not x["winter_lt10_signal"] and not x["summer_ge32_signal"] for x in out14)},
  "all_214_counts":{"winter_lt10":w,"summer_ge32":s,"sunshine_lt1800":su,
   "union_any_climate_hardline_signal":len(climate),"no_climate_hardline_signal":214-len(climate),
   "annual_sunshine_measured":sun_measured,"annual_sunshine_missing":214-sun_measured,
   "altitude_point_over2000m_warning":len(alt),
   "climate_or_altitude_point_warning_union":len({x["candidate_code"] for x in climate+alt}),
   "formal_region_exclusions":0},
  "hardline_signal_candidates":[{"code":x["candidate_code"],"name":x["candidate_name"],
   "tier":x["history_tier"],"winter":x["winter_lt10_signal"],"summer":x["summer_ge32_signal"],
   "sunshine":x["sunshine_lt1800_signal"]} for x in climate],
  "no_climate_signal_candidates":[{"code":x["candidate_code"],"name":x["candidate_name"],
   "tier":x["history_tier"],"sunshine_measured":x["annual_sunshine_hours"] is not None} for x in allrows if x not in climate],
  "limitations":["214 are the subset of national candidate counties with existing R1 point evidence, not all 2847 counties and not a residential-region list.",
   "Long and interim histories remain tiered; the interim tier is not a full 30-year normal.",
   "Winter/summer fields are multi-month means of monthly mean daily maximum; crossing is a one-sided signal, non-crossing is not proof of pass.",
   "Sunshine is available only where directly observed; rainfall is never substituted for sunshine.",
   "Station/ERA5/DEM points are not verified residential micro-areas; no irreversible region exclusion is made.",
   "All 2847 provisional county rows remain in the evidence register until a specific residential evaluation unit is confirmed."]
 }
 OUTJSON.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"status":"PASS","remaining14":len(out14),
  "remaining14_winter_lt10":summary["remaining_14_counts"]["winter_lt10"],
  "remaining14_summer_ge32":summary["remaining_14_counts"]["summer_ge32"],
  "all214":len(allrows),"winter_lt10":w,"summer_ge32":s,"sun_lt1800":su,
  "climate_union":len(climate),"sun_measured":sun_measured,"altitude_warnings":len(alt),
  "climate_or_altitude_union":summary["all_214_counts"]["climate_or_altitude_point_warning_union"],
  "formal_exclusions":0},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
