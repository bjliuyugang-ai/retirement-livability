#!/usr/bin/env python3
"""Area-level public convenience service POI proxy: bank, courier, housekeeping.

Queries 110 retained areas at the same 1km government-reference point:
- Bank: typecode 160100
- Courier: keyword '快递' within life-service parent type 070000
- Housekeeping: keyword '家政' within life-service parent type 070000
Counts only are persisted; no POI names/IDs.
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
from collections import Counter

REFERENCE = Path("anju/results/pharmacy_1km/latest.json")
ROOT = Path("anju/results/public_services_1km")
ENDPOINT = "https://restapi.amap.com/v5/place/around"
PROVIDER = "Gaode Web Service v5 POI Around"
CATEGORIES = {
    "bank": {"label": "银行", "typecode": "160100", "keywords": None},
    "courier": {"label": "快递", "typecode": "070000", "keywords": "快递"},
    "housekeeping": {"label": "家政", "typecode": "070000", "keywords": "家政"},
}
RADIUS_M = 1000
PAGE_SIZE = 25
MAX_REQUESTS = int(os.environ.get("ANJU_MAX_REQUESTS", "350"))
KEY = os.environ.get("AMAP_WEB_KEY", "")
HARD_FAIL_CODES = {
    "10001", "10002", "10003", "10004", "10005", "10006", "10007",
    "10008", "10009", "10010", "10011", "10012", "10013", "10014",
    "10015", "10016", "10017", "10019", "10020", "10021"
}
request_count = 0
halt_reason = ""

def call(params):
    global request_count, halt_reason
    if request_count >= MAX_REQUESTS:
        halt_reason = "REQUEST_CAP_REACHED"
        return None, halt_reason
    if not KEY:
        halt_reason = "MISSING_AMAP_SECRET"
        return None, halt_reason
    query = dict(params)
    query["key"] = KEY
    request_count += 1
    url = ENDPOINT + "?" + urllib.parse.urlencode(query)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Anju-Public-Services-110/1.0"})
        with urllib.request.urlopen(req, timeout=18) as response:
            raw = response.read(300000)
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None, "BAD_RESPONSE"
        if str(data.get("status")) != "1":
            code = str(data.get("infocode", "UNKNOWN"))[:20]
            if code in HARD_FAIL_CODES:
                halt_reason = "PROVIDER_STOP_" + code
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

def main():
    global halt_reason
    raw = REFERENCE.read_bytes()
    reference = json.loads(raw)
    rows = reference.get("rows") or []
    assert len(rows) == 110, f"Expected 110 reference rows, got {len(rows)}"
    assert 330 <= MAX_REQUESTS <= 400, "Request cap must cover 3 categories x 110 areas"

    out_rows = []
    for ref in rows:
        row = {
            "id": ref["id"],
            "area": ref["area"],
            "province": ref["province"],
            "district": ref["district"],
            "reference_address": ref.get("geocode_address", ""),
            "center_gcj02": ref.get("center_gcj02", ""),
            "radius_m": RADIUS_M,
            "reference_coordinate_source": "Reuse validated pharmacy geocode; no repeated geocoding"
        }
        out_rows.append(row)
        valid = bool(ref.get("geocode_matched") and ref.get("center_gcj02"))
        try:
            lng, lat = (float(v) for v in str(ref.get("center_gcj02", "")).split(","))
            valid = valid and (73 < lng < 135 and 18 < lat < 55)
        except (ValueError, TypeError):
            valid = False

        for key, category in CATEGORIES.items():
            row[key + "_label"] = category["label"]
            row[key + "_typecode"] = category["typecode"]
            row[key + "_keywords"] = category["keywords"] or ""
            row[key + "_count"] = ""
            row[key + "_api_count"] = ""
            row[key + "_status"] = "NOT_ATTEMPTED"

            if halt_reason:
                row[key + "_status"] = halt_reason
                continue
            if not valid:
                row[key + "_status"] = "REFERENCE_CENTER_UNAVAILABLE"
                continue
            params = {
                "location": ref["center_gcj02"],
                "radius": str(RADIUS_M),
                "types": category["typecode"],
                "sortrule": "distance",
                "page_size": str(PAGE_SIZE),
                "page_num": "1",
                "output": "json"
            }
            if category["keywords"]:
                params["keywords"] = category["keywords"]
            result, error = call(params)
            if error:
                row[key + "_status"] = error
                continue
            pois = result.get("pois")
            if not isinstance(pois, list):
                row[key + "_status"] = "UNEXPECTED_RESPONSE"
                continue
            ids = {str(p.get("id")) for p in pois if isinstance(p, dict) and p.get("id")}
            n = len(ids)
            try:
                api_count = int(result.get("count", n))
            except (TypeError, ValueError):
                api_count = n
            row[key + "_count"] = n
            row[key + "_api_count"] = api_count
            if n >= PAGE_SIZE or api_count >= PAGE_SIZE:
                row[key + "_status"] = "AT_LEAST_25"
            elif n == 0:
                row[key + "_status"] = "NO_POI_RETURNED_UNKNOWN"
            else:
                row[key + "_status"] = "RETURNED_1_TO_24"

    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    ROOT.mkdir(parents=True, exist_ok=True)
    status_counts = {
        key: dict(Counter(r.get(key + "_status", "") for r in out_rows))
        for key in CATEGORIES
    }
    payload = {
        "schema": "anju_public_services_1km_proxy_v1",
        "timestamp_utc": stamp,
        "target": "110 retained phase-2 areas",
        "reference_source": "anju/results/pharmacy_1km/latest.json",
        "reference_sha256": hashlib.sha256(raw).hexdigest(),
        "provider": PROVIDER,
        "endpoint": ENDPOINT,
        "categories": CATEGORIES,
        "radius_m": RADIUS_M,
        "page_size": PAGE_SIZE,
        "actual_requests": request_count,
        "max_requests": MAX_REQUESTS,
        "halt_reason": halt_reason,
        "status_counts_by_category": status_counts,
        "limitations": [
            "Bank uses typecode 160100; courier and housekeeping use keyword filtering under 070000 life-service parent",
            "Keyword filtering may not include all businesses or current operating status",
            "25 returned means at least 25; not exact total",
            "No result is unknown/not detected, not a confirmed zero",
            "Government point 1km radius is an area-level proxy, not a verified residential point",
            "Gaode POI is a proxy and not Dianping data or a certified full inventory",
            "No POI names or IDs are persisted",
            "No formal A-D rating or V12.2 score is changed"
        ],
        "rows": out_rows
    }
    (ROOT / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = list(dict.fromkeys(k for row in out_rows for k in row.keys()))
    with (ROOT / "latest.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)
    print(json.dumps({
        "timestamp_utc": stamp,
        "areas": len(out_rows),
        "requests": request_count,
        "status_counts_by_category": status_counts,
        "halt_reason": halt_reason
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
