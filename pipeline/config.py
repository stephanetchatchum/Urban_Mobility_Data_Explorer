import os
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
LOGS_DIR = ROOT / "data" /"logs"

# Database connection (MySQL). The real values are set as environment variables, never typed in the code.
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "urban_mobility")
DB_SSL_CA = os.environ.get("DB_SSL_CA")   # optional: path to the certificate file some cloud databases require

# Setting a valid start date and end date from where trips should be picked up and analyse
DATA_START = datetime(2019, 1, 1)
DATA_END = datetime(2019, 2, 1)

# Setting all physical and logical limits for data collection to be analyse
MAX_DURATION_MIN = 180          # If it is higher than this value it means the meter was left running
MAX_SPEED_MPH = 80              # It is not realistic to go beyond this limit in New York City
MAX_DISTANCE_MI = 100           # A distance longer than this is not consider as a normal yellow cab trip
MAX_FARE_USD = 500              # Above this limit should be considered an outlier
LOW_SPEED_FLAG_MPH = 2.0        # Kept but flagged: walking pace or bad distance
TOTAL_TOLERANCE_USD = 0.05      # Allowed rounding gap between total_amount and its parts
MAX_PASSENGERS = 6              # It is the legal capacity allowed for yellow cabs


VALID_VENDORS = (1, 2, 4)
VALID_RATE_CODES = (1, 2, 3, 4, 5, 6)
VALID_PAYMENT_TYPES = (1, 2, 3, 4, 5, 6)
FLAT_FARE_RATE_CODE = 2
UNKNOWN_ZONE_IDS = (264, 265)

MIN_TRIPS_RELIABLE = 30
DEFAULT_CHUNK_SIZE = 500_000