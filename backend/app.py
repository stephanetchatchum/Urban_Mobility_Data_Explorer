from flask import Flask, jsonify
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

if __name__ == "__main__":
    app.run(debug=True)