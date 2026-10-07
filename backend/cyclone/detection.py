"""Heuristic cyclone-candidate features from a synthetic satellite field.

A neural detector has not been trained. Features are diagnostic summaries of
the parametric field plus best-track intensity, used only for the prototype UI.
"""

from __future__ import annotations

from typing import Any

from backend.models.imd import classify_wind_kt


def field_features(frame: dict[str, Any], center: dict[str, Any]) -> dict[str, Any]:
    vals = frame.get("values") or []
    imagery = frame.get("imagery", "ir")
    flat = [v for row in vals for v in row]
    if not flat:
        return {"organization": 0.2, "convection": 0.2, "symmetry": 0.2, "spiral": 0.1, "cdo": 0.1}

    if imagery == "visible":
        cold_frac = sum(1 for v in flat if v > 0.55) / len(flat)
        convection = cold_frac
    else:
        q = sorted(flat)
        p10 = q[max(0, len(q) // 10)]
        cold_frac = sum(1 for v in flat if v < -35) / len(flat)
        convection = min(1.0, max(0.0, (-p10 - 20) / 60))
        convection = 0.5 * convection + 0.5 * min(1.0, cold_frac * 4)

    wind = float(center.get("wind_kt") or 0)
    cdo = min(1.0, max(0.0, (wind - 20) / 55))
    spiral = min(1.0, max(0.0, (wind - 28) / 50))
    organization = min(1.0, 0.35 * convection + 0.35 * cdo + 0.30 * spiral)
    symmetry = min(1.0, 0.4 + 0.6 * (1.0 / (1.0 + abs((center.get("lat") or 15) - 15) / 18)))
    return {
        "organization": round(organization, 3),
        "convection": round(convection, 3),
        "symmetry": round(symmetry, 3),
        "spiral": round(spiral, 3),
        "cdo": round(cdo, 3),
        "cold_cloud_fraction": round(cold_frac, 3),
    }


def evolution(track: list[dict[str, Any]], now_idx: int) -> dict[str, Any]:
    p = track[now_idx]
    look = [q for q in track if q["hours_from_start"] <= p["hours_from_start"] and q["hours_from_start"] >= p["hours_from_start"] - 12]
    winds = [q.get("wind_kt") for q in look if q.get("wind_kt") is not None]
    d_wind = None
    if len(winds) >= 2:
        d_wind = winds[-1] - winds[0]
    if d_wind is None:
        state = "uncertain"
    elif d_wind >= 15:
        state = "rapidly_intensifying"
    elif d_wind >= 5:
        state = "strengthening"
    elif d_wind <= -10:
        state = "weakening"
    else:
        state = "steady_or_forming"
    return {"state": state, "d_wind_12h": d_wind, "n_frames": len(look)}


def candidate_probability(features: dict[str, Any], wind_kt: float | None, evo: dict[str, Any]) -> float:
    w = float(wind_kt or 0)
    base = 0.15 + 0.45 * features["organization"] + 0.2 * features["convection"]
    if w >= 34:
        base = max(base, 0.72)
    if w >= 48:
        base = max(base, 0.84)
    if evo["state"] == "rapidly_intensifying":
        base += 0.06
    if evo["state"] == "weakening":
        base -= 0.05
    return round(min(0.94, max(0.08, base)), 3)


def explain(features: dict[str, Any], evo: dict[str, Any], basin: str, cls_name: str) -> str:
    basin_name = "the Bay of Bengal" if basin == "BB" else "the Arabian Sea" if basin == "AS" else "the North Indian Ocean"
    bits = []
    if features["convection"] > 0.55:
        bits.append("persistent deep convection")
    if features["cdo"] > 0.45:
        bits.append("a developing central dense overcast")
    if features["spiral"] > 0.4:
        bits.append("curved banding / spiral organization")
    if features["symmetry"] > 0.55:
        bits.append("increasing cloud symmetry")
    feat = ", ".join(bits) if bits else "limited organization in the diagnostic field"
    motion = {
        "rapidly_intensifying": "The 12-hour wind trend suggests rapid intensification.",
        "strengthening": "The system appears to be gradually intensifying.",
        "weakening": "Recent frames suggest weakening or reduced convection.",
        "steady_or_forming": "The disturbance is organizing or holding intensity.",
        "uncertain": "Intensity trend is uncertain from the available fixes.",
    }[evo["state"]]
    return (
        f"{cls_name} signature over {basin_name}: {feat}. {motion} "
        "This is an experimental decision-support summary, not an IMD forecast."
    )


def trend_label(evo: dict[str, Any]) -> str:
    return {
        "rapidly_intensifying": "Rapid intensification signals in the last 12 h",
        "strengthening": "Strengthening",
        "weakening": "Weakening",
        "steady_or_forming": "Forming / little change",
        "uncertain": "Trend uncertain",
    }[evo["state"]]
