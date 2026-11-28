#!/usr/bin/env python3
"""Validate nearest high-speed rail access for Anju's 110 areas.

Method:
1) AMap returns nearby railway-station POIs (not the keyword "high-speed station").
2) Resolve each POI to the official 12306 station dictionary.
3) Verify actual G/D/C passenger service from the official 12306 station-board endpoint
   on one weekday and, only if needed, one weekend date.
4) Route only to the nearest station with observed G/D/C service.

A map POI or station name alone is never treated as proof of high-speed service.
No-result/failed lookups are not silently converted to zero.
"""
import csv
import datetime as dt
import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

SOURCE=pathlib.Path("anju/results/pharmacy_1km/latest.json")
OUT=pathlib.Path("anju/results/transport_hsr_v2")
AMAP_KEY=os.environ.get("AMAP_WEB_KEY","")
AMAP_BASE="https://restapi.amap.com"
AMAP_LIMIT=220
RAIL_LIMIT=240
SERVICE_DATES=("20261201","20261205")  # Tuesday + Saturday
AMAP_REQUESTS=0
RAIL_REQUESTS=0
HALT=""
STATION_CACHE={}
USER_AGENT="Anju-Second-Stage-Research/1.0 (read-only batch)"

def http_json(url, data=None, headers=None, timeout=20):
    req=urllib.request.Request(url,data=data,headers=headers or {},method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req,timeout=timeout) as response:
        raw=response.read(2_000_000)
    return json.loads(raw.decode("utf-8"))

def amap(path, params):
    global AMAP_REQUESTS,HALT
    if AMAP_REQUESTS>=AMAP_LIMIT:
        HALT="AMAP_REQUEST_CAP"
        return None,"AMAP_REQUEST_CAP"
    if not AMAP_KEY:
        HALT="AMAP_KEY_MISSING"
        return None,"AMAP_KEY_MISSING"
    q=dict(params);q["key"]=AMAP_KEY;q["output"]="json"
    AMAP_REQUESTS+=1
    try:
        d=http_json(AMAP_BASE+path+"?"+urllib.parse.urlencode(q),
                    headers={"User-Agent":USER_AGENT})
        if not isinstance(d,dict) or str(d.get("status"))!="1":
            return None,"AMAP_"+str((d or {}).get("infocode","BAD_RESPONSE"))
        return d,None
    except urllib.error.HTTPError as e:
        return None,"AMAP_HTTP_"+str(e.code)
    except Exception as e:
        return None,"AMAP_"+type(e).__name__
    finally:
        time.sleep(0.25)

def station_dictionary():
    url="https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"
    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Referer":"https://kyfw.12306.cn/otn/czxx/init/"})
    with urllib.request.urlopen(req,timeout=25) as response:
        text=response.read(3_000_000).decode("utf-8","replace")
    if "=" not in text:
        raise RuntimeError("12306_STATION_DICTIONARY_BAD_FORMAT")
    payload=text.split("=",1)[1].strip().rstrip(";").strip()
    if len(payload)>=2 and payload[0] in ("'",'"') and payload[-1]==payload[0]:
        payload=payload[1:-1]
    out={}
    for record in payload.split("@"):
        f=record.split("|")
        if len(f)<3 or not f[1].strip() or not f[2].strip():
            continue
        name=f[1].strip()
        code=f[2].strip().upper()
        key=normalize_station_name(name)
        if key and re.fullmatch(r"[A-Z0-9]{3}",code):
            out.setdefault(key,{"name":name,"telecode":code})
    if len(out)<1000:
        raise RuntimeError("12306_STATION_DICTIONARY_INCOMPLETE_"+str(len(out)))
    return out

def normalize_station_name(value):
    s=str(value or "").strip()
    s=re.sub(r"[（(].*?[）)]","",s)
    s=re.sub(r"(进站口|出站口|检票口|候车室)$","",s)
    s=re.sub(r"\s+","",s)
    if s.endswith("站"):
        s=s[:-1]
    return s.strip()

def railway_board(telecode, service_date):
    global RAIL_REQUESTS,HALT
    key=(telecode,service_date)
    if key in STATION_CACHE:
        return STATION_CACHE[key]
    if RAIL_REQUESTS>=RAIL_LIMIT:
        HALT="12306_REQUEST_CAP"
        return {"state":"CAP","gdc":[],"all_count":0}
    url=("https://mobile.12306.cn/wxxcx/wechat/bigScreen/queryTrainByStation"
         f"?train_start_date={service_date}&train_station_code={urllib.parse.quote(telecode)}")
    RAIL_REQUESTS+=1
    try:
        req=urllib.request.Request(url,data=b"",
             headers={"User-Agent":USER_AGENT,
                      "Content-Type":"application/x-www-form-urlencoded",
                      "Referer":"https://www.12306.cn/"},method="POST")
        with urllib.request.urlopen(req,timeout=20) as response:
            body=response.read(2_000_000)
        d=json.loads(body.decode("utf-8","replace"))
        if d.get("status") is not True or not isinstance(d.get("data"),list):
            result={"state":"API_ERROR","gdc":[],"all_count":0,
                    "error":str(d.get("errorMsg") or d.get("errorCode") or d.get("status"))[:120]}
        else:
            rows=d["data"]
            gdc=[]
            for row in rows:
                code=str(row.get("station_train_code") or "").strip().upper() if isinstance(row,dict) else ""
                if len(code)>1 and code[0] in "GDC":
                    gdc.append({"train":code,
                                "origin":str(row.get("start_station_name") or "")[:60],
                                "destination":str(row.get("end_station_name") or "")[:60]})
            result={"state":"OK","gdc":gdc,"all_count":len(rows)}
    except urllib.error.HTTPError as e:
        result={"state":"API_ERROR","gdc":[],"all_count":0,"error":"HTTP_"+str(e.code)}
    except Exception as e:
        result={"state":"API_ERROR","gdc":[],"all_count":0,"error":type(e).__name__}
    STATION_CACHE[key]=result
    time.sleep(1.05)
    return result

def verify_station(telecode):
    first=railway_board(telecode,SERVICE_DATES[0])
    if first["state"]=="OK" and first["gdc"]:
        return {"state":"CONFIRMED_GDC","dates":[SERVICE_DATES[0]],
                "trains":first["gdc"][:8],"all_count":first["all_count"]}
    if first["state"]!="OK":
        return {"state":first["state"],"dates":[SERVICE_DATES[0]],
                "trains":[],"all_count":first.get("all_count",0),
                "error":first.get("error","")}
    second=railway_board(telecode,SERVICE_DATES[1])
    if second["state"]=="OK" and second["gdc"]:
        return {"state":"CONFIRMED_GDC","dates":[SERVICE_DATES[1]],
                "trains":second["gdc"][:8],"all_count":second["all_count"]}
    if second["state"]!="OK":
        return {"state":second["state"],"dates":list(SERVICE_DATES),
                "trains":[],"all_count":second.get("all_count",0),
                "error":second.get("error","")}
    return {"state":"NO_GDC_ON_SAMPLE_DATES","dates":list(SERVICE_DATES),
            "trains":[],"all_count":max(first["all_count"],second["all_count"])}

def main():
    global HALT
    if not SOURCE.is_file():
        raise SystemExit("MISSING_110_AREA_GEOCODE_SOURCE")
    source=json.loads(SOURCE.read_text(encoding="utf-8"))
    areas=source.get("rows",[])
    assert len(areas)==110 and len({x.get("area") for x in areas})==110
    assert all(x.get("center_gcj02") for x in areas)
    stations=station_dictionary()
    output=[]
    for area in areas:
        row={
          "area":area["area"],"reference_anchor":area.get("geocode_address",""),
          "reference_point_gcj02":area["center_gcj02"],
          "search_radius_m":50000,"amap_poi_total_count":"",
          "amap_poi_returned_count":0,"unique_station_candidates_checked":0,
          "nearest_confirmed_gdc_station":"","station_telecode":"",
          "station_poi_typecode":"","station_poi_type":"",
          "station_straight_distance_m":"",
          "driving_distance_m":"","driving_duration_s":"",
          "gdc_service_dates":"","gdc_train_examples":"",
          "status":"NOT_ATTEMPTED",
          "zero_semantics":"UNKNOWN_UNLESS_COMPLETE_CANDIDATE_SET_AND_NO_GDC",
          "source":"AMap v5 railway POI + official 12306 station dictionary + official 12306 station board + AMap driving"
        }
        output.append(row)
        if HALT:
            row["status"]="HALTED_"+HALT
            continue
        poi,err=amap("/v5/place/around",{
            "location":area["center_gcj02"],"radius":"50000",
            "types":"150200","sortrule":"distance",
            "page_size":"25","page_num":"1"
        })
        if err:
            row["status"]="AMAP_POI_ERROR_"+err
            continue
        pois=poi.get("pois") or []
        if not isinstance(pois,list):
            row["status"]="AMAP_POI_BAD_LIST"
            continue
        try: total=int(poi.get("count") or len(pois))
        except (ValueError,TypeError): total=len(pois)
        row["amap_poi_total_count"]=total
        row["amap_poi_returned_count"]=len(pois)
        candidates=[]
        seen=set()
        for p in pois:
            if not isinstance(p,dict): continue
            name=str(p.get("name") or "")
            nkey=normalize_station_name(name)
            match=stations.get(nkey)
            if not match: continue
            code=match["telecode"]
            if code in seen: continue
            seen.add(code)
            try: dist=float(p.get("distance") or 1e18)
            except (ValueError,TypeError): dist=1e18
            candidates.append((dist,p,match))
        candidates.sort(key=lambda z:z[0])
        row["unique_station_candidates_checked"]=0
        if not pois:
            row["status"]="NO_RAILWAY_POI_WITHIN_50KM"
            row["zero_semantics"]="NO_MAP_POI_FOUND_NOT_PROVEN_ZERO"
            continue
        if not candidates:
            row["status"]="NO_12306_STATION_CODE_MATCH"
            row["zero_semantics"]="UNKNOWN"
            continue
        best_unknown=None
        confirmed=None
        for dist,p,match in candidates:
            if HALT: break
            row["unique_station_candidates_checked"]+=1
            check=verify_station(match["telecode"])
            if check["state"]=="CONFIRMED_GDC":
                confirmed=(dist,p,match,check)
                break
            if check["state"] not in ("NO_GDC_ON_SAMPLE_DATES",):
                best_unknown=(dist,p,match,check)
                # Keep looking for a different station with verified service.
        if confirmed:
            dist,p,match,check=confirmed
            row.update({
              "nearest_confirmed_gdc_station":match["name"],
              "station_telecode":match["telecode"],
              "station_poi_typecode":str(p.get("typecode") or ""),
              "station_poi_type":str(p.get("type") or "")[:150],
              "station_straight_distance_m":int(dist) if dist<1e17 else "",
              "gdc_service_dates":";".join(check["dates"]),
              "gdc_train_examples":";".join(x["train"] for x in check["trains"]),
              "status":"GDC_CONFIRMED_ROUTE_PENDING"
            })
            route,err=amap("/v5/direction/driving",{
              "origin":area["center_gcj02"],
              "destination":str(p.get("location") or ""),
              "destination_id":str(p.get("id") or ""),
              "strategy":"32","show_fields":"cost"
            })
            if err:
                row["status"]="GDC_CONFIRMED_ROUTE_ERROR_"+err
            else:
                paths=(route.get("route") or {}).get("paths") or []
                if not paths:
                    row["status"]="GDC_CONFIRMED_NO_ROUTE"
                else:
                    best=paths[0];cost=best.get("cost") or {}
                    try: row["driving_distance_m"]=int(float(best.get("distance")))
                    except (ValueError,TypeError): pass
                    try: row["driving_duration_s"]=int(float(cost.get("duration")))
                    except (ValueError,TypeError): pass
                    row["status"]="GDC_CONFIRMED_ROUTE_OK" if row["driving_duration_s"]!="" else "GDC_CONFIRMED_ROUTE_DURATION_MISSING"
        elif best_unknown:
            dist,p,match,check=best_unknown
            row.update({"nearest_unverified_station_candidate":match["name"],
                        "station_telecode":match["telecode"],
                        "station_poi_typecode":str(p.get("typecode") or ""),
                        "station_straight_distance_m":int(dist) if dist<1e17 else "",
                        "status":"12306_VERIFICATION_INCOMPLETE",
                        "zero_semantics":"UNKNOWN"})
        elif total<=len(pois) and len(pois)<25:
            row["status"]="NO_GDC_IN_COMPLETE_RETURNED_POI_SET_ON_TWO_DATES"
            row["zero_semantics"]="PROVISIONAL_ZERO_WITHIN_50KM_MAP_POI_COVERAGE"
        else:
            row["status"]="NO_GDC_IN_FIRST_25_POIS_CANDIDATE_SET_CAPPED"
            row["zero_semantics"]="UNKNOWN_POI_RESULT_CAPPED"
    OUT.mkdir(parents=True,exist_ok=True)
    counts=Counter(x["status"] for x in output)
    doc={
      "schema":"anju_110_hsr_official_12306_verified_v2",
      "generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "metric":"Nearest AMap railway POI within 50km whose station exists in official 12306 station dictionary and has at least one G/D/C train on either sampled service date; driving distance and duration from county-government reference point",
      "areas_total":110,"service_dates":list(SERVICE_DATES),
      "amap_requests":AMAP_REQUESTS,"official_12306_station_board_requests":RAIL_REQUESTS,
      "limits":{"amap_max":AMAP_LIMIT,"rail_max":RAIL_LIMIT},
      "halt_reason":HALT,
      "limitations":[
        "12306 station board is checked on one weekday and a second weekend date only when no G/D/C service is found on the weekday",
        "G/D/C service on sampled dates confirms passenger service; no G/D/C on two sampled dates is not a proof of permanent absence",
        "Amap returns at most 25 POIs per area; capped results with no confirmed G/D/C remain unknown",
        "No AMap POI within 50km is not proof of no high-speed rail station beyond 50km",
        "County-government reference point is a proxy for the target residential area"
      ],
      "sources":[
        "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js",
        "https://mobile.12306.cn/wxxcx/wechat/bigScreen/queryTrainByStation",
        "https://lbs.amap.com/api/webservice/guide/api-advanced/newpoisearch"
      ],
      "rows":output
    }
    (OUT/"latest.json").write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    fields=sorted(set().union(*(x.keys() for x in output)))
    with (OUT/"latest.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(output)
    print(json.dumps({"areas":110,"statuses":dict(counts),
      "gdc_confirmed":sum(x["status"].startswith("GDC_CONFIRMED_ROUTE_OK") for x in output),
      "provisional_zero":sum(x["status"]=="NO_GDC_IN_COMPLETE_RETURNED_POI_SET_ON_TWO_DATES" for x in output),
      "unknown":sum(x["zero_semantics"]=="UNKNOWN" or x["zero_semantics"].startswith("NO_MAP") for x in output),
      "amap_requests":AMAP_REQUESTS,"12306_requests":RAIL_REQUESTS,"halt":HALT},
      ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
