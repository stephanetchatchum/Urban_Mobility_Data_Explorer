"""Checks one chunk of trips against the cleaning rules and fixes the data types."""

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
# The columns we compare to decide whether two rows are exact copies
IDENTITY_COLS = DATETIME_COLS + NUMERIC_COLS + ["congestion_surcharge", "store_and_fwd_flag"]

# The final columns of the cleaned table and their data types 
CLEAN_DTYPES = {
    "trip_id": "int64", "vendor_id": "int8", "pickup_ts": "datetime64[us]",
    "dropoff_ts": "datetime64[us]", "passenger_count": "Int8",
    "trip_distance_mi": "float64", "rate_code_id": "int8", "store_and_fwd": "int8",
    "pu_location_id": "int16", "do_location_id": "int16", "payment_type_id": "int8",
    "fare_amount": "float64", "extra": "float64", "mta_tax": "float64",
    "tip_amount": "float64", "tolls_amount": "float64",
    "improvement_surcharge": "float64", "congestion_surcharge": "float64",
    "total_amount": "float64", "duration_min": "float64", "avg_speed_mph": "float64",
    "min_per_mile": "float64", "fare_per_mile": "float64", "fare_per_min": "float64",
    "pickup_date": "string", "pickup_hour": "int8", "pickup_dow": "int8",
    "is_weekend": "int8", "is_flat_fare": "int8", "flag_unknown_zone": "int8",
    "flag_passenger_suspect": "int8", "flag_low_speed": "int8", "flag_total_mismatch": "int8",
}


@dataclass
class ChunkResult:
    """Everything that is returned by the clean_chunk for one chunk of trips."""
    clean: pd.DataFrame            # The trips we keep
    excluded_log: pd.DataFrame     # One row for every removed trip, reason
    reason_counts: dict            # How many trips each rule affected
    n_raw: int                     # Trips in the chunk before cleaning
    n_excluded: int                # Trips removed
    raw_zone_hour: pd.DataFrame    # Totals before cleaning, per zone and hour
    raw_daily: pd.DataFrame = field(default_factory=pd.DataFrame)


def standardize(raw: pd.DataFrame) -> pd.DataFrame:
    """Fix the data types: dates become real dates, numbers become numbers, and Y/N becomes 1/0."""
    df = pd.DataFrame(index=raw.index)
    for c in DATETIME_COLS:
        df[c] = pd.to_datetime(raw[c], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    for c in NUMERIC_COLS:
        df[c] = pd.to_numeric(raw[c], errors="coerce")
    # This column only exists from January 2019. If it is empty, no charge applied, so we use 0.
    cong = raw["congestion_surcharge"] if "congestion_surcharge" in raw else pd.Series(0.0, index=raw.index)
    df["congestion_surcharge"] = pd.to_numeric(cong, errors="coerce").fillna(0.0)
    flag = raw["store_and_fwd_flag"].astype("string").str.strip().str.upper()
    df["store_and_fwd_flag"] = flag.map({"Y": 1, "N": 0}).fillna(0).astype(int)
    return df


class DuplicateTracker:
    """Finds rows that are exact copies of an earlier row, even if that row was in a different chunk. 
    Each row is turned into one number (a hash) that works like a fingerprint.
    Identical rows have identical fingerprints, so we only store fingerprints, not the whole rows.
    Two different rows could share a fingerprint, but the chance is about 1 in 600,000 and we accept that.
    """

    def __init__(self):
        self._seen = np.empty(0, dtype=np.uint64)

    def mark(self, std: pd.DataFrame) -> pd.Series:
        hashes = pd.util.hash_pandas_object(std[IDENTITY_COLS], index=False).to_numpy()
        dup_in_chunk = pd.Series(hashes).duplicated().to_numpy()
        dup_before = np.isin(hashes, self._seen)
        self._seen = np.union1d(self._seen, hashes)
        return pd.Series(dup_in_chunk | dup_before, index=std.index)

    

def _durations(std):
    return (std["tpep_dropoff_datetime"] - std["tpep_pickup_datetime"]).dt.total_seconds() / 60.0


def clean_chunk(raw: pd.DataFrame, first_row: int, valid_zone_ids, duplicate_mask=None) -> ChunkResult:
    """Clean one chunk.

    first_row: 1-based row number (in the source file) of the chunk's first record.
    valid_zone_ids: set of LocationIDs present in the zone lookup.
    duplicate_mask: boolean Series (aligned to raw.index) from DuplicateTracker, or None.
    """
    n = len(raw)
    raw = raw.reset_index(drop=True)
    std = standardize(raw)
    source_row = np.arange(first_row, first_row + n, dtype=np.int64)

    pick, drop = std["tpep_pickup_datetime"], std["tpep_dropoff_datetime"]
    dist, fare = std["trip_distance"], std["fare_amount"]
    pu, do = std["PULocationID"], std["DOLocationID"]
    dur = _durations(std)
    with np.errstate(divide="ignore", invalid="ignore"):
        speed = np.where(dur > 0, dist / (dur / 60.0), np.nan)
    speed = pd.Series(speed, index=std.index)

    # Match duplicate flags to rows by position (1st, 2nd, ...). Later chunks start at an index like 500000, not 0.
    dup_flags = (pd.Series(False, index=std.index) if duplicate_mask is None
                 else pd.Series(np.asarray(duplicate_mask, dtype=bool), index=std.index))
    zones = pd.Series(sorted(valid_zone_ids))
    in_range = (pick >= cfg.DATA_START) & (pick < cfg.DATA_END)
    components = (std[["fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
                       "improvement_surcharge", "congestion_surcharge"]].sum(axis=1))

    # Each rule is a True/False column. True means the trip breaks the rule and is removed.
    rules = {
        "MISSING_VALUE": std[REQUIRED_COLS].isna().any(axis=1),
        "DUPLICATE_RECORD": dup_flags,
        "OUT_OF_RANGE_DATE": pick.notna() & ~in_range,
        "DROPOFF_BEFORE_PICKUP": dur < 0,
        "ZERO_DURATION": dur == 0,
        "EXCESSIVE_DURATION": dur > cfg.MAX_DURATION_MIN,
        "IMPOSSIBLE_SPEED": speed > cfg.MAX_SPEED_MPH,
        "NON_POSITIVE_DISTANCE": dist <= 0,
        "EXCESSIVE_DISTANCE": dist > cfg.MAX_DISTANCE_MI,
        "REVERSAL_OR_REFUND": fare < 0,
        "ZERO_FARE": fare == 0,
        "EXTREME_FARE": fare > cfg.MAX_FARE_USD,
        "INVALID_VENDOR": std["VendorID"].notna() & ~std["VendorID"].isin(cfg.VALID_VENDORS),
        "INVALID_RATE_CODE": std["RatecodeID"].notna() & ~std["RatecodeID"].isin(cfg.VALID_RATE_CODES),
        "INVALID_PAYMENT_TYPE": std["payment_type"].notna() & ~std["payment_type"].isin(cfg.VALID_PAYMENT_TYPES),
        "INVALID_ZONE_ID": (pu.notna() & ~pu.isin(zones)) | (do.notna() & ~do.isin(zones)),
    }
    # Flags work the same way, but the trip is kept and only marked.
    flags = {
        "UNKNOWN_ZONE": pu.isin(cfg.UNKNOWN_ZONE_IDS) | do.isin(cfg.UNKNOWN_ZONE_IDS),
        "PASSENGER_COUNT_SUSPECT": std["passenger_count"].isna() | (std["passenger_count"] < 1)
                                   | (std["passenger_count"] > cfg.MAX_PASSENGERS),
        "LOW_SPEED": speed < cfg.LOW_SPEED_FLAG_MPH,
        "TOTAL_MISMATCH": (std["total_amount"] - components).abs() > cfg.TOTAL_TOLERANCE_USD,
    }

    excluded_any = pd.Series(False, index=std.index)
    for mask in rules.values():
        excluded_any |= mask.fillna(False)
    keep = ~excluded_any

    # ---- Exclusion log: one line for every (trip, reason) pair, so every removal can be explained ----
    log_parts, counts = [], {}
    for code, mask in rules.items():
        mask = mask.fillna(False).astype(bool)
        counts[code] = int(mask.sum())
        if mask.any():
            part = pd.DataFrame({
                "source_row": source_row[mask.to_numpy()],
                "reason_code": code,
                "pickup_ts": pick[mask].dt.strftime("%Y-%m-%d %H:%M:%S"),
                "dropoff_ts": drop[mask].dt.strftime("%Y-%m-%d %H:%M:%S"),
                "trip_distance_mi": dist[mask].to_numpy(),
                "fare_amount": fare[mask].to_numpy(),
                "pu_location_id": pu[mask].to_numpy(),
                "do_location_id": do[mask].to_numpy(),
            })
            log_parts.append(part)
    excluded_log = pd.concat(log_parts, ignore_index=True) if log_parts else pd.DataFrame(
        columns=["source_row", "reason_code", "pickup_ts", "dropoff_ts", "trip_distance_mi", "fare_amount", "pu_location_id", "do_location_id"])
    
    for code, mask in flags.items():                      # Count flags only for kept trips. Removed trips are already counted under their removal reason.
        counts[code] = int((mask.fillna(False) & keep).sum())

    # ---- Totals before cleaning, so the dashboard can compare raw numbers with cleaned numbers ----
    raw_zone_hour, raw_daily = _raw_aggregates(pick, pu, dur, dist)

    # ---- Build the table of kept trips. The new columns come from feature_engineering.py ----
    k = keep.to_numpy()
    base = pd.DataFrame({
        "trip_id": source_row[k],
        "vendor_id": std["VendorID"][k], "pickup_ts": pick[k], "dropoff_ts": drop[k],
        "passenger_count": std["passenger_count"][k],
        "trip_distance_mi": dist[k], "rate_code_id": std["RatecodeID"][k],
        "store_and_fwd": std["store_and_fwd_flag"][k],
        "pu_location_id": pu[k], "do_location_id": do[k], "payment_type_id": std["payment_type"][k],
        "fare_amount": fare[k], "extra": std["extra"][k], "mta_tax": std["mta_tax"][k],
        "tip_amount": std["tip_amount"][k], "tolls_amount": std["tolls_amount"][k],
        "improvement_surcharge": std["improvement_surcharge"][k],
        "congestion_surcharge": std["congestion_surcharge"][k],
        "total_amount": std["total_amount"][k], "duration_min": dur[k],
    })
    feats = derive_features(base)
    flag_cols = pd.DataFrame({
        "flag_unknown_zone": flags["UNKNOWN_ZONE"][k].astype(int),
        "flag_passenger_suspect": flags["PASSENGER_COUNT_SUSPECT"][k].astype(int),
        "flag_low_speed": flags["LOW_SPEED"][k].astype(int),
        "flag_total_mismatch": flags["TOTAL_MISMATCH"][k].astype(int),
    })
    out = pd.concat([base.drop(columns=["duration_min"]), feats, flag_cols], axis=1)
    out = out[list(CLEAN_DTYPES)].astype(CLEAN_DTYPES).reset_index(drop=True)
    return ChunkResult(out, excluded_log, counts, n, int(excluded_any.sum()), raw_zone_hour, raw_daily)


def _raw_aggregates(pick, pu, dur, dist):
    """Adds up trips and speeds before any cleaning. Only rows with a pickup time and a pickup zone are counted"""
    ok = pick.notna() & pu.notna()
    spd_ok = ok & (dur > 0) & (dist >= 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        spd = dist / (dur / 60.0)
    base = pd.DataFrame({
        "pu_location_id": pu[ok].astype(int), "pickup_hour": pick[ok].dt.hour,
        "day_type": np.where(pick[ok].dt.dayofweek >= 5, "weekend", "weekday"),
        "pickup_date": pick[ok].dt.strftime("%Y-%m-%d"),
        "speed": spd[ok].where(spd_ok[ok]),
    })
    base["has_speed"] = base["speed"].notna().astype(int)
    zh = (base.groupby(["pu_location_id", "pickup_hour", "day_type"])
          .agg(raw_trips=("speed", "size"), raw_speed_n=("has_speed", "sum"),
               raw_speed_sum=("speed", "sum")).reset_index())
    daily = (base.groupby("pickup_date")
             .agg(raw_trips=("speed", "size"), raw_speed_n=("has_speed", "sum"),
                  raw_speed_sum=("speed", "sum")).reset_index())
    return zh, daily
