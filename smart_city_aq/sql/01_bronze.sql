-- =============================================================================
-- 01_bronze.sql  —  Bronze / RAW Layer DDL
-- Smart City Air Quality Monitoring System — Pakistan
-- Run FIRST in Snowflake before executing the pipeline.
-- =============================================================================

CREATE DATABASE IF NOT EXISTS AIR_QUALITY_DB
    DATA_RETENTION_TIME_IN_DAYS = 1
    COMMENT = 'Smart City Air Quality Monitoring — Pakistan';

CREATE SCHEMA IF NOT EXISTS AIR_QUALITY_DB.RAW
    DATA_RETENTION_TIME_IN_DAYS = 1
    COMMENT = 'Bronze: raw IoT sensor readings and OpenAQ API data';

-- ── IoT Readings ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS AIR_QUALITY_DB.RAW.IOT_READINGS (
    reading_id          VARCHAR(50)  NOT NULL  COMMENT 'UUID per reading',
    sensor_id           VARCHAR(20)  NOT NULL  COMMENT 'e.g. KHI_IND_001',
    city                VARCHAR(50)  NOT NULL,
    zone_type           VARCHAR(20)  NOT NULL  COMMENT 'industrial|traffic|residential|park',
    lat                 FLOAT,
    lon                 FLOAT,
    pm25                FLOAT        COMMENT 'µg/m³',
    pm10                FLOAT        COMMENT 'µg/m³',
    no2                 FLOAT        COMMENT 'µg/m³',
    co                  FLOAT        COMMENT 'mg/m³',
    o3                  FLOAT        COMMENT 'µg/m³',
    so2                 FLOAT        COMMENT 'µg/m³',
    aqi_value           INTEGER      COMMENT 'US EPA AQI 0–500',
    aqi_category        VARCHAR(50),
    health_risk         VARCHAR(20),
    reading_timestamp   TIMESTAMP_NTZ,
    ingested_at         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Simulated IoT sensor readings for 5 Pakistani cities';

-- ── OpenAQ Raw ────────────────────────────────────────────────────────────────
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
COMMENT = 'Raw OpenAQ V3 measurements for Pakistan';
