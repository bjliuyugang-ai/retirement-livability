#!/usr/bin/env python3
"""Fit-for-purpose source probe for CHM_Tmax v2 (Zenodo record 22097524)."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import pathlib
import urllib.request
import zipfile

RECORD_ID = "22097524"
RECORD_API = f"https://zenodo.org/api/records/{RECORD_ID}"
TARGET_FILE = "CHM_Tmax_1990_1999.zip"
ROOT = pathlib.Path("research_engine/retirement/national_funnel/R2_SOURCE_PROBE/CHM_TMAX")
OUT = ROOT / "output"
WORK = pathlib.Path("work_chm_tmax_probe")
UA = "RetirementLivability-ClimateScreen/1.0"

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def download(url, path, expected_size=None):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 RetirementLivability-ClimateScreen/1.0", "Accept": "*/*"})
    h = hashlib.md5()
    n = 0
    with urllib.request.urlopen(req, timeout=300) as r:
        headers = dict(r.headers.items())
        with path.open("wb") as f:
            while True:
                block = r.read(4 * 1024 * 1024)
                if not block:
                    break
                f.write(block)
                h.update(block)
                n += len(block)
    if expected_size is not None and n != expected_size:
        raise RuntimeError(f"SIZE_MISMATCH expected={expected_size} actual={n}")
    return {"bytes": n, "md5": h.hexdigest(), "headers": headers}

def main():
    started = now()
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    record = get_json(RECORD_API)
    files = record.get("files", [])
    item = next((x for x in files if x.get("key") == TARGET_FILE), None)
    if not item:
        raise RuntimeError("TARGET_FILE_NOT_FOUND_IN_ZENODO_RECORD")
    links = item.get("links", {})
    url = f"https://zenodo.org/records/{RECORD_ID}/files/{TARGET_FILE}?download=1"
    archive = WORK / TARGET_FILE
    print(json.dumps({"probe_target_url": url, "file_metadata": item}, ensure_ascii=False), flush=True)
    download_meta = download(url, archive, item.get("size"))
    expected_md5 = str(item.get("checksum", "")).split(":")[-1]
    if expected_md5 and download_meta["md5"].lower() != expected_md5.lower():
        raise RuntimeError(f"MD5_MISMATCH expected={expected_md5} actual={download_meta['md5']}")
    with zipfile.ZipFile(archive) as z:
        members = [{"name": x.filename, "bytes": x.file_size, "compressed_bytes": x.compress_size} for x in z.infolist()]
        nc_member = next((x.filename for x in z.infolist() if x.filename.lower().endswith(".nc")), None)
        if not nc_member:
            raise RuntimeError("NO_NETCDF_MEMBER_IN_ZIP")
        extracted = WORK / pathlib.Path(nc_member).name
        with z.open(nc_member) as src, extracted.open("wb") as dst:
            while True:
                b = src.read(8 * 1024 * 1024)
                if not b:
                    break
                dst.write(b)
    try:
        import netCDF4
        import numpy as np
        with netCDF4.Dataset(extracted, "r") as ds:
            dims = {k: len(v) for k, v in ds.dimensions.items()}
            variables = {}
            for name, var in ds.variables.items():
                variables[name] = {
                    "dimensions": list(var.dimensions),
                    "shape": list(var.shape),
                    "dtype": str(var.dtype),
                    "units": getattr(var, "units", None),
                    "scale_factor": getattr(var, "scale_factor", None),
                    "add_offset": getattr(var, "add_offset", None),
                    "long_name": getattr(var, "long_name", None),
                }
            lat = ds.variables.get("lat")
            lon = ds.variables.get("lon")
            tmax = ds.variables.get("Tmax")
            sample = {}
            if lat is not None:
                sample["lat_min"] = float(np.nanmin(lat[:]))
                sample["lat_max"] = float(np.nanmax(lat[:]))
            if lon is not None:
                sample["lon_min"] = float(np.nanmin(lon[:]))
                sample["lon_max"] = float(np.nanmax(lon[:]))
            if tmax is not None and lat is not None and lon is not None:
                sample_points = {"Beijing": (39.9, 116.4), "Shanghai": (31.2, 121.4), "Guangzhou": (23.1, 113.3)}
                sample["city_grid_samples"] = {}
                lat_values = np.asarray(lat[:])
                lon_values = np.asarray(lon[:])
                for city, (target_lat, target_lon) in sample_points.items():
                    iy = int(np.abs(lat_values - target_lat).argmin())
                    ix = int(np.abs(lon_values - target_lon).argmin())
                    arr = np.ma.asarray(tmax[0:3, max(0, iy-1):iy+2, max(0, ix-1):ix+2])
                    finite = arr.compressed()
                    sample["city_grid_samples"][city] = {
                        "nearest_lat": float(lat_values[iy]),
                        "nearest_lon": float(lon_values[ix]),
                        "first_3_days_valid_cell_count": int(finite.size),
                        "first_3_days_min_c": float(finite.min()) if finite.size else None,
                        "first_3_days_max_c": float(finite.max()) if finite.size else None,
                        "first_3_days_mean_c": float(finite.mean()) if finite.size else None
                    }
                sample["lat_order"] = "ascending" if lat_values[0] < lat_values[-1] else "descending"
                sample["lon_order"] = "ascending" if lon_values[0] < lon_values[-1] else "descending"
        result = {
            "schema": "RETIREMENT_CHM_TMAX_V2_SOURCE_PROBE_V1",
            "status": "PASS",
            "record_id": RECORD_ID,
            "record_title": record.get("metadata", {}).get("title"),
            "record_version": "v2 (Zenodo record 22097524)",
            "target_file": TARGET_FILE,
            "target_file_size": item.get("size"),
            "target_file_checksum": item.get("checksum"),
            "download_url": url,
            "download": download_meta,
            "zip_members": members,
            "netcdf_member": nc_member,
            "netcdf_size_bytes": extracted.stat().st_size,
            "dimensions": dims,
            "variables": variables,
            "sample": sample,
            "started_at_utc": started,
            "completed_at_utc": now(),
            "next_step": "Download only the 1990-1999, 2000-2009, 2010-2019 and 2020-2022 Tmax files; compute 1991-2020 county zonal summaries. No need to download other variables."
        }
    finally:
        try: extracted.unlink()
        except Exception: pass
        try: archive.unlink()
        except Exception: pass
    out = OUT / "chm_tmax_source_probe.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
