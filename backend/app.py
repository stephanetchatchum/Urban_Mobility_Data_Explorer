from flask import Flask, jsonify, request
from backend.db import get_connection
from backend.algorithms.custom_algorithm import MinHeap
from backend.routes.story import story_bp
from backend.routes.economics import economics_bp
from backend.routes.heatmap import heatmap_bp
from flask_cors import CORS
from flask.json.provider import DefaultJSONProvider
from datetime import datetime
from decimal import Decimal

class MyJSONProvider(DefaultJSONProvider):
    # MySQL gives Decimal and datetime values, the default provider turns them into text
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, datetime):
            return o.strftime("%Y-%m-%dT%H:%M:%S")
        return super().default(o)

app = Flask(__name__)
app.json = MyJSONProvider(app)
CORS(app)
app.register_blueprint(story_bp)
app.register_blueprint(economics_bp)
app.register_blueprint(heatmap_bp)

@app.route("/api/health")
def health():
    return jsonify({"status":"ok"})

@app.route("/api/zones")
def zones():
    connect = get_connection()
    cursor = connect.cursor(dictionary=True)
    try:
        cursor.execute("SELECT location_id, borough, zone, service_zone FROM zones")
        rows = cursor.fetchall()

        return jsonify(rows)
    finally:
        cursor.close()
        connect.close()

SORT_COLUMNS = {
    "time": "pickup_datetime",
    "distance": "trip_distance",
    "fare": "fare_amount",
    "speed": "speed_mph",
    "duration": "duration_min",
}

def read_date(name):
    text = request.args.get(name)
    if not text:
        return None
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None
    return text

@app.route("/api/trips")
def trips():
    page = request.args.get("page",default=1, type=int)
    per_page = request.args.get("per_page", default=50, type=int)

    min_distance = request.args.get("min_distance", default=None, type=float)
    max_distance = request.args.get("max_distance", default=None, type=float)

    min_fare = request.args.get("min_fare", default=None, type=float)
    max_fare = request.args.get("max_fare", default=None, type=float)

    sort = request.args.get("sort", default="time")
    order = request.args.get("order", default="asc")    

    page = max(page, 1)
    per_page = min(max(per_page, 1), 200)

    offset = (page-1)*per_page

    if sort not in SORT_COLUMNS:
        sort = "time"
    if order not in ("asc", "desc"):
        order = "asc"

    conditions = []
    values = []

    pickup_zone = request.args.get("pickup_zone", type=int)
    if pickup_zone is not None:
        conditions.append("pickup_zone_id = %s")
        values.append(pickup_zone)

    dropoff_zone = request.args.get("dropoff_zone", type=int)
    if dropoff_zone is not None:
        conditions.append("dropoff_zone_id = %s")
        values.append(dropoff_zone)

    hour = request.args.get("hour", type=int)
    if hour is not None:
        conditions.append("pickup_hour = %s")
        values.append(hour)

    start_date = read_date("start_date")
    if start_date is not None:
        conditions.append("pickup_date >= %s")
        values.append(start_date)

    end_date = read_date("end_date")
    if end_date is not None:
        conditions.append("pickup_date <= %s")
        values.append(end_date)

    if min_distance is not None:
        conditions.append("trip_distance >= %s")
        values.append(min_distance)

    if max_distance is not None:
        conditions.append("trip_distance <= %s")
        values.append(max_distance)

    if min_fare is not None:
        conditions.append("fare_amount >= %s")
        values.append(min_fare)

    if max_fare is not None:
        conditions.append("fare_amount <= %s")
        values.append(max_fare)

    where_sql = ""
    if conditions:
        where_sql = "WHERE " + " AND ".join(conditions) + " "

    count_values = tuple(values)

    values.append(per_page)
    values.append(offset)

    sql = ("SELECT t.trip_id, t.pickup_datetime, t.trip_distance, t.duration_min, t.fare_amount, t.speed_mph, "
           "pz.zone AS pickup_zone, dz.zone AS dropoff_zone "
           "FROM trips t LEFT JOIN zones pz ON t.pickup_zone_id = pz.location_id "
           "LEFT JOIN zones dz ON t.dropoff_zone_id = dz.location_id " + where_sql + "ORDER BY " + SORT_COLUMNS[sort] + " " + order + ", t.trip_id LIMIT %s OFFSET %s")

    connect = get_connection()
    cursor = connect.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) AS total FROM trips " + where_sql, count_values)
        total = cursor.fetchone()["total"]

        cursor.execute(sql, tuple(values))
        rows = cursor.fetchall()
        for row in rows:
            for column in ("trip_distance", "duration_min", "fare_amount", "speed_mph"):
                if row[column] is not None:
                    row[column] = float(row[column])
            if row["pickup_datetime"] is not None:
                row["pickup_datetime"]= row["pickup_datetime"].strftime("%Y-%m-%d %H:%M:%S")

        total_pages = (total + per_page - 1) // per_page
        return jsonify({"page": page, "per_page": per_page, "total": total, "total_pages": total_pages, "data": rows})
    finally:
        cursor.close()
        connect.close()

@app.route("/api/trips/<int:trip_id>")
def trip_detail(trip_id):
    connect = get_connection()
    cursor = connect.cursor(dictionary=True)
    try:
        cursor.execute("SELECT t.*, pz.zone AS pickup_zone, pz.borough AS pickup_borough, "
                       "dz.zone AS dropoff_zone, dz.borough AS dropoff_borough, "
                       "pt.description AS payment_type, rc.description AS rate_code "
                       "FROM trips t LEFT JOIN zones pz ON t.pickup_zone_id = pz.location_id "
                       "LEFT JOIN zones dz ON t.dropoff_zone_id = dz.location_id "
                       "LEFT JOIN payment_types pt ON t.payment_type_id = pt.payment_type_id "
                       "LEFT JOIN rate_codes rc ON t.rate_code_id = rc.rate_code_id "
                       "WHERE t.trip_id = %s", (trip_id,))
        row = cursor.fetchone()
    finally:
        cursor.close()
        connect.close()

    if row is None:
        return jsonify({"error": "trip not found"}), 404

    for column in row:
        if hasattr(row[column], "strftime"):
            row[column] = str(row[column])
        elif row[column] is not None and not isinstance(row[column], (int, str)):
            row[column] = float(row[column])
    return jsonify(row)

@app.route("/api/zones/slowest")
def slowest_zones():
    k = request.args.get("k", default=10, type=int)
    min_trips = request.args.get("min_trips", default=30, type=int)

    k = min(max(k, 1), 50)
    min_trips = max(min_trips, 1)

    connect = get_connection()
    cursor = connect.cursor(dictionary=True)
    try:
        cursor.execute("SELECT z.zone AS zone, AVG(t.speed_mph) AS avg_speed ""FROM trips t JOIN zones z ON t.pickup_zone_id = z.location_id ""GROUP BY t.pickup_zone_id, z.zone ""HAVING COUNT(*) >= %s", (min_trips,))
        rows = cursor.fetchall()
    finally:
        cursor.close()
        connect.close()

    heap = MinHeap()
    for row in rows:
        if row["avg_speed"] is not None:
            heap.push((float(row["avg_speed"]), row["zone"]))

    slowest = []
    for _ in range(k):
        item = heap.pop()
        if item is None:
            break
        slowest.append({"zone": item[1], "avg_speed": round(item[0], 2)})

    return jsonify(slowest)

@app.route("/api/insights/top-routes")
def top_routes():
    n = request.args.get("n", default=10, type=int)
    min_trips = request.args.get("min_trips", default=30, type=int)

    n = min(max(n, 1), 100)
    min_trips = max(min_trips, 1)

    connect = get_connection()
    cursor = connect.cursor(dictionary=True)
    try:
        cursor.execute("SELECT t.pickup_zone_id, pz.zone AS pickup_zone, t.dropoff_zone_id, dz.zone AS dropoff_zone, "
                       "COUNT(*) AS trips, AVG(t.fare_amount) AS avg_fare, AVG(t.duration_min) AS avg_duration_min "
                       "FROM trips t JOIN zones pz ON t.pickup_zone_id = pz.location_id "
                       "JOIN zones dz ON t.dropoff_zone_id = dz.location_id "
                       "WHERE pz.is_mappable = 1 AND dz.is_mappable = 1 "
                       "GROUP BY t.pickup_zone_id, pz.zone, t.dropoff_zone_id, dz.zone "
                       "HAVING COUNT(*) >= %s", (min_trips,))
        rows = cursor.fetchall()
    finally:
        cursor.close()
        connect.close()

    # the heap gives the smallest first, so we push the trips as a negative number
    heap = MinHeap()
    for row in rows:
        heap.push((-row["trips"], row))

    busiest = []
    for _ in range(n):
        item = heap.pop()
        if item is None:
            break
        route = item[1]
        route["avg_fare"] = round(float(route["avg_fare"]), 2)
        route["avg_duration_min"] = round(float(route["avg_duration_min"]), 2)
        busiest.append(route)

    return jsonify(busiest)

@app.route("/api/insights/speed-by-hour")
def speed_by_hour():
    weekend = request.args.get("weekend", type=int)
    conditions = ["pickup_hour IS NOT NULL"]
    values = []
    if weekend in (0,1):
        conditions.append("is_weekend = %s")
        values.append(weekend)
    connect = get_connection()
    cursor = connect.cursor(dictionary=True)
    try:
        cursor.execute("SELECT pickup_hour AS hour, "
                       "AVG(speed_mph) AS avg_speed, "
                       "COUNT(speed_mph) AS trip_count "
                       "FROM trips WHERE " + " AND ".join(conditions) + " "
                       "GROUP BY pickup_hour "
                       "ORDER BY pickup_hour", tuple(values))
        rows = cursor.fetchall()
    finally:
        cursor.close()
        connect.close()

    for row in rows:
        if row["avg_speed"] is not None:
            row["avg_speed"] = round(float(row["avg_speed"]), 2)
    return jsonify(rows)

@app.route("/api/insights/cost-of-slowness")
def cost_of_slowness():
    weekend = request.args.get("weekend", type=int)
    conditions = ["pickup_hour IS NOT NULL",
                  "min_per_mile IS NOT NULL",
                  "fare_per_min IS NOT NULL"]

    values = []
    if weekend in (0, 1):
        conditions.append("is_weekend = %s")
        values.append(weekend)

    connect = get_connection()
    cursor = connect.cursor(dictionary=True)
    try:
        cursor.execute("SELECT pickup_hour AS hour, "
                       "AVG(min_per_mile) AS avg_min_per_mile, "
                       "AVG(fare_per_min) AS avg_fare_per_min, "
                       "COUNT(*) AS trip_count "
                       "FROM trips WHERE " + " AND ".join(conditions) + " "
                       "GROUP BY pickup_hour "
                       "ORDER BY pickup_hour", tuple(values))
        rows = cursor.fetchall()
    finally:
        cursor.close()
        connect.close()

    for row in rows:
        for column in ("avg_min_per_mile", "avg_fare_per_min"):
            if row[column] is not None:
                row[column] = round(float(row[column]), 2)
    return jsonify(rows)

if __name__ == "__main__":
    app.run(debug=True)
