-- CREATE TABLE IF NOT EXISTS live_readings (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     city TEXT NOT NULL,
--     lat REAL,
--     lon REAL,
--     weather_time_utc TEXT,
--     air_time_utc TEXT,
--     temperature_c REAL,
--     precipitation_mm REAL,
--     pm2_5 REAL,
--     pm10 REAL,
--     us_aqi INTEGER,
--     source TEXT,
--     fetched_at_utc TEXT,
--     ow_aqi INTEGER,
--     UNIQUE (city, weather_time_utc, air_time_utc, source)
-- );

-- CREATE TABLE IF NOT EXISTS daily_weather (
--     city TEXT NOT NULL,
--     date TEXT NOT NULL,
--     temp_mean_c REAL,
--     temp_max_c REAL,
--     temp_min_c REAL,
--     precip_mm REAL,
--     PRIMARY KEY (city, date)
-- );

-- CREATE TABLE IF NOT EXISTS daily_air (
--     city TEXT NOT NULL,
--     date TEXT NOT NULL,
--     pm2_5_mean REAL,
--     pm10_mean REAL,
--     us_aqi_mean REAL,
--     hours_count INTEGER,
--     PRIMARY KEY (city, date)
-- );


-- CREATE TABLE IF NOT EXISTS emissions_country (
--     country TEXT NOT NULL,
--     year INTEGER NOT NULL,
--     co2_mt REAL,
--     co2_per_capita_t REAL,
--     share_global_co2_pct REAL,
--     co2_incl_luc_mt REAL,
--     population REAL,
--     PRIMARY KEY (country, year)
-- );

drop view if exists v_latest_readings;
create view v_latest_readings as
   select city,
          source,
          datetime(
             weather_time_utc,
             '+330 minutes'
          ) as weather_time_ist,
          temperature_c,
          precipitation_mm,
          pm2_5,
          pm10,
          us_aqi,
          ow_aqi,
          case
             when us_aqi is not null then
                   case
                      when us_aqi <= 50  then
                         'Good'
                      when us_aqi <= 100 then
                         'Moderate'
                      when us_aqi <= 150 then
                         'Unhealthy for Sensitive Groups'
                      when us_aqi <= 200 then
                         'Unhealthy'
                      when us_aqi <= 300 then
                         'Very Unhealthy'
                      else
                         'Hazardous'
                   end
             when ow_aqi is not null then
                   case ow_aqi
                      when 1 then
                         'Good'
                      when 2 then
                         'Fair'
                      when 3 then
                         'Moderate'
                      when 4 then
                         'Poor'
                      else
                         'Very Poor'
                   end
          end as aqi_category
     from (
      select *,
             row_number()
             over(partition by city,
                               source
                  order by air_time_utc desc,
                           weather_time_utc desc
             ) as rn
        from live_readings
   )
    where rn = 1;

drop view if exists v_air_last7;
create view v_air_last7 as
   select city,
          round(
             avg(pm2_5_mean),
             1
          ) as avg_pm25_7d,
          round(
             max(pm2_5_mean),
             1
          ) as max_pm25_7d,
          min(date) as from_date,
          max(date) as to_date
     from daily_air
    where date >= date(
      (
         select max(date)
           from daily_air
      ),
      '-6 days'
   )
    group by city;


create table if not exists forecasts (
   city          text not null,
   metric        text not null,
   forecast_date text not null,
   run_date      text not null,
   yhat          real,
   lower         real,
   upper         real,
   method        text,
      primary key ( city,
                    metric,
                    forecast_date,
                    run_date )
);

create table if not exists forecast_backtest (
   city          text not null,
   metric        text not null,
   run_date      text not null,
   mae_model     real,
   mae_naive     real,
   folds         integer,
   chosen_method text,
   primary key ( city,
                 metric,
                 run_date )
);