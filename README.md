# Climate Impact Dashboard

Live weather, air quality, forecasts and CO2 context for 10 Indian cities, refreshed automatically three times a day.

**Live demo:** https://YOUR-APP-NAME.streamlit.app <!-- replace after deploying -->

## What it shows

- Temperature now (flip counter), US AQI gauge, 7-day PM2.5 outlook for the selected city
- City-specific KPIs: temperature vs average of all cities, PM2.5 rank, 7-day average
- Rainfall by month, PM2.5 trend, ranking of all cities
- Forecast tab with an honest backtest (the model must beat a simple baseline to be used)
- Annual CO2 emissions for India, China, USA and the world (country level, not live)
- Excel MIS report and PDF report, generated automatically from the latest data
- Light and dark theme, works on laptop and phone

## How it works

```
Open-Meteo + OpenWeather + Our World in Data
              |
   GitHub Actions (06:00, 12:00, 18:00 IST)
   collect -> clean -> forecast -> data/climate.db (SQLite)
              |  commit
        GitHub repository
              |  auto-update
   Streamlit Community Cloud  ->  dashboard/app.py
              (reads the database read-only, builds Excel/PDF on demand)

Optional, on a local PC: run_daily.bat -> SQL Server (ClimateImpact) -> Power BI
```

## Data sources

| Data                     | Source                         | Note                                   |
| ------------------------ | ------------------------------ | -------------------------------------- |
| Live temperature, rain   | OpenWeather, Open-Meteo        | free API                               |
| Air quality (PM2.5, AQI) | Open-Meteo (CAMS), OpenWeather | modelled estimates, not ground sensors |
| Daily weather history    | Open-Meteo archive (ERA5)      | about 7 days behind                    |
| CO2 emissions            | Our World in Data              | annual, country level                  |

## Limits (on purpose, stated openly)

- Air quality values are model estimates. The two sources use different AQI scales (US 0-500, OpenWeather 1-5).
- PM2.5 history is about 90 days, so forecasts are short-term trends and cannot predict seasonal smog spikes.
- Forecasts are compared with a baseline (last 7-day average); where the baseline wins, the baseline is shown.

## Run locally

```
pip install -r requirements-pipeline.txt -r requirements.txt
# put OPENWEATHER_API_KEY=... in a .env file
python src/run_daily.py
python -m streamlit run dashboard/app.py
```

## Optional: SQL Server and Power BI

`sql/mssql/` has the T-SQL scripts (database, tables, report views, daily report procedure).
`python src/mssql_setup.py` creates them, `python src/mssql_sync.py` loads the data.
Set `MSSQL_ENABLED=1` in `.env` and `run_daily.py` syncs automatically.

## Project layout

```
src/        data pipeline (collect, clean, forecast, SQL Server sync)
dashboard/  Streamlit app
reports/    Excel MIS and PDF generators
sql/        report queries (SQLite) and T-SQL scripts (SQL Server)
.github/    scheduled refresh workflow
```
