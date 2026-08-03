"""
load.py — Snowflake Loader (Bronze layer)
Smart City Air Quality Monitoring System

Loads transformed DataFrames to RAW.IOT_READINGS and RAW.OPENAQ_RAW.

Functions:
    get_connection()              -> connection | None
    load_iot_readings(df, conn)   -> int (rows)
    load_openaq_raw(df, conn)     -> int (rows)
"""

import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import SNOWFLAKE_CONFIG, DB, BRONZE_SCHEMA

try:
    import snowflake.connector
    from snowflake.connector.pandas_tools import write_pandas
    _SF = True
except ImportError:
    _SF = False
    print("⚠️  snowflake-connector-python not installed.")

_IOT_COLS = [
    "reading_id", "sensor_id", "city", "zone_type", "lat", "lon",
    "pm25", "pm10", "no2", "co", "o3", "so2",
    "aqi_value", "aqi_category", "health_risk", "reading_timestamp",
]

_OPENAQ_COLS = [
    "location_id", "location_name", "city", "parameter",
    "value", "unit", "lat", "lon", "measured_at", "aqi_value", "aqi_category",
]


def get_connection():
    """Return Snowflake connection (with retry) or None."""
    if not _SF:
        return None

    # Add timeouts + retry to handle warehouse auto-suspend
    cfg = {**SNOWFLAKE_CONFIG,
           "login_timeout": 30,
           "network_timeout": 30}

    for attempt in range(1, 4):   # 3 attempts
        try:
            conn = snowflake.connector.connect(**cfg)
            # Resume warehouse explicitly in case it was suspended
            try:
                wh = SNOWFLAKE_CONFIG.get("warehouse", "")
                if wh:
                    conn.cursor().execute(f"ALTER WAREHOUSE {wh} RESUME IF SUSPENDED")
            except Exception:
                pass
            print(f"🔌  Snowflake connected — {SNOWFLAKE_CONFIG['account']}")
            return conn
        except Exception as exc:
            print(f"  ⚠️  Snowflake attempt {attempt}/3 failed: {exc}")
            if attempt < 3:
                import time; time.sleep(3)
    print("⚠️  Snowflake connection failed after 3 attempts.")
    return None


def _upload(conn, df: pd.DataFrame, cols: list, table: str) -> int:
    """Subset, uppercase columns, bulk-load via write_pandas."""
    if conn is None or df.empty:
        return 0
    upload = df.copy()
    for c in cols:
        if c not in upload.columns:
            upload[c] = None
    upload = upload[cols].copy()
    upload.columns = [c.upper() for c in upload.columns]
    try:
        ok, chunks, rows, _ = write_pandas(
            conn=conn, df=upload, table_name=table,
            schema=BRONZE_SCHEMA, database=DB,
            auto_create_table=False, overwrite=False,
        )
        if ok:
            print(f"✅  Loaded {rows} rows → {DB}.{BRONZE_SCHEMA}.{table}")
            return rows
        print(f"⚠️  write_pandas failed for {table}")
        return 0
    except Exception as exc:
        print(f"⚠️  Load error {table}: {exc}")
        return 0


def load_iot_readings(df: pd.DataFrame, conn) -> int:
    """Load IoT DataFrame to RAW.IOT_READINGS."""
    upload = df.copy()
    if "reading_timestamp" in upload.columns:
        upload["reading_timestamp"] = (
            pd.to_datetime(upload["reading_timestamp"], errors="coerce")
            .dt.tz_localize(None)
        )
    return _upload(conn, upload, _IOT_COLS, "IOT_READINGS")


def load_openaq_raw(df: pd.DataFrame, conn) -> int:
    """Load OpenAQ DataFrame to RAW.OPENAQ_RAW."""
    upload = df.copy()
    if "measured_at" in upload.columns:
        ts = pd.to_datetime(upload["measured_at"], errors="coerce", utc=True)
        upload["measured_at"] = ts.dt.tz_localize(None)
    return _upload(conn, upload, _OPENAQ_COLS, "OPENAQ_RAW")
