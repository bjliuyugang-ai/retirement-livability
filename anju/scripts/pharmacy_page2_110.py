#!/usr/bin/env python3
"""Targeted second-page retrieval for pharmacy POIs in the 110 retained areas."""
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

SOURCE = Path("anju/results/pharmacy_1km/latest.json")
ROOT = Path("anju/results/pharmacy_1km")
ENDPOINT = "https://restapi.amap.com/v5/place/around"
TYPECODE = "090601"
RADIUS_M = 1000
PAGE_SIZE = 25
MAX_REQUESTS = int(os.environ.get("ANJU_MAX_REQUESTS", "75"))
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
        req = urllib.request.Request(url, headers={"User-Agent": "Anju-Pharmacy-Page2/1.0"})
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
    source = json.loads(raw)
    rows = source.get("rows") or []
    assert len(rows) == 110, f"Expected 110 pharmacy rows, got {len(rows)}"
    assert 1 <= MAX_REQUESTS <= 100

    for row in rows:
        row["page2_count"] = ""
        row["page2_api_count"] = ""
        row["first2_cumulative"] = ""
        row["pagination_status"] = "NOT_NEEDED"
        count = row.get("poi_returned_count")
        status = row.get("status", "")
        if status == "CAPPED_LOWER_BOUND" and count not in (None, ""):
            if halt_reason:
                row["pagination_status"] = halt_reason
                continue
            if request_count >= MAX_REQUESTS:
                halt_reason = "REQUEST_CAP_REACHED"
                row["pagination_status"] = halt_reason
                continue
            result, error = call({
                "location": row["center_gcj02"],
                "radius": str(RADIUS_M),
                "types": TYPECODE,
                "sortrule": "distance",
                "page_size": str(PAGE_SIZE),
                "page_num": "2",
                "output": "json"
            })
            if error:
                row["pagination_status"] = error
                continue
            pois = result.get("pois")
            if not isinstance(pois, list):
                row["pagination_status"] = "UNEXPECTED_RESPONSE"
                continue
            ids = {
                str(p.get("id")) for p in pois
                if isinstance(p, dict) and p.get("id")
            }
            n = len(ids)
            row["page2_count"] = n
            try:
                api_count = int(result.get("count", n))
            except (TypeError, ValueError):
                api_count = n
            row["page2_api_count"] = api_count
            cumulative = int(count or 0) + n
            row["first2_cumulative"] = cumulative
            if n >= PAGE_SIZE or api_count >= PAGE_SIZE:
                row["pagination_status"] = "AT_LEAST_50"
            else:
                row["pagination_status"] = "PAGE2_BELOW_CAP; FIRST_2_PAGE_RETURNED_TOTAL"
        elif status == "FIRST_PAGE_UNCAPPED" and int(count or 0) == 0:
            row["pagination_status"] = "NO_POI_RETURNED_UNKNOWN"
        elif status == "FIRST_PAGE_UNCAPPED":
            row["first2_cumulative"] = int(count or 0)
            row["pagination_status"] = "FIRST_PAGE_BELOW_CAP"
        else:
            row["pagination_status"] = status or "UNKNOWN"

    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    ROOT.mkdir(parents=True, exist_ok=True)
    tally = dict(Counter(r.get("pagination_status", "") for r in rows))
    payload = {
        "schema": "anju_pharmacy_1km_page2_v1",
        "timestamp_utc": stamp,
        "source_first_page_timestamp": source.get("timestamp_utc"),
        "source_first_page_sha256": hashlib.sha256(raw).hexdigest(),
        "target": "110 retained areas; page 2 only for first-page pharmacy results capped at 25",
        "provider": "Gaode Web Service v5 POI Around",
        "typecode": TYPECODE,
        "radius_m": RADIUS_M,
        "page_size": PAGE_SIZE,
        "actual_requests": request_count,
        "max_requests": MAX_REQUESTS,
        "halt_reason": halt_reason,
        "status_counts": tally,
        "limitations": [
            "Only first-page capped rows were queried on page 2",
            "Page 2 below 25 means the first two pages returned fewer than 50; not a certified complete pharmacy inventory",
            "Page 2 returning 25 means at least 50; pages 3-8 not queried",
            "No first-page result is unknown/not detected, never confirmed zero",
            "Government point 1km radius is an area-level proxy, not a verified residential point",
            "No POI names or IDs are persisted",
            "No formal A-D rating or V12.2 score changed"
        ],
        "rows": rows
    }
    (ROOT / "page2.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = list(dict.fromkeys(k for row in rows for k in row.keys()))
    with (ROOT / "page2.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({
        "timestamp_utc": stamp,
        "areas": len(rows),
        "requests": request_count,
        "status_counts": tally,
        "halt_reason": halt_reason
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
