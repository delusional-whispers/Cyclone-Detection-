"""Early-warning pipeline: mock satellite → features → track/intensity/risk.

Neural CV/temporal models are not trained. Track/intensity reuse the
statistical NIO ensemble. Risk is a documented composite heuristic.
"""

from __future__ import annotations

from typing import Any

from backend.cyclone.analogs import similar_cyclones
from backend.cyclone.detection import candidate_probability, evolution, explain, field_features, trend_label
from backend.cyclone.risk import assess_risk
from backend.inference.engine import detect_snapshot, forecast_storm
from backend.models.imd import classify_wind_kt
from backend.satellite.provider import default_provider
from backend.services.landfall import nearest_coast


def analyze(storm: dict[str, Any], time_index: int, imagery: str, region: str, ensemble_size: int = 11) -> dict[str, Any]:
    idx = max(1, min(int(time_index), len(storm["track"]) - 1))
    now = storm["track"][idx]
    sat = default_provider()
    frame = sat.frame(now, imagery, region)
    feats = field_features(frame, now)
    evo = evolution(storm["track"], idx)
    det = detect_snapshot(storm, idx)
    p_cyc = candidate_probability(feats, now.get("wind_kt"), evo)
    fc = forecast_storm(storm, idx, ensemble_size=ensemble_size, model="indian_analog_ensemble")
    land = fc.get("landfall") or {}
    d24 = None
    if idx >= 1 and storm["track"][idx].get("wind_kt") and storm["track"][max(0, idx - 4)].get("wind_kt"):
        d24 = storm["track"][idx]["wind_kt"] - storm["track"][max(0, idx - 4)]["wind_kt"]
    spread72 = None
    for p in fc["mean_track"]:
        if p["lead_hours"] == 72:
            spread72 = p.get("spread_km")
    _, _, coast_name, _, coast_d = nearest_coast(now["lat"], now["lon"])
    risk = assess_risk(
        wind_kt=now.get("wind_kt"),
        d_wind_24h=d24,
        dist2land_km=now.get("dist2land_km") if now.get("dist2land_km") is not None else coast_d,
        landfall_probability=land.get("probability"),
        landfall_region=str(land.get("region") or coast_name),
        spread_km_72=spread72,
        ri_probability=fc.get("rapid_intensification_probability"),
    )
    points = []
    for p in fc["mean_track"]:
        r = assess_risk(
            wind_kt=p.get("wind_kt"),
            d_wind_24h=d24,
            dist2land_km=now.get("dist2land_km"),
            landfall_probability=land.get("probability"),
            landfall_region=str(land.get("region") or ""),
            spread_km_72=p.get("spread_km"),
            ri_probability=fc.get("rapid_intensification_probability"),
        )
        conf = max(0.18, min(0.88, 0.82 - p["lead_hours"] / 220 - (p.get("spread_km") or 0) / 1800))
        points.append(
            {
                "lead_hours": p["lead_hours"],
                "lat": p["lat"],
                "lon": p["lon"],
                "wind_kt": p.get("wind_kt"),
                "pres_hpa": p.get("pres_hpa"),
                "category": p.get("category"),
                "risk_level": r["level"],
                "confidence": round(conf, 3),
            }
        )

    tnow = now["hours_from_start"]
    loop = []
    for hours_back in [12, 9, 6, 3, 0]:
        target = tnow - hours_back
        q = min(storm["track"], key=lambda x: abs(x["hours_from_start"] - target))
        loop.append(
            {
                "hours_before_now": hours_back,
                "iso_time": q["iso_time"],
                "lat": q["lat"],
                "lon": q["lon"],
                "wind_kt": q.get("wind_kt"),
                "frame": sat.frame(q, imagery, region),
            }
        )

    cls = classify_wind_kt(now.get("wind_kt"))
    basin = now.get("sub_basin") or storm.get("genesis_basin") or "NI"
    return {
        "label": "Desk product — historical case, not a live watch",
        "official_precedence": "IMD / RSMC New Delhi warnings always take precedence.",
        "capability": "Early detection and probabilistic forecasting of tropical cyclone development and trajectory.",
        "neural_models_trained": False,
        "satellite": {
            "live": False,
            "imagery": imagery,
            "region": region,
            "frame": frame,
            "loop": loop,
        },
        "detection": {
            **det,
            "cyclone_probability": p_cyc,
            "features": feats,
            "evolution": evo,
            "trend": trend_label(evo),
            "system_label": cls.name,
            "method": "Parametric IR kernel + IBTrACS centre + IMD wind class. Neural detector not trained.",
        },
        "forecast_points": points,
        "mean_track": fc["mean_track"],
        "uncertainty_cone": fc["uncertainty_cone"],
        "movement": {
            "heading": fc["now"]["heading"],
            "heading_deg": fc["now"]["heading_deg"],
            "speed_kt": fc["now"]["speed_kt"],
            "speed_kmh": fc["now"]["speed_kmh"],
        },
        "risk": risk,
        "landfall": land,
        "analogs": similar_cyclones(storm, idx, k=5),
        "ensemble": fc["ensemble"][:4],
        "explanation": explain(feats, evo, basin, cls.name),
        "forecast_confidence": points[0]["confidence"] if points else 0.5,
        "disclaimer": fc["disclaimer"] + " Satellite fields are synthetic diagnostics, not live imagery.",
    }
