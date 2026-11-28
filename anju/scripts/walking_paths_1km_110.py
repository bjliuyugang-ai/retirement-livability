#!/usr/bin/env python3
"""Anju phase-2 walking-path POI proxy for all 110 retained areas.

One keyword-only Amap POI 2.0 around query per area:
- keyword: 步道
- radius: 1km from the validated county/district-government reference point
- no POI type filter, to avoid excluding trails filed under different categories

Only aggregate counts and returned typecode distribution are persisted. No POI
names, IDs, addresses, or coordinates of individual facilities are stored.
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
ROOT = Path("anju/results/walking_paths_1km")
ENDPOINT = "https://restapi.amap.com/v5/place/around"
PROVIDER = "Gaode Web Service v5 POI Around"
KEYWORD = "步道"
RADIUS_M = 1000
PAGE_SIZE = 25
MAX_REQUESTS = int(os.environ.get("ANJU_MAX_REQUESTS", "130"))
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
    url = ENDPOINT + "?" + urllib.parse.urlencode(query)
    request_count += 1
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Anju-Walking-Paths-110/1.0"}
        )
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
    assert 110 <= MAX_REQUESTS <= 150, "Request cap must cover 110 areas"

    out_rows = []
    for ref in rows:
        row = {
            "id": ref["id"],
            "area": ref["area"],
            "province": ref.get("province", ref["area"].split("·", 1)[0]),
            "district": ref.get("district", ref["area"].split("·", 1)[1]),
            "reference_address": ref.get("geocode_address", ""),
            "center_gcj02": ref.get("center_gcj02", ""),
            "radius_m": RADIUS_M,
            "keyword": KEYWORD,
            "type_filter": "NONE_KEYWORD_ONLY",
            "reference_coordinate_source": "Reuse validated pharmacy geocode; no repeated geocoding",
            "walking_path_count": "",
            "walking_path_api_count": "",
            "returned_typecode_counts": "",
            "walking_path_status": "NOT_ATTEMPTED"
        }
        out_rows.append(row)
        valid = bool(ref.get("geocode_matched") and ref.get("center_gcj02"))
        try:
            lng, lat = (float(v) for v in str(ref.get("center_gcj02", "")).split(","))
            valid = valid and (73 < lng < 135 and 18 < lat < 55)
        except (ValueError, TypeError):
            valid = False

        if halt_reason:
            row["walking_path_status"] = halt_reason
            continue
        if not valid:
            row["walking_path_status"] = "REFERENCE_CENTER_UNAVAILABLE"
            continue

        result, error = call({
            "location": ref["center_gcj02"],
            "radius": str(RADIUS_M),
            "keywords": KEYWORD,
            "sortrule": "distance",
            "page_size": str(PAGE_SIZE),
            "page_num": "1",
            "output": "json"
        })
        if error:
            row["walking_path_status"] = error
            continue

        pois = result.get("pois")
        if not isinstance(pois, list):
            row["walking_path_status"] = "UNEXPECTED_RESPONSE"
            continue
        ids = {
            str(p.get("id")) for p in pois
            if isinstance(p, dict) and p.get("id")
        }
        n = len(ids)
        try:
            api_count = int(result.get("count", n))
        except (TypeError, ValueError):
            api_count = n
        type_counts = Counter(
            str(p.get("typecode", "UNKNOWN"))
            for p in pois if isinstance(p, dict)
        )
        row["walking_path_count"] = n
        row["walking_path_api_count"] = api_count
        row["returned_typecode_counts"] = json.dumps(dict(type_counts), ensure_ascii=False, sort_keys=True)

        if n >= PAGE_SIZE or api_count >= PAGE_SIZE:
            row["walking_path_status"] = "AT_LEAST_25"
        elif n == 0:
            row["walking_path_status"] = "NO_POI_RETURNED_UNKNOWN"
        else:
            row["walking_path_status"] = "RETURNED_1_TO_24"

    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    ROOT.mkdir(parents=True, exist_ok=True)
    status_counts = dict(Counter(r.get("walking_path_status", "") for r in out_rows))
    payload = {
        "schema": "anju_walking_paths_1km_keyword_proxy_v1",
        "timestamp_utc": stamp,
        "target": "110 retained phase-2 areas",
        "reference_source": "anju/results/pharmacy_1km/latest.json",
        "reference_sha256": hashlib.sha256(raw).hexdigest(),
        "provider": PROVIDER,
        "endpoint": ENDPOINT,
        "keyword": KEYWORD,
        "type_filter": None,
        "radius_m": RADIUS_M,
        "page_size": PAGE_SIZE,
        "actual_requests": request_count,
        "max_requests": MAX_REQUESTS,
        "halt_reason": halt_reason,
        "status_counts": status_counts,
        "limitations": [
            "Keyword-only search for 步道; one keyword per Amap POI 2.0 request",
            "No type filter, to avoid excluding trail POIs filed under other categories",
            "Keyword matching can include false positives and miss POIs named 绿道/健身路线 without 步道",
            "First page only; 25 means at least 25, not exact total",
            "Government reference point 1km is a proxy, not a confirmed representative residential point",
            "POI search results are not a certified complete walking-trail inventory",
            "No result is unknown/not detected, not a confirmed zero",
            "No individual POI names, IDs, addresses, or facility coordinates are persisted",
            "Returned typecode distribution is retained for category-quality audit",
            "Walking-route continuity, surface, accessibility, slope, and residential access are not measured",
            "No A-D rating or V12.2 formal score is changed"
        ],
        "rows": out_rows
    }
    (ROOT / "latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    fields = list(dict.fromkeys(k for row in out_rows for k in row.keys()))
    with (ROOT / "latest.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)
    print(json.dumps({
        "timestamp_utc": stamp,
        "areas": len(out_rows),
        "requests": request_count,
        "status_counts": status_counts,
        "halt_reason": halt_reason,
        "formal_scores_changed": 0
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
