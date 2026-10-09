-- Step 1: database banao (agar pehle se nahi hai)
IF DB_ID(N'ClimateImpact') IS NULL
    CREATE DATABASE ClimateImpact;
GO


-- Step 2: schemas aur tables. Dobara chalane par kuch nahi bigadta (idempotent).
USE ClimateImpact;
GO

IF SCHEMA_ID(N'climate') IS NULL EXEC (N'CREATE SCHEMA climate');
GO
IF SCHEMA_ID(N'rpt') IS NULL EXEC (N'CREATE SCHEMA rpt');
GO

-- Dimension: cities
IF OBJECT_ID(N'climate.City', N'U') IS NULL
CREATE TABLE climate.City (
    CityId     int IDENTITY(1,1) NOT NULL CONSTRAINT PK_City PRIMARY KEY,
    CityName   nvarchar(60) NOT NULL CONSTRAINT UQ_City_Name UNIQUE,
    Latitude   decimal(9,4) NULL,
    Longitude  decimal(9,4) NULL
);
GO

-- Fact: live readings (har run par har city ki 2 rows: Open-Meteo aur OpenWeather)
IF OBJECT_ID(N'climate.LiveReading', N'U') IS NULL
CREATE TABLE climate.LiveReading (
    ReadingId        bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_LiveReading PRIMARY KEY,
    CityId           int NOT NULL CONSTRAINT FK_LiveReading_City REFERENCES climate.City (CityId),
    Source           varchar(20) NOT NULL,
    WeatherTimeUtc   datetime2(0) NOT NULL,
    AirTimeUtc       datetime2(0) NOT NULL,
    TemperatureC     decimal(5,2) NULL,
    PrecipitationMm  decimal(7,2) NULL,
    Pm25             decimal(7,2) NULL,
    Pm10             decimal(7,2) NULL,
    UsAqi            smallint NULL,
    OwAqi            tinyint NULL,
    FetchedAtUtc     datetime2(0) NULL,
    CONSTRAINT UQ_LiveReading UNIQUE (CityId, Source, WeatherTimeUtc, AirTimeUtc)
);
GO

-- Fact: daily weather (Open-Meteo archive)
IF OBJECT_ID(N'climate.DailyWeather', N'U') IS NULL
CREATE TABLE climate.DailyWeather (
    CityId        int NOT NULL CONSTRAINT FK_DailyWeather_City REFERENCES climate.City (CityId),
    WeatherDate   date NOT NULL,
    TempMeanC     decimal(5,2) NULL,
    TempMaxC      decimal(5,2) NULL,
    TempMinC      decimal(5,2) NULL,
    PrecipMm      decimal(7,2) NULL,
    CONSTRAINT PK_DailyWeather PRIMARY KEY (CityId, WeatherDate)
);
GO

-- Fact: daily air quality (hourly data ka daily average)
IF OBJECT_ID(N'climate.DailyAir', N'U') IS NULL
CREATE TABLE climate.DailyAir (
    CityId       int NOT NULL CONSTRAINT FK_DailyAir_City REFERENCES climate.City (CityId),
    AirDate      date NOT NULL,
    Pm25Mean     decimal(7,2) NULL,
    Pm10Mean     decimal(7,2) NULL,
    UsAqiMean    decimal(6,1) NULL,
    HoursCount   smallint NULL,
    CONSTRAINT PK_DailyAir PRIMARY KEY (CityId, AirDate)
);
GO

-- Fact: annual emissions (country level, Our World in Data)
IF OBJECT_ID(N'climate.EmissionsCountry', N'U') IS NULL
CREATE TABLE climate.EmissionsCountry (
    Country            nvarchar(60) NOT NULL,
    [Year]             smallint NOT NULL,
    Co2Mt              decimal(12,3) NULL,
    Co2PerCapitaT      decimal(8,3) NULL,
    ShareGlobalCo2Pct  decimal(8,4) NULL,
    Co2InclLucMt       decimal(12,3) NULL,
    Population         bigint NULL,
    CONSTRAINT PK_EmissionsCountry PRIMARY KEY (Country, [Year])
);
GO

-- Forecasts (har run ki date ke saath, taaki purane forecasts bhi bache rahein)
IF OBJECT_ID(N'climate.Forecast', N'U') IS NULL
CREATE TABLE climate.Forecast (
    CityId        int NOT NULL CONSTRAINT FK_Forecast_City REFERENCES climate.City (CityId),
    Metric        varchar(20) NOT NULL,
    ForecastDate  date NOT NULL,
    RunDate       date NOT NULL,
    Yhat          decimal(9,2) NULL,
    LowerBound    decimal(9,2) NULL,
    UpperBound    decimal(9,2) NULL,
    Method        varchar(30) NULL,
    CONSTRAINT PK_Forecast PRIMARY KEY (CityId, Metric, ForecastDate, RunDate)
);
GO

IF OBJECT_ID(N'climate.ForecastBacktest', N'U') IS NULL
CREATE TABLE climate.ForecastBacktest (
    CityId         int NOT NULL CONSTRAINT FK_ForecastBacktest_City REFERENCES climate.City (CityId),
    Metric         varchar(20) NOT NULL,
    RunDate        date NOT NULL,
    MaeModel       decimal(9,3) NULL,
    MaeNaive       decimal(9,3) NULL,
    Folds          tinyint NULL,
    ChosenMethod   varchar(30) NULL,
    CONSTRAINT PK_ForecastBacktest PRIMARY KEY (CityId, Metric, RunDate)
);
GO

-- Dimension: calendar (Power BI ke time charts ke liye). Language/DATEFIRST par depend nahi karta.
IF OBJECT_ID(N'climate.DimDate', N'U') IS NULL
BEGIN
    CREATE TABLE climate.DimDate (
        DateKey      date NOT NULL CONSTRAINT PK_DimDate PRIMARY KEY,
        [Year]       smallint NOT NULL,
        MonthNo      tinyint NOT NULL,
        MonthName    varchar(10) NOT NULL,
        YearMonth    char(7) NOT NULL,
        DayNo        tinyint NOT NULL,
        WeekdayNo    tinyint NOT NULL,   -- 0 = Sunday ... 6 = Saturday
        WeekdayName  varchar(10) NOT NULL,
        IsWeekend    bit NOT NULL
    );

    ;WITH d AS (
        SELECT CAST('2024-01-01' AS date) AS dt
        UNION ALL
        SELECT DATEADD(day, 1, dt) FROM d WHERE dt < '2030-12-31'
    )
    INSERT INTO climate.DimDate (DateKey, [Year], MonthNo, MonthName, YearMonth, DayNo, WeekdayNo, WeekdayName, IsWeekend)
    SELECT dt,
           YEAR(dt),
           MONTH(dt),
           CHOOSE(MONTH(dt), 'January','February','March','April','May','June','July','August','September','October','November','December'),
           CONVERT(char(7), dt, 126),
           DAY(dt),
           DATEDIFF(day, '19000107', dt) % 7,
           CHOOSE(DATEDIFF(day, '19000107', dt) % 7 + 1, 'Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'),
           CASE WHEN DATEDIFF(day, '19000107', dt) % 7 IN (0, 6) THEN 1 ELSE 0 END
    FROM d
    OPTION (MAXRECURSION 3000);
END
GO

-- Step 3: report views (schema rpt). Power BI inhi views se data lega.
USE ClimateImpact;
GO

CREATE OR ALTER VIEW rpt.LatestReading AS
WITH ranked AS (
    SELECT lr.CityId, lr.Source, lr.WeatherTimeUtc, lr.TemperatureC, lr.PrecipitationMm,
           lr.Pm25, lr.Pm10, lr.UsAqi, lr.OwAqi,
           ROW_NUMBER() OVER (PARTITION BY lr.CityId, lr.Source
                              ORDER BY lr.AirTimeUtc DESC, lr.WeatherTimeUtc DESC) AS rn
    FROM climate.LiveReading AS lr
)
SELECT c.CityName,
       r.Source,
       DATEADD(minute, 330, r.WeatherTimeUtc) AS WeatherTimeIst,
       r.TemperatureC,
       r.PrecipitationMm,
       r.Pm25,
       r.Pm10,
       r.UsAqi,
       r.OwAqi,
       CASE
           WHEN r.UsAqi IS NOT NULL THEN
               CASE WHEN r.UsAqi <= 50  THEN 'Good'
                    WHEN r.UsAqi <= 100 THEN 'Moderate'
                    WHEN r.UsAqi <= 150 THEN 'Unhealthy for Sensitive Groups'
                    WHEN r.UsAqi <= 200 THEN 'Unhealthy'
                    WHEN r.UsAqi <= 300 THEN 'Very Unhealthy'
                    ELSE 'Hazardous' END
           WHEN r.OwAqi IS NOT NULL THEN
               CASE r.OwAqi WHEN 1 THEN 'Good' WHEN 2 THEN 'Fair' WHEN 3 THEN 'Moderate'
                            WHEN 4 THEN 'Poor' ELSE 'Very Poor' END
       END AS AqiCategory
FROM ranked AS r
JOIN climate.City AS c ON c.CityId = r.CityId
WHERE r.rn = 1;
GO

-- Ek city = ek row (dono sources side by side). Power BI ka main "now" table.
CREATE OR ALTER VIEW rpt.CityNow AS
SELECT c.CityName,
       c.Latitude,
       c.Longitude,
       COALESCE(ow.TemperatureC, om.TemperatureC)       AS TemperatureC,
       COALESCE(ow.PrecipitationMm, om.PrecipitationMm) AS RainMm,
       om.Pm25                                          AS Pm25OpenMeteo,
       om.UsAqi                                         AS UsAqi,
       om.AqiCategory                                   AS UsAqiCategory,
       CASE WHEN om.UsAqi IS NULL THEN NULL
            WHEN om.UsAqi <= 50  THEN 1
            WHEN om.UsAqi <= 100 THEN 2
            WHEN om.UsAqi <= 150 THEN 3
            WHEN om.UsAqi <= 200 THEN 4
            WHEN om.UsAqi <= 300 THEN 5
            ELSE 6 END                                  AS UsAqiBandNo,
       CASE WHEN om.UsAqi > 150 THEN 1 ELSE 0 END       AS IsUnhealthy,
       ow.Pm25                                          AS Pm25OpenWeather,
       ow.OwAqi                                         AS OwAqi,
       ow.AqiCategory                                   AS OwAqiCategory,
       om.WeatherTimeIst                                AS OpenMeteoTimeIst,
       ow.WeatherTimeIst                                AS OpenWeatherTimeIst
FROM climate.City AS c
LEFT JOIN rpt.LatestReading AS om ON om.CityName = c.CityName AND om.Source = 'open-meteo'
LEFT JOIN rpt.LatestReading AS ow ON ow.CityName = c.CityName AND ow.Source = 'openweather';
GO

-- Har live run ki history (pipeline roz chalegi toh ye table badhti jayegi)
CREATE OR ALTER VIEW rpt.LiveHistory AS
SELECT c.CityName,
       lr.Source,
       DATEADD(minute, 330, lr.WeatherTimeUtc) AS ReadingTimeIst,
       CAST(DATEADD(minute, 330, lr.WeatherTimeUtc) AS date) AS ReadingDate,
       lr.TemperatureC,
       lr.PrecipitationMm,
       lr.Pm25,
       lr.Pm10,
       lr.UsAqi,
       lr.OwAqi
FROM climate.LiveReading AS lr
JOIN climate.City AS c ON c.CityId = lr.CityId;
GO

CREATE OR ALTER VIEW rpt.DailyWeather AS
SELECT c.CityName, w.WeatherDate, w.TempMeanC, w.TempMaxC, w.TempMinC, w.PrecipMm
FROM climate.DailyWeather AS w
JOIN climate.City AS c ON c.CityId = w.CityId;
GO

CREATE OR ALTER VIEW rpt.DailyAir AS
SELECT c.CityName, a.AirDate, a.Pm25Mean, a.Pm10Mean, a.UsAqiMean, a.HoursCount
FROM climate.DailyAir AS a
JOIN climate.City AS c ON c.CityId = a.CityId;
GO

CREATE OR ALTER VIEW rpt.Air7Day AS
SELECT c.CityName,
       CAST(AVG(a.Pm25Mean) AS decimal(7,1)) AS AvgPm25_7d,
       CAST(MAX(a.Pm25Mean) AS decimal(7,1)) AS MaxPm25_7d,
       MIN(a.AirDate) AS FromDate,
       MAX(a.AirDate) AS ToDate
FROM climate.DailyAir AS a
JOIN climate.City AS c ON c.CityId = a.CityId
WHERE a.AirDate >= DATEADD(day, -6, (SELECT MAX(AirDate) FROM climate.DailyAir))
GROUP BY c.CityName;
GO

CREATE OR ALTER VIEW rpt.ForecastLatest AS
SELECT c.CityName, f.Metric, f.ForecastDate, f.Yhat, f.LowerBound, f.UpperBound, f.Method, f.RunDate
FROM climate.Forecast AS f
JOIN climate.City AS c ON c.CityId = f.CityId
WHERE f.RunDate = (SELECT MAX(RunDate) FROM climate.Forecast);
GO

CREATE OR ALTER VIEW rpt.BacktestLatest AS
SELECT c.CityName, b.Metric, b.MaeModel, b.MaeNaive, b.ChosenMethod, b.Folds, b.RunDate,
       CASE WHEN b.MaeModel < b.MaeNaive THEN 1 ELSE 0 END AS ModelBeatBaseline
FROM climate.ForecastBacktest AS b
JOIN climate.City AS c ON c.CityId = b.CityId
WHERE b.RunDate = (SELECT MAX(RunDate) FROM climate.ForecastBacktest);
GO

CREATE OR ALTER VIEW rpt.Emissions AS
SELECT e.Country,
       e.[Year],
       e.Co2Mt,
       e.Co2PerCapitaT,
       e.ShareGlobalCo2Pct,
       e.Co2InclLucMt,
       e.Population,
       CAST(e.Co2Mt / NULLIF(LAG(e.Co2Mt) OVER (PARTITION BY e.Country ORDER BY e.[Year]), 0) - 1 AS decimal(9,4)) AS Co2YoY
FROM climate.EmissionsCountry AS e;
GO

-- Data kitna purana hai (Power BI mein "Data freshness" card ke liye)
CREATE OR ALTER VIEW rpt.DataFreshness AS
SELECT MAX(FetchedAtUtc)                               AS LastFetchUtc,
       DATEADD(minute, 330, MAX(FetchedAtUtc))         AS LastFetchIst,
       DATEDIFF(hour, MAX(FetchedAtUtc), SYSUTCDATETIME()) AS AgeHours
FROM climate.LiveReading;
GO


-- Step 4: SQL Server mein daily report (stored procedure). SSMS mein: EXEC rpt.usp_DailyReport;
USE ClimateImpact;
GO

CREATE OR ALTER PROCEDURE rpt.usp_DailyReport
AS
BEGIN
    SET NOCOUNT ON;

    -- Result 1: headline numbers
    SELECT CAST(AVG(TemperatureC) AS decimal(5,1)) AS AvgTempC,
           MAX(TemperatureC)                       AS MaxTempC,
           MAX(Pm25OpenMeteo)                      AS MaxPm25,
           SUM(IsUnhealthy)                        AS CitiesAboveAqi150,
           COUNT(*)                                AS CityCount
    FROM rpt.CityNow;

    -- Result 2: har city ka abhi ka haal (sabse polluted pehle)
    SELECT CityName, TemperatureC, RainMm, Pm25OpenMeteo, UsAqi, UsAqiCategory,
           Pm25OpenWeather, OwAqi, OwAqiCategory
    FROM rpt.CityNow
    ORDER BY Pm25OpenMeteo DESC;

    -- Result 3: pichle 7 din ka PM2.5
    SELECT CityName, AvgPm25_7d, MaxPm25_7d, FromDate, ToDate
    FROM rpt.Air7Day
    ORDER BY AvgPm25_7d DESC;

    -- Result 4: agle 7 din ka PM2.5 forecast (statistical, guarantee nahi)
    SELECT CityName,
           CAST(AVG(Yhat) AS decimal(7,1)) AS AvgForecastPm25,
           MIN(LowerBound)                 AS LowPm25,
           MAX(UpperBound)                 AS HighPm25,
           MAX(Method)                     AS Method
    FROM rpt.ForecastLatest
    WHERE Metric = 'pm2_5'
    GROUP BY CityName
    ORDER BY AvgForecastPm25 DESC;
END;
GO

-- Step 5 (optional): SSMS mein khud chalane wali report queries. Har query alag se chalao.
USE ClimateImpact;
GO

-- 1) Pichle 7 din mein kaun si city sabse polluted thi (rank ke saath)
SELECT CityName, AvgPm25_7d, MaxPm25_7d,
       RANK() OVER (ORDER BY AvgPm25_7d DESC) AS PollutionRank
FROM rpt.Air7Day
ORDER BY PollutionRank;

-- 2) Kitne din PM2.5 60 ug/m3 se upar raha (India ki 24-ghante ki limit), % ke saath
SELECT CityName,
       COUNT(*)                                               AS DaysWithData,
       SUM(CASE WHEN Pm25Mean > 60 THEN 1 ELSE 0 END)         AS DaysAbove60,
       CAST(100.0 * SUM(CASE WHEN Pm25Mean > 60 THEN 1 ELSE 0 END) / COUNT(*) AS decimal(5,1)) AS PctDaysAbove60
FROM rpt.DailyAir
GROUP BY CityName
ORDER BY PctDaysAbove60 DESC;

-- 3) Monthly rainfall (mm) city-wise
SELECT CityName,
       DATEFROMPARTS(YEAR(WeatherDate), MONTH(WeatherDate), 1) AS MonthStart,
       CAST(SUM(PrecipMm) AS decimal(9,1))                     AS RainMm,
       COUNT(*)                                                AS DaysInData
FROM rpt.DailyWeather
GROUP BY CityName, DATEFROMPARTS(YEAR(WeatherDate), MONTH(WeatherDate), 1)
ORDER BY CityName, MonthStart;

-- 4) India CO2: saal-dar-saal badlav
SELECT [Year], Co2Mt, CAST(Co2YoY * 100 AS decimal(6,2)) AS YoYPercent
FROM rpt.Emissions
WHERE Country = 'India' AND [Year] >= 2015
ORDER BY [Year];

-- 5) Forecast model ne baseline ko kahan haraya
SELECT Metric,
       SUM(ModelBeatBaseline) AS CitiesWhereModelWon,
       COUNT(*)               AS TotalCities
FROM rpt.BacktestLatest
GROUP BY Metric;

-- 6) Data kitna taaza hai
SELECT * FROM rpt.DataFreshness;


