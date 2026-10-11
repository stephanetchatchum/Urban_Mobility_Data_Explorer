CREATE INDEX idx_trips_pickup_time ON trips (pickup_datetime);

CREATE INDEX idx_trips_zone_time ON trips (pickup_zone_id, pickup_datetime);