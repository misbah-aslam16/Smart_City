"""
silver.py — Silver Layer Builder
Smart City Air Quality Monitoring System

Reads Bronze tables, unifies IoT + OpenAQ, and writes to CLEAN.AQI_CLEAN.

Functions:
    read_bronze_iot(conn)            -> DataFrame
    read_bronze_openaq(conn)         -> DataFrame
    build_silver(iot_df, openaq_df)  -> DataFrame
    load_silver(df, conn)            -> int
    run_silver_pipeline(conn)        -> DataFrame
"""

import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import DB, BRONZE_SCHEMA, SILVER_SCHEMA
from etl.transform import calculate_aqi, _HEALTH_RISK

try:
    from snowflake.connector.pandas_tools import write_pandas
    _SF = True
except ImportError:
    _SF = False


def _run_query(conn, sql: str) -> pd.DataFrame:
    if conn is None:
        return pd.DataFrame()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0].lower() for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)
    except Exception as exc:
        print(f"⚠️  Query error: {exc}")
        return pd.DataFrame()


def _add_aqi(df: pd.DataFrame, pm25_col: str = "pm25") -> pd.DataFrame:
    if pm25_col not in df.columns:
        df["aqi_value"] = -1; df["aqi_category"] = "Unknown"; df["health_risk"] = "Unknown"
        return df
    results = df[pm25_col].apply(calculate_aqi)
    df["aqi_value"]    = [r[0] for r in results]
    df["aqi_category"] = [r[1] for r in results]
    df["health_risk"]  = df["aqi_category"].map(_HEALTH_RISK).fillna("Unknown")
    return df


# ---------------------------------------------------------------------------
# Bronze readers
# ---------------------------------------------------------------------------

def read_bronze_iot(conn) -> pd.DataFrame:
    """Read RAW.IOT_READINGS from Snowflake."""
    sql = f"""
        SELECT reading_id, sensor_id, city, zone_type, lat, lon,
               pm25, pm10, no2, co, o3, so2, reading_timestamp
        FROM {DB}.{BRONZE_SCHEMA}.IOT_READINGS
        ORDER BY reading_timestamp DESC
    """
    df = _run_query(conn, sql)
    if not df.empty:
        df["reading_timestamp"] = pd.to_datetime(df["reading_timestamp"], errors="coerce")
        print(f"📥  Bronze IoT    : {len(df):,} rows")
    else:
        print("⚠️  Bronze IoT empty — run Phase 1 first")
    return df


def read_bronze_openaq(conn) -> pd.DataFrame:
    """Read PM2.5 rows from RAW.OPENAQ_RAW from Snowflake."""
    sql = f"""
        SELECT location_id, location_name, city, value AS pm25, lat, lon, measured_at
        FROM {DB}.{BRONZE_SCHEMA}.OPENAQ_RAW
        WHERE LOWER(parameter) IN ('pm25','pm2.5') AND value IS NOT NULL
        ORDER BY measured_at DESC
    """
    df = _run_query(conn, sql)
    if not df.empty:
        df["measured_at"] = pd.to_datetime(df["measured_at"], errors="coerce")
        df["pm25"]        = pd.to_numeric(df["pm25"], errors="coerce")
        print(f"📥  Bronze OpenAQ : {len(df):,} rows")
    else:
        print("⚠️  Bronze OpenAQ empty")
    return df


# ---------------------------------------------------------------------------
# Silver builder
# ---------------------------------------------------------------------------

def build_silver(iot_df: pd.DataFrame, openaq_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge IoT + OpenAQ Bronze data into unified Silver DataFrame.

    Adds: source, source_id, reading_ts, reading_date, aqi, health_risk.
    """
    frames = []

    if not iot_df.empty:
        iot = iot_df.copy()
        iot["source"]    = "iot"
        iot["source_id"] = iot.get("reading_id", pd.Series(range(len(iot)))).astype(str)
        iot["reading_ts"] = pd.to_datetime(iot.get("reading_timestamp"), errors="coerce")
        iot = _add_aqi(iot, "pm25")
        frames.append(iot[[
            "source","source_id","city","zone_type","lat","lon",
            "pm25","pm10","no2","co","o3","so2",
            "aqi_value","aqi_category","health_risk","reading_ts",
        ]])

    if not openaq_df.empty:
        oaq = openaq_df.copy()
        # After transform_openaq, PM2.5 column is still called "value"
        if "value" in oaq.columns and "pm25" not in oaq.columns:
            oaq = oaq.rename(columns={"value": "pm25"})
        oaq["source"]    = "openaq"
        oaq["source_id"] = oaq["location_id"].astype(str) + "::" + oaq.get("measured_at", pd.Series(range(len(oaq)))).astype(str)
        ts_col = "measured_at" if "measured_at" in oaq.columns else "timestamp"
        oaq["reading_ts"] = pd.to_datetime(oaq[ts_col], utc=True, errors="coerce")
        oaq["zone_type"]  = "station"
        for col in ["pm10","no2","co","o3","so2"]:
            oaq[col] = None
        oaq = _add_aqi(oaq, "pm25")
        frames.append(oaq[[
            "source","source_id","city","zone_type","lat","lon",
            "pm25","pm10","no2","co","o3","so2",
            "aqi_value","aqi_category","health_risk","reading_ts",
        ]])

    if not frames:
        print("⚠️  build_silver: no data to build from")
        return pd.DataFrame()

    silver = pd.concat(frames, ignore_index=True)

    # Validate
    before = len(silver)
    # Force reading_ts to datetime BEFORE dropna/dt operations
    silver["reading_ts"] = pd.to_datetime(silver["reading_ts"], errors="coerce", utc=False)
    silver.dropna(subset=["city","reading_ts"], inplace=True)
    if (d := before - len(silver)):
        print(f"  🗑️   Silver: dropped {d} rows with null city/ts")

    # Strip timezone for Snowflake TIMESTAMP_NTZ
    if silver["reading_ts"].dt.tz is not None:
        silver["reading_ts"] = silver["reading_ts"].dt.tz_convert("UTC").dt.tz_localize(None)

    # reading_date column (after tz strip)
    silver["reading_date"] = silver["reading_ts"].dt.date

    # Dedup
    before = len(silver)
    silver.drop_duplicates(subset=["source","source_id"], keep="first", inplace=True)
    if (d := before - len(silver)):
        print(f"  🗑️   Silver: dropped {d} duplicates")

    silver["aqi_value"] = silver["aqi_value"].fillna(-1).astype(int)

    iot_n = (silver["source"] == "iot").sum()
    oaq_n = (silver["source"] == "openaq").sum()
    print(f"✅  Silver built   : {len(silver):,} rows ({iot_n:,} IoT + {oaq_n:,} OpenAQ)")
    return silver.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Silver loader
# ---------------------------------------------------------------------------

def load_silver(df: pd.DataFrame, conn) -> int:
    """Load Silver DataFrame to CLEAN.AQI_CLEAN."""
    if conn is None or df.empty:
        return 0
    upload = df.copy()
    upload.columns = [c.upper() for c in upload.columns]
    if "READING_DATE" in upload.columns:
        upload["READING_DATE"] = upload["READING_DATE"].astype(str)
    try:
        ok, chunks, rows, _ = write_pandas(
            conn=conn, df=upload, table_name="AQI_CLEAN",
            schema=SILVER_SCHEMA, database=DB,
            auto_create_table=False, overwrite=False,
        )
        if ok:
            print(f"✅  Loaded {rows} rows → {DB}.{SILVER_SCHEMA}.AQI_CLEAN")
            return rows
        print("⚠️  write_pandas failed for AQI_CLEAN")
        return 0
    except Exception as exc:
        print(f"⚠️  Silver load error: {exc}")
        return 0


def run_silver_pipeline(conn) -> pd.DataFrame:
    """Read Bronze → build Silver → load Silver. Returns Silver DataFrame."""
    iot_df    = read_bronze_iot(conn)
    openaq_df = read_bronze_openaq(conn)
    silver_df = build_silver(iot_df, openaq_df)
    load_silver(silver_df, conn)
    return silver_df
