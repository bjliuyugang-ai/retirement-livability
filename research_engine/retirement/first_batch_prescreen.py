#!/usr/bin/env python3
"""Stage-3 FIRST-BATCH pre-screen using frozen 11 existing ERA5 point observations.

Run: python research_engine/retirement/first_batch_prescreen.py
This intentionally does NOT wait for the 12th point, extra CMA data, or
complete 2026 official code verification. But it does NOT confer formal
A/B/C/D grades, national coverage, or second-stage admission.
The research baseline's preferred windows are NOT hard elimination rules.
"""
from collections import defaultdict
import csv,datetime,hashlib,json,pathlib
ROOT=pathlib.Path("research_engine/retirement")
SRC=ROOT/"evidence/spatial_002_frozen_partial_42315459712.json"
CODES=pathlib.Path("retirement-climate-pilot/status/latest-adcode-probe.json")
DEM=ROOT/"status/latest-microclimate-pilot.json"
OUT=ROOT/"output"
OUT.mkdir(parents=True,exist_ok=True)
TARGET={
 "Panzhihua":{"county":"四川省攀枝花市东区","prior_master_region":"东区／仁和区候选片区",
 "prior_master_provisional_grade":"C","priority":"P1_LOCAL_RESIDENTIAL_EXPOSURE_QA",
 "working_conclusion":"冬季日间适宜的点位与夏季相对温和的点位并存，城市河谷及工业污染暴露须分区核验。"},
 "Mengzi":{"county":"云南省红河州蒙自市","prior_master_region":"蒙自坝区／城市成熟社区",
 "prior_master_provisional_grade":"B","priority":"P1_BASIN_VS_VALLEY_REPRESENTATIVENESS",
 "working_conclusion":"坝区和周边山地/低海拔河谷季节温差显著；年湿度再分析值不应直接替代官方观测。"},
 "Jinghong":{"county":"云南省西双版纳州景洪市","prior_master_region":"景洪城区／城市成熟区",
 "prior_master_provisional_grade":"D","priority":"P2_PRESERVE_POTENTIAL_MICROCLIMATE_EXCEPTION",
 "working_conclusion":"热湿与夏季高温是明显偏好冲突；较高海拔点可能不同，但不能据此推翻原暂定等级。"},
 "Dali":{"county":"云南省大理州大理市","prior_master_region":None,
 "prior_master_provisional_grade":None,"priority":"P2_HIGH_ELEVATION_WINTER_LIMIT",
 "working_conclusion":"夏季气温相对温和，但采样海拔偏高、冬季偏凉，不能将全市视为均一气候。"}}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
src=json.loads(SRC.read_text(encoding="utf-8"))
codes=json.loads(CODES.read_text(encoding="utf-8"))
dem=json.loads(DEM.read_text(encoding="utf-8"))
if src.get("request_count_completed")!=11 or src.get("formal_county_screenings")!=0:
 raise RuntimeError("Frozen scope changed; this action requires the original exactly 11 preliminary points")
if not codes.get("candidate_links") or dem.get("status")!="PASS_ELEVATION_SENSITIVITY":
 raise RuntimeError("Code or terrain provenance not validated as exploratory inputs")
by_code={x["site"]:x for x in codes["candidate_links"]}
by_dem={x["site"]:x for x in dem["points"]}
allrows=[];countyrows=[]
for c in src["cases"]:
 site=c["site"];spec=TARGET[site];code=by_code[site]
 if code["candidate_count"]!=1 or code["candidate_code"]!=c["archival_county_candidate"]:
  raise RuntimeError("Archival code disagreement for "+site)
 if by_dem[site]["candidate_county_code"]!=code["candidate_code"]:
  raise RuntimeError("DEM code disagreement for "+site)
 valid=[p for p in c["samples"] if isinstance(p.get("metrics"),dict)]
 if not valid:raise RuntimeError("No actual ERA5 observations for "+site)
 for idx,p in enumerate(valid):
  m=p["metrics"];winter=m["winter_temperature_2m_max"];summer=m["summer_temperature_2m_max"]
  humidity=m["annual_relative_humidity_2m_mean"];alt=p["elevation_m"]
  checks={"winter_day_18_25_preference":18<=winter<=25,
          "summer_day_25_29_preference":25<=summer<=29,
          "annual_humidity_50_70_preference":50<=humidity<=70,
          "altitude_at_or_below_1500_preference":alt<=1500}
  point_flags=[key for key,val in checks.items() if not val]
  row={"site":site,"candidate_county":spec["county"],"archival_code":code["candidate_code"],
       "point_index_in_frozen_source":idx,"latitude":p["latitude"],"longitude":p["longitude"],
       "sample_dem_elevation_m":alt,
       "winter_mean_daily_max_c":winter,"summer_mean_daily_max_c":summer,
       "annual_relative_humidity_pct":humidity,"summer_mean_dewpoint_c":m["summer_dew_point_2m_mean"],
       "era5_annual_sunshine_hours_estimated":round(m["annual_sunshine_duration"]*365.25/3600,1),
       "preference_checks":checks,"preference_mismatch_flags":point_flags,
       "independent_era5_grid_verified":False,
       "residential_location_verified":False,"official_climate_station_crosschecked":False,
       "formal_grading":"UNASSESSED","observation_type":"ERA5_MODEL_POINT_EXPLORATORY"}
  allrows.append(row)
 candidate=[r for r in allrows if r["site"]==site]
 good=sum(all(r["preference_checks"][key] for key in ("winter_day_18_25_preference","summer_day_25_29_preference","annual_humidity_50_70_preference")) for r in candidate)
 countyrows.append({"site":site,"county":spec["county"],"archival_code":code["candidate_code"],
     "point_count_used":len(valid),"geometric_dem_span_m":c["dem_span_m"],
     "winter_daytime_max_range_c":[min(r["winter_mean_daily_max_c"] for r in candidate),max(r["winter_mean_daily_max_c"] for r in candidate)],
     "summer_daytime_max_range_c":[min(r["summer_mean_daily_max_c"] for r in candidate),max(r["summer_mean_daily_max_c"] for r in candidate)],
     "humidity_range_pct":[min(r["annual_relative_humidity_pct"] for r in candidate),max(r["annual_relative_humidity_pct"] for r in candidate)],
     "points_meeting_three_climate_preferences":good,
     "prior_master_region":spec["prior_master_region"],"prior_master_provisional_grade":spec["prior_master_provisional_grade"],
     "working_priority":spec["priority"],"working_conclusion":spec["working_conclusion"],
     "stage3_first_batch_preliminary":"PRE_SCREEN_DONE_FORMAL_PENDING",
     "formal_county_grade":"UNASSESSED",
     "formal_county_screening_valid":False,
     "formal_blockers":["2026官方行政身份及边界全国对账未完成","ERA5格点及气象站1991—2020同口径交叉核验未完成","非实际候选住宅片区；局部微气候仍待核","空气、饮用水、污染源及灾害底线尚未完成住宅级核验"],
     "sunshine_data_caveat":"ERA5 sunshine_duration 不能代替有来源的观测年日照，不用于正式评级"})
if len(allrows)!=11 or len(countyrows)!=4:raise RuntimeError("Wrong point or county counts")
payload={"schema":"RET_STAGE3_FIRST_BATCH_PRESCREEN_V1",
         "generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "run_scope":"2026-11-07 user-authorized leap from stage2 quality-research to stage3 method validation",
         "stage3_preliminary_county_units":4,"preliminary_point_records":11,
         "valid_county_screenings":0,"formal_a_b_c_d_count":0,
         "source":{"frozen_11point_evidence":str(SRC),"source_sha256":sha(SRC),
                   "code_candidate":str(CODES),"code_sha256":sha(CODES),
                   "dem_evidence":str(DEM),"dem_sha256":sha(DEM)},
         "research_standard":{"winter_day_preference_c":[18,25],"summer_day_preference_c":[25,29],
                              "annual_rh_preference_pct":[50,70],"altitude_reference_m":[0,1500],
                              "hard_exclusion_inferred_from_preference":False},
         "limitations":["11 coordinates represent four historical candidate counties, not 11 validated counties",
                        "Point positions are not confirmed residential communities; ERA5 sample grids may overlap",
                        "Working rankings/flags are NOT formal A/B/C/D and cannot trigger second-stage enrollment",
                        "2000m DEM sample does not eliminate an entire county; local low-elevation areas remain assessable",
                        "2026 official national county register and actual residential exposure still unverified",
                        "No missing value is treated as proof of inadequacy"],
         "point_rows":allrows,"county_rows":countyrows}
path=OUT/"first_batch_prescreen.json";path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
with (OUT/"first_batch_prescreen_counties.csv").open("w",encoding="utf-8-sig",newline="") as f:
 columns=["site","county","archival_code","point_count_used","geometric_dem_span_m",
          "winter_daytime_max_range_c","summer_daytime_max_range_c","humidity_range_pct",
          "points_meeting_three_climate_preferences","prior_master_region",
          "prior_master_provisional_grade","working_priority","working_conclusion",
          "stage3_first_batch_preliminary","formal_county_grade","formal_county_screening_valid","formal_blockers"]
 w=csv.DictWriter(f,fieldnames=columns);w.writeheader()
 for r in countyrows:
  w.writerow({k:(json.dumps(r[k],ensure_ascii=False) if isinstance(r[k],list) else r[k]) for k in columns})
print(json.dumps({"status":"FIRST_BATCH_PRE_SCREEN_COMPUTED","point_records":len(allrows),
                   "candidate_counties":len(countyrows),"valid_county_screenings":0,
                   "county_lookahead":[{"site":x["site"],"ideal_point_count":x["points_meeting_three_climate_preferences"],"priority":x["working_priority"]} for x in countyrows]},ensure_ascii=False))
