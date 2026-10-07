"""Parametric weather layers for globe visualization.

These fields are NOT satellite, ERA5, or in-situ observations. They combine:
- Holland vortex around the selected center
- Seasonal monsoon / SST climatology sketches for the NIO box
"""

from __future__ import annotations

import math
from typing import Any

from backend.models.geo import haversine_km
from backend.models.holland import cyclonic_uv, pressure_hpa_at, wind_kt_at

LATS = list(range(0, 31, 2))
LONS = list(range(50, 111, 2))


def _sst_c(lat: float, lon: float, month: int) -> float:
    # Warm pool sketch: Bay of Bengal / SE Arabian Sea.
    base = 28.4 - 0.07 * abs(lat - 8) + 0.4 * math.sin((month - 5) / 12 * 2 * math.pi)
    if 80 <= lon <= 95:
        base += 0.6
    if lon < 65:
        base -= 0.8
    return round(base, 2)


def _temp_c(lat: float, month: int, storm_boost: float) -> float:
    return round(27.5 - 0.18 * lat + 2.2 * math.sin((month - 4) / 12 * 2 * math.pi) - storm_boost * 3.5, 2)


def weather_grid(center: dict[str, Any], month: int) -> dict[str, Any]:
    clat, clon = center["lat"], center["lon"]
    vmax = center.get("wind_kt") or 40.0
    pmin = center.get("pres_hpa") or 990.0
    cells = []
    for lat in LATS:
        for lon in LONS:
            d = haversine_km(clat, clon, lat, lon)
            w = wind_kt_at(lat, lon, clat, clon, vmax, pmin)
            # add weak monsoon background
            bg = 8.0 if month in (6, 7, 8, 9) else 5.0
            u_s, v_s = cyclonic_uv(lat, lon, clat, clon, w)
            u = u_s + bg * 0.4
            v = v_s + (4.0 if month in (6, 7, 8) else -1.0)
            pr = pressure_hpa_at(lat, lon, clat, clon, vmax, pmin)
            rain = max(0.0, (w / max(vmax, 1)) ** 2 * math.exp(-(((d - 90) / 70) ** 2)) * 28)
            sst = _sst_c(lat, lon, month)
            hum = min(98.0, 62 + 28 * math.exp(-d / 280) + (2 if lon > 80 else 0))
            ctt = 12 - 70 * math.exp(-((d - 55) / 80) ** 2) - (8 if d < 25 else 0)
            cells.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "wind_kt": round(w + bg * 0.2, 1),
                    "u_kt": round(u, 2),
                    "v_kt": round(v, 2),
                    "mslp_hpa": round(pr, 1),
                    "temp_c": _temp_c(lat, month, math.exp(-d / 120)),
                    "rh": round(hum, 1),
                    "precip_mm_hr": round(rain, 2),
                    "sst_c": sst,
                    "ctt_c": round(ctt, 1),
                }
            )
    return {
        "kind": "parametric_visualization",
        "disclaimer": (
            "Visualization fields from a Holland vortex + seasonal climatology sketch. "
            "Not ERA5, INSAT, or live satellite data."
        ),
        "center": {"lat": clat, "lon": clon},
        "shape": [len(LATS), len(LONS)],
        "lats": LATS,
        "lons": LONS,
        "cells": cells,
    }
