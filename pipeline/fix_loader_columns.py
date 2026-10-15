"""One-off: make pipeline/load_to_db.py write to the column names in database/schema.sql.
Run once from the repo root:  python pipeline/fix_loader_columns.py
(The loader's own comment says: if the table uses another name, change only the right-hand side.)"""
import re
from pathlib import Path

path = Path(__file__).resolve().parent / "load_to_db.py"
text = path.read_text(encoding="utf-8")
renames = {
    '"pickup_ts": "pickup_ts"': '"pickup_ts": "pickup_datetime"',
    '"dropoff_ts": "dropoff_ts"': '"dropoff_ts": "dropoff_datetime"',
    '"trip_distance_mi": "trip_distance_mi"': '"trip_distance_mi": "trip_distance"',
    '"avg_speed_mph": "avg_speed_mph"': '"avg_speed_mph": "speed_mph"',
}
start = text.index("TRIP_COLUMNS = {")
end = text.index("}", start)
block = text[start:end]
for old, new in renames.items():
    block = block.replace(old, new)
block = block.replace('"pu_location_id": "pu_location_id"', '"pu_location_id": "pickup_zone_id"')
block = block.replace('"do_location_id": "do_location_id"', '"do_location_id": "dropoff_zone_id"')
path.write_text(text[:start] + block + text[end:], encoding="utf-8")
print("TRIP_COLUMNS updated")
