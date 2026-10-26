"""Copy the bronze tables from the DuckDB file into PostGIS, so the same dbt project builds its spatial models there.
Geometry travels as longitude/latitude and WKT text; dbt builds the PostGIS geometries. Uses the PG* variables.

Usage: python ingestion/copy_bronze_to_postgis.py --db warehouse/fixture.duckdb
"""
from __future__ import annotations

import argparse
import os

import duckdb


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()
    dsn = " ".join(f"{k}={os.environ[v]}" for k, v in [("host", "PGHOST"), ("port", "PGPORT"), ("user", "PGUSER"),
                                                        ("password", "PGPASSWORD"), ("dbname", "PGDATABASE")] if v in os.environ)
    con = duckdb.connect()
    con.execute(f"attach '{args.db}' as src (read_only)")
    con.execute("install postgres; load postgres")
    con.execute(f"attach '{dsn}' as pg (type postgres)")
    con.execute("call postgres_execute('pg', 'create extension if not exists postgis')")
    con.execute("call postgres_execute('pg', 'create schema if not exists bronze')")
    for (table,) in con.execute("select table_name from duckdb_tables() where database_name = 'src' and schema_name = 'bronze'").fetchall():
        con.execute(f"drop table if exists pg.bronze.{table}")
        con.execute(f"create table pg.bronze.{table} as select * from src.bronze.{table}")
        print(f"pg bronze.{table}: {con.execute(f'select count(*) from pg.bronze.{table}').fetchone()[0]:,} rows")


if __name__ == "__main__":
    main()
