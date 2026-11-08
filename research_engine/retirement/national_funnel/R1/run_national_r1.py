#!/usr/bin/env python3
"""National R1 funnel: population-weighted sunshine + inhabited-cell elevation samples.

This is a new, independent nationwide screening line. It does not modify the
legacy 34-area work or the existing V1.6 task state machine.

R1 inputs: 2026-06 provisional 2,847-county roster.
Sunshine: 1km monthly mean sunshine percentage (1991-2020), converted to
estimated annual sunshine hours using astronomical day length. A +/-75h
guard band prevents borderline values from being hard-excluded.
Elevation: Open-Meteo Elevation API backed by Copernicus GLO-90 (~90m),
queried only at population-grid residential sample cells.
"""
from __future__ import annotations

import calendar
import csv
import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask, geometry_window
from rasterio.transform import xy
from rasterio.warp import reproject
from shapely.geometry import mapping, shape

ROOT = pathlib.Path("research_engine/retirement")
BASE = ROOT / "national_funnel" / "R1"
CACHE = BASE / "cache"
OUT = BASE / "output"
ROSTER = ROOT / "evidence" / "provisional_counties_2026_06.csv"

GEOMETRY_URL = (
    "https://raw.githubusercontent.com/zzhonglei/GeoCode-Release/main/"
    "contributions/china-admin-boundaries/skill/data/china_county.geojson"
)
GEOMETRY_SHA256 = "22db6c54b9cb0118ecdcc8a117bf2da4fc24a2229cdba7e6e55dbb5dd56e8246"

# WorldPop 2024 global 1km population-count mosaic, constrained, WGS84.
POP_URL = (
    "https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2024/"
    "0_Mosaicked/v1/1km_ua/constrained/"
    "global_pop_2024_CN_1km_R2025A_UA_v1.tif"
)

# ScienceDB V8 1991-2020 1km monthly mean sunshine percentage, 12 bands.
SUNP_URL = "https://china.scidb.cn/download?fileId=cc20e819b4c903a1dc200aeead645e7c"
SUNP_EXPECTED_ARCHIVE_BYTES = 286802207

ELEVATION_API = "https://api.open-meteo.com/v1/elevation"
ELEVATION_SOURCE = "Copernicus DEM GLO-90 via Open-Meteo Elevation API"

ALTITUDE_LIMIT_M = 2000.0
SUNSHINE_LIMIT_H = 1800.0
SUNSHINE_GUARD_H = 75.0
SUNSHINE_CLEAR_FAIL_H = SUNSHINE_LIMIT_H - SUNSHINE_GUARD_H
SUNSHINE_CLEAR_PASS_H = SUNSHINE_LIMIT_H + SUNSHINE_GUARD_H
MAX_ALTITUDE_SAMPLES = 10
SPATIAL_SAMPLE_MIN_DISTANCE_KM = 5.0
ELEVATION_BATCH_SIZE = 100
ELEVATION_BATCH_SLEEP_SECONDS = 10.2

RUN_ID = os.getenv("GITHUB_RUN_ID", "MANUAL")
NOW = lambda: dt.datetime.now(dt.timezone.utc).isoformat()

def sha_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def write_json(path: pathlib.Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )

def download(url: str, dest: pathlib.Path, expected_size: int | None = None) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        size = dest.stat().st_size
        if expected_size is None or size == expected_size:
            return {
                "status": "REUSED",
                "bytes": size,
                "sha256": sha_file(dest),
                "url": url,
            }
        dest.unlink()
    part = dest.with_suffix(dest.suffix + ".part")
    part.unlink(missing_ok=True)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Retirement-National-Funnel-R1/1.0", "Accept": "*/*"},
    )
    h = hashlib.sha256()
    n = 0
    with urllib.request.urlopen(req, timeout=240) as response:
        status = response.status
        final_url = response.geturl()
        content_type = response.headers.get("Content-Type")
        content_length = response.headers.get("Content-Length")
        with part.open("wb") as f:
            while True:
                block = response.read(4 * 1024 * 1024)
                if not block:
                    break
                f.write(block)
                h.update(block)
                n += len(block)
    if expected_size is not None and n != expected_size:
        part.unlink(missing_ok=True)
        raise RuntimeError(f"DOWNLOAD_SIZE_MISMATCH expected={expected_size} got={n}")
    part.replace(dest)
    return {
        "status": "DOWNLOADED",
        "http_status": status,
        "final_url": final_url,
        "content_type": content_type,
        "content_length_header": content_length,
        "bytes": n,
        "sha256": h.hexdigest(),
        "url": url,
    }

def load_roster() -> list[dict]:
    with ROSTER.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 2847:
        raise RuntimeError(f"ROSTER_COUNT_EXPECTED_2847_GOT_{len(rows)}")
    codes = [r["code"] for r in rows]
    if len(set(codes)) != len(codes):
        raise RuntimeError("DUPLICATE_ROSTER_CODES")
    return rows

def load_geometry() -> tuple[dict, dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "china_county.geojson"
    if not path.exists() or sha_file(path) != GEOMETRY_SHA256:
        meta = download(GEOMETRY_URL, path)
    else:
        meta = {"status": "REUSED", "bytes": path.stat().st_size, "sha256": sha_file(path)}
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != GEOMETRY_SHA256:
        raise RuntimeError("GEOMETRY_SHA256_MISMATCH " + actual)
    doc = json.loads(raw.decode("utf-8"))
    features = doc.get("features") or []
    geo = {}
    for feature in features:
        props = feature.get("properties") or {}
        code = str(props.get("adcode") or "")
        name = str(props.get("name") or "")
        if len(code) != 6 or not code.isdigit():
            continue
        if code in geo:
            raise RuntimeError("DUPLICATE_GEOMETRY_CODE " + code)
        geo[code] = {"name": name, "geometry": feature.get("geometry")}
    return geo, {
        "url": GEOMETRY_URL,
        "sha256": actual,
        "feature_count": len(features),
        "coded_feature_count": len(geo),
        "vintage": "third-party coded GeoJSON; vintage/datum not independently certified",
        "exact_code_name_matches": None,
        "status": "PROVISIONAL_GEOMETRY",
        "download": meta,
    }

def extract_sunp() -> tuple[pathlib.Path, dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    archive = CACHE / "China_sunp_1km_1991-2020.zip"
    tif = CACHE / "China_sunp_1km_1991-2020.tif"
    archive_meta = download(SUNP_URL, archive, SUNP_EXPECTED_ARCHIVE_BYTES)
    if not tif.exists():
        with zipfile.ZipFile(archive) as zf:
            bad = zf.testzip()
            if bad:
                raise RuntimeError("SUNP_ZIP_CRC_FAIL " + str(bad))
            members = [m for m in zf.infolist() if m.filename.lower().endswith((".tif", ".tiff"))]
            if len(members) != 1:
                raise RuntimeError("SUNP_EXPECTED_ONE_GEOTIFF_GOT_" + str(len(members)))
            member = members[0]
            with zf.open(member) as src, tif.open("wb") as dst:
                while True:
                    block = src.read(8 * 1024 * 1024)
                    if not block:
                        break
                    dst.write(block)
    return tif, {
        "archive": archive_meta,
        "geotiff_member": "single GeoTIFF member",
        "geotiff_bytes": tif.stat().st_size,
        "geotiff_sha256": sha_file(tif),
    }

def get_sunp_divisor(ds) -> tuple[float, dict]:
    samples = []
    windows = [
        (0.10, 0.10), (0.25, 0.50), (0.50, 0.50), (0.75, 0.50), (0.90, 0.90)
    ]
    for fracx, fracy in windows:
        col = min(ds.width - 256, max(0, int(ds.width * fracx)))
        row = min(ds.height - 256, max(0, int(ds.height * fracy)))
        win = rasterio.windows.Window(col, row, min(256, ds.width-col), min(256, ds.height-row))
        for band in (1, 6, 12):
            a = ds.read(band, window=win, masked=False).astype("float32", copy=False)
            valid = np.isfinite(a) & (a > -1e20)
            if ds.nodata is not None:
                valid &= a != ds.nodata
            if valid.any():
                vals = a[valid]
                if vals.size > 5000:
                    vals = vals[:: max(1, vals.size // 5000)]
                samples.extend(vals.tolist())
    if not samples:
        raise RuntimeError("SUNP_NO_VALID_SAMPLE_VALUES")
    p99 = float(np.percentile(np.asarray(samples, dtype="float32"), 99))
    if p99 <= 1.5:
        divisor = 1.0
        mode = "fraction_0_to_1"
    elif p99 <= 100.5:
        divisor = 100.0
        mode = "percent_0_to_100"
    elif p99 <= 10000.0:
        divisor = 10000.0
        mode = "scaled_percent_0_to_10000"
    else:
        raise RuntimeError(f"SUNP_VALUE_SCALE_UNRECOGNIZED p99={p99}")
    return divisor, {"sample_p99": p99, "divisor": divisor, "mode": mode}

def solar_daylength_hours(latitude_deg: np.ndarray, doy: int, year: int) -> np.ndarray:
    days_in_year = 366 if calendar.isleap(year) else 365
    gamma = 2.0 * math.pi * (doy - 1) / days_in_year
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.001480 * math.sin(3 * gamma)
    )
    phi = np.radians(latitude_deg)
    h0 = math.radians(-0.833)
    denom = np.cos(phi) * math.cos(decl)
    denom = np.where(np.abs(denom) < 1e-8, 1e-8, denom)
    cos_omega = (math.sin(h0) - np.sin(phi) * math.sin(decl)) / denom
    omega = np.arccos(np.clip(cos_omega, -1.0, 1.0))
    return (24.0 / math.pi) * omega

def build_monthly_solar_daylength(ds) -> tuple[np.ndarray, np.ndarray]:
    if ds.crs is None or ds.crs.to_epsg() != 4326:
        raise RuntimeError("SUNP_GRID_MUST_BE_EPSG4326")
    rows = np.arange(ds.height, dtype="float64")
    lat = ds.transform.f + (rows + 0.5) * ds.transform.e
    daylight_sum = np.zeros((ds.height, 12), dtype="float64")
    days_sum = np.zeros(12, dtype="float64")
    for year in range(1991, 2021):
        for month in range(1, 13):
            days = calendar.monthrange(year, month)[1]
            day_values = []
            for day in range(1, days + 1):
                doy = dt.date(year, month, day).timetuple().tm_yday
                day_values.append(solar_daylength_hours(lat, doy, year))
            daylight_sum[:, month - 1] += np.mean(np.stack(day_values, axis=0), axis=0)
            days_sum[month - 1] += days
    daylight_mean = (daylight_sum / 30.0).astype("float32")
    month_days_mean = (days_sum / 30.0).astype("float32")
    return daylight_mean, month_days_mean

def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float | None:
    if values.size == 0 or weights.size == 0:
        return None
    order = np.argsort(values)
    v = values[order]
    w = weights[order]
    total = float(np.sum(w))
    if total <= 0:
        return None
    c = np.cumsum(w)
    return float(np.interp(q * total, c, v))

def distance_km(lon1, lat1, lon2, lat2) -> float:
    dx = (lon2 - lon1) * 111.32 * math.cos(math.radians((lat1 + lat2) / 2.0))
    dy = (lat2 - lat1) * 111.32
    return math.sqrt(dx * dx + dy * dy)

def choose_population_samples(pop: np.ndarray, mask: np.ndarray, window, transform, max_n=10) -> list[dict]:
    cells = np.argwhere(mask & np.isfinite(pop) & (pop > 0))
    if cells.size == 0:
        return []
    vals = pop[cells[:, 0], cells[:, 1]]
    order = np.argsort(vals)[::-1]
    selected = []
    selected_indices = set()
    for idx in order:
        rr, cc = cells[idx]
        global_row = int(window.row_off) + int(rr)
        global_col = int(window.col_off) + int(cc)
        lon, lat = xy(transform, global_row, global_col, offset="center")
        if all(distance_km(lon, lat, p["longitude"], p["latitude"]) >= SPATIAL_SAMPLE_MIN_DISTANCE_KM for p in selected):
            selected.append({
                "sample_rank": len(selected) + 1,
                "longitude": float(lon),
                "latitude": float(lat),
                "population_grid_value": float(vals[idx]),
                "global_row": global_row,
                "global_col": global_col,
            })
            selected_indices.add(int(idx))
            if len(selected) >= max_n:
                break
    if len(selected) < min(max_n, len(cells)):
        for idx in order:
            if int(idx) in selected_indices:
                continue
            rr, cc = cells[idx]
            global_row = int(window.row_off) + int(rr)
            global_col = int(window.col_off) + int(cc)
            lon, lat = xy(transform, global_row, global_col, offset="center")
            selected.append({
                "sample_rank": len(selected) + 1,
                "longitude": float(lon),
                "latitude": float(lat),
                "population_grid_value": float(vals[idx]),
                "global_row": global_row,
                "global_col": global_col,
            })
            if len(selected) >= max_n:
                break
    return selected

def query_elevation(points: list[dict], phase: str) -> dict:
    completed = 0
    failed_batches = 0
    for start in range(0, len(points), ELEVATION_BATCH_SIZE):
        batch = points[start:start + ELEVATION_BATCH_SIZE]
        latitudes = ",".join(f"{p['latitude']:.6f}" for p in batch)
        longitudes = ",".join(f"{p['longitude']:.6f}" for p in batch)
        query = urllib.parse.urlencode({"latitude": latitudes, "longitude": longitudes})
        url = ELEVATION_API + "?" + query
        success = False
        last_error = None
        for attempt in range(1, 4):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Retirement-National-Funnel-R1/1.0", "Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=90) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                elevations = payload.get("elevation")
                if not isinstance(elevations, list) or len(elevations) != len(batch):
                    raise RuntimeError("ELEVATION_RESPONSE_LENGTH_MISMATCH")
                for point, elevation in zip(batch, elevations):
                    point["elevation_m"] = float(elevation) if elevation is not None else None
                    point["elevation_query_status"] = "OK" if elevation is not None else "NO_VALUE"
                success = True
                break
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                time.sleep(5 * attempt)
        if not success:
            failed_batches += 1
            for point in batch:
                point["elevation_m"] = None
                point["elevation_query_status"] = "FAILED: " + str(last_error)[:200]
        completed += len(batch)
        if start + ELEVATION_BATCH_SIZE < len(points):
            time.sleep(ELEVATION_BATCH_SLEEP_SECONDS)
        if completed % 600 == 0 or completed == len(points):
            print(f"ELEVATION_PHASE {phase} completed={completed}/{len(points)} failed_batches={failed_batches}", flush=True)
    return {"phase": phase, "points_submitted": len(points), "points_completed": completed, "failed_batches": failed_batches}

def write_csv(path: pathlib.Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    started = NOW()
    progress_path = OUT / "R1_PROGRESS.json"
    summary_path = OUT / "R1_SUMMARY.json"

    roster = load_roster()
    geo, geometry_meta = load_geometry()
    exact = [r for r in roster if r["code"] in geo and geo[r["code"]]["name"] == r["name"] and geo[r["code"]]["geometry"]]
    geometry_meta["exact_code_name_matches"] = len(exact)
    geometry_meta["missing_or_name_mismatch"] = len(roster) - len(exact)

    sunp_tif, sunp_download_meta = extract_sunp()
    pop_path = CACHE / "global_pop_2024_CN_1km_R2025A_UA_v1.tif"
    pop_download_meta = download(POP_URL, pop_path)

    results = {}
    point_candidates = {}
    altitude_point_rows = []
    sunp_scale_meta = {}
    raster_meta = {}
    population_grid_meta = {}
    altitude_query_meta = []

    with rasterio.open(sunp_tif) as sun_ds, rasterio.open(pop_path) as pop_ds:
        if sun_ds.count != 12:
            raise RuntimeError(f"SUNP_EXPECTED_12_BANDS_GOT_{sun_ds.count}")
        if sun_ds.crs is None or sun_ds.crs.to_epsg() != 4326:
            raise RuntimeError("SUNP_CRS_NOT_EPSG4326")
        divisor, sunp_scale_meta = get_sunp_divisor(sun_ds)
        daylight, month_days = build_monthly_solar_daylength(sun_ds)

        pop_grid = np.zeros((sun_ds.height, sun_ds.width), dtype="float32")
        reproject(
            source=rasterio.band(pop_ds, 1),
            destination=pop_grid,
            src_transform=pop_ds.transform,
            src_crs=pop_ds.crs,
            src_nodata=pop_ds.nodata,
            dst_transform=sun_ds.transform,
            dst_crs=sun_ds.crs,
            dst_nodata=0,
            resampling=Resampling.average,
            init_dest_nodata=True,
            num_threads=2,
        )
        pop_grid[~np.isfinite(pop_grid)] = 0
        pop_grid[pop_grid < 0] = 0
        if float(pop_grid.sum()) <= 0:
            raise RuntimeError("POPULATION_GRID_REPROJECTED_SUM_ZERO")
        population_grid_meta = {
            "source_url": POP_URL,
            "source_crs": str(pop_ds.crs),
            "source_width": pop_ds.width,
            "source_height": pop_ds.height,
            "source_transform": list(pop_ds.transform),
            "target_crs": str(sun_ds.crs),
            "target_width": sun_ds.width,
            "target_height": sun_ds.height,
            "target_transform": list(sun_ds.transform),
            "resampling": "average_to_sunp_1km_grid",
            "positive_target_cells": int(np.count_nonzero(pop_grid > 0)),
            "target_population_grid_sum_relative": float(pop_grid.sum()),
        }
        raster_meta = {
            "sunp_crs": str(sun_ds.crs),
            "sunp_width": sun_ds.width,
            "sunp_height": sun_ds.height,
            "sunp_bands": sun_ds.count,
            "sunp_dtype": list(sun_ds.dtypes),
            "sunp_nodata": sun_ds.nodata,
            "sunp_bounds": list(sun_ds.bounds),
            "sunp_transform": list(sun_ds.transform),
            "sunp_tags": sun_ds.tags(),
            "sunp_band1_tags": sun_ds.tags(1),
        }

        total = len(roster)
        for i, r in enumerate(roster, 1):
            code, name = r["code"], r["name"]
            row = {
                "code": code,
                "name": name,
                "source_class": r.get("source_class", ""),
                "asof": r.get("asof", ""),
                "geometry_status": "EXACT_CODE_NAME_MATCH_PROVISIONAL",
                "inhabited_grid_cells": 0,
                "valid_sunshine_pop_cells": 0,
                "population_grid_sum_relative": None,
                "sunshine_population_coverage": None,
                "sunshine_pop_weighted_mean_h": None,
                "sunshine_pop_weighted_p10_h": None,
                "sunshine_pop_weighted_p50_h": None,
                "sunshine_pop_weighted_p90_h": None,
                "sunshine_max_pop_ge10_h": None,
                "sunshine_pop_share_ge1800": None,
                "sunshine_status": "PENDING",
                "altitude_population_sample_count": 0,
                "altitude_population_cells_total": 0,
                "altitude_min_sample_m": None,
                "altitude_max_sample_m": None,
                "altitude_status": "PENDING",
                "altitude_source": ELEVATION_SOURCE,
                "R1_next_round_status": "PENDING_CONTINUE",
                "R1_exclusion_reason": "",
            }
            if code not in geo or geo[code]["name"] != name or not geo[code]["geometry"]:
                row["geometry_status"] = "NO_EXACT_GEOMETRY_PENDING"
                row["sunshine_status"] = "PENDING_GEOMETRY"
                row["altitude_status"] = "PENDING_GEOMETRY"
                results[code] = row
                continue

            geom = shape(geo[code]["geometry"])
            if not geom.is_valid:
                geom = geom.buffer(0)
            if geom.is_empty or not geom.is_valid:
                row["geometry_status"] = "INVALID_GEOMETRY_PENDING"
                row["sunshine_status"] = "PENDING_INVALID_GEOMETRY"
                row["altitude_status"] = "PENDING_INVALID_GEOMETRY"
                results[code] = row
                continue

            try:
                window = geometry_window(sun_ds, [mapping(geom)])
                window = window.intersection(rasterio.windows.Window(0, 0, sun_ds.width, sun_ds.height))
                h, w = int(window.height), int(window.width)
                if h <= 0 or w <= 0:
                    raise ValueError("EMPTY_WINDOW")
                inside = geometry_mask(
                    [mapping(geom)],
                    out_shape=(h, w),
                    transform=sun_ds.window_transform(window),
                    invert=True,
                    all_touched=False,
                )
            except Exception as exc:
                row["geometry_status"] = "NO_GRID_WINDOW_PENDING"
                row["sunshine_status"] = "PENDING_NO_GRID_WINDOW"
                row["altitude_status"] = "PENDING_NO_GRID_WINDOW"
                row["geometry_error"] = str(exc)[:200]
                results[code] = row
                continue

            r0, c0 = int(window.row_off), int(window.col_off)
            pop = pop_grid[r0:r0+h, c0:c0+w]
            inhabited = inside & np.isfinite(pop) & (pop > 0)
            n_inhabited = int(inhabited.sum())
            pop_total = float(pop[inhabited].sum()) if n_inhabited else 0.0
            row["inhabited_grid_cells"] = n_inhabited
            row["altitude_population_cells_total"] = n_inhabited
            row["population_grid_sum_relative"] = round(pop_total, 3) if n_inhabited else 0.0

            # Select up to 10 spatially dispersed inhabited cells for elevation.
            samples = choose_population_samples(pop, inside, window, sun_ds.transform, MAX_ALTITUDE_SAMPLES)
            point_candidates[code] = [
                {
                    "code": code,
                    "name": name,
                    "sample_rank": p["sample_rank"],
                    "longitude": p["longitude"],
                    "latitude": p["latitude"],
                    "population_grid_value": p["population_grid_value"],
                    "elevation_m": None,
                    "elevation_query_status": "NOT_QUERIED",
                }
                for p in samples
            ]

            if n_inhabited == 0:
                row["sunshine_status"] = "PENDING_NO_INHABITED_POPULATION_GRID"
                row["altitude_status"] = "PENDING_NO_INHABITED_POPULATION_GRID"
                results[code] = row
                continue

            sun = sun_ds.read(indexes=list(range(1, 13)), window=window, masked=False).astype("float32", copy=False)
            valid_bands = np.isfinite(sun) & (sun > -1e20)
            if sun_ds.nodata is not None:
                valid_bands &= (sun != sun_ds.nodata)
            valid_sun = np.all(valid_bands, axis=0)
            valid_pop = inhabited & valid_sun
            n_valid = int(valid_pop.sum())
            valid_pop_sum = float(pop[valid_pop].sum()) if n_valid else 0.0
            row["valid_sunshine_pop_cells"] = n_valid
            row["sunshine_population_coverage"] = round(valid_pop_sum / pop_total, 4) if pop_total > 0 else 0.0

            if n_valid > 0:
                lat_rows = sun_ds.transform.f + (np.arange(r0, r0+h, dtype="float32") + 0.5) * sun_ds.transform.e
                annual = np.zeros((h, w), dtype="float32")
                for month in range(12):
                    frac = np.clip(sun[month] / divisor, 0.0, 1.0)
                    annual += frac * daylight[r0:r0+h, month][:, None] * month_days[month]
                vals = annual[valid_pop].astype("float64")
                weights = pop[valid_pop].astype("float64")
                row["sunshine_pop_weighted_mean_h"] = round(float(np.average(vals, weights=weights)), 1)
                row["sunshine_pop_weighted_p10_h"] = round(weighted_quantile(vals, weights, 0.10), 1)
                row["sunshine_pop_weighted_p50_h"] = round(weighted_quantile(vals, weights, 0.50), 1)
                row["sunshine_pop_weighted_p90_h"] = round(weighted_quantile(vals, weights, 0.90), 1)
                # Ignore cells with fewer than 10 estimated residents for the primary residential maximum,
                # but retain the all-population coverage in the raw cell count.
                primary = valid_pop & (pop >= 10)
                if not primary.any():
                    primary = valid_pop
                max_h = float(np.max(annual[primary]))
                row["sunshine_max_pop_ge10_h"] = round(max_h, 1)
                row["sunshine_pop_share_ge1800"] = round(
                    float(weights[vals >= SUNSHINE_LIMIT_H].sum() / weights.sum()), 4
                ) if weights.sum() > 0 else 0.0

                coverage = float(row["sunshine_population_coverage"] or 0)
                if coverage < 0.90:
                    row["sunshine_status"] = "PENDING_INCOMPLETE_POPULATION_SUNSHINE_COVERAGE"
                elif max_h < SUNSHINE_CLEAR_FAIL_H:
                    row["sunshine_status"] = "CLEAR_FAIL_BELOW_1800_GUARD75"
                elif max_h < SUNSHINE_LIMIT_H:
                    row["sunshine_status"] = "BOUNDARY_PENDING_1725_TO_1800"
                elif max_h < SUNSHINE_CLEAR_PASS_H:
                    row["sunshine_status"] = "PASS_NEAR_1800_REVIEW"
                else:
                    row["sunshine_status"] = "PASS_HAS_POPULATED_RESIDENTIAL_CELL_GE1875"
            else:
                row["sunshine_status"] = "PENDING_NO_VALID_POPULATED_SUNSHINE_CELLS"

            results[code] = row
            if i % 100 == 0 or i == total:
                write_json(progress_path, {
                    "run_id": RUN_ID,
                    "phase": "POPULATION_WEIGHTED_SUNSHINE_AND_SAMPLE_PREPARATION",
                    "processed_counties": i,
                    "total_counties": total,
                    "matched_geometry_counties": len(exact),
                    "inhabited_counties": sum(1 for x in results.values() if x["inhabited_grid_cells"] > 0),
                    "updated_at_utc": NOW(),
                })
                print(f"R1_SUNSHINE_PROGRESS {i}/{total}", flush=True)

        # Stage 1: one main populated-cell elevation point for each county.
        initial_points = []
        for code, points in point_candidates.items():
            if points:
                initial_points.append(points[0])
        altitude_query_meta.append(query_elevation(initial_points, "MAIN_POPULATED_CELL"))

        # Stage 2: only counties whose main populated cell is above 2,000m receive
        # additional spatially dispersed samples to detect lower-altitude exceptions.
        high_altitude_codes = set()
        for code, points in point_candidates.items():
            if points and points[0].get("elevation_m") is not None and points[0]["elevation_m"] > ALTITUDE_LIMIT_M:
                high_altitude_codes.add(code)
        extra_points = []
        for code in high_altitude_codes:
            extra_points.extend(point_candidates[code][1:])
        if extra_points:
            altitude_query_meta.append(query_elevation(extra_points, "HIGH_ALTITUDE_EXCEPTION_CHECK"))

        for code, row in results.items():
            points = point_candidates.get(code, [])
            elevations = [p["elevation_m"] for p in points if p.get("elevation_m") is not None]
            row["altitude_population_sample_count"] = len(elevations)
            row["altitude_min_sample_m"] = round(min(elevations), 1) if elevations else None
            row["altitude_max_sample_m"] = round(max(elevations), 1) if elevations else None
            if not points:
                if row["altitude_status"] == "PENDING":
                    row["altitude_status"] = "PENDING_NO_INHABITED_POPULATION_GRID"
            elif not elevations or len(elevations) != len(points):
                row["altitude_status"] = "PENDING_ELEVATION_API_INCOMPLETE"
            elif any(e <= ALTITUDE_LIMIT_M for e in elevations):
                row["altitude_status"] = "PASS_LOW_ALTITUDE_RESIDENTIAL_EXCEPTION_FOUND"
            elif len(points) == int(row["altitude_population_cells_total"]):
                row["altitude_status"] = "CONFIRMED_FAIL_ALL_INHABITED_GRID_CELLS_ABOVE_2000"
            elif len(elevations) >= MAX_ALTITUDE_SAMPLES:
                row["altitude_status"] = "STRONG_FAIL_10_SPATIAL_SAMPLES_ABOVE_2000_PENDING_LOCAL_EXCEPTION_AUDIT"
            else:
                row["altitude_status"] = "PENDING_HIGH_ALTITUDE_LOW_SAMPLE_COVERAGE"

            reasons = []
            if row["sunshine_status"] == "CLEAR_FAIL_BELOW_1800_GUARD75":
                reasons.append("SUNSHINE_CLEAR_FAIL")
            if row["altitude_status"] == "CONFIRMED_FAIL_ALL_INHABITED_GRID_CELLS_ABOVE_2000":
                reasons.append("ALTITUDE_ALL_INHABITED_CELLS_GT2000")
            row["R1_exclusion_reason"] = ";".join(reasons)
            if reasons:
                row["R1_next_round_status"] = "EXCLUDE_CONFIRMED"
            elif (
                str(row["sunshine_status"]).startswith("PENDING")
                or str(row["sunshine_status"]).startswith("BOUNDARY")
                or str(row["altitude_status"]).startswith("PENDING")
                or str(row["altitude_status"]).startswith("STRONG_FAIL")
            ):
                row["R1_next_round_status"] = "PENDING_CONTINUE"
            else:
                row["R1_next_round_status"] = "CARRY_FORWARD"

    all_rows = [results[r["code"]] for r in roster]
    excluded = [r for r in all_rows if r["R1_next_round_status"] == "EXCLUDE_CONFIRMED"]
    remaining = [r for r in all_rows if r["R1_next_round_status"] != "EXCLUDE_CONFIRMED"]
    pending = [r for r in all_rows if r["R1_next_round_status"] == "PENDING_CONTINUE"]
    for code, points in point_candidates.items():
        for p in points:
            altitude_point_rows.append({
                "code": code,
                "name": results[code]["name"],
                "sample_rank": p["sample_rank"],
                "longitude": p["longitude"],
                "latitude": p["latitude"],
                "population_grid_value": round(p["population_grid_value"], 3),
                "elevation_m": p.get("elevation_m"),
                "elevation_query_status": p.get("elevation_query_status", "NOT_QUERIED"),
                "elevation_source": ELEVATION_SOURCE,
            })

    fields = [
        "code", "name", "source_class", "asof", "geometry_status",
        "inhabited_grid_cells", "valid_sunshine_pop_cells", "population_grid_sum_relative",
        "sunshine_population_coverage", "sunshine_pop_weighted_mean_h",
        "sunshine_pop_weighted_p10_h", "sunshine_pop_weighted_p50_h", "sunshine_pop_weighted_p90_h",
        "sunshine_max_pop_ge10_h", "sunshine_pop_share_ge1800", "sunshine_status",
        "altitude_population_sample_count", "altitude_population_cells_total",
        "altitude_min_sample_m", "altitude_max_sample_m", "altitude_status",
        "altitude_source", "R1_next_round_status", "R1_exclusion_reason",
    ]
    write_csv(OUT / "R1_ALL_2847.csv", all_rows, fields)
    write_csv(OUT / "R1_REMAINING.csv", remaining, fields)
    write_csv(OUT / "R1_EXCLUDED.csv", excluded, fields)
    write_csv(OUT / "R1_PENDING.csv", pending, fields)
    write_csv(
        OUT / "R1_ALTITUDE_SAMPLE_POINTS.csv",
        altitude_point_rows,
        ["code", "name", "sample_rank", "longitude", "latitude", "population_grid_value",
         "elevation_m", "elevation_query_status", "elevation_source"],
    )

    summary = {
        "schema": "RETIREMENT_NATIONAL_FUNNEL_R1_V1",
        "run_id": RUN_ID,
        "status": "COMPLETED_WITH_PENDING" if len(all_rows) == 2847 else "PARTIAL",
        "started_at_utc": started,
        "completed_at_utc": NOW(),
        "input_count": len(roster),
        "geometry_exact_matches": len(exact),
        "geometry_pending": len(roster) - len(exact),
        "sunshine_clear_fail_count": sum(1 for r in all_rows if r["sunshine_status"] == "CLEAR_FAIL_BELOW_1800_GUARD75"),
        "sunshine_boundary_pending_count": sum(1 for r in all_rows if str(r["sunshine_status"]).startswith("BOUNDARY")),
        "sunshine_other_pending_count": sum(1 for r in all_rows if str(r["sunshine_status"]).startswith("PENDING")),
        "altitude_confirmed_fail_count": sum(1 for r in all_rows if r["altitude_status"] == "CONFIRMED_FAIL_ALL_INHABITED_GRID_CELLS_ABOVE_2000"),
        "altitude_strong_fail_pending_count": sum(1 for r in all_rows if str(r["altitude_status"]).startswith("STRONG_FAIL")),
        "altitude_low_altitude_exception_count": sum(1 for r in all_rows if r["altitude_status"] == "PASS_LOW_ALTITUDE_RESIDENTIAL_EXCEPTION_FOUND"),
        "confirmed_exclusion_count": len(excluded),
        "remaining_for_R2_count": len(remaining),
        "pending_continue_count": len(pending),
        "exclusion_rule": "A county-level unit is removed only when the population-grid sunshine estimate is clearly below 1,725h in all populated residential cells, or every inhabited population-grid cell has been sampled and is above 2,000m. Strong altitude samples with unsampled local cells remain pending and continue.",
        "sunshine_source": {
            "name": "ScienceDB V8 China 1km monthly mean sunshine percentage",
            "period": "1991-2020",
            "resolution": "1km",
            "variable": "sunp monthly mean percentage of sunshine",
            "conversion": "monthly sunp fraction × mean astronomical day length for that month × mean month days; summed over 12 months",
            "sunp_scale": sunp_scale_meta,
            "guard_band_hours": SUNSHINE_GUARD_H,
            "archive": sunp_download_meta,
            "license": "not independently confirmed on ScienceDB landing page; exploratory screening evidence",
        },
        "population_source": {
            "name": "WorldPop 2024 Global2 constrained population count grid",
            "resolution": "1km",
            "license": "CC BY 4.0",
            "download": pop_download_meta,
            "grid": population_grid_meta,
        },
        "elevation_source": {
            "name": ELEVATION_SOURCE,
            "resolution": "90m",
            "method": "main population cell first; only if >2,000m query up to 9 additional spatially dispersed populated cells to test lower-altitude exceptions",
            "api_batch_size": ELEVATION_BATCH_SIZE,
            "query_batches": altitude_query_meta,
            "attribution": "Copernicus DEM and Open-Meteo",
        },
        "geometry_source": geometry_meta,
        "raster": raster_meta,
        "outputs": {
            "all": "R1_ALL_2847.csv",
            "remaining": "R1_REMAINING.csv",
            "excluded": "R1_EXCLUDED.csv",
            "pending": "R1_PENDING.csv",
            "altitude_samples": "R1_ALTITUDE_SAMPLE_POINTS.csv",
        },
        "limitations": [
            "This is a first-pass nationwide funnel, not final city-level certification.",
            "The 2,847 roster and third-party county geometry remain provisional; 9 roster units have no exact code/name geometry match and are pending.",
            "Sunshine hours are derived from monthly mean sunshine percentage and astronomical day length, not directly summed from daily sunshine observations; the 75-hour guard band prevents borderline hard exclusions.",
            "Altitude samples are selected from populated 1km grid cells; counties with more than 10 inhabited cells and all 10 samples above 2,000m remain pending for local low-altitude exception checks.",
            "A county is an indexing unit, not a claim that its entire territory is one residential area. Separate valleys, basins, and populated settlements must remain independently evaluable.",
        ],
    }
    write_json(summary_path, summary)
    write_json(OUT / "R1_STATE.json", {
        "schema": "RETIREMENT_NATIONAL_FUNNEL_STATE_V1",
        "current_round": "R1",
        "current_round_status": summary["status"],
        "input_count": len(roster),
        "remaining_count": len(remaining),
        "excluded_count": len(excluded),
        "pending_continue_count": len(pending),
        "next_round_input": "R1_REMAINING.csv",
        "updated_at_utc": NOW(),
        "run_id": RUN_ID,
    })
    write_json(progress_path, {
        "run_id": RUN_ID,
        "phase": "COMPLETED",
        "processed_counties": len(roster),
        "confirmed_exclusions": len(excluded),
        "remaining_for_R2": len(remaining),
        "pending_continue": len(pending),
        "updated_at_utc": NOW(),
    })
    print(json.dumps({
        "status": summary["status"],
        "input": len(roster),
        "geometry_exact": len(exact),
        "sunshine_clear_fail": summary["sunshine_clear_fail_count"],
        "altitude_confirmed_fail": summary["altitude_confirmed_fail_count"],
        "confirmed_exclusions": len(excluded),
        "remaining_for_R2": len(remaining),
        "pending_continue": len(pending),
    }, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        OUT.mkdir(parents=True, exist_ok=True)
        write_json(OUT / "R1_SUMMARY.json", {
            "schema": "RETIREMENT_NATIONAL_FUNNEL_R1_V1",
            "run_id": RUN_ID,
            "status": "FAILED_OR_BLOCKED",
            "error_type": type(exc).__name__,
            "error": str(exc)[:3000],
            "formal_exclusions": 0,
            "remaining_for_R2": 2847,
            "updated_at_utc": NOW(),
        })
        raise
