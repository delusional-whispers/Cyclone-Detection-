#!/usr/bin/env python3
"""Align weather/satellite cubes to IBTrACS times — stub until ERA5/INSAT exist."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "alignment_status.json"


def main():
    report = {
        "aligned": False,
        "track_times": "IBTrACS 3-hourly interpolated / typically 6-hourly reports",
        "era5": "not downloaded — target 6-hourly, 0.25°, NIO crop, bilinear to storm-centered 64x64",
        "insat": "not downloaded — nearest hour mosaic, reproject to same storm-centered grid",
        "ocean": "not downloaded — OISST daily interpolated to 6-hourly track times",
        "note": "Do not train neural models until this report is aligned=true.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
