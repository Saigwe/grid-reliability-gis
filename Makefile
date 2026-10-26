PY ?= python
RAW ?= data/raw
DB ?= warehouse/grid.duckdb
RESULTS ?= results
MAP ?= map/index.html
DBT_BIN ?= dbt
DBT = cd dbt && DUCKDB_PATH=../$(DB) $(DBT_BIN)

.PHONY: all fetch load network simulate dbt map test fixture-all postgis-fixture clean

all: load network simulate dbt map test   ## real open data (run `make fetch` once first)

fetch:      ## UKPN, ONS/Nomis and OSM downloads (about 10 MB), cached in data/raw
	$(PY) ingestion/fetch.py --raw $(RAW)

load:
	mkdir -p $(dir $(DB))
	$(PY) ingestion/load.py --raw $(RAW) --db $(DB)

network:    ## phase 1: customers mapped to the nearest primary substation
	$(DBT) build --profiles-dir . --select +int_customer_feeder --exclude stg_outages --indirect-selection cautious

simulate:   ## SYNTHETIC outage history on the real customer-to-feeder map
	$(PY) ingestion/simulate_outages.py --db $(DB)

dbt:        ## phase 2: everything, outages included
	$(DBT) build --profiles-dir .

map:
	$(PY) analysis/build_map.py --db $(DB) --map $(MAP) --results $(RESULTS)

test:
	GRID_RESULTS=$(RESULTS) $(PY) -m pytest -q tests

fixture-all:   ## synthetic files in the real formats, through the same pipeline (CI)
	$(PY) tests/fixtures/make_fixture.py --raw data/fixture/raw
	$(MAKE) all RAW=data/fixture/raw DB=warehouse/fixture.duckdb RESULTS=data/fixture/results MAP=data/fixture/map/index.html

postgis-fixture: fixture-all   ## then the same dbt project on PostGIS (PG* env vars)
	$(PY) ingestion/copy_bronze_to_postgis.py --db warehouse/fixture.duckdb
	cd dbt && DBT_TARGET=postgis $(DBT_BIN) build --profiles-dir .

clean:
	rm -rf warehouse dbt/target dbt/logs data/fixture
