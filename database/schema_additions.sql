-- Run ONCE, right after Member 2's schema.sql (python -m database.init_db schema), and BEFORE the loaders.
-- Everything here is what the pipeline output needs and the first schema did not have.
USE urban_mobility;

-- 1. Trips: the 8 raw columns the pipeline keeps (needed for fare / fee / tip analysis and for tracing a trip)
ALTER TABLE trips
    ADD COLUMN vendor_id             TINYINT UNSIGNED NULL,
    ADD COLUMN store_and_fwd         TINYINT(1)       NULL,
    ADD COLUMN extra                 DECIMAL(10,2)    NULL,
    ADD COLUMN mta_tax               DECIMAL(10,2)    NULL,
    ADD COLUMN tip_amount            DECIMAL(10,2)    NULL,
    ADD COLUMN tolls_amount          DECIMAL(10,2)    NULL,
    ADD COLUMN improvement_surcharge DECIMAL(10,2)    NULL,
    ADD COLUMN congestion_surcharge  DECIMAL(10,2)    NULL;

-- 2. Zones: geometry facts computed from the shapefile (pipeline/zones_to_geojson.py)
ALTER TABLE zones
    ADD COLUMN area_km2     DECIMAL(10,4) NULL,
    ADD COLUMN centroid_lat DECIMAL(9,6)  NULL,
    ADD COLUMN centroid_lon DECIMAL(9,6)  NULL,
    ADD COLUMN has_geometry TINYINT(1)    NOT NULL DEFAULT 0,
    ADD COLUMN is_mappable  TINYINT(1)    NOT NULL DEFAULT 0;   -- 0 for unknown zones 264 / 265

-- 3. Transparency tables. Member 2's first exclusion_log did not match the pipeline output, so it is replaced.
DROP TABLE IF EXISTS exclusion_log;
CREATE TABLE exclusion_reasons (
    reason_code  VARCHAR(40)  NOT NULL PRIMARY KEY,
    action       VARCHAR(8)   NOT NULL,          -- EXCLUDED or FLAGGED
    description  VARCHAR(200) NOT NULL
);
CREATE TABLE cleaning_summary (
    reason_code  VARCHAR(40)   NOT NULL PRIMARY KEY,
    row_count    INT UNSIGNED  NOT NULL,
    pct_of_raw   DECIMAL(7,4)  NOT NULL,
    FOREIGN KEY (reason_code) REFERENCES exclusion_reasons (reason_code)
);
CREATE TABLE exclusion_log (
    log_id            INT UNSIGNED  NOT NULL AUTO_INCREMENT PRIMARY KEY,
    source_row        INT UNSIGNED  NOT NULL,    -- row number in the raw file
    reason_code       VARCHAR(40)   NOT NULL,
    pickup_ts         DATETIME      NULL,
    dropoff_ts        DATETIME      NULL,
    trip_distance_mi  DECIMAL(12,2) NULL,
    fare_amount       DECIMAL(12,2) NULL,
    pu_location_id    INT           NULL,        -- raw value, may be invalid, so no foreign key
    do_location_id    INT           NULL,
    FOREIGN KEY (reason_code) REFERENCES exclusion_reasons (reason_code)
);

-- 4. Precomputed statistics for the "price of slowness" story (cleaned AND raw, so the dashboard can toggle)
CREATE TABLE zone_hour_stats (
    pu_location_id       INT              NOT NULL,
    pickup_hour          TINYINT UNSIGNED NOT NULL,
    day_type             VARCHAR(8)       NOT NULL,       -- weekday / weekend
    trips                INT UNSIGNED     NOT NULL,       -- cleaned trips behind the numbers
    mean_speed_mph       DECIMAL(8,3) NULL,
    median_speed_mph     DECIMAL(8,3) NULL,
    median_min_per_mile  DECIMAL(10,3) NULL,
    median_fare_per_min  DECIMAL(10,3) NULL,              -- flat-fare trips left out
    median_fare_per_mile DECIMAL(10,3) NULL,
    raw_trips            INT UNSIGNED NOT NULL,
    raw_speed_n          INT UNSIGNED NOT NULL,
    raw_mean_speed_mph   DECIMAL(8,3) NULL,
    is_reliable          TINYINT(1)   NOT NULL,           -- 1 when trips >= 30
    PRIMARY KEY (pu_location_id, pickup_hour, day_type),
    FOREIGN KEY (pu_location_id) REFERENCES zones (location_id)
);
CREATE TABLE hour_stats (
    pickup_hour          TINYINT UNSIGNED NOT NULL,
    day_type             VARCHAR(8)       NOT NULL,
    trips                INT UNSIGNED     NOT NULL,
    mean_speed_mph       DECIMAL(8,3) NULL,
    median_speed_mph     DECIMAL(8,3) NULL,
    median_min_per_mile  DECIMAL(10,3) NULL,
    median_fare_per_min  DECIMAL(10,3) NULL,
    median_fare_per_mile DECIMAL(10,3) NULL,
    raw_trips            INT UNSIGNED NOT NULL,
    raw_speed_n          INT UNSIGNED NOT NULL,
    raw_mean_speed_mph   DECIMAL(8,3) NULL,
    is_reliable          TINYINT(1)   NOT NULL,
    PRIMARY KEY (pickup_hour, day_type)
);
CREATE TABLE daily_stats (
    pickup_date          DATE         NOT NULL PRIMARY KEY,   -- includes the few out-of-range raw dates (2001, 2088 ...)
    trips                INT UNSIGNED NOT NULL,
    mean_speed_mph       DECIMAL(8,3) NULL,
    median_speed_mph     DECIMAL(8,3) NULL,
    median_min_per_mile  DECIMAL(10,3) NULL,
    median_fare_per_min  DECIMAL(10,3) NULL,
    median_fare_per_mile DECIMAL(10,3) NULL,
    raw_trips            INT UNSIGNED NOT NULL,
    raw_speed_n          INT UNSIGNED NOT NULL,
    raw_mean_speed_mph   DECIMAL(8,3) NULL,
    is_reliable          TINYINT(1)   NOT NULL
);
