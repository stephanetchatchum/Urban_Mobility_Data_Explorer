"""Economics slice: what a ride costs hour by hour (Member 1's endpoint).

The numbers come from the table econ_hour, which pipeline/build_aggregates.py precomputed,
so the call is fast and the 7.5 million trips are not grouped on every request.
"""
from flask import Blueprint, jsonify, request

from backend.db import fetch_all

economics_bp = Blueprint("economics", __name__)

DAY_TYPES = ("weekday", "weekend")


@economics_bp.route("/api/economics/by-hour")
def by_hour():
    """Average fare, fees and card tip rate for each pickup hour.

    Optional day_type = weekday | weekend | all (default). With 'all' the weekday and weekend rows
    are combined, weighted by their number of trips.
    fees = everything on the bill that is neither fare nor tip. The tip rate is a percentage of the
    fare and only counts card payments, because cash tips are not recorded.
    """
    day_type = request.args.get("day_type", default="all")
    if day_type != "all" and day_type not in DAY_TYPES:
        return jsonify({"error": "day_type must be weekday, weekend or all"}), 400
    sql = ("SELECT pickup_hour AS hour, SUM(trips) AS trips, "
           "SUM(avg_fare * trips) / SUM(trips) AS avg_fare, "
           "SUM(avg_fees * trips) / SUM(trips) AS avg_fees, "
           "SUM(avg_fare_per_mile * trips) / SUM(trips) AS avg_fare_per_mile, "
           "SUM(card_tip_pct * card_trips) / NULLIF(SUM(card_trips), 0) AS card_tip_pct "
           "FROM econ_hour ")
    params = []
    if day_type != "all":
        sql += "WHERE day_type = %s "
        params.append(day_type)
    return jsonify(fetch_all(sql + "GROUP BY pickup_hour ORDER BY pickup_hour", params))
