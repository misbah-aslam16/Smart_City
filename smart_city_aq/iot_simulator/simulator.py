"""
simulator.py — IoT Sensor Simulator
Smart City Air Quality Monitoring System — Pakistan

Simulates PM2.5, PM10, NO2, CO, O3, SO2 readings for 10 virtual sensors
across Karachi, Lahore, Islamabad, Peshawar, Multan.

Usage:
    python iot_simulator/simulator.py          # 100 readings → data/
    python iot_simulator/simulator.py --n 500
"""

import argparse
import pathlib
import sys
import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import DATA_DIR, DEFAULT_BATCH_SIZE
from iot_simulator.sensor_config import SENSORS, ZONE_POLLUTION_RANGES

DATA_DIR.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(seed=42)


def _noisy(value: float, pct: float = 0.05) -> float:
    """Add ±pct Gaussian noise and clip to non-negative."""
    return max(0.0, value + RNG.normal(0, abs(value) * pct))


def _make_reading(sensor: dict, ts: datetime) -> dict:
    zone   = sensor["zone_type"]
    ranges = ZONE_POLLUTION_RANGES[zone]

    def sample(key):
        lo, hi = ranges[key]
        return round(_noisy(RNG.uniform(lo, hi)), 4)

    return {
        "reading_id":        str(uuid.uuid4()),
        "sensor_id":         sensor["sensor_id"],
        "city":              sensor["city"],
        "zone_type":         zone,
        "lat":               sensor["lat"],
        "lon":               sensor["lon"],
        "pm25":              sample("pm25"),
        "pm10":              sample("pm10"),
        "no2":               sample("no2"),
        "co":                sample("co"),
        "o3":                sample("o3"),
        "so2":               sample("so2"),
        "reading_timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
    }


def generate_batch(n_readings: int = DEFAULT_BATCH_SIZE) -> pd.DataFrame:
    """
    Generate n_readings rows spread across all 10 sensors,
    with timestamps spread over the past 24 hours.

    Returns:
        pandas DataFrame with one row per reading.
    """
    now     = datetime.now(timezone.utc).replace(tzinfo=None)
    records = []
    for i in range(n_readings):
        sensor = SENSORS[i % len(SENSORS)]
        ts     = now - timedelta(seconds=int(RNG.uniform(0, 86_400)))
        records.append(_make_reading(sensor, ts))

    df = pd.DataFrame(records)
    df["reading_timestamp"] = pd.to_datetime(df["reading_timestamp"])
    print(f"✅  Simulated {len(df)} readings — "
          f"{df['city'].nunique()} cities, {df['sensor_id'].nunique()} sensors")
    return df


def save_to_csv(df: pd.DataFrame, filepath=None) -> pathlib.Path:
    """Save DataFrame to timestamped CSV in data/."""
    if filepath is None:
        ts   = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filepath = DATA_DIR / f"iot_readings_{ts}.csv"
    filepath = pathlib.Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"💾  IoT CSV saved → {filepath}  ({len(df)} rows)")
    return filepath


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()
    df  = generate_batch(args.n)
    out = save_to_csv(df)
    print(df.head().to_string(index=False))
