#!/usr/bin/env python3
"""Targeted 11-area autonomous-county alias correction for Anju 1km pharmacy aggregate.
Reads previous 110-row evidence; NEVER repeats completed 99 areas.
No raw individual POI data, no original V12.2 score updates, bounded to <=22 API requests.
"""
import csv
import datetime as dt
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

ROOT = pathlib.Path("anju/results/pharmacy_1km")
SRC = ROOT/"latest.json"
OUT = ROOT/"latest.json"
KEY = os.environ.get("AMAP_WEB_KEY", "")
ALIASES = {
    "云南·峨山县": "峨山彝族自治县",
    "云南·南涧县": "南涧彝族自治县",
    "云南·宁洱县": "宁洱哈尼族彝族自治县",
    "云南·寻甸回族县": "寻甸回族彝族自治县",
    "云南·巍山县": "巍山彝族回族自治县",
    "云南·景东县": "景东彝族自治县",
    "云南·景谷傣族县": "景谷傣族彝族自治县",
    "云南·江城县": "江城哈尼族彝族自治县",
    "云南·漾濞县": "漾濞彝族自治县",
    "云南·石林县": "石林彝族自治县",
    "云南·镇沅县": "镇沅彝族哈尼族拉祜族自治县",
}
REQUEST_LIMIT=22
requests=0
halt_reason=""
def call(endpoint, params):
    global requests,halt_reason
    if requests >= REQUEST_LIMIT:
        halt_reason="REQUEST_CAP_REACHED"
        return None,"CAP_REACHED"
    if not KEY:
        halt_reason="KEY_NOT_CONFIGURED"
        return None,"NO_KEY"
    query=dict(params)
    query["key"]=KEY
    url=endpoint+"?"+urllib.parse.urlencode(query)
    requests+=1
    try:
        with urllib.request.urlopen(urllib.request.Request(
            url,headers={"User-Agent":"Anju-Aggregate-POI-Study/1.0"}
        ),timeout=14) as r:
            result=json.load(r)
        if not isinstance(result,dict): return None,"BAD_BODY"
        if str(result.get("status")) != "1":
            code=str(result.get("infocode","UNKNOWN"))[:20]
            if code.startswith("100"):
                halt_reason="MAP_PROVIDER_ERROR_"+code
            return None,"PROVIDER_"+code
        return result,None
    except (urllib.error.URLError,TimeoutError): return None,"NETWORK_ERROR"
    except (ValueError,UnicodeDecodeError): return None,"JSON_ERROR"
    finally:
        time.sleep(0.25)
def main():
    assert SRC.is_file(), "Missing source 110-area evidence; refusing fresh partial list"
    data=json.loads(SRC.read_text(encoding="utf-8"))
    rows=data["rows"]
    assert len(rows)==110 and len(set(x["area"] for x in rows))==110
    affected=[x for x in rows if x["status"]=="REVIEW_CENTER_MISMATCH"]
    assert len(affected)==11 and set(x["area"] for x in affected)==set(ALIASES)
    assert requests==0
    for row in affected:
        if halt_reason:
            row["status"]="RETRY_BLOCKED_"+halt_reason
            continue
        full=ALIASES[row["area"]]
        query="云南省"+full+"人民政府"
        d,e=call("https://restapi.amap.com/v3/geocode/geo",
                 {"address":query,"output":"json"})
        if e:
            row["status"]="RETRY_GEOCODE_"+e
            continue
        candidates=d.get("geocodes") or []
        if not candidates or not isinstance(candidates[0],dict):
            row["status"]="RETRY_GEOCODE_EMPTY"
            continue
        p=candidates[0]
        address=str(p.get("formatted_address",""))
        district=str(p.get("district",""))
        level=str(p.get("level",""))
        location=str(p.get("location",""))
        try:
            lng,lat=(float(v) for v in location.split(","))
            coords_valid=73<lng<135 and 18<lat<55
        except (ValueError,TypeError):
            coords_valid=False
        if not coords_valid or full not in address+" "+district:
            row["status"]="RETRY_CENTER_WRONG"
            continue
        if "禄劝" in address:
            row["status"]="RETRY_CENTER_WRONG"
            continue
        row.update({"anchor":query,"geocode_matched":True,
                    "geocode_level":level,
                    "geocode_address":address[:150],
                    "center_gcj02":location,"adcode":str(p.get("adcode","")),
                    "center_alias_correction":full,
                    "center_reference_quality":
                     "COUNTY_CENTROID_PROXY" if level=="区县" else "GOVERNMENT_POI_CANDIDATE"})
        p,e=call("https://restapi.amap.com/v5/place/around",
                 {"location":location,"radius":"1000","types":"090601",
                  "sortrule":"distance","page_size":"25","page_num":"1",
                  "output":"json"})
        if e:
            row["status"]="RETRY_POI_"+e
            continue
        pois=p.get("pois")
        if not isinstance(pois,list):
            row["status"]="RETRY_POI_BAD_BODY"
            continue
        count=len({str(x.get("id")) for x in pois if isinstance(x,dict) and x.get("id")})
        row["poi_returned_count"]=count
        if len(pois)>=25:
            row["count_interpretation"]="AT_LEAST_25_NOT_EXACT"
            row["status"]="CAPPED_LOWER_BOUND"
        else:
            row["count_interpretation"]="API_PAGE_COUNT_NOT_FULL_INVENTORY"
            row["status"]="FIRST_PAGE_UNCAPPED"
    data["targeted_autonomous_alias_retry_utc"]=dt.datetime.now(dt.timezone.utc).isoformat()
    data["targeted_retry_requests"]=requests
    data["targeted_retry_halt"]=halt_reason
    data["targeted_retry_aliases"]=ALIASES
    data["original_generated_utc"]=data.get("timestamp_utc")
    data["source"]="Gaode v3 geocode + v5 POI aggregate; county government proxy, corrected autonomous names"
    counts=Counter(x["status"] for x in rows)
    with OUT.open("w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
        f.write("\n")
    with (ROOT/"latest.csv").open("w",encoding="utf-8-sig",newline="") as f:
        fields=sorted(set().union(*(x.keys() for x in rows)))
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"total_areas":len(rows),"new_requests":requests,
                      "statuses":dict(counts),"unresolved":[x["area"] for x in rows if
                           x["status"] not in ("CAPPED_LOWER_BOUND","FIRST_PAGE_UNCAPPED")],
                      "halt":halt_reason,"formal_score_update":0},ensure_ascii=False))
if __name__=="__main__":main()
