from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

from db import get_conn, init_db

ROOT = Path(__file__).resolve().parent.parent
CITIES_CSV = ROOT / "config" / "cities.csv"

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
TZ = "Asia/Kolkata"


def clean_rows(df):
    df = df.astype(object).where(df.notna(), None)
    return list(df.itertuples(index=False, name=None))


def fetch_weather(city, lat, lon, start, end):
    r = requests.get(
        ARCHIVE_URL,
        params={
            "latitude": lat, "longitude": lon,
            "start_date": start, "end_date": end,
            "daily": "temperature_2m_mean,temperature_2m_max,"
                     "temperature_2m_min,precipitation_sum",
            "timezone": TZ,
        },
        timeout=60,
    )
    r.raise_for_status()
    d = pd.DataFrame(r.json()["daily"])
    d.insert(0, "city", city)
    return clean_rows(d)


def fetch_air(city, lat, lon):
    r = requests.get(
        AIR_URL,
        params={
            "latitude": lat, "longitude": lon,
            "hourly": "pm2_5,pm10,us_aqi",
            "past_days": 90, "forecast_days": 1,
            "timezone": TZ,
        },
        timeout=60,
    )
    r.raise_for_status()
    h = pd.DataFrame(r.json()["hourly"])
    h["date"] = h["time"].str[:10]
    today = pd.Timestamp.now(tz=TZ).strftime("%Y-%m-%d")
    h = h[h["date"] < today]  # adhoora aaj ka din chhod do
    g = h.groupby("date").agg(
        pm2_5_mean=("pm2_5", "mean"),
        pm10_mean=("pm10", "mean"),
        us_aqi_mean=("us_aqi", "mean"),
        hours_count=("pm2_5", "count"),
    ).reset_index()
    g[["pm2_5_mean", "pm10_mean", "us_aqi_mean"]] = g[
        ["pm2_5_mean", "pm10_mean", "us_aqi_mean"]
    ].round(1)
    g.insert(0, "city", city)
    return clean_rows(g[["city", "date", "pm2_5_mean", "pm10_mean",
                         "us_aqi_mean", "hours_count"]])


def main():
    init_db()
    cities = pd.read_csv(CITIES_CSV)
    end = date.today() - timedelta(days=7)   # archive data mein kuch din ki deri hoti hai
    start = end - timedelta(days=364)

    with get_conn() as conn:
        for c in cities.itertuples():
            try:
                rows = fetch_weather(c.city, c.lat, c.lon, start.isoformat(), end.isoformat())
                conn.executemany(
                    "INSERT OR REPLACE INTO daily_weather VALUES (?,?,?,?,?,?)", rows)
                print("OK   weather", c.city, len(rows), "days")
            except Exception as e:
                print("FAIL weather", c.city, "->", e)
            try:
                rows = fetch_air(c.city, c.lat, c.lon)
                conn.executemany(
                    "INSERT OR REPLACE INTO daily_air VALUES (?,?,?,?,?,?)", rows)
                print("OK   air    ", c.city, len(rows), "days")
            except Exception as e:
                print("FAIL air    ", c.city, "->", e)

        w = pd.read_sql_query(
            """SELECT city, COUNT(*) AS days,
                      ROUND(AVG(temp_mean_c),1) AS avg_temp,
                      ROUND(SUM(precip_mm),0) AS rain_mm
               FROM daily_weather GROUP BY city""", conn)
        a = pd.read_sql_query(
            """SELECT city, COUNT(*) AS days,
                      ROUND(AVG(pm2_5_mean),1) AS avg_pm25,
                      ROUND(MAX(pm2_5_mean),1) AS max_pm25
               FROM daily_air GROUP BY city""", conn)
    print("\nWeather summary:\n", w.to_string(index=False))
    print("\nAir summary:\n", a.to_string(index=False))


if __name__ == "__main__":
    main()