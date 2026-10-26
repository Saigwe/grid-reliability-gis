"""Build the H3 hex map of the worst-served areas, from gold.rpt_lsoa_reliability.

Each LSOA's customer minutes lost go to the H3 cell (resolution 8, ~0.7 km2) of its population-weighted centroid;
a hex's CML is its customer minutes lost over its households, so hexes are comparable whatever their size.

Writes
  map/index.html                 interactive deck.gl map (hexes by CML, primary substations, real live outages)
  results/hex_reliability.csv    hex_id, households, CML, CI: loads straight into kepler.gl (hex_id is detected)
  results/hex_map.png            static image for the README
  results/map_summary.json       the numbers quoted in the README

Usage: python analysis/build_map.py --db warehouse/grid.duckdb --year 2025
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import h3
import pandas as pd

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>London Grid Reliability Map</title>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
<script src="https://unpkg.com/h3-js@4.1.0/dist/h3-js.umd.js"></script>
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<script src="https://unpkg.com/deck.gl@9.0.38/dist.min.js"></script>
<style>
  :root { --bg: #ffffff; --fg: #1f2933; --muted: #52606d; --panel: rgba(255,255,255,0.94); --border: #d9e2ec; }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #0f1720; --fg: #e4e7eb; --muted: #9aa5b1; --panel: rgba(15,23,32,0.94); --border: #323f4b; } }
  :root[data-theme="dark"] { --bg: #0f1720; --fg: #e4e7eb; --muted: #9aa5b1; --panel: rgba(15,23,32,0.94); --border: #323f4b; }
  html, body { margin: 0; height: 100%; background: var(--bg); color: var(--fg); font: 14px/1.45 system-ui, -apple-system, Segoe UI, sans-serif; }
  #map { position: absolute; inset: 0; }
  .panel { position: absolute; top: 12px; left: 12px; max-width: min(360px, calc(100vw - 48px)); background: var(--panel);
           border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; z-index: 2; }
  .panel h1 { font-size: 16px; margin: 0 0 6px; } .panel p { margin: 4px 0; color: var(--muted); }
  .legend { display: flex; height: 10px; border-radius: 3px; overflow: hidden; margin: 8px 0 2px; }
  .legend span { flex: 1; } .scale { display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); }
  label { display: block; margin-top: 6px; font-size: 13px; } .tag { font-weight: 600; color: var(--fg); }
</style></head>
<body>
<div id="map"></div>
<div class="panel">
  <h1>London grid reliability, __YEAR__</h1>
  <p>Customer minutes lost (CML) per customer, by H3 hex (resolution 8). Customers: Census 2021 households.
     Network: OpenStreetMap primary substations. Outages: <span class="tag">synthetic</span> history; dots are
     <span class="tag">real</span> UK Power Networks outages at download time.</p>
  <div class="legend">__LEGEND__</div><div class="scale"><span>0</span><span>__MID__ min</span><span>__MAX__+ min</span></div>
  <label><input type="checkbox" id="subs" checked> Primary substations (__NSUBS__)</label>
  <label><input type="checkbox" id="live" checked> Real outages (__NLIVE__)</label>
  <p>London overall: __CI__ interruptions per 100 customers, __CML__ minutes lost per customer.</p>
</div>
<script>
const HEX = __HEX__, SUBS = __SUBS__, LIVE = __LIVE__, COLORS = __COLORS__, MAX = __MAXV__;
const color = v => COLORS[Math.min(COLORS.length - 1, Math.floor(v / MAX * COLORS.length))];
const map = new maplibregl.Map({ container: "map", style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
  center: [-0.11, 51.51], zoom: 10.3 });
const overlay = new deck.MapboxOverlay({ interleaved: false, getTooltip: ({object}) => object && (object.hex
  ? `${object.households.toLocaleString()} households\\nCML ${object.cml.toFixed(1)} min · CI ${object.ci.toFixed(1)} per 100`
  : object.name ? `${object.name}\\n${object.customers.toLocaleString()} customers mapped` : `${object.feed}: ${object.type}`) });
map.addControl(overlay);
function render() {
  overlay.setProps({ layers: [
    new deck.H3HexagonLayer({ id: "hex", data: HEX, getHexagon: d => d.hex, getFillColor: d => color(d.cml),
      extruded: false, opacity: 0.72, pickable: true, stroked: false }),
    document.getElementById("subs").checked && new deck.ScatterplotLayer({ id: "subs", data: SUBS,
      getPosition: d => [d.lon, d.lat], getRadius: 140, radiusMinPixels: 3, getFillColor: [33, 37, 41], pickable: true }),
    document.getElementById("live").checked && new deck.ScatterplotLayer({ id: "live", data: LIVE,
      getPosition: d => [d.lon, d.lat], getRadius: 220, radiusMinPixels: 5, getFillColor: [0, 160, 200], stroked: true,
      getLineColor: [255, 255, 255], lineWidthMinPixels: 1, pickable: true }),
  ].filter(Boolean) });
}
document.querySelectorAll("input").forEach(i => i.addEventListener("change", render));
render();
</script></body></html>
"""
# sequential, light to dark (colour-blind safe)
COLORS = [[255, 245, 235], [254, 230, 206], [253, 208, 162], [253, 174, 107], [253, 141, 60], [241, 105, 19],
          [217, 72, 1], [166, 54, 3], [127, 39, 4]]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="warehouse/grid.duckdb")
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--resolution", type=int, default=8)
    ap.add_argument("--map", type=Path, default=Path("map/index.html"))
    ap.add_argument("--results", type=Path, default=Path("results"))
    args = ap.parse_args()
    con = duckdb.connect(args.db, read_only=True)
    lsoa = con.execute("select * from gold.rpt_lsoa_reliability where year = ?", [args.year]).df()
    subs = con.execute("select primary_id, primary_name as name, lon, lat, customers from gold.dim_primary_substation").df()
    live = con.execute("select feed, outage_type as type, lon, lat from gold.rpt_live_outages").df()
    feeders = con.execute("""select 100.0 * sum(customers_interrupted) / sum(customers_served) as ci,
                                    1.0 * sum(customer_minutes_lost) / sum(customers_served) as cml
                             from gold.rpt_feeder_reliability where year = ?""", [args.year]).fetchone()

    lsoa["hex"] = [h3.latlng_to_cell(lat, lon, args.resolution) for lat, lon in zip(lsoa.lat, lsoa.lon)]
    hexes = lsoa.groupby("hex").agg(households=("households", "sum"), cmin=("customer_minutes_lost", "sum"),
                                    cint=("customers_interrupted", "sum"), lsoas=("lsoa_code", "count")).reset_index()
    hexes["cml"] = hexes.cmin / hexes.households
    hexes["ci"] = 100 * hexes.cint / hexes.households
    vmax = float(hexes.cml.quantile(0.95))

    args.results.mkdir(parents=True, exist_ok=True)
    hexes.rename(columns={"hex": "hex_id"})[["hex_id", "households", "lsoas", "cml", "ci"]].round(3) \
        .to_csv(args.results / "hex_reliability.csv", index=False)

    worst = hexes.sort_values("cml", ascending=False)
    top_decile = worst.head(max(1, len(worst) // 10))
    summary = {"year": args.year, "resolution": args.resolution, "hexes": len(hexes), "lsoas": len(lsoa),
               "households": int(hexes.households.sum()), "london_ci_per_100": round(feeders[0], 1),
               "london_cml": round(feeders[1], 1), "hex_cml_median": round(float(hexes.cml.median()), 1),
               "hex_cml_p95": round(vmax, 1), "worst_decile_hexes": len(top_decile),
               "worst_decile_households": int(top_decile.households.sum()),
               "worst_decile_cml": round(float(top_decile.cmin.sum() / top_decile.households.sum()), 1)}
    (args.results / "map_summary.json").write_text(json.dumps(summary, indent=1))

    legend = "".join(f'<span style="background: rgb({r},{g},{b})"></span>' for r, g, b in COLORS)
    html = (TEMPLATE.replace("__YEAR__", str(args.year)).replace("__LEGEND__", legend)
            .replace("__MID__", f"{vmax / 2:.0f}").replace("__MAX__", f"{vmax:.0f}")
            .replace("__NSUBS__", str(len(subs))).replace("__NLIVE__", str(len(live)))
            .replace("__CI__", f"{feeders[0]:.1f}").replace("__CML__", f"{feeders[1]:.1f}")
            .replace("__HEX__", hexes[["hex", "households", "cml", "ci"]].round(2).to_json(orient="records"))
            .replace("__SUBS__", subs[["name", "lon", "lat", "customers"]].to_json(orient="records"))
            .replace("__LIVE__", live.to_json(orient="records"))
            .replace("__COLORS__", json.dumps(COLORS)).replace("__MAXV__", f"{vmax:.2f}"))
    args.map.parent.mkdir(parents=True, exist_ok=True)
    args.map.write_text(html, encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import LinearSegmentedColormap

    cmap = LinearSegmentedColormap.from_list("cml", [[c / 255 for c in rgb] for rgb in COLORS])
    polys = [[(lng, lat) for lat, lng in h3.cell_to_boundary(h)] for h in hexes.hex]
    fig, ax = plt.subplots(figsize=(9, 6.5), dpi=130)
    pc = PolyCollection(polys, array=hexes.cml.clip(upper=vmax), cmap=cmap, edgecolors="none")
    ax.add_collection(pc)
    ax.scatter(subs.lon, subs.lat, s=6, c="#212529", label="Primary substations (OSM)")
    ax.scatter(live.lon, live.lat, s=18, c="#00a0c8", edgecolors="white", linewidths=0.5, label="Real outages (UKPN, snapshot)")
    ax.autoscale_view()
    ax.set_aspect(1 / 0.62)
    ax.set_axis_off()
    fig.colorbar(pc, ax=ax, shrink=0.6, label=f"Customer minutes lost per customer, {args.year}")
    ax.legend(loc="lower left", frameon=False, fontsize=8)
    ax.set_title(f"London: customer minutes lost by H3 hex (synthetic outages, real customers and network)", fontsize=10)
    fig.tight_layout()
    fig.savefig(args.results / "hex_map.png")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
