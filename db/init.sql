-- db/init.sql
-- Schema for the smart grid anomaly detection system.

-- Every reading ingested through the API, whether normal or anomalous.
-- This is the full audit trail of everything the system has seen.
CREATE TABLE IF NOT EXISTS readings (
    id SERIAL PRIMARY KEY,
    meter_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    kwh DOUBLE PRECISION NOT NULL,
    is_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    z_score DOUBLE PRECISION,
    rolling_mean DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A focused table of just the flagged anomalies, so /anomalies queries
-- don't have to scan and filter the entire readings table every time.
CREATE TABLE IF NOT EXISTS anomalies (
    id SERIAL PRIMARY KEY,
    reading_id INTEGER NOT NULL REFERENCES readings(id),
    meter_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    kwh DOUBLE PRECISION NOT NULL,
    z_score DOUBLE PRECISION,
    rolling_mean DOUBLE PRECISION,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes: queries in this system almost always filter by meter_id
-- and/or a time range (e.g. "show me MTR-0001's readings from today"),
-- so these are the two columns worth indexing.
CREATE INDEX IF NOT EXISTS idx_readings_meter_id ON readings(meter_id);
CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings(timestamp);
CREATE INDEX IF NOT EXISTS idx_anomalies_meter_id ON anomalies(meter_id);
CREATE INDEX IF NOT EXISTS idx_anomalies_timestamp ON anomalies(timestamp);