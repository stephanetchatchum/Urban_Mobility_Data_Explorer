"""Register each reasons why a trip should be excluded or flagged"""

EXCLUDED = "EXCLUDED"
FLAGGED = "FLAGGED"

REASONS = {
    "MISSING_VALUE": (EXCLUDED, "If a required field is empty or could not be parsed"),
    "DUPLICATE_RECORD": (EXCLUDED, "It is an exact copy of an earlier row"),
    "OUT_OF_RANGE_DATE": (EXCLUDED, "The time of pickup is outside the month of January"),
    "DROPOFF_BEFORE_PICKUP": (EXCLUDED, "The dropoff time is earlier than the pickup time"),
    "ZERO_DURATION": (EXCLUDED, "Dropoff time is equals to the pickup time"),
    "EXCESSIVE_DURATION": (EXCLUDED, "The trip is longer than 180 minutes"),
    "IMPOSSIBLE_SPEED": (EXCLUDED, "The average speed is greater than 80 mph"),
    "NON_POSITIVE_DISTANCE": (EXCLUDED, "The trip distance is zero or it is negative"),
    "EXCESSIVE_DISTANCE": (EXCLUDED, "The distance of the trip is greater than 100 miles"),
    "REVERSAL_OR_REFUND": (EXCLUDED, "A fare that is negative(reversal, refund, or dispute)"),
    "ZERO_FARE": (EXCLUDED, "The fare amount is zero"),
    "EXTREME_FARE": (EXCLUDED, "The fare amount is above 500usd"),
    "INVALID_VENDOR": (EXCLUDED, "Vendor id is not recognized"),
    "INVALID_RATE_CODE": (EXCLUDED, "The code is not in between 1 to 6"),
    "INVALID_PAYMENT_TYPE": (EXCLUDED, "The payment type is not in between 1 to 6"),
    "INVALID_ZONE_ID": (EXCLUDED, "Pickup or dropoff id is missing from the zone lookup"),
    "UNKNOWN_ZONE": (FLAGGED, "Pickup or dropoff in zone 264 or 265; kept, hidden from the maps and rankings"),
    "PASSENGER_COUNT_SUSPECT": (FLAGGED, "The passenger exceed 6 or is 0"),
    "LOW_SPEED": (FLAGGED, "The average speed is below 2 mph"),
    "TOTAL_MISMATCH": (FLAGGED, "The total_amount differs from the sum of its components by more than 0.05 usd"),
}