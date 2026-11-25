#!/usr/bin/env python3
"""Anju phase-2 one-parameter, 110-area pharmacy access proxy.
One geocode + one around-POI query per area; aggregate counts only.
No individual POI names/IDs are saved. NOT an A-D rating or full inventory.
"""
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

REGISTRY = Path("anju/inputs/areas_110.json")
ROOT = Path("anju/results/pharmacy_2km")
PROVIDER = "Gaode Web Service v3 Geocode + v5 POI Around"
TYPECODE = "090601"
RADIUS_M = 2000
MAX_POIS = 25
MAX_REQUESTS = int(os.environ.get("ANJU_MAX_REQUESTS", "230"))
LIMIT = int(os.environ.get("ANJU_MAX_AREAS", "110"))
KEY = os.environ.get("AMAP_WEB_KEY", "")
PROVINCE = {"云南": "云南省", "四川": "四川省", "广东": "广东省",
            "浙江": "浙江省", "海南": "海南省", "福建": "福建省"}
HARD_FAIL_CODES = {"10001", "10002", "10003", "10004", "10005",
                   "10006", "10007", "10008", "10009", "10010",
                   "10011", "10012", "10013", "10014", "10015",
                   "10016", "10017", "10019", "10020", "10021"}
counter = 0
halt = ""

def call(endpoint, params):
    global counter, halt
    if counter >= MAX_REQUESTS:
        halt = "REQUEST_CAP_REACHED"
        return None, "REQUEST_CAP_REACHED"
    if not KEY:
        halt = "MISSING_AMAP_SECRET"
        return None, halt
    values = dict(params)
    values["key"] = KEY
    address = endpoint + "?" + urllib.parse.urlencode(values)
    counter += 1
    try:
        req = urllib.request.Request(address, headers={"User-Agent": "Anju-Aggregate-POI-Study/1.0"})
        with urllib.request.urlopen(req, timeout=16) as response:
            raw = response.read(200000)
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None, "BAD_RESPONSE"
        if str(data.get("status")) != "1":
            code = str(data.get("infocode", "UNKNOWN"))[:20]
            if code in HARD_FAIL_CODES:
                halt = "PROVIDER_STOP_" + code
            return None, "PROVIDER_" + code
        return data, None
    except urllib.error.HTTPError as exc:
        return None, "HTTP_" + str(exc.code)
    except (urllib.error.URLError, TimeoutError):
        return None, "NETWORK_ERROR"
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
        return None, "JSON_ERROR"
    finally:
        time.sleep(0.22)

def run():
    global halt
    source = json.loads(REGISTRY.read_text(encoding="utf-8"))
    areas = source["areas"]
    assert len(areas) == 110
    assert len(set(a["name"] for a in areas)) == 110
    assert 1 <= LIMIT <= 110
    assert 2 <= MAX_REQUESTS <= 260
    rows = []
    for a in areas:
        name = a["name"]
        province, district = name.split("·", 1)
        row = {
            "id": a["id"], "area": name, "province": province,
            "district": district, "anchor": province + district + "人民政府",
            "geocode_matched": "", "geocode_level": "", "geocode_address": "",
            "adcode": "", "center_gcj02": "", "radius_m": RADIUS_M,
            "poi_typecode": TYPECODE, "poi_returned_count": "",
            "count_interpretation": "", "status": "NOT_ATTEMPTED",
            "provider_code": "", "source": PROVIDER
        }
        rows.append(row)
        if a["id"] > LIMIT:
            row["status"] = "OUTSIDE_PILOT"
            continue
        if halt:
            row["status"] = halt
            continue
        geo, err = call(
            "https://restapi.amap.com/v3/geocode/geo",
            {"address": PROVINCE.get(province, province) + district + "人民政府",
             "output": "json"})
        if err:
            row["status"] = "GEOCODE_" + err
            continue
        points = geo.get("geocodes") or []
        if not points:
            row["status"] = "GEOCODE_NO_RESULT"
            continue
        first = points[0]
        if not isinstance(first, dict):
            row["status"] = "GEOCODE_INVALID"
            continue
        district_reply = first.get("district", "")
        if isinstance(district_reply, list):
            district_reply = " ".join(map(str, district_reply))
        address = str(first.get("formatted_address") or "")
        loc = str(first.get("location") or "")
        row.update({"geocode_level": str(first.get("level", "")),
                    "geocode_address": address[:150],
                    "adcode": str(first.get("adcode", "")),
                    "center_gcj02": loc})
        try:
            lng, lat = (float(v) for v in loc.split(","))
            valid_xy = 73 < lng < 135 and 18 < lat < 55
        except (ValueError, TypeError):
            valid_xy = False
        # Reject an unmatched county, not just a province-level geocode.
        matched = district in (district_reply + " " + address)
        row["geocode_matched"] = bool(matched and valid_xy)
        if not (matched and valid_xy):
            row["status"] = "REVIEW_CENTER_MISMATCH"
            continue
        poi, err = call(
            "https://restapi.amap.com/v5/place/around",
            {"location": loc, "radius": str(RADIUS_M), "types": TYPECODE,
             "sortrule": "distance", "page_size": str(MAX_POIS),
             "page_num": "1", "output": "json"})
        if err:
            row["status"] = "POI_" + err
            continue
        places = poi.get("pois")
        if not isinstance(places, list):
            row["status"] = "POI_UNEXPECTED"
            continue
        # Aggregate only; individual POIs aren't copied to durable storage.
        n = len({str(p.get("id")) for p in places
                 if isinstance(p, dict) and p.get("id")})
        row["poi_returned_count"] = n
        if len(places) == MAX_POIS:
            row["count_interpretation"] = "AT_LEAST_25_NOT_EXACT"
            row["status"] = "CAPPED_LOWER_BOUND"
        else:
            row["count_interpretation"] = "API_PAGE_COUNT_NOT_FULL_INVENTORY"
            row["status"] = "FIRST_PAGE_UNCAPPED"
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "anju_pharmacy_2km_proxy_v1",
        "timestamp_utc": stamp,
        "target": "110 phase-2 areas (one parameter only)",
        "registry_sha256": hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
        "metric": "Pharmacy POIs within 2km of geocoded county government reference point",
        "source": PROVIDER,
        "limitations": [
            "Government-location proxy is not confirmed representative housing location",
            "POI results are search hits, not a certified complete pharmacy inventory",
            "First page yields a lower bound when 25 results are returned",
            "No A-D scores; no formal V12.2 value overwritten"
        ],
        "radius_m": RADIUS_M, "typecode": TYPECODE,
        "max_requests": MAX_REQUESTS, "actual_requests": counter,
        "first_n_areas_attempted": LIMIT, "halt_reason": halt,
        "rows": rows
    }
    (ROOT / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
    fields = list(rows[0])
    with (ROOT / "latest.csv").open("w", newline="", encoding="utf-8-sig") as file:
        w = csv.DictWriter(file, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    tally = Counter(r["status"] for r in rows)
    print(json.dumps({"timestamp_utc": stamp, "areas_in_registry": len(rows),
                      "area_limit": LIMIT, "requests": counter,
                      "statuses": dict(tally),
                      "valid_uncapped": tally.get("FIRST_PAGE_UNCAPPED", 0),
                      "valid_lower_bound": tally.get("CAPPED_LOWER_BOUND", 0),
                      "halt_reason": halt, "formal_scores_changed": 0},
                     ensure_ascii=False, indent=2))

if __name__ == "__main__":
    run()
