-- View: smog_wroclaw.v_cigarette_equivalent
-- Ekwiwalent papierosowy per stacja per miesiąc
-- Formuła: 22 µg/m³ PM2.5 / 24h = 1 papieros (Brennan et al. 2015)
-- Używane przez: scorecard w Looker Studio

CREATE OR REPLACE VIEW `smog_wroclaw.v_cigarette_equivalent` AS
WITH daily_pm25 AS (
  SELECT
    DATE(measured_at)  AS date,
    station_id,
    AVG(value)         AS daily_avg_pm25
  FROM `smog_wroclaw.raw_measurements`
  WHERE parameter = 'PM2.5'
  GROUP BY 1, 2
)
SELECT
  FORMAT_DATE('%Y-%m', date)           AS month,
  station_id,
  ROUND(AVG(daily_avg_pm25), 2)        AS avg_pm25_ugm3,
  ROUND(AVG(daily_avg_pm25) / 22, 2)  AS cigarettes_per_day,
  COUNT(DISTINCT date)                 AS days_with_data
FROM daily_pm25
GROUP BY 1, 2
ORDER BY 1 DESC, cigarettes_per_day DESC;
