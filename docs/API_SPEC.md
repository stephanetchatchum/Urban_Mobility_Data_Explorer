# API specification

Base URL (local): `http://127.0.0.1:5000` — read-only JSON over HTTP GET, CORS enabled.
Backend: Flask + MySQL (`mysql-connector-python`). Every value from the query string travels as a `%s` parameter, never inside the SQL text.
Code: `backend/app.py` (trips, zones, slowest zones, top routes, speed insights), `backend/routes/story.py` (story and trust layer), `backend/routes/economics.py` (economics), `backend/routes/heatmap.py` (time heatmap).

## Conventions
- Success: the JSON is returned directly (an object or an array). `/api/trips` returns `{page, per_page, total, total_pages, data}`.
- Errors: `400 {"errors": [..]}` (invalid filters) or `400/404 {"error": "message"}`.
- `Decimal` values are sent as numbers and timestamps as ISO strings (`2019-01-10T08:00:00`), by the JSON provider (`MyJSONProvider`) in `backend/app.py`.
- Speeds are miles per hour, `min_per_mile` is minutes per mile, fares are US dollars.
- A zone-hour statistic is only used for ranking when it rests on at least **30 cleaned trips** (`MIN_TRIPS_RELIABLE`). Zones 264 and 265 (unknown location) are never ranked or mapped (`zones.is_mappable = 0`).

## Endpoint list
| Path | Purpose | Source |
|---|---|---|
| `/api/health` | Liveness check | app.py |
| `/api/trips` | Filter, sort and page through cleaned trips | trips table |
| `/api/trips/{trip_id}` | One trip with zone names, rate code and payment type | trips table |
| `/api/zones` | Zone list | zones table |
| `/api/zones/geojson` | Zone polygons (lat/lon) for the map | `data/processed/zones.geojson` |
| `/api/zones/slowest` | Slowest pickup zones by mean speed (heap) | trips table |
| `/api/insights/top-routes` | Busiest pickup to dropoff pairs (heap) | trips table |
| `/api/insights/speed-by-hour` | Average speed and trip count per hour | trips table |
| `/api/insights/cost-of-slowness` | Minutes per mile and fare per minute per hour | trips table |
| `/api/story/hour-profile` | Minutes per mile, speed, fare per minute and per mile by hour | `hour_stats` |
| `/api/story/zone-hour` | One value per mappable zone for a chosen hour (map colouring) | `zone_hour_stats` |
| `/api/story/slowest-zones` | Top-K slowest zones with the trips behind each (manual min-heap) | `zone_hour_stats` |
| `/api/economics/by-hour` | Average fare, fees and card tip rate per hour | `econ_hour` |
| `/api/time/heatmap` | Day of week by hour grid (trips, speed or minutes per mile) | trips table (cached) |
| `/api/trust/summary` | Every cleaning rule with its row count and share of the raw file | `cleaning_summary` |
| `/api/trust/raw-vs-clean` | Mean speed before and after cleaning, by hour or by day | `hour_stats`, `daily_stats` |
| `/api/trust/exclusion-log` | Paged list of removed trips | `exclusion_log` |

## Trips

### GET /api/trips
Filters (all optional, combined with AND): `min_distance`, `max_distance` (miles), `min_fare`, `max_fare` (USD), `start_date`, `end_date` (`YYYY-MM-DD`, both inclusive), `hour` (0 to 23), `pickup_zone`, `dropoff_zone` (location id).
Sorting: `sort` = `time` (default) | `distance` | `fare` | `duration` | `speed`; `order` = `asc` (default) | `desc`. Paging: `page` (default 1), `per_page` (default 50, maximum 200). Ties are broken by `trip_id`, so pages are stable.
Row fields: `trip_id, pickup_datetime, trip_distance, duration_min, fare_amount, speed_mph, pickup_zone, dropoff_zone`.
```json
{ "page": 1, "per_page": 50, "total": 7578846, "total_pages": 151577, "data": [ { "trip_id": 12, "pickup_datetime": "2019-01-01 00:59:47", "trip_distance": 2.6, "fare_amount": 14.0, "speed_mph": 8.1, "pickup_zone": "Upper East Side South" } ] }
```
### GET /api/trips/{trip_id}
Every column of the trips table plus `pickup_zone, pickup_borough, dropoff_zone, dropoff_borough, payment_type, rate_code`. Unknown id: `404 {"error": "trip not found"}`.

## Zones and insights
### GET /api/zones
`[{location_id, borough, zone, service_zone}]` (265 zones).
### GET /api/zones/geojson
GeoJSON FeatureCollection. Each feature has `location_id, zone_name, borough, service_zone` and a simplified polygon in WGS84. Join statistics to it on `location_id`. Returns `404` if the pipeline has not produced `zones.geojson` yet.
### GET /api/zones/slowest
`k` (1 to 50, default 10) and `min_trips` (default 30). Returns `[{zone, avg_speed}]`, slowest first, ranked with the manual heap. It averages all kept trips, including zones 264 and 265; the dashboard should use `/api/story/slowest-zones` for the ranking.
### GET /api/insights/top-routes
`n` (1 to 100, default 10) and `min_trips` (default 30). Unknown zones 264 and 265 are left out. Rows: `pickup_zone_id, pickup_zone, dropoff_zone_id, dropoff_zone, trips, avg_fare, avg_duration_min`, busiest first (manual heap).
### GET /api/insights/speed-by-hour and /api/insights/cost-of-slowness
Optional `weekend` (0 or 1). Rows: `hour, avg_speed, trip_count` and `hour, avg_min_per_mile, avg_fare_per_min, trip_count`.

## Economics
### GET /api/economics/by-hour
Optional `day_type` (`weekday`, `weekend`, `all`). Rows: `hour, trips, avg_fare, avg_fees, avg_fare_per_mile, card_tip_pct`. `avg_fees` is everything on the bill that is neither fare nor tip. `card_tip_pct` is the tip as a percentage of the fare, card payments only, because cash tips are not recorded (it is `null` for an hour with no card trips).

## Time
### GET /api/time/heatmap
`metric` = `trips` (default) | `speed` | `min_per_mile`. Rows: `dow` (0 = Monday), `hour`, `value`, `trips`. The first call groups the whole trips table and takes a few seconds; the answer is then kept in memory.

## The story: price of slowness (precomputed medians)
`day_type` is `weekday`, `weekend` or `all` (default, no filter). An invalid value returns `400`.

### GET /api/story/hour-profile
Optional `day_type`. Rows: `hour, day_type, trips, median_min_per_mile, median_speed_mph, median_fare_per_min, median_fare_per_mile`. Flat-fare trips (rate code 2) are left out of `median_fare_per_min`.
### GET /api/story/zone-hour
Required `hour` (0 to 23); optional `day_type`. One row per mappable zone that has trips: `location_id, zone, borough, day_type, trips, is_reliable, median_min_per_mile, median_speed_mph, median_fare_per_min`. Draw cells with `is_reliable = 0` in grey.
### GET /api/story/slowest-zones
Optional `n` (1 to 100, default 10), `hour_from`, `hour_to` (0 to 23, default 0 and 23), `day_type`, `min_trips` (default 30). Rows: `location_id, zone, borough, trips, min_per_mile, speed_mph, fare_per_min`, slowest first. `min_per_mile` is the trip-weighted mean of the zone-hour medians. The ranking uses `k_smallest` (manual min-heap) on the negated value.

## Trust layer
### GET /api/trust/summary
Rows: `reason_code, action (EXCLUDED or FLAGGED), description, row_count, pct_of_raw`, largest first.
### GET /api/trust/raw-vs-clean
`by` = `hour` (default) or `day`. Hour rows: `hour, day_type, trips, raw_trips, mean_speed_mph, raw_mean_speed_mph` (optional `day_type`). Day rows: `day, trips, raw_trips, mean_speed_mph, raw_mean_speed_mph`, January 2019 only. `raw_*` values are before cleaning.
### GET /api/trust/exclusion-log
Optional `reason` (a reason code), `page`, `per_page` (maximum 200). Returns `{page, per_page, total, data}`; rows: `log_id, source_row, reason_code, pickup_ts, dropoff_ts, trip_distance_mi, fare_amount, pu_location_id, do_location_id`. `source_row` is the 1-based data row in the raw file and equals `trip_id` for kept trips.

## Performance notes
Statistics and trust endpoints read small precomputed tables. `/api/trips`, `/api/insights/*` and the first `/api/time/heatmap` call read the full `trips` table: only `pickup_datetime` and `(pickup_zone_id, pickup_datetime)` are indexed, so sorting by fare, distance, duration or speed on the full table can be slow. Measure on the loaded database before the demo; a sample load (`--sample-every 20`) keeps these calls fast.
