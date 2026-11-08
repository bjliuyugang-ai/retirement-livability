#!/usr/bin/env python3
"""Apply Phase-1 hard-line signals to 127 short-history R1 and 126 short-history R2 candidates."""
from __future__ import annotations
import csv,json,hashlib,datetime,pathlib,collections
ROOT=pathlib.Path("research_engine/retirement")
STATUS=ROOT/"status"
R1JSON=STATUS/"meteostat_CN_226_R1_tiered_expansion_evidence.json"
R1CSV=STATUS/"meteostat_CN_226_station_spatial_period_quality.csv"
R2JSON=STATUS/"meteostat_CN132_interim_R2_evidence.json"
ALTCSV=STATUS/"national_R3_205_station_dem_point_evidence.csv"
LONG73=STATUS/"national_73_existing_evidence_hard_screen_20261108.csv"
OUTR1=STATUS/"national_127_short_history_R1_hard_screen_20261108.csv"
OUTR2=STATUS/"national_126_short_history_R2_sunshine_review_20261108.csv"
OUTJSON=STATUS/"national_short_history_hard_screen_20261108.json"
WINTER=10.0;SUMMER=32.0;SUN=1800.0;ALT=2000.0

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def readcsv(p):
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def num(v):
 if v is None or str(v).strip()=="":return None
 x=float(v)
 return x if x==x and abs(x)!=float("inf") else None

def main():
 r1=json.loads(R1JSON.read_text(encoding="utf-8"))
 r2=json.loads(R2JSON.read_text(encoding="utf-8"))
 stations=readcsv(R1CSV);altrows=readcsv(ALTCSV);long=readcsv(LONG73)
 codes=set(r1["new_interim_county_codes"])
 r1rows=[x for x in stations if x["coded_candidate_code"] in codes and x["accept_for_interim_partial_R1"]=="True"]
 if len(r1rows)!=127 or len({x["coded_candidate_code"] for x in r1rows})!=127:
  raise RuntimeError(f"R1_SHORT_127_SCHEMA_FAIL rows={len(r1rows)} unique={len({x['coded_candidate_code'] for x in r1rows})}")
 longcodes={x["candidate_code"] for x in long}
 if codes & longcodes:raise RuntimeError("Short and long cohorts overlap; stop rather than double-count")
 r2codes=set(r2["new_interim_R2_codes"])
 if len(r2codes)!=126:raise RuntimeError("Expected 126 new short R2 codes")
 groups=collections.defaultdict(list)
 for x in r2["station_parameter_results"]:
  if x["candidate_code"] in r2codes:groups[x["candidate_code"]].append(x)
 if len(groups)!=126:raise RuntimeError(f"R2_SHORT_126_JOIN_FAIL unique={len(groups)}")
 # Choose the source row with most valid sunshine months, then precipitation months.
 # Never average two stations; retain all station IDs in the output.
 r2selected={}
 for code,items in groups.items():
  items=sorted(items,key=lambda x:(int(x.get("R2_observation_sunshine_months") or 0),
    int(x.get("R2_observation_precip_months") or 0)),reverse=True)
  r2selected[code]=items[0]
 altby={x["candidate_code"]:x for x in altrows}
 out1=[];w_hits=[];s_hits=[];alt_hits=set()
 for x in r1rows:
  code=x["coded_candidate_code"]
  w=num(x.get("winter_mean_daily_tmax_c"));s=num(x.get("summer_mean_daily_tmax_c"))
  wh=w is not None and w<WINTER
  sh=s is not None and s>=SUMMER
  a=altby.get(code)
  altwarn=(a is not None and a.get("high_station_or_DEM_point_over_2000_m")=="True") or (num(x.get("station_elevation_m")) is not None and num(x.get("station_elevation_m"))>ALT)
  if wh:w_hits.append(code)
  if sh:s_hits.append(code)
  if altwarn:alt_hits.add(code)
  out1.append({
   "candidate_code":code,"candidate_name":x["coded_candidate_name"],"station_id":x["station_id"],
   "station_lat":x.get("station_lat"),"station_lon":x.get("station_lon"),
   "station_elevation_m":num(x.get("station_elevation_m")),
   "observed_months_in_1991_2020_window":num(x.get("obs_month_count_in_1991_2020_range")),
   "minimum_observed_years_per_calendar_month":num(x.get("min_per_calendar_month_obs_years")),
   "history_tier":"INTERIM_180_MONTHS_10_PER_CALENDAR_MONTH_NOT_FULL_30_YEAR_NORMAL",
   "winter_dec_feb_mean_daily_tmax_c":w,"winter_lt10_signal":wh,
   "summer_jun_sep_mean_daily_tmax_c":s,"summer_ge32_signal":sh,
   "altitude_point_over2000m_warning":altwarn,
   "residential_altitude_verified":False,
   "preliminary_classification":"PRELIMINARY_TEMPERATURE_HARDLINE_SIGNAL" if wh or sh else ("RESIDENTIAL_ALTITUDE_CHECK_REQUIRED" if altwarn else "NO_TEMPERATURE_TRIGGER_PENDING_SUNSHINE"),
   "formal_region_exclusion":False,
   "note":"15-year/interim observations are not a 1991-2020 full normal; multi-month mean daily Tmax threshold crossings are one-sided signals; station point is not residential micro-area."
  })
 cols=list(out1[0])
 with OUTR1.open("w",encoding="utf-8-sig",newline="") as f:
  wr=csv.DictWriter(f,fieldnames=cols);wr.writeheader();wr.writerows(out1)
 out2=[];sunfail=[];sunpass=[]
 for code in sorted(r2codes):
  x=r2selected[code]
  v=num(x.get("R2_sunshine_rough_annual_hours_during_available_years"))
  months=num(x.get("R2_observation_sunshine_months"))
  hit=v is not None and v<SUN
  if hit:sunfail.append(code)
  if v is not None and not hit:sunpass.append(code)
  out2.append({
   "candidate_code":code,"candidate_name":x.get("candidate_name"),
   "selected_station_id":x.get("station_id"),
   "all_station_ids_for_candidate":";".join(sorted({z.get("station_id","") for z in groups[code]})),
   "sunshine_annual_hours_interim":v,"sunshine_observed_months":months,
   "sunshine_lt1800_signal":hit,"precipitation_annual_mm_context_only":num(x.get("R2_precip_rough_annual_mm_during_available_years")),
   "history_tier":"INTERIM_SHORT_HISTORY_NOT_FULL_30_YEAR_NORMAL",
   "classification":"PRELIMINARY_SUNSHINE_HARDLINE_SIGNAL" if hit else ("SUNSHINE_NO_TRIGGER_IN_AVAILABLE_DATA" if v is not None else "SUNSHINE_NO_DATA_PENDING"),
   "formal_region_exclusion":False,
   "note":"Rainfall is context only and is not substituted for sunshine; missing sunshine is PENDING."
  })
 with OUTR2.open("w",encoding="utf-8-sig",newline="") as f:
  wr=csv.DictWriter(f,fieldnames=list(out2[0]));wr.writeheader();wr.writerows(out2)
 temp_union=set(w_hits)|set(s_hits)
 sunfail_codes={x["code"] for x in sunfail}
 combined=set(temp_union)|sunfail_codes
 alt_only=alt_hits-temp_union-sunfail_codes
 sun_by_code={x["candidate_code"]:num(x.get("R2_sunshine_rough_annual_hours_during_available_years")) for x in out2}
 no_temp_and_sun_missing=sum(1 for x in out1 if not x["winter_lt10_signal"] and not x["summer_ge32_signal"] and sun_by_code.get(x["candidate_code"]) is None)
 all_ids=codes|r2codes
 if len(all_ids)!=128: # 127 R1 + 126 R2, with 125 overlap => 128
  raise RuntimeError(f"R1_R2_SHORT_UNION_EXPECTED_128_GOT_{len(all_ids)}")
 # R2 has 125 overlap and one additional long-R1/short-R2 code; the union of
 # the 127 short-R1 codes plus 126 short-R2 codes is therefore 128.
 summary={
  "schema":"RET_PHASE1_NATIONAL_SHORT_HISTORY_R1_R2_HARDLINE_SIGNAL_SCREEN_V1",
  "created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "action_id":"RET-CASCADE-NATIONAL-SHORT-HISTORY-R1_R2-SCREEN-019",
  "source_sha256":{"R1_tier_json":sha(R1JSON),"R1_station_csv":sha(R1CSV),"R2_interim_json":sha(R2JSON),
   "R3_altitude_csv":sha(ALTCSV),"prior_long_73_screen":sha(LONG73)},
  "cohort_counts":{"new_short_R1_temperature_candidates":127,"new_short_R2_rain_sun_candidates":126,
   "R1_R2_overlap":len(codes&r2codes),"short_R1_R2_union":len(all_ids)},
  "thresholds":{"winter_season_mean_daily_tmax_lt_c":WINTER,"summer_season_mean_daily_tmax_ge_c":SUMMER,
   "annual_sunshine_lt_hours":SUN,"residential_altitude_gt_m":ALT},
  "R1_temperature_counts":{"winter_lt10":len(set(w_hits)),"summer_ge32":len(set(s_hits)),
   "union_any_temperature_signal":len(temp_union),"no_temperature_trigger":127-len(temp_union),
   "observed_month_count_min":min(int(x["obs_month_count_in_1991_2020_range"]) for x in r1rows),
   "observed_month_count_max":max(int(x["obs_month_count_in_1991_2020_range"]) for x in r1rows)},
  "R2_sunshine_counts":{"short_R2_candidates":126,"sunshine_measured":len(sunpass)+len(sunfail),
   "sunshine_lt1800":len(sunfail),"sunshine_measured_no_trigger":len(sunpass),
   "sunshine_missing":126-len(sunpass)-len(sunfail)},
  "altitude_counts":{"short_R1_candidates_with_station_or_dem_point_over2000":len(alt_hits),
   "altitude_only_no_temperature_or_sunshine_trigger":len(alt_only)},
  "combined_short_cohort":{"temperature_or_sunshine_signal_candidates":len(combined),
   "altitude_point_warning_candidates":len(alt_hits),"altitude_only_cases":len(alt_only),
   "no_known_climate_trigger_but_sunshine_missing":no_temp_and_sun_missing,
   "formal_region_exclusions":0},
  "temperature_signal_candidates":[{"code":x["candidate_code"],"name":x["candidate_name"],
   "winter_lt10":x["winter_lt10_signal"],"summer_ge32":x["summer_ge32_signal"]} for x in out1 if x["winter_lt10_signal"] or x["summer_ge32_signal"]],
  "sunshine_signal_candidates":[{"code":x["candidate_code"],"name":x["candidate_name"]} for x in out2 if x["sunshine_lt1800_signal"]],
  "altitude_only_candidates":[{"code":x["candidate_code"],"name":x["candidate_name"]} for x in out1 if x["candidate_code"] in alt_only],
  "all_2847_national_candidates_carry_forward":True,
  "formal_valid_county_screenings":0,"confirmed_county_exclusions":0,
  "interpretation":"This is a short-history (at least 180 observed months with at least 10 observations in every calendar month) preliminary signal screen. It is not a full 1991-2020 30-year normal and does not certify residential microclimate. Threshold hits are high-priority exit candidates for the specific evaluation point, subject to one residential-site confirmation; missing sunshine stays PENDING.",
  "limitations":["Do not mix this short-history cohort with the 73 longer-source cohort when reporting long-normal coverage.",
   "Winter and summer are multi-month means of monthly mean daily maximum; a crossing proves at least one month crosses the hard line, while no crossing does not prove the coldest/hottest month passes.",
   "Only 9 short-history R2 candidates have measured sunshine; the remaining 117 are pending, not failed.",
   "Station elevation is not dwelling elevation; >2000m is a residential-site check, not a county-wide exclusion.",
   "Rainfall is not a hard line in this confirmed rule and is not used to infer sunshine.",
   "No formal county grade or irreversible region exclusion is made in this run."]
 }
 OUTJSON.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"status":"PASS","R1_short":127,"R2_short":126,"winter_lt10":len(set(w_hits)),
  "summer_ge32":len(set(s_hits)),"temperature_union":len(temp_union),
  "sun_measured":len(sunpass)+len(sunfail),"sun_lt1800":len(sunfail),
  "altitude_warning":len(alt_hits),"combined_signals":len(combined),
  "R1_R2_union":len(all_ids),"formal_exclusions":0},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
