"""Geographic helpers for the North Indian Ocean domain."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def destination_point(lat: float, lon: float, bearing_deg: float, distance_km: float) -> tuple[float, float]:
    brng = math.radians(bearing_deg)
    phi1 = math.radians(lat)
    lam1 = math.radians(lon)
    ang = distance_km / EARTH_RADIUS_KM
    phi2 = math.asin(math.sin(phi1) * math.cos(ang) + math.cos(phi1) * math.sin(ang) * math.cos(brng))
    lam2 = lam1 + math.atan2(
        math.sin(brng) * math.sin(ang) * math.cos(phi1),
        math.cos(ang) - math.sin(phi1) * math.sin(phi2),
    )
    lon2 = (math.degrees(lam2) + 540) % 360 - 180
    return math.degrees(phi2), lon2


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def compass_label(bearing: float) -> str:
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return dirs[int((bearing + 11.25) / 22.5) % 16]


def in_domain(lat: float, lon: float, lat_min=0.0, lat_max=30.0, lon_min=50.0, lon_max=110.0) -> bool:
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def sub_basin(lon: float) -> str:
    return "AS" if lon < 80.0 else "BB"


def knots_to_kmh(kts: float) -> float:
    return kts * 1.852


def kmh_to_knots(kmh: float) -> float:
    return kmh / 1.852


def mean_track(tracks: Sequence[Sequence[tuple[float, float]]]) -> list[tuple[float, float]]:
    if not tracks:
        return []
    n = min(len(t) for t in tracks)
    out = []
    for i in range(n):
        lat = sum(t[i][0] for t in tracks) / len(tracks)
        lon = sum(t[i][1] for t in tracks) / len(tracks)
        out.append((lat, lon))
    return out


def median_track(tracks: Sequence[Sequence[tuple[float, float]]]) -> list[tuple[float, float]]:
    if not tracks:
        return []
    n = min(len(t) for t in tracks)
    out = []
    for i in range(n):
        lats = sorted(t[i][0] for t in tracks)
        lons = sorted(t[i][1] for t in tracks)
        m = len(lats) // 2
        if len(lats) % 2:
            out.append((lats[m], lons[m]))
        else:
            out.append(((lats[m - 1] + lats[m]) / 2, (lons[m - 1] + lons[m]) / 2))
    return out


def spread_km(points: Iterable[tuple[float, float]]) -> float:
    pts = list(points)
    if len(pts) < 2:
        return 0.0
    clat = sum(p[0] for p in pts) / len(pts)
    clon = sum(p[1] for p in pts) / len(pts)
    return sum(haversine_km(clat, clon, p[0], p[1]) for p in pts) / len(pts)
