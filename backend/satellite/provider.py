"""Satellite data provider abstraction.

Live INSAT/MOSDAC granules are not bundled. The mock provider synthesizes
diagnostic brightness-temperature-like fields from a Holland cloud-top kernel
so the UI and pipeline can be demonstrated. Fields are labeled synthetic.
"""

from __future__ import annotations

import math
from typing import Any, Protocol

from backend.models.geo import haversine_km
from backend.models.holland import holland_b, radius_max_wind_km

IMAGERY = [
    {"id": "visible", "name": "Visible (synthetic)"},
    {"id": "ir", "name": "Infrared (synthetic)"},
    {"id": "wv", "name": "Water vapor (synthetic)"},
    {"id": "eir", "name": "Enhanced IR (synthetic)"},
    {"id": "ctt", "name": "Cloud-top temperature (synthetic)"},
    {"id": "multi", "name": "Multi-spectral composite (synthetic)"},
]

REGIONS = [
    {"id": "bob", "name": "Bay of Bengal", "lat": [5, 24], "lon": [80, 100]},
    {"id": "as", "name": "Arabian Sea", "lat": [5, 26], "lon": [50, 78]},
    {"id": "nio", "name": "North Indian Ocean", "lat": [0, 30], "lon": [50, 110]},
    {"id": "india", "name": "India & coasts", "lat": [6, 28], "lon": [68, 92]},
]


class SatelliteDataProvider(Protocol):
    def frame(self, center: dict[str, Any], imagery: str, region: str) -> dict[str, Any]: ...


def _ctt(lat: float, lon: float, clat: float, clon: float, vmax: float, imagery: str) -> float:
    d = haversine_km(clat, clon, lat, lon)
    rmw = radius_max_wind_km(vmax, clat)
    b = holland_b(vmax, 980.0)
    eyewall = math.exp(-(((d - rmw) / max(18.0, rmw * 0.55)) ** 2))
    cdo = math.exp(-((d / max(40.0, rmw * 1.8)) ** 2))
    band = 0.55 * math.exp(-(((d - 160) / 70) ** 2)) * (0.6 + 0.4 * math.sin(math.atan2(lat - clat, lon - clon) * 3 + d / 40))
    cold = -78 * eyewall - 52 * cdo - 28 * band
    if imagery == "visible":
        return max(0.0, min(1.0, 0.15 + 0.85 * (eyewall + 0.7 * cdo + band)))
    if imagery == "wv":
        return -40 + cold * 0.45
    if imagery == "eir":
        return cold * 1.15
    return cold  # ir / ctt / multi


class MockSatelliteProvider:
    def frame(self, center: dict[str, Any], imagery: str, region: str) -> dict[str, Any]:
        box = next((r for r in REGIONS if r["id"] == region), REGIONS[2])
        clat, clon = center["lat"], center["lon"]
        # Crop around the centre so the UI gets a satellite-style window, not a 60° ocean.
        half = 8.0
        lat0 = max(box["lat"][0], clat - half)
        lat1 = min(box["lat"][1], clat + half)
        lon0 = max(box["lon"][0], clon - half)
        lon1 = min(box["lon"][1], clon + half)
        if lat1 - lat0 < 4:
            lat0, lat1 = box["lat"][0], min(box["lat"][0] + 12, box["lat"][1])
        if lon1 - lon0 < 4:
            lon0, lon1 = box["lon"][0], min(box["lon"][0] + 12, box["lon"][1])
        step = 0.75
        nlat = max(2, int((lat1 - lat0) / step) + 1)
        nlon = max(2, int((lon1 - lon0) / step) + 1)
        lats = [lat0 + i * step for i in range(nlat)]
        lons = [lon0 + j * step for j in range(nlon)]
        vmax = float(center.get("wind_kt") or 35)
        values: list[list[float]] = []
        coldest = 40.0
        for lat in lats:
            row = []
            for lon in lons:
                v = _ctt(lat, lon, clat, clon, vmax, imagery)
                row.append(round(v, 2))
                if imagery not in {"visible"} and v < coldest:
                    coldest = v
            values.append(row)
        return {
            "provider": "mock_parametric",
            "live": False,
            "imagery": imagery,
            "region": region,
            "lats": lats,
            "lons": lons,
            "values": values,
            "units": "cloud_fraction" if imagery == "visible" else "C_proxy",
            "coldest": None if imagery == "visible" else round(coldest, 1),
            "disclaimer": (
                "Synthetic diagnostic field from a parametric cloud-top kernel around the "
                "best-track centre. Not INSAT, MOSDAC, or any live satellite granule."
            ),
        }


def default_provider() -> MockSatelliteProvider:
    return MockSatelliteProvider()
