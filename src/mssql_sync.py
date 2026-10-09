import math
from datetime import datetime

import pandas as pd

from db import get_conn
from mssql_conn import connect

# kind: s = text, f = decimal, i = integer, d = date, t = datetime
TABLES = [
    {
        "name": "City",
        "target": "climate.City",
        "query": "SELECT city, MAX(lat) AS lat, MAX(lon) AS lon FROM live_readings GROUP BY city",
        "kinds": "sff",
        "stage": "CREATE TABLE #stg (CityName nvarchar(60), Latitude decimal(9,4), Longitude decimal(9,4))",
        "merge": """
            MERGE climate.City AS t
            USING #stg AS s ON t.CityName = s.CityName
            WHEN MATCHED THEN UPDATE SET t.Latitude = s.Latitude, t.Longitude = s.Longitude
            WHEN NOT MATCHED THEN INSERT (CityName, Latitude, Longitude) VALUES (s.CityName, s.Latitude, s.Longitude);""",
    },
    {
        "name": "LiveReading",
        "target": "climate.LiveReading",
        "query": ("SELECT city, source, weather_time_utc, air_time_utc, temperature_c, precipitation_mm, "
                  "pm2_5, pm10, us_aqi, ow_aqi, fetched_at_utc FROM live_readings"),
        "kinds": "ssttffffiit",
        "stage": ("CREATE TABLE #stg (CityName nvarchar(60), Source varchar(20), WeatherTimeUtc datetime2(0), "
                  "AirTimeUtc datetime2(0), TemperatureC decimal(5,2), PrecipitationMm decimal(7,2), "
                  "Pm25 decimal(7,2), Pm10 decimal(7,2), UsAqi smallint, OwAqi tinyint, FetchedAtUtc datetime2(0))"),
        "merge": """
            MERGE climate.LiveReading AS t
            USING (SELECT c.CityId, s.* FROM #stg AS s JOIN climate.City AS c ON c.CityName = s.CityName) AS s
               ON t.CityId = s.CityId AND t.Source = s.Source
              AND t.WeatherTimeUtc = s.WeatherTimeUtc AND t.AirTimeUtc = s.AirTimeUtc
            WHEN MATCHED THEN UPDATE SET t.TemperatureC = s.TemperatureC, t.PrecipitationMm = s.PrecipitationMm,
                 t.Pm25 = s.Pm25, t.Pm10 = s.Pm10, t.UsAqi = s.UsAqi, t.OwAqi = s.OwAqi, t.FetchedAtUtc = s.FetchedAtUtc
            WHEN NOT MATCHED THEN INSERT (CityId, Source, WeatherTimeUtc, AirTimeUtc, TemperatureC, PrecipitationMm,
                 Pm25, Pm10, UsAqi, OwAqi, FetchedAtUtc)
                 VALUES (s.CityId, s.Source, s.WeatherTimeUtc, s.AirTimeUtc, s.TemperatureC, s.PrecipitationMm,
                 s.Pm25, s.Pm10, s.UsAqi, s.OwAqi, s.FetchedAtUtc);""",
    },
    {
        "name": "DailyWeather",
        "target": "climate.DailyWeather",
        "query": "SELECT city, date, temp_mean_c, temp_max_c, temp_min_c, precip_mm FROM daily_weather",
        "kinds": "sdffff",
        "stage": ("CREATE TABLE #stg (CityName nvarchar(60), WeatherDate date, TempMeanC decimal(5,2), "
                  "TempMaxC decimal(5,2), TempMinC decimal(5,2), PrecipMm decimal(7,2))"),
        "merge": """
            MERGE climate.DailyWeather AS t
            USING (SELECT c.CityId, s.* FROM #stg AS s JOIN climate.City AS c ON c.CityName = s.CityName) AS s
               ON t.CityId = s.CityId AND t.WeatherDate = s.WeatherDate
            WHEN MATCHED THEN UPDATE SET t.TempMeanC = s.TempMeanC, t.TempMaxC = s.TempMaxC,
                 t.TempMinC = s.TempMinC, t.PrecipMm = s.PrecipMm
            WHEN NOT MATCHED THEN INSERT (CityId, WeatherDate, TempMeanC, TempMaxC, TempMinC, PrecipMm)
                 VALUES (s.CityId, s.WeatherDate, s.TempMeanC, s.TempMaxC, s.TempMinC, s.PrecipMm);""",
    },
    {
        "name": "DailyAir",
        "target": "climate.DailyAir",
        "query": "SELECT city, date, pm2_5_mean, pm10_mean, us_aqi_mean, hours_count FROM daily_air",
        "kinds": "sdfffi",
        "stage": ("CREATE TABLE #stg (CityName nvarchar(60), AirDate date, Pm25Mean decimal(7,2), "
                  "Pm10Mean decimal(7,2), UsAqiMean decimal(6,1), HoursCount smallint)"),
        "merge": """
            MERGE climate.DailyAir AS t
            USING (SELECT c.CityId, s.* FROM #stg AS s JOIN climate.City AS c ON c.CityName = s.CityName) AS s
               ON t.CityId = s.CityId AND t.AirDate = s.AirDate
            WHEN MATCHED THEN UPDATE SET t.Pm25Mean = s.Pm25Mean, t.Pm10Mean = s.Pm10Mean,
                 t.UsAqiMean = s.UsAqiMean, t.HoursCount = s.HoursCount
            WHEN NOT MATCHED THEN INSERT (CityId, AirDate, Pm25Mean, Pm10Mean, UsAqiMean, HoursCount)
                 VALUES (s.CityId, s.AirDate, s.Pm25Mean, s.Pm10Mean, s.UsAqiMean, s.HoursCount);""",
    },
    {
        "name": "EmissionsCountry",
        "target": "climate.EmissionsCountry",
        "query": ("SELECT country, year, co2_mt, co2_per_capita_t, share_global_co2_pct, co2_incl_luc_mt, population "
                  "FROM emissions_country"),
        "kinds": "siffffi",
        "stage": ("CREATE TABLE #stg (Country nvarchar(60), Yr smallint, Co2Mt decimal(12,3), Co2PerCapitaT decimal(8,3), "
                  "ShareGlobalCo2Pct decimal(8,4), Co2InclLucMt decimal(12,3), Population bigint)"),
        "merge": """
            MERGE climate.EmissionsCountry AS t
            USING #stg AS s ON t.Country = s.Country AND t.[Year] = s.Yr
            WHEN MATCHED THEN UPDATE SET t.Co2Mt = s.Co2Mt, t.Co2PerCapitaT = s.Co2PerCapitaT,
                 t.ShareGlobalCo2Pct = s.ShareGlobalCo2Pct, t.Co2InclLucMt = s.Co2InclLucMt, t.Population = s.Population
            WHEN NOT MATCHED THEN INSERT (Country, [Year], Co2Mt, Co2PerCapitaT, ShareGlobalCo2Pct, Co2InclLucMt, Population)
                 VALUES (s.Country, s.Yr, s.Co2Mt, s.Co2PerCapitaT, s.ShareGlobalCo2Pct, s.Co2InclLucMt, s.Population);""",
    },
    {
        "name": "Forecast",
        "target": "climate.Forecast",
        "query": "SELECT city, metric, forecast_date, run_date, yhat, lower, upper, method FROM forecasts",
        "kinds": "ssddfffs",
        "stage": ("CREATE TABLE #stg (CityName nvarchar(60), Metric varchar(20), ForecastDate date, RunDate date, "
                  "Yhat decimal(9,2), LowerBound decimal(9,2), UpperBound decimal(9,2), Method varchar(30))"),
        "merge": """
            MERGE climate.Forecast AS t
            USING (SELECT c.CityId, s.* FROM #stg AS s JOIN climate.City AS c ON c.CityName = s.CityName) AS s
               ON t.CityId = s.CityId AND t.Metric = s.Metric AND t.ForecastDate = s.ForecastDate AND t.RunDate = s.RunDate
            WHEN MATCHED THEN UPDATE SET t.Yhat = s.Yhat, t.LowerBound = s.LowerBound,
                 t.UpperBound = s.UpperBound, t.Method = s.Method
            WHEN NOT MATCHED THEN INSERT (CityId, Metric, ForecastDate, RunDate, Yhat, LowerBound, UpperBound, Method)
                 VALUES (s.CityId, s.Metric, s.ForecastDate, s.RunDate, s.Yhat, s.LowerBound, s.UpperBound, s.Method);""",
    },
    {
        "name": "ForecastBacktest",
        "target": "climate.ForecastBacktest",
        "query": "SELECT city, metric, run_date, mae_model, mae_naive, folds, chosen_method FROM forecast_backtest",
        "kinds": "ssdffis",
        "stage": ("CREATE TABLE #stg (CityName nvarchar(60), Metric varchar(20), RunDate date, MaeModel decimal(9,3), "
                  "MaeNaive decimal(9,3), Folds tinyint, ChosenMethod varchar(30))"),
        "merge": """
            MERGE climate.ForecastBacktest AS t
            USING (SELECT c.CityId, s.* FROM #stg AS s JOIN climate.City AS c ON c.CityName = s.CityName) AS s
               ON t.CityId = s.CityId AND t.Metric = s.Metric AND t.RunDate = s.RunDate
            WHEN MATCHED THEN UPDATE SET t.MaeModel = s.MaeModel, t.MaeNaive = s.MaeNaive,
                 t.Folds = s.Folds, t.ChosenMethod = s.ChosenMethod
            WHEN NOT MATCHED THEN INSERT (CityId, Metric, RunDate, MaeModel, MaeNaive, Folds, ChosenMethod)
                 VALUES (s.CityId, s.Metric, s.RunDate, s.MaeModel, s.MaeNaive, s.Folds, s.ChosenMethod);""",
    },
]


def conv(v, kind):
    """pyodbc numpy types nahi samajhta, isliye har value ko plain python mein badalte hain."""
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    if kind == "s":
        return str(v)
    if kind == "f":
        return float(v)
    if kind == "i":
        return int(round(float(v)))
    if kind == "d":
        return pd.to_datetime(v).date()
    if kind == "t":
        return pd.to_datetime(v).to_pydatetime().replace(microsecond=0)
    raise ValueError(kind)


def read_rows(query, kinds):
    with get_conn() as lite:
        df = pd.read_sql_query(query, lite)
    assert len(df.columns) == len(kinds), f"{len(df.columns)} columns, {len(kinds)} kinds"
    return [tuple(conv(v, k) for v, k in zip(rec, kinds)) for rec in df.itertuples(index=False, name=None)]


def sync_table(conn, spec):
    rows = read_rows(spec["query"], spec["kinds"])
    cur = conn.cursor()
    cur.fast_executemany = True
    cur.execute(spec["stage"])
    if rows:
        placeholders = ",".join("?" * len(spec["kinds"]))
        cur.executemany(f"INSERT INTO #stg VALUES ({placeholders})", rows)
    cur.execute(spec["merge"])
    cur.execute("DROP TABLE #stg")
    total = cur.execute(f"SELECT COUNT(*) FROM {spec['target']}").fetchone()[0]
    conn.commit()
    print(f"OK   {spec['name']:<17} sent {len(rows):>5} rows | table now has {total}")


def main():
    conn = connect()
    try:
        for spec in TABLES:       # City pehle, kyunki baaki tables CityId use karti hain
            try:
                sync_table(conn, spec)
            except Exception:
                conn.rollback()
                print(f"FAIL {spec['name']}")
                raise
        row = conn.cursor().execute("SELECT LastFetchIst, AgeHours FROM rpt.DataFreshness").fetchone()
        if row:
            print(f"\nSQL Server mein latest data: {row[0]} IST ({row[1]} hours pehle)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()