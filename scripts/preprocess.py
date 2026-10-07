#!/usr/bin/env python3
"""Alias matching the spec name."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("preprocess_data.py")), run_name="__main__")
