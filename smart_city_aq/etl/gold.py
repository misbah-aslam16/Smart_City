"""
gold.py — Gold Layer Builder
Smart City Air Quality Monitoring System

Aggregates Silver (CLEAN.AQI_CLEAN) into daily city-level summaries
(ANALYTICS.CITY_DAILY).

Functions:
    read_silver(conn)                      -> DataFrame
    build_gold(silver_df)                  -> DataFrame
    load_gold(df, conn)                    -> int
    run_gold_pipeline(conn, silver_df)     -> DataFrame
"""

import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import DB, SILVER_SCHEMA, GOLD_SCHEMA, CITIES

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


def _dominant(series: pd.Series) -> str:
    vals = series.dropna()
    return vals.value_counts().idxmax() if not vals.empty else "Unknown"


def read_silver(conn) -> pd.DataFrame:
    """Read CLEAN.AQI_CLEAN from Snowflake."""
    sql = f"""
        SELECT source, city, zone_type, lat, lon,
               pm25, pm10, no2, co, o3, so2,
               aqi_value, aqi_category, health_risk,
               reading_ts, reading_date
        FROM {DB}.{SILVER_SCHEMA}.AQI_CLEAN
        WHERE aqi_value >= 0
        ORDER BY reading_date, city
    """
    df = _run_query(conn, sql)
    if not df.empty:
        df["reading_date"] = pd.to_datetime(df["reading_date"], errors="coerce").dt.date
        df["aqi_value"]    = pd.to_numeric(df["aqi_value"], errors="coerce").fillna(-1).astype(int)
        for col in ["pm25","pm10","no2","co","o3","so2"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        print(f"📥  Silver read   : {len(df):,} rows")
    else:
        print("⚠️  Silver empty — run silver pipeline first")
    return df


def build_gold(silver_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate Silver into one row per (city, reading_date).

    Columns: avg_aqi, max_aqi, min_aqi, avg_pm25…so2,
             dominant_risk, dominant_aqi_cat,
             reading_count, iot_count, openaq_count, lat, lon.
    """
    if silver_df.empty:
        print("⚠️  build_gold: empty input")
        return pd.DataFrame()

    df = silver_df.copy()
    for col in ["aqi_value","pm25","pm10","no2","co","o3","so2"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    records = []
    for (city, date), grp in df.groupby(["city","reading_date"]):
        cfg = CITIES.get(city, {})
        records.append({
            "city":             city,
            "reading_date":     date,
            "avg_aqi":          round(grp["aqi_value"].mean(), 2),
            "max_aqi":          int(grp["aqi_value"].max()),
            "min_aqi":          int(grp["aqi_value"].min()),
            "avg_pm25":         round(grp["pm25"].mean(), 4)  if "pm25" in grp.columns else None,
            "avg_pm10":         round(grp["pm10"].mean(), 4)  if "pm10" in grp.columns else None,
            "avg_no2":          round(grp["no2"].mean(),  4)  if "no2"  in grp.columns else None,
            "avg_co":           round(grp["co"].mean(),   4)  if "co"   in grp.columns else None,
            "avg_o3":           round(grp["o3"].mean(),   4)  if "o3"   in grp.columns else None,
            "avg_so2":          round(grp["so2"].mean(),  4)  if "so2"  in grp.columns else None,
            "dominant_risk":    _dominant(grp["health_risk"]),
            "dominant_aqi_cat": _dominant(grp["aqi_category"]),
            "reading_count":    len(grp),
            "iot_count":        int((grp["source"]=="iot").sum())     if "source" in grp.columns else 0,
            "openaq_count":     int((grp["source"]=="openaq").sum())  if "source" in grp.columns else 0,
            "lat":              cfg.get("lat") or float(grp["lat"].mean()),
            "lon":              cfg.get("lon") or float(grp["lon"].mean()),
        })

    gold = pd.DataFrame(records)
    gold["reading_date"] = pd.to_datetime(gold["reading_date"]).dt.date
    print(f"✅  Gold built     : {len(gold):,} rows "
          f"({gold['city'].nunique()} cities × {gold['reading_date'].nunique()} dates)")
    return gold.reset_index(drop=True)


def load_gold(df: pd.DataFrame, conn) -> int:
    """Load Gold DataFrame to ANALYTICS.CITY_DAILY."""
    if conn is None or df.empty:
        return 0
    upload = df.copy()
    upload["reading_date"] = upload["reading_date"].astype(str)
    upload.columns = [c.upper() for c in upload.columns]
    try:
        ok, chunks, rows, _ = write_pandas(
            conn=conn, df=upload, table_name="CITY_DAILY",
            schema=GOLD_SCHEMA, database=DB,
            auto_create_table=False, overwrite=False,
        )
        if ok:
            print(f"✅  Loaded {rows} rows → {DB}.{GOLD_SCHEMA}.CITY_DAILY")
            return rows
        print("⚠️  write_pandas failed for CITY_DAILY")
        return 0
    except Exception as exc:
        print(f"⚠️  Gold load error: {exc}")
        return 0


def run_gold_pipeline(conn, silver_df: pd.DataFrame = None) -> pd.DataFrame:
    """Read Silver (or accept pre-built) → build Gold → load Gold."""
    if silver_df is None or silver_df.empty:
        silver_df = read_silver(conn)
    gold_df = build_gold(silver_df)
    load_gold(gold_df, conn)
    return gold_df
