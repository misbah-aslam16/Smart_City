"""
fetcher.py — OpenAQ V3 API Fetcher for Pakistan
Smart City Air Quality Monitoring System

Strategy:
  1. GET /v3/locations?countries_id=109  → Pakistan location list
  2. GET /v3/locations/{id}/sensors      → sensors with latest values + parameter names
  Uses ThreadPoolExecutor (20 workers) for fast parallel fetching.

Pakistan country ID in OpenAQ V3 = 109

Usage:
    python openaq_fetcher/fetcher.py
"""

import json
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import pandas as pd
import requests

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import OPENAQ_API_KEY, DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)

PAKISTAN_COUNTRY_ID = 109
_BASE    = "https://api.openaq.org/v3"
_TIMEOUT = 15

# Cities we care about
_PK_CITIES = ["karachi","lahore","islamabad","peshawar","multan"]


def _headers() -> dict:
    h = {"Accept": "application/json", "User-Agent": "SmartCityAQ/1.0"}
    if OPENAQ_API_KEY:
        h["X-API-Key"] = OPENAQ_API_KEY
    return h


def _map_city(name: str, locality: str) -> str:
    """Try to match location name/locality to our 5 cities."""
    text = ((name or "") + " " + (locality or "")).lower()
    for city in _PK_CITIES:
        if city in text:
            return city.title()
    return (locality or name or "Unknown").strip()


def _get_pakistan_locations(max_locations: int = 300) -> list:
    """Fetch all Pakistan locations (paginated). Returns list of dicts."""
    locations = []
    page = 1
    while len(locations) < max_locations:
        try:
            r = requests.get(
                f"{_BASE}/locations",
                headers=_headers(),
                params={"countries_id": PAKISTAN_COUNTRY_ID,
                        "limit": 100, "page": page},
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            results = r.json().get("results", [])
            if not results:
                break
            for item in results:
                coords = item.get("coordinates") or {}
                locations.append({
                    "location_id":   item["id"],
                    "location_name": item.get("name", "Unknown"),
                    "city":          _map_city(item.get("name",""), item.get("locality","")),
                    "lat":           coords.get("latitude"),
                    "lon":           coords.get("longitude"),
                })
            if len(results) < 100:
                break
            page += 1
        except Exception as exc:
            print(f"  ⚠️  Locations page {page} error: {exc}")
            break

    print(f"📡  Found {len(locations)} Pakistan locations")
    return locations[:max_locations]


def _fetch_sensors_for_location(loc: dict) -> list:
    """
    GET /v3/locations/{id}/sensors
    Returns rows with parameter name, latest value, timestamp.
    """
    loc_id = loc["location_id"]
    try:
        r = requests.get(
            f"{_BASE}/locations/{loc_id}/sensors",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        if r.status_code in (404, 422):
            return []
        r.raise_for_status()
        sensors = r.json().get("results", [])

        rows = []
        for s in sensors:
            latest = s.get("latest") or {}
            if not latest or latest.get("value") is None:
                continue

            param = s.get("parameter", {}) or {}
            param_name = param.get("name", "unknown")
            unit       = param.get("units", "")

            dt = latest.get("datetime", {}) or {}
            ts = dt.get("utc") if isinstance(dt, dict) else str(dt)

            coords = latest.get("coordinates") or {}

            rows.append({
                "location_id":   loc_id,
                "location_name": loc["location_name"],
                "city":          loc["city"],
                "parameter":     param_name,
                "value":         latest.get("value"),
                "unit":          unit,
                "timestamp":     ts,
                "lat":           loc.get("lat") or coords.get("latitude"),
                "lon":           loc.get("lon") or coords.get("longitude"),
            })
        return rows
    except Exception:
        return []


def fetch_pakistan_data(max_locations: int = 300) -> pd.DataFrame:
    """
    Fetch latest air quality data for Pakistan using /sensors endpoint.

    Args:
        max_locations: How many locations to query (default 300)

    Returns:
        DataFrame with columns:
            location_id, location_name, city, parameter,
            value, unit, timestamp, lat, lon
    """
    if not OPENAQ_API_KEY:
        print("⚠️  OPENAQ_API_KEY not set.")
        print("    Get free key: https://explore.openaq.org/ → Account → API Keys")
        return pd.DataFrame()

    locations = _get_pakistan_locations(max_locations)
    if not locations:
        return pd.DataFrame()

    print(f"⬇️   Fetching sensor data (parallel, 20 workers) …")

    all_rows = []
    done     = 0

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {pool.submit(_fetch_sensors_for_location, loc): loc
                   for loc in locations}
        for future in as_completed(futures):
            rows  = future.result()
            all_rows.extend(rows)
            done += 1
            if done % 100 == 0:
                print(f"  … {done}/{len(locations)} locations, "
                      f"{len(all_rows)} measurements so far")

    if not all_rows:
        print("⚠️  No measurements returned.")
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["value"]     = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value", "parameter"])
    df = df[df["parameter"] != "unknown"]

    print(f"✅  Fetched {len(df):,} measurements — "
          f"{df['parameter'].nunique()} parameters, "
          f"{df['city'].nunique()} cities")
    print(f"    Parameters: {df['parameter'].value_counts().to_dict()}")
    return df


def save_to_json(df: pd.DataFrame, filepath=None) -> pathlib.Path:
    """Save DataFrame to timestamped JSON in data/."""
    if filepath is None:
        ts       = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filepath = DATA_DIR / f"openaq_raw_{ts}.json"
    filepath = pathlib.Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    records = json.loads(
        df.to_json(orient="records", date_format="iso", force_ascii=False)
    )
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"💾  OpenAQ JSON saved → {filepath}  ({len(df)} rows)")
    return filepath


if __name__ == "__main__":
    print("\n🚀  OpenAQ V3 Fetcher — Pakistan\n")
    df = fetch_pakistan_data()
    if not df.empty:
        save_to_json(df)
        print(f"\n📊  Sample:\n{df.head(10).to_string(index=False)}")
    else:
        print("No data fetched.")
