from flask import Flask, jsonify, request
from backend.db import get_connection
from backend.algorithms.custom_algorithm import MinHeap
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

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

    values.append(per_page)
    values.append(offset)

    sql = ("SELECT trip_id, pickup_datetime, trip_distance, fare_amount, speed_mph ""FROM trips " + where_sql + "ORDER BY " + SORT_COLUMNS[sort] + " " + order + ", trip_id LIMIT %s OFFSET %s")

    connect = get_connection()
    cursor = connect.cursor(dictionary=True)
    try:
        cursor.execute(sql, tuple(values))
        rows = cursor.fetchall()
        for row in rows:
            for column in ("trip_distance", "fare_amount", "speed_mph"):
                if row[column] is not None:
                    row[column] = float(row[column])
            if row["pickup_datetime"] is not None:
                row["pickup_datetime"]= row["pickup_datetime"].strftime("%Y-%m-%d %H:%M:%S")

        return jsonify(rows)
    finally:
        cursor.close()
        connect.close()

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

if __name__ == "__main__":
    app.run(debug=True)