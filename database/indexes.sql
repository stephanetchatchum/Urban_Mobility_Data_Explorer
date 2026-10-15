CREATE INDEX idx_trips_pickup_time ON trips (pickup_datetime);

CREATE INDEX idx_trips_zone_time ON trips (pickup_zone_id, pickup_datetime);

CREATE INDEX idx_trips_route ON trips (pickup_zone_id, dropoff_zone_id);

CREATE INDEX idx_trips_date_hour ON trips (pickup_date, pickup_hour);

CREATE INDEX idx_trips_hour ON trips (pickup_hour);

CREATE INDEX idx_trips_fare ON trips (fare_amount);

CREATE INDEX idx_trips_distance ON trips (trip_distance);

