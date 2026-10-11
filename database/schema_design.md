Table Name: zones
Columns: location_id(primary key, integer), borough(text), zone(text), service_zone(text)

location_id is the primary key because the yellow trip file already stores zone numbers in PULocationID and DOLocationID, and those numbers are the same as the LocationID in the Taxi zone lookup csv.

I kept borough as a column in zones because there are only 7 different boroughs which will be pointless to have a whole table for it.

Table Name: payment_types
Columns: payment_type_id(primary key, integer), description(text)

we will keep the 6 codes, so that a foreign key never fails on other months data

Table Name: rate_codes
Columns: rate_code_id(primary key, integer), description(text)

we keep code 99 so those trips can load under the foreign key