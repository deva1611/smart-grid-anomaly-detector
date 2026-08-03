"""
main.py — FastAPI ingestion service (Days 6-7)

Wraps the compiled C++ anomaly detection engine (via pybind11) behind
two HTTP endpoints:

  POST /ingest     - submit one meter reading, get back whether it's anomalous
  GET  /anomalies   - see everything flagged so far

Results are held in memory for now — Days 8-9 will move this to
PostgreSQL so nothing is lost on restart.
"""

from datetime import datetime
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

import smart_grid_engine as engine

app = FastAPI(title="Smart Grid Anomaly Detection API")

# One detector instance, shared across all requests, so each meter's
# rolling statistics persist between calls instead of resetting every time.
detector = engine.RollingZScoreDetector(threshold=3.0, warmup_readings=5, window_size=20)

# In-memory store of anomalies seen so far. Replaced by a real database
# in Days 8-9 — this is just enough to prove the API works end-to-end.
anomaly_log: List[dict] = []


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
    """Feed one reading through the C++ engine and record it if anomalous."""
    result = detector.process(reading.meter_id, reading.kwh)

    if result.is_anomaly:
        anomaly_log.append({
            "meter_id": reading.meter_id,
            "timestamp": reading.timestamp,
            "kwh": reading.kwh,
            "z_score": result.z_score,
            "rolling_mean": result.rolling_mean,
            "detected_at": datetime.utcnow().isoformat(),
        })

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
    """Return everything flagged as anomalous so far."""
    return {"count": len(anomaly_log), "anomalies": anomaly_log}


@app.get("/")
def root():
    return {"message": "Smart Grid Anomaly Detection API is running. See /docs for usage."}