"""Load the processed Indian Cyclone Dataset (IBTrACS NI, domain-cropped)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "data" / "processed" / "indian_cyclone_catalog.json"
CLIMO_PATH = ROOT / "data" / "processed" / "motion_climatology.json"
EVAL_PATH = ROOT / "data" / "processed" / "baseline_evaluation.json"


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(
            f"Processed catalog missing at {CATALOG_PATH}. Run scripts/create_cyclone_dataset.py"
        )
    return json.loads(CATALOG_PATH.read_text())


def storms() -> list[dict[str, Any]]:
    return load_catalog()["storms"]


def get_storm(storm_id: str) -> dict[str, Any]:
    for s in storms():
        if s["id"] == storm_id:
            return s
    raise KeyError(storm_id)


def point_at(storm: dict[str, Any], index: int) -> dict[str, Any]:
    pts = storm["track"]
    i = max(0, min(int(index), len(pts) - 1))
    return pts[i]


@lru_cache(maxsize=1)
def load_climatology() -> dict[str, Any]:
    if not CLIMO_PATH.exists():
        return {"cells": {}, "genesis": []}
    return json.loads(CLIMO_PATH.read_text())


@lru_cache(maxsize=1)
def load_evaluation() -> dict[str, Any]:
    if not EVAL_PATH.exists():
        return {
            "status": "not_run",
            "disclaimer": "Baseline evaluation has not been computed yet.",
        }
    return json.loads(EVAL_PATH.read_text())
