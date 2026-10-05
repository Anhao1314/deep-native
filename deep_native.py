#!/usr/bin/env python3
"""Run the bundled CLI without installing a package."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "skills/deep-native/scripts/deep_native.py"), run_name="__main__")
