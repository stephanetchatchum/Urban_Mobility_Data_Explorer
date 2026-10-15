from flask import Blueprint, jsonify, request

from backend.db import fetch_all

heatmap_bp = Blueprint("heatmap", __name__)

# grouping 7 million trips takes a few seconds, so we do it once and keep the answer in memory
cache = {}

METRICS = {
    "trips": "COUNT(*)",
    "speed": "AVG(speed_mph)",
    "min_per_mile": "AVG(min_per_mile)",
}

@heatmap_bp.route("/api/time/heatmap")
def heatmap():
    metric = request.args.get("metric", default="trips")
    if metric not in METRICS:
        return jsonify({"error": "metric must be trips, speed or min_per_mile"}), 400

    if metric not in cache:
        sql = ("SELECT pickup_dow AS dow, pickup_hour AS hour, " + METRICS[metric] + " AS value, COUNT(*) AS trips "
               "FROM trips GROUP BY pickup_dow, pickup_hour ORDER BY pickup_dow, pickup_hour")
        rows = fetch_all(sql)
        for row in rows:
            row["value"] = float(row["value"]) if row["value"] is not None else None
        cache[metric] = rows

    return jsonify(cache[metric])
