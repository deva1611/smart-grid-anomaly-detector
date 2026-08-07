"""
db.py — PostgreSQL connection handling.

Centralizes how the FastAPI service talks to the database. Connection
details are loaded from environment variables (via a local .env file,
which is never committed to git) rather than hardcoded, so real
credentials never end up in version control.
"""

import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

# Loads variables from a .env file (in the project root) into the
# environment, if one exists. In production this would typically be
# skipped in favor of variables set directly by the hosting platform.
load_dotenv()

DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": os.environ.get("POSTGRES_PORT", "5432"),
    "dbname": os.environ.get("POSTGRES_DB", "smart_grid"),
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD"),
}


def get_connection():
    """Open a new database connection. Called per-request for simplicity."""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


def insert_reading(meter_id: str, timestamp: str, kwh: float,
                    is_anomaly: bool, z_score: float, rolling_mean: float) -> int:
    """Insert one reading and return its new row id."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO readings (meter_id, timestamp, kwh, is_anomaly, z_score, rolling_mean)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (meter_id, timestamp, kwh, is_anomaly, z_score, rolling_mean),
            )
            reading_id = cur.fetchone()["id"]
        conn.commit()
        return reading_id
    finally:
        conn.close()


def insert_anomaly(reading_id: int, meter_id: str, timestamp: str,
                    kwh: float, z_score: float, rolling_mean: float) -> None:
    """Record a flagged anomaly, linked back to its reading."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO anomalies (reading_id, meter_id, timestamp, kwh, z_score, rolling_mean)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (reading_id, meter_id, timestamp, kwh, z_score, rolling_mean),
            )
        conn.commit()
    finally:
        conn.close()


def fetch_anomalies() -> list[dict]:
    """Return all recorded anomalies, most recent first."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM anomalies ORDER BY detected_at DESC")
            return cur.fetchall()
    finally:
        conn.close()