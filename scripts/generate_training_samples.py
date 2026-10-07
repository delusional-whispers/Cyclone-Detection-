#!/usr/bin/env python3
"""Generate storm-centered training samples when aligned cubes exist."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "training_samples_status.json"


def main():
    report = {
        "generated": False,
        "reason": "ERA5/INSAT cubes are not present. Refusing to synthesize fake atmospheric fields as training labels.",
        "planned_sample": {
            "grid": "64x64",
            "patch_deg": 20,
            "frames": 8,
            "dt_hours": 6,
            "channels": [
                "u10",
                "v10",
                "mslp",
                "t850",
                "z500",
                "rh700",
                "sst",
                "ir_bt",
            ],
            "targets": ["dlat", "dlon", "dwind", "dpres", "imd_class", "ri_flag"],
            "split": "cyclone-level chronological",
        },
    }
    OUT.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
