"""Indian Cyclone AI Weather Lab API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.inference.engine import detect_snapshot, forecast_storm, verify_track_error
from backend.services.catalog import get_storm, load_evaluation, storms
from backend.services.weather import weather_grid

app = FastAPI(
    title="Indian Cyclone AI Weather Lab",
    version="0.1.0",
    description=(
        "Research prototype for North Indian Ocean tropical cyclones. "
        "Neural forecasting models are not trained. "
        "Statistical baselines are evaluated on IBTrACS NI. "
        "Not an official IMD warning system."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class DetectRequest(BaseModel):
    storm_id: str
    time_index: int = 0


class PredictRequest(BaseModel):
    storm_id: str
    time_index: int = 8
    ensemble_size: int = Field(21, ge=5, le=51)
    model: str = "indian_analog_ensemble"


def _summary(s: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": s["id"],
        "name": s["name"],
        "season": s["season"],
        "start_time": s["start_time"],
        "end_time": s["end_time"],
        "genesis_basin": s.get("genesis_basin"),
        "sub_basin": s.get("sub_basin"),
        "peak_wind_kt": s.get("peak_wind_kt"),
        "min_pres_hpa": s.get("min_pres_hpa"),
        "peak_category": s.get("peak_category"),
        "split": s.get("split"),
        "n_points": len(s["track"]),
        "landfall_hint": s.get("landfall_hint"),
    }


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "mode": "historical_replay",
        "live_data": False,
        "neural_models_trained": False,
        "dataset": "IBTrACS v04r01 North Indian Ocean, domain-cropped",
    }


@app.get("/api/cyclones")
def list_cyclones(
    season: int | None = None,
    basin: str | None = None,
    q: str | None = None,
    limit: int = Query(80, le=400),
):
    items = storms()
    if season:
        items = [s for s in items if s["season"] == season]
    if basin:
        items = [s for s in items if s.get("genesis_basin") == basin or s.get("sub_basin") == basin]
    if q:
        qq = q.upper()
        items = [s for s in items if qq in s["name"].upper() or qq in s["id"].upper()]
    # prefer named, satellite-era, stronger storms first
    items = sorted(items, key=lambda s: (-s["season"], -(s.get("peak_wind_kt") or 0), s["name"]))
    return {
        "count": len(items),
        "cyclones": [_summary(s) for s in items[:limit]],
        "disclaimer": "Historical IBTrACS best tracks. This is not a live cyclone feed.",
    }


@app.get("/api/cyclones/{storm_id}")
def cyclone_detail(storm_id: str):
    try:
        s = get_storm(storm_id)
    except KeyError as exc:
        raise HTTPException(404, "Unknown cyclone") from exc
    return {**_summary(s), "track": s["track"], "notes": s.get("notes")}


@app.get("/api/cyclones/{storm_id}/track")
def cyclone_track(storm_id: str):
    try:
        s = get_storm(storm_id)
    except KeyError as exc:
        raise HTTPException(404, "Unknown cyclone") from exc
    return {"id": s["id"], "name": s["name"], "track": s["track"]}


@app.get("/api/cyclones/{storm_id}/forecast")
def cyclone_forecast(
    storm_id: str,
    time_index: int = 8,
    ensemble_size: int = 21,
    model: str = "indian_analog_ensemble",
):
    try:
        s = get_storm(storm_id)
    except KeyError as exc:
        raise HTTPException(404, "Unknown cyclone") from exc
    fc = forecast_storm(s, time_index, ensemble_size=ensemble_size, model=model)
    fc["verification"] = verify_track_error(s, time_index, fc)
    fc["detection"] = detect_snapshot(s, time_index)
    return fc


@app.post("/api/detect")
def detect(req: DetectRequest):
    try:
        s = get_storm(req.storm_id)
    except KeyError as exc:
        raise HTTPException(404, "Unknown cyclone") from exc
    return detect_snapshot(s, req.time_index)


@app.post("/api/predict")
def predict(req: PredictRequest):
    try:
        s = get_storm(req.storm_id)
    except KeyError as exc:
        raise HTTPException(404, "Unknown cyclone") from exc
    fc = forecast_storm(s, req.time_index, ensemble_size=req.ensemble_size, model=req.model)
    fc["verification"] = verify_track_error(s, req.time_index, fc)
    return fc


@app.get("/api/weather")
def weather(storm_id: str, time_index: int = 8):
    try:
        s = get_storm(storm_id)
    except KeyError as exc:
        raise HTTPException(404, "Unknown cyclone") from exc
    p = s["track"][max(0, min(time_index, len(s["track"]) - 1))]
    month = int(p["iso_time"][5:7])
    return weather_grid(p, month)


@app.get("/api/satellite")
def satellite(storm_id: str, time_index: int = 8):
    try:
        s = get_storm(storm_id)
    except KeyError as exc:
        raise HTTPException(404, "Unknown cyclone") from exc
    p = s["track"][max(0, min(time_index, len(s["track"]) - 1))]
    return {
        "available": False,
        "storm_id": storm_id,
        "iso_time": p["iso_time"],
        "reason": "INSAT/MOSDAC granules are not bundled. Enable scripts/download_data.py after MOSDAC login.",
        "placeholder_layer": "parametric_cloud_top_temperature",
    }


@app.get("/api/models")
def models():
    return {
        "models": [
            {
                "id": "persistence",
                "name": "Baseline Persistence",
                "trained": True,
                "kind": "statistical",
            },
            {
                "id": "climatology_steering",
                "name": "CLIPER-style NIO climatology",
                "trained": True,
                "kind": "statistical",
            },
            {
                "id": "indian_analog_ensemble",
                "name": "Indian analog ensemble",
                "trained": True,
                "kind": "statistical",
            },
            {
                "id": "convlstm_baseline",
                "name": "ConvLSTM (untrained)",
                "trained": False,
                "kind": "neural",
                "note": "Model not trained yet.",
            },
            {
                "id": "spatiotemporal_transformer",
                "name": "Spatiotemporal transformer (untrained)",
                "trained": False,
                "kind": "neural",
                "note": "Model not trained yet.",
            },
        ],
        "evaluation": load_evaluation(),
    }


@app.get("/api/evaluation")
def evaluation():
    return load_evaluation()


class EarlyWarningRequest(BaseModel):
    storm_id: str
    time_index: int = 8
    imagery: str = "ir"
    region: str = "nio"
    ensemble_size: int = Field(21, ge=5, le=41)


@app.get("/api/early-warning/meta")
def early_warning_meta():
    from backend.satellite.provider import IMAGERY, REGIONS

    return {
        "imagery": IMAGERY,
        "regions": REGIONS,
        "leads_hours": [0, 6, 12, 24, 48, 72, 96, 120],
        "neural_models_trained": False,
        "capability": "Early detection and probabilistic forecasting of tropical cyclone development and trajectory.",
        "disclaimer": "Experimental decision support. IMD warnings take precedence. Satellite fields are synthetic.",
    }


@app.post("/api/early-warning/analyze")
def early_warning_analyze(req: EarlyWarningRequest):
    from backend.cyclone.pipeline import analyze

    try:
        s = get_storm(req.storm_id)
    except KeyError as exc:
        raise HTTPException(404, "Unknown cyclone") from exc
    return analyze(s, req.time_index, req.imagery, req.region, ensemble_size=req.ensemble_size)


@app.get("/api/early-warning/analyze")
def early_warning_analyze_get(
    storm_id: str,
    time_index: int = 8,
    imagery: str = "ir",
    region: str = "nio",
):
    from backend.cyclone.pipeline import analyze

    try:
        s = get_storm(storm_id)
    except KeyError as exc:
        raise HTTPException(404, "Unknown cyclone") from exc
    return analyze(s, time_index, imagery, region)


DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/", include_in_schema=False)
def spa_index():
    index = DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return {
        "error": "Frontend build missing. Run: cd frontend && npm run build",
        "api": "/api/health",
    }


@app.get("/{full_path:path}", include_in_schema=False)
def spa_assets(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(404, "Unknown API route")
    target = DIST / full_path
    if target.is_file():
        return FileResponse(target)
    index = DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    raise HTTPException(404, "Not found")
