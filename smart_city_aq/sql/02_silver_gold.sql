-- =============================================================================
-- 02_silver_gold.sql  —  Silver & Gold Layer DDL
-- Smart City Air Quality Monitoring System — Pakistan
-- Run AFTER 01_bronze.sql
-- =============================================================================

USE DATABASE AIR_QUALITY_DB;

-- ── Silver Schema ─────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS AIR_QUALITY_DB.CLEAN
    DATA_RETENTION_TIME_IN_DAYS = 7
    COMMENT = 'Silver: validated, AQI-tagged, both sources joined';

CREATE TABLE IF NOT EXISTS AIR_QUALITY_DB.CLEAN.AQI_CLEAN (
    source              VARCHAR(10)   NOT NULL  COMMENT 'iot | openaq',
    source_id           VARCHAR(200)            COMMENT 'reading_id or location::ts',
    city                VARCHAR(100)  NOT NULL,
    zone_type           VARCHAR(30)             COMMENT 'industrial|traffic|residential|park|station',
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
COMMENT = 'Silver: cleaned and unified readings (IoT + OpenAQ)';

-- ── Gold Schema ───────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS AIR_QUALITY_DB.ANALYTICS
    DATA_RETENTION_TIME_IN_DAYS = 30
    COMMENT = 'Gold: daily city-level aggregates for dashboards';

CREATE TABLE IF NOT EXISTS AIR_QUALITY_DB.ANALYTICS.CITY_DAILY (
    city                VARCHAR(100)  NOT NULL,
    reading_date        DATE          NOT NULL,
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
    aggregated_at       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (city, reading_date)
)
COMMENT = 'Gold: daily city AQI aggregates for Streamlit / Power BI';

-- ── Verification (uncomment after first run) ──────────────────────────────────
-- SELECT source, city, COUNT(*) FROM AIR_QUALITY_DB.CLEAN.AQI_CLEAN GROUP BY 1,2;
-- SELECT city, reading_date, avg_aqi, dominant_risk FROM AIR_QUALITY_DB.ANALYTICS.CITY_DAILY ORDER BY 2 DESC;
