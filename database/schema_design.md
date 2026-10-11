## Tables
**Table Name:** `zones`
**Columns:** location_id(primary key, integer), borough(text), zone(text), service_zone(text)

location_id is the primary key because the yellow trip file already stores zone numbers in PULocationID and DOLocationID, and those numbers are the same as the LocationID in the Taxi zone lookup csv.

I kept borough as a column in zones because there are only 7 different boroughs which will be pointless to have a whole table for it.

**Table Name:** `payment_types`
**Columns:** payment_type_id(primary key, integer), description(text)

we will keep the 6 codes, so that a foreign key never fails on other months data

**Table Name:** `rate_codes`
Columns: rate_code_id(primary key, integer), description(text)

we keep code 99 so those trips can load under the foreign key

**Table Name:** `trips`
Columns: trip_id(primary key, integer, auto increment), pickup_datetime(datetime{ISO format}), dropoff_datetime(datetime{ISO format}), passenger_count(integer), trip_distance(decimal),
pickup_zone_id(foreign key to zones.location_id, integer), dropoff_zone_id(foreign key to zones.location_id, integer), rate_code_id(foreign key to rate_codes.rate_code_id, integer), payment_type_id(foreign key to payment_types.payment_type_id, integer), fare_amount(decimal), total_amount(decimal), duration_min(decimal, dropoff - pickup, in mins), speed_mph(decimal, distance/duration in hours), min_per_mile(decimal, duration/distance), fare_per_min(decimal, fare/duration) 

we dropped congestion_surcharge column because it is almost empty, we also dropped tip_amount, extra, mta_tax, tolls_amount, improvement_surcharge, and store_and_fwd_flag because they donot connect to the story. 

**Table Name:** `exclusion_log`
**Columns:** log_id(primary key, integer)
source_row_number(integer), reason_code(character), details(character), logged_at(datetime)

this table has no foreign key linked to trips because the excluded rows never get loaded

## Indexes
**idx_tripspickup_time** on `pickup_datetime`
this speeds up any query that filters or groups by time. This prevents mysql from scaning 7 million rows

**idx_trips_zone_time** on (`pickup_zone_id`, `pickupt_datetime`)
this speeds up the query of about one zone at a time

**automatic indexes**
mysql created indexes on orein key columns (`dropoff_zone_id`, `rate_code_id`, `payment_type_id`)

**trade-off and load order**
unfortunately, indexes insert slower, because they update with every inserted row, and that is why we separate the different sql codes, to avoid the slowing down of the 7.6 million rows. The run order is schema.sql then the data load, then the indexes.sql