"""Cleaning rules and normalisation for one chunk of trips"""

from dataclasses import dataclass, field
import numpy as np
import pandas as pd

from . import config as cfg
from .feature_engineering import derive_features

DATETIME_COLS = ["tpep_pickup_datetime", "tpep_dropoff_datetime"]
MONEY_COLS = ["fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
              "improvement_surcharge", "total_amount"]
NUMERIC_COLS = ["VendorID", "passenger_count", "trip_distance", "RatecodeID",
                "PULocationID", "DOLocationID", "payment_type"] + MONEY_COLS
REQUIRED_COLS = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "trip_distance",
                 "fare_amount", "total_amount", "VendorID", "RatecodeID",
                 "payment_type", "PULocationID", "DOLocationID"]
# Columns that identify a record when looking for exact duplicates
IDENTITY_COLS = DATETIME_COLS + NUMERIC_COLS + ["congestion_surcharge", "store_and_fwd_flag"]


def standardize(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalise types: timestamps to datetime, numbers to float, store_and_fwd flag to 0/1."""
    df = pd.DataFrame(index=raw.index)
    for c in DATETIME_COLS:
        df[c] = pd.to_datetime(raw[c], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    for c in NUMERIC_COLS:
        df[c] = pd.to_numeric(raw[c], errors="coerce")
    # congestion_surcharge is new in Jan 2019; empty means "not applicable", so we use 0
    cong = raw["congestion_surcharge"] if "congestion_surcharge" in raw else pd.Series(0.0, index=raw.index)
    df["congestion_surcharge"] = pd.to_numeric(cong, errors="coerce").fillna(0.0)
    flag = raw["store_and_fwd_flag"].astype("string").str.strip().str.upper()
    df["store_and_fwd_flag"] = flag.map({"Y": 1, "N": 0}).fillna(0).astype(int)
    return df


class DuplicateTracker:
    """Finds exact duplicate rows across chunks using a 64-bit hash of each row.

    It needs 8 bytes per row seen (about 60 MB for 7.6 million rows). The chance of two
    different rows sharing a hash is roughly 1.6e-6, which we accept and document.
    """

    def __init__(self):
        self._seen = np.empty(0, dtype=np.uint64)

    def mark(self, std: pd.DataFrame) -> pd.Series:
        hashes = pd.util.hash_pandas_object(std[IDENTITY_COLS], index=False).to_numpy()
        dup_in_chunk = pd.Series(hashes).duplicated().to_numpy()
        dup_before = np.isin(hashes, self._seen)
        self._seen = np.union1d(self._seen, hashes)
        return pd.Series(dup_in_chunk | dup_before, index=std.index)