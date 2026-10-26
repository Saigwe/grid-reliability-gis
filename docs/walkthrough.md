# 3-minute walkthrough: Grid Assets GIS & Reliability (SAIDI/SAIFI)

A timed script for a Loom recording of about 3 minutes (screen plus camera bubble, 1080p). Say it in your own words; the lines are a guide, not a teleprompter.

**Open these tabs before you press record:** Interactive map, README, dbt/models, results/hex_map.png, GitHub Actions (DuckDB + PostGIS).

| Time | On screen | What to say |
|---|---|---|
| 0:00–0:20 | Portfolio card, then the README title | Reliability is reported per network, but customers live in streets. This places 2.04 million London households on the open network map and shows where they're worst served. |
| 0:20–0:45 | README intro and the Data section | At a Nigerian electricity distributor I delivered GIS customer enumeration and asset mapping, and defined the network's reliability KPIs, including SAIDI and SAIFI. This rebuilds it on open London data. No employer data is used. |
| 0:45–1:10 | The interactive map at saigwe.github.io/maps/london-grid-reliability | Each hex shows customer minutes lost. Real UK Power Networks outages sit on top. |
| 1:10–1:35 | The completeness check in Numbers | Before trusting the open map, I measured it: OpenStreetMap has 75% of UKPN's primary substations and 6% of its secondary sites. |
| 1:35–2:00 | The SAIDI/SAIFI models and their unit tests | The regulator's rules are unit-tested: auto-reclose under 3 minutes and planned works never count. |
| 2:00–2:30 | Numbers: worst-served hexes | The worst-served 10% of hexes lose 100 minutes a year, 4.3 times the city average. The outages are synthetic, calibrated below UKPN's published figures, and the same models build on DuckDB and PostGIS in CI. |
| 2:30–2:45 | `docs/design_doc.md`, the options table | The decision I'd defend in an interview: Check the map's completeness against the utility's own counts first, because a missing substation shows up as one primary absorbing 150,000 households. |
| 2:45–3:00 | Back to the README top | For a network operator, that means where to send maintenance money, and how far to trust the map first. The repo, numbers and design doc are linked under the video. |

## Recording checklist
- Close email, chat and notifications. Zoom the browser to 125% so code is readable.
- Run `make fixture-all` once before recording, so CI-style output is fresh if you show it.
- Keep to one take per section; Loom lets you trim. Aim for 2:45 to 3:10.
- Show real numbers on screen as you say them; never estimate on camera.
- Say "synthetic" out loud wherever the README labels data as synthetic.

## After recording
1. Copy the Loom share link.
2. In `README.md`, replace the roadmap line with `- [x] [3-minute Loom walkthrough](<your Loom link>)` and add the link under the title.
3. Add the link to this project's card on saigwe.github.io.
