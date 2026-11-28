#!/usr/bin/env python3
"""Anju phase-2 daily procurement POI proxy: separate 110-area category queries.

Runs one independent Gaode v5 around-POI request per area per category:
060200 convenience stores, 060400 supermarkets, 060700 general markets.
Reuses already validated government-reference coordinates. One first page
(25 max) per category; only aggregate counts are persisted, never POI names/IDs.
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

REGISTRY = Path("anju/inputs/areas_110.json")
REFERENCE = Path("anju/results/pharmacy_1km/latest.json")
ROOT = Path("anju/results/daily_essentials_by_category_1km")
ENDPOINT = "https://restapi.amap.com/v5/place/around"
PROVIDER = "Gaode Web Service v5 POI Around"
CATEGORIES = {
    "convenience": {"typecode": "060200", "label": "便民商店/便利店"},
    "supermarket": {"typecode": "060400", "label": "超市"},
    "market": {"typecode": "060700", "label": "综合市场"},
}
RADIUS_M = 1000
PAGE_SIZE = 25
MAX_REQUESTS = int(os.environ.get("ANJU_MAX_REQUESTS", "350"))
LIMIT = int(os.environ.get("ANJU_MAX_AREAS", "110"))
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
            url, headers={"User-Agent": "Anju-Daily-Procurement-ByCategory/1.0"}
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
    registry_bytes = REGISTRY.read_bytes()
    registry = json.loads(registry_bytes)
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    areas = registry.get("areas") or []
    reference_rows = reference.get("rows") or []
    assert len(areas) == 110, f"Expected 110 registry areas, got {len(areas)}"
    assert len({a["name"] for a in areas}) == 110, "Duplicate area names"
    assert len(reference_rows) == 110, f"Expected 110 reference rows, got {len(reference_rows)}"
    ref_by_name = {r.get("area"): r for r in reference_rows}
    assert len(ref_by_name) == 110, "Duplicate/missing reference rows"
    assert set(ref_by_name) == {a["name"] for a in areas}, "Registry/reference area mismatch"
    assert 1 <= LIMIT <= 110
    assert 330 <= MAX_REQUESTS <= 400, "Request cap must cover 3 independent queries x 110 areas"

    rows = []
    for area in areas:
        name = area["name"]
        ref = ref_by_name[name]
        row = {
            "id": area["id"],
            "area": name,
            "province": name.split("·", 1)[0],
            "district": name.split("·", 1)[1],
            "reference_anchor": ref.get("anchor", ""),
            "reference_address": ref.get("geocode_address", ""),
            "reference_adcode": ref.get("adcode", ""),
            "center_gcj02": ref.get("center_gcj02", ""),
            "radius_m": RADIUS_M,
            "reference_coordinate_source": "已验收药房1km批次地理编码结果复用；本轮未重复地理编码",
        }
        rows.append(row)

        if area["id"] > LIMIT:
            for key in CATEGORIES:
                row[key + "_count"] = ""
                row[key + "_api_count"] = ""
                row[key + "_status"] = "OUTSIDE_LIMIT"
                row[key + "_typecode"] = CATEGORIES[key]["typecode"]
            continue

        valid_ref = bool(ref.get("geocode_matched") and ref.get("center_gcj02"))
        try:
            lng, lat = (float(v) for v in str(ref.get("center_gcj02", "")).split(","))
            valid_ref = valid_ref and (73 < lng < 135 and 18 < lat < 55)
        except (ValueError, TypeError):
            valid_ref = False

        for key, category in CATEGORIES.items():
            row[key + "_typecode"] = category["typecode"]
            row[key + "_label"] = category["label"]
            row[key + "_count"] = ""
            row[key + "_api_count"] = ""
            row[key + "_status"] = "NOT_ATTEMPTED"

            if halt_reason:
                row[key + "_status"] = halt_reason
                continue
            if not valid_ref:
                row[key + "_status"] = "REFERENCE_CENTER_UNAVAILABLE"
                continue

            result, error = call({
                "location": ref["center_gcj02"],
                "radius": str(RADIUS_M),
                "types": category["typecode"],
                "sortrule": "distance",
                "page_size": str(PAGE_SIZE),
                "page_num": "1",
                "output": "json"
            })
            if error:
                row[key + "_status"] = error
                continue

            pois = result.get("pois")
            if not isinstance(pois, list):
                row[key + "_status"] = "UNEXPECTED_RESPONSE"
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
        key: dict(Counter(r.get(key + "_status", "") for r in rows))
        for key in CATEGORIES
    }
    payload = {
        "schema": "anju_daily_essentials_by_category_1km_proxy_v1",
        "timestamp_utc": stamp,
        "target": "110 phase-2 areas",
        "registry_sha256": hashlib.sha256(registry_bytes).hexdigest(),
        "reference_source": "anju/results/pharmacy_1km/latest.json",
        "metric": "Separate POI first-page counts for convenience stores, supermarkets and general markets within 1km of each county/district government reference point",
        "provider": PROVIDER,
        "endpoint": ENDPOINT,
        "categories": CATEGORIES,
        "radius_m": RADIUS_M,
        "page_size": PAGE_SIZE,
        "max_requests": MAX_REQUESTS,
        "actual_requests": request_count,
        "area_limit": LIMIT,
        "halt_reason": halt_reason,
        "status_counts_by_category": status_counts,
        "limitations": [
            "Three categories are queried separately; unlike the previous combined query, one category cannot crowd out another on the same first page",
            "Each category is still limited to the first 25 results in this batch; 25 means at least 25, not an exact total",
            "The API documentation states a maximum of 200 records across pagination for one query; this batch deliberately does not paginate",
            "County/district government reference point is a proxy, not a confirmed representative residential location",
            "Gaode POI search hits are not a certified complete merchant inventory",
            "No result is unknown/not detected, not a confirmed zero",
            "No individual POI names or IDs are persisted",
            "No A-D score or V12.2 formal value is changed"
        ],
        "rows": rows
    }
    (ROOT / "latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    fields = list(rows[0].keys())
    with (ROOT / "latest.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({
        "timestamp_utc": stamp,
        "areas_in_registry": len(rows),
        "requests": request_count,
        "status_counts_by_category": status_counts,
        "halt_reason": halt_reason,
        "formal_scores_changed": 0
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
