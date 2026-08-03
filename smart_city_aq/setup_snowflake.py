"""
setup_snowflake.py — One-time Snowflake setup
Smart City Air Quality Monitoring System — Pakistan

Creates:
  - Database : AIR_QUALITY_DB
  - Schema   : RAW      (Bronze)
  - Schema   : CLEAN    (Silver)
  - Schema   : ANALYTICS (Gold)
  - Table    : RAW.IOT_READINGS
  - Table    : RAW.OPENAQ_RAW
  - Table    : CLEAN.AQI_CLEAN
  - Table    : ANALYTICS.CITY_DAILY

Run once before running the pipeline:
    python setup_snowflake.py
"""

import os
import pathlib
import sys
import snowflake.connector
from dotenv import load_dotenv

load_dotenv(dotenv_path=pathlib.Path(__file__).parent / ".env")

ACCOUNT   = os.getenv("SNOWFLAKE_ACCOUNT")
USER      = os.getenv("SNOWFLAKE_USER")
PASSWORD  = os.getenv("SNOWFLAKE_PASSWORD")
ROLE      = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")

# All DDL statements in execution order
DDL_STEPS = [

    # ── Database ─────────────────────────────────────────────────────────
    ("Create database", """
        CREATE DATABASE IF NOT EXISTS AIR_QUALITY_DB
        COMMENT = 'Smart City Air Quality Monitoring — Pakistan'
    """),

    # ── Schemas ──────────────────────────────────────────────────────────
    ("Create RAW schema", """
        CREATE SCHEMA IF NOT EXISTS AIR_QUALITY_DB.RAW
        COMMENT = 'Bronze: raw IoT and OpenAQ data'
    """),
    ("Create CLEAN schema", """
        CREATE SCHEMA IF NOT EXISTS AIR_QUALITY_DB.CLEAN
        COMMENT = 'Silver: validated, AQI-tagged, unified data'
    """),
    ("Create ANALYTICS schema", """
        CREATE SCHEMA IF NOT EXISTS AIR_QUALITY_DB.ANALYTICS
        COMMENT = 'Gold: daily city-level aggregates'
    """),

    # ── Bronze Tables ────────────────────────────────────────────────────
    ("Create RAW.IOT_READINGS", """
        CREATE TABLE IF NOT EXISTS AIR_QUALITY_DB.RAW.IOT_READINGS (
            reading_id          VARCHAR(50),
            sensor_id           VARCHAR(20),
            city                VARCHAR(50),
            zone_type           VARCHAR(20),
            lat                 FLOAT,
            lon                 FLOAT,
            pm25                FLOAT,
            pm10                FLOAT,
            no2                 FLOAT,
            co                  FLOAT,
            o3                  FLOAT,
            so2                 FLOAT,
            aqi_value           INTEGER,
            aqi_category        VARCHAR(50),
            health_risk         VARCHAR(20),
            reading_timestamp   TIMESTAMP_NTZ,
            ingested_at         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """),
    ("Create RAW.OPENAQ_RAW", """
        CREATE TABLE IF NOT EXISTS AIR_QUALITY_DB.RAW.OPENAQ_RAW (
            location_id         INTEGER,
            location_name       VARCHAR(200),
            city                VARCHAR(100),
            parameter           VARCHAR(20),
            value               FLOAT,
            unit                VARCHAR(20),
            lat                 FLOAT,
            lon                 FLOAT,
            measured_at         TIMESTAMP_NTZ,
            aqi_value           INTEGER,
            aqi_category        VARCHAR(50),
            ingested_at         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """),

    # ── Silver Table ─────────────────────────────────────────────────────
    ("Create CLEAN.AQI_CLEAN", """
        CREATE TABLE IF NOT EXISTS AIR_QUALITY_DB.CLEAN.AQI_CLEAN (
            source              VARCHAR(10),
            source_id           VARCHAR(200),
            city                VARCHAR(100),
            zone_type           VARCHAR(30),
            lat                 FLOAT,
            lon                 FLOAT,
            pm25                FLOAT,
            pm10                FLOAT,
            no2                 FLOAT,
            co                  FLOAT,
            o3                  FLOAT,
            so2                 FLOAT,
            aqi_value           INTEGER,
            aqi_category        VARCHAR(50),
            health_risk         VARCHAR(20),
            reading_ts          TIMESTAMP_NTZ,
            reading_date        DATE,
            processed_at        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """),

    # ── Gold Table ───────────────────────────────────────────────────────
    ("Create ANALYTICS.CITY_DAILY", """
        CREATE TABLE IF NOT EXISTS AIR_QUALITY_DB.ANALYTICS.CITY_DAILY (
            city                VARCHAR(100),
            reading_date        DATE,
            avg_aqi             FLOAT,
            max_aqi             INTEGER,
            min_aqi             INTEGER,
            avg_pm25            FLOAT,
            avg_pm10            FLOAT,
            avg_no2             FLOAT,
            avg_co              FLOAT,
            avg_o3              FLOAT,
            avg_so2             FLOAT,
            dominant_risk       VARCHAR(20),
            dominant_aqi_cat    VARCHAR(50),
            reading_count       INTEGER,
            iot_count           INTEGER,
            openaq_count        INTEGER,
            lat                 FLOAT,
            lon                 FLOAT,
            aggregated_at       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """),
]


def run_setup():
    print("\n" + "="*60)
    print("  Snowflake Setup — Smart City AQI Pakistan")
    print("="*60)
    print(f"\n  Account  : {ACCOUNT}")
    print(f"  User     : {USER}")
    print(f"  Role     : {ROLE}")
    print(f"  Warehouse: {WAREHOUSE}\n")

    try:
        conn = snowflake.connector.connect(
            account=ACCOUNT,
            user=USER,
            password=PASSWORD,
            role=ROLE,
            warehouse=WAREHOUSE,
        )
        print("  🔌  Connected to Snowflake!\n")
    except Exception as e:
        print(f"  ❌  Connection failed: {e}")
        sys.exit(1)

    cur = conn.cursor()
    errors = []

    for label, sql in DDL_STEPS:
        try:
            cur.execute(sql.strip())
            print(f"  ✅  {label}")
        except Exception as e:
            print(f"  ❌  {label} — {e}")
            errors.append((label, str(e)))

    cur.close()
    conn.close()

    print("\n" + "="*60)
    if errors:
        print(f"  ⚠️   {len(errors)} error(s) occurred:")
        for lbl, err in errors:
            print(f"      - {lbl}: {err}")
    else:
        print("  🎉  All objects created successfully!")
        print("\n  Next steps:")
        print("  1. Run pipeline:    python run_pipeline.py")
        print("  2. Run dashboard:   streamlit run dashboard/app.py")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_setup()
