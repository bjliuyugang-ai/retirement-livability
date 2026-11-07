#!/usr/bin/env python3
"""Inspect ACTUAL archived NASA POWER custom climatology regional GeoJSON.

No remote fetch; uses prior successful 42322382752 artifact to establish
per-feature grid coordinate, temporal schema and climate variable semantics.
"""
import datetime,hashlib,json,pathlib,statistics
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
RAWROOT=OUT/"nasa_probe_archive"
REG=next(iter(RAWROOT.rglob("nasa_power_2deg_region_custom_tmax_avg.json")))
POINT=next(iter(RAWROOT.rglob("nasa_power_custom_1991_2020_mengzi_tmax_avg.json")))
regbytes=REG.read_bytes();data=json.loads(regbytes)
features=data["features"]
if not isinstance(features,list) or not features:raise ValueError("regional NASA data lacks feature records")
example=features[:2]
header=data.get("header",{})
out={"schema":"NASA_REGIONAL_1991_2020_FEATURE_INSPECTION_V1",
 "at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_artifact_run":"42322382752","source_archive":"independent-custom-climate-and-bulk-source-probe",
 "region_raw_sha256":hashlib.sha256(regbytes).hexdigest(),
 "point_raw_sha256":hashlib.sha256(POINT.read_bytes()).hexdigest(),
 "feature_count":len(features),"top_level_keys":list(data.keys()),
 "regional_header":header,
 "regional_parameters":data.get("parameters"),
 "regional_times":data.get("times"),
 "feature_sample":example,
 "feature_geometries":[f.get("geometry",{}) for f in features[:20]],
 "feature_property_keys":[list(f.get("properties",{}).keys()) for f in features[:5]],
 "status":"ACTUAL_REGION_DATA_SCHEMA_READ",
 "formal_valid_county_screenings":0}
path=OUT/"nasa_regional_schema_inspection.json"
path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:out[k] for k in ["status","feature_count","top_level_keys","regional_parameters","regional_times","feature_property_keys"]},ensure_ascii=False)[:2600],flush=True)
print("NASA_FIRST_FEATURE",json.dumps(example[0],ensure_ascii=False)[:2500],flush=True)
