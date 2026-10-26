"""Load the raw downloads into DuckDB `bronze`. Geometry is kept as longitude/latitude columns and WKT text, so the
same dbt project can build its spatial models on DuckDB (spatial extension) or on PostGIS.

  bronze.lsoa_centroids   2021 LSOA population-weighted centroids (England and Wales)
  bronze.households       Census 2021 households per LSOA
  bronze.lpn_zones        London Power Networks' operational zones (WKT polygons)
  bronze.osm_substations  OSM power=substation: centroid, tags
  bronze.osm_lines        OSM power=line/cable/minor_line: WKT linestring, tags
  bronze.live_faults      UKPN live faults (a snapshot)
  bronze.national_outages UKPN national energy outage feed (a snapshot)
  bronze.network_statistics  UKPN customers and assets per licence area

Usage: python ingestion/load.py --raw data/raw --db warehouse/grid.duckdb
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd


def osm(raw: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    subs, lines = [], []
    for e in json.loads((raw / "osm-power.json").read_text(encoding="utf-8"))["elements"]:
        t = e.get("tags", {})
        if t.get("power") == "substation":
            if e["type"] == "node":
                lon, lat = e["lon"], e["lat"]
            elif "geometry" in e:
                pts = e["geometry"]
                lon, lat = sum(p["lon"] for p in pts) / len(pts), sum(p["lat"] for p in pts) / len(pts)
            elif "bounds" in e:
                b = e["bounds"]
                lon, lat = (b["minlon"] + b["maxlon"]) / 2, (b["minlat"] + b["maxlat"]) / 2
            else:
                continue
            subs.append({"osm_id": f"{e['type']}/{e['id']}", "lon": lon, "lat": lat, "name": t.get("name"),
                         "operator": t.get("operator"), "voltage": t.get("voltage"),
                         "substation_type": t.get("substation"), "ref": t.get("ref")})
        elif t.get("power") in ("line", "cable", "minor_line") and "geometry" in e:
            wkt = "LINESTRING (" + ", ".join(f"{p['lon']} {p['lat']}" for p in e["geometry"]) + ")"
            lines.append({"osm_id": f"way/{e['id']}", "power": t.get("power"), "voltage": t.get("voltage"),
                          "operator": t.get("operator"), "location": t.get("location"), "wkt": wkt})
    return pd.DataFrame(subs), pd.DataFrame(lines)


def zones(raw: Path) -> pd.DataFrame:
    import duckdb as d

    con = d.connect()
    con.execute("install spatial; load spatial")
    return con.execute(f"""select ops_area as zone, ST_AsText(geom) as wkt
                           from st_read('{(raw / "lpn-operational-zones.geojson").as_posix()}')""").df()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--db", default="warehouse/grid.duckdb")
    args = ap.parse_args()
    raw = args.raw

    cent = json.loads((raw / "lsoa-centroids.geojson").read_text(encoding="utf-8"))["features"]
    centroids = pd.DataFrame([{"lsoa_code": f["properties"]["LSOA21CD"], "lon": f["geometry"]["coordinates"][0],
                               "lat": f["geometry"]["coordinates"][1]} for f in cent])
    households = pd.read_csv(raw / "households.csv").rename(columns={"GEOGRAPHY_CODE": "lsoa_code", "OBS_VALUE": "households"})
    subs, lines = osm(raw)
    lf = json.loads((raw / "live-faults.json").read_text(encoding="utf-8"))
    live = pd.DataFrame([{"incident_ref": r["incidentreference"], "power_cut_type": r.get("powercuttype"),
                          "created_at": r.get("creationdatetime"), "restored_at": r.get("restoreddatetime"),
                          "customers_affected": r.get("nocustomeraffected"), "category": r.get("incidentcategory"),
                          "lon": (r.get("geopoint") or {}).get("lon"), "lat": (r.get("geopoint") or {}).get("lat")}
                         for r in lf])
    no = json.loads((raw / "national-outages.json").read_text(encoding="utf-8"))
    national = pd.DataFrame([{"fault_id": r["fault_id"], "licence_area": r.get("licence_area"), "voltage": r.get("voltage"),
                              "planned": r.get("planned"), "start_at": r.get("outage_start_date"),
                              "restored_at": r.get("date_of_restoration"),
                              "lon": (r.get("geo_point_2d") or {}).get("lon"), "lat": (r.get("geo_point_2d") or {}).get("lat")}
                             for r in no])
    stats = pd.DataFrame(json.loads((raw / "network-statistics.json").read_text(encoding="utf-8")))
    stats = stats[["licence_area", "no_of_customers", "main_substations_grid_primary", "grid_substation",
                   "primary_substation", "secondary_substations_gm", "secondary_substations_pm", "hv_cables_underground",
                   "hv_cables_overhead_lines", "lv_cables_underground"]].astype(str)

    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(args.db)
    con.execute("create schema if not exists bronze")
    tables = {"lsoa_centroids": centroids, "households": households, "lpn_zones": zones(raw), "osm_substations": subs,
              "osm_lines": lines, "live_faults": live, "national_outages": national, "network_statistics": stats}
    for name, df in tables.items():
        con.execute(f"create or replace table bronze.{name} as select * from df")
        print(f"bronze.{name:<20} {len(df):>7,} rows")


if __name__ == "__main__":
    main()
