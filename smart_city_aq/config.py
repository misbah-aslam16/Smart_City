"""
config.py — Central configuration
Smart City Air Quality Monitoring System — Pakistan

All credentials are loaded from .env file.
Run: cp .env.example .env  and fill in your values before running.
"""

import os
import pathlib
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(dotenv_path=pathlib.Path(__file__).parent / ".env")

# ---------------------------------------------------------------------------
# Snowflake
# ---------------------------------------------------------------------------
SNOWFLAKE_CONFIG = {
    "account":   os.getenv("SNOWFLAKE_ACCOUNT",  "your_account_identifier"),
    "user":      os.getenv("SNOWFLAKE_USER",      "your_username"),
    "password":  os.getenv("SNOWFLAKE_PASSWORD",  "your_password"),
    "database":  os.getenv("SNOWFLAKE_DATABASE",  "AIR_QUALITY_DB"),
    "schema":    os.getenv("SNOWFLAKE_SCHEMA",    "RAW"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    "role":      os.getenv("SNOWFLAKE_ROLE",      "SYSADMIN"),
}

# ---------------------------------------------------------------------------
# OpenAQ V3 API
# ---------------------------------------------------------------------------
OPENAQ_API_KEY  = os.getenv("OPENAQ_API_KEY", "")
OPENAQ_BASE_URL = "https://api.openaq.org/v3"

# ---------------------------------------------------------------------------
# Snowflake layer references
# ---------------------------------------------------------------------------
DB            = "AIR_QUALITY_DB"
BRONZE_SCHEMA = "RAW"        # Phase 1 — raw data
SILVER_SCHEMA = "CLEAN"      # Phase 2 — validated + joined
GOLD_SCHEMA   = "ANALYTICS"  # Phase 2 — aggregated

# Fully-qualified table names
BRONZE_IOT    = f"{DB}.{BRONZE_SCHEMA}.IOT_READINGS"
BRONZE_OPENAQ = f"{DB}.{BRONZE_SCHEMA}.OPENAQ_RAW"
SILVER_TABLE  = f"{DB}.{SILVER_SCHEMA}.AQI_CLEAN"
GOLD_TABLE    = f"{DB}.{GOLD_SCHEMA}.CITY_DAILY"

# ---------------------------------------------------------------------------
# Pakistani Cities
# ---------------------------------------------------------------------------
CITIES = {
    "Karachi":   {"lat": 24.8607, "lon": 67.0011},
    "Lahore":    {"lat": 31.5204, "lon": 74.3587},
    "Islamabad": {"lat": 33.6844, "lon": 73.0479},
    "Peshawar":  {"lat": 34.0151, "lon": 71.5249},
    "Multan":    {"lat": 30.1575, "lon": 71.5249},
}

# ---------------------------------------------------------------------------
# AQI colour maps (used by Streamlit dashboard)
# ---------------------------------------------------------------------------
AQI_COLORS = {
    "Good":                             "#00E400",
    "Moderate":                         "#FFFF00",
    "Unhealthy for Sensitive Groups":   "#FF7E00",
    "Unhealthy":                        "#FF0000",
    "Very Unhealthy":                   "#8F3F97",
    "Hazardous":                        "#7E0023",
    "Unknown":                          "#AAAAAA",
}

HEALTH_RISK_COLORS = {
    "Low":       "#00E400",
    "Moderate":  "#FFFF00",
    "Elevated":  "#FF7E00",
    "High":      "#FF0000",
    "Very High": "#8F3F97",
    "Critical":  "#7E0023",
    "Unknown":   "#AAAAAA",
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR          = pathlib.Path(__file__).parent
DATA_DIR          = BASE_DIR / "data"
DEFAULT_BATCH_SIZE = 100
