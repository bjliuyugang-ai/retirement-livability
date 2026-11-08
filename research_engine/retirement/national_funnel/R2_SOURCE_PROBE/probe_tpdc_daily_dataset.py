#!/usr/bin/env python3
"""Probe the official TPDC daily 1km climate dataset for R2 source readiness.

This is source discovery only. It does not screen any R1/R2 candidate area.
"""
from __future__ import annotations
import csv
import datetime as dt
import hashlib
import json
import pathlib
import re
import urllib.parse
import urllib.request
import zipfile

BASE_URL = "https://data.tpdc.ac.cn"
DATASET_ID = "0ae99103-cb2e-4557-a203-2d97cf04e980"
ROOT = pathlib.Path("research_engine/retirement/national_funnel/R2_SOURCE_PROBE")
OUT = ROOT / "output"
UA = "Retirement-National-Funnel-R2-Source-Probe/1.0"
MAX_NODES = 2000
MAX_SAMPLE_DOWNLOAD_BYTES = 150_000_000

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def request(url, method="GET", payload=None, timeout=90, stream=False):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "User-Agent": UA,
        "Accept": "application/json,text/plain,*/*",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    response = urllib.request.urlopen(req, timeout=timeout)
    if stream:
        return response.status, response.headers, response
    with response:
        body = response.read()
        return response.status, response.headers, body

def decode_json(raw, label):
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"{label}_NOT_JSON: {raw[:500]!r}; {exc}")

def list_nodes(obj):
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        for key in ("data", "context", "records", "list", "rows", "children", "fileList", "result"):
            if isinstance(obj.get(key), list):
                return [x for x in obj[key] if isinstance(x, dict)]
            if isinstance(obj.get(key), dict):
                nested = list_nodes(obj[key])
                if nested:
                    return nested
    return []

def get_id(node):
    for k in ("id", "fileId", "fileID", "_id", "nodeId", "folderId"):
        if node.get(k) is not None:
            return str(node[k])
    return ""

def get_name(node):
    for k in ("name", "fileName", "filename", "orginName", "originalName", "title", "label"):
        if node.get(k):
            return str(node[k])
    return ""

def get_size(node):
    for k in ("size", "fileSize", "filesize", "file_size", "length", "totalSize"):
        v = node.get(k)
        if v is None:
            continue
        try:
            if isinstance(v, str):
                v = v.replace(",", "").strip()
                if v.lower().endswith("mb"):
                    return int(float(v[:-2].strip()) * 1024 * 1024)
                if v.lower().endswith("gb"):
                    return int(float(v[:-2].strip()) * 1024 * 1024 * 1024)
            return int(float(v))
        except Exception:
            continue
    return None

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    started = now()
    audit = []
    detail = {}
    root_obj = {}
    try:
        status, headers, raw = request(
            BASE_URL + "/view/metadataView/detail/",
            method="POST",
            payload={"userId": "", "metadataId": DATASET_ID},
        )
        detail = decode_json(raw, "METADATA_DETAIL")
        (OUT / "tpdc_metadata_detail.json").write_text(
            json.dumps(detail, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        audit.append({
            "step": "metadata_detail",
            "status": "PASS",
            "http_status": status,
            "content_type": headers.get("Content-Type"),
            "bytes": len(raw),
            "response_code": detail.get("code") if isinstance(detail, dict) else None,
        })
    except Exception as exc:
        audit.append({"step": "metadata_detail", "status": "ERROR", "error": repr(exc)})

    root_url = BASE_URL + "/file/file/getRootFileDataList?" + urllib.parse.urlencode({"metadataId": DATASET_ID})
    try:
        status, headers, raw = request(root_url)
        root_obj = decode_json(raw, "ROOT_FILE_LIST")
        (OUT / "tpdc_root_file_list.json").write_text(
            json.dumps(root_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        roots = list_nodes(root_obj)
        audit.append({
            "step": "root_file_list",
            "status": "PASS",
            "http_status": status,
            "content_type": headers.get("Content-Type"),
            "bytes": len(raw),
            "response_code": root_obj.get("code") if isinstance(root_obj, dict) else None,
            "root_nodes": len(roots),
        })
    except Exception as exc:
        roots = []
        audit.append({"step": "root_file_list", "status": "ERROR", "error": repr(exc)})

    queue = [(x, "") for x in roots]
    seen = set()
    inventory = []
    child_errors = []
    while queue and len(inventory) < MAX_NODES:
        node, parent_path = queue.pop(0)
        nid = get_id(node)
        name = get_name(node)
        key = (nid, name)
        if key in seen:
            continue
        seen.add(key)
        full_path = f"{parent_path}/{name}".strip("/")
        size = get_size(node)
        row = {
            "id": nid,
            "name": name,
            "path": full_path,
            "size_bytes": size,
            "size_mb": round(size / 1024 / 1024, 2) if size is not None else None,
            "raw_json": json.dumps(node, ensure_ascii=False)[:5000],
        }
        inventory.append(row)

        # Querying each node is harmless; file nodes return an empty child list.
        if nid:
            child_url = BASE_URL + "/file/file/getFileDataList?" + urllib.parse.urlencode({"parentId": nid})
            try:
                cstatus, cheaders, craw = request(child_url, timeout=30)
                child_obj = decode_json(craw, "CHILD_FILE_LIST")
                kids = list_nodes(child_obj)
                for kid in kids:
                    queue.append((kid, full_path))
            except Exception as exc:
                child_errors.append({"node_id": nid, "name": name, "error": repr(exc)[:500]})

    fields = ["id", "name", "path", "size_bytes", "size_mb", "raw_json"]
    with (OUT / "file_inventory.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(inventory)

    pattern = re.compile(r"(tmax|tasmax|maximum.?temp|air.?temp|max.?temperature|sunshine|sun.?duration|ssd)", re.I)
    targets = [r for r in inventory if pattern.search(r["name"] + " " + r["path"])]
    with (OUT / "climate_target_files.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(targets)

    sample_result = {"status": "NOT_ATTEMPTED", "reason": "No clearly identified climate file at or below 150 MB"}
    candidates = [r for r in targets if r["id"] and r["size_bytes"] is not None and 0 < r["size_bytes"] <= MAX_SAMPLE_DOWNLOAD_BYTES]
    if candidates:
        candidates.sort(key=lambda r: (
            0 if re.search(r"(tmax|tasmax|maximum.?temp|max.?temperature)", r["name"], re.I) else 1,
            r["size_bytes"],
        ))
        chosen = candidates[0]
        url = BASE_URL + "/file/file/batchDownloadByFileId?" + urllib.parse.urlencode({"fileId": chosen["id"]})
        try:
            status, headers, response = request(url, method="POST", payload={"noToken": True}, timeout=600, stream=True)
            sample_path = OUT / "sample_climate_file.bin"
            h = hashlib.sha256()
            n = 0
            with response:
                with sample_path.open("wb") as f:
                    while True:
                        block = response.read(4 * 1024 * 1024)
                        if not block:
                            break
                        f.write(block)
                        h.update(block)
                        n += len(block)
            sample_result = {
                "status": "DOWNLOADED",
                "selected_file": chosen,
                "http_status": status,
                "content_type": headers.get("Content-Type"),
                "content_disposition": headers.get("Content-Disposition"),
                "content_length_header": headers.get("Content-Length"),
                "bytes": n,
                "sha256": h.hexdigest(),
                "is_zip": zipfile.is_zipfile(sample_path),
            }
            if sample_result["is_zip"]:
                with zipfile.ZipFile(sample_path) as z:
                    sample_result["zip_members"] = [
                        {"name": x.filename, "bytes": x.file_size}
                        for x in z.infolist()[:100]
                    ]
        except Exception as exc:
            sample_result = {"status": "DOWNLOAD_FAILED", "selected_file": chosen, "error": repr(exc)[:1500]}

    (OUT / "child_list_errors.json").write_text(
        json.dumps(child_errors, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "sample_download_result.json").write_text(
        json.dumps(sample_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "schema": "RETIREMENT_TPDC_DAILY_CLIMATE_SOURCE_PROBE_V1",
        "dataset_id": DATASET_ID,
        "started_at_utc": started,
        "completed_at_utc": now(),
        "metadata_detail_status": next((x["status"] for x in audit if x["step"] == "metadata_detail"), "NOT_RUN"),
        "root_list_status": next((x["status"] for x in audit if x["step"] == "root_file_list"), "NOT_RUN"),
        "root_node_count": len(roots),
        "inventory_node_count": len(inventory),
        "climate_target_file_count": len(targets),
        "child_list_error_count": len(child_errors),
        "sample_download": sample_result,
        "audit": audit,
        "next_action": (
            "Inspect inventory and test daily Tmax aggregation if actual GeoTIFF/NetCDF files are available."
            if inventory else
            "Investigate TPDC API/authentication and dataset access restrictions; no climate screening has been run."
        ),
    }
    (OUT / "probe_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if not inventory:
        raise RuntimeError("TPDC_FILE_INVENTORY_EMPTY; source access remains unverified")

if __name__ == "__main__":
    main()
