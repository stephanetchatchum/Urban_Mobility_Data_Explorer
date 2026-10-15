import argparse
import json
import time
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from . import config as cfg
from .clean_data import DuplicateTracker, clean_chunk, standardize
from .load_data import find_input, iter_raw_chunks
from .reasons import REASONS
from .zones_to_geojson import build_zone_assets


LOG_COLUMNS = ["source_row", "reason_code", "pickup_ts", "dropoff_ts", "trip_distance_mi",
               "fare_amount", "pu_location_id", "do_location_id"]

def run(input_path=None, lookup_csv=None, shapefile=None, out_dir=None, logs_dir=None,
        chunk_size=cfg.DEFAULT_CHUNK_SIZE, limit_rows=None) -> dict:
    t0 = time.time()
    input_path = Path(input_path) if input_path else find_input(cfg.RAW_DIR)
    lookup_csv = Path(lookup_csv) if lookup_csv else cfg.RAW_DIR / "taxi_zone_lookup.csv"
    shapefile = Path(shapefile) if shapefile else cfg.RAW_DIR / "taxi_zones.shp"
    out_dir = Path(out_dir) if out_dir else cfg.PROCESSED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = Path(logs_dir) if logs_dir else cfg.LOGS_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] Building zone assets from {lookup_csv.name} + {shapefile.name}")
    zones = build_zone_assets(lookup_csv, shapefile, out_dir)
    valid_zones = set(zones["location_id"])

    print(f"[2/3] Cleaning {input_path.name} in chunks of {chunk_size:,} rows")
    tracker = DuplicateTracker()
    writer, schema = None, None
    parquet_path, log_path = out_dir / "clean_trips.parquet", logs_dir / "exclusion_log.csv"

    if log_path.exists():
        log_path.unlink()
    totals = {code: 0 for code in REASONS}
    raw_zh, raw_daily = [], []
    n_raw = n_excluded = n_kept = 0


    for chunk in iter_raw_chunks(input_path, chunk_size):
        if limit_rows is not None and n_raw >= limit_rows:
            break
        if limit_rows is not None:
            chunk = chunk.iloc[: limit_rows - n_raw]
        dup_mask = tracker.mark(standardize(chunk))
        res = clean_chunk(chunk, first_row=n_raw + 1, valid_zone_ids=valid_zones, duplicate_mask=dup_mask)
        n_raw += res.n_raw
        n_excluded += res.n_excluded
        n_kept += len(res.clean)

        for code, c in res.reason_counts.items():
            totals[code] += c
        raw_zh.append(res.raw_zone_hour)
        raw_daily.append(res.raw_daily)

        if len(res.clean):
            table = pa.Table.from_pandas(res.clean, preserve_index=False)
            if writer is None:
                schema = table.schema
                writer = pq.ParquetWriter(parquet_path, schema, compression="snappy")
            writer.write_table(table.cast(schema))

        if len(res.excluded_log):
            res.excluded_log[LOG_COLUMNS].to_csv(log_path, mode="a", index=False, header=not log_path.exists())
        print(f"    rows read: {n_raw:>10,}   kept: {n_kept:>10,}   excluded: {n_excluded:>9,}")

    if writer is not None:
        writer.close()
    if not log_path.exists():
        pd.DataFrame(columns=LOG_COLUMNS).to_csv(log_path, index= False)

    print("[3/3] Writing summaries")
    pd.concat(raw_zh).groupby(["pu_location_id", "pickup_hour", "day_type"], as_index=False).sum() \
        .to_csv(out_dir / "raw_zone_hour_agg.csv", index=False)
    pd.concat(raw_daily).groupby("pickup_date", as_index=False).sum() \
        .to_csv(out_dir / "raw_daily_agg.csv", index=False)
    summary = pd.DataFrame([
        {"reason_code": code, "action": action, "description": desc, "rows": totals[code],
         "pct_of_raw": round(100.0 * totals[code] / n_raw, 4) if n_raw else 0.0}
        for code, (action, desc) in REASONS.items()])
    summary.to_csv(logs_dir / "cleaning_summary.csv", index=False)


    report = {
        "input_file": input_path.name, "raw_rows": n_raw, "kept_rows": n_kept,
        "excluded_rows": n_excluded, "excluded_pct": round(100.0 * n_excluded / n_raw, 4) if n_raw else 0.0,
        "rows_flagged_unknown_zone": totals["UNKNOWN_ZONE"],
        "thresholds": {k: getattr(cfg, k) for k in (
            "MAX_DURATION_MIN", "MAX_SPEED_MPH", "MAX_DISTANCE_MI", "MAX_FARE_USD",
            "LOW_SPEED_FLAG_MPH", "TOTAL_TOLERANCE_USD", "MAX_PASSENGERS")},
        "data_start": cfg.DATA_START.isoformat(), "data_end_exclusive": cfg.DATA_END.isoformat(),
        "runtime_seconds": round(time.time() - t0, 1),
    }
    (logs_dir / "cleaning_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Done: {n_raw:,} read, {n_kept:,} kept, {n_excluded:,} excluded ({report['excluded_pct']}%)"
          f" in {report['runtime_seconds']} s")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", help="trip file (.parquet or .csv); default: auto-detect in data/raw/")
    p.add_argument("--lookup", help="taxi_zone_lookup.csv")
    p.add_argument("--shapefile", help="taxi_zones.shp")
    p.add_argument("--out", help="output directory (default data/processed)")
    p.add_argument("--logs", help="log directory (default data/logs)")
    p.add_argument("--chunk-size", type=int, default=cfg.DEFAULT_CHUNK_SIZE)
    p.add_argument("--limit-rows", type=int, help="process only the first N rows (testing)")
    a = p.parse_args()
    run(a.input, a.lookup, a.shapefile, a.out, a.logs, a.chunk_size, a.limit_rows)


if __name__ == "__main__":
    main()
    