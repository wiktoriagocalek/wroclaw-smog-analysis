-- View: smog_wroclaw.v_hourly_pattern
-- Profil godzinowy PM2.5 i NO₂ — identyfikuje szczyty komunikacyjne vs grzewcze
-- Używane przez: heatmapa godzina × stężenie w Looker Studio

CREATE OR REPLACE VIEW `smog_wroclaw.v_hourly_pattern` AS
SELECT
  hour_of_day,
  month,
  parameter,
  ROUND(AVG(value), 2)  AS avg_value,
  COUNT(*)              AS n_measurements,
  CASE
    WHEN month IN (11, 12, 1, 2) THEN 'winter'
    WHEN month IN (6, 7, 8)      THEN 'summer'
    ELSE 'transition'
  END                   AS season
FROM (
  SELECT
    EXTRACT(HOUR FROM measured_at)  AS hour_of_day,
    EXTRACT(MONTH FROM measured_at) AS month,
    parameter,
    value
  FROM `smog_wroclaw.raw_measurements`
  WHERE value IS NOT NULL
)
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
