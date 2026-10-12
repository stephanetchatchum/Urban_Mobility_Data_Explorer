"""Derived features, justified in docs/exclusion_log_notes.md.

Input columns: pickup_ts, trip_distance_mi, fare_amount, duration_min, rate_code_id.
Inputs are already cleaned, so duration and distance are positive and no division can fail.
"""
import pandas as pd

from . import config as cfg


def derive_features(trips: pd.DataFrame) -> pd.DataFrame:
    dist, dur = trips["trip_distance_mi"], trips["duration_min"]
    fare, pick = trips["fare_amount"], trips["pickup_ts"]
    return pd.DataFrame({
        "duration_min": dur.round(3),                                # minutes
        "avg_speed_mph": (dist / (dur / 60.0)).round(2),             # congestion indicator
        "min_per_mile": (dur / dist).round(3),                       # time cost of one mile
        "fare_per_mile": (fare / dist).round(2),                     # price of distance
        "fare_per_min": (fare / dur).round(3),                       # price of time
        "pickup_date": pick.dt.strftime("%Y-%m-%d"),
        "pickup_hour": pick.dt.hour,
        "pickup_dow": pick.dt.dayofweek,                             # 0 = Monday
        "is_weekend": (pick.dt.dayofweek >= 5).astype(int),
        "is_flat_fare": (trips["rate_code_id"] == cfg.FLAT_FARE_RATE_CODE).astype(int),
    }, index=trips.index)