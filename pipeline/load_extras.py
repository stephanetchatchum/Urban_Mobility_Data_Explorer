"""Stage 4: load the zone geometry facts and the precomputed statistics into MySQL.

Run from the repository root, after load_to_db and build_aggregates:
    python -m pipeline.load_extras

These tables are derived data, so every run empties and refills them (safe to repeat).
"""
import sys

import pandas as pd

from . import config as cfg
from .load_to_db import connect, insert_rows, to_rows, truncate

STATS_TABLES = {
    "zone_hour_stats": "zone_hour_stats.csv",
    "hour_stats": "hour_stats.csv",
    "daily_stats": "daily_stats.csv",
    "econ_hour": "econ_hour_stats.csv",
}


def load_zone_geometry(conn):
    """Add area, centroid and is_mappable to the zones that Member 2's init_db already inserted."""
    zones = pd.read_csv(cfg.PROCESSED_DIR / "zones_dim.csv")
    cols = ["area_km2", "centroid_lat", "centroid_lon", "has_geometry", "is_mappable", "location_id"]
    rows = to_rows(zones[cols].astype({"has_geometry": int, "is_mappable": int}))
    with conn.cursor() as cur:
        cur.executemany("UPDATE zones SET area_km2=%s, centroid_lat=%s, centroid_lon=%s, "
                        "has_geometry=%s, is_mappable=%s WHERE location_id=%s", rows)
        updated = cur.rowcount
    conn.commit()
    print(f"  zones: geometry added to {len(zones)} zones ({updated} rows changed)")


def load_stats(conn, table, csv_name):
    frame = pd.read_csv(cfg.PROCESSED_DIR / csv_name)
    truncate(conn, table)
    for start in range(0, len(frame), 5_000):
        insert_rows(conn, table, list(frame.columns), to_rows(frame.iloc[start:start + 5_000]))
    conn.commit()
    print(f"  {table}: {len(frame):,} rows")


def main():
    conn = connect()
    print("Loading zone geometry and statistics")
    for name in list(STATS_TABLES.values()) + ["zones_dim.csv"]:
        if not (cfg.PROCESSED_DIR / name).exists():
            sys.exit(f"ERROR: data/processed/{name} not found. Run run_pipeline and build_aggregates first.")
    load_zone_geometry(conn)
    for table, csv_name in STATS_TABLES.items():
        load_stats(conn, table, csv_name)
    conn.close()
    print("Done")


if __name__ == "__main__":
    main()
