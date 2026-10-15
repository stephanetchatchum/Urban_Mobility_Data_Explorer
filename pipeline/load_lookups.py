import csv

from backend.db import get_connection
from .config import RAW_DIR

LOOKUP_CSV = RAW_DIR / "taxi_zone_lookup.csv"

PAYMENT_TYPES = [
    (1, "Credit card"), (2, "Cash"), (3, "No charge"),
    (4, "Dispute"), (5, "Unknown"), (6, "Voided trip"),
]

RATE_CODES =[
    (1, "Standard rate"), (2, "JFK"), (3, "Newark"), (4, "Nassau or Westchester"),
    (5, "Negotiated fare"), (6, "Group ride"), (99, "Unknown"),
]

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

def load_all():
    zones = read_zones()

    connect = get_connection()
    cursor = connect.cursor()
    try:
        cursor.executemany(
            "INSERT INTO zones (location_id, borough, zone, service_zone) "
            "VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE borough = VALUES(borough), "
            "zone = VALUES(zone), service_zone = VALUES(service_zone)",
            zones)
        cursor.executemany(
            "INSERT INTO payment_types (payment_type_id, description) "
            "VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE description = VALUES(description)",
            PAYMENT_TYPES)
        cursor.executemany(
            "INSERT INTO rate_codes (rate_code_id, description) "
            "VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE description = VALUES(description)",
            RATE_CODES)
        connect.commit()
        print("Loaded", len(zones), "zones,", len(PAYMENT_TYPES), "payment types,", len(RATE_CODES), "rate codes.")
    finally:
        cursor.close()
        connect.close()

if __name__ == "__main__":
    load_all()
