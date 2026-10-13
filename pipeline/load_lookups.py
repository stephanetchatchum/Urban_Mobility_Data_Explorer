"""Load the zone lookup table (taxi_zone_lookup.csv) into the zones table
Run from the project root, after database/schema.sql:
  python -m pipeline.load_lookups

It is safe to run more than once.
"""
import csv

from backend.db import get_connection
from .config import RAW_DIR

LOOKUP_CSV = RAW_DIR / "taxi_zone_lookup.csv"

def clean(text):
    text = text.strip()
    if text == "" or text == "N/A":
        return "Unknown"
    return text

def read_zones():
    zones = []
    with open(LOOKUP_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            zones.append((int(row["LocationID"]), clean(row["Borough"]), clean(row["Zone"]), clean(row["service_zone"])))
    
    return zones

def load_zones():
    zones = read_zones()

    connect = get_connection()
    cursor = connect.cursor()
    try:
        cursor.executemany("INSERT INTO zones (location_id, borough, zone, service_zone) ""VALUES (%s, %s, %s, %s) ""ON DUPLICATE KEY UPDATE borough = VALUES(borough), ""zone = VALUES(zone), service_zone = VALUES(service_zone)", zones)
        connect.commit()
        print("Loaded", len(zones), "zones.")
    finally:
        cursor.close()
        connect.close()

if __name__ == "__main__":
    load_zones()