#!/usr/bin/env python3
"""Actual R3 natural altitude evidence across the full 2847 mainland county
candidate ledger, based only on existing station metadata (201 stations)
and independent Copernicus DEM (12 county candidates, 36 samples).

198 unique station-coded counties + 12 DEM counties with five overlaps => 205
distinct candidates having SOME R3 point altitude evidence, never a certified
residential elevation. No hard exclusions using station height or 3 DEM points.
"""
import collections,csv,datetime,hashlib,json,pathlib
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
ST=ROOT/"status/meteostat_CN_226_R1_tiered_expansion_evidence.json"
DEM=ROOT/"status/latest-microclimate-pilot.json"
PREV=ROOT/"status/national_R2_132_interim_obs_source_2847.csv"
SUM=ROOT/"status/meteostat_CN132_interim_R2_evidence.json"
def sha(b):return hashlib.sha256(b).hexdigest()
st=json.loads(ST.read_text(encoding="utf-8"));dem=json.loads(DEM.read_text(encoding="utf-8"));prior=json.loads(SUM.read_text(encoding="utf-8"))
if not (st["original_226_observational_temperature_stations"]==226
 and st["reproduced_69_long_station_identity_and_geometry_accepted"]==69
 and st["interim_stations_spatially_accepted"]==132
 and dem["dem_points_loaded"]==36 and dem["sites_count"]==12
 and prior["R2_total_counties_any_partial_evidence_including_interim"]==199):
 raise RuntimeError("R3 source predecessor changed")
if sha(PREV.read_bytes())!=prior["national_output_csv_sha256"]:raise RuntimeError("National 2847 input CSV source hash changed")
with PREV.open(encoding="utf-8-sig",newline="") as f:
 reader=csv.DictReader(f);fields=list(reader.fieldnames);rows=list(reader)
bycode={r["candidate_code"]:r for r in rows}
if len(rows)!=2847 or len(bycode)!=2847:raise RuntimeError("National county code cardinality changed")
stationrecords=[x for x in st["station_details"] if x["accept_for_long_period_R1"] or x["accept_for_interim_partial_R1"]]
by_stationcode=collections.defaultdict(list)
for r in stationrecords:
 alt=r["station_elevation_m"]
 if alt is None or not (-100<=float(alt)<=9500):raise RuntimeError("Missing or impossible station altitude "+r["station_id"])
 by_stationcode[r["coded_candidate_code"]].append(r)
by_dem={str(x["candidate_county_code"]):x for x in dem["points"]}
if not(len(stationrecords)==201 and len(by_stationcode)==198 and len(by_dem)==12):
 raise RuntimeError("Incorrect point counts")
codes=set(by_stationcode)|set(by_dem)
if len(codes)!=205:raise RuntimeError("Unexpected station/DEM county overlap")
def band(alt):
 if alt<1500:return "STATION_POINT_0_1500_REFERENCE"
 if alt<1800:return "STATION_POINT_1500_1800_CAUTION"
 if alt<=2000:return "STATION_POINT_1800_2000_CAUTION"
 return "STATION_POINT_OVER_2000_NEED_RESIDENTIAL_VALLEY_EXCEPTION"
quality=collections.Counter();features=[];highpointcodes=set();large_alt_sites=[]
for code in sorted(codes):
 if code not in bycode:raise RuntimeError("Point record not in provisional 2847 county registry "+code)
 station=by_stationcode.get(code,[])
 demrow=by_dem.get(code)
 alts=sorted(float(x["station_elevation_m"]) for x in station)
 delta=round(max(alts)-min(alts),1) if alts else 0
 dspan=int(demrow["sample_dem_span_m"]) if demrow else None
 if station and demrow:source="BOTH_STATION_AND_DEM_SAMPLED"
 elif station:source="STATION_METADATA_ONLY"
 else:source="DEM_THREE_POINT_ONLY"
 quality[source]+=1
 stationhigh=any(x>2000 for x in alts)
 demhigh=bool(demrow and demrow["sample_dem_max_m"]>2000)
 highpointcodes.add(code) if (stationhigh or demhigh) else None
 large=bool(delta>=500 or (dspan is not None and dspan>=500))
 if large:large_alt_sites.append(code)
 z={"candidate_code":code,"candidate_name":bycode[code]["candidate_name"],
 "station_metadata_station_count":len(station),
 "station_point_ids":[x["station_id"] for x in station],
 "station_point_lat_lon":[[x["station_lat"],x["station_lon"]] for x in station],
 "station_point_elevation_m":alts,
 "station_altitude_min_m":min(alts) if alts else None,
 "station_altitude_max_m":max(alts) if alts else None,
 "multi_station_altitude_span_m":delta if len(alts)>1 else None,
 "station_point_altitude_reference_bands":[band(x) for x in alts],
 "three_point_Copernicus_dem_available":bool(demrow),
 "dem_three_point_sample_elevations_m":[int(x["copernicus_glo90_elevation_m"]) for x in demrow["points"]] if demrow else [],
 "dem_three_point_min_m":demrow["sample_dem_min_m"] if demrow else None,
 "dem_three_point_max_m":demrow["sample_dem_max_m"] if demrow else None,
 "dem_three_point_span_m":dspan,
 "source_point_elevation_class":source,
 "significant_internal_altitude_heterogeneity_flag":large,
 "high_station_or_DEM_point_over_2000_m":stationhigh or demhigh,
 "residential_elevation_verified":False,
 "official_current_2026_geometry_verified":False,
 "basis":"Meteostat station metadata altitude + Copernicus GLO90 three-point DEM inside historical polygon, not dwelling and not county extrema",
 "can_set_county_grade_or_remove":False}
 features.append(z)
 r=bycode[code]
 if r["R3_status"]=="NOT_SCREENED":
  r["R3_status"]="STATION_AND_DEM_POINT_ALTITUDE_PENDING_RESIDENCE" if station and demrow else (
       "STATION_METADATA_ELEVATION_PENDING_RESIDENCE" if station else "THREE_DEM_SAMPLES_PENDING_RESIDENCE")
  r["last_completed_round"]="R3_POINT_ALTITUDE_PARTIAL"
  r["cascade_status"]="ACTIVE_PENDING"
 r["R3_point_evidence_source_class"]=source
 r["R3_station_ids"]=";".join(z["station_point_ids"])
 r["R3_station_elevations_m"]=";".join(str(int(a) if a.is_integer() else a) for a in alts)
 r["R3_dem_3sample_elevations_m"]=";".join(str(a) for a in z["dem_three_point_sample_elevations_m"])
 r["R3_altitude_heterogeneity_flag"]="TRUE" if large else "FALSE"
 r["R3_over2000_point_warning_nonfatal"]="TRUE" if z["high_station_or_DEM_point_over_2000_m"] else "FALSE"
 r["R3_residential_altitude_verified"]="FALSE"
 r["R3_missing_parameters"]="EXACT_RESIDENTIAL_COORDINATE;2026_OFFICIAL_POLYGON;VALLEY_LOW_ALTITUDE_EXCEPTIONS;LANDSLIDE_AND_FLOOD_RISK"
 if r["confirmed_exit_round"] or str(r["valid_county_screening"]).lower()=="true":
  raise RuntimeError("Unexpected formal county grade/exclusion")
extra=["R3_point_evidence_source_class","R3_station_ids","R3_station_elevations_m","R3_dem_3sample_elevations_m",
 "R3_altitude_heterogeneity_flag","R3_over2000_point_warning_nonfatal","R3_residential_altitude_verified","R3_missing_parameters"]
# Earlier R3 pilot schema may already reserve an empty column for the
# same parameter; preserve the column identity rather than treating existence
# as a source-evidence conflict. Actual new values come only from 201 real
# station altitudes and 36 archived DEM points.
prior_columns=[k for k in extra if k in fields]
fields += [k for k in extra if k not in fields]
countall=sum(r["R3_status"]!="NOT_SCREENED" for r in rows)
if countall!=205:raise RuntimeError("Actual R3 count changed unexpectedly "+str(countall))
path=OUT/"national_R3_205_station_dem_altitude_partial_2847.csv"
with path.open("w",encoding="utf-8-sig",newline="") as f:
 writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
sourcecsv=OUT/"national_R3_205_station_dem_point_evidence.csv"
columns=["candidate_code","candidate_name","station_metadata_station_count","station_point_ids",
 "station_point_elevation_m","station_altitude_min_m","station_altitude_max_m","multi_station_altitude_span_m",
 "three_point_Copernicus_dem_available","dem_three_point_sample_elevations_m","dem_three_point_min_m","dem_three_point_max_m",
 "dem_three_point_span_m","source_point_elevation_class",
 "significant_internal_altitude_heterogeneity_flag","high_station_or_DEM_point_over_2000_m",
 "residential_elevation_verified","official_current_2026_geometry_verified"]
with sourcecsv.open("w",encoding="utf-8-sig",newline="") as f:
 writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
 for z in features:
  rr={k:z.get(k) for k in columns}
  for k in ["station_point_ids","station_point_elevation_m","dem_three_point_sample_elevations_m"]:
   rr[k]=json.dumps(rr[k],ensure_ascii=False)
  writer.writerow(rr)
report={"schema":"RET_NATIONAL_2847_R3_205_ACTUAL_STATION_AND_GLO90_DEM_SOURCE_ONLY_V1",
 "asof_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "station_metadata_source_sha256":sha(ST.read_bytes()),
 "Copernicus_3point_dem_source_sha256":sha(DEM.read_bytes()),
 "original_R2_2847_national_sha256":sha(PREV.read_bytes()),
 "input_2025_2026_provisional_counties":2847,
 "accepted_station_points":201,"station_altitude_counties":198,
 "DEM_3sample_counties":12,"DEM_total_sample_points":36,
 "overlap_station_and_DEM_counties":5,
 "total_R3_partial_point_evidence_counties":countall,
 "R3_completely_unmeasured_counties":2847-countall,
 "source_class_counts":dict(quality),
 "preexisting_source_csv_R3_column_headers":prior_columns,
 "R3_countries_with_station_or_DEM_over2000m_point":len(highpointcodes),
 "R3_countries_with_station_or_3point_DEM_spread_ge500m":len(large_alt_sites),
 "high_point_reference_only_codes":sorted(highpointcodes),
 "heterogeneity_review_codes":sorted(large_alt_sites),
 "source_point_evidence_county_records":features,
 "R1_any_partial_retained":214,"R2_any_partial_retained":199,
 "all_carry_forward":2847,"formal_valid_county_screenings":0,"confirmed_exclusions":0,
 "provisional_nonhard_station_reference_bands":[[0,1500],[1500,1800],[1800,2000],[2000,None]],
 "output_national_csv_sha256":sha(path.read_bytes()),
 "output_station_DEM_csv_sha256":sha(sourcecsv.read_bytes()),
 "cautions":["STA elevation is not residential elevation, DEM only 3 historical polygon sampled locations and may miss low-elevation city or valleys",
 "Any >2000m altitude at one station cannot be used to eliminate entire county, especially canyon/river settlements",
 "Strong county microclimate heterogeneity flagged for independent residential-site sampling before rating",
 "2026 current official county boundary and high-resolution residential address unknown",
 "No natural hazard/earthquake/landslide/flood/air/water assessment completed by this source",
 "No A/B/C/D formal grades, no exclusions, all 2847 carry forward"]}
(OUT/"national_R3_205_station_dem_altitude_source_evidence.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["accepted_station_points","station_altitude_counties",
 "DEM_3sample_counties","DEM_total_sample_points","overlap_station_and_DEM_counties",
 "total_R3_partial_point_evidence_counties","R3_completely_unmeasured_counties",
 "source_class_counts","R3_countries_with_station_or_DEM_over2000m_point",
 "R3_countries_with_station_or_3point_DEM_spread_ge500m"]},ensure_ascii=False),flush=True)
