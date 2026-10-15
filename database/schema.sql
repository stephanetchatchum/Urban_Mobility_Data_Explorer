-- Urban Mobility Data Explorer: MySQL schema (one file: Member 2's design + the columns the pipeline output needs).
-- Run with: python -m database.init_db schema   (add --reset to drop and rebuild)
-- Load order: schema -> pipeline.load_to_db -> pipeline.load_extras -> database.init_db indexes
CREATE DATABASE IF NOT EXISTS urban_mobility;
USE urban_mobility;

CREATE TABLE zones (
    location_id INT PRIMARY KEY,
    borough VARCHAR(30),
    zone VARCHAR(100),
    service_zone VARCHAR(30),
    area_km2 DECIMAL(10,4) NULL,
    centroid_lat DECIMAL(9,6) NULL,
    centroid_lon DECIMAL(9,6) NULL,
    has_geometry TINYINT(1) NOT NULL DEFAULT 0,
    is_mappable TINYINT(1) NOT NULL DEFAULT 0
);

CREATE TABLE payment_types (
    payment_type_id INT PRIMARY KEY,
    description     VARCHAR(50)
);

CREATE TABLE rate_codes (
    rate_code_id INT PRIMARY KEY,
    description VARCHAR(50)
);

CREATE TABLE trips (
    trip_id BIGINT PRIMARY KEY,
    vendor_id TINYINT UNSIGNED NULL,
    pickup_datetime DATETIME,
    dropoff_datetime DATETIME,
    passenger_count TINYINT UNSIGNED NULL,
    trip_distance DECIMAL(10,2),
    pickup_zone_id INT,
    dropoff_zone_id INT,
    rate_code_id INT,
    payment_type_id INT,
    store_and_fwd TINYINT(1) NULL,
    fare_amount DECIMAL(10,2),
    extra DECIMAL(10,2) NULL,
    mta_tax DECIMAL(10,2) NULL,
    tip_amount DECIMAL(10,2) NULL,
    tolls_amount DECIMAL(10,2) NULL,
    improvement_surcharge DECIMAL(10,2) NULL,
    congestion_surcharge DECIMAL(10,2) NULL,
    total_amount DECIMAL(10,2),
    duration_min DECIMAL(10,3),
    speed_mph DECIMAL(10,2),
    min_per_mile DECIMAL(12,3),
    fare_per_min DECIMAL(12,3),
    fare_per_mile DECIMAL(12,2),
    pickup_date DATE,
    pickup_hour TINYINT UNSIGNED,
    pickup_dow TINYINT UNSIGNED,
    is_weekend TINYINT(1),
    is_flat_fare TINYINT(1),
    flag_unknown_zone TINYINT(1) NOT NULL DEFAULT 0,
    flag_passenger_suspect TINYINT(1) NOT NULL DEFAULT 0,
    flag_low_speed TINYINT(1) NOT NULL DEFAULT 0,
    flag_total_mismatch TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (pickup_zone_id) REFERENCES zones (location_id),
    FOREIGN KEY (dropoff_zone_id) REFERENCES zones (location_id),
    FOREIGN KEY (rate_code_id) REFERENCES rate_codes (rate_code_id),
    FOREIGN KEY (payment_type_id) REFERENCES payment_types (payment_type_id)
);

CREATE TABLE exclusion_reasons (
    reason_code VARCHAR(40) NOT NULL PRIMARY KEY,
    action VARCHAR(8) NOT NULL,
    description VARCHAR(200) NOT NULL
);

CREATE TABLE cleaning_summary (
    reason_code VARCHAR(40) NOT NULL PRIMARY KEY,
    row_count INT UNSIGNED NOT NULL,
    pct_of_raw DECIMAL(7,4) NOT NULL,
    FOREIGN KEY (reason_code) REFERENCES exclusion_reasons (reason_code)
);

CREATE TABLE exclusion_log (
    log_id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    source_row INT UNSIGNED NOT NULL,
    reason_code VARCHAR(40) NOT NULL,
    pickup_ts DATETIME NULL,
    dropoff_ts DATETIME NULL,
    trip_distance_mi DECIMAL(12,2) NULL,
    fare_amount DECIMAL(12,2) NULL,
    pu_location_id INT NULL,
    do_location_id INT NULL,
    FOREIGN KEY (reason_code) REFERENCES exclusion_reasons (reason_code)
);

CREATE TABLE zone_hour_stats (
    pu_location_id INT NOT NULL,
    pickup_hour TINYINT UNSIGNED NOT NULL,
    day_type VARCHAR(8) NOT NULL,
    trips INT UNSIGNED NOT NULL,
    mean_speed_mphn DECIMAL(8,3) NULL,
    median_speed_mph DECIMAL(8,3) NULL,
    median_min_per_mile DECIMAL(10,3) NULL,
    median_fare_per_min DECIMAL(10,3) NULL,
    median_fare_per_mile DECIMAL(10,3) NULL,
    raw_trips INT UNSIGNED NOT NULL,
    raw_speed_n INT UNSIGNED NOT NULL,
    raw_mean_speed_mph DECIMAL(8,3) NULL,
    is_reliable TINYINT(1) NOT NULL,
    PRIMARY KEY (pu_location_id, pickup_hour, day_type),
    FOREIGN KEY (pu_location_id) REFERENCES zones (location_id)
);

CREATE TABLE hour_stats (
    pickup_hour TINYINT UNSIGNED NOT NULL,
    day_type VARCHAR(8) NOT NULL,
    trips INT UNSIGNED NOT NULL,
    mean_speed_mph DECIMAL(8,3) NULL,
    median_speed_mph DECIMAL(8,3) NULL,
    median_min_per_mile DECIMAL(10,3) NULL,
    median_fare_per_min DECIMAL(10,3) NULL,
    median_fare_per_mile DECIMAL(10,3) NULL,
    raw_trips INT UNSIGNED NOT NULL,
    raw_speed_n INT UNSIGNED NOT NULL,
    raw_mean_speed_mph DECIMAL(8,3) NULL,
    is_reliable TINYINT(1) NOT NULL,
    PRIMARY KEY (pickup_hour, day_type)
);

CREATE TABLE daily_stats (
    pickup_date DATE NOT NULL PRIMARY KEY,
    trips INT UNSIGNED NOT NULL,
    mean_speed_mph DECIMAL(8,3) NULL,
    median_speed_mph DECIMAL(8,3) NULL,
    median_min_per_mile DECIMAL(10,3) NULL,
    median_fare_per_min DECIMAL(10,3) NULL,
    median_fare_per_mile DECIMAL(10,3) NULL,
    raw_trips INT UNSIGNED NOT NULL,
    raw_speed_n INT UNSIGNED NOT NULL,
    raw_mean_speed_mph DECIMAL(8,3) NULL,
    is_reliable TINYINT(1) NOT NULL
);

CREATE TABLE econ_hour (
    pickup_hour TINYINT UNSIGNED NOT NULL,
    day_type VARCHAR(8) NOT NULL,
    trips INT UNSIGNED NOT NULL,
    avg_fare DECIMAL(10,3) NULL,
    avg_fees DECIMAL(10,3) NULL,
    avg_fare_per_mile DECIMAL(10,3) NULL,
    card_trips INT UNSIGNED NOT NULL,
    card_tip_pct DECIMAL(8,3) NULL,
    PRIMARY KEY (pickup_hour, day_type)
);
