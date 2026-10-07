"""Composite 1–5 cyclone risk for NIO coasts.

Not an IMD warning. Score combines intensity, intensification, coast proximity,
landfall chance, exposure, rain/surge proxies, and forecast uncertainty.
"""

from __future__ import annotations

from typing import Any

LEVELS = {
    1: {"name": "Minimal", "blurb": "Weak disturbance. Low organization. Low immediate threat."},
    2: {"name": "Low", "blurb": "Developing circulation and increasing convection. Some potential to strengthen."},
    3: {"name": "Moderate", "blurb": "Organized tropical system. Coastal areas should monitor. Strengthening possible."},
    4: {"name": "High", "blurb": "Strong tropical cyclone. Significant wind, rain, and surge potential for coasts."},
    5: {"name": "Extreme", "blurb": "Very severe cyclone. Destructive wind, surge, and flood potential. Official warnings take precedence."},
}

EXPOSURE = {
    "Odisha": 92,
    "West Bengal": 95,
    "Andhra": 88,
    "Tamil Nadu": 86,
    "Bangladesh": 98,
    "Gujarat": 84,
    "Maharashtra": 90,
    "Kerala": 80,
    "Karnataka": 72,
    "Goa": 70,
    "Sri Lanka": 78,
    "Andaman": 55,
    "Lakshadweep": 50,
    "Myanmar": 82,
    "Oman": 40,
    "Pakistan": 70,
    "Maldives": 48,
}


def _exposure(region: str | None) -> float:
    if not region:
        return 50.0
    for key, val in EXPOSURE.items():
        if key.lower() in region.lower():
            return float(val)
    return 58.0


def _clip(x: float, lo=0.0, hi=100.0) -> float:
    return max(lo, min(hi, x))


def assess_risk(
    *,
    wind_kt: float | None,
    d_wind_24h: float | None,
    dist2land_km: float | None,
    landfall_probability: float | None,
    landfall_region: str | None,
    spread_km_72: float | None,
    ri_probability: float | None,
) -> dict[str, Any]:
    w = float(wind_kt or 0.0)
    intensity = _clip(w / 1.15)
    ri = _clip(40.0 * float(ri_probability or 0.0) + max(0.0, float(d_wind_24h or 0.0)) * 1.6)
    if dist2land_km is None:
        coast = 35.0
    else:
        coast = _clip(100.0 - float(dist2land_km) / 7.5)
    land = _clip(100.0 * float(landfall_probability or 0.0))
    exposure = _exposure(landfall_region)
    rain = _clip(w * 1.05)
    surge = _clip(max(0.0, w - 28.0) * 1.35) * (0.35 if (dist2land_km or 400) > 280 else 1.0)
    spread = float(spread_km_72 or 80.0)
    if spread > 250:
        uncertainty = "High"
        # Wide cone: raise situational awareness, do not inflate catastrophe claims.
        unc_term = 18.0
        intensity *= 0.92
    elif spread > 120:
        uncertainty = "Medium"
        unc_term = 10.0
    else:
        uncertainty = "Low"
        unc_term = 4.0

    score = (
        0.26 * intensity
        + 0.12 * ri
        + 0.16 * coast
        + 0.14 * land
        + 0.10 * exposure
        + 0.10 * rain
        + 0.08 * surge
        + 0.04 * unc_term
    )
    score = round(_clip(score), 1)
    if score < 22:
        level = 1
    elif score < 38:
        level = 2
    elif score < 55:
        level = 3
    elif score < 73:
        level = 4
    else:
        level = 5
    meta = LEVELS[level]
    return {
        "score": score,
        "level": level,
        "name": meta["name"],
        "blurb": meta["blurb"],
        "uncertainty": uncertainty,
        "components": {
            "intensity": round(intensity, 1),
            "intensification": round(ri, 1),
            "coast_proximity": round(coast, 1),
            "landfall": round(land, 1),
            "population_exposure": round(exposure, 1),
            "rainfall_proxy": round(rain, 1),
            "surge_proxy": round(surge, 1),
            "uncertainty_term": round(unc_term, 1),
        },
        "disclaimer": (
            "Composite research score, not an IMD warning. Official bulletins take precedence."
        ),
    }
