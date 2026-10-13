from flask import Flask, jsonify, request
from backend.db import get_connection

app = Flask(__name__)

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

if __name__ == "__main__":
    app.run(debug=True)