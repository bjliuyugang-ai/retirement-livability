#!/usr/bin/env python3
"""Anju phase-2 daily-procurement POI proxy for all 110 retained areas.

Narrowed from the broad shopping-service parent category after 108/110 areas
hit the first-page cap. Queries convenience stores, supermarkets and general
markets (typecodes 060200|060400|060700) within 1km of the already verified
county-government reference point. Stores aggregate counts only.
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
ROOT = Path("anju/results/daily_essentials_1km")
PROVIDER = "Gaode Web Service v5 POI Around"
ENDPOINT = "https://restapi.amap.com/v5/place/around"
TYPECODES = "060200|060400|060700"
TYPE_NAME = "日常采购设施（便利店、超市、综合市场）"
RADIUS_M = 1000
PAGE_SIZE = 25
MAX_REQUESTS = int(os.environ.get("ANJU_MAX_REQUESTS", "130"))
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
            url, headers={"User-Agent": "Anju-Daily-Procurement-POI/1.0"}
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
    assert len(reference_rows) == 110, f"Expected 110 verified reference rows, got {len(reference_rows)}"
    ref_by_name = {r.get("area"): r for r in reference_rows}
    assert len(ref_by_name) == 110, "Reference rows contain duplicate/missing area names"
    assert set(ref_by_name) == {a["name"] for a in areas}, "Registry/reference area set mismatch"
    assert 1 <= LIMIT <= 110
    assert 1 <= MAX_REQUESTS <= 150

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
            "poi_typecodes": TYPECODES,
            "poi_type_name": TYPE_NAME,
            "page_size": PAGE_SIZE,
            "unique_poi_returned": "",
            "api_count": "",
            "convenience_store_hits_first_page": "",
            "supermarket_hits_first_page": "",
            "market_hits_first_page": "",
            "count_interpretation": "",
            "status": "NOT_ATTEMPTED",
            "provider_code": "",
            "source": PROVIDER,
            "reference_coordinate_source": "已验收药房1km批次地理编码结果复用；本轮未重复地理编码"
        }
        rows.append(row)
        if area["id"] > LIMIT:
            row["status"] = "OUTSIDE_LIMIT"
            continue
        if halt_reason:
            row["status"] = halt_reason
            continue
        if not ref.get("geocode_matched") or not ref.get("center_gcj02"):
            row["status"] = "REFERENCE_CENTER_UNAVAILABLE"
            continue
        try:
            lng, lat = (float(v) for v in str(ref["center_gcj02"]).split(","))
            if not (73 < lng < 135 and 18 < lat < 55):
                raise ValueError("coordinate outside expected China range")
        except (ValueError, TypeError):
            row["status"] = "REFERENCE_COORDINATE_INVALID"
            continue

        result, error = call({
            "location": ref["center_gcj02"],
            "radius": str(RADIUS_M),
            "types": TYPECODES,
            "sortrule": "distance",
            "page_size": str(PAGE_SIZE),
            "page_num": "1",
            "output": "json"
        })
        if error:
            row["status"] = "POI_" + error
            row["provider_code"] = error
            continue

        pois = result.get("pois")
        if not isinstance(pois, list):
            row["status"] = "POI_UNEXPECTED_RESPONSE"
            continue
        unique = {}
        for p in pois:
            if isinstance(p, dict) and p.get("id"):
                unique[str(p["id"])] = p
        n = len(unique)
        try:
            api_count = int(result.get("count", n))
        except (TypeError, ValueError):
            api_count = n
        row["unique_poi_returned"] = n
        row["api_count"] = api_count

        # These are first-page category counts only; they are not full category totals.
        typecodes = [str(p.get("typecode", "")) for p in unique.values()]
        row["convenience_store_hits_first_page"] = sum(1 for t in typecodes if t.startswith("0602"))
        row["supermarket_hits_first_page"] = sum(1 for t in typecodes if t.startswith("0604"))
        row["market_hits_first_page"] = sum(1 for t in typecodes if t.startswith("0607"))

        if n >= PAGE_SIZE or api_count >= PAGE_SIZE:
            row["count_interpretation"] = "AT_LEAST_25_FIRST_PAGE_CAP"
            row["status"] = "AT_LEAST_25"
        elif n == 0:
            row["count_interpretation"] = "NO_POI_RETURNED; NOT_PROOF_OF_ZERO"
            row["status"] = "NO_POI_RETURNED_UNKNOWN"
        else:
            row["count_interpretation"] = "BELOW_25_FIRST_PAGE_UNSATURATED; MAP_DATABASE_NOT_CERTIFIED_COMPLETE"
            row["status"] = "RETURNED_1_TO_24"

    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    ROOT.mkdir(parents=True, exist_ok=True)
    tally = Counter(r["status"] for r in rows)
    payload = {
        "schema": "anju_daily_essentials_1km_proxy_v1",
        "timestamp_utc": stamp,
        "target": "110 phase-2 areas",
        "registry_sha256": hashlib.sha256(registry_bytes).hexdigest(),
        "reference_source": "anju/results/pharmacy_1km/latest.json",
        "metric": "Convenience stores, supermarkets and general markets within 1km of each county/district government reference point",
        "provider": PROVIDER,
        "endpoint": ENDPOINT,
        "typecodes": TYPECODES,
        "type_name": TYPE_NAME,
        "radius_m": RADIUS_M,
        "page_size": PAGE_SIZE,
        "max_requests": MAX_REQUESTS,
        "actual_requests": request_count,
        "area_limit": LIMIT,
        "halt_reason": halt_reason,
        "status_counts": dict(tally),
        "limitations": [
            "Narrower daily-procurement category selected after broad shopping-service query hit the first-page cap in 108/110 areas",
            "County/district government reference point is a proxy, not a confirmed representative residential location",
            "Gaode POI search hits are not a certified complete merchant inventory",
            "A first page of 25 means at least 25; exact count is not claimed",
            "A first page below 25 is an observed return count, not a government-certified complete inventory",
            "No result is unknown/not detected, not a confirmed zero",
            "No individual POI names or IDs are persisted",
            "First-page subcategory composition is not a full subcategory count",
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
        "statuses": dict(tally),
        "at_least_25": tally.get("AT_LEAST_25", 0),
        "returned_1_to_24": tally.get("RETURNED_1_TO_24", 0),
        "no_result_unknown": tally.get("NO_POI_RETURNED_UNKNOWN", 0),
        "reference_unavailable": tally.get("REFERENCE_CENTER_UNAVAILABLE", 0),
        "halt_reason": halt_reason,
        "formal_scores_changed": 0
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
