#!/usr/bin/env python3
"""R3 actual terrain/altitude cascade using existing 36 DEM samples at 12 2017 county points.
Unknown actual residential elevation => retain. No whole-county exclusion.
"""
import csv,datetime,hashlib,json,pathlib
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/"status/national_r2_first_real_batch.csv"
SUMMARY=ROOT/"status/national_r2_first_real_batch_evidence.json"
DEM=ROOT/"status/latest-microclimate-pilot.json"
def sha(b):return hashlib.sha256(b).hexdigest()
prev=json.loads(SUMMARY.read_text(encoding="utf-8"))
dem=json.loads(DEM.read_text(encoding="utf-8"))
if prev["R2_carry_forward"]!=2847 or prev["R2_county_point_sun_rain_scanned"]!=12:
 raise RuntimeError("R2 carry-forward not verified")
if dem["dem_points_loaded"]!=36 or dem["sites_count"]!=12:
 raise RuntimeError("DEM source does not have twelve three-point sites")
if sha(SRC.read_bytes())!=prev["CSV_sha256"]:
 raise RuntimeError("Source R2 register digest mismatch")
with SRC.open(encoding="utf-8-sig",newline="") as f:
    dr=csv.DictReader(f);cols=list(dr.fieldnames);rows=list(dr)
if len(rows)!=2847 or len({x["candidate_code"] for x in rows})!=2847:
 raise RuntimeError("Invalid national R2 denominator")
bycode={x["candidate_code"]:x for x in rows}
newcols=["R3_historic_DEM_anchor_altitude_m","R3_DEM_sample_min_m","R3_DEM_sample_max_m",
 "R3_DEM_sample_span_m","R3_DEM_sample_below1500_count","R3_DEM_sample_above2000_count",
 "R3_local_exception_status","R3_residential_altitude_verified","R3_evidence_source",
 "R3_missing_parameters"]
for field in newcols:
 if field in cols:raise RuntimeError("R3 already has field "+field)
cols+=newcols
records=[]
for sample in dem["points"]:
    code=sample["candidate_county_code"]
    if code not in bycode:raise RuntimeError("DEM site not joined to national R0: "+code)
    r=bycode[code];elev=[p["copernicus_glo90_elevation_m"] for p in sample["points"]]
    if len(elev)!=3 or any(x is None for x in elev):raise RuntimeError("Incomplete DEM three-point site")
    if r["R3_status"]!="NOT_SCREENED":raise RuntimeError("R3 previously scanned code "+code)
    nlow=sum(e<=1500 for e in elev);nhigh=sum(e>2000 for e in elev)
    r["R3_status"]="DEM_THREE_POINT_EVIDENCE_PENDING_RESIDENTIAL_QA"
    r["R3_historic_DEM_anchor_altitude_m"]=elev[0]
    r["R3_DEM_sample_min_m"]=min(elev)
    r["R3_DEM_sample_max_m"]=max(elev)
    r["R3_DEM_sample_span_m"]=max(elev)-min(elev)
    r["R3_DEM_sample_below1500_count"]=nlow
    r["R3_DEM_sample_above2000_count"]=nhigh
    r["R3_local_exception_status"]="POTENTIAL_LOW_ALTITUDE_SUBAREAS_EXIST" if nlow>0 else "ALL_THREE_SAMPLES_HIGH_BUT_EXCEPTIONS_NOT_CLOSED"
    r["R3_residential_altitude_verified"]="FALSE"
    r["R3_evidence_source"]="research_engine/retirement/status/latest-microclimate-pilot.json"
    r["R3_missing_parameters"]="ACTUAL_RESIDENCE_COORDINATES;DEM_TO_RESIDENTIAL_LOCATION_QA;LOW_ALTITUDE_EXCEPTIONS;DISASTER_OVERLAY"
    r["cascade_status"]="ACTIVE_PENDING"
    r["last_completed_round"]="R3_DEM_POINT_EXPLORATORY"
    r["missing_parameter_list"]="R1_R3_INCOMPLETE_RESIDENTIAL_REPRESENTATIVENESS;R4_R5_UNSCANNED;2026_CODE_UNVERIFIED"
    records.append({"site":sample["site"],"candidate_code":code,"point_count":3,
     "historical_polygon_dem_points":sample["points"],"min_m":min(elev),"max_m":max(elev),
     "span_m":max(elev)-min(elev),"samples_below_1500_m":nlow,
     "samples_above_2000_m":nhigh,"residential_elevation_verified":False,
     "county_exclusion_authorized":False,
     "risk_note":"DEM polygons are exploratory; no actual dwelling verified, county-level local exceptions remain open"})
n=sum(x["R3_status"]=="DEM_THREE_POINT_EVIDENCE_PENDING_RESIDENTIAL_QA" for x in rows)
unknown=sum(x["R3_status"]=="NOT_SCREENED" for x in rows)
if n!=12 or unknown!=2835 or any(x["confirmed_exit_round"] for x in rows):
 raise RuntimeError("R3 pass-forward or verified-fatal guard mismatch")
p=OUT/"national_r3_first_real_batch.csv"
with p.open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
res={"schema":"RET_NATIONAL_R3_REAL_DEM_ALTITUDE_BATCH_V1",
"generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"source_R2_CSV_sha256":prev["CSV_sha256"],"source_DEM_sha256":sha(DEM.read_bytes()),
"input":2847,"R3_DEM_three_point_counties":n,"DEM_total_samples":36,
"R3_unscanned":unknown,"R3_confirmed_exclusions":0,"R3_carry_forward":2847,
"formal_valid_county_screenings":0,"formal_grade_changes":0,
"R3_records":records,"csv_sha256":sha(p.read_bytes()),
"limitations":["Historical county DEM samples are not actual residences",
 "High-elevation points cannot eliminate lower residential areas without audit",
 "2026 official county boundaries remain unverified",
 "Only 12 of 2847 counties have R3 elevation point evidence"]}
(OUT/"national_r3_first_real_batch_evidence.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"R3_true_DEM_three_point_counties":n,"actual_DEM_samples":36,
"R3_not_scanned":unknown,"R4_carry_forward":2847,"confirmed_exits":0},ensure_ascii=False),flush=True)
