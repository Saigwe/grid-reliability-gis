"""Synthetic raw files in the exact formats of the real downloads (UKPN, ONS/Nomis, OSM Overpass), so CI runs
the real loader, the spatial dbt models (DuckDB and PostGIS), the outage simulation and the map, offline.
A small made-up city: 2 zones, 12 primary substations, 150 LSOAs, a few live outages.

Usage: python tests/fixtures/make_fixture.py --raw data/fixture/raw
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def square(lon0, lat0, lon1, lat1):
    return [[[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=Path("data/fixture/raw"))
    args = ap.parse_args()
    rng = np.random.default_rng(18)
    raw = args.raw
    raw.mkdir(parents=True, exist_ok=True)
    zones = {"West": square(-0.30, 51.40, -0.10, 51.60), "East": square(-0.10, 51.40, 0.10, 51.60)}
    (raw / "lpn-operational-zones.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"ops_area": z}, "geometry": {"type": "Polygon", "coordinates": c}}
        for z, c in zones.items()]}))

    lons, lats = rng.uniform(-0.29, 0.09, 150), rng.uniform(51.41, 51.59, 150)
    codes = [f"E0199{i:04d}" for i in range(150)]
    outside = {"type": "Feature", "properties": {"LSOA21CD": "W01000001"}, "geometry": {"type": "Point", "coordinates": [-3.2, 51.5]}}
    (raw / "lsoa-centroids.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [outside] + [
        {"type": "Feature", "properties": {"LSOA21CD": c}, "geometry": {"type": "Point", "coordinates": [x, y]}}
        for c, x, y in zip(codes, lons, lats)]}))
    (raw / "households.csv").write_text('"GEOGRAPHY_CODE","OBS_VALUE"\n' + '"W01000001",600\n'
                                        + "".join(f'"{c}",{h}\n' for c, h in zip(codes, rng.integers(450, 900, 150))))

    elements = []
    for i in range(12):
        elements.append({"type": "node", "id": 1000 + i, "lat": float(rng.uniform(51.42, 51.58)), "lon": float(rng.uniform(-0.28, 0.08)),
                         "tags": {"power": "substation", "voltage": "33000;11000", "operator": "UK Power Networks", "name": f"Primary {i}"}})
    for i in range(30):
        elements.append({"type": "node", "id": 2000 + i, "lat": float(rng.uniform(51.41, 51.59)), "lon": float(rng.uniform(-0.29, 0.09)),
                         "tags": {"power": "substation", "substation": "minor_distribution"}})
    elements.append({"type": "way", "id": 3000, "tags": {"power": "substation", "substation": "traction", "operator": "Network Rail"},
                     "geometry": [{"lat": 51.5, "lon": -0.2}, {"lat": 51.501, "lon": -0.199}, {"lat": 51.5, "lon": -0.198}]})
    elements.append({"type": "way", "id": 4000, "tags": {"power": "cable", "voltage": "132000"},
                     "geometry": [{"lat": 51.45, "lon": -0.25}, {"lat": 51.5, "lon": -0.1}, {"lat": 51.55, "lon": 0.05}]})
    (raw / "osm-power.json").write_text(json.dumps({"elements": elements}))

    live = [{"incidentreference": f"INCD-9{i:05d}-Z", "powercuttype": ["Unplanned", "Restored", "Planned"][i % 3],
             "creationdatetime": f"2026-10-2{5 + i % 2}T0{i % 9}:15:00", "restoreddatetime": f"2026-10-2{5 + i % 2}T1{i % 9}:00:00" if i % 3 == 1 else None,
             "nocustomeraffected": int(rng.integers(5, 300)), "incidentcategory": 1,
             "geopoint": {"lon": float(rng.uniform(-0.28, 0.08)), "lat": float(rng.uniform(51.42, 51.58))}} for i in range(6)]
    (raw / "live-faults.json").write_text(json.dumps(live))
    national = [{"fault_id": "INCD-900001-Z", "licence_area": "London", "voltage": "LV", "planned": "FALSE",
                 "outage_start_date": "2026-10-25T00:15:00+00:00", "date_of_restoration": None,
                 "geo_point_2d": live[0]["geopoint"]},
                {"fault_id": "INCD-800001-X", "licence_area": "London", "voltage": "LV", "planned": "FALSE",
                 "outage_start_date": "2026-10-25T03:10:00+00:00", "date_of_restoration": "2026-10-25T03:11:00+00:00",
                 "geo_point_2d": {"lon": -0.15, "lat": 51.5}}]
    (raw / "national-outages.json").write_text(json.dumps(national))
    stats = {"licence_area": "London Power Networks (LPN)", "no_of_customers": "0.1", "main_substations_grid_primary": 20,
             "grid_substation": 4, "primary_substation": 16, "secondary_substations_gm": 40, "secondary_substations_pm": 0,
             "hv_cables_underground": 100, "hv_cables_overhead_lines": 0, "lv_cables_underground": 200}
    (raw / "network-statistics.json").write_text(json.dumps([stats]))
    print(f"wrote fixture sources to {raw}")


if __name__ == "__main__":
    main()
