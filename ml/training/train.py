"""Training entry point.

Refuses to fake results. Neural training requires processed ERA5 patches.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arch", choices=["convlstm", "transformer"], default="convlstm")
    p.add_argument("--epochs", type=int, default=1)
    args = p.parse_args()
    patch_dir = ROOT / "data" / "processed" / "patches"
    if not patch_dir.exists() or not any(patch_dir.glob("*.npz")):
        report = {
            "status": "skipped",
            "arch": args.arch,
            "reason": "Model not trained yet. Storm-centered ERA5/INSAT patches are not present.",
            "next": "Run scripts/download_data.py (CDS credentials) then scripts/generate_training_samples.py",
        }
        out = ROOT / "data" / "processed" / "training_status.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        return
    raise SystemExit("Patch dataset found but full trainer is intentionally not auto-run in this prototype.")


if __name__ == "__main__":
    main()
