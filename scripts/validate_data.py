#!/usr/bin/env python3
"""Validate downloaded IBTrACS NI file before processing."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "raw" / "ibtracs.NI.list.v04r01.csv"


def main() -> int:
    if not CSV.exists():
        print(f"MISSING {CSV}")
        return 1
    with CSV.open() as f:
        header = f.readline()
        units = f.readline()
        row = f.readline()
    if "SID" not in header or "NEWDELHI_WIND" not in header:
        print("Unexpected IBTrACS header")
        return 2
    if "1842" not in row and "N" not in row:
        print("Unexpected first data row")
        return 3
    print(f"OK {CSV} size={CSV.stat().st_size} header_cols={header.count(',')+1}")
    print(f"units_row_present={bool(units.strip())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
