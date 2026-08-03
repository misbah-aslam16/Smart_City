"""
sensor_config.py — 10 virtual IoT sensors across 5 Pakistani cities
Smart City Air Quality Monitoring System
"""

# Naming: {CITY_CODE}_{ZONE_CODE}_{SEQ}
SENSORS = [
    # ── Karachi ─────────────────────────────────────────────────────────
    {"sensor_id": "KHI_IND_001", "city": "Karachi",   "zone_type": "industrial",  "lat": 24.8607, "lon": 67.0011, "desc": "Korangi Industrial Zone"},
    {"sensor_id": "KHI_TRF_002", "city": "Karachi",   "zone_type": "traffic",     "lat": 24.8722, "lon": 67.0306, "desc": "Shahra-e-Faisal Corridor"},
    # ── Lahore ──────────────────────────────────────────────────────────
    {"sensor_id": "LHR_IND_001", "city": "Lahore",    "zone_type": "industrial",  "lat": 31.5204, "lon": 74.3587, "desc": "Kot Lakhpat Industrial Area"},
    {"sensor_id": "LHR_TRF_002", "city": "Lahore",    "zone_type": "traffic",     "lat": 31.5497, "lon": 74.3436, "desc": "Mall Road / GT Road"},
    # ── Islamabad ───────────────────────────────────────────────────────
    {"sensor_id": "ISB_RES_001", "city": "Islamabad", "zone_type": "residential", "lat": 33.6844, "lon": 73.0479, "desc": "F-6 Residential Sector"},
    {"sensor_id": "ISB_PRK_002", "city": "Islamabad", "zone_type": "park",        "lat": 33.7294, "lon": 73.0931, "desc": "Margalla Hills National Park"},
    # ── Peshawar ────────────────────────────────────────────────────────
    {"sensor_id": "PSH_IND_001", "city": "Peshawar",  "zone_type": "industrial",  "lat": 34.0151, "lon": 71.5249, "desc": "Hayatabad Industrial Estate"},
    {"sensor_id": "PSH_TRF_002", "city": "Peshawar",  "zone_type": "traffic",     "lat": 34.0080, "lon": 71.5780, "desc": "GT Road / Namak Mandi"},
    # ── Multan ──────────────────────────────────────────────────────────
    {"sensor_id": "MLT_RES_001", "city": "Multan",    "zone_type": "residential", "lat": 30.1575, "lon": 71.5249, "desc": "Gulgasht Colony"},
    {"sensor_id": "MLT_IND_002", "city": "Multan",    "zone_type": "industrial",  "lat": 30.1960, "lon": 71.4753, "desc": "Industrial Estate, Vehari Road"},
]

# Realistic pollution ranges per zone (µg/m³ unless noted)
ZONE_POLLUTION_RANGES = {
    "industrial": {
        "pm25": (50,  200), "pm10": (80,  300),
        "no2":  (40,  120), "co":   (1.5,  8.0),
        "o3":   (20,   80), "so2":  (20,  100),
    },
    "traffic": {
        "pm25": (40,  150), "pm10": (60,  200),
        "no2":  (50,  150), "co":   (2.0, 10.0),
        "o3":   (15,   60), "so2":  (10,   50),
    },
    "residential": {
        "pm25": (20,   80), "pm10": (30,  120),
        "no2":  (15,   60), "co":   (0.5,  3.0),
        "o3":   (10,   50), "so2":  (5,    30),
    },
    "park": {
        "pm25": (10,   40), "pm10": (15,   60),
        "no2":  (5,    30), "co":   (0.2,  1.5),
        "o3":   (20,   70), "so2":  (2,    15),
    },
}

SENSOR_BY_ID = {s["sensor_id"]: s for s in SENSORS}
