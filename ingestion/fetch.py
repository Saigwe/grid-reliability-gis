"""Download the open sources for London Power Networks' area into data/raw. Each file is fetched once
and cached; delete it to refresh.

  UK Power Networks open data portal (datasets readable without an account; the asset registers need one)
    lpn-operational-zones.geojson        London Power Networks' operational zone boundaries (the study area)
    network-statistics.json              customers and assets per licence area
    live-faults.json, national-outages.json   current and recent outages (a snapshot)
  ONS / Nomis
    lsoa-centroids.geojson               2021 LSOA population-weighted centroids (England and Wales)
    households.csv                       Census 2021 TS041 number of households per LSOA
  OpenStreetMap (Overpass API), the network itself
    osm-power.json                       power=substation and power=line/cable/minor_line in the study area's bounding box

Usage: python ingestion/fetch.py --raw data/raw
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "grid-reliability-gis/1.0 (+https://github.com/Saigwe/grid-reliability-gis)"
UKPN = "https://ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets"
CENTROIDS = ("https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/LSOA_PopCentroids_EW_2021_V4/"
             "FeatureServer/0/query")
NOMIS = "https://www.nomisweb.co.uk/api/v01/dataset/NM_2059_1.data.csv"
OVERPASS = "https://overpass-api.de/api/interpreter"


def get(url: str, data: bytes | None = None, retries: int = 4) -> bytes:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as r:
                body = r.read()
            time.sleep(0.5)
            return body
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(5 * 2 ** attempt)


def cached(path: Path, fetch) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(fetch())
        print(f"downloaded {path} ({path.stat().st_size / 1e6:.1f} MB)")
    return path


def ukpn_export(dataset: str, where: str | None = None, fmt: str = "geojson") -> bytes:
    q = f"?where={urllib.parse.quote(where)}" if where else ""
    return get(f"{UKPN}/{dataset}/exports/{fmt}{q}")


def arcgis_all(url: str) -> bytes:
    features, offset = [], 0
    while True:
        params = urllib.parse.urlencode({"where": "1=1", "outFields": "LSOA21CD", "outSR": 4326, "f": "geojson",
                                         "resultOffset": offset, "resultRecordCount": 2000})
        page = json.loads(get(f"{url}?{params}"))
        features += page["features"]
        if not page.get("properties", {}).get("exceededTransferLimit") and len(page["features"]) < 2000:
            break
        offset += len(page["features"])
    return json.dumps({"type": "FeatureCollection", "features": features}).encode()


def nomis_households() -> bytes:
    rows, offset, header = [], 0, None
    while True:
        params = urllib.parse.urlencode({"geography": "TYPE151", "measures": 20100,
                                         "select": "geography_code,obs_value", "recordoffset": offset})
        lines = get(f"{NOMIS}?{params}").decode().splitlines()
        header, body = lines[0], lines[1:]
        rows += body
        if len(body) < 25000:
            return "\n".join([header] + rows).encode()
        offset += len(body)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    args = ap.parse_args()
    raw = args.raw

    cached(raw / "network-statistics.json", lambda: ukpn_export("ukpn-network-statistics", fmt="json"))
    cached(raw / "lpn-operational-zones.geojson", lambda: ukpn_export("ukpn-lpn-area-operational-boundaries"))
    cached(raw / "live-faults.json", lambda: ukpn_export("ukpn-live-faults", fmt="json"))
    cached(raw / "national-outages.json", lambda: ukpn_export("ukpn-national-energy-outage", fmt="json"))
    cached(raw / "lsoa-centroids.geojson", lambda: arcgis_all(CENTROIDS))
    cached(raw / "households.csv", nomis_households)

    areas = json.loads((raw / "lpn-operational-zones.geojson").read_text())
    coords = [c for f in areas["features"] for c in _flatten(f["geometry"]["coordinates"])]
    south, west = min(c[1] for c in coords), min(c[0] for c in coords)
    north, east = max(c[1] for c in coords), max(c[0] for c in coords)
    query = (f"[out:json][timeout:300];("
             f'nwr["power"="substation"]({south},{west},{north},{east});'
             f'way["power"~"^(line|cable|minor_line)$"]({south},{west},{north},{east});'
             f");out geom tags;")
    cached(raw / "osm-power.json", lambda: get(OVERPASS, data=urllib.parse.urlencode({"data": query}).encode()))
    print(f"bounding box {south:.3f},{west:.3f},{north:.3f},{east:.3f}")


def _flatten(coords):
    if coords and isinstance(coords[0], (int, float)):
        yield coords
    else:
        for c in coords:
            yield from _flatten(c)


if __name__ == "__main__":
    main()
