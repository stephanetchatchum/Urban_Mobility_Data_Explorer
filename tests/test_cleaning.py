import numpy as np
import pandas as pd
from pipeline.clean_data import DuplicateTracker, clean_chunk, standardize

ZONES = {1, 2, 3, 264, 265}

def row(**over):
    base = dict(VendorID=1, tpep_pickup_datetime="2019-01-10 08:00:00", tpep_dropoff_datetime="2019-01-10 08:20:00",
                passenger_count=1, trip_distance=3.0, RatecodeID=1, store_and_fwd_flag="N", PULocationID=1,
                DOLocationID=2, payment_type=1, fare_amount=12.0, extra=0.5, mta_tax=0.5, tip_amount=2.0,
                tolls_amount=0.0, improvement_surcharge=0.3, total_amount=15.3, congestion_surcharge=np.nan)
    base.update(over)
    return base

def run(*rows, dup=None):
    return clean_chunk(pd.DataFrame(rows), 1, ZONES, dup)

def test_each_exclusion_rule_fires_once():
    cases = {
        "ZERO_DURATION": row(tpep_dropoff_datetime="2019-01-10 08:00:00"),
        "DROPOFF_BEFORE_PICKUP": row(tpep_dropoff_datetime="2019-01-10 07:50:00"),
        "EXCESSIVE_DURATION": row(tpep_dropoff_datetime="2019-01-10 11:01:00", trip_distance=10),
        "IMPOSSIBLE_SPEED": row(trip_distance=40.0),
        "NON_POSITIVE_DISTANCE": row(trip_distance=0.0),
        "EXCESSIVE_DISTANCE": row(trip_distance=101.0, tpep_dropoff_datetime="2019-01-10 10:50:00"),
        "REVERSAL_OR_REFUND": row(fare_amount=-5.0),
        "ZERO_FARE": row(fare_amount=0.0),
        "EXTREME_FARE": row(fare_amount=600.0),
        "INVALID_RATE_CODE": row(RatecodeID=99),
        "INVALID_PAYMENT_TYPE":row(payment_type=9),
        "INVALID_VENDOR": row(VendorID=3),
        "INVALID_ZONE_ID":row(PULocationID=999),
        "OUT_OF_RANGE_DATE": row(tpep_pickup_datetime="2008-12-31 23:50:00", tpep_dropoff_datetime="2008-12-31 23:59:00"),
        "MISSING_VALUE": row(trip_distance=np.nan),
    }
    for code, bad in cases.items():
        res = run(row(), bad)
        assert res.reason_counts[code] == 1, code
        assert len(res.clean) == 1 and res.n_excluded == 1, code
        assert code in set(res.excluded_log["reason_code"]), code
        assert list(res.excluded_log["source_row"].unique()) == [2], code  # traceable to source row


def test_flags_keep_the_row():
    res = run(row(DOLocationID=264), row(passenger_count=0), row(trip_distance=0.5), row(total_amount=99.0))
    assert len(res.clean) ==4 and res.n_excluded == 0
    assert res.clean["flag_unknown_zone"].tolist() == [1, 0, 0, 0]
    assert res.clean["flag_passenger_suspect"].tolist() == [0, 1, 0, 0]
    assert res.clean["flag_low_speed"].tolist() == [0, 0, 1, 0]
    assert res.clean["flag_total_mismatch"].tolist() == [0, 0, 0, 1]


def test_duplicates_are_detected_within_and_across_chunks():
    tracker = DuplicateTracker()
    a = standardize(pd.DataFrame([row(), row(), row(fare_amount=13.0, total_amount=16.3)]))
    assert tracker.mark(a).tolist() == [False, True, False]
    b = standardize(pd.DataFrame([row(), row(PULocationID=3)]))
    assert tracker.mark(b).tolist() == [True, False]
    res = run(row(), row(), dup=pd.Series([False, True]))
    assert res.reason_counts["DUPLICATE_RECORD"] == 1 and len(res.clean) == 1


def test_raw_aggregates_include_unclean_rows():
    res = run(row(), row(trip_distance=40.0))    # second row has 120 mph speed
    zh = res.raw_zone_hour.iloc[0]
    assert zh.raw_trips == 2 and zh.raw_speed_n == 2
    assert abs(zh.raw_speed_sum - (9.0 + 120.0)) < 1e-9

def test_missing_congestion_column_is_treated_as_zero():
    raw = pd.DataFrame([row()]).drop(columns=["congestion_surcharge"])      # older files have no such column
    res = clean_chunk(raw, 1, ZONES)
    assert len(res.clean) == 1 and res.clean.iloc[0].congestion_surcharge == 0.0