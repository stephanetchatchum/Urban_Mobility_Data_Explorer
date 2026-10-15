"""Stage 3: precompute the tables the dashboard reads (zone-hour, hour, day), cleaned AND raw.

Run from the repository root, after `python -m pipeline.run_pipeline`:
    python -m pipeline.build_aggregates

Reads : data/processed/clean_trips.parquet, raw_zone_hour_agg.csv, raw_daily_agg.csv
Writes: data/processed/zone_hour_stats.csv, hour_stats.csv, daily_stats.csv, econ_hour_stats.csv

Why medians: a few huge or tiny speeds pull a mean away from what a typical rider experiences.
Why precomputed: MySQL has no MEDIAN, and grouping 7.5 million trips on every click is too slow.
Flat-fare trips (rate code 2) are left out of fare-per-minute, because their price does not depend on time.
"""
import numpy as np
import pandas as pd

from . import config as cfg

NEEDED = ["pu_location_id", "pickup_hour", "pickup_date", "is_weekend", "is_flat_fare",
          "min_per_mile", "avg_speed_mph", "fare_per_min", "fare_per_mile"]


# Columns needed for the economics table (average bill per hour)
ECON_NEEDED = ["pickup_hour", "is_weekend", "payment_type_id", "fare_amount", "tip_amount",
               "total_amount", "fare_per_mile"]


def _prepare(clean: pd.DataFrame) -> pd.DataFrame:
    df = clean[NEEDED].copy()
    df["day_type"] = np.where(df["is_weekend"] == 1, "weekend", "weekday")
    df["fare_per_min_nf"] = df["fare_per_min"].where(df["is_flat_fare"] == 0)
    return df


def _clean_stats(df: pd.DataFrame, keys: list) -> pd.DataFrame:
    return (df.groupby(keys)
              .agg(trips=("avg_speed_mph", "size"),
                   mean_speed_mph=("avg_speed_mph", "mean"),
                   median_speed_mph=("avg_speed_mph", "median"),
                   median_min_per_mile=("min_per_mile", "median"),
                   median_fare_per_min=("fare_per_min_nf", "median"),
                   median_fare_per_mile=("fare_per_mile", "median"))
              .reset_index())


def _add_raw(stats: pd.DataFrame, raw: pd.DataFrame, keys: list) -> pd.DataFrame:
    raw = raw.groupby(keys, as_index=False)[["raw_trips", "raw_speed_n", "raw_speed_sum"]].sum()
    out = stats.merge(raw, on=keys, how="outer")
    for col in ("trips", "raw_trips", "raw_speed_n"):
        out[col] = out[col].fillna(0).astype(int)
    out["raw_mean_speed_mph"] = np.where(out["raw_speed_n"] > 0,
                                         out["raw_speed_sum"] / out["raw_speed_n"].replace(0, np.nan), np.nan)
    out = out.drop(columns=["raw_speed_sum"])
    out["is_reliable"] = (out["trips"] >= cfg.MIN_TRIPS_RELIABLE).astype(int)
    num = out.select_dtypes("float").columns
    out[num] = out[num].round(3)
    return out


def compute_all(clean: pd.DataFrame, raw_zone_hour: pd.DataFrame, raw_daily: pd.DataFrame):
    """Return (zone_hour, hour, daily) DataFrames. All three carry cleaned and raw columns."""
    df = _prepare(clean)
    zk = ["pu_location_id", "pickup_hour", "day_type"]
    zone_hour = _add_raw(_clean_stats(df, zk), raw_zone_hour, zk)
    hk = ["pickup_hour", "day_type"]
    hour = _add_raw(_clean_stats(df, hk), raw_zone_hour.drop(columns="pu_location_id"), hk)
    dk = ["pickup_date"]
    daily = _add_raw(_clean_stats(df, dk), raw_daily, dk)
    return zone_hour, hour, daily


def compute_economics(clean: pd.DataFrame) -> pd.DataFrame:
    """Average bill per pickup hour and day type: fare, fees and the tip rate on card payments.

    fees = total_amount - fare_amount - tip_amount (extra, MTA tax, tolls and surcharges).
    Cash tips are not recorded (they show as 0), so the tip rate uses card trips only (payment_type_id 1).
    """
    df = clean[ECON_NEEDED].copy()
    df["day_type"] = np.where(df["is_weekend"] == 1, "weekend", "weekday")
    df["tip_amount"] = df["tip_amount"].fillna(0)
    df["fees"] = df["total_amount"] - df["fare_amount"] - df["tip_amount"]
    keys = ["pickup_hour", "day_type"]

    bill = (df.groupby(keys)
              .agg(trips=("fare_amount", "size"),
                   avg_fare=("fare_amount", "mean"),
                   avg_fees=("fees", "mean"),
                   avg_fare_per_mile=("fare_per_mile", "mean"))
              .reset_index())
    card = (df[df["payment_type_id"] == 1].groupby(keys)
              .agg(card_trips=("fare_amount", "size"),
                   card_fare=("fare_amount", "sum"),
                   card_tip=("tip_amount", "sum"))
              .reset_index())

    out = bill.merge(card, on=keys, how="left")
    out["card_trips"] = out["card_trips"].fillna(0).astype(int)
    out["card_tip_pct"] = np.where(out["card_fare"] > 0, 100 * out["card_tip"] / out["card_fare"], np.nan)
    out = out.drop(columns=["card_fare", "card_tip"])
    num = out.select_dtypes("float").columns
    out[num] = out[num].round(3)
    return out


def main():
    import pyarrow.parquet as pq
    clean = pq.read_table(cfg.PROCESSED_DIR / "clean_trips.parquet", columns=NEEDED).to_pandas()
    raw_zh = pd.read_csv(cfg.PROCESSED_DIR / "raw_zone_hour_agg.csv")
    raw_daily = pd.read_csv(cfg.PROCESSED_DIR / "raw_daily_agg.csv")
    zone_hour, hour, daily = compute_all(clean, raw_zh, raw_daily)
    zone_hour.to_csv(cfg.PROCESSED_DIR / "zone_hour_stats.csv", index=False)
    hour.to_csv(cfg.PROCESSED_DIR / "hour_stats.csv", index=False)
    daily.to_csv(cfg.PROCESSED_DIR / "daily_stats.csv", index=False)
    print(f"zone_hour_stats: {len(zone_hour):,} rows ({int(zone_hour.is_reliable.sum()):,} reliable, "
          f"{100 * (1 - zone_hour.is_reliable.mean()):.0f}% below {cfg.MIN_TRIPS_RELIABLE} trips)")
    print(f"hour_stats: {len(hour)} rows   daily_stats: {len(daily)} rows")
    econ_clean = pq.read_table(cfg.PROCESSED_DIR / "clean_trips.parquet", columns=ECON_NEEDED).to_pandas()
    econ = compute_economics(econ_clean)
    econ.to_csv(cfg.PROCESSED_DIR / "econ_hour_stats.csv", index=False)
    print(f"econ_hour_stats: {len(econ)} rows")


if __name__ == "__main__":
    main()
