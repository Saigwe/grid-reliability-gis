# Design doc: Grid Reliability GIS (London)

| | |
|---|---|
| **Author** | Stanley Igwe |
| **Status** | Core build complete on open London data |
| **Last updated** | 2026-10-26 |

## 1. Problem and users
- **Users:** network operations and asset managers at a distribution company; regulatory reporting teams.
- **Questions they need answered:** Which substations and neighbourhoods are worst served? Are we inside the regulator's targets? How far can we trust the asset map?
- **Current pain (scenario):** reliability is reported for the whole network each year, so a run of bad months on one substation is invisible, and the GIS is missing assets nobody has measured.

## 2. Requirements
| Type | Requirement |
|---|---|
| Functional | Customers placed on the network, SAIDI and SAIFI by substation and month, hex map of the worst-served areas. |
| Correctness | Regulatory rules (3-minute threshold, planned works excluded); every household mapped exactly once; views reconcile. |
| Portability | The same models on a laptop (DuckDB spatial) and on a production spatial database (PostGIS). |
| Scale | 2,914 LSOAs x 78 primaries today; at national scale, nearest-neighbour moves to a spatial index (PostGIS `<->`, or H3 candidate rings). |

## 3. Design
- **Layers:** raw downloads → bronze (coordinates and WKT text only, engine-neutral) → silver (geometries in British National Grid, customer-to-substation map) → gold (interruptions, indices, hex inputs).
- **Key choices:** distances are measured in British National Grid metres, not degrees. Customers are households at population-weighted LSOA centroids. The synthetic outages are generated on the real customer map, so the indices follow the network's real shape.

## 4. Options considered
| Decision | Options | Chosen | Why |
|---|---|---|---|
| Network source | UKPN asset registers; OSM | OSM (+ UKPN counts to check it) | The registers need an account; OSM is open, and its coverage is measured, not assumed. |
| Customer locations | Address points; postcode centroids; LSOA centroids + Census households | LSOA centroids + households | Open, complete, and population-weighted. |
| Spatial engine | PostGIS only; DuckDB only; both | Both, through macros | Fast local work, production-grade target, one codebase. |
| Hex system | Grid squares; H3 | H3 resolution 8 | Equal-area hexes, a standard id kepler.gl and deck.gl read directly. |
| Map | kepler.gl app; deck.gl page | deck.gl page + kepler.gl CSV | A shareable, self-contained page, with the CSV for kepler.gl users. |

## 5. Risks and what I'd change at 10x scale
- Nearest-substation is a proxy; OSM misses 25% of primaries, so some primaries absorb far too many customers. Real connectivity data is the fix.
- The outage history is synthetic; collecting UKPN's live feed on a schedule would build a real one.
- At 10x: PostGIS with spatial indexes, H3-indexed candidate search for nearest assets, and incremental monthly builds.
