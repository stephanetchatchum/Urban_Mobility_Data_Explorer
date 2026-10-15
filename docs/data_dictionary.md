# Data dictionary

One row per trip in the `trips` table. The pipeline writes these columns to `data/processed/clean_trips.parquet`,
and `pipeline/load_to_db.py` loads them into MySQL. The ready-made table definition is `database/pipeline_tables.sql`.
All times are New York local time. Money is in US dollars, distance in miles, speed in miles per hour.

## Table `trips`

| Column | MySQL type | Meaning |
|---|---|---|
| `trip_id` | INT UNSIGNED, primary key | Row number of the trip in the raw file (starts at 1), so every trip can be traced back |
| `vendor_id` | TINYINT UNSIGNED | Company that supplied the record: 1, 2 or 4 (4 is not in the TLC documentation) |
| `pickup_ts` | DATETIME | When the trip started |
| `dropoff_ts` | DATETIME | When the trip ended |
| `passenger_count` | TINYINT UNSIGNED, may be NULL | Passengers declared by the driver |
| `trip_distance_mi` | DECIMAL(8,2) | Distance on the meter, in miles (always above 0) |
| `rate_code_id` | TINYINT UNSIGNED | Fare type, 1 to 6 (2 = JFK flat fare) |
| `store_and_fwd` | TINYINT(1) | 1 if the trip was stored in the taxi before being sent, else 0 |
| `pu_location_id` | SMALLINT UNSIGNED | Pickup zone id (see the zones table) |
| `do_location_id` | SMALLINT UNSIGNED | Dropoff zone id |
| `payment_type_id` | TINYINT UNSIGNED | How the rider paid, 1 to 6 (1 = card, 2 = cash) |
| `fare_amount` | DECIMAL(10,2) | Metered fare (always above 0) |
| `extra` | DECIMAL(10,2) | Rush-hour and overnight extras |
| `mta_tax` | DECIMAL(10,2) | MTA tax |
| `tip_amount` | DECIMAL(10,2) | Tip. Cash tips are not recorded, so this is almost always 0 for cash trips |
| `tolls_amount` | DECIMAL(10,2) | Tolls paid |
| `improvement_surcharge` | DECIMAL(10,2) | Improvement surcharge |
| `congestion_surcharge` | DECIMAL(10,2) | Congestion surcharge (0 when it did not apply) |
| `total_amount` | DECIMAL(10,2) | Total charged to the rider (cash tips not included) |

Columns we calculate:

| Column | MySQL type | Meaning |
|---|---|---|
| `duration_min` | DECIMAL(10,3) | Trip length in minutes (dropoff minus pickup) |
| `avg_speed_mph` | DECIMAL(6,2) | Distance divided by duration in hours |
| `min_per_mile` | DECIMAL(12,3) | Minutes needed to drive one mile |
| `fare_per_mile` | DECIMAL(12,2) | Fare divided by distance |
| `fare_per_min` | DECIMAL(12,3) | Fare divided by duration in minutes |
| `pickup_date` | DATE | Day of the pickup |
| `pickup_hour` | TINYINT UNSIGNED | Hour of the pickup, 0 to 23 |
| `pickup_dow` | TINYINT UNSIGNED | Day of the week: **0 = Monday, 1 = Tuesday, ... 6 = Sunday** (pandas convention) |
| `is_weekend` | TINYINT(1) | 1 for Saturday and Sunday (`pickup_dow` is 5 or 6), else 0 |
| `is_flat_fare` | TINYINT(1) | 1 if the rate code is 2 (JFK flat fare of $52) |

Quality flags (the trip is kept, but marked). Each is 0 or 1 and never empty:

| Column | MySQL type | The flag is 1 when |
|---|---|---|
| `flag_unknown_zone` | TINYINT(1) | Pickup or dropoff is zone 264 or 265, so the place is unknown |
| `flag_passenger_suspect` | TINYINT(1) | Passenger count is 0, missing or above 6 |
| `flag_low_speed` | TINYINT(1) | Average speed is below 2 mph |
| `flag_total_mismatch` | TINYINT(1) | `total_amount` differs by more than $0.05 from the sum of its parts |

Values that must already exist in the lookup tables, or MySQL will refuse the trips:
vendors 1, 2 and 4; rate codes 1 to 6; payment types 1 to 6; zones 1 to 265 (including 264 and 265).

## Transparency tables (what the cleaning removed)

| Table | Columns | Meaning |
|---|---|---|
| `exclusion_reasons` | `reason_code` VARCHAR(40) PK, `action` VARCHAR(8) (EXCLUDED or FLAGGED), `description` VARCHAR(200) | The 20 cleaning rules |
| `cleaning_summary` | `reason_code` VARCHAR(40) PK, `row_count` INT UNSIGNED, `pct_of_raw` DECIMAL(7,4) | How many trips each rule affected. The name `row_count` avoids the MySQL keyword `rows` |
| `exclusion_log` | `log_id` INT AUTO_INCREMENT PK, `source_row` INT UNSIGNED, `reason_code` VARCHAR(40), `pickup_ts` DATETIME NULL, `dropoff_ts` DATETIME NULL, `trip_distance_mi` DECIMAL(12,2) NULL, `fare_amount` DECIMAL(12,2) NULL, `pu_location_id` INT NULL, `do_location_id` INT NULL | One row for every removed trip and reason (98,524 rows for 88,946 trips). The location ids are the raw values, so they have no foreign key |

Expected totals for January 2019: 7,667,792 trips read, 7,578,846 kept, 88,946 excluded (1.16%).
