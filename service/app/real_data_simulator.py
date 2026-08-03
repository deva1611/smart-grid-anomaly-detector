"""
real_data_simulator.py — Real Smart Meter Data Replay

Instead of purely synthetic Gaussian noise (see simulator.py), this script
streams REAL half-hourly household electricity readings from UK Power
Networks' "Low Carbon London" dataset (2011-2014), replaying them as a
live-feeling stream. Synthetic anomalies (spikes, flatlines, negative
values) are still injected on top, since real anomalies in this dataset
are rare, unlabeled, and not something we can reliably demo against.

Output shape matches simulator.py exactly: meter_id, timestamp, kwh —
so this can be dropped into the same ingestion pipeline without any
changes downstream.
"""

import json
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "block_0.csv"
NUM_METERS = 5          # how many real households to replay simultaneously
ANOMALY_PROBABILITY = 0.08
SEND_INTERVAL_SECONDS = 1.0


@dataclass
class Reading:
    meter_id: str
    timestamp: str
    kwh: float
    is_anomaly: bool


# ---------------------------------------------------------------------------
# Load and clean the real dataset
# ---------------------------------------------------------------------------

def load_household_series(num_meters: int) -> dict[str, list[float]]:
    """
    Read block_0.csv and return {household_id: [ordered real kwh readings]}
    for a handful of real households, cleaned and time-sorted.
    """
    df = pd.read_csv(DATA_PATH)

    # The energy column arrives as strings like ' 0.143 ' (extra whitespace),
    # and this dataset is known to contain literal "Null" for some missing
    # readings — errors='coerce' turns anything unparseable into NaN so we
    # can drop it instead of crashing.
    df["energy(kWh/hh)"] = pd.to_numeric(
        df["energy(kWh/hh)"].astype(str).str.strip(), errors="coerce"
    )
    df = df.dropna(subset=["energy(kWh/hh)"])

    df["tstp"] = pd.to_datetime(df["tstp"])
    df = df.sort_values(["LCLid", "tstp"])

    chosen_households = df["LCLid"].unique()[:num_meters]

    series = {}
    for household_id in chosen_households:
        household_readings = df.loc[df["LCLid"] == household_id, "energy(kWh/hh)"].tolist()
        series[household_id] = household_readings

    return series


# ---------------------------------------------------------------------------
# Anomaly injection (same approach as simulator.py)
# ---------------------------------------------------------------------------

flatline_state: dict[str, dict] = {}


def _current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _inject_spike(value: float) -> float:
    multiplier = random.uniform(4, 10)
    # Real readings are sometimes 0 (e.g. overnight); guard against a
    # spike-of-zero being a no-op by falling back to a small base value.
    base = value if value > 0.01 else 0.5
    return round(base * multiplier, 3)


def _inject_negative(value: float) -> float:
    base = value if value > 0.01 else 0.5
    return round(-abs(base) * random.uniform(0.5, 2), 3)


def _maybe_start_or_continue_flatline(meter_id: str, value: float):
    state = flatline_state.setdefault(meter_id, {"active": False, "value": None, "remaining": 0})

    if state["active"]:
        state["remaining"] -= 1
        if state["remaining"] <= 0:
            state["active"] = False
        return state["value"]

    if random.random() < 0.02:
        state["active"] = True
        state["value"] = round(value, 3)
        state["remaining"] = random.randint(3, 6)
        return state["value"]

    return None


def build_reading(meter_id: str, real_value: float) -> Reading:
    """Take a real historical reading and decide whether to corrupt it."""
    is_anomaly = False
    value = real_value

    flatlined_value = _maybe_start_or_continue_flatline(meter_id, real_value)
    if flatlined_value is not None:
        return Reading(meter_id, _current_timestamp(), flatlined_value, True)

    if random.random() < ANOMALY_PROBABILITY:
        is_anomaly = True
        if random.random() < 0.5:
            value = _inject_spike(real_value)
        else:
            value = _inject_negative(real_value)

    return Reading(meter_id, _current_timestamp(), round(value, 3), is_anomaly)


# ---------------------------------------------------------------------------
# Main replay loop
# ---------------------------------------------------------------------------

def run_replay(interval_seconds: float = SEND_INTERVAL_SECONDS) -> None:
    print(f"Loading real household data from {DATA_PATH} ...")
    series = load_household_series(NUM_METERS)

    meter_ids = list(series.keys())
    print(f"Replaying {len(meter_ids)} real households: {meter_ids}")
    print("(Ctrl+C to stop)\n")

    # Track each household's position in its own historical sequence,
    # looping back to the start once we run out of real readings.
    positions = {meter_id: 0 for meter_id in meter_ids}

    try:
        while True:
            for meter_id in meter_ids:
                household_series = series[meter_id]
                i = positions[meter_id]
                real_value = household_series[i % len(household_series)]
                positions[meter_id] += 1

                reading = build_reading(meter_id, real_value)
                payload = {
                    "meter_id": reading.meter_id,
                    "timestamp": reading.timestamp,
                    "kwh": reading.kwh,
                }
                flag = "  <-- ANOMALY" if reading.is_anomaly else ""
                print(json.dumps(payload) + flag)
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nReplay stopped.")


if __name__ == "__main__":
    run_replay()