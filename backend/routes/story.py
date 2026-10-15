"""The "price of slowness" story and the trust layer (Member 1's endpoints).

Every number comes from tables that pipeline/build_aggregates.py precomputed, so each call is fast.
A zone-hour cell is only ranked when it has at least MIN_TRIPS_RELIABLE cleaned trips, and the
unknown zones 264 / 265 are never ranked or mapped (is_mappable = 0).
"""
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from backend.algorithms.custom_algorithm import k_smallest
from backend.db import fetch_all

story_bp = Blueprint("story", __name__)

MIN_TRIPS_RELIABLE = 30
GEOJSON = Path(__file__).resolve().parents[2] / "data" / "processed" / "zones.geojson"
DAY_TYPES = ("weekday", "weekend")


def _day_type():
    """Return (value, error). 'all' or missing means no filter."""
    value = request.args.get("day_type", default="all")
    if value == "all":
        return None, None
    if value not in DAY_TYPES:
        return None, "day_type must be weekday, weekend or all"
    return value, None


@story_bp.route("/api/zones/geojson")
def zones_geojson():
    """Zone polygons in lat/lon. Each feature has location_id, zone_name, borough, service_zone."""
    if not GEOJSON.exists():
        return jsonify({"error": "zones.geojson not found; run python -m pipeline.run_pipeline"}), 404
    return send_file(GEOJSON, mimetype="application/json")


@story_bp.route("/api/story/hour-profile")
def hour_profile():
    """Minutes per mile, speed and fare per minute for each hour (the main chart and heatmap)."""
    day_type, error = _day_type()
    if error:
        return jsonify({"error": error}), 400
    sql = ("SELECT pickup_hour AS hour, day_type, trips, median_min_per_mile, median_speed_mph, "
           "median_fare_per_min, median_fare_per_mile FROM hour_stats ")
    params = []
    if day_type:
        sql += "WHERE day_type = %s "
        params.append(day_type)
    return jsonify(fetch_all(sql + "ORDER BY day_type, pickup_hour", params))


@story_bp.route("/api/story/zone-hour")
def zone_hour():
    """One row per mappable zone for a chosen hour: colours the map. Cells under 30 trips are marked unreliable."""
    day_type, error = _day_type()
    hour = request.args.get("hour", type=int)
    if error or hour is None or not 0 <= hour <= 23:
        return jsonify({"error": error or "hour (0-23) is required"}), 400
    sql = ("SELECT s.pu_location_id AS location_id, z.zone, z.borough, s.day_type, s.trips, s.is_reliable, "
           "s.median_min_per_mile, s.median_speed_mph, s.median_fare_per_min "
           "FROM zone_hour_stats s JOIN zones z ON z.location_id = s.pu_location_id "
           "WHERE z.is_mappable = 1 AND s.trips > 0 AND s.pickup_hour = %s ")
    params = [hour]
    if day_type:
        sql += "AND s.day_type = %s "
        params.append(day_type)
    return jsonify(fetch_all(sql, params))


@story_bp.route("/api/story/slowest-zones")
def slowest_zones():
    """The n slowest zones (most minutes per mile) for a range of hours, with the trips behind each.

    SQL adds up the zone-hour cells; the ranking is done by the hand-written heap (k_smallest on the
    negated value), not by ORDER BY. The zone value is the trips-weighted mean of the cell medians.
    """
    day_type, error = _day_type()
    n = min(max(request.args.get("n", default=10, type=int), 1), 100)
    hour_from = request.args.get("hour_from", default=0, type=int)
    hour_to = request.args.get("hour_to", default=23, type=int)
    min_trips = request.args.get("min_trips", default=MIN_TRIPS_RELIABLE, type=int)
    if error or not 0 <= hour_from <= hour_to <= 23:
        return jsonify({"error": error or "hour_from and hour_to must satisfy 0 <= from <= to <= 23"}), 400
    sql = ("SELECT s.pu_location_id AS location_id, z.zone, z.borough, SUM(s.trips) AS trips, "
           "SUM(s.median_min_per_mile * s.trips) / SUM(s.trips) AS min_per_mile, "
           "SUM(s.median_speed_mph * s.trips) / SUM(s.trips) AS speed_mph, "
           "SUM(s.median_fare_per_min * s.trips) / SUM(s.trips) AS fare_per_min "
           "FROM zone_hour_stats s JOIN zones z ON z.location_id = s.pu_location_id "
           "WHERE z.is_mappable = 1 AND s.trips > 0 AND s.pickup_hour BETWEEN %s AND %s ")
    params = [hour_from, hour_to]
    if day_type:
        sql += "AND s.day_type = %s "
        params.append(day_type)
    sql += "GROUP BY s.pu_location_id, z.zone, z.borough HAVING SUM(s.trips) >= %s"
    params.append(min_trips)
    per_zone = [r for r in fetch_all(sql, params) if r["min_per_mile"] is not None]
    return jsonify(k_smallest(per_zone, n, lambda r: -float(r["min_per_mile"])))


@story_bp.route("/api/trust/summary")
def trust_summary():
    """Every cleaning rule with its action, description, row count and share of the raw file."""
    return jsonify(fetch_all(
        "SELECT r.reason_code, r.action, r.description, c.row_count, c.pct_of_raw "
        "FROM exclusion_reasons r JOIN cleaning_summary c ON c.reason_code = r.reason_code "
        "ORDER BY c.row_count DESC"))


@story_bp.route("/api/trust/raw-vs-clean")
def raw_vs_clean():
    """Mean speed before and after cleaning, by hour (default) or by day. Drives the raw / cleaned toggle."""
    by = request.args.get("by", default="hour")
    day_type, error = _day_type()
    if by not in ("hour", "day") or error:
        return jsonify({"error": error or "by must be hour or day"}), 400
    if by == "day":
        sql = ("SELECT pickup_date AS day, trips, raw_trips, mean_speed_mph, raw_mean_speed_mph "
               "FROM daily_stats WHERE pickup_date >= '2019-01-01' AND pickup_date < '2019-02-01' "
               "ORDER BY pickup_date")
        return jsonify(fetch_all(sql))
    sql = ("SELECT pickup_hour AS hour, day_type, trips, raw_trips, mean_speed_mph, raw_mean_speed_mph "
           "FROM hour_stats ")
    params = []
    if day_type:
        sql += "WHERE day_type = %s "
        params.append(day_type)
    return jsonify(fetch_all(sql + "ORDER BY day_type, pickup_hour", params))


@story_bp.route("/api/trust/exclusion-log")
def exclusion_log():
    """A page of removed trips, so a reader can inspect them. Filter with ?reason=ZERO_FARE."""
    reason = request.args.get("reason")
    page = max(request.args.get("page", default=1, type=int), 1)
    per_page = min(max(request.args.get("per_page", default=50, type=int), 1), 200)
    where, params = ("WHERE reason_code = %s ", [reason]) if reason else ("", [])
    rows = fetch_all("SELECT log_id, source_row, reason_code, pickup_ts, dropoff_ts, trip_distance_mi, "
                     "fare_amount, pu_location_id, do_location_id FROM exclusion_log "
                     f"{where}ORDER BY log_id LIMIT %s OFFSET %s", params + [per_page, (page - 1) * per_page])
    total = fetch_all(f"SELECT COUNT(*) AS n FROM exclusion_log {where}", params)[0]["n"]
    return jsonify({"page": page, "per_page": per_page, "total": total, "data": rows})
