"""Checks the economics table (pandas) and its endpoint (in-memory SQLite, no MySQL needed)."""
import sqlite3
import sys
import types

try:
    import mysql.connector  # noqa: F401
except ImportError:  # lets the test run on a machine without the MySQL driver
    sys.modules["mysql"] = types.ModuleType("mysql")
    sys.modules["mysql.connector"] = types.ModuleType("mysql.connector")

import pandas as pd
import pytest
from flask import Flask

from backend.routes import economics
from pipeline.build_aggregates import compute_economics


def clean_rows():
    # hour 8 weekday: two card trips and one cash trip; hour 9 weekend: one card trip
    rows = [
        (8, 0, 1, 10.0, 2.0, 15.0, 5.0),    # fees = 15 - 10 - 2 = 3
        (8, 0, 1, 20.0, 4.0, 27.0, 5.0),    # fees = 3
        (8, 0, 2, 10.0, 0.0, 13.0, 4.0),    # cash: tip is 0, must not lower the tip rate
        (9, 1, 1, 10.0, 1.0, 12.0, 6.0),
    ]
    return pd.DataFrame(rows, columns=["pickup_hour", "is_weekend", "payment_type_id", "fare_amount",
                                       "tip_amount", "total_amount", "fare_per_mile"])


def test_card_tip_rate_ignores_cash_trips():
    out = compute_economics(clean_rows())
    row = out[(out.pickup_hour == 8) & (out.day_type == "weekday")].iloc[0]
    assert row.trips == 3 and row.card_trips == 2
    assert abs(row.card_tip_pct - 20.0) < 1e-9          # (2 + 4) / (10 + 20)
    assert abs(row.avg_fees - 3.0) < 1e-9


@pytest.fixture()
def client(monkeypatch):
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE econ_hour (pickup_hour INT, day_type TEXT, trips INT, avg_fare REAL, avg_fees REAL,
            avg_fare_per_mile REAL, card_trips INT, card_tip_pct REAL);
        INSERT INTO econ_hour VALUES (8,'weekday',100,15,3,5,80,18.0),(8,'weekend',50,13,3,5,40,16.0),(9,'weekday',10,12,3,6,0,NULL);
    """)

    def fake_fetch_all(sql, params=()):
        return [dict(r) for r in db.execute(sql.replace("%s", "?"), list(params)).fetchall()]

    monkeypatch.setattr(economics, "fetch_all", fake_fetch_all)
    app = Flask(__name__)
    app.register_blueprint(economics.economics_bp)
    return app.test_client()


def test_by_hour_combines_day_types(client):
    rows = client.get("/api/economics/by-hour").get_json()
    assert [r["hour"] for r in rows] == [8, 9]
    assert abs(rows[0]["avg_fare"] - (15 * 100 + 13 * 50) / 150) < 1e-9
    assert rows[1]["card_tip_pct"] is None              # no card trips in that hour


def test_by_hour_one_day_type_and_bad_value(client):
    rows = client.get("/api/economics/by-hour?day_type=weekend").get_json()
    assert len(rows) == 1 and rows[0]["card_tip_pct"] == 16.0
    assert client.get("/api/economics/by-hour?day_type=monday").status_code == 400
