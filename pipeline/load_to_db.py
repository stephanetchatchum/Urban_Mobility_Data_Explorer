"""Stage 2: load the cleaned trips and the cleaning log into MySQL.

Run from the repository root, after `python -m pipeline.run_pipeline`:
    python -m pipeline.load_to_db --check              # only test the connection and the table columns
    python -m pipeline.load_to_db --limit-rows 200000  # load a small sample first
    python -m pipeline.load_to_db                      # load everything
    python -m pipeline.load_to_db --truncate           # empty the tables first, then load

Connection settings are read from environment variables (see config.py):
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, and DB_SSL_CA (optional)
"""
import argparse
import sys
import time

import pandas as pd
import pyarrow.parquet as pq
import pymysql

from . import config as cfg
from .reasons import REASONS

BATCH_ROWS = 5_000   # rows sent to MySQL in one go; small enough to stay under its packet size limit

# In each dictionary below: the left side is the column name in our files, and the right side
# is the column name in the MySQL table. If the table uses another name, change only the right side.
TRIPS_TABLE = "trips"
TRIP_COLUMNS = {
    "trip_id": "trip_id", "vendor_id": "vendor_id", "pickup_ts": "pickup_datetime", "dropoff_ts": "dropoff_datetime",
    "passenger_count": "passenger_count", "trip_distance_mi": "trip_distance",
    "rate_code_id": "rate_code_id", "store_and_fwd": "store_and_fwd",
    "pu_location_id": "pickup_zone_id", "do_location_id": "dropoff_zone_id",
    "payment_type_id": "payment_type_id", "fare_amount": "fare_amount", "extra": "extra",
    "mta_tax": "mta_tax", "tip_amount": "tip_amount", "tolls_amount": "tolls_amount",
    "improvement_surcharge": "improvement_surcharge", "congestion_surcharge": "congestion_surcharge",
    "total_amount": "total_amount", "duration_min": "duration_min", "avg_speed_mph": "speed_mph",
    "min_per_mile": "min_per_mile", "fare_per_mile": "fare_per_mile", "fare_per_min": "fare_per_min",
    "pickup_date": "pickup_date", "pickup_hour": "pickup_hour", "pickup_dow": "pickup_dow",
    "is_weekend": "is_weekend", "is_flat_fare": "is_flat_fare",
    "flag_unknown_zone": "flag_unknown_zone", "flag_passenger_suspect": "flag_passenger_suspect",
    "flag_low_speed": "flag_low_speed", "flag_total_mismatch": "flag_total_mismatch",
}
REASONS_TABLE = "exclusion_reasons"
REASON_COLUMNS = {"reason_code": "reason_code", "action": "action", "description": "description"}
SUMMARY_TABLE = "cleaning_summary"
SUMMARY_COLUMNS = {"reason_code": "reason_code", "rows": "row_count", "pct_of_raw": "pct_of_raw"}
LOG_TABLE = "exclusion_log"
LOG_COLUMNS = {
    "source_row": "source_row", "reason_code": "reason_code", "pickup_ts": "pickup_ts",
    "dropoff_ts": "dropoff_ts", "trip_distance_mi": "trip_distance_mi", "fare_amount": "fare_amount",
    "pu_location_id": "pu_location_id", "do_location_id": "do_location_id",
}
DATETIME_COLUMNS = ("pickup_ts", "dropoff_ts")


def connect():
    """Open a connection to MySQL using the settings from config.py."""
    settings = dict(host=cfg.DB_HOST, port=cfg.DB_PORT, user=cfg.DB_USER, password=cfg.DB_PASSWORD,
                    database=cfg.DB_NAME, charset="utf8mb4", autocommit=False)
    if cfg.DB_SSL_CA:
        settings["ssl"] = {"ca": cfg.DB_SSL_CA}
    return pymysql.connect(**settings)


def table_columns(conn, table):
    """Return the set of column names of a table, or None if the table does not exist."""
    with conn.cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = %s AND table_name = %s", (cfg.DB_NAME, table))
        names = {row[0].lower() for row in cur.fetchall()}
    return names or None


def check_table(conn, table, mapping, required):
    """Check that the table exists and has every column we want to fill. Return True if it is usable."""
    present = table_columns(conn, table)
    if present is None:
        message = f"table '{table}' not found in database '{cfg.DB_NAME}'"
        if required:
            sys.exit(f"ERROR: {message}. Run schema.sql first.")
        print(f"  SKIPPED: {message}. Ask Member 2 to add it (see database/pipeline_tables.sql).")
        return False
    missing = [c for c in mapping.values() if c.lower() not in present]
    if missing:
        sys.exit(f"ERROR: table '{table}' has no column(s): {', '.join(missing)}.\n"
                 f"Add them to the table, or change the right-hand side of the column dictionary "
                 f"in pipeline/load_to_db.py.")
    unfilled = sorted(present - {c.lower() for c in mapping.values()})
    note = f" (columns this loader does not fill: {', '.join(unfilled)})" if unfilled else ""
    print(f"  OK: {table}{note}")
    return True


def to_rows(df):
    """Turn a DataFrame into a list of tuples that MySQL accepts: empty values become NULL."""
    df = df.copy()
    for col in DATETIME_COLUMNS:
        if col in df:
            df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S") if hasattr(df[col], "dt") else df[col]
    objects = df.astype(object).where(df.notna(), None)
    return list(objects.itertuples(index=False, name=None))


def insert_rows(conn, table, db_columns, rows):
    names = ", ".join(f"`{c}`" for c in db_columns)
    marks = ", ".join(["%s"] * len(db_columns))
    with conn.cursor() as cur:
        cur.executemany(f"INSERT INTO `{table}` ({names}) VALUES ({marks})", rows)


def truncate(conn, table):
    with conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        cur.execute(f"TRUNCATE TABLE `{table}`")
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()


def load_reasons(conn):
    frame = pd.DataFrame([(code, action, text) for code, (action, text) in REASONS.items()],
                         columns=list(REASON_COLUMNS))
    insert_rows(conn, REASONS_TABLE, list(REASON_COLUMNS.values()), to_rows(frame))
    conn.commit()
    print(f"  {REASONS_TABLE}: {len(frame)} rows")


def load_summary(conn):
    frame = pd.read_csv(cfg.LOGS_DIR / "cleaning_summary.csv")[list(SUMMARY_COLUMNS)]
    insert_rows(conn, SUMMARY_TABLE, list(SUMMARY_COLUMNS.values()), to_rows(frame))
    conn.commit()
    print(f"  {SUMMARY_TABLE}: {len(frame)} rows")


def load_log(conn):
    frame = pd.read_csv(cfg.LOGS_DIR / "exclusion_log.csv")[list(LOG_COLUMNS)]
    for col in ("source_row", "pu_location_id", "do_location_id"):
        frame[col] = frame[col].astype("Int64")        # keeps whole numbers even when some are empty
    total = 0
    for start in range(0, len(frame), BATCH_ROWS):
        part = frame.iloc[start:start + BATCH_ROWS]
        insert_rows(conn, LOG_TABLE, list(LOG_COLUMNS.values()), to_rows(part))
        conn.commit()
        total += len(part)
    print(f"  {LOG_TABLE}: {total:,} rows")


def load_trips(conn, limit_rows=None):
    parquet = pq.ParquetFile(cfg.PROCESSED_DIR / "clean_trips.parquet")
    total, started = 0, time.time()
    for batch in parquet.iter_batches(batch_size=BATCH_ROWS, columns=list(TRIP_COLUMNS)):
        frame = batch.to_pandas()
        if limit_rows is not None:
            frame = frame.iloc[: limit_rows - total]
        insert_rows(conn, TRIPS_TABLE, list(TRIP_COLUMNS.values()), to_rows(frame))
        conn.commit()
        total += len(frame)
        if (total // BATCH_ROWS) % 20 == 0:
            speed = total / max(time.time() - started, 1e-9)
            print(f"    trips loaded: {total:>10,}   ({speed:,.0f} rows per second)")
        if limit_rows is not None and total >= limit_rows:
            break
    print(f"  {TRIPS_TABLE}: {total:,} rows in {time.time() - started:,.0f} s")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="only test the connection and the table columns")
    parser.add_argument("--limit-rows", type=int, help="load only the first N trips (a sample)")
    parser.add_argument("--truncate", action="store_true", help="empty the tables before loading")
    args = parser.parse_args()

    try:
        conn = connect()
    except pymysql.err.OperationalError as error:
        sys.exit(f"ERROR: cannot connect to MySQL at {cfg.DB_HOST}:{cfg.DB_PORT} as '{cfg.DB_USER}' ({error}).\n"
                 f"Check the DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME (and DB_SSL_CA) settings.")
    print(f"Connected to {cfg.DB_HOST}:{cfg.DB_PORT}/{cfg.DB_NAME}")

    print("Checking the tables")
    has_reasons = check_table(conn, REASONS_TABLE, REASON_COLUMNS, required=False)
    has_summary = check_table(conn, SUMMARY_TABLE, SUMMARY_COLUMNS, required=False)
    has_log = check_table(conn, LOG_TABLE, LOG_COLUMNS, required=False)
    check_table(conn, TRIPS_TABLE, TRIP_COLUMNS, required=True)
    if args.check:
        conn.close()
        return

    if args.truncate:
        for table, exists in ((LOG_TABLE, has_log), (SUMMARY_TABLE, has_summary), (REASONS_TABLE, has_reasons),
                              (TRIPS_TABLE, True)):
            if exists:
                truncate(conn, table)
        print("Tables emptied")

    print("Loading")
    try:
        if has_reasons:
            load_reasons(conn)
        if has_reasons and has_summary:
            load_summary(conn)
        if has_reasons and has_log:
            load_log(conn)
        load_trips(conn, args.limit_rows)
    except pymysql.err.IntegrityError as error:
        conn.rollback()
        sys.exit(f"ERROR: MySQL rejected a row ({error}).\n"
                 f"If the tables already hold data, run again with --truncate.")
    conn.close()
    print("Done")


if __name__ == "__main__":
    main()
