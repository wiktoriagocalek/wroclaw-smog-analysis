-- View: smog_wroclaw.v_daily_averages
-- Średnie dobowe PM2.5 i NO₂ per stacja
-- Używane przez: Looker Studio (wykres trendów)

CREATE OR REPLACE VIEW `smog_wroclaw.v_daily_averages` AS
SELECT
  DATE(measured_at)                    AS date,
  station_id,
  parameter,
  ROUND(AVG(value), 2)                 AS avg_value,
  ROUND(MAX(value), 2)                 AS max_value,
  ROUND(MIN(value), 2)                 AS min_value,
  COUNT(*)                             AS n_measurements
FROM `smog_wroclaw.raw_measurements`
WHERE value IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 2, 3;
