#!/usr/bin/env python3
"""Evaluate statistical baselines on held-out Indian cyclones.

Reports real haversine track error and intensity MAE. Neural models are skipped.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.models.geo import haversine_km
from backend.services.catalog import storms
from backend.services.forecast import LEAD_HOURS, forecast_storm
from ml.evaluation.metrics import mae_rmse_r2
from ml.experiments import log_experiment


def evaluate(model: str, split: str = "test", max_storms: int = 80) -> dict:
    items = [s for s in storms() if s["split"] == split and len(s["track"]) >= 10]
    items = items[:max_storms]
    track_err = defaultdict(list)
    winds_y, winds_hat = [], []
    pres_y, pres_hat = [], []
    n_fc = 0
    for s in items:
        # initialize at 24h into storm if possible
        idx = min(4, len(s["track"]) // 3)
        fc = forecast_storm(s, idx, ensemble_size=9, model=model)
        now_h = s["track"][idx]["hours_from_start"]
        by_lead = {p["lead_hours"]: p for p in fc["mean_track"]}
        for lead in LEAD_HOURS:
            p = by_lead.get(lead)
            if not p:
                continue
            obs = min(s["track"], key=lambda q: abs(q["hours_from_start"] - (now_h + lead)))
            if abs(obs["hours_from_start"] - (now_h + lead)) > 4:
                continue
            track_err[lead].append(haversine_km(p["lat"], p["lon"], obs["lat"], obs["lon"]))
            if obs.get("wind_kt") is not None:
                winds_y.append(obs["wind_kt"])
                winds_hat.append(p["wind_kt"])
            if obs.get("pres_hpa") is not None:
                pres_y.append(obs["pres_hpa"])
                pres_hat.append(p["pres_hpa"])
        n_fc += 1
    summary = {
        "model": model,
        "split": split,
        "n_storms": len(items),
        "n_forecasts": n_fc,
        "track_error_km": {
            str(k): {
                "mean": round(sum(v) / len(v), 1) if v else None,
                "median": round(sorted(v)[len(v) // 2], 1) if v else None,
                "n": len(v),
            }
            for k, v in sorted(track_err.items())
        },
        "intensity_wind_kt": mae_rmse_r2(winds_y, winds_hat),
        "intensity_pres_hpa": mae_rmse_r2(pres_y, pres_hat),
        "neural_models_trained": False,
        "disclaimer": "Statistical baseline only. These are not neural WeatherNext-style scores.",
    }
    return summary


def main():
    reports = [evaluate("persistence"), evaluate("indian_analog_ensemble")]
    out = {
        "status": "ok",
        "dataset": "Indian Cyclone Dataset from IBTrACS NI",
        "models": reports,
        "untrained": [
            {"id": "convlstm_baseline", "note": "Model not trained yet."},
            {"id": "spatiotemporal_transformer", "note": "Model not trained yet."},
        ],
    }
    path = ROOT / "data" / "processed" / "baseline_evaluation.json"
    path.write_text(json.dumps(out, indent=2))
    log_experiment(
        {
            "model": "indian_analog_ensemble",
            "dataset": "IBTrACS-NI-crop",
            "epochs": 0,
            "track_error": reports[1]["track_error_km"],
            "intensity_mae": reports[1]["intensity_wind_kt"],
        }
    )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
