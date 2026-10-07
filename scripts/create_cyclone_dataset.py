#!/usr/bin/env python3
"""Build the Indian Cyclone Dataset from IBTrACS North Indian Ocean.

Filters to the configurable NIO box, prefers IMD New Delhi wind/pressure,
splits at cyclone level by season (no leakage), and writes climatology tables.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.models.geo import bearing_deg, haversine_km, in_domain, sub_basin
from backend.models.imd import classify_wind_kt, from_ibtracs_grade

RAW = ROOT / "data" / "raw" / "ibtracs.NI.list.v04r01.csv"
OUT_DIR = ROOT / "data" / "processed"


def _f(v: str) -> float | None:
    v = (v or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _pick(*vals: float | None) -> float | None:
    for v in vals:
        if v is not None:
            return v
    return None


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        next(reader)  # units
        idx = {name: i for i, name in enumerate(header)}
        rows = []
        for parts in reader:
            if len(parts) < len(header):
                continue
            lat = _f(parts[idx["LAT"]])
            lon = _f(parts[idx["LON"]])
            if lat is None or lon is None:
                continue
            if not in_domain(lat, lon):
                continue
            iso = parts[idx["ISO_TIME"]].strip()
            wind = _pick(
                _f(parts[idx["NEWDELHI_WIND"]]),
                _f(parts[idx["WMO_WIND"]]),
                _f(parts[idx["USA_WIND"]]),
            )
            pres = _pick(
                _f(parts[idx["NEWDELHI_PRES"]]),
                _f(parts[idx["WMO_PRES"]]),
                _f(parts[idx["USA_PRES"]]),
            )
            grade = parts[idx["NEWDELHI_GRADE"]].strip() or None
            cls = from_ibtracs_grade(grade, wind)
            rows.append(
                {
                    "id": parts[idx["SID"]].strip(),
                    "season": int(_f(parts[idx["SEASON"]]) or 0),
                    "name": parts[idx["NAME"]].strip() or "UNNAMED",
                    "iso_time": iso,
                    "lat": lat,
                    "lon": lon,
                    "wind_kt": wind,
                    "pres_hpa": pres,
                    "grade": grade,
                    "category": cls.name,
                    "imd_code": cls.code,
                    "nature": parts[idx["NATURE"]].strip(),
                    "dist2land_km": _f(parts[idx["DIST2LAND"]]),
                    "storm_speed_kt": _f(parts[idx["STORM_SPEED"]]),
                    "storm_dir_deg": _f(parts[idx["STORM_DIR"]]),
                    "usa_rmw_nm": _f(parts[idx["USA_RMW"]]),
                    "subbasin": parts[idx["SUBBASIN"]].strip(),
                }
            )
    return rows


def group_storms(rows: list[dict]) -> list[dict]:
    by = defaultdict(list)
    for r in rows:
        by[r["id"]].append(r)
    storms = []
    for sid, pts in by.items():
        pts.sort(key=lambda p: p["iso_time"])
        t0 = datetime.fromisoformat(pts[0]["iso_time"].replace(" ", "T"))
        track = []
        for i, p in enumerate(pts):
            t = datetime.fromisoformat(p["iso_time"].replace(" ", "T"))
            hours = (t - t0).total_seconds() / 3600.0
            rmw = p["usa_rmw_nm"] * 1.852 if p["usa_rmw_nm"] else None
            heading = p["storm_dir_deg"]
            speed = p["storm_speed_kt"]
            if i > 0:
                heading = heading or bearing_deg(pts[i - 1]["lat"], pts[i - 1]["lon"], p["lat"], p["lon"])
                dt = max(1.0, hours - track[-1]["hours_from_start"])
                dist = haversine_km(pts[i - 1]["lat"], pts[i - 1]["lon"], p["lat"], p["lon"])
                speed = speed or dist / dt / 1.852
            track.append(
                {
                    "iso_time": p["iso_time"],
                    "hours_from_start": round(hours, 2),
                    "lat": round(p["lat"], 3),
                    "lon": round(p["lon"], 3),
                    "wind_kt": p["wind_kt"],
                    "pres_hpa": p["pres_hpa"],
                    "category": p["category"],
                    "imd_code": p["imd_code"],
                    "dist2land_km": p["dist2land_km"],
                    "heading_deg": None if heading is None else round(heading, 1),
                    "speed_kt": None if speed is None else round(speed, 2),
                    "radius_km": None if rmw is None else round(rmw, 1),
                    "sub_basin": "AS" if (p["subbasin"] == "AS" or p["lon"] < 80) else "BB",
                }
            )
        winds = [p["wind_kt"] for p in pts if p["wind_kt"] is not None]
        pres = [p["pres_hpa"] for p in pts if p["pres_hpa"] is not None]
        peak = max(winds) if winds else None
        season = pts[0]["season"]
        if season <= 2016:
            split = "train"
        elif season <= 2019:
            split = "valid"
        else:
            split = "test"
        genesis = track[0]
        land_hint = None
        for p in track:
            if p["dist2land_km"] is not None and p["dist2land_km"] == 0:
                land_hint = {"lat": p["lat"], "lon": p["lon"], "iso_time": p["iso_time"]}
                break
        storms.append(
            {
                "id": sid,
                "name": pts[0]["name"],
                "season": season,
                "start_time": pts[0]["iso_time"],
                "end_time": pts[-1]["iso_time"],
                "genesis_basin": sub_basin(genesis["lon"]),
                "sub_basin": sub_basin(sum(p["lon"] for p in track) / len(track)),
                "peak_wind_kt": peak,
                "min_pres_hpa": min(pres) if pres else None,
                "peak_category": classify_wind_kt(peak).name if peak else None,
                "peak_month": int(pts[0]["iso_time"][5:7]),
                "split": split,
                "satellite_era": season >= 1980,
                "landfall_hint": land_hint,
                "track": track,
                "notes": "Positions/intensity from IBTrACS v04r01 (IMD New Delhi preferred).",
            }
        )
    storms.sort(key=lambda s: (s["season"], s["start_time"]))
    return storms


def climatology(storms: list[dict]) -> dict:
    cells: dict[str, dict] = {}
    genesis = []
    for s in storms:
        if not s["satellite_era"] or s["split"] != "train":
            continue
        tr = s["track"]
        if tr:
            genesis.append(
                {
                    "lat": tr[0]["lat"],
                    "lon": tr[0]["lon"],
                    "month": int(tr[0]["iso_time"][5:7]),
                    "weight": 1.0,
                    "basin": s["genesis_basin"],
                }
            )
        for i in range(1, len(tr)):
            a, b = tr[i - 1], tr[i]
            dt = max(1.0, b["hours_from_start"] - a["hours_from_start"])
            if dt > 12:
                continue
            heading = bearing_deg(a["lat"], a["lon"], b["lat"], b["lon"])
            speed = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) / dt / 1.852
            d_wind = 0.0
            if a.get("wind_kt") and b.get("wind_kt"):
                d_wind = (b["wind_kt"] - a["wind_kt"]) * (6 / dt)
            month = int(a["iso_time"][5:7])
            lat_b = int(math.floor(a["lat"] / 2.0) * 2)
            lon_b = int(math.floor(a["lon"] / 2.0) * 2)
            key = f"{month}:{lat_b}:{lon_b}"
            rec = cells.setdefault(key, {"n": 0, "heading_x": 0.0, "heading_y": 0.0, "speed": 0.0, "d_wind": 0.0})
            rec["n"] += 1
            rec["heading_x"] += math.cos(math.radians(heading))
            rec["heading_y"] += math.sin(math.radians(heading))
            rec["speed"] += speed
            rec["d_wind"] += d_wind
    out_cells = {}
    for k, rec in cells.items():
        n = rec["n"]
        h = (math.degrees(math.atan2(rec["heading_y"] / n, rec["heading_x"] / n)) + 360) % 360
        out_cells[k] = {
            "n": n,
            "heading": round(h, 2),
            "speed_kt": round(rec["speed"] / n, 3),
            "d_wind": round(rec["d_wind"] / n, 3),
        }
    return {
        "built_from": "train split, satellite era >= 1980",
        "cells": out_cells,
        "genesis": genesis,
    }


def main():
    if not RAW.exists():
        raise SystemExit(f"Missing {RAW}; run scripts/download_data.py")
    rows = load_rows(RAW)
    storms = group_storms(rows)
    # Keep a usable catalog: satellite-era storms with >=4 points, plus famous pre-1980 if named? Keep 1980+ primarily.
    catalog_storms = [s for s in storms if s["satellite_era"] and len(s["track"]) >= 4]
    climo = climatology(catalog_storms)
    meta = {
        "dataset": "Indian Cyclone Dataset",
        "source": "IBTrACS v04r01 NI basin, cropped to 0-30N, 50-110E",
        "doi": "10.25921/82ty-9e16",
        "license": "IBTrACS may be redistributed and used without restriction; cite NOAA/NCEI.",
        "n_storms": len(catalog_storms),
        "n_points": sum(len(s["track"]) for s in catalog_storms),
        "splits": {
            "train": sum(1 for s in catalog_storms if s["split"] == "train"),
            "valid": sum(1 for s in catalog_storms if s["split"] == "valid"),
            "test": sum(1 for s in catalog_storms if s["split"] == "test"),
        },
        "domain": {"lat": [0, 30], "lon": [50, 110]},
        "neural_models_trained": False,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"meta": meta, "storms": catalog_storms}
    (OUT_DIR / "indian_cyclone_catalog.json").write_text(json.dumps(payload))
    (OUT_DIR / "motion_climatology.json").write_text(json.dumps(climo))
    (OUT_DIR / "dataset_meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
