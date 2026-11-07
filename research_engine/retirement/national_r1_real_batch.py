#!/usr/bin/env python3
"""Nationwide R1 sequential temperature evidence cascade, first sourced batch.

Reuses archived 12 genuine Open-Meteo ERA5 1991-2020 raw daily records from
GitHub Actions run 42245826626, artifact 13518156891. No API refetches.
All 2847 provisional administrative records preserved. 12 historical county
linkages get POINT-ONLY climate evidence; 2835 remain NOT_SCREENED.
No formal A/B/C/D, no county-wide climate representativeness, no automatic D.
"""
import csv,datetime,hashlib,json,pathlib,statistics
ROOT=pathlib.Path("research_engine/retirement")
CLIMATE=ROOT/"output/archived_climate_42245826626"
OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
R0=ROOT/"status/national_cascade_r0_provisional.csv"
R0SUM=ROOT/"status/national_cascade_r0_summary.json"
JOIN=pathlib.Path("retirement-climate-pilot/status/latest-adcode-probe.json")
MICRO=ROOT/"status/latest-microclimate-pilot.json"
MULTI=ROOT/"status/latest-spatial-variability-002.json"
SITES=["Haikou","Kunming","Xiamen","Panzhihua","Mengzi","Jinghong","Guilin","Quanzhou","Dali","Guiyang","Nanning","Sanya"]
def sha(b):return hashlib.sha256(b).hexdigest()
def getraw(site):
    files=list(CLIMATE.rglob(site+".json"))
    if len(files)!=1:raise RuntimeError("Artifact missing or duplicates "+site+": "+str([str(x) for x in files]))
    b=files[0].read_bytes()
    return json.loads(b),sha(b),str(files[0])
def days_mean(d,values,monthset):
    a=[float(v) for dt,v in zip(d,values) if v is not None and int(dt[5:7]) in monthset]
    expected=sum(int(dt[5:7]) in monthset for dt in d)
    if len(a)<expected*0.99:raise RuntimeError("Daily data incomplete")
    return round(statistics.mean(a),3)
def longest(b):
    maximum=cur=0
    for flag in b:
        cur=cur+1 if flag else 0
        if cur>maximum:maximum=cur
    return maximum
summary=json.loads(R0SUM.read_text(encoding="utf-8"))
if summary["candidate_count"]!=2847 or summary["formal_valid_county_screenings"]!=0 or summary["2026_official_national_county_roster_verified"] is not False:
    raise RuntimeError("R0 must be provisional with no valid screenings")
if sha(R0.read_bytes())!=summary["output_sha256"]:raise RuntimeError("R0 CSV source digest mismatch")
with R0.open(encoding="utf-8-sig",newline="") as f:
    rd=csv.DictReader(f);cols=list(rd.fieldnames);rows=list(rd)
if len(rows)!=2847 or len({x["candidate_code"] for x in rows})!=2847:raise RuntimeError("R0 not 2847 unique")
joins=json.loads(JOIN.read_text(encoding="utf-8"))
if joins["candidate_unique_count"]!=12 or joins["official_code_verified"]!=0:raise RuntimeError("Expected historical-only 12 code matches")
jmap={x["site"]:x for x in joins["candidate_links"]}
if set(jmap)!=set(SITES):raise RuntimeError("Unexpected sites in geocode mapping")
terrain=json.loads(MICRO.read_text(encoding="utf-8"))
mmap={x["site"]:x for x in terrain["points"]}
multi=json.loads(MULTI.read_text(encoding="utf-8"))
multinames={x["site"] for x in multi["cases"]}
bycode={r["candidate_code"]:r for r in rows}
records=[]
for site in SITES:
    link=jmap[site];code=link["candidate_code"]
    if link["candidate_count"]!=1 or code not in bycode:raise RuntimeError("County code missing or ambiguous "+site)
    if bycode[code]["candidate_name"]!=link["archival_county_chinese"]:
        raise RuntimeError("2025 vs historical county name conflict "+site)
    original,raw_sha,file_path=getraw(site)
    daily=original["daily"];dates=daily["time"]
    if len(dates)!=10958 or dates[0]!="1991-01-01" or dates[-1]!="2020-12-31":
        raise RuntimeError("ERA5 coverage error "+site)
    for field in ["temperature_2m_mean","temperature_2m_max","temperature_2m_min","precipitation_sum","sunshine_duration"]:
        if field not in daily or len(daily[field])!=len(dates):
            raise RuntimeError("Missing original daily field "+field+" "+site)
    tmax=daily["temperature_2m_max"];tmin=daily["temperature_2m_min"]
    hot=[v is not None and float(v)>=35 for v in tmax]
    cold=[v is not None and float(v)<=5 for v in tmin]
    m={"winter_daytime_mean_max_c":days_mean(dates,tmax,{12,1,2}),
       "winter_nighttime_mean_min_c":days_mean(dates,tmin,{12,1,2}),
       "summer_jun_sep_mean_max_c":days_mean(dates,tmax,{6,7,8,9}),
       "summer_jun_sep_mean_min_c":days_mean(dates,tmin,{6,7,8,9}),
       "hot_ge35_days_per_year":round(sum(hot)/30,3),
       "cold_le5_nights_per_year":round(sum(cold)/30,3),
       "longest_hot_ge35_consecutive_days_30y":longest(hot),
       "longest_cold_le5_consecutive_nights_30y":longest(cold)}
    pref=(18<=m["winter_daytime_mean_max_c"]<=25 and
          25<=m["summer_jun_sep_mean_max_c"]<=29 and
          m["hot_ge35_days_per_year"]<=10)
    rec={"site":site,"candidate_county_name":bycode[code]["candidate_name"],"candidate_county_code":code,
      "candidate_official_2026_verified":False,"1991_2020_daily_rows":len(dates),
      "api_returned_grid_center_latitude":original.get("latitude"),
      "api_returned_grid_center_longitude":original.get("longitude"),
      "era5_grid_resolution_qa":"INDEPENDENCE_AND_RESIDENTIAL_REPRESENTATIVENESS_OPEN",
      "climate_model":"ERA5_OPEN_METEO_NOT_CMA",
      "calendar_period":"1991-01-01/2020-12-31",
      "source_artifact_run_id":"42245826626","source_artifact_id":"13518156891",
      "source_workflow_overall_conclusion":"FAILURE_BUT_ARCHIVE_RAW_COVERAGE_VALIDATED",
      "raw_daily_sha256":raw_sha,
      "raw_daily_file_path":file_path,
      "original_query_url":"https://archive-api.open-meteo.com/v1/archive",
      "metrics":m,"point_preference_signal":"POINT_MATCHES_SELECTED_IDEALS" if pref else "POINT_MISSES_ONE_OR_MORE_IDEALS",
      "county_exclusion_authorized":False,
      "terrain_exception_status":"REVIEW_REQUIRED",
      "dem_sample_altitude_m":mmap[site]["points"][0]["copernicus_glo90_elevation_m"],
      "dem_three_point_span_m":mmap[site]["sample_dem_span_m"],
      "county_multigrid_older_exploratory_available":site in multinames,
      "missing_fields":["county-wide climate spatial representativeness","residential neighborhood position",
          "independent 1991-2020 station crosscheck","official 2026 county identity",
          "local terrain and residential microclimate exceptions"]}
    records.append(rec)
fields=cols+["R1_evidence_scope","R1_winter_max_mean_c","R1_winter_min_mean_c","R1_summer_jun_sep_max_mean_c",
    "R1_summer_jun_sep_min_mean_c","R1_hot_ge35_days_per_year","R1_longest_hot_run_days",
    "R1_preference_signal","R1_evidence_source","R1_raw_sha256","R1_spatial_flag",
    "R1_missing_parameters"]
mapping={x["candidate_county_code"]:x for x in records}
for r in rows:
    code=r["candidate_code"]
    if code not in mapping:
        if r["R1_status"]!="NOT_SCREENED":raise RuntimeError("Expected R1 untouched before batch "+code)
        r["R1_evidence_scope"]="NONE"
        continue
    item=mapping[code];metric=item["metrics"]
    r["R1_status"]="SCANNED_POINT_EVIDENCE_PENDING_COUNTY_QA"
    r["last_completed_round"]="R1_POINT_PRELIMINARY"
    r["cascade_status"]="ACTIVE_PENDING"
    r["R1_evidence_scope"]="ONE_ERA5_POINT_NOT_WHOLE_COUNTY"
    r["R1_winter_max_mean_c"]=metric["winter_daytime_mean_max_c"]
    r["R1_winter_min_mean_c"]=metric["winter_nighttime_mean_min_c"]
    r["R1_summer_jun_sep_max_mean_c"]=metric["summer_jun_sep_mean_max_c"]
    r["R1_summer_jun_sep_min_mean_c"]=metric["summer_jun_sep_mean_min_c"]
    r["R1_hot_ge35_days_per_year"]=metric["hot_ge35_days_per_year"]
    r["R1_longest_hot_run_days"]=metric["longest_hot_ge35_consecutive_days_30y"]
    r["R1_preference_signal"]=item["point_preference_signal"]
    r["R1_evidence_source"]="42245826626/retirement-climate-pilot-output/"+item["site"]+".json"
    r["R1_raw_sha256"]=item["raw_daily_sha256"]
    r["R1_spatial_flag"]="LOCAL_MICROCLIMATE_EXCEPTIONS_NOT_CLOSED"
    r["R1_missing_parameters"]=";".join(item["missing_fields"])
    r["missing_parameter_list"]="R1_POINT_SPATIAL_AND_STATION_QA_PENDING;R2_R5_UNSCANNED;OFFICIAL_2026_CODE_UNVERIFIED"
output=OUT/"national_r1_first_real_batch.csv"
with output.open("w",encoding="utf-8-sig",newline="") as f:
    wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader();wr.writerows(rows)
scanned=[x for x in rows if x["R1_status"]=="SCANNED_POINT_EVIDENCE_PENDING_COUNTY_QA"]
unscanned=[x for x in rows if x["R1_status"]=="NOT_SCREENED"]
if len(scanned)!=12 or len(unscanned)!=2835:raise RuntimeError("R1 actual scanning count mismatched")
if any(x["confirmed_exit_round"] for x in rows) or any(str(x["valid_county_screening"]).lower()=="true" for x in rows):
    raise RuntimeError("Premature exclusion / formal screening")
if any(x["R2_status"]!="NOT_SCREENED" for x in rows):raise RuntimeError("R2 was modified")
detail=OUT/"national_r1_first_real_batch_evidence.json"
detail.write_text(json.dumps({"schema":"RET_CASCADE_NATIONAL_R1_REAL_BATCH_V1",
    "created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "artifact_source":{"run_id":"42245826626","artifact_id":"13518156891",
        "artifact_name":"retirement-climate-pilot-output",
        "workflow_conclusion":"FAILURE; validation of daily-file coverage performed independently",
        "archive_source":"Open-Meteo ERA5, 1991-2020 not CMA normals"},
    "national_roster_source_sha256":summary["output_sha256"],
    "input_counties":2847,"R1_real_point_evidence_counties":12,
    "R1_not_scanned_counties":2835,"R1_county_wide_validated":0,
    "R1_verified_fatal_exclusions":0,"R1_carry_forward_count":2847,
    "R2_eligible_to_enter_counties":2847,
    "R2_only_r1_evidence_available_counties":12,
    "official_national_roster_verified":False,"formal_valid_county_screenings":0,
    "formal_grades_changed":0,
    "source_join":"retirement-climate-pilot/status/latest-adcode-probe.json",
    "joining_is_archival_and_nonofficial":True,
    "county_era5_climate_records":records,
    "CSV_sha256":sha(output.read_bytes()),
    "semantics":"Scanned point data is NOT complete county evidence; unscanned remains unscanned, all pass to R2 with preserved unknown R1. No hard elimination based on ideal preference."},
    ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"result":"R1_REAL_12_COUNTIES_POINT_CLIMATE","national_roster":2847,
 "R1_point_supported":12,"R1_not_scanned":2835,"R1_formally_valid":0,
 "R1_excluded":0,"R2_carry_forward":2847,"output_sha256":sha(output.read_bytes())},ensure_ascii=False),flush=True)
