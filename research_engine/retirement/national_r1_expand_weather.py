#!/usr/bin/env python3
"""Real ERA5 1991-2020 R1 temperature expansion from historic county polygons.

30 newly geolocated sampled anchors across 16 administrative prefix groups
are explicit 2017 historic geometry and unique-2025-name candidates,
NOT verified current official counties, residential sites or formal screenings.

Batch multicoordinate Open-Meteo archive requests (<=5 locations each), bound
retries, persist actual response digests, and never mark failed fetch as scanned.
"""
import csv,datetime,gzip,hashlib,json,pathlib,statistics,time,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path("research_engine/retirement")
OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
PREVCSV=ROOT/"status/national_r1_first_real_batch.csv"
PREVEV=ROOT/"status/national_r1_first_real_batch_evidence.json"
CROSS=ROOT/"status/r1_expand_strict_crosswalk.json"
def sha(b):return hashlib.sha256(b).hexdigest()
cross=json.loads(CROSS.read_text(encoding="utf-8"))
prior=json.loads(PREVEV.read_text(encoding="utf-8"))
if (cross["sampled_count"]!=30 or
    cross["official_2026_code_verified"]!=0 or
    cross["sampled_province_prefix_count"]<12 or
    prior["R1_real_point_evidence_counties"]!=12 or
    prior["R1_not_scanned_counties"]!=2835):
    raise RuntimeError("Crosswalk or prior R1 evidence mismatch")
targets=cross["selected_30"]
if len({p["county_code"] for p in targets})!=30:raise RuntimeError("Duplicate expansion codes")
with PREVCSV.open(encoding="utf-8-sig",newline="") as f:
    dr=csv.DictReader(f);cols=list(dr.fieldnames);rows=list(dr)
bycode={x["candidate_code"]:x for x in rows}
if len(rows)!=2847 or len(bycode)!=2847:raise RuntimeError("Nationwide R1 ledger damaged")
if any(bycode[x["county_code"]]["R1_status"]!="NOT_SCREENED" for x in targets):
    raise RuntimeError("Already-measured or previously modified expansion target")
if any(bycode[x["county_code"]]["candidate_name"]!=x["county_2025_name"] for x in targets):
    raise RuntimeError("2025 name/code conflict in strict historic crosswalk")
def fetch(batch):
    params={"latitude":",".join(str(x["latitude_2017_polygon_interior"]) for x in batch),
    "longitude":",".join(str(x["longitude_2017_polygon_interior"]) for x in batch),
    "start_date":"1991-01-01","end_date":"2020-12-31",
    "daily":"temperature_2m_max,temperature_2m_min",
    "timezone":"Asia/Shanghai","models":"era5"}
    url="https://archive-api.open-meteo.com/v1/archive?"+urllib.parse.urlencode(params,safe=",")
    req=urllib.request.Request(url,headers={"User-Agent":"retirement-national-R1-2026/0.2"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req,timeout=110) as resp:raw=resp.read()
            return url,raw
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as e:
            if isinstance(e,urllib.error.HTTPError) and e.code not in [429,500,502,503,504]:
                raise
            print("RETRY_API_BATCH",len(batch),attempt+1,repr(e),flush=True)
            if attempt==1:raise
            time.sleep(14)
def mean(d,values,months):
    subset=[float(v) for day,v in zip(d,values) if v is not None and int(day[5:7]) in months]
    expected=sum(int(day[5:7]) in months for day in d)
    if len(subset)<expected*.99:raise ValueError("Excessive null ERA5 values")
    return round(statistics.mean(subset),3)
def longest(flags):
    n=best=0
    for yes in flags:
        n=n+1 if yes else 0;best=max(best,n)
    return best
record=[];failed=[];batchmeta=[]
for start in range(0,len(targets),5):
    batch=targets[start:start+5]
    try:
        url,raw=fetch(batch)
        digest=sha(raw)
        (OUT/("R1_expansion_raw_batch_"+str(start//5+1)+".json.gz")).write_bytes(gzip.compress(raw))
        payload=json.loads(raw)
        if not isinstance(payload,list) or len(payload)!=len(batch):
            raise ValueError("Expected "+str(len(batch))+" multicoordinate responses")
        for index,(loc,point) in enumerate(zip(payload,batch)):
            code=point["county_code"]
            try:
                arr=loc["daily"];d=arr["time"];tmax=arr["temperature_2m_max"];tmin=arr["temperature_2m_min"]
                if (len(d)!=10958 or len(tmax)!=10958 or len(tmin)!=10958
                    or d[0]!="1991-01-01" or d[-1]!="2020-12-31"):
                    raise ValueError("Invalid 1991-2020 coverage")
                hot=[v is not None and float(v)>=35 for v in tmax]
                cold=[v is not None and float(v)<=5 for v in tmin]
                metrics={"winter_daytime_mean_max_c":mean(d,tmax,{12,1,2}),
                    "winter_nighttime_mean_min_c":mean(d,tmin,{12,1,2}),
                    "summer_jun_sep_mean_max_c":mean(d,tmax,{6,7,8,9}),
                    "summer_jun_sep_mean_min_c":mean(d,tmin,{6,7,8,9}),
                    "hot_ge35_days_per_year":round(sum(hot)/30,3),
                    "cold_le5_nights_per_year":round(sum(cold)/30,3),
                    "longest_hot_ge35_consecutive_days_30y":longest(hot),
                    "longest_cold_le5_consecutive_nights_30y":longest(cold)}
                match=(18<=metrics["winter_daytime_mean_max_c"]<=25 and
                    25<=metrics["summer_jun_sep_mean_max_c"]<=29 and
                    metrics["hot_ge35_days_per_year"]<=10)
                rec={"county_code_candidate":code,"county_name_2025_mirror":point["county_2025_name"],
                    "source_historic_polygon_name":point["shape_name_2017"],
                    "source_historic_polygon_id":point["shape_id_2017"],
                    "historic_polygon_geometry_sha256":cross["geometry_sha256"],
                    "requested_latitude":point["latitude_2017_polygon_interior"],
                    "requested_longitude":point["longitude_2017_polygon_interior"],
                    "api_returned_grid_center_latitude":loc.get("latitude"),
                    "api_returned_grid_center_longitude":loc.get("longitude"),
                    "raw_response_sha256":digest,"source_batch_response_index":index,
                    "source_url":url,"days":len(d),"base_period":"1991-2020","model":"ERA5",
                    "point_preference_signal":"POINT_MATCHES_SELECTED_IDEALS" if match else "POINT_MISSES_ONE_OR_MORE_IDEALS",
                    "metrics":metrics,"official_county_2026_verified":False,
                    "residential_geolocation_verified":False,
                    "county_wide_representativeness_verified":False,
                    "can_exclude_county":False}
                record.append(rec)
                print("COUNTY_R1_REAL",code,point["county_2025_name"],metrics["winter_daytime_mean_max_c"],metrics["summer_jun_sep_mean_max_c"],flush=True)
            except Exception as ex:
                failed.append({"code":code,"county":point["county_2025_name"],
                    "reason":"RESPONSE_DATA_QA_FAILED","error":repr(ex)})
        batchmeta.append({"batch":start//5+1,"point_count":len(batch),"raw_sha256":digest,
            "completed_sites":sum(r["county_code_candidate"] in {p["county_code"] for p in batch} for r in record)})
    except Exception as ex:
        for point in batch:
            failed.append({"code":point["county_code"],"county":point["county_2025_name"],
                "reason":"OPENMETEO_BATCH_REQUEST_FAILED","error":repr(ex)})
        print("BATCH_BLOCKED",start//5+1,repr(ex),flush=True)
    time.sleep(3)
if len(record)+len(failed)!=len(targets):raise RuntimeError("Success+failure count not equal sampled 30")
seen={x["county_code_candidate"] for x in record}
if len(seen)!=len(record):raise RuntimeError("Duplicate measured county candidate")
for point in record:
    code=point["county_code_candidate"];m=point["metrics"];x=bycode[code]
    x["R1_status"]="SCANNED_POINT_EVIDENCE_PENDING_COUNTY_QA"
    x["cascade_status"]="ACTIVE_PENDING"
    x["last_completed_round"]="R1_POINT_PRELIMINARY"
    x["R1_evidence_scope"]="2017_POLYGON_INTERIOR_ERA5_GRID_NOT_RESIDENTIAL"
    x["R1_winter_max_mean_c"]=m["winter_daytime_mean_max_c"]
    x["R1_winter_min_mean_c"]=m["winter_nighttime_mean_min_c"]
    x["R1_summer_jun_sep_max_mean_c"]=m["summer_jun_sep_mean_max_c"]
    x["R1_summer_jun_sep_min_mean_c"]=m["summer_jun_sep_mean_min_c"]
    x["R1_hot_ge35_days_per_year"]=m["hot_ge35_days_per_year"]
    x["R1_longest_hot_run_days"]=m["longest_hot_ge35_consecutive_days_30y"]
    x["R1_preference_signal"]=point["point_preference_signal"]
    x["R1_evidence_source"]="Open-Meteo-ERA5-1991-2020/r1-expand/"+point["raw_response_sha256"]
    x["R1_raw_sha256"]=point["raw_response_sha256"]
    x["R1_spatial_flag"]="2017_HISTORIC_POLYGON_INTERIOR_AND_2025_CODE_MATCH_PENDING_2026_QA"
    x["R1_missing_parameters"]="2026_CURRENT_COUNTY_IDENTITY;LOCAL_MICROCLIMATE;RESIDENTIAL_ADDRESS;CMA_STATION_QA;EXTREMES_COMPENSATION"
    x["missing_parameter_list"]="R1_COUNTY_RESIDENTIAL_REPRESENTATIVENESS_OPEN;R2_R5_UNSCANNED;2026_CODE_UNVERIFIED"
for f in failed:
    x=bycode[f["code"]]
    x["R1_evidence_scope"]="R1_API_FETCH_FAILED_OR_INVALID"
    x["R1_missing_parameters"]="R1_DATA_FETCH_RETRY_NEEDED;"+f["reason"]
    if x["R1_status"]!="NOT_SCREENED":raise RuntimeError("Failed R1 must remain unscanned")
n_scanned=sum(x["R1_status"]=="SCANNED_POINT_EVIDENCE_PENDING_COUNTY_QA" for x in rows)
n_unscanned=sum(x["R1_status"]=="NOT_SCREENED" for x in rows)
if n_scanned!=12+len(record) or n_unscanned!=2847-n_scanned:raise RuntimeError("R1 cumulative counts invalid")
if any(x["confirmed_exit_round"] for x in rows) or any(x["R2_status"]!="NOT_SCREENED" for x in rows):
    raise RuntimeError("Exclusion or R2 mutation without quality gate")
cols=list(rows[0].keys())
output=OUT/"national_r1_expanded.csv"
with output.open("w",encoding="utf-8-sig",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader();writer.writerows(rows)
summary={"schema":"RET_NATIONAL_R1_2017_GEOMETRY_EXPANSION_V1",
 "generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_crosswalk":"research_engine/retirement/status/r1_expand_strict_crosswalk.json",
 "crosswalk_sha256":sha(CROSS.read_bytes()),"source_prior_r1_sha256":sha(PREVCSV.read_bytes()),
 "requested_new_county_candidates":len(targets),"new_point_evidence_counties":len(record),
 "failed_or_missing_new_targets":len(failed),"failure_details":failed,
 "new_points_with_provinces":len({x["county_code_candidate"][:2] for x in record}),
 "cumulative_R1_point_data_counties":n_scanned,"R1_not_scanned":n_unscanned,
 "cumulative_R1_verified_fatal_exclusions":0,"R1_carry_forward_to_R2":2847,
 "official_national_2026_code_verification_complete":False,
 "formal_valid_county_screenings":0,"formal_grades_changed":0,
 "new_point_records":record,"batches":batchmeta,"output_csv_sha256":sha(output.read_bytes()),
 "status":"REAL_R1_INCREMENT_VERIFIED" if len(record)>0 else "BLOCKED_WITH_REAL_ERRORS",
 "limitations":["Historic 2017 boundaries and provisional 2025 code names not certified current 2026",
 "Single model grid point is not county-wide nor residence-scale representative",
 "All non-measured counties are NOT_SCREENED not screened-and-missing",
 "No hard county elimination from ideal-value mismatch; only approved fatal risks after spatial exception QA"]}
p=OUT/"national_r1_expanded_summary.json";p.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:summary[k] for k in ["requested_new_county_candidates","new_point_evidence_counties",
 "failed_or_missing_new_targets","new_points_with_provinces","cumulative_R1_point_data_counties",
 "R1_not_scanned","R1_carry_forward_to_R2","status"]},ensure_ascii=False),flush=True)
if not record:raise SystemExit(2)
