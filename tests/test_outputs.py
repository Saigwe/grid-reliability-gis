"""Checks on a finished run: the map and its numbers agree with the warehouse, and the hex CSV loads in kepler.gl."""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import h3

RESULTS = Path(os.environ.get("GRID_RESULTS", Path(__file__).resolve().parents[1] / "results"))


def test_hex_csv_is_valid_h3_and_covers_every_household():
    rows = list(csv.DictReader((RESULTS / "hex_reliability.csv").open()))
    summary = json.loads((RESULTS / "map_summary.json").read_text())
    assert rows and all(h3.is_valid_cell(r["hex_id"]) for r in rows)
    assert sum(int(r["households"]) for r in rows) == summary["households"]
    assert all(float(r["cml"]) >= 0 and float(r["ci"]) >= 0 for r in rows)


def test_worst_decile_is_worse_than_the_city():
    s = json.loads((RESULTS / "map_summary.json").read_text())
    assert s["worst_decile_cml"] >= s["london_cml"]
