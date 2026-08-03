"""
data_loader.py — Dashboard data loading
Smart City Air Quality Monitoring System

Loads Gold and Silver data from Snowflake with demo fallback.
"""

import os
import pathlib
import sys

import numpy as np
import pandas as pd
import streamlit as st

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import CITIES, AQI_COLORS, HEALTH_RISK_COLORS
from dotenv import load_dotenv

load_dotenv(dotenv_path=ROOT / ".env")


def _snowflake_params() -> dict:
    return {
        "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
        "user":      os.getenv("SNOWFLAKE_USER"),
        "password":  os.getenv("SNOWFLAKE_PASSWORD"),
        "role":      os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        "database":  "AIR_QUALITY_DB",
        "login_timeout":   10,   # seconds to wait for login
        "network_timeout": 15,   # seconds for network ops
    }


def _query(sql: str) -> pd.DataFrame:
    """Run SQL against Snowflake. Returns empty DataFrame on any error."""
    try:
        import snowflake.connector
        conn = snowflake.connector.connect(**_snowflake_params())
        cur  = conn.cursor()
        cur.execute(sql)
        cols = [d[0].lower() for d in cur.description]
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return pd.DataFrame(rows, columns=cols)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_gold() -> pd.DataFrame:
    """Load ANALYTICS.CITY_DAILY. Falls back to demo data if unavailable."""
    df = _query("""
        SELECT city, reading_date, avg_aqi, max_aqi, min_aqi,
               avg_pm25, avg_pm10, avg_no2, avg_co, avg_o3, avg_so2,
               dominant_risk, dominant_aqi_cat,
               reading_count, iot_count, openaq_count, lat, lon
        FROM AIR_QUALITY_DB.ANALYTICS.CITY_DAILY
        ORDER BY reading_date DESC, city
    """)

    if not df.empty:
        df["reading_date"] = pd.to_datetime(df["reading_date"])
        for c in ["avg_aqi", "max_aqi", "min_aqi", "avg_pm25", "avg_pm10",
                  "avg_no2", "avg_co", "avg_o3", "avg_so2",
                  "reading_count", "iot_count", "openaq_count"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df

    # Snowflake unavailable — use demo data
    return _demo_gold()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_silver() -> pd.DataFrame:
    """Load CLEAN.AQI_CLEAN (max 2000 rows). Falls back to demo data."""
    df = _query("""
        SELECT source, city, zone_type, pm25, aqi_value,
               aqi_category, health_risk, reading_ts, reading_date
        FROM AIR_QUALITY_DB.CLEAN.AQI_CLEAN
        WHERE aqi_value >= 0
        ORDER BY reading_ts DESC
        LIMIT 2000
    """)

    if not df.empty:
        # reading_ts can be datetime or string depending on Snowflake driver version
        df["reading_ts"] = pd.to_datetime(df["reading_ts"], errors="coerce", utc=False)
        # strip timezone if present
        if hasattr(df["reading_ts"].dt, "tz") and df["reading_ts"].dt.tz is not None:
            df["reading_ts"] = df["reading_ts"].dt.tz_localize(None)
        df["reading_date"] = pd.to_datetime(df["reading_date"], errors="coerce")
        df["aqi_value"]    = pd.to_numeric(df["aqi_value"],     errors="coerce")
        df["pm25"]         = pd.to_numeric(df["pm25"],          errors="coerce")
        return df

    return _demo_silver()


# ---------------------------------------------------------------------------
# Demo data generators — used when Snowflake is unavailable
# ---------------------------------------------------------------------------

def _demo_gold() -> pd.DataFrame:
    rng   = np.random.default_rng(7)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=14, freq="D")
    base  = {"Karachi": 160, "Lahore": 185, "Islamabad": 90,
             "Peshawar": 145, "Multan": 135}

    def aqi_to_info(a):
        if a <= 50:  return "Good", "Low"
        if a <= 100: return "Moderate", "Moderate"
        if a <= 150: return "Unhealthy for Sensitive Groups", "Elevated"
        if a <= 200: return "Unhealthy", "High"
        if a <= 300: return "Very Unhealthy", "Very High"
        return "Hazardous", "Critical"

    rows = []
    for city, b in base.items():
        for d in dates:
            avg = float(np.clip(rng.normal(b, 28), 15, 380))
            cat, risk = aqi_to_info(avg)
            rows.append({
                "city": city, "reading_date": d,
                "avg_aqi":          round(avg, 2),
                "max_aqi":          int(np.clip(avg + rng.uniform(10, 55), avg, 500)),
                "min_aqi":          int(np.clip(avg - rng.uniform(10, 45), 0, avg)),
                "avg_pm25":         round(avg * 0.42, 4),
                "avg_pm10":         round(avg * 0.70, 4),
                "avg_no2":          round(float(rng.uniform(20, 80)), 4),
                "avg_co":           round(float(rng.uniform(0.5, 6.0)), 4),
                "avg_o3":           round(float(rng.uniform(15, 70)), 4),
                "avg_so2":          round(float(rng.uniform(5, 60)), 4),
                "dominant_risk":    risk,
                "dominant_aqi_cat": cat,
                "reading_count":    int(rng.integers(80, 200)),
                "iot_count":        int(rng.integers(40, 110)),
                "openaq_count":     int(rng.integers(10, 50)),
                "lat":              CITIES[city]["lat"],
                "lon":              CITIES[city]["lon"],
            })
    return pd.DataFrame(rows)


def _demo_silver() -> pd.DataFrame:
    rng    = np.random.default_rng(99)
    cities = list(CITIES.keys())
    zones  = ["industrial", "traffic", "residential", "park", "station"]
    dates  = pd.date_range(end=pd.Timestamp.today(), periods=3, freq="D")
    cats   = ["Good", "Moderate", "Unhealthy for Sensitive Groups",
              "Unhealthy", "Very Unhealthy", "Hazardous"]
    hmap   = {
        "Good": "Low", "Moderate": "Moderate",
        "Unhealthy for Sensitive Groups": "Elevated",
        "Unhealthy": "High", "Very Unhealthy": "Very High",
        "Hazardous": "Critical",
    }
    rows = []
    for city in cities:
        for date in dates:
            for _ in range(20):
                pm25 = float(np.clip(rng.normal(120, 60), 5, 400))
                aqi  = int(np.clip(pm25 * 1.5, 0, 500))
                cat  = cats[min(aqi // 60, 5)]
                rows.append({
                    "source":       rng.choice(["iot", "openaq"]),
                    "city":         city,
                    "zone_type":    rng.choice(zones),
                    "pm25":         round(pm25, 4),
                    "aqi_value":    aqi,
                    "aqi_category": cat,
                    "health_risk":  hmap[cat],
                    "reading_ts":   date + pd.Timedelta(hours=int(rng.integers(0, 24))),
                    "reading_date": date,
                })
    return pd.DataFrame(rows)
