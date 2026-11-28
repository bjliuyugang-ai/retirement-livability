#!/usr/bin/env python3
"""Fetch page 2 only for capped daily-procurement category queries.

Consumes the accepted first-page 110-area matrix. Queries page 2 only where
page 1 returned 25 results, for each of 060200/060400/060700 independently.
This staged approach adds resolution without blindly requesting pages 3-8.
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

SOURCE = Path("anju/results/daily_essentials_by_category_1km/latest.json")
ROOT = Path("anju/results/daily_essentials_by_category_1km")
ENDPOINT = "https://restapi.amap.com/v5/place/around"
PROVIDER = "Gaode Web Service v5 POI Around"
CATEGORIES = {
    "convenience": {"typecode": "060200", "label": "便民商店/便利店"},
    "supermarket": {"typecode": "060400", "label": "超市"},
    "market": {"typecode": "060700", "label": "综合市场"},
}
PAGE_SIZE = 25
RADIUS_M = 1000
MAX_REQUESTS = int(os.environ.get("ANJU_MAX_REQUESTS", "200"))
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
        req = urllib.request.Request(url, headers={"User-Agent": "Anju-Daily-Procurement-Page2/1.0"})
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
    raw = SOURCE.read_bytes()
    payload = json.loads(raw)
    rows = payload.get("rows") or []
    assert len(rows) == 110, f"Expected 110 rows, got {len(rows)}"
    assert 1 <= MAX_REQUESTS <= 220

    for row in rows:
        for key, category in CATEGORIES.items():
            first_status = row.get(key + "_status", "")
            first_count = row.get(key + "_count", "")
            row[key + "_page2_count"] = ""
            row[key + "_first2_cumulative"] = ""
            row[key + "_pagination_status"] = "NOT_NEEDED"
            if first_status != "AT_LEAST_25":
                row[key + "_pagination_status"] = "FIRST_PAGE_BELOW_CAP_OR_UNKNOWN"
                if first_count != "":
                    row[key + "_first2_cumulative"] = first_count
                continue
            if halt_reason:
                row[key + "_pagination_status"] = halt_reason
                continue
            if request_count >= MAX_REQUESTS:
                halt_reason = "REQUEST_CAP_REACHED"
                row[key + "_pagination_status"] = halt_reason
                continue

            result, error = call({
                "location": row["center_gcj02"],
                "radius": str(RADIUS_M),
                "types": category["typecode"],
                "sortrule": "distance",
                "page_size": str(PAGE_SIZE),
                "page_num": "2",
                "output": "json"
            })
            if error:
                row[key + "_pagination_status"] = error
                continue
            pois = result.get("pois")
            if not isinstance(pois, list):
                row[key + "_pagination_status"] = "UNEXPECTED_RESPONSE"
                continue
            ids = {
                str(p.get("id")) for p in pois
                if isinstance(p, dict) and p.get("id")
            }
            n = len(ids)
            row[key + "_page2_count"] = n
            try:
                api_count = int(result.get("count", n))
            except (TypeError, ValueError):
                api_count = n
            row[key + "_page2_api_count"] = api_count
            cumulative = int(first_count or 0) + n
            row[key + "_first2_cumulative"] = cumulative
            if n >= PAGE_SIZE or api_count >= PAGE_SIZE:
                row[key + "_pagination_status"] = "AT_LEAST_50"
            else:
                row[key + "_pagination_status"] = "PAGE2_BELOW_CAP; FIRST_2_PAGE_RETURNED_TOTAL"

    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    status_counts = {
        key: dict(Counter(r.get(key + "_pagination_status", "") for r in rows))
        for key in CATEGORIES
    }
    out = {
        "schema": "anju_daily_essentials_by_category_1km_page2_v1",
        "timestamp_utc": stamp,
        "source_first_page_timestamp": payload.get("timestamp_utc"),
        "source_first_page_schema": payload.get("schema"),
        "source_first_page_sha256": hashlib.sha256(raw).hexdigest(),
        "target": "110 phase-2 areas; page 2 only for category cells capped at page 1",
        "provider": PROVIDER,
        "endpoint": ENDPOINT,
        "categories": CATEGORIES,
        "radius_m": RADIUS_M,
        "page_size": PAGE_SIZE,
        "page_fetched": 2,
        "max_requests": MAX_REQUESTS,
        "actual_requests": request_count,
        "halt_reason": halt_reason,
        "status_counts_by_category": status_counts,
        "limitations": [
            "Only cells capped at 25 on page 1 are queried on page 2",
            "Page 2 below 25 indicates the first two pages returned fewer than 50; it is not a certified complete merchant inventory",
            "Page 2 returning 25 means at least 50; pages 3-8 have not been queried",
            "Amap POI 2.0 supports at most 200 records across pages for one query",
            "Government reference point within 1km remains a proxy, not a confirmed representative residential location",
            "No POI names or IDs are persisted",
            "No result remains unknown, never a confirmed zero",
            "No A-D score or formal V12.2 value is changed"
        ],
        "rows": rows
    }
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "page2.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = list(dict.fromkeys(k for row in rows for k in row.keys()))
    with (ROOT / "page2.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({
        "timestamp_utc": stamp,
        "areas": len(rows),
        "requests": request_count,
        "status_counts_by_category": status_counts,
        "halt_reason": halt_reason
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
