CREATE DATABASE IF NOT EXISTS urban_mobility;
USE urban_mobility;

CREATE Table zones(
    location_id INT  PRIMARY KEY,
    borough VARCHAR(30),
    zone VARCHAR(100),
    service_zone VARCHAR(30)
);

CREATE Table zone_shapes(
    location_id INT PRIMARY KEY,
    geojson JSON,

    Foreign Key (location_id) REFERENCES zones(location_id)
);

CREATE Table payment_types(
    payment_type_id INT PRIMARY KEY,
    description VARCHAR(50)
);

CREATE Table rate_codes(
    rate_code_id INT PRIMARY KEY,
    description VARCHAR(50)
);

CREATE Table trips(
    trip_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    pickup_datetime DATETIME,
    dropoff_datetime DATETIME,
    passenger_count TINYINT,
    trip_distance DECIMAL(10,2),
    pickup_zone_id INT,
    dropoff_zone_id INT,
    rate_code_id INT,
    payment_type_id INT,
    fare_amount DECIMAL(10,2),
    total_amount DECIMAL(10,2),
    duration_min DECIMAL(10,2),
    speed_mph DECIMAL(10,2),
    min_per_mile DECIMAL(10,2),
    fare_per_min DECIMAL(10,2),

    fare_per_mile DECIMAL(10,2),
    pickup_date DATE,
    pickup_hour TINYINT,
    pickup_dow TINYINT,
    is_weekend TINYINT(1),
    is_flat_fare TINYINT(1),

    FOREIGN KEY (pickup_zone_id)
    REFERENCES zones(location_id),

    FOREIGN KEY (dropoff_zone_id)
    REFERENCES zones(location_id),

    FOREIGN KEY (rate_code_id)
    REFERENCES rate_codes(rate_code_id),

    FOREIGN KEY (payment_type_id)
    REFERENCES payment_types(payment_type_id)
);

CREATE Table exclusion_log(
    log_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    source_row_number BIGINT,
    reason_code VARCHAR(50),
    details VARCHAR(255),
    logged_at DATETIME
);