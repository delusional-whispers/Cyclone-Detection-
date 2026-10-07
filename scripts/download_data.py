#!/usr/bin/env python3
"""Download public Indian-region cyclone inputs.

Default: IBTrACS North Indian Ocean CSV only (small, open).
ERA5 / MOSDAC / INCOIS require accounts and are opt-in flags.
Does not download multi-terabyte archives.
"""

from __future__ import annotations

import argparse
import ssl
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

IBTRACS_NI = (
    "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/"
    "v04r01/access/csv/ibtracs.NI.list.v04r01.csv"
)


def fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"GET {url}")
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, context=ctx, timeout=180) as r, dest.open("wb") as f:
        while True:
            chunk = r.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)
    print(f"wrote {dest} ({dest.stat().st_size} bytes)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ibtracs", action="store_true", default=True)
    p.add_argument("--era5", action="store_true", help="Print CDS recipe; do not download.")
    p.add_argument("--mosdac", action="store_true", help="Print MOSDAC recipe; do not download.")
    args = p.parse_args()
    if args.ibtracs:
        fetch(IBTRACS_NI, RAW / "ibtracs.NI.list.v04r01.csv")
    if args.era5:
        print(
            "ERA5: register at https://cds.climate.copernicus.eu then use cdsapi for "
            "reanalysis-era5-pressure-levels over lat 0-30, lon 50-110, 6-hourly, cyclone windows only. "
            "See docs/DATASETS.md. This script will not pull the global archive."
        )
    if args.mosdac:
        print(
            "MOSDAC INSAT: https://mosdac.gov.in order/API after login. "
            "Request TIR brightness temperature for NIO cyclone cases only."
        )


if __name__ == "__main__":
    main()
