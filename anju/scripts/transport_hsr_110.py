#!/usr/bin/env python3
"""Anju 110-area nearest high-speed-rail POI + driving-time batch.
Uses already geocoded county-government reference points from pharmacy 1km evidence.
One nearest-station POI query per area, then one route request if a candidate exists.
A POI keyword match is a map candidate, not proof of scheduled train service.
"""
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

SRC=pathlib.Path("anju/results/pharmacy_1km/latest.json")
ROOT=pathlib.Path("anju/results/transport_hsr")
KEY=os.environ.get("AMAP_WEB_KEY","")
RADIUS=50000
MAX_REQUESTS=220
requests=0
halt=""
BASE="https://restapi.amap.com"

def call(path,params):
    global requests,halt
    if requests>=MAX_REQUESTS:
        halt="REQUEST_CAP_REACHED"
        return None,"REQUEST_CAP_REACHED"
    if not KEY:
        halt="MISSING_AMAP_WEB_KEY"
        return None,halt
    q=dict(params);q["key"]=KEY
    url=BASE+path+"?"+urllib.parse.urlencode(q)
    requests+=1
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Anju-Transport-Access-Study/1.0"})
        with urllib.request.urlopen(req,timeout=18) as resp:
            raw=resp.read(250000)
        d=json.loads(raw)
        if not isinstance(d,dict): return None,"BAD_JSON_OBJECT"
        if str(d.get("status"))!="1":
            code=str(d.get("infocode","UNKNOWN"))[:20]
            if code.startswith("100"):
                halt="PROVIDER_STOP_"+code
            return None,"PROVIDER_"+code
        return d,None
    except urllib.error.HTTPError as e:
        return None,"HTTP_"+str(e.code)
    except (urllib.error.URLError,TimeoutError):
        return None,"NETWORK_ERROR"
    except (json.JSONDecodeError,UnicodeDecodeError,ValueError,TypeError):
        return None,"JSON_ERROR"
    finally:
        time.sleep(1.05)

def main():
    global halt
    if not SRC.is_file():
        raise SystemExit("MISSING_110_AREA_GEOCODE_SOURCE")
    source=json.loads(SRC.read_text(encoding="utf-8"))
    rows=source.get("rows",[])
    assert len(rows)==110 and len({x.get("area") for x in rows})==110
    assert all(x.get("center_gcj02") and x.get("geocode_matched") for x in rows), "110 matched reference coordinates required"
    output=[]
    for src in rows:
        area=src["area"]
        origin=src["center_gcj02"]
        r={
          "area":area,"reference_anchor":src.get("geocode_address",""),
          "reference_point_gcj02":origin,
          "search_radius_m":RADIUS,
          "query":"高铁站","poi_typecode":"150200",
          "nearest_hsr_candidate_name":"","candidate_address":"",
          "candidate_location_gcj02":"","candidate_straight_distance_m":"",
          "candidate_type":"","poi_count_returned":"",
          "driving_distance_m":"","driving_duration_s":"",
          "status":"NOT_ATTEMPTED",
          "hsr_service_verification":"MAP_POI_KEYWORD_CANDIDATE_ONLY",
          "source":"AMap Web Service v5 place/around + v5 direction/driving"
        }
        output.append(r)
        if halt:
            r["status"]=halt
            continue
        poi,err=call("/v5/place/around",{
          "keywords":"高铁站","types":"150200","location":origin,
          "radius":str(RADIUS),"sortrule":"distance",
          "page_size":"25","page_num":"1","output":"json"
        })
        if err:
            r["status"]="POI_"+err
            continue
        pois=poi.get("pois")
        if not isinstance(pois,list):
            r["status"]="POI_BAD_RESULT_LIST"
            continue
        r["poi_count_returned"]=len(pois)
        candidates=[]
        for p in pois:
            if not isinstance(p,dict): continue
            loc=str(p.get("location") or "")
            try:
                lon,lat=(float(v) for v in loc.split(","))
                if not (73<lon<135 and 18<lat<55): continue
            except (ValueError,TypeError):
                continue
            tcode=str(p.get("typecode") or "")
            ptype=str(p.get("type") or "")
            if not (tcode.startswith("1502") or "火车站" in ptype):
                continue
            try: distance=float(p.get("distance") or 1e18)
            except (ValueError,TypeError): distance=1e18
            candidates.append((distance,p))
        if not candidates:
            r["status"]="NO_HSR_POI_MATCH_WITHIN_50KM"
            r["hsr_service_verification"]="NO_MAP_POI_MATCH_WITHIN_50KM_NOT_PROOF_OF_ABSENCE"
            continue
        candidates.sort(key=lambda x:x[0])
        straight,p=candidates[0]
        dest=str(p.get("location"))
        r.update({
          "nearest_hsr_candidate_name":str(p.get("name") or "")[:120],
          "candidate_address":str(p.get("address") or "")[:180],
          "candidate_location_gcj02":dest,
          "candidate_straight_distance_m":int(straight) if straight<1e17 else "",
          "candidate_type":str(p.get("type") or "")[:120],
          "candidate_poi_typecode":str(p.get("typecode") or ""),
          "candidate_poi_id":str(p.get("id") or "")
        })
        if halt: 
            r["status"]="ROUTE_"+halt
            continue
        route,err=call("/v5/direction/driving",{
          "origin":origin,"destination":dest,
          "destination_id":str(p.get("id") or ""),
          "strategy":"32","show_fields":"cost","output":"json"
        })
        if err:
            r["status"]="ROUTE_"+err
            continue
        paths=(route.get("route") or {}).get("paths") or []
        if not paths:
            r["status"]="ROUTE_NO_PATH"
            continue
        best=paths[0]
        cost=best.get("cost") or {}
        try: dist=int(float(best.get("distance")))
        except (ValueError,TypeError): dist=""
        try: duration=int(float(cost.get("duration")))
        except (ValueError,TypeError): duration=""
        r.update({"driving_distance_m":dist,"driving_duration_s":duration,
                  "status":"ROUTE_OK" if duration!="" else "ROUTE_OK_DURATION_MISSING"})
    ROOT.mkdir(parents=True,exist_ok=True)
    stamp=dt.datetime.now(dt.timezone.utc).isoformat()
    doc={
      "schema":"anju_110_nearest_hsr_poi_driving_v1",
      "generated_utc":stamp,
      "metric":"Nearest Gaode POI matching keyword 高铁站 and railway-station category 150200 within 50km; driving route time from county-government reference point",
      "areas_total":110,"reference":"same 110 county-government GCJ-02 points already used in pharmacy proxy",
      "radius_m":RADIUS,"max_requests":MAX_REQUESTS,"actual_requests":requests,
      "halt_reason":halt,
      "limitations":[
        "Amap POI keyword result is a candidate, not proof that scheduled high-speed trains currently stop there",
        "No match within 50km is not proof of no high-speed rail access beyond 50km",
        "County-government reference point is a proxy, not a surveyed residential-area centroid",
        "Driving duration is map-planned estimate and can vary by traffic and road changes"
      ],
      "source_registry_sha256":hashlib.sha256(SRC.read_bytes()).hexdigest(),
      "rows":output
    }
    (ROOT/"latest.json").write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    fields=sorted(set().union(*(x.keys() for x in output)))
    with (ROOT/"latest.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(output)
    counts=Counter(x["status"] for x in output)
    print(json.dumps({"generated_utc":stamp,"areas":110,"requests":requests,
      "statuses":dict(counts),"route_ok":counts.get("ROUTE_OK",0),
      "no_poi_within_50km":counts.get("NO_HSR_POI_MATCH_WITHIN_50KM",0),
      "halt_reason":halt,"formal_scores_changed":0},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
