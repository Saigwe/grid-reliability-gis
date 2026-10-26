"""SYNTHETIC two-year outage history (2024-2025) on the real customer-to-feeder map (fixed seed).

UKPN publishes live outages but not an open fault history, so this script generates one on the real network
model (silver.int_customer_feeder: Census households mapped to OSM primary substations):

  11 kV feeders   each primary's area is split into ~2,500-customer feeders, as angular sectors around it
  HV faults       per feeder, rate x the primary's risk (gamma-distributed, mean 1: some areas are worse served)
                  20% clear by auto-reclose in under 3 minutes (a short interruption: not counted in CI/CML);
                  otherwise ~75% of customers are switched back within about 45 minutes, the rest after repair
  LV faults       per LSOA: 20-150 customers off for about 2 hours
  planned works   per feeder, notified in advance: counted separately, never in CI/CML
  seasonality     winter months 20% above average, summer 10% below

The rates are assumptions chosen so London lands below UK Power Networks' group-wide 2023/24 figures (37.6
interruptions per 100 customers, 29.0 minutes lost), since UKPN reports London as its most reliable network.

Writes bronze.outage_events (one row per outage) and bronze.outage_impacts (customers per outage, LSOA, stage).
Usage: python ingestion/simulate_outages.py --db warehouse/grid.duckdb
"""
from __future__ import annotations

import argparse
import json
import math

import duckdb
import numpy as np
import pandas as pd

SEED = 1818
FEEDER_CUSTOMERS = 2500
HV_PER_FEEDER_YEAR = 0.20
LV_PER_LSOA_YEAR = 0.45
PLANNED_PER_FEEDER_YEAR = 0.30
SEASON = {1: 1.2, 2: 1.2, 3: 1.0, 4: 1.0, 5: 0.9, 6: 0.9, 7: 0.9, 8: 0.9, 9: 1.0, 10: 1.0, 11: 1.2, 12: 1.2}
CAUSES_HV = ["cable fault", "joint failure", "switchgear", "third-party damage"]
CAUSES_LV = ["cable fault", "service cut-out", "fuse", "third-party damage"]


def months(start: str, end: str) -> list[pd.Timestamp]:
    return list(pd.date_range(start, end, freq="MS"))


def random_time(rng, month: pd.Timestamp) -> pd.Timestamp:
    return month + pd.Timedelta(seconds=int(rng.integers(0, month.days_in_month * 86400)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="warehouse/grid.duckdb")
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2025-12-01")
    args = ap.parse_args()
    rng = np.random.default_rng(SEED)
    con = duckdb.connect(args.db)
    cust = con.execute("""
        select c.lsoa_code, c.households, c.primary_id, c.lon, c.lat, p.lon as p_lon, p.lat as p_lat
        from silver.int_customer_feeder c join silver.int_primary_substations p using (primary_id)
        order by c.primary_id, c.lsoa_code
    """).df()

    # 11 kV feeders: sectors around each primary, about FEEDER_CUSTOMERS customers each
    cust["angle"] = np.arctan2(cust.lat - cust.p_lat, (cust.lon - cust.p_lon) * math.cos(math.radians(51.5)))
    feeders = []
    for pid, g in cust.sort_values(["primary_id", "angle"]).groupby("primary_id"):
        n = max(1, round(g.households.sum() / FEEDER_CUSTOMERS))
        cut = np.minimum((g.households.cumsum() - 1) // (g.households.sum() / n), n - 1).astype(int)
        feeders.append(g.assign(feeder_id=[f"{pid}#F{k + 1:02d}" for k in cut]))
    cust = pd.concat(feeders)
    risk = {p: r for p, r in zip(cust.primary_id.unique(), rng.gamma(2.0, 0.5, cust.primary_id.nunique()))}

    events, impacts, n = [], [], 0
    def new_event(primary, level, planned, cause, start):
        nonlocal n
        n += 1
        oid = f"OUT{n:07d}"
        events.append((oid, primary, level, planned, cause, start))
        return oid

    for month in months(args.start, args.end):
        s = SEASON[month.month] / 12
        for (pid, fid), g in cust.groupby(["primary_id", "feeder_id"]):
            for _ in range(rng.poisson(HV_PER_FEEDER_YEAR * risk[pid] * s)):
                start = random_time(rng, month)
                oid = new_event(pid, "HV", False, str(rng.choice(CAUSES_HV)), start)
                if rng.random() < 0.2:  # auto-reclose: everyone back within 3 minutes
                    back = start + pd.Timedelta(seconds=int(rng.integers(5, 170)))
                    impacts += [(oid, l, 1, h, back) for l, h in zip(g.lsoa_code, g.households)]
                    continue
                switched = start + pd.Timedelta(minutes=float(rng.lognormal(math.log(45), 0.5)))
                repaired = switched + pd.Timedelta(minutes=float(rng.lognormal(math.log(150), 0.5)))
                for l, h in zip(g.lsoa_code, g.households):
                    first = int(round(h * rng.uniform(0.65, 0.85)))
                    impacts.append((oid, l, 1, first, switched))
                    if h - first > 0:
                        impacts.append((oid, l, 2, h - first, repaired))
            for _ in range(rng.poisson(PLANNED_PER_FEEDER_YEAR * s)):
                start = random_time(rng, month).floor("h")
                oid = new_event(pid, "HV", True, "planned works", start)
                l, h = g.sample(1, random_state=int(rng.integers(1e9)))[["lsoa_code", "households"]].iloc[0]
                impacts.append((oid, l, 1, int(min(h, rng.integers(50, 300))),
                                start + pd.Timedelta(minutes=int(rng.integers(240, 480)))))
        for l, h, pid in zip(cust.lsoa_code, cust.households, cust.primary_id):
            for _ in range(rng.poisson(LV_PER_LSOA_YEAR * risk[pid] * s)):
                start = random_time(rng, month)
                oid = new_event(pid, "LV", False, str(rng.choice(CAUSES_LV)), start)
                impacts.append((oid, l, 1, int(min(h, rng.integers(20, 151))),
                                start + pd.Timedelta(minutes=float(rng.lognormal(math.log(110), 0.6)))))

    ev = pd.DataFrame(events, columns=["outage_id", "primary_id", "voltage_level", "planned", "cause", "started_at"])
    im = pd.DataFrame(impacts, columns=["outage_id", "lsoa_code", "stage", "customers", "restored_at"])
    im = im[im.customers > 0]
    con.execute("create schema if not exists bronze")
    con.execute("create or replace table bronze.outage_events as select * from ev")
    con.execute("create or replace table bronze.outage_impacts as select * from im")
    feeders_n = cust.feeder_id.nunique()
    print(json.dumps({"primaries": int(cust.primary_id.nunique()), "feeders": feeders_n, "outages": len(ev),
                      "impact_rows": len(im),
                      "by_level": {f"{lvl}{' planned' if pl else ''}": int(c)
                                   for (lvl, pl), c in ev.groupby(["voltage_level", "planned"]).size().items()}}))


if __name__ == "__main__":
    main()
