#!/usr/bin/env python3
"""Spatial crop + basic cleaning notes. Track dataset creation is in create_cyclone_dataset.py."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    print("preprocess_data: IBTrACS cleaning is performed inside create_cyclone_dataset.py")
    print("ERA5/INSAT cropping will write Zarr under data/processed/weather once downloaded.")
    (ROOT / "data" / "processed" / "weather").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "processed" / "satellite").mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
