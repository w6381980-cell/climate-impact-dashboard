-- Daily report queries. Har query "-- name: ..." line se shuru hoti hai.
-- Excel aur PDF dono yahi queries use karte hain.

-- name: latest_city
SELECT cities.city,
       COALESCE(ow.temperature_c, om.temperature_c) AS temp_c,
       COALESCE(ow.precipitation_mm, om.precipitation_mm) AS rain_mm,
       om.pm2_5 AS pm25_openmeteo,
       om.us_aqi AS us_aqi,
       om.aqi_category AS us_category,
       ow.pm2_5 AS pm25_openweather,
       ow.ow_aqi AS ow_aqi,
       ow.aqi_category AS ow_category
FROM (SELECT DISTINCT city FROM v_latest_readings) AS cities
LEFT JOIN v_latest_readings om ON om.city = cities.city AND om.source = 'open-meteo'
LEFT JOIN v_latest_readings ow ON ow.city = cities.city AND ow.source = 'openweather'
ORDER BY cities.city;

-- name: trend_14d
SELECT city, date, pm2_5_mean
FROM daily_air
WHERE date >= date((SELECT MAX(date) FROM daily_air), '-13 days')
ORDER BY date, city;

-- name: last7
SELECT city, avg_pm25_7d, max_pm25_7d, from_date, to_date
FROM v_air_last7
ORDER BY avg_pm25_7d DESC;

-- name: forecast_pm25
SELECT city, forecast_date, yhat, lower, upper, method
FROM forecasts
WHERE metric = 'pm2_5'
  AND run_date = (SELECT MAX(run_date) FROM forecasts)
ORDER BY city, forecast_date;

-- name: backtest
SELECT city, metric, mae_model, mae_naive, chosen_method
FROM forecast_backtest
WHERE run_date = (SELECT MAX(run_date) FROM forecast_backtest)
ORDER BY metric, city;

-- name: emissions
SELECT country, year, co2_mt, co2_per_capita_t
FROM emissions_country
WHERE year >= (SELECT MAX(year) FROM emissions_country) - 9
  AND country IN ('India', 'China', 'United States', 'World')
ORDER BY year, country;