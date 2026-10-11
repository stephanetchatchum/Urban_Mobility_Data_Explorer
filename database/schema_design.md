Table Name: zones
Columns: location_id(primary key, integer), borough(text), zone(text), service_zone(text)

location_id is the primary key because the yellow trip file already stores zone numbers in PULocationID and DOLocationID, and those numbers are the same as the LocationID in the Taxi zone lookup csv.

I kept borough as a column in zone because there are only 6 boroughs which will be pointless to have a whole table for it.

Table Name: payment_types
Colums: payement_type_id(primary key, integer), description(text)

