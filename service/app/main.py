"""
main.py — FastAPI ingestion service (Days 6-9)

Wraps the compiled C++ anomaly detection engine (via pybind11) behind
two HTTP endpoints:

  POST /ingest      - submit one meter reading, get back whether it's anomalous
  GET  /anomalies    - see everything flagged so far

As of Days 8-9, results are persisted in PostgreSQL instead of an
in-memory list, so nothing is lost when the server restarts.
"""

from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

import smart_grid_engine as engine
import db

app = FastAPI(title="Smart Grid Anomaly Detection API")

# One detector instance, shared across all requests, so each meter's
# rolling statistics persist between calls instead of resetting every time.
detector = engine.RollingZScoreDetector(threshold=3.0, warmup_readings=5, window_size=20)


class Reading(BaseModel):
    meter_id: str
    timestamp: str
    kwh: float


class IngestResponse(BaseModel):
    meter_id: str
    kwh: float
    is_anomaly: bool
    warming_up: bool
    z_score: float
    rolling_mean: float


@app.post("/ingest", response_model=IngestResponse)
def ingest_reading(reading: Reading):
    """Feed one reading through the C++ engine, then persist it to Postgres."""
    result = detector.process(reading.meter_id, reading.kwh)

    # Every reading gets logged, anomalous or not — this is the full
    # audit trail described in the schema design.
    reading_id = db.insert_reading(
        meter_id=reading.meter_id,
        timestamp=reading.timestamp,
        kwh=reading.kwh,
        is_anomaly=result.is_anomaly,
        z_score=result.z_score,
        rolling_mean=result.rolling_mean,
    )

    if result.is_anomaly:
        db.insert_anomaly(
            reading_id=reading_id,
            meter_id=reading.meter_id,
            timestamp=reading.timestamp,
            kwh=reading.kwh,
            z_score=result.z_score,
            rolling_mean=result.rolling_mean,
        )

    return IngestResponse(
        meter_id=reading.meter_id,
        kwh=reading.kwh,
        is_anomaly=result.is_anomaly,
        warming_up=result.warming_up,
        z_score=result.z_score,
        rolling_mean=result.rolling_mean,
    )


@app.get("/anomalies")
def get_anomalies():
    """Return everything flagged as anomalous so far, read from Postgres."""
    anomalies = db.fetch_anomalies()
    return {"count": len(anomalies), "anomalies": anomalies}


@app.get("/")
def root():
    return {"message": "Smart Grid Anomaly Detection API is running. See /docs for usage."}