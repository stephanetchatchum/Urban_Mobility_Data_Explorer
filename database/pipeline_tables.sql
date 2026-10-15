-- MySQL tables that receive the pipeline output.
-- Member 2: compare `trips` with your own table, add the columns you are missing, and copy the
-- three transparency tables into schema.sql. Column names and types are explained in docs/data_dictionary.md.

CREATE TABLE IF NOT EXISTS trips (
    trip_id                INT UNSIGNED      NOT NULL PRIMARY KEY,   -- row number in the raw file
    vendor_id              TINYINT UNSIGNED  NOT NULL,
    pickup_ts              DATETIME          NOT NULL,
    dropoff_ts             DATETIME          NOT NULL,
    passenger_count        TINYINT UNSIGNED  NULL,
    trip_distance_mi       DECIMAL(8,2)      NOT NULL,
    rate_code_id           TINYINT UNSIGNED  NOT NULL,
    store_and_fwd          TINYINT(1)        NOT NULL,
    pu_location_id         SMALLINT UNSIGNED NOT NULL,
    do_location_id         SMALLINT UNSIGNED NOT NULL,
    payment_type_id        TINYINT UNSIGNED  NOT NULL,
    fare_amount            DECIMAL(10,2)     NOT NULL,
    extra                  DECIMAL(10,2)     NOT NULL,
    mta_tax                DECIMAL(10,2)     NOT NULL,
    tip_amount             DECIMAL(10,2)     NOT NULL,
    tolls_amount           DECIMAL(10,2)     NOT NULL,
    improvement_surcharge  DECIMAL(10,2)     NOT NULL,
    congestion_surcharge   DECIMAL(10,2)     NOT NULL,
    total_amount           DECIMAL(10,2)     NOT NULL,
    duration_min           DECIMAL(10,3)     NOT NULL,
    avg_speed_mph          DECIMAL(6,2)      NOT NULL,
    min_per_mile           DECIMAL(12,3)     NOT NULL,
    fare_per_mile          DECIMAL(12,2)     NOT NULL,
    fare_per_min           DECIMAL(12,3)     NOT NULL,
    pickup_date            DATE              NOT NULL,
    pickup_hour            TINYINT UNSIGNED  NOT NULL,              -- 0 to 23
    pickup_dow             TINYINT UNSIGNED  NOT NULL,              -- 0 = Monday ... 6 = Sunday
    is_weekend             TINYINT(1)        NOT NULL,
    is_flat_fare           TINYINT(1)        NOT NULL,
    flag_unknown_zone      TINYINT(1)        NOT NULL,
    flag_passenger_suspect TINYINT(1)        NOT NULL,
    flag_low_speed         TINYINT(1)        NOT NULL,
    flag_total_mismatch    TINYINT(1)        NOT NULL
);

CREATE TABLE IF NOT EXISTS exclusion_reasons (
    reason_code  VARCHAR(40)  NOT NULL PRIMARY KEY,
    action       VARCHAR(8)   NOT NULL,                              -- EXCLUDED or FLAGGED
    description  VARCHAR(200) NOT NULL
);

CREATE TABLE IF NOT EXISTS cleaning_summary (
    reason_code  VARCHAR(40)   NOT NULL PRIMARY KEY,
    row_count    INT UNSIGNED  NOT NULL,
    pct_of_raw   DECIMAL(7,4)  NOT NULL,
    FOREIGN KEY (reason_code) REFERENCES exclusion_reasons (reason_code)
);

CREATE TABLE IF NOT EXISTS exclusion_log (
    log_id            INT UNSIGNED  NOT NULL AUTO_INCREMENT PRIMARY KEY,
    source_row        INT UNSIGNED  NOT NULL,
    reason_code       VARCHAR(40)   NOT NULL,
    pickup_ts         DATETIME      NULL,
    dropoff_ts        DATETIME      NULL,
    trip_distance_mi  DECIMAL(12,2) NULL,
    fare_amount       DECIMAL(12,2) NULL,
    pu_location_id    INT           NULL,   -- raw value, may be invalid, so no foreign key
    do_location_id    INT           NULL,
    FOREIGN KEY (reason_code) REFERENCES exclusion_reasons (reason_code)
);
