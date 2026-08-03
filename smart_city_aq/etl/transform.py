"""
transform.py — Transform Layer (Bronze → Silver-ready)
Smart City Air Quality Monitoring System

Cleans raw DataFrames, computes US-EPA AQI from PM2.5,
assigns health-risk labels, and deduplicates.

Functions:
    calculate_aqi(pm25)   -> (aqi_value, aqi_category)
    transform_iot(df)     -> cleaned IoT DataFrame
    transform_openaq(df)  -> cleaned OpenAQ DataFrame
"""

import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# US EPA PM2.5 breakpoints: (c_lo, c_hi, aqi_lo, aqi_hi, category)
_BREAKPOINTS = [
    (0.0,   12.0,   0,   50, "Good"),
    (12.1,  35.4,  51,  100, "Moderate"),
    (35.5,  55.4, 101,  150, "Unhealthy for Sensitive Groups"),
    (55.5, 150.4, 151,  200, "Unhealthy"),
    (150.5, 250.4, 201, 300, "Very Unhealthy"),
    (250.5, 500.0, 301, 500, "Hazardous"),
]

_HEALTH_RISK = {
    "Good":                             "Low",
    "Moderate":                         "Moderate",
    "Unhealthy for Sensitive Groups":   "Elevated",
    "Unhealthy":                        "High",
    "Very Unhealthy":                   "Very High",
    "Hazardous":                        "Critical",
}


def calculate_aqi(pm25: float) -> tuple:
    """
    Compute US-EPA AQI value and category from a PM2.5 concentration.

    Returns:
        (aqi_value: int, aqi_category: str)
    """
    if pd.isna(pm25) or pm25 < 0:
        return (-1, "Unknown")
    pm25 = min(pm25, 500.0)
    for c_lo, c_hi, a_lo, a_hi, cat in _BREAKPOINTS:
        if c_lo <= pm25 <= c_hi:
            aqi = ((a_hi - a_lo) / (c_hi - c_lo)) * (pm25 - c_lo) + a_lo
            return (int(round(aqi)), cat)
    return (500, "Hazardous")


def _add_aqi(df: pd.DataFrame, pm25_col: str = "pm25") -> pd.DataFrame:
    """Add aqi_value, aqi_category, health_risk columns."""
    if pm25_col not in df.columns:
        df["aqi_value"] = -1
        df["aqi_category"] = "Unknown"
        df["health_risk"]  = "Unknown"
        return df
    results = df[pm25_col].apply(calculate_aqi)
    df["aqi_value"]    = [r[0] for r in results]
    df["aqi_category"] = [r[1] for r in results]
    df["health_risk"]  = df["aqi_category"].map(_HEALTH_RISK).fillna("Unknown")
    return df


def transform_iot(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean raw IoT DataFrame:
      1. Drop rows missing sensor_id / reading_timestamp
      2. Clip pollutant values to physical ranges
      3. Add aqi_value, aqi_category, health_risk
      4. Deduplicate on reading_id
    """
    if df.empty:
        print("⚠️  transform_iot: empty input")
        return pd.DataFrame()

    df = df.copy()
    before = len(df)
    df.dropna(subset=["sensor_id", "reading_timestamp"], inplace=True)
    if (d := before - len(df)):
        print(f"  🗑️   transform_iot: dropped {d} rows with nulls")

    # Clip to plausible ranges
    clips = {"pm25": (0,999), "pm10": (0,999), "no2": (0,500),
             "co": (0,50), "o3": (0,500), "so2": (0,500)}
    for col, (lo, hi) in clips.items():
        if col in df.columns:
            df[col] = df[col].clip(lo, hi)

    df = _add_aqi(df, "pm25")

    if "reading_id" in df.columns:
        before = len(df)
        df.drop_duplicates(subset=["reading_id"], keep="first", inplace=True)
        if (d := before - len(df)):
            print(f"  🗑️   transform_iot: dropped {d} duplicate reading_ids")

    df["reading_timestamp"] = pd.to_datetime(df["reading_timestamp"], errors="coerce")
    df["aqi_value"]         = df["aqi_value"].astype(int)
    print(f"✅  transform_iot: {len(df)} rows, AQI {df['aqi_value'].min()}–{df['aqi_value'].max()}")
    return df.reset_index(drop=True)


def transform_openaq(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean raw OpenAQ DataFrame:
      1. Drop rows missing value / timestamp
      2. Filter PM2.5 only
      3. Clip values
      4. Add aqi_value, aqi_category
      5. Rename timestamp → measured_at
      6. Deduplicate
    """
    if df.empty:
        print("⚠️  transform_openaq: empty input")
        return pd.DataFrame()

    df = df.copy()
    before = len(df)
    df.dropna(subset=["value", "timestamp"], inplace=True)
    if (d := before - len(df)):
        print(f"  🗑️   transform_openaq: dropped {d} rows with nulls")

    if "parameter" in df.columns:
        df = df[df["parameter"].str.lower().isin(["pm25", "pm2.5"])].copy()

    if df.empty:
        print("⚠️  transform_openaq: no PM2.5 rows")
        return pd.DataFrame()

    df["value"] = df["value"].clip(0, 999)
    df = _add_aqi(df, "value")
    df.rename(columns={"timestamp": "measured_at"}, inplace=True)

    dedup = [c for c in ["location_id", "measured_at", "parameter"] if c in df.columns]
    before = len(df)
    df.drop_duplicates(subset=dedup, keep="first", inplace=True)
    if (d := before - len(df)):
        print(f"  🗑️   transform_openaq: dropped {d} duplicates")

    df["aqi_value"] = df["aqi_value"].astype(int)
    print(f"✅  transform_openaq: {len(df)} PM2.5 rows, AQI {df['aqi_value'].min()}–{df['aqi_value'].max()}")
    return df.reset_index(drop=True)


# CLI smoke-test
if __name__ == "__main__":
    cases = [(5, "Good"), (20, "Moderate"), (45, "Unhealthy for Sensitive Groups"),
             (100, "Unhealthy"), (200, "Very Unhealthy"), (300, "Hazardous")]
    print("\n── AQI Smoke-Test ──")
    for pm25, expected in cases:
        val, cat = calculate_aqi(pm25)
        ok = "✅" if cat == expected else "❌"
        print(f"  {ok}  PM2.5={pm25:5.1f} → AQI={val:4d} [{cat}]")
