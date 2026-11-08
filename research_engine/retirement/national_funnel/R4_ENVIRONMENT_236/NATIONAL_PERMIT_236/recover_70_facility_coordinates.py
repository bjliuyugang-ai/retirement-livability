#!/usr/bin/env python3
"""Recover facility coordinates from 70 actual permits returned by national R4 batch 2.

The previous parallel detail extraction returned 0 coordinates despite HTTP 200.
A deterministic audit on the identical public pages successfully returned five
coordinate pairs when fetched sequentially with a fresh MEE public session.
This correction is a distinct immutable run and does not rewrite batch 2.
"""
import csv,importlib.util,json,pathlib,time
from datetime import datetime,timezone
from collections import defaultdict
from shapely.geometry import Point

ROOT=pathlib.Path("research_engine/retirement/national_funnel/R4_ENVIRONMENT_236/NATIONAL_PERMIT_236")
SOURCE=ROOT/"output/runs/42467472886/NATIONAL_236_PERMIT_FACILITY_DETAIL_SAMPLE.csv"
OUT=ROOT/"output"
CAN=pathlib.Path("research_engine/retirement/national_funnel/FINAL_FILTER/runs/42453646573/FINAL_CARRY_FORWARD_AFTER_R1_R2_R3.csv")
spec=importlib.util.spec_from_file_location("permit_run",ROOT/"run_national_permit_236.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def save(rows,path,fields=None):
 if fields is None:fields=list(rows[0]) if rows else []
 with path.open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)
def main():
 with SOURCE.open(encoding="utf-8-sig",newline="") as f:original=list(csv.DictReader(f))
 with CAN.open(encoding="utf-8-sig",newline="") as f:candidates=list(csv.DictReader(f))
 if len(original)!=70 or len(candidates)!=236:raise RuntimeError("SOURCE_EXPECTATIONS_CHANGED "+str((len(original),len(candidates))))
 if len({x["permit_no"] for x in original})!=70:raise RuntimeError("NOT_UNIQUE_70_PERMITS")
 areas=m.geoms()
 names={c["code"]:c["name"] for c in candidates}
 matched=defaultdict(list)
 rows=[]
 for i,record in enumerate(original,1):
  # Use exact validated public detail fetch and preserve its status.
  fetched=m.detail_one(record)
  lon,lat=fetched.get("facility_lon"),fetched.get("facility_lat")
  matched_codes=[]
  if lon is not None and lat is not None and 70 <= lon <= 140 and 15 <= lat <= 55:
   pt=Point(lon,lat)
   for code,name in names.items():
    g=areas.get(code)
    if g and g["name"]==name and g["geometry"].covers(pt):
     matched_codes.append(code)
  fetched["candidate_code"]=";".join(matched_codes) if len(matched_codes)==1 else ""
  fetched["county_point_match_status"]="ONE_PROVISIONAL_COUNTY_MATCH" if len(matched_codes)==1 else "OUTSIDE_CANDIDATES" if lon is not None and lat is not None else "PENDING_NO_VALID_COORDS"
  if len(matched_codes)==1:matched[matched_codes[0]].append(fetched)
  rows.append(fetched)
  if i%10==0:print("PUBLIC_DETAIL_COORDINATES_RECOVERY",i,"valid",sum(x.get("facility_lon") is not None for x in rows),"candidate_site_hits",sum(len(x) for x in matched.values()),flush=True)
  time.sleep(0.25)
 fields=["candidate_code","company","permit_no","query_city_group","query_city_name","industry","plant_industry","plant_address","admin_region","facility_lon","facility_lat","management","issued","validity","air_pollutant_list","water_pollutant_list","detail_status","county_point_match_status","error","detail_url"]
 save(rows,OUT/"NATIONAL_236_PERMIT_DETAIL_COORDINATES_RECOVERED_70.csv",fields)
 matrix=[]
 for c in candidates:
  hits=matched.get(c["code"],[])
  matrix.append({"code":c["code"],"name":c["name"],"R1_status":c["R1_next_round_status"],
   "public_permit_sample_count_geospatially_matched":len(hits),
   "official_facility_names":"；".join(x["company"] for x in hits),
   "official_industries":"；".join(x.get("plant_industry") or x["industry"] for x in hits),
   "official_facility_lnglat":"；".join(f'{x["facility_lon"]},{x["facility_lat"]}' for x in hits),
   "official_permit_nos":"；".join(x["permit_no"] for x in hits),
   "official_plant_addresses":"；".join(x.get("plant_address","") for x in hits),
   "air_pollutants_list":"；".join(x.get("air_pollutant_list","") for x in hits if x.get("air_pollutant_list")),
   "water_pollutants_list":"；".join(x.get("water_pollutant_list","") for x in hits if x.get("water_pollutant_list")),
   "source_quality":"70_PUBLIC_LICENSE_DETAILS_SAMPLE_NOT_COMPLETE_COUNTY_CENSUS",
   "residential_exposure_verified":"NO","formal_R4_exclusion":"NO"})
 save(matrix,OUT/"NATIONAL_236_PERMIT_FACILITY_MATCH_REPAIRED_70.csv")
 summary={
  "schema":"R4_NATIONAL_236_OFFICIAL_PERMIT_DETAIL_COORDINATES_RECOVERY_V1",
  "created_at_utc":datetime.now(timezone.utc).isoformat(),
  "candidate_count":236,"source_run_id":42467472886,"source_detail_pages":70,
  "sequential_detail_page_requests":70,
  "details_with_coords":sum(x.get("facility_lon") is not None and x.get("facility_lat") is not None for x in rows),
  "details_without_coords":sum(x.get("facility_lon") is None or x.get("facility_lat") is None for x in rows),
  "candidate_count_with_a_sampled_actual_facility":len(matched),
  "facility_sample_points_matching_236_counties":sum(len(x) for x in matched.values()),
  "candidate_matches":[{"code":code,"name":names[code],"companies":[x["company"] for x in p]} for code,p in matched.items()],
  "failures":[{"company":x["company"],"error":x.get("error"),"status":x.get("detail_status")} for x in rows if x.get("facility_lon") is None],
  "formal_exclusions":0,"candidate_count_remaining":236,
  "guards":["70 permitted facilities only; not all facilities in 236 counties.","Exact county polygon match is provisional. Residential proximity, actual emissions, wind direction and groundwater travel unverified.","No candidate with 0 sample matched is proven free of industrial sources.","Pollutants on permit are licensed pollutant species, not actual emissions or violations."]}
 (OUT/"NATIONAL_236_PERMIT_DETAIL_COORDINATES_RECOVERY_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("PUBLIC_PERMIT_70_FINAL",json.dumps({k:summary[k] for k in ("source_detail_pages","details_with_coords","candidate_count_with_a_sampled_actual_facility","facility_sample_points_matching_236_counties","candidate_count_remaining")},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
