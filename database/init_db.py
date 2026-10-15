import os
import sys
import mysql.connector

from backend.db import get_connection
from pipeline.load_lookups import load_all

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")
INDEX_FILE = os.path.join(os.path.dirname(__file__), "indexes.sql")

def read_statements(path):
    with open(path, encoding="utf-8") as f:
        lines = [line for line in f if not line.strip().startswith("--")]
    statements = "".join(lines).split(";")
    return [s.strip() for s in statements if s.strip()]

def run_file(path, connect):
    cursor = connect.cursor()
    try:
        for statement in read_statements(path):
            cursor.execute(statement)
        connect.commit()
    finally:
        cursor.close()

def create_schema(reset):
    # the database may not exist yet, so we connect to the server without a database first
    server = mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD"),
    )
    name = os.environ.get("DB_NAME", "urban_mobility")
    try:
        if reset:
            cursor = server.cursor()
            cursor.execute("DROP DATABASE IF EXISTS " + name)
            cursor.close()
        run_file(SCHEMA_FILE, server)
    finally:
        server.close()

    load_all()

def create_indexes():
    connect = get_connection()
    try:
        run_file(INDEX_FILE, connect)
        print("Indexes created.")
    finally:
        connect.close()

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("schema", "indexes"):
        print("Usage: python -m database.init_db schema [--reset]  |  python -m database.init_db indexes")
        sys.exit(1)

    if sys.argv[1] == "schema":
        create_schema("--reset" in sys.argv)
    else:
        create_indexes()


