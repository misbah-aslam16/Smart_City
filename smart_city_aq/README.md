# 🌆 Smart City Air Quality Monitoring System

Karachi · Lahore · Islamabad · Peshawar · Multan

---

## Project Structure

```
smart_city_aq/
├── iot_simulator/
│   ├── sensor_config.py     # 10 sensors, 5 cities, pollution ranges
│   └── simulator.py         # generates IoT readings → data/
├── openaq_fetcher/
│   └── fetcher.py           # OpenAQ V3 API → data/
├── etl/
│   ├── extract.py           # CSV + JSON → DataFrame
│   ├── transform.py         # AQI calc, clean, dedup
│   ├── load.py              # → Snowflake Bronze (RAW)
│   ├── silver.py            # Bronze → Silver (CLEAN.AQI_CLEAN)
│   └── gold.py              # Silver → Gold (ANALYTICS.CITY_DAILY)
├── dashboard/
│   ├── data_loader.py       # Snowflake queries + demo fallback
│   └── app.py               # Streamlit dashboard
├── sql/
│   ├── 01_bronze.sql        # RAW.IOT_READINGS + RAW.OPENAQ_RAW
│   └── 02_silver_gold.sql   # CLEAN.AQI_CLEAN + ANALYTICS.CITY_DAILY
├── data/                    # CSV + JSON output (gitignored)
├── config.py                # Central config (reads .env)
├── run_pipeline.py          # Full pipeline orchestrator
├── requirements.txt
└── .env.example
```

---

## Architecture

```
IoT Simulator (Python)          OpenAQ V3 API (Pakistan)
      │ CSV                            │ JSON
      └──────────────┬─────────────────┘
                     │
              data/ (local files)
                     │
          ┌──── ETL Pipeline ────┐
          │ Extract → Transform  │
          │   → Load (Bronze)    │
          └──────────┬───────────┘
                     │
          Snowflake — Bronze (RAW)
          ├── RAW.IOT_READINGS
          └── RAW.OPENAQ_RAW
                     │
          Snowflake — Silver (CLEAN)
          └── CLEAN.AQI_CLEAN
                     │
          Snowflake — Gold (ANALYTICS)
          └── ANALYTICS.CITY_DAILY
                     │
          Streamlit Dashboard
          (bar · line · metric cards · pie)
```

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure credentials
```bash
copy .env.example .env
# Fill in Snowflake credentials and OpenAQ API key
```

### 3. Create Snowflake tables
Run in Snowflake worksheet (in order):
```
sql/01_bronze.sql
sql/02_silver_gold.sql
```

---

## Running

### Full pipeline (all 7 steps)
```bash
python run_pipeline.py
```

### With custom IoT batch size
```bash
python run_pipeline.py --n 500
```

### Local mode (no Snowflake needed)
```bash
python run_pipeline.py --skip-snowflake
```

### Launch dashboard after pipeline
```bash
python run_pipeline.py --dashboard
```

### Launch dashboard standalone
```bash
streamlit run dashboard/app.py
```

### Run individual components
```bash
python iot_simulator/simulator.py --n 100
python openaq_fetcher/fetcher.py
python etl/transform.py     # AQI smoke-test
```

---

## Snowflake Layers

| Layer | Schema | Table | Description |
|-------|--------|-------|-------------|
| Bronze | RAW | IOT_READINGS | Raw IoT sensor readings |
| Bronze | RAW | OPENAQ_RAW | Raw OpenAQ API measurements |
| Silver | CLEAN | AQI_CLEAN | Validated, unified, AQI-tagged |
| Gold | ANALYTICS | CITY_DAILY | Daily city-level aggregates |

---

## AQI Categories (US EPA)

| PM2.5 µg/m³ | AQI | Category | Health Risk |
|-------------|-----|----------|-------------|
| 0–12 | 0–50 | Good | Low |
| 12.1–35.4 | 51–100 | Moderate | Moderate |
| 35.5–55.4 | 101–150 | Unhealthy for Sensitive Groups | Elevated |
| 55.5–150.4 | 151–200 | Unhealthy | High |
| 150.5–250.4 | 201–300 | Very Unhealthy | Very High |
| 250.5+ | 301–500 | Hazardous | Critical |

---

## Deliverables

- ✅ D1 — IoT simulator (10 sensors × 5 cities)
- ✅ D2 — OpenAQ V3 API fetcher
- ✅ D3 — ETL → Snowflake Bronze
- ✅ D4 — Bronze loaded
- ✅ D5 — Silver + Gold built
- ✅ D6 — Streamlit dashboard live

