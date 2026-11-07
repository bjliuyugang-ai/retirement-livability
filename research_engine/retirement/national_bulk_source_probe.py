#!/usr/bin/env python3
"""Validate alternative high-throughput China climate source methods.
NASA POWER: user-approved custom 1991-2020 climatology, strict parameter
semantics (T2M_MAX_AVG is average daily high, NOT T2M_MAX max extreme).
Meteostat: bulk download metadata diagnostic only, not a climate measurement.
No formal county grades or automatic exclusions.
"""
import datetime,hashlib,json,pathlib,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
def get(url,method="GET",timeout=95):
    request=urllib.request.Request(url,method=method,headers={"User-Agent":"RetirementClimateSourceQA/2026-11-07","Accept":"application/json, */*"})
    with urllib.request.urlopen(request,timeout=timeout) as response:
        b=response.read() if method=="GET" else b""
        return {"url":url,"status":response.status,"content_type":response.headers.get("Content-Type"),
          "content_length_header":response.headers.get("Content-Length"),"raw":b}
def parse_power_point(source,expected):
    data=json.loads(source["raw"])
    props=data.get("properties",{})
    params=props.get("parameter",{})
    if expected not in params:
        raise ValueError("NASA monthly parameter not present: "+expected+"; keys="+str(list(params)))
    raw=params[expected]
    keys=[x for x in raw if x.upper() in {"JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"}]
    if len(keys)!=12:raise ValueError("NASA climatology did not return twelve months "+str(list(raw)))
    values={x:raw[x] for x in keys}
    if any(v is None or not -80<float(v)<70 for v in values.values()):
        raise ValueError("NASA climatology contains invalid daily highs")
    return {"months":values,"month_count":len(keys),
      "parameter":expected,"source_version":data.get("header",{}),
      "raw_sha256":hashlib.sha256(source["raw"]).hexdigest(),
      "raw_bytes":len(source["raw"])}
res={"generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "schema":"RET_NATIONWIDE_CLIMATE_HIGH_THROUGHPUT_SOURCE_QA_V1",
 "stage":"SOURCE_PROBE_NOT_COUNTY_SCREENING","formal_valid_county_screenings":0,
 "official_2026_county_codes_verified":0,
 "sources":[],"notes":["1991-2020 NASA POWER derived climatology is independent source, not CMA normal",
 "NASA T2M_MAX_AVG must not be confused with monthly all-time maximum T2M_MAX",
 "Regional climatology may have coarse 0.5 degree grid and does not resolve county microclimate",
 "No API source is assumed working before response-level tests"]}
attempts=[
 ("nasa_power_custom_1991_2020_mengzi_tmax_avg","https://power.larc.nasa.gov/api/temporal/climatology/point?"+
  urllib.parse.urlencode({"parameters":"T2M_MAX_AVG","community":"SB","longitude":"103.39","latitude":"23.37",
  "format":"JSON","start":"1991","end":"2020"}),"power_point"),
 ("nasa_power_custom_1991_2020_mengzi_tmin_avg","https://power.larc.nasa.gov/api/temporal/climatology/point?"+
  urllib.parse.urlencode({"parameters":"T2M_MIN_AVG","community":"SB","longitude":"103.39","latitude":"23.37",
  "format":"JSON","start":"1991","end":"2020"}),"power_point"),
 ("nasa_power_2deg_region_custom_tmax_avg","https://power.larc.nasa.gov/api/temporal/climatology/regional?"+
  urllib.parse.urlencode({"parameters":"T2M_MAX_AVG","community":"SB","longitude-min":"102","longitude-max":"104",
  "latitude-min":"22","latitude-max":"24","format":"JSON","start":"1991","end":"2020"}),"power_regional"),
 ("meteostat_all_station_monthly_parquet_head","https://data.meteostat.net/monthly.parquet","head")
]
for name,url,typ in attempts:
    entry={"name":name,"url":url,"status":"NOT_TESTED"}
    try:
        if typ=="head":
            z=get(url,method="HEAD",timeout=30)
            entry.update({"status":"HEAD_RESPONDED","http_status":z["status"],
                "content_type":z["content_type"],"content_length_header":z["content_length_header"],
                "actual_climate_data_downloaded":False})
        else:
            z=get(url,timeout=95);entry.update({"http_status":z["status"],"content_type":z["content_type"],
                "raw_sha256":hashlib.sha256(z["raw"]).hexdigest(),"raw_bytes":len(z["raw"])})
            (OUT/(name+".json")).write_bytes(z["raw"])
            if typ=="power_point":
                expected="T2M_MIN_AVG" if "tmin" in name else "T2M_MAX_AVG"
                entry.update(parse_power_point(z,expected))
                entry["status"]="PASS_TWELVE_MONTH_CUSTOM_1991_2020"
                entry["actual_climate_data_downloaded"]=True
            else:
                d=json.loads(z["raw"])
                entry["response_structure"]={"top_level_type":type(d).__name__,
                    "top_level_keys":list(d)[:20] if isinstance(d,dict) else []}
                if not isinstance(d,(dict,list)):raise ValueError("Unexpected NASA region JSON structure")
                entry["status"]="REGIONAL_HTTP_JSON_RETURNED_NEEDS_SPATIAL_SCHEMA_QA"
                entry["actual_climate_data_downloaded"]=True
    except Exception as exc:
        entry.update({"status":"BLOCKED_WITH_ACTUAL_ERROR","error":repr(exc),"actual_climate_data_downloaded":False})
    res["sources"].append(entry);print(json.dumps({k:v for k,v in entry.items() if k!="months"},ensure_ascii=False),flush=True)
res["nasa_custom_point_months_pass"]=sum(x["status"]=="PASS_TWELVE_MONTH_CUSTOM_1991_2020" for x in res["sources"])
res["nasa_regional_json_obtained"]=any(x["name"]=="nasa_power_2deg_region_custom_tmax_avg" and
 x["status"]=="REGIONAL_HTTP_JSON_RETURNED_NEEDS_SPATIAL_SCHEMA_QA" for x in res["sources"])
res["status"]="PASS_REAL_SOURCE_PROBE" if res["nasa_custom_point_months_pass"]>=1 or res["nasa_regional_json_obtained"] else "BLOCKED_WITH_EVIDENCE"
(OUT/"national_bulk_source_probe.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":res["status"],"point_custom_pass":res["nasa_custom_point_months_pass"],
 "region_response":res["nasa_regional_json_obtained"],
 "meteostat_probe":res["sources"][-1]["status"]},ensure_ascii=False),flush=True)
if res["status"]!="PASS_REAL_SOURCE_PROBE":raise SystemExit(2)
