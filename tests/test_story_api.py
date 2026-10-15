"""Checks the story endpoints against a tiny in-memory SQLite database (no MySQL needed).
The SQL used by the endpoints is plain SQL, so SQLite runs it the same way as MySQL."""
import sqlite3
import sys
import types

try:
    import mysql.connector  # noqa: F401
except ImportError:  # lets the test run on a machine without the MySQL driver
    sys.modules["mysql"] = types.ModuleType("mysql")
    sys.modules["mysql.connector"] = types.ModuleType("mysql.connector")

import pytest
from flask import Flask

from backend.routes import story


@pytest.fixture()
def client(monkeypatch):
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE zones (location_id INT, zone TEXT, borough TEXT, is_mappable INT);
        CREATE TABLE zone_hour_stats (pu_location_id INT, pickup_hour INT, day_type TEXT, trips INT,
            median_min_per_mile REAL, median_speed_mph REAL, median_fare_per_min REAL, is_reliable INT);
        CREATE TABLE hour_stats (pickup_hour INT, day_type TEXT, trips INT, median_min_per_mile REAL,
            median_speed_mph REAL, median_fare_per_min REAL, median_fare_per_mile REAL);
        INSERT INTO zones VALUES (1,'A','Manhattan',1),(2,'B','Queens',1),(3,'C','Bronx',1),(264,'Unknown','N/A',0),(4,'Rare','Bronx',1);
        INSERT INTO zone_hour_stats VALUES
          (1,8,'weekday',100,9.0,6.0,0.8,1),(2,8,'weekday',100,5.0,12.0,1.0,1),(3,8,'weekday',100,7.0,8.0,0.9,1),
          (264,8,'weekday',500,20.0,3.0,0.5,1),(4,8,'weekday',5,30.0,2.0,0.4,0);
        INSERT INTO hour_stats VALUES (8,'weekday',305,7.0,8.0,0.9,6.0),(4,'weekday',50,3.5,17.0,1.2,4.0);
    """)

    def fake_fetch_all(sql, params=()):
        return [dict(r) for r in db.execute(sql.replace("%s", "?"), list(params)).fetchall()]

    monkeypatch.setattr(story, "fetch_all", fake_fetch_all)
    app = Flask(__name__)
    app.register_blueprint(story.story_bp)
    return app.test_client()


def test_slowest_zones_ranked_by_heap_and_filtered(client):
    data = client.get("/api/story/slowest-zones?n=3&hour_from=8&hour_to=8").get_json()
    assert [z["location_id"] for z in data] == [1, 3, 2]        # slowest first: 9.0, 7.0, 5.0 min per mile
    ids = {z["location_id"] for z in data}
    assert 264 not in ids and 4 not in ids                      # unknown zone and a 5-trip zone are never ranked


def test_zone_hour_hides_unknown_zone(client):
    data = client.get("/api/story/zone-hour?hour=8&day_type=weekday").get_json()
    assert 264 not in {z["location_id"] for z in data}
    assert {z["location_id"]: z["is_reliable"] for z in data}[4] == 0   # kept, but marked unreliable


def test_hour_profile_and_validation(client):
    rows = client.get("/api/story/hour-profile?day_type=weekday").get_json()
    assert [r["hour"] for r in rows] == [4, 8]
    assert client.get("/api/story/hour-profile?day_type=monday").status_code == 400
    assert client.get("/api/story/zone-hour").status_code == 400
    assert client.get("/api/story/slowest-zones?hour_from=9&hour_to=3").status_code == 400
