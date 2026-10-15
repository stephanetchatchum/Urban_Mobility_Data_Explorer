import numpy as np
import pandas as pd

from pipeline.build_aggregates import compute_all


def clean_rows():
    # zone 1, weekday 8h: 40 trips (reliable). zone 2, weekday 8h: 5 trips (unreliable). One flat-fare trip.
    rows = []
    for i in range(40):
        rows.append((1, 8, "2019-01-10", 0, 0, 6.0 + (i % 2), 10.0, 1.0 + (i % 2) * 0.2, 5.0))
    for i in range(5):
        rows.append((2, 8, "2019-01-10", 0, 0, 3.0, 20.0, 1.5, 4.0))
    rows.append((1, 8, "2019-01-10", 0, 1, 2.0, 30.0, 9.99, 3.0))     # flat fare: must not enter fare_per_min
    return pd.DataFrame(rows, columns=["pu_location_id", "pickup_hour", "pickup_date", "is_weekend", "is_flat_fare",
                                       "min_per_mile", "avg_speed_mph", "fare_per_min", "fare_per_mile"])


def raw_parts():
    zh = pd.DataFrame([(1, 8, "weekday", 50, 50, 1000.0), (2, 8, "weekday", 5, 5, 100.0)],
                      columns=["pu_location_id", "pickup_hour", "day_type", "raw_trips", "raw_speed_n", "raw_speed_sum"])
    daily = pd.DataFrame([("2019-01-10", 55, 55, 1100.0), ("2088-01-24", 2, 2, 10.0)],
                         columns=["pickup_date", "raw_trips", "raw_speed_n", "raw_speed_sum"])
    return zh, daily


def test_reliability_and_counts():
    zh, daily = raw_parts()
    zone_hour, hour, _ = compute_all(clean_rows(), zh, daily)
    z1 = zone_hour[zone_hour.pu_location_id == 1].iloc[0]
    z2 = zone_hour[zone_hour.pu_location_id == 2].iloc[0]
    assert z1.trips == 41 and z1.is_reliable == 1
    assert z2.trips == 5 and z2.is_reliable == 0
    assert z1.raw_trips == 50 and abs(z1.raw_mean_speed_mph - 20.0) < 1e-9
    assert len(hour) == 1 and hour.iloc[0].trips == 46


def test_flat_fare_is_left_out_of_fare_per_minute():
    zh, daily = raw_parts()
    zone_hour, _, _ = compute_all(clean_rows(), zh, daily)
    z1 = zone_hour[zone_hour.pu_location_id == 1].iloc[0]
    assert z1.median_fare_per_min < 2.0        # the 9.99 flat fare would have pushed it up if it was included


def test_raw_only_dates_are_kept():
    zh, daily = raw_parts()
    _, _, d = compute_all(clean_rows(), zh, daily)
    odd = d[d.pickup_date == "2088-01-24"].iloc[0]
    assert odd.trips == 0 and odd.raw_trips == 2
