#!/usr/bin/env python3
"""One-time Meteostat monthly bulk+stations.db provenance and 1991-2020 coverage QA.

Downloaded Parquet/station DB retained only as GitHub Actions runtime data and
checksummed. Station location bbox is NOT official Chinese administrative proof.
Monthly sources may be observation/model blends; no formal county grade.
"""
import datetime,hashlib,json,pathlib,sqlite3,time,urllib.request
import duckdb
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
DATA=OUT/"meteostat_bulk_runtime";DATA.mkdir(parents=True,exist_ok=True)
res={"schema":"RET_METEOSTAT_STATION_BULK_MONTHLY_1991_2020_QA_V1",
 "generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "status":"RUNNING","sources":[],"base_period":"1991-2020",
 "site_is_official_current_county_verified":False,"formal_county_screenings":0,
 "caveats":["Meteostat monthly dataset may include model substitutes; source columns must be inspected",
   "Station coordinates are site-specific; cannot certify county boundary, residence or safety",
   "Station inventory data may be incomplete and uneven across provinces",
   "No country claims from a bounding box alone"]}
def download(url,name,maxbytes):
 path=DATA/name;h=hashlib.sha256();n=0
 req=urllib.request.Request(url,headers={"User-Agent":"RetirementMeteostatStationCoverageQA/0.1"})
 with urllib.request.urlopen(req,timeout=180) as rr, path.open("wb") as f:
  for chunk in iter(lambda:rr.read(1024*1024),b""):
   n+=len(chunk)
   if n>maxbytes:raise ValueError("Source too large for pilot")
   f.write(chunk);h.update(chunk)
 item={"url":url,"bytes":n,"sha256":h.hexdigest(),"filename":name}
 res["sources"].append(item)
 print("DOWNLOADED",name,n,h.hexdigest()[:15],flush=True)
 return path
try:
 p=download("https://data.meteostat.net/monthly.parquet","monthly.parquet",210_000_000)
 q=download("https://data.meteostat.net/stations.db","stations.db",170_000_000)
 sq=sqlite3.connect(str(q))
 tables=[x[0] for x in sq.execute("SELECT name FROM sqlite_master WHERE type='table'")]
 res["station_db_tables"]=tables
 if "stations" not in tables:raise ValueError("Meteostat SQLite lacks stations table")
 stationcols=[r[1] for r in sq.execute("PRAGMA table_info(stations)")]
 res["station_db_columns"]=stationcols
 idcol=next((x for x in ["id","station","station_id"] if x in stationcols),None)
 latcol=next((x for x in ["latitude","lat"] if x in stationcols),None)
 loncol=next((x for x in ["longitude","lon"] if x in stationcols),None)
 if not all([idcol,latcol,loncol]):raise ValueError("Meteostat station DB lacks expected id/lat/lon columns")
 countrycol=next((x for x in ["country","country_code"] if x in stationcols),None)
 sql="SELECT "+",".join([idcol,latcol,loncol]+([countrycol] if countrycol else []))+" FROM stations WHERE "+latcol+" BETWEEN 17 AND 55 AND "+loncol+" BETWEEN 73 AND 135"
 candidates=list(sq.execute(sql))
 res["station_db_total_stations"]=sq.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
 res["candidate_station_bbox_count"]=len(candidates)
 res["country_column_present"]=bool(countrycol)
 if countrycol:
  res["observed_country_values_in_bbox"]=dict(list(sq.execute(
      "SELECT "+countrycol+",COUNT(*) AS n FROM stations WHERE "+latcol+" BETWEEN 17 AND 55 AND "+loncol+" BETWEEN 73 AND 135 GROUP BY "+countrycol+" ORDER BY n DESC LIMIT 12")))
 if not candidates:raise ValueError("No candidate stations in China geographic bbox")
 con=duckdb.connect(database=":memory:")
 info=con.execute("DESCRIBE SELECT * FROM read_parquet(?)",[str(p)]).fetchall()
 names=[r[0] for r in info]
 res["monthly_parquet_columns"]=[{"name":r[0],"dtype":r[1]} for r in info]
 meta=con.execute("SELECT COUNT(*) FROM read_parquet(?)",[str(p)]).fetchone()[0]
 res["monthly_parquet_total_records"]=meta
 stationfield=next((c for c in ["station","station_id","id"] if c in names),None)
 datefield=next((c for c in ["time","date","month"] if c in names),None)
 tmaxfield=next((c for c in ["tmax","txav"] if c in names),None)
 if not all([stationfield,datefield,tmaxfield]):raise ValueError("No expected monthly station/time/tmax: "+str(names))
 con.execute("CREATE TABLE box_station_ids (id VARCHAR)")
 con.executemany("INSERT INTO box_station_ids VALUES (?)",[(str(row[0]),) for row in candidates])
 sql=("SELECT COUNT(*) AS months_with_tmax, COUNT(DISTINCT a."+stationfield+") AS station_count "+
  "FROM read_parquet(?) a JOIN box_station_ids b ON CAST(a."+stationfield+" AS VARCHAR)=b.id "+
  "WHERE TRY_CAST(a."+datefield+" AS DATE) BETWEEN DATE '1991-01-01' AND DATE '2020-12-31' "+
  "AND a."+tmaxfield+" IS NOT NULL")
 total,stations=con.execute(sql,[str(p)]).fetchone()
 res["bbox_1991_2020_monthly_tmax_observation_rows"]=int(total)
 res["bbox_1991_2020_monthly_tmax_station_count"]=int(stations)
 sourcefield=tmaxfield+"_source"
 if sourcefield in names:
  sql=("SELECT CAST(a."+sourcefield+" AS VARCHAR), COUNT(*) AS n FROM read_parquet(?) a "+
   "JOIN box_station_ids b ON CAST(a."+stationfield+" AS VARCHAR)=b.id "+
   "WHERE TRY_CAST(a."+datefield+" AS DATE) BETWEEN DATE '1991-01-01' AND DATE '2020-12-31' "+
   "AND a."+tmaxfield+" IS NOT NULL GROUP BY 1 ORDER BY n DESC LIMIT 20")
  res["tmax_source_values"]=[{"source":r[0],"records":int(r[1])} for r in con.execute(sql,[str(p)]).fetchall()]
 else:
  res["tmax_source_values"]="SOURCE_FIELD_MISSING"
 # Distinguish station records with full 30yr coverage from scattered or model-substituted data.
 sql=("SELECT COUNT(*) FROM (SELECT CAST(a."+stationfield+" AS VARCHAR) AS sid, "+
  "COUNT(DISTINCT STRFTIME(TRY_CAST(a."+datefield+" AS DATE),'%Y-%m')) AS months "+
  "FROM read_parquet(?) a JOIN box_station_ids b ON CAST(a."+stationfield+" AS VARCHAR)=b.id "+
  "WHERE TRY_CAST(a."+datefield+" AS DATE) BETWEEN DATE '1991-01-01' AND DATE '2020-12-31' "+
  "AND a."+tmaxfield+" IS NOT NULL GROUP BY 1 HAVING COUNT(DISTINCT STRFTIME(TRY_CAST(a."+datefield+" AS DATE),'%Y-%m')) >=300)")
 res["bbox_stations_ge300_of360_months_tmax"]=con.execute(sql,[str(p)]).fetchone()[0]
 res["status"]="REAL_STATION_BULK_DATA_READ_WITH_PROVENANCE_LIMITS"
 print("STATION_QA",json.dumps({k:res.get(k) for k in ["monthly_parquet_total_records",
  "candidate_station_bbox_count","bbox_1991_2020_monthly_tmax_station_count",
  "bbox_1991_2020_monthly_tmax_observation_rows",
  "bbox_stations_ge300_of360_months_tmax","tmax_source_values"]},ensure_ascii=False)[:3500],flush=True)
except Exception as ex:
 res["status"]="SOURCE_QA_BLOCKED_WITH_ERROR";res["error"]=repr(ex)
 print("STATION_BULK_ERROR",repr(ex),flush=True)
(OUT/"meteostat_1991_2020_bulk_station_QA.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if res["status"]!="REAL_STATION_BULK_DATA_READ_WITH_PROVENANCE_LIMITS":raise SystemExit(2)
