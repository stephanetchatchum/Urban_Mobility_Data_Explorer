import sqlite3
import sys
from datetime import datetime
import types

try:
    import mysql.connector  # noqa: F401
except ImportError:
    sys.modules["mysql"] = types.ModuleType("mysql")
    sys.modules["mysql.connector"] = types.ModuleType("mysql.connector")

import pytest

from backend import app as app_module
from backend.routes import story


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self.cursor = None

    def execute(self, sql, params=()):
        self.cursor = self.db.execute(sql.replace("%s", "?"), list(params))

    def fetchall(self):
        rows = [dict(r) for r in self.cursor.fetchall()]
        for row in rows:                      # MySQL returns datetime objects, SQLite returns text
            if isinstance(row.get("pickup_datetime"), str):
                row["pickup_datetime"] = datetime.fromisoformat(row["pickup_datetime"])
        return rows

    def fetchone(self):
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def close(self):
        pass


class FakeConnection:
    def __init__(self, db):
        self.db = db

    def cursor(self, dictionary=False):
        return FakeCursor(self.db)

    def close(self):
        pass


@pytest.fixture()
def client(monkeypatch):
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE zones (location_id INT, borough TEXT, zone TEXT, service_zone TEXT, is_mappable INT);
        CREATE TABLE payment_types (payment_type_id INT, description TEXT);
        CREATE TABLE rate_codes (rate_code_id INT, description TEXT);
        CREATE TABLE trips (trip_id INT, pickup_datetime TEXT, trip_distance REAL, duration_min REAL, speed_mph REAL,
            min_per_mile REAL, fare_amount REAL, pickup_zone_id INT, dropoff_zone_id INT, payment_type_id INT,
            rate_code_id INT, pickup_date TEXT, pickup_hour INT, pickup_dow INT);
        INSERT INTO zones VALUES (1,'Manhattan','A','Yellow',1),(2,'Queens','B','Boro',1),(264,'Unknown','N/A','N/A',0);
        INSERT INTO payment_types VALUES (1,'Credit card'); INSERT INTO rate_codes VALUES (1,'Standard rate');
        INSERT INTO trips VALUES (1,'2019-01-01 08:00:00',3.0,20,9.0,6.7,15.0,1,2,1,1,'2019-01-01',8,1),
                                 (2,'2019-01-01 09:00:00',1.0,10,6.0,10.0,8.0,2,1,1,1,'2019-01-01',9,1),
                                 (3,'2019-01-02 10:00:00',9.0,30,18.0,3.3,30.0,1,2,1,1,'2019-01-02',10,2),
                                 (4,'2019-01-02 11:00:00',2.0,10,12.0,5.0,9.0,1,264,1,1,'2019-01-02',11,2);
    """)
    fake = lambda: FakeConnection(db)
    monkeypatch.setattr(app_module, "get_connection", fake)
    monkeypatch.setattr(story, "fetch_all", lambda sql, params=(): [dict(r) for r in db.execute(sql.replace("%s", "?"), list(params))])
    return app_module.app.test_client()


def test_trips_sort_filter_and_paging(client):
    r = client.get("/api/trips?sort=fare&order=desc&per_page=2").get_json()
    assert [t["trip_id"] for t in r["data"]] == [3, 1]
    assert r["total"] == 4 and r["total_pages"] == 2
    assert r["data"][0]["pickup_zone"] == "A" and r["data"][0]["dropoff_zone"] == "B"
    r = client.get("/api/trips?min_distance=2&max_fare=20").get_json()
    assert [t["trip_id"] for t in r["data"]] == [1, 4]
    r = client.get("/api/trips?hour=9").get_json()
    assert [t["trip_id"] for t in r["data"]] == [2]


def test_sort_name_is_whitelisted(client):
    assert client.get("/api/trips?sort=fare;DROP TABLE trips").status_code == 200


def test_trip_detail(client):
    d = client.get("/api/trips/1").get_json()
    assert d["payment_type"] == "Credit card" and d["pickup_borough"] == "Manhattan"
    assert client.get("/api/trips/999").status_code == 404


def test_top_routes_uses_heap_and_skips_unknown_zone(client):
    r = client.get("/api/insights/top-routes?n=5&min_trips=1").get_json()
    assert [(x["pickup_zone_id"], x["dropoff_zone_id"], x["trips"]) for x in r] == [(1, 2, 2), (2, 1, 1)]
    assert client.get("/api/insights/top-routes?min_trips=3").get_json() == []

