# Exclusion log notes: cleaning rules and feature engineering

Source: `yellow_tripdata_2019-01.csv` (7,667,792 trips), joined to `taxi_zone_lookup.csv` and the `taxi_zones` shapefile. Run: `python -m pipeline.run_pipeline` (about 3 minutes). Code: `pipeline/load_data.py` (read), `clean_data.py` (rules), `feature_engineering.py` (features), `zones_to_geojson.py` (shapefile to lat/lon GeoJSON). The log is written to `data/logs/` (`exclusion_log.csv`, `cleaning_summary.csv`, `cleaning_report.json`).
Result: **7,578,846 trips kept, 88,946 excluded (1.16%)**, plus 170,637 kept trips flagged for touching zone 264/265. Every threshold is a constant in `pipeline/config.py`.

**Assumptions:** a metered trip cannot exceed 80 mph or 3 hours in NYC; a fare of zero or below is a reversal, not a trip; a zero-distance trip cannot yield a speed; trips in zones 264/265 are real trips with an unknown location, so they are kept and flagged instead of deleted.

## Missing values and duplicates
| Check | Result | Handling |
|---|---|---|
| Missing values in required columns | 0 | Would be excluded as `MISSING_VALUE` |
| `congestion_surcharge` empty | 4,855,978 rows | Column was new in Jan 2019, so empty means "not applicable": filled with 0 |
| Exact duplicate rows | 0 | Detected with 64-bit row hashes across chunks; would be excluded as `DUPLICATE_RECORD` |
| Zone ids missing from the lookup | 0 | Would be excluded as `INVALID_ZONE_ID` |
| Lookup text `"N/A"` (zones 264/265) | 2 rows | Read as text, not null, then labelled `Unknown` |
| Shapefile polygons | 263 polygons for 260 ids | Merged per LocationID (dissolve); 5 ids have no polygon (57, 104, 105, 264, 265) |

## Exclusion rules (record removed, written to `exclusion_log`)
| Code | Rule | Rows |
|---|---|---|
| `NON_POSITIVE_DISTANCE` | distance <= 0 | 54,770 |
| `EXCESSIVE_DURATION` | duration > 180 min | 20,913 |
| `REVERSAL_OR_REFUND` | fare < 0 | 7,131 |
| `ZERO_DURATION` | dropoff = pickup | 6,290 |
| `IMPOSSIBLE_SPEED` | speed > 80 mph (duration > 0) | 6,135 |
| `ZERO_FARE` | fare = 0 | 2,426 |
| `OUT_OF_RANGE_DATE` | pickup outside Jan 2019 (years 2001-2088 seen) | 537 |
| `INVALID_RATE_CODE` | rate code not 1-6 (all were 99) | 252 |
| `EXTREME_FARE` | fare > $500 | 34 |
| `EXCESSIVE_DISTANCE` | distance > 100 miles | 32 |
| `DROPOFF_BEFORE_PICKUP` | dropoff earlier than pickup | 4 |
A record can break several rules, so rows per rule add up to more than 88,946 (the log has 98,524 rows for 88,946 records).

## Flag rules (record kept, flag column set)
| Flag | Rule | Rows kept and flagged |
|---|---|---|
| `UNKNOWN_ZONE` | pickup or dropoff in 264/265 | 170,637 |
| `PASSENGER_COUNT_SUSPECT` | 0, missing or above 6 passengers | 115,104 |
| `TOTAL_MISMATCH` | total differs from sum of components by more than $0.05 | 15,746 |
| `LOW_SPEED` | average speed below 2 mph | 11,585 |

## Normalisation
Shapefile polygons are converted from EPSG:2263 (feet) to EPSG:4326 (lat/lon) and written to `data/processed/zones.geojson`.
Timestamps parsed to datetime (ISO text in the database); numeric columns coerced to numbers; `store_and_fwd_flag` Y/N to 1/0; codes to small integers; money rounded only in derived columns; all dtypes fixed in `CLEAN_DTYPES`.

## Derived features
| Feature | Formula | Why it matters |
|---|---|---|
| `duration_min` | (dropoff - pickup) in minutes | Basis of every time-cost metric |
| `avg_speed_mph` | distance / (duration / 60) | Measures congestion; also exposes impossible trips |
| `min_per_mile` | duration / distance | Time cost of a mile: easier to read than speed and additive across trips |
| `fare_per_mile` | fare / distance | Price of distance; separates flat-fare and short-trip effects |
| `fare_per_min` | fare / duration | Price of time; shows what slowness costs the rider |
| `pickup_hour`, `pickup_dow`, `is_weekend`, `pickup_date` | from pickup time | Hour-of-day and weekday patterns without date parsing in queries |
| `is_flat_fare` | rate code = 2 | Flat $52 JFK trips ignore time, so they are left out of `fare_per_min` statistics |

## Trust score (zone-hour level)
`trust_score = (clean trips - low-speed trips) / raw trips`, between 0 and 1. A cell is "reliable" when it has at least 30 clean trips; fewer-trip cells are hidden in the API.

## Economics slice (fares, tips, fees)
Tables `economics_hour_stats`, `economics_payment_stats`, `economics_speed_band_stats`, served by `/api/economics/*` and drawn by `frontend/js/economics.js`.
- **Cash tips are not recorded:** 0.015% of cash trips (307 of 2,103,781) show a tip, against 95.9% of card trips. Tip statistics are therefore reported for card trips or by payment type, never as a citywide average of "tipping".
- **Price of slowness:** among standard-rate trips of 2-5 miles, the median fare per mile is $7.99 for trips under 5 mph and $3.18 for trips at 30+ mph (a 151% premium), and a mile takes 13.2 minutes against 1.8. The comparison is an association: very slow trips are also more likely to be congested midtown trips, and the $2.50 starting charge is shared over fewer miles on shorter trips, which the 2-5 mile window limits but does not remove.
