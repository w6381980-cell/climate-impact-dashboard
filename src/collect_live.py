import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from db import get_conn, init_db

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
OW_KEY = (os.getenv("OPENWEATHER_API_KEY") or "").strip().strip('"').strip("'")
CITIES_CSV = ROOT / "config" / "cities.csv"

OM_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
OM_AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
OW_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
OW_AIR_URL = "https://api.openweathermap.org/data/2.5/air_pollution"


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")


def ts(unix):
    return datetime.fromtimestamp(unix, timezone.utc).strftime("%Y-%m-%dT%H:%M")


def fetch_openmeteo(city, lat, lon):
    w = requests.get(
        OM_WEATHER_URL,
        params={"latitude": lat, "longitude": lon, "timezone": "GMT",
                "current": "temperature_2m,precipitation"},
        timeout=20,
    )
    w.raise_for_status()
    a = requests.get(
        OM_AIR_URL,
        params={"latitude": lat, "longitude": lon, "timezone": "GMT",
                "current": "pm2_5,pm10,us_aqi"},
        timeout=20,
    )
    a.raise_for_status()
    wc, ac = w.json()["current"], a.json()["current"]
    return (city, lat, lon, wc["time"], ac["time"],
            wc.get("temperature_2m"), wc.get("precipitation"),
            ac.get("pm2_5"), ac.get("pm10"), ac.get("us_aqi"),
            "open-meteo", now_utc(), None)


def fetch_openweather(city, lat, lon):
    w = requests.get(
        OW_WEATHER_URL,
        params={"lat": lat, "lon": lon, "appid": OW_KEY, "units": "metric"},
        timeout=20,
    )
    w.raise_for_status()
    a = requests.get(
        OW_AIR_URL,
        params={"lat": lat, "lon": lon, "appid": OW_KEY},
        timeout=20,
    )
    a.raise_for_status()
    wj = w.json()
    aj = a.json()["list"][0]
    rain = wj.get("rain", {}).get("1h", 0.0)  # sirf tab aata hai jab baarish ho
    return (city, lat, lon, ts(wj["dt"]), ts(aj["dt"]),
            wj["main"]["temp"], rain,
            aj["components"]["pm2_5"], aj["components"]["pm10"], None,
            "openweather", now_utc(), aj["main"]["aqi"])


def main():
    init_db()
    cities = pd.read_csv(CITIES_CSV)
    fetchers = [fetch_openmeteo]
    if OW_KEY:
        fetchers.append(fetch_openweather)
    else:
        print("OpenWeather key nahi mili, sirf Open-Meteo chalega")

    rows = []
    for c in cities.itertuples():
        for fetch in fetchers:
            try:
                rows.append(fetch(c.city, c.lat, c.lon))
                print("OK  ", c.city, fetch.__name__)
            except Exception as e:
                print("FAIL", c.city, fetch.__name__, "->", e)

    with get_conn() as conn:
        conn.executemany(
            """INSERT OR IGNORE INTO live_readings
               (city, lat, lon, weather_time_utc, air_time_utc,
                temperature_c, precipitation_mm, pm2_5, pm10, us_aqi,
                source, fetched_at_utc, ow_aqi)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
        df = pd.read_sql_query(
            """SELECT city, source, temperature_c, pm2_5, us_aqi, ow_aqi
               FROM live_readings ORDER BY id DESC LIMIT 20""",
            conn,
        )
    print("\nSaved. Latest rows:")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()