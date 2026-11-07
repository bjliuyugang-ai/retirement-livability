#!/usr/bin/env python3
"""Nationwide county-wise R1/R2 cascade audit, after source-vetted 226 station
and 132 short-history station data. Keep 30-year-class versus interim separate.

No temperature threshold, exclusion or formal A/B/C/D applied. Missing stays
PENDING / carry-forward; this audit is prioritized source evidence, NOT a
complete first-stage climate screening. 2847 provisional county codes conserved.
"""
import collections,csv,datetime,hashlib,json,pathlib
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
R2CSV=ROOT/"status/national_R2_132_interim_obs_source_2847.csv"
R2JSON=ROOT/"status/meteostat_CN132_interim_R2_evidence.json"
R1JSON=ROOT/"status/meteostat_CN_226_R1_tiered_expansion_evidence.json"
def sha(b):return hashlib.sha256(b).hexdigest()
a=json.loads(R1JSON.read_text(encoding="utf-8"))
b=json.loads(R2JSON.read_text(encoding="utf-8"))
if not(a["new_interim_only_candidate_counties"]==127 and a["R1_counties_with_any_real_point_including_short_history"]==214
 and b["new_interim_only_R2_counties"]==126 and b["R2_total_counties_any_partial_evidence_including_interim"]==199
 and b["prior_R2_longer_source_partials_retained"]==73):
 raise RuntimeError("R1 R2 frozen source counts mismatch")
if sha(R2CSV.read_bytes())!=b["national_output_csv_sha256"]:raise RuntimeError("R2 full national dataset hash changed")
with R2CSV.open(encoding="utf-8-sig",newline="") as f:
 rdr=csv.DictReader(f);fields=list(rdr.fieldnames);rows=list(rdr)
if len(rows)!=2847 or len({r["candidate_code"] for r in rows})!=2847:
 raise RuntimeError("National county code count or uniqueness failed")
if any(r["confirmed_exit_round"] or r["formal_grade"] or str(r["valid_county_screening"]).lower()=="true" for r in rows):
 raise RuntimeError("Formal grade or unsupported exclusion unexpectedly present")
counts=collections.Counter();quality=collections.Counter();r1codes=set();r2codes=set()
candidate_records=[]
for row in rows:
 r1=row["R1_status"];r2=row["R2_status"]
 has1=r1!="NOT_SCREENED";has2=r2!="NOT_SCREENED"
 c1=("LONGER_OR_ERA5_POINT_PARTIAL" if has1 and not r1.startswith("INTERIM_") else
     "SHORT_HISTORY_OBS_PARTIAL" if has1 else "NO_R1_TEMP_EVIDENCE")
 c2=("LONGER_OR_ERA5_POINT_PARTIAL" if has2 and not r2.startswith("INTERIM_") else
     "SHORT_HISTORY_OBS_PARTIAL" if has2 else "NO_R2_RAIN_OR_SUN_EVIDENCE")
 q=("BOTH_R1_R2" if has1 and has2 else
    "R1_ONLY_R2_MISSING" if has1 else
    "R2_ONLY_R1_MISSING" if has2 else
    "BOTH_MISSING")
 counts[q]+=1
 quality[(c1,c2)]+=1
 if has1:r1codes.add(row["candidate_code"])
 if has2:r2codes.add(row["candidate_code"])
 if q=="BOTH_R1_R2":
  if c1=="LONGER_OR_ERA5_POINT_PARTIAL" and c2=="LONGER_OR_ERA5_POINT_PARTIAL":
   next_step="R1_R2_MORE_EXTREMES_HUMIDITY_AND_RESIDENTIAL_QA"
  else:
   next_step="BACKFILL_FULL_1991_2020_INTERVAL_PLUS_EXTREMES_HUMIDITY"
 elif q=="R1_ONLY_R2_MISSING":next_step="OBTAIN_R2_PRECIP_SUN_OBS"
 elif q=="R2_ONLY_R1_MISSING":next_step="OBTAIN_R1_TEMP_MAX_MIN_EXTREME_OBS"
 else:next_step="OBTAIN_R1_TEMP_FIRST_KEEP_ALL_UNKNOWN"
 row["R1_R2_joint_evidence"] = q
 row["R1_evidence_quality_tier"]=c1
 row["R2_evidence_quality_tier"]=c2
 row["R1_R2_next_data_priority"]=next_step
 row["R1_R2_all_source_periods_1991_2020_full_30yrs_verified"]="FALSE"
 row["R1_R2_2026_official_boundary_verified"]="FALSE"
 row["R1_R2_formal_grade_allowed"]="FALSE"
 row["R1_R2_carry_forward"]="TRUE"
 candidate_records.append({"code":row["candidate_code"],"county":row["candidate_name"],
  "province_code_prefix":row["candidate_code"][:2],"evidence_joint":q,
  "R1_tier":c1,"R2_tier":c2,"next_data_priority":next_step,
  "R1_status":r1,"R2_status":r2,
  "R1_interim_obs_station_ids":row.get("R1_interim_15yr_station_ids",""),
  "R2_interim_obs_station_ids":row.get("R2_short_history_obs_station_id",""),
  "R1_long_obs_station_ids":row.get("R1_meteostat_station_ids",""),
  "R2_long_obs_station_id":row.get("R2_meteostat_station_id",""),
  "official_2026_county_roster_verified":False,
  "residential_microclimate_verified":False,
  "formal_valid_county_screening":False})
if len(r1codes)!=214 or len(r2codes)!=199:raise RuntimeError("R1 R2 non-NOT_SCREENED counts fail")
if sum(counts.values())!=2847:raise RuntimeError("Four quadrants fail to conserve candidates")
if len(r1codes&r2codes)!=counts["BOTH_R1_R2"]:raise RuntimeError("R1 R2 actual ID intersection wrong")
if len(r1codes|r2codes)!=2847-counts["BOTH_MISSING"]:
 raise RuntimeError("Union coverage incorrect")
more=["R1_R2_joint_evidence","R1_evidence_quality_tier","R2_evidence_quality_tier","R1_R2_next_data_priority",
 "R1_R2_all_source_periods_1991_2020_full_30yrs_verified",
 "R1_R2_2026_official_boundary_verified","R1_R2_formal_grade_allowed","R1_R2_carry_forward"]
for x in more:
 if x in fields:raise RuntimeError("R1/R2 cascade column unexpected already exists")
fields+=more
p=OUT/"national_2847_R1_R2_joint_cascade_evidence_and_next_gap.csv"
with p.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader();wr.writerows(rows)
c=OUT/"national_R1_R2_double_observed_candidate_list.csv"
cfields=list(candidate_records[0])
with c.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=cfields);wr.writeheader()
 for item in candidate_records:
  if item["evidence_joint"]=="BOTH_R1_R2":wr.writerow(item)
report={"schema":"RET_NATIONWIDE_2847_R1_R2_SOURCE_QUALITY_CASCADE_AND_MISSINGNESS_V1",
 "asof_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_R1_tier_evidence_sha256":sha(R1JSON.read_bytes()),
 "source_R2_tier_evidence_sha256":sha(R2JSON.read_bytes()),
 "source_R2_national_2847_CSV_sha256":sha(R2CSV.read_bytes()),
 "total_provisional_counties":2847,
 "R1_has_any_long_or_short_source_evidence":214,
 "R2_has_any_long_or_short_source_evidence":199,
 "R1_R2_both_partial_evidence":counts["BOTH_R1_R2"],
 "R1_only_R2_missing":counts["R1_ONLY_R2_MISSING"],
 "R2_only_R1_missing":counts["R2_ONLY_R1_MISSING"],
 "R1_R2_both_missing":counts["BOTH_MISSING"],
 "R1_R2_either_round_some_source":2847-counts["BOTH_MISSING"],
 "R1_existing_longer_source_ERA5_or_station":87,
 "R1_additional_short_history_obs_counties":127,
 "R2_existing_longer_source_ERA5_or_station":73,
 "R2_additional_short_history_obs_counties":126,
 "quality_tier_cross_counts":[{"R1_tier":k[0],"R2_tier":k[1],"count":v} for k,v in sorted(quality.items())],
 "both_evidence_counties": [x for x in candidate_records if x["evidence_joint"]=="BOTH_R1_R2"],
 "R1_R2_formal_valid_screenings":0,"confirmed_exclusions":0,"all_carry_forward":2847,
 "official_current_2026_county_roster_fully_verified":False,
 "national_cascade_csv_sha256":sha(p.read_bytes()),
 "both_parameter_county_list_csv_sha256":sha(c.read_bytes()),
 "warnings":["Overlaps of station point and model source are not county-wide normals or physical residential suitability",
 "Short-history monthly values do not meet 1991-2020 full reference-period requirement",
 "Neither existing R1 nor R2 includes required extremes/consecutive sunshine/rain/altitude/residential microclimate and other natural conditions",
 "Do not treat a missing value as failing thresholds, all 2847 retained, no A/B/C/D and no exclusions",
 "Stage1 full-country final acceptance remains zero; this is source coverage and sequencing only"]}
(OUT/"national_2847_R1_R2_joint_cascade_summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["total_provisional_counties","R1_has_any_long_or_short_source_evidence",
 "R2_has_any_long_or_short_source_evidence","R1_R2_both_partial_evidence",
 "R1_only_R2_missing","R2_only_R1_missing","R1_R2_both_missing",
 "R1_R2_either_round_some_source","quality_tier_cross_counts"]},ensure_ascii=False),flush=True)
