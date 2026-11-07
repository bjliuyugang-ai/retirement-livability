#!/usr/bin/env python3
"""Nationwide honest administrative code comparison: 2025-year-end historical
code compilation vs 2024 compilation and a third-party 2891-feature coded
county GeoJSON. Source for 2025 compilation cites Ministry's National Geonames
Database, but repository mirror is NOT independently verified 2026 official
live data. MCA live service was DNS-blocked; do not certify latest county list.

Keeps 2847 R0-R5 old candidates without exclusions. Spotlights stale geometry
e.g. Chongqing 2025 Liangiang district (500157) vs older 500105 / 500112.
"""
import collections,csv,datetime,hashlib,json,pathlib,re,urllib.request
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
PREV=ROOT/"status/national_R2_meteostat_station_source_2847.csv"
PREVSUM=ROOT/"status/national_R2_meteostat_station_source_evidence.json"
MIRROR=ROOT/"evidence/mirror_2025_adcodes.txt"
SQA=ROOT/"status/meteostat_70_station_coded_county_spatial_QA.json"
OFFPROBE=ROOT/"status/mca_official_api_real_access_QA.json"
SOURCES={
 "2025":"https://raw.githubusercontent.com/yescallop/areacodes/master/data/2025.txt",
 "2024":"https://raw.githubusercontent.com/yescallop/areacodes/master/data/2024.txt",
 "coded_geometry":"https://raw.githubusercontent.com/zzhonglei/GeoCode-Release/main/contributions/china-admin-boundaries/skill/data/china_county.geojson"}
def sha(b):return hashlib.sha256(b).hexdigest()
def fetch(url,max_bytes):
 req=urllib.request.Request(url,headers={"User-Agent":"National2025CodeAndGeometryDeltaQA/1.0"})
 with urllib.request.urlopen(req,timeout=140) as f:b=f.read(max_bytes+1)
 if len(b)>max_bytes:raise RuntimeError("Source over limit "+url)
 return b
def parse_text(raw):
 d={}
 for line in raw.decode("utf-8-sig").splitlines():
  if not line.strip():continue
  m=re.fullmatch(r"([0-9]{6})\\s+(.+)",line.strip())
  if not m:raise RuntimeError("Invalid 2025/24 code line "+line[:80])
  code,name=m.group(1),m.group(2)
  if code in d:raise RuntimeError("Duplicate in year-end historical code list "+code)
  d[code]=name
 return d
prev=json.loads(PREVSUM.read_text(encoding="utf-8"))
station=json.loads(SQA.read_text(encoding="utf-8"))
official=json.loads(OFFPROBE.read_text(encoding="utf-8"))
if not(prev["R2_total_partial_site_counties"]==73 and station["station_provisional_code_geoposition_and_name_accepted"]==69 and
 official["source_status"]=="OFFICIAL_API_BLOCKED_WITH_REAL_ERROR" and prev["formal_valid_county_screenings"]==0):
 raise RuntimeError("Wrong source/previous status")
if sha(PREV.read_bytes())!=prev["CSV_sha256"]:raise RuntimeError("National R2 evidence source digest changed")
with PREV.open(encoding="utf-8-sig",newline="") as f:
 rd=csv.DictReader(f);rows=list(rd)
if len(rows)!=2847:raise RuntimeError("National input changed")
bycode={r["candidate_code"]:r for r in rows}
raw25=fetch(SOURCES["2025"],500000);raw24=fetch(SOURCES["2024"],500000)
rawgeom=fetch(SOURCES["coded_geometry"],30_000_000)
yr25=parse_text(raw25);yr24=parse_text(raw24)
mirror=parse_text(MIRROR.read_bytes())
if yr25!=mirror:raise RuntimeError("Prior 2025 mirror not same as independently sourced historical 2025 compilation")
county25={code:name for code,name in yr25.items() if not code.endswith("00")}
county24={code:name for code,name in yr24.items() if not code.endswith("00")}
geodata=json.loads(rawgeom);features=geodata.get("features") or []
geo={}
for f in features:
 p=f.get("properties") or {}
 code=str(p.get("adcode") or "");name=str(p.get("name") or "")
 if not re.fullmatch(r"[0-9]{6}",code):raise RuntimeError("GeoJSON invalid 6-digit code")
 if code in geo:raise RuntimeError("duplicate geom code")
 geo[code]=name
if len(geo)!=2891 or len(county25)!=2847 or len(bycode)!=2847:raise RuntimeError("Unexpected national denominator or geometry feature count "+str((len(geo),len(county25),len(bycode))))
if set(bycode)!=set(county25):raise RuntimeError("R0 2847 candidate IDs differ from 2025 source IDs")
if any(bycode[k]["candidate_name"]!=v for k,v in county25.items()):raise RuntimeError("R0 name mismatch 2025 source")
codes_missing_geom=sorted(set(county25)-set(geo))
extra_geom=sorted(set(geo)-set(county25))
samecodes=sorted(set(geo)&set(county25))
name_different=[k for k in samecodes if geo[k]!=county25[k]]
year_added=sorted(set(yr25)-set(yr24))
year_deleted=sorted(set(yr24)-set(yr25))
year_renamed=sorted(k for k in set(yr25)&set(yr24) if yr25[k]!=yr24[k])
accepted=[s for s in station["station_records"] if s["can_add_county_R1_station_evidence"]]
station_wrong=[s for s in accepted if s["2026_candidate_county_code"] not in county25 or county25[s["2026_candidate_county_code"]]!=s["coded_geometry_name"]]
if len(station_wrong)!=0:raise RuntimeError("Mapped climate station code not in independent 2025 roster")
# Do not treat 2025 compilation as official 2026 current; geo snapshot vintage unknown.
status_rows=[]
for code in sorted(set(county25)|set(geo)):
 code_25=county25.get(code);geo_name=geo.get(code)
 if code_25 is None:status="GEOMETRY_CODE_NOT_IN_2025_COUNTY_ROSTER"
 elif geo_name is None:status="2025_COUNTY_HAS_NO_CODED_GEOMETRY"
 elif code_25!=geo_name:status="SAME_CODE_NAME_MISMATCH"
 else:status="SOURCE_LEVEL_CODE_NAME_CONCORDANT"
 item=bycode.get(code)
 status_rows.append({"code":code,"historical_2025_name":code_25 or "",
 "third_party_coded_geom_name":geo_name or "","source_comparison_status":status,
 "in_2024_county_roster":code in county24,
 "2024_name":county24.get(code) or "",
 "2025_new_county_code":code in county25 and code not in county24,
 "2025_retired_county_code":code in county24 and code not in county25,
 "current_2026_official_code_verified":False,
 "R1_status":item["R1_status"] if item else "OUT_OF_2025_NATIONAL_ROSTER",
 "R2_status":item["R2_status"] if item else "OUT_OF_2025_NATIONAL_ROSTER",
 "R1_can_be_formally_graded":False})
with (OUT/"national_2025_roster_vs_2891_coded_geometry_diff.csv").open("w",encoding="utf-8-sig",newline="") as f:
 cols=list(status_rows[0]);w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(status_rows)
outfile=OUT/"national_2025_roster_vs_2891_coded_geometry_diff.csv"
report={"schema":"RET_2025_HISTORICAL_ROSTER_VS_THIRD_PARTY_CODED_GEOMETRY_AUDIT_V1",
 "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "official_live_portal_status":official["source_status"],
 "official_live_portal_error":official.get("error"),
 "source_urls":SOURCES,"source_sha256":{"2025":sha(raw25),"2024":sha(raw24),"county_geojson":sha(rawgeom)},
 "source_description":"yescallop historical year-end 2025 compilation cites MCA National Geonames database; GeoCode-Release coded map is third-party packaged source",
 "actual_2026_official_live_roster_verified":False,
 "source_historical_code_entries_2025":len(yr25),
 "source_historical_code_entries_2024":len(yr24),
 "historical_2025_non00_county_code_count":len(county25),
 "historical_2024_non00_county_code_count":len(county24),
 "mapped_2025_counties_in_real_R0":len(bycode),
 "coded_geometry_feature_count":len(geo),
 "geometry_code_in_2025_name_same_count":len(samecodes)-len(name_different),
 "2025_county_codes_missing_coded_geometry_count":len(codes_missing_geom),
 "coded_geometry_codes_absent_2025_roster_count":len(extra_geom),
 "same_code_different_name_count":len(name_different),
 "2025_county_codes_missing_coded_geometry":[{"code":k,"name_2025":county25[k]} for k in codes_missing_geom],
 "geometry_codes_absent_2025":[{"code":k,"name_in_geometry":geo[k],"2024_name":yr24.get(k)} for k in extra_geom],
 "same_code_name_mismatches":[{"code":k,"name_2025":county25[k],"name_geom":geo[k]} for k in name_different],
 "year2025_vs_2024_total_codes_added":[{"code":k,"new":yr25[k]} for k in year_added],
 "year2025_vs_2024_total_codes_removed":[{"code":k,"old":yr24[k]} for k in year_deleted],
 "year2025_vs_2024_same_code_renamed":[{"code":k,"old":yr24[k],"new":yr25[k]} for k in year_renamed],
 "mapped_station_codes_consistent_with_2025_history":len(accepted)-len(station_wrong),
 "mapped_station_code_or_name_conflicts_in_2025":station_wrong,
 "source_QA_70_code_name_conflicts_kept_hold":station["station_unresolved_due_to_code_or_identity"],
 "R1_partial_evidence_counties_retained":87,"R2_partial_evidence_counties_retained":73,
 "no_2026_formal_county_screenings":0,"no_unauthorized_county_exclusions":0,
 "national_diff_csv_sha256":sha(outfile.read_bytes()),
 "interpretation_limits":["2025 archived geoname compilation is NOT direct 2026 authenticated official endpoint result",
 "Third-party GeoJSON code geometry date and map certification NOT established",
 "Source code/name differences indicate possible stale geometry, aliases, direct-admin jurisdiction or polygons; no automatic administrative exclusion",
 "All 2847 counties retained for real screening; missing coded geometry becomes spatial QA pending, not excluded"]}
(OUT/"national_2025_roster_vs_2891_coded_geometry_evidence.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["historical_2025_non00_county_code_count","coded_geometry_feature_count",
 "geometry_code_in_2025_name_same_count","2025_county_codes_missing_coded_geometry_count",
 "coded_geometry_codes_absent_2025_roster_count","same_code_different_name_count",
 "mapped_station_codes_consistent_with_2025_history"]},ensure_ascii=False),flush=True)
