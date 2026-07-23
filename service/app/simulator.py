"""
simulator.py — Smart Meter Data Simulator (Day 1)

Generates a real-time stream of smart meter readings and prints each
reading to the console as JSON. Occasionally injects realistic anomalies
(spikes, flatlines, negative values) so the downstream anomaly detector
has something to catch later in the project.
"""

import json
import random
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

METER_IDS = [f"MTR-{i:04d}" for i in range(1, 6)]   # 5 simulated meters
NORMAL_MEAN_KWH = 2.5        # typical household draw per interval
NORMAL_STD_KWH = 0.4         # normal fluctuation
ANOMALY_PROBABILITY = 0.08   # ~8% chance a given reading is anomalous
SEND_INTERVAL_SECONDS = 1.0  # how often we emit a reading


@dataclass
class Reading:
    meter_id: str
    timestamp: str
    kwh: float
    is_anomaly: bool  # kept for our own debugging; the real engine won't see this


# ---------------------------------------------------------------------------
# State: tracks whether a meter is "stuck" in a flatline right now
# ---------------------------------------------------------------------------

flatline_state = {meter_id: {"active": False, "value": None, "remaining": 0}
                   for meter_id in METER_IDS}


def _current_timestamp() -> str:
    """Return an ISO-8601 timestamp in UTC, e.g. 2026-07-24T14:03:11.123456+00:00"""
    return datetime.now(timezone.utc).isoformat()


def _generate_normal_reading() -> float:
    """A normal reading: mean usage plus small random noise."""
    return round(random.gauss(NORMAL_MEAN_KWH, NORMAL_STD_KWH), 3)


def _inject_spike(value: float) -> float:
    """Simulate a sudden usage spike — e.g. an appliance surge or fault."""
    multiplier = random.uniform(4, 10)
    return round(value * multiplier, 3)


def _inject_negative(value: float) -> float:
    """Simulate a faulty meter reporting impossible negative consumption."""
    return round(-abs(value) * random.uniform(0.5, 2), 3)


def _maybe_start_or_continue_flatline(meter_id: str, value: float):
    """
    Flatlines are different from spikes/negatives: they persist across
    several consecutive readings (a stuck sensor repeating the same value),
    so we track state per meter instead of deciding fresh each call.
    Returns the flatlined value, or None if no flatline is active.
    """
    state = flatline_state[meter_id]

    if state["active"]:
        state["remaining"] -= 1
        if state["remaining"] <= 0:
            state["active"] = False
        return state["value"]

    # Small independent chance to start a new flatline on this meter
    if random.random() < 0.02:
        state["active"] = True
        state["value"] = round(value, 3)
        state["remaining"] = random.randint(3, 6)  # stuck for 3-6 readings
        return state["value"]

    return None


def generate_reading(meter_id: str) -> Reading:
    """Build one reading for a given meter, occasionally corrupting it."""
    base_value = _generate_normal_reading()
    is_anomaly = False

    # Flatline check first, since it can override several readings in a row
    flatlined_value = _maybe_start_or_continue_flatline(meter_id, base_value)
    if flatlined_value is not None:
        return Reading(meter_id, _current_timestamp(), flatlined_value, True)

    # Otherwise, roll the dice for a one-off spike or negative-value anomaly
    if random.random() < ANOMALY_PROBABILITY:
        is_anomaly = True
        if random.random() < 0.5:
            base_value = _inject_spike(base_value)
        else:
            base_value = _inject_negative(base_value)

    return Reading(meter_id, _current_timestamp(), base_value, is_anomaly)


def run_simulation(interval_seconds: float = SEND_INTERVAL_SECONDS) -> None:
    """Continuously emit one reading per meter, per interval, forever."""
    print(f"Starting smart meter simulation for {len(METER_IDS)} meters "
          f"(Ctrl+C to stop)...\n")
    try:
        while True:
            for meter_id in METER_IDS:
                reading = generate_reading(meter_id)
                payload = {
                    "meter_id": reading.meter_id,
                    "timestamp": reading.timestamp,
                    "kwh": reading.kwh,
                }
                flag = "  <-- ANOMALY" if reading.is_anomaly else ""
                print(json.dumps(payload) + flag)
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nSimulation stopped.")


if __name__ == "__main__":
    run_simulation()