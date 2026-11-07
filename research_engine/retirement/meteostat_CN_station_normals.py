#!/usr/bin/env python3
"""Compute actual 1991-2020 monthly station-climatology candidates in China
from Meteostat public bulk monthly Parquet + station metadata SQLite.

Reject station months with source dwd_mosmix (model substitution) for
observational-only summaries; preserve source-family counts and gaps.
Join nearest CN stations to 42 existing archival county-point anchors ONLY
as spatial candidates, never official county or residence confirmation.
"""
import collections,datetime,hashlib,json,math,pathlib,sqlite3,statistics,time,urllib.request,csv
import duckdb
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
DATA=OUT/"meteostat_bulk_runtime";DATA.mkdir(parents=True,exist_ok=True)
CROSS=ROOT/"status/r1_expand_strict_crosswalk.json"
MICRO=ROOT/"status/latest-microclimate-pilot.json"
SOURCES={"monthly.parquet":"https://data.meteostat.net/monthly.parquet",
         "stations.db":"https://data.meteostat.net/stations.db"}
def sha(b):return hashlib.sha256(b).hexdigest()
def ensure(name,url,maxbytes):
 path=DATA/name
 if path.exists() and path.stat().st_size>10000:
  print("REUSED_CACHED_SOURCE",name,path.stat().st_size,flush=True)
  return path
 n=0;h=hashlib.sha256()
 with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"RetirementCNStationNormalsStudy/1.0"}),timeout=170) as rr,path.open("wb") as f:
  for piece in iter(lambda:rr.read(1024*1024),b""):
   n+=len(piece)
   if n>maxbytes:raise ValueError("Oversized pilot download "+name)
   f.write(piece);h.update(piece)
 print("FETCHED",name,n,h.hexdigest()[:15],flush=True)
 return path
def distance_km(a,b,c,d):
 r=6371.0088;p1=math.radians(a);p2=math.radians(c)
 z=math.sin((p2-p1)/2)**2+math.cos(p1)*math.cos(p2)*math.sin(math.radians(d-b)/2)**2
 return 2*r*math.asin(min(1,math.sqrt(z)))
out={"schema":"RET_CN_METEOSTAT_1991_2020_MONTHLY_STATION_NORMALS_V1",
     "asof_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
     "source_urls":SOURCES,"period":"1991-2020",
     "station_source_classes":"ghcnd/climat/isd_lite/metar only; exclude dwd_mosmix model in vetted observation months",
     "official_2026_county_roster_verified":False,"formal_county_screenings":0,
     "data_quality_limit":"MONTHLY_TMAX/TMIN observatory records; not station-certified 1991-2020 CMA normals or dwelling climate"}
try:
 m=ensure("monthly.parquet",SOURCES["monthly.parquet"],210_000_000)
 s=ensure("stations.db",SOURCES["stations.db"],170_000_000)
 out["source_sizes"]={"monthly_bytes":m.stat().st_size,"stations_db_bytes":s.stat().st_size}
 out["source_sha256"]={"monthly_parquet":sha(m.read_bytes()),"station_sqlite":sha(s.read_bytes())}
 con=sqlite3.connect(s)
 stations=[dict(zip(["id","latitude","longitude","elevation","country"],
              row)) for row in con.execute(
              "SELECT id,latitude,longitude,elevation,country FROM stations WHERE country='CN' AND latitude BETWEEN 17 AND 55 AND longitude BETWEEN 73 AND 135")]
 if len(stations)<100:raise RuntimeError("Unexpectedly few CN stations: "+str(len(stations)))
 byid={str(z["id"]):z for z in stations}
 d=duckdb.connect(":memory:")
 d.execute("CREATE TABLE china_stations(id VARCHAR)")
 d.executemany("INSERT INTO china_stations VALUES (?)",[(str(x["id"]),) for x in stations])
 # Meteorology supported fields are station, date, tmax, tmin, prcp, tsun and source.
 schema=[x[0] for x in d.execute("DESCRIBE SELECT * FROM read_parquet(?)",[str(m)]).fetchall()]
 needed={"station","date","tmax","tmin","tmax_source","tmin_source"}
 if not needed.issubset(schema):raise RuntimeError("Bulk Meteostat schema mismatch "+str(schema))
 query="""SELECT CAST(a.station AS VARCHAR), CAST(a.date AS DATE),
 CAST(a.tmax AS DOUBLE), CAST(a.tmin AS DOUBLE),
 CAST(a.tmax_source AS VARCHAR), CAST(a.tmin_source AS VARCHAR)
 FROM read_parquet(?) a JOIN china_stations b ON CAST(a.station AS VARCHAR)=b.id
 WHERE a.date BETWEEN DATE '1991-01-01' AND DATE '2020-12-31'
 ORDER BY a.station, a.date"""
 rows=d.execute(query,[str(m)]).fetchall()
 grouped=collections.defaultdict(list)
 for sid,when,tmax,tmin,srcmax,srcmin in rows:
  grouped[sid].append((when,tmax,tmin,srcmax,srcmin))
 out["stations_CN_in_bbox"]=len(stations)
 out["stations_CN_with_monthly_any"]=len(grouped)
 out["CN_monthly_rows_1991_2020"]=len(rows)
 allowed={"ghcnd","climat","isd_lite","metar","dwd_hourly","dwd_daily"}
 def observed(v):
  if v is None:return False
  ss=str(v).lower().split()
  return bool(ss) and all(x in allowed for x in ss)
 station_results=[]
 for sid,info in grouped.items():
  obs=[(dt,x,y,sx,sy) for dt,x,y,sx,sy in info if x is not None and y is not None and observed(sx) and observed(sy)]
  # Source family distribution across station months.
  providers=collections.Counter()
  for dt,x,y,sx,sy in obs:
   providers[str(sx)]+=1
  permonth=collections.defaultdict(list)
  for dt,x,y,sx,sy in obs:permonth[dt.month].append((float(x),float(y)))
  if not permonth:continue
  mx=sum(len(v) for v in permonth.values())
  good_months=sum(len(permonth[k])>=20 for k in range(1,13))
  complete=mx>=300 and good_months==12
  wt=[12,1,2];su=[6,7,8,9]
  if any(not permonth[k] for k in wt+su):continue
  def clim(keys,pos):
   vals=[v[pos] for key in keys for v in permonth[key]]
   return round(statistics.mean(vals),3)
  station_results.append({"station_id":sid,"station_country":"CN",
    "latitude":info["latitude"],"longitude":info["longitude"],"altitude_m":info["elevation"],
    "months_both_tmax_tmin_observation_class":mx,
    "months_in_each_calendar_month":{str(k):len(permonth[k]) for k in range(1,13)},
    "full30_yr_candidate_ge300months_everymonth_ge20":complete,
    "winter_dec_feb_mean_daily_max_c":clim(wt,0),
    "summer_jun_sep_mean_daily_max_c":clim(su,0),
    "winter_dec_feb_mean_daily_min_c":clim(wt,1),
    "summer_jun_sep_mean_daily_min_c":clim(su,1),
    "observed_provider_counts":dict(providers),
    "source_uncertainty":"provider IDs classify source family; do not prove original record was all CMA observations"})
 stations_good=[x for x in station_results if x["full30_yr_candidate_ge300months_everymonth_ge20"]]
 out["CN_stations_with_source_vetted_any"]=len(station_results)
 out["CN_stations_meeting_ge300_both_tmax_tmin_and_20_per_calendar_month"]=len(stations_good)
 if len(stations_good)<20:raise RuntimeError("Insufficient long station evidence after source provenance filtering")
 # Optional source vetting status makes it a candidate, still non-official.
 cross=json.loads(CROSS.read_text(encoding="utf-8"))
 micro=json.loads(MICRO.read_text(encoding="utf-8"))
 anchors=[{"candidate_code":x["county_code"],"county":x["county_2025_name"],
  "site_class":"2017_polygon_interior_UNVERIFIED_CURRENT",
  "lat":x["latitude_2017_polygon_interior"],
  "lon":x["longitude_2017_polygon_interior"],"anchor_dem_altitude_m":None}
  for x in cross["selected_30"]]
 for x in micro["points"]:
  p=x["points"][0]
  anchors.append({"candidate_code":x["candidate_county_code"],"county":x["site"],
   "site_class":"EXPLORATORY_EXISTING_COUNTY_ERA5_POINT",
   "lat":p["latitude"],"lon":p["longitude"],
   "anchor_dem_altitude_m":p["copernicus_glo90_elevation_m"]})
 if len(anchors)!=42:raise RuntimeError("Expected 42 existing uniquely anchored areas")
 joins=[]
 for a in anchors:
  opts=sorted(stations_good,key=lambda q:distance_km(a["lat"],a["lon"],q["latitude"],q["longitude"]))
  if not opts:continue
  selected=opts[0]
  km=distance_km(a["lat"],a["lon"],selected["latitude"],selected["longitude"])
  altitude_delta=abs(selected["altitude_m"]-a["anchor_dem_altitude_m"]) if a["anchor_dem_altitude_m"] is not None and selected["altitude_m"] is not None else None
  qualifies=km<=65 and (altitude_delta is None or altitude_delta<=350)
  joins.append({"county_candidate":a["county"],"code":a["candidate_code"],"anchor_class":a["site_class"],
   "nearest_CNHQ_station_id":selected["station_id"],"distance_km":round(km,2),
   "station_elevation_m":selected["altitude_m"],"altitude_delta_m":altitude_delta,
   "station_1991_2020_approx_normals":{k:selected[k] for k in [
      "winter_dec_feb_mean_daily_max_c","summer_jun_sep_mean_daily_max_c",
      "winter_dec_feb_mean_daily_min_c","summer_jun_sep_mean_daily_min_c"]},
   "nearby_station_quality_gate":qualifies,
   "official_residential_county_coverage_certified":False,
   "crosswalk_quality":"NEARBY_STATION_WITHIN_65KM_NOT_COUNTY_POLYGON_VERIFIED"})
 out["anchored_county_sample_count"]=len(anchors)
 out["county_anchors_with_station_65km_and_elevation_qc"]=sum(z["nearby_station_quality_gate"] for z in joins)
 out["county_nearest_station_links"]=joins
 out["CN_1991_2020_candidate_station_normals"]=station_results
 out["status"]="REAL_30YEAR_CN_STATION_CANDIDATE_NORMALS_AND_SPATIAL_CROSSWALK"
 # Separate small CSV for convenient auditing.
 stationcsv=OUT/"meteostat_CN_1991_2020_station_candidate_normals.csv"
 keys=["station_id","station_country","latitude","longitude","altitude_m",
       "months_both_tmax_tmin_observation_class",
       "full30_yr_candidate_ge300months_everymonth_ge20",
       "winter_dec_feb_mean_daily_max_c","summer_jun_sep_mean_daily_max_c",
       "winter_dec_feb_mean_daily_min_c","summer_jun_sep_mean_daily_min_c",
       "observed_provider_counts"]
 with stationcsv.open("w",encoding="utf-8-sig",newline="") as f:
  wr=csv.DictWriter(f,fieldnames=keys);wr.writeheader()
  for x in station_results:
   rec={k:x[k] for k in keys}
   rec["observed_provider_counts"]=json.dumps(rec["observed_provider_counts"],ensure_ascii=False)
   wr.writerow(rec)
 out["station_csv_sha256"]=sha(stationcsv.read_bytes())
 print("METEOSTAT_CN_OBS_MONTHS",json.dumps({k:out[k] for k in [
  "CN_monthly_rows_1991_2020","stations_CN_in_bbox",
  "CN_stations_with_source_vetted_any",
  "CN_stations_meeting_ge300_both_tmax_tmin_and_20_per_calendar_month",
  "county_anchors_with_station_65km_and_elevation_qc"]},ensure_ascii=False),flush=True)
except Exception as exc:
 out["status"]="STATION_NORMALS_OR_SPATIAL_QA_FAILED_WITH_EVIDENCE"
 out["error"]=repr(exc)
 print("METEOSTAT_CN_NORMALS_ERROR",repr(exc),flush=True)
(OUT/"meteostat_CN_1991_2020_station_candidate_normals.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if out["status"]!="REAL_30YEAR_CN_STATION_CANDIDATE_NORMALS_AND_SPATIAL_CROSSWALK":raise SystemExit(2)
