"""Coastal landfall risk from a forecast track vs a simplified South Asia shoreline.

Polygons are coarse boxes for labeling, not cadastral coastlines.
Predictions are probabilistic estimates, never guarantees.
"""

from __future__ import annotations

from typing import Any

from backend.models.geo import haversine_km, in_domain

# Approximate coastal landmarks (lat, lon, label, basin)
COAST_POINTS: list[tuple[float, float, str, str]] = [
    (21.6, 60.0, "Oman (Arabian Sea coast)", "AS"),
    (25.0, 62.3, "Pakistan — Makran / Sindh", "AS"),
    (23.0, 68.5, "Gujarat — Kutch / Saurashtra", "AS"),
    (21.1, 72.2, "Gujarat — Gulf of Khambhat", "AS"),
    (19.0, 72.8, "Maharashtra — Mumbai coast", "AS"),
    (15.5, 73.8, "Goa / north Karnataka", "AS"),
    (13.0, 74.8, "Karnataka — Mangaluru", "AS"),
    (10.0, 76.2, "Kerala", "AS"),
    (8.5, 76.9, "South Kerala / Kanyakumari", "AS"),
    (6.9, 79.9, "Sri Lanka — west", "BB"),
    (8.2, 81.4, "Sri Lanka — east", "BB"),
    (4.2, 73.5, "Maldives", "AS"),
    (10.6, 72.6, "Lakshadweep", "AS"),
    (11.7, 79.8, "Tamil Nadu — Coromandel", "BB"),
    (14.4, 80.2, "Andhra Pradesh — south", "BB"),
    (16.5, 82.2, "Andhra Pradesh — Godavari", "BB"),
    (17.7, 83.3, "Andhra Pradesh — Visakhapatnam", "BB"),
    (19.8, 85.8, "Odisha — Gopalpur / Puri", "BB"),
    (20.3, 86.7, "Odisha — Paradip", "BB"),
    (21.5, 87.0, "Odisha / West Bengal — Digha", "BB"),
    (21.8, 88.2, "West Bengal — Sundarbans", "BB"),
    (22.4, 91.8, "Bangladesh — Chattogram", "BB"),
    (20.8, 92.3, "Bangladesh / Myanmar — Cox's Bazar", "BB"),
    (16.8, 94.4, "Myanmar — Ayeyarwady", "BB"),
    (11.7, 92.7, "Andaman and Nicobar Islands", "BB"),
]


def nearest_coast(lat: float, lon: float) -> tuple[float, float, str, str, float]:
    best = None
    best_d = 1e9
    for clat, clon, name, basin in COAST_POINTS:
        d = haversine_km(lat, lon, clat, clon)
        if d < best_d:
            best_d = d
            best = (clat, clon, name, basin, d)
    assert best is not None
    return best


def landfall_from_track(track: list[dict[str, Any]], now_idx: int) -> dict[str, Any]:
    """Estimate first close approach to a labeled coast along the future track."""
    future = track[now_idx:]
    if len(future) < 2:
        return {"possible": False, "disclaimer": "Insufficient future track to estimate landfall."}

    candidates = []
    for i, p in enumerate(future):
        clat, clon, name, basin, dist = nearest_coast(p["lat"], p["lon"])
        over_land = p.get("dist2land_km") is not None and p["dist2land_km"] == 0
        close = dist < 180 or over_land or (p.get("dist2land_km") is not None and p["dist2land_km"] < 40)
        if close:
            hours = i * 6
            wind = p.get("wind_kt")
            candidates.append(
                {
                    "region": name,
                    "basin": basin,
                    "latitude": round(p["lat"], 2),
                    "longitude": round(p["lon"], 2),
                    "coast_lat": clat,
                    "coast_lon": clon,
                    "estimated_hours": hours,
                    "estimated_wind_kt": wind,
                    "uncertainty_radius_km": round(40 + hours * 8.5, 1),
                    "distance_to_label_km": round(dist, 1),
                }
            )
            break

    if not candidates:
        last = future[-1]
        clat, clon, name, basin, dist = nearest_coast(last["lat"], last["lon"])
        return {
            "possible": dist < 400 and in_domain(last["lat"], last["lon"]),
            "region": name,
            "probability": round(max(0.05, min(0.45, 1.0 - dist / 800.0)), 2),
            "estimated_hours": (len(future) - 1) * 6,
            "estimated_wind_kt": last.get("wind_kt"),
            "uncertainty_radius_km": 180,
            "disclaimer": "No close coastal intercept in the 120 h cone; low-confidence nearest coast shown.",
        }

    hit = candidates[0]
    hours = hit["estimated_hours"]
    # Prototype probability: closer and sooner → higher, capped well below 1.
    p = 0.72 * max(0.0, 1.0 - hours / 140.0) * max(0.2, 1.0 - hit["distance_to_label_km"] / 250.0)
    hit["possible"] = True
    hit["probability"] = round(min(0.78, max(0.12, p)), 2)
    hit["disclaimer"] = (
        "Landfall region, time, and wind are prototype estimates from a statistical track "
        "and a coarse coastline gazetteer. They are not official IMD warnings."
    )
    return hit
