"""
extract.py — Extract Layer
Smart City Air Quality Monitoring System

Reads IoT CSV and OpenAQ JSON files from data/ folder.

Functions:
    extract_iot_csv(data_dir)      -> DataFrame
    extract_openaq_json(data_dir)  -> DataFrame
"""

import json
import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import DATA_DIR


def extract_iot_csv(data_dir=None) -> pd.DataFrame:
    """
    Read all iot_readings_*.csv files from data_dir and combine them.

    Returns combined DataFrame, or empty DataFrame if no files found.
    """
    data_dir = pathlib.Path(data_dir) if data_dir else DATA_DIR
    if not data_dir.exists():
        print(f"⚠️  Data dir not found: {data_dir}")
        return pd.DataFrame()

    files = sorted(data_dir.glob("iot_readings_*.csv"))
    if not files:
        print(f"⚠️  No IoT CSV files in {data_dir}")
        return pd.DataFrame()

    frames = []
    for fp in files:
        try:
            df = pd.read_csv(fp)
            frames.append(df)
            print(f"  📂  {fp.name}  ({len(df)} rows)")
        except Exception as exc:
            print(f"  ⚠️  Cannot read {fp.name}: {exc}")

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined["reading_timestamp"] = pd.to_datetime(combined["reading_timestamp"], errors="coerce")
    before = len(combined)
    combined.drop_duplicates(subset=["reading_id"], inplace=True)
    if (d := before - len(combined)):
        print(f"  🗑️   Dropped {d} duplicate IoT rows")
    print(f"✅  IoT extract: {len(combined)} rows from {len(files)} file(s)")
    return combined.reset_index(drop=True)


def extract_openaq_json(data_dir=None) -> pd.DataFrame:
    """
    Read all openaq_raw_*.json files from data_dir and combine them.

    Returns combined DataFrame, or empty DataFrame if no files found.
    """
    data_dir = pathlib.Path(data_dir) if data_dir else DATA_DIR
    if not data_dir.exists():
        print(f"⚠️  Data dir not found: {data_dir}")
        return pd.DataFrame()

    files = sorted(data_dir.glob("openaq_raw_*.json"))
    if not files:
        print(f"⚠️  No OpenAQ JSON files in {data_dir}")
        return pd.DataFrame()

    frames = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                records = json.load(fh)
            df = pd.DataFrame(records)
            frames.append(df)
            print(f"  📂  {fp.name}  ({len(df)} rows)")
        except Exception as exc:
            print(f"  ⚠️  Cannot read {fp.name}: {exc}")

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined["timestamp"] = pd.to_datetime(combined["timestamp"], utc=True, errors="coerce")
    combined["value"]     = pd.to_numeric(combined["value"], errors="coerce")
    dedup = [c for c in ["location_id", "timestamp", "parameter"] if c in combined.columns]
    before = len(combined)
    combined.drop_duplicates(subset=dedup, inplace=True)
    if (d := before - len(combined)):
        print(f"  🗑️   Dropped {d} duplicate OpenAQ rows")
    print(f"✅  OpenAQ extract: {len(combined)} rows from {len(files)} file(s)")
    return combined.reset_index(drop=True)
