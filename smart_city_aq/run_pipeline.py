"""
run_pipeline.py — Full Pipeline Orchestrator
Smart City Air Quality Monitoring System — Pakistan

Runs ALL 5 steps end-to-end:
  Step 1 : IoT Simulator      → data/iot_readings_*.csv
  Step 2 : OpenAQ Fetcher     → data/openaq_raw_*.json
  Step 3 : Extract CSV + JSON
  Step 4 : Transform (AQI, dedup, clean)
  Step 5 : Load Bronze → Snowflake (RAW.IOT_READINGS + RAW.OPENAQ_RAW)
  Step 6 : Build Silver        → CLEAN.AQI_CLEAN
  Step 7 : Build Gold          → ANALYTICS.CITY_DAILY

Usage:
    python run_pipeline.py                     # full run
    python run_pipeline.py --n 500             # 500 IoT readings
    python run_pipeline.py --skip-snowflake    # no Snowflake, local files only
    python run_pipeline.py --dashboard         # launch Streamlit after pipeline
"""

import argparse
import pathlib
import sys
import time
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))

from config import DATA_DIR, DEFAULT_BATCH_SIZE

DATA_DIR.mkdir(parents=True, exist_ok=True)


def sep(title): print(f"\n{'═'*64}\n  {title}\n{'═'*64}\n")
def step(n, label): print(f"\n{'─'*64}\n  Step {n}: {label}\n{'─'*64}")


def run(n_readings: int = DEFAULT_BATCH_SIZE,
        skip_snowflake: bool = False,
        launch_dashboard: bool = False) -> dict:

    t0 = time.perf_counter()
    sep("🌆 Smart City Air Quality Monitoring — Full Pipeline")
    print(f"  🕐  Started   : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"  📊  IoT batch : {n_readings}")
    print(f"  ❄️   Snowflake : {'SKIPPED' if skip_snowflake else 'ENABLED'}")

    # ── Step 1 — IoT Simulator ────────────────────────────────────────────
    step(1, "🤖  IoT Sensor Simulator")
    from iot_simulator.simulator import generate_batch, save_to_csv
    iot_raw = generate_batch(n_readings)
    save_to_csv(iot_raw)

    # ── Step 2 — OpenAQ Fetcher ───────────────────────────────────────────
    step(2, "🌐  OpenAQ V3 Fetcher")
    from openaq_fetcher.fetcher import fetch_pakistan_data, save_to_json
    openaq_raw = fetch_pakistan_data()
    if not openaq_raw.empty:
        save_to_json(openaq_raw)
    else:
        print("  ℹ️   No OpenAQ data — continuing with IoT data only")

    # ── Step 3 — Extract ──────────────────────────────────────────────────
    step(3, "📥  Extract — CSV + JSON")
    from etl.extract import extract_iot_csv, extract_openaq_json
    iot_extracted    = extract_iot_csv(DATA_DIR)
    openaq_extracted = extract_openaq_json(DATA_DIR)

    # ── Step 4 — Transform ────────────────────────────────────────────────
    step(4, "🔄  Transform — Clean, AQI-tag, Dedup")
    from etl.transform import transform_iot, transform_openaq
    iot_t    = transform_iot(iot_extracted)
    openaq_t = transform_openaq(openaq_extracted)

    # ── Step 5 — Load Bronze ──────────────────────────────────────────────
    step(5, "❄️   Load → Snowflake Bronze (RAW)")
    iot_loaded = openaq_loaded = 0
    conn = None

    if skip_snowflake:
        print("  ⏭️   Snowflake skipped.")
    else:
        from etl.load import get_connection, load_iot_readings, load_openaq_raw
        conn = get_connection()
        if conn:
            iot_loaded    = load_iot_readings(iot_t, conn)
            openaq_loaded = load_openaq_raw(openaq_t, conn)
        else:
            print("  ⚠️   Could not connect to Snowflake — Bronze load skipped.")

    # ── Step 6 — Silver ───────────────────────────────────────────────────
    step(6, "🥈  Build Silver — CLEAN.AQI_CLEAN")
    from etl.silver import build_silver, load_silver
    silver_df = build_silver(iot_t, openaq_t)
    silver_loaded = 0
    if skip_snowflake:
        print(f"  ⏭️   Snowflake skipped. Silver built locally ({len(silver_df)} rows).")
    elif conn:
        silver_loaded = load_silver(silver_df, conn)
    else:
        print("  ⚠️   No Snowflake connection — Silver load skipped.")

    # ── Step 7 — Gold ─────────────────────────────────────────────────────
    step(7, "🥇  Build Gold — ANALYTICS.CITY_DAILY")
    from etl.gold import build_gold, load_gold
    gold_df = build_gold(silver_df)
    gold_loaded = 0
    if skip_snowflake:
        print(f"  ⏭️   Snowflake skipped. Gold built locally ({len(gold_df)} rows).")
    elif conn:
        gold_loaded = load_gold(gold_df, conn)
    else:
        print("  ⚠️   No Snowflake connection — Gold load skipped.")

    if conn:
        conn.close()
        print("  🔌  Snowflake connection closed.")

    # ── Summary ───────────────────────────────────────────────────────────
    duration = round(time.perf_counter() - t0, 2)
    sep("📋  Pipeline Summary")
    W = 46
    print(f"  {'Metric':<{W}} {'Value':>8}")
    print(f"  {'─'*W} {'─'*8}")
    print(f"  {'IoT readings simulated':<{W}} {len(iot_raw):>8,}")
    print(f"  {'OpenAQ measurements fetched':<{W}} {len(openaq_raw):>8,}")
    print(f"  {'IoT rows transformed':<{W}} {len(iot_t):>8,}")
    print(f"  {'OpenAQ rows transformed':<{W}} {len(openaq_t):>8,}")
    print(f"  {'IoT rows → RAW.IOT_READINGS':<{W}} {iot_loaded:>8,}")
    print(f"  {'OpenAQ rows → RAW.OPENAQ_RAW':<{W}} {openaq_loaded:>8,}")
    print(f"  {'Silver rows → CLEAN.AQI_CLEAN':<{W}} {len(silver_df):>8,}")
    print(f"  {'Gold rows → ANALYTICS.CITY_DAILY':<{W}} {len(gold_df):>8,}")
    print(f"  {'Duration (seconds)':<{W}} {duration:>8}")
    print(f"\n  ✅  Pipeline complete!")
    print(f"\n  💡  Launch dashboard:\n      streamlit run dashboard/app.py\n")

    if launch_dashboard:
        import subprocess
        app = ROOT / "dashboard" / "app.py"
        subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(app)], cwd=str(ROOT))
        print("  🌐  Streamlit starting at http://localhost:8501 …")

    return {
        "iot_simulated":    len(iot_raw),
        "openaq_fetched":   len(openaq_raw),
        "silver_rows":      len(silver_df),
        "gold_rows":        len(gold_df),
        "duration_seconds": duration,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart City AQI — Full Pipeline")
    parser.add_argument("--n",               type=int, default=DEFAULT_BATCH_SIZE,
                        help="IoT readings to simulate")
    parser.add_argument("--skip-snowflake",  action="store_true",
                        help="Skip all Snowflake loads (local mode)")
    parser.add_argument("--dashboard",       action="store_true",
                        help="Launch Streamlit after pipeline")
    args = parser.parse_args()
    run(n_readings=args.n, skip_snowflake=args.skip_snowflake, launch_dashboard=args.dashboard)
