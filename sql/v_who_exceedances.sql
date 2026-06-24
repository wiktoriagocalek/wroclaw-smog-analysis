-- View: smog_wroclaw.v_who_exceedances
-- Dni przekraczające normy WHO — gotowe do wyróżnienia w Looker Studio

CREATE OR REPLACE VIEW `smog_wroclaw.v_who_exceedances` AS
WITH who_limits AS (
  SELECT 'PM2.5' AS parameter, 15.0 AS daily_limit UNION ALL
  SELECT 'NO2',                 25.0               UNION ALL
  SELECT 'PM10',                45.0
),
daily AS (
  SELECT
    DATE(measured_at)  AS date,
    station_id,
    parameter,
    AVG(value)         AS daily_avg
  FROM `smog_wroclaw.raw_measurements`
  GROUP BY 1, 2, 3
)
SELECT
  d.date,
  d.station_id,
  d.parameter,
  ROUND(d.daily_avg, 2)                        AS daily_avg_ugm3,
  w.daily_limit                                AS who_limit_ugm3,
  ROUND(d.daily_avg / w.daily_limit, 2)        AS ratio_to_who,
  CASE
    WHEN d.daily_avg / w.daily_limit >= 2 THEN 'critical'
    WHEN d.daily_avg / w.daily_limit >= 1.5 THEN 'high'
    ELSE 'moderate'
  END                                          AS severity
FROM daily d
JOIN who_limits w ON d.parameter = w.parameter
WHERE d.daily_avg > w.daily_limit
ORDER BY d.date DESC, ratio_to_who DESC;
