# Ingestion

| Script | Does |
|---|---|
| `fetch.py` | Downloads the open sources once into `data/raw`: UKPN (zones, statistics, live faults, national outages), ONS centroids, Nomis households, OSM via Overpass. |
| `load.py` | Loads them into DuckDB `bronze`, geometry as coordinates and WKT text so dbt can build it on DuckDB or PostGIS. |
| `simulate_outages.py` | SYNTHETIC two-year outage history on the customer-to-substation map (runs after the first dbt phase). |
| `copy_bronze_to_postgis.py` | Copies bronze into PostGIS for the PostGIS build (CI). |
