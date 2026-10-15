import sqlite3
import sys
import types

try:
    import mysql.connector  # noqa: F401
except ImportError:
    sys.modules["mysql"] = types.ModuleType("mysql")
    sys.modules["mysql.connector"] = types.ModuleType("mysql.connector")

import pytest
from flask import Flask

from backend.routes import heatmap


@pytest.fixture()
def client(monkeypatch):
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE trips (pickup_dow INT, pickup_hour INT, speed_mph REAL, min_per_mile REAL);
        INSERT INTO trips VALUES (0, 8, 10.0, 6.0), (0, 8, 20.0, 3.0), (1, 9, 12.0, 5.0);
    """)

    def fake_fetch_all(sql, params=()):
        return [dict(r) for r in db.execute(sql.replace("%s", "?"), list(params)).fetchall()]

    monkeypatch.setattr(heatmap, "fetch_all", fake_fetch_all)
    heatmap.cache.clear()
    app = Flask(__name__)
    app.register_blueprint(heatmap.heatmap_bp)
    return app.test_client()


def test_heatmap_counts_trips(client):
    rows = client.get("/api/time/heatmap?metric=trips").get_json()
    assert rows[0] == {"dow": 0, "hour": 8, "value": 2.0, "trips": 2}
    assert len(rows) == 2


def test_heatmap_average_speed(client):
    rows = client.get("/api/time/heatmap?metric=speed").get_json()
    assert rows[0]["value"] == 15.0


def test_heatmap_rejects_unknown_metric(client):
    assert client.get("/api/time/heatmap?metric=bad").status_code == 400
