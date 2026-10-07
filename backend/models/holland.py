"""Holland (1980) parametric tropical cyclone wind/pressure field.

Used only as a visualization / diagnostic kernel around a best-track center.
This is not a substitute for reanalysis or satellite winds.
"""

from __future__ import annotations

import math

from .geo import haversine_km, bearing_deg


def radius_max_wind_km(wind_kt: float, lat: float) -> float:
    # Willoughby & Rahn-inspired compact RMW for NIO prototype.
    w = max(20.0, wind_kt)
    return max(18.0, min(80.0, 51.6 * math.exp(-0.0223 * w) + 0.8 * abs(lat)))


def holland_b(wind_kt: float, pmin: float, penv: float = 1010.0) -> float:
    rho = 1.15
    vmax = wind_kt * 0.514444
    dp = max(4.0, penv - pmin) * 100.0
    return min(2.5, max(1.0, rho * vmax * vmax / dp))


def wind_kt_at(lat: float, lon: float, clat: float, clon: float, vmax_kt: float, pmin: float) -> float:
    r = haversine_km(clat, clon, lat, lon)
    rmw = radius_max_wind_km(vmax_kt, clat)
    if r < 1.0:
        return vmax_kt * 0.25
    b = holland_b(vmax_kt, pmin)
    x = (rmw / max(r, 1.0)) ** b
    return float(vmax_kt * math.sqrt(x * math.exp(1.0 - x)))


def pressure_hpa_at(lat: float, lon: float, clat: float, clon: float, vmax_kt: float, pmin: float, penv: float = 1010.0) -> float:
    r = haversine_km(clat, clon, lat, lon)
    rmw = radius_max_wind_km(vmax_kt, clat)
    b = holland_b(vmax_kt, pmin)
    x = (rmw / max(r, 1.0)) ** b
    return float(pmin + (penv - pmin) * math.exp(-x))


def cyclonic_uv(lat: float, lon: float, clat: float, clon: float, speed_kt: float) -> tuple[float, float]:
    """Northern-hemisphere cyclonic flow (inward-inflow ~15%)."""
    brng = bearing_deg(clat, clon, lat, lon)
    tang = (brng + 90.0) % 360.0
    inflow = (tang + 20.0) % 360.0
    rad = math.radians(inflow)
    u = speed_kt * math.sin(rad)
    v = speed_kt * math.cos(rad)
    return u, v
