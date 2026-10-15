import os
import mysql.connector

def get_connection():
    settings = {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", "3306")),
        "user": os.environ.get("DB_USER", "root"),
        "password": os.environ.get("DB_PASSWORD"),
        "database": os.environ.get("DB_NAME", "urban_mobility"),
    }
    if os.environ.get("DB_SSL_CA"):
        settings["ssl_ca"] = os.environ.get("DB_SSL_CA")
    return mysql.connector.connect(**settings)

def fetch_all(sql, params=()):
    connect = get_connection()
    cursor = connect.cursor(dictionary=True)
    try:
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
    finally:
        cursor.close()
        connect.close()
