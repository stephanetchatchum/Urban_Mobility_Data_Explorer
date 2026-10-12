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

@app.route("/api/trips")
def trips():
    page = request.args.get("page",default=1, type=int)
    per_page = request.args.get("per_page", default=50, type=int)

    page = max(page, 1)
    per_page = min(max(per_page, 1), 200)

    offset = (page-1)*per_page

    connect = get_connection()
    cursor = connect.cursor(dictionary=True)
    try:
        cursor.execute("SELECT trip_id, pickup_datetime, trip_distance, fare_amount, speed_mph ""FROM trips ""ORDER BY trip_id ""LIMIT %s OFFSET %s", (per_page,offset),)
        rows = cursor.fetchall()
        return jsonify(rows)
    finally:
        cursor.close()
        connect.close()

if __name__ == "__main__":
    app.run(debug=True)