"""CLIPER-inspired persistence + analog ensemble for NIO cyclone tracks.

This is a statistical baseline, not a trained neural weather model.
Intensity uses persistence blended with basin-month wind change climatology.
"""

from __future__ import annotations

import math
import random
from typing import Any

from backend.models.geo import (
    bearing_deg,
    compass_label,
    destination_point,
    haversine_km,
    knots_to_kmh,
    mean_track,
    median_track,
    spread_km,
    sub_basin,
)
from backend.models.imd import classify_wind_kt, rapid_intensification, rapid_weakening
from backend.services.catalog import load_climatology, storms
from backend.services.landfall import landfall_from_track

LEAD_HOURS = [6, 12, 24, 48, 72, 96, 120]


def _motion(track: list[dict[str, Any]], idx: int) -> tuple[float, float]:
    if idx <= 0:
        return 280.0, 12.0
    a, b = track[idx - 1], track[idx]
    dist = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
    hours = max(1.0, (b["hours_from_start"] - a["hours_from_start"]) or 6)
    speed_kmh = dist / hours * 1.0
    speed_kt = speed_kmh / 1.852
    brng = bearing_deg(a["lat"], a["lon"], b["lat"], b["lon"])
    return brng, max(2.0, min(30.0, speed_kt))


def _climo_cell(lat: float, lon: float, month: int) -> dict[str, float] | None:
    climo = load_climatology()
    lat_b = int(math.floor(lat / 2.0) * 2)
    lon_b = int(math.floor(lon / 2.0) * 2)
    key = f"{month}:{lat_b}:{lon_b}"
    return climo.get("cells", {}).get(key)


def _step(lat, lon, heading, speed_kt, hours, jitter_deg=0.0, jitter_spd=0.0, rng=None):
    rng = rng or random.Random(0)
    h = heading + rng.gauss(0, jitter_deg)
    s = max(1.0, speed_kt + rng.gauss(0, jitter_spd))
    return destination_point(lat, lon, h, s * 1.852 * hours)


def _blend_heading(obs_h: float, climo_h: float, w_climo: float) -> float:
    # circular blend
    o = math.radians(obs_h)
    c = math.radians(climo_h)
    x = (1 - w_climo) * math.cos(o) + w_climo * math.cos(c)
    y = (1 - w_climo) * math.sin(o) + w_climo * math.sin(c)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def analog_storms(storm: dict[str, Any], now_idx: int, k: int = 8) -> list[dict[str, Any]]:
    p = storm["track"][now_idx]
    month = int(p["iso_time"][5:7])
    basin = p.get("sub_basin") or sub_basin(p["lon"])
    scored = []
    for other in storms():
        if other["id"] == storm["id"]:
            continue
        if other.get("peak_month") != month and int(other["start_time"][5:7]) != month:
            continue
        if other.get("sub_basin") not in (basin, "NI"):
            # still allow if genesis basin matches
            if other.get("genesis_basin") != basin:
                continue
        # analog at similar latitude
        mid = other["track"][min(len(other["track"]) // 2, len(other["track"]) - 1)]
        d = abs(mid["lat"] - p["lat"]) + 0.4 * abs(mid["lon"] - p["lon"])
        scored.append((d, other))
    scored.sort(key=lambda x: x[0])
    return [s for _, s in scored[:k]]


def _intensity_step(wind, pres, d_wind, hours=6):
    nw = max(15.0, min(140.0, wind + d_wind * (hours / 6.0)))
    # wind-pressure (Atkinson-Holliday-like, tuned loosely)
    npres = 1010.0 - (nw / 3.92) ** 1.644 if nw else pres
    if pres:
        npres = 0.7 * npres + 0.3 * (pres - d_wind * 0.9)
    return nw, float(npres)


def forecast_storm(
    storm: dict[str, Any],
    now_idx: int,
    ensemble_size: int = 21,
    model: str = "indian_analog_ensemble",
) -> dict[str, Any]:
    track = storm["track"]
    now_idx = max(1, min(now_idx, len(track) - 1))
    now = track[now_idx]
    heading, speed = _motion(track, now_idx)
    month = int(now["iso_time"][5:7])
    cell = _climo_cell(now["lat"], now["lon"], month)
    if cell:
        heading = _blend_heading(heading, cell["heading"], 0.35)
        speed = 0.65 * speed + 0.35 * cell["speed_kt"]
    if model == "indian_analog_ensemble":
        analogs = analog_storms(storm, now_idx, k=6)
        ah, asp, n = 0.0, 0.0, 0
        for other in analogs:
            j = min(now_idx, len(other["track"]) - 1)
            h, s = _motion(other["track"], j)
            ah += h
            asp += s
            n += 1
        if n:
            heading = _blend_heading(heading, ah / n, 0.25)
            speed = 0.75 * speed + 0.25 * (asp / n)

    wind = now.get("wind_kt") or 35.0
    pres = now.get("pres_hpa") or 996.0
    d_wind = 0.0
    if now_idx >= 1 and track[now_idx - 1].get("wind_kt") and now.get("wind_kt"):
        dt = max(6, track[now_idx]["hours_from_start"] - track[now_idx - 1]["hours_from_start"])
        d_wind = (now["wind_kt"] - track[now_idx - 1]["wind_kt"]) * (6 / dt)

    if cell and cell.get("d_wind") is not None:
        d_wind = 0.6 * d_wind + 0.4 * cell["d_wind"]

    rng = random.Random(hash((storm["id"], now_idx, model)) & 0xFFFFFFFF)
    members = []
    for m in range(ensemble_size):
        lat, lon = now["lat"], now["lon"]
        h, s = heading, speed
        w, pr = wind, pres
        dw = d_wind
        pts = [
            {
                "lead_hours": 0,
                "lat": lat,
                "lon": lon,
                "wind_kt": w,
                "pres_hpa": pr,
                "category": classify_wind_kt(w).name,
            }
        ]
        for lead in range(6, 121, 6):
            jdeg = 7.5 if model != "persistence" else 0.4
            jspd = 2.2 if model != "persistence" else 0.2
            if model == "persistence":
                lat, lon = _step(lat, lon, heading, speed, 6, 0.3, 0.1, rng)
            else:
                lat, lon = _step(lat, lon, h, s, 6, jdeg, jspd, rng)
                h = (h + rng.gauss(0, 3.5)) % 360
                s = max(2.0, s + rng.gauss(0, 0.6))
                # recurvature bias in Bay of Bengal north of 18N
                if lon >= 80 and lat > 17:
                    h = _blend_heading(h, 10.0, 0.08)
            # land decay if near coast (dist2land of now as proxy + lat)
            if lat > 22:
                dw = min(dw, -1.5)
            w, pr = _intensity_step(w, pr, dw + rng.gauss(0, 1.1), 6)
            if lead in LEAD_HOURS or lead % 6 == 0:
                pts.append(
                    {
                        "lead_hours": lead,
                        "lat": round(lat, 3),
                        "lon": round(lon, 3),
                        "wind_kt": round(w, 1),
                        "pres_hpa": round(pr, 1),
                        "category": classify_wind_kt(w).name,
                    }
                )
        members.append({"member": m, "track": [p for p in pts if p["lead_hours"] in [0, *LEAD_HOURS] or p["lead_hours"] % 12 == 0]})

    # trim member tracks to 0 + LEAD_HOURS
    def trim(mem):
        keep = {0, *LEAD_HOURS}
        return [p for p in mem if p["lead_hours"] in keep]

    trimmed = [trim(m["track"]) for m in members]
    coords = [[(p["lat"], p["lon"]) for p in t] for t in trimmed]
    mean_xy = mean_track(coords)
    med_xy = median_track(coords)
    mean_pts = []
    for i, lead in enumerate([0, *LEAD_HOURS]):
        winds = [t[i]["wind_kt"] for t in trimmed]
        pres = [t[i]["pres_hpa"] for t in trimmed]
        mean_pts.append(
            {
                "lead_hours": lead,
                "lat": round(mean_xy[i][0], 3),
                "lon": round(mean_xy[i][1], 3),
                "wind_kt": round(sum(winds) / len(winds), 1),
                "pres_hpa": round(sum(pres) / len(pres), 1),
                "category": classify_wind_kt(sum(winds) / len(winds)).name,
                "spread_km": round(spread_km(c[i] for c in coords), 1),
            }
        )

    # RI/RW from ensemble 24h wind change
    d24 = [t[3]["wind_kt"] - t[0]["wind_kt"] for t in trimmed if len(t) > 3]
    ri = sum(1 for d in d24 if d >= 30) / max(1, len(d24))
    rw = sum(1 for d in d24 if d <= -30) / max(1, len(d24))

    fut = [
        {
            "lat": p["lat"],
            "lon": p["lon"],
            "wind_kt": p["wind_kt"],
            "pres_hpa": p["pres_hpa"],
            "dist2land_km": None,
        }
        for p in mean_pts
    ]
    land = landfall_from_track(fut, 0)

    cone = []
    for i, lead in enumerate([0, *LEAD_HOURS]):
        cone.append(
            {
                "lead_hours": lead,
                "lat": mean_pts[i]["lat"],
                "lon": mean_pts[i]["lon"],
                "radius_km": round(18 + lead * 1.15 + mean_pts[i]["spread_km"], 1),
            }
        )

    trained = model in {"persistence", "climatology_steering", "indian_analog_ensemble"}
    return {
        "storm_id": storm["id"],
        "model": model,
        "model_trained": trained,
        "disclaimer": (
            "Statistical baseline (persistence + NIO motion climatology + analog ensemble). "
            if trained
            else "Model not trained yet. Neural weights are random; do not use these numbers as skill."
        )
        + " Not an official IMD forecast.",
        "now": {
            "iso_time": now["iso_time"],
            "lat": now["lat"],
            "lon": now["lon"],
            "wind_kt": now.get("wind_kt"),
            "pres_hpa": now.get("pres_hpa"),
            "category": classify_wind_kt(now.get("wind_kt")).name,
            "heading_deg": round(heading, 1),
            "heading": compass_label(heading),
            "speed_kt": round(speed, 1),
            "speed_kmh": round(knots_to_kmh(speed), 1),
        },
        "mean_track": mean_pts,
        "median_track": [
            {"lead_hours": [0, *LEAD_HOURS][i], "lat": round(xy[0], 3), "lon": round(xy[1], 3)}
            for i, xy in enumerate(med_xy)
        ],
        "ensemble": [{"member": i, "track": trimmed[i]} for i in range(min(ensemble_size, len(trimmed)))],
        "uncertainty_cone": cone,
        "rapid_intensification_probability": round(ri, 3),
        "rapid_weakening_probability": round(rw, 3),
        "landfall": land,
        "formation": formation_probabilities(now["lat"], now["lon"], month),
    }


def formation_probabilities(lat: float, lon: float, month: int) -> dict[str, Any]:
    """Climatological genesis density — not a trained cyclogenesis detector."""
    climo = load_climatology()
    genesis = climo.get("genesis", [])
    scores = {24: 0.0, 48: 0.0, 72: 0.0}
    basin = sub_basin(lon)
    for g in genesis:
        if g["month"] != month:
            continue
        d = haversine_km(lat, lon, g["lat"], g["lon"])
        if d > 400:
            continue
        w = math.exp(-((d / 180.0) ** 2))
        for h in scores:
            scores[h] += w * g["weight"] * (0.55 + 0.15 * (h / 24))
    # normalize roughly against peak cell
    peak = max((x["weight"] for x in genesis if x["month"] == month), default=1.0)
    out = {}
    for h, s in scores.items():
        p = 1 - math.exp(-s / max(0.4, peak * 3.5))
        if basin == "AS" and month not in (5, 6, 10, 11, 12):
            p *= 0.65
        if basin == "BB" and month not in (4, 5, 6, 9, 10, 11, 12):
            p *= 0.7
        out[str(h)] = round(min(0.92, max(0.02, p)), 3)
    return {
        "window_hours": out,
        "method": "month-basin genesis climatology from IBTrACS NI (satellite era)",
        "disclaimer": "Climatological formation probability, not a trained AI cyclogenesis model.",
    }


def detect_snapshot(storm: dict[str, Any], now_idx: int) -> dict[str, Any]:
    p = storm["track"][now_idx]
    wind = p.get("wind_kt") or 0.0
    cls = classify_wind_kt(wind)
    # Probability is a calibrated display score from intensity, not a trained detector.
    if wind >= 34:
        prob = 0.82 + min(0.15, (wind - 34) / 400)
    elif wind >= 17:
        prob = 0.45 + (wind - 17) / 50
    else:
        prob = 0.12
    rmw = max(40.0, 220.0 - wind)
    return {
        "cyclone_probability": round(min(0.97, prob), 3),
        "latitude": p["lat"],
        "longitude": p["lon"],
        "max_wind_speed": wind,
        "central_pressure": p.get("pres_hpa"),
        "radius_km": round(rmw, 1),
        "imd_class": cls.name,
        "imd_code": cls.code,
        "method": "IBTrACS best-track center + IMD wind thresholds (not a trained detector)",
        "disclaimer": "Detection uses historical best-track positions. A neural detector has not been trained yet.",
    }


def verify_track_error(storm: dict[str, Any], now_idx: int, forecast: dict[str, Any]) -> dict[str, Any]:
    """Haversine error vs remaining best track when replaying history."""
    track = storm["track"]
    now_hours = track[now_idx]["hours_from_start"]
    errors = {}
    for p in forecast["mean_track"]:
        lead = p["lead_hours"]
        target_h = now_hours + lead
        # nearest observed
        obs = min(track, key=lambda q: abs(q["hours_from_start"] - target_h))
        if abs(obs["hours_from_start"] - target_h) > 4:
            errors[str(lead)] = None
            continue
        errors[str(lead)] = round(haversine_km(p["lat"], p["lon"], obs["lat"], obs["lon"]), 1)
    return {
        "metric": "haversine_km",
        "errors": errors,
        "note": "Computed only when a best-track observation exists near that lead time.",
    }
