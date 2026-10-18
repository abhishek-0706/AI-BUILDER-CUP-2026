-- RetailIQ - demand forecasting with BigQuery ML ARIMA_PLUS
--
-- Two models, because the dashboard and the replenishment engine ask different
-- questions:
--   1. store_revenue_forecast   one series per store, daily revenue. Drives the
--                               "7-day demand forecast" chart.
--   2. product_demand_forecast  one series per store x product, daily units.
--                               Drives recommended order quantities.
--
-- ARIMA_PLUS handles the weekly seasonality and the Indian holiday calendar
-- itself, so there is no manual feature engineering here.
--
-- Placeholders ${GCP_PROJECT} and ${BQ_DATASET} are substituted by deploy.sh.
--
-- Run:  envsubst < forecast.sql | bq query --use_legacy_sql=false
-- Cost note: retraining reads the full history partition range. Schedule it
-- daily, not per request; the API only reads demand_forecast_daily.


-- ---------------------------------------------------------------------------
-- 1. Training input: daily revenue per store.
--    Gaps are left as gaps. ARIMA_PLUS imputes missing days (DATA_FREQUENCY
--    plus its own cleanup), which is more honest than writing zeros for days
--    the store was shut.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW `${GCP_PROJECT}.${BQ_DATASET}.v_daily_store_revenue` AS
SELECT
  store_id,
  txn_date,
  SUM(line_revenue) AS revenue
FROM `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions`
WHERE NOT is_return
GROUP BY store_id, txn_date;


CREATE OR REPLACE VIEW `${GCP_PROJECT}.${BQ_DATASET}.v_daily_product_units` AS
SELECT
  CONCAT(store_id, '|', product_id) AS series_id,
  store_id,
  product_id,
  txn_date,
  SUM(quantity) AS units
FROM `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions`
WHERE NOT is_return
GROUP BY store_id, product_id, txn_date;


-- ---------------------------------------------------------------------------
-- 2. Store revenue model.
--    AUTO_ARIMA searches the (p, d, q) space; HOLIDAY_REGION='IN' adds Indian
--    public holidays, which matter a lot for grocery weekend peaks.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE MODEL `${GCP_PROJECT}.${BQ_DATASET}.store_revenue_forecast`
OPTIONS (
  MODEL_TYPE            = 'ARIMA_PLUS',
  TIME_SERIES_TIMESTAMP_COL = 'txn_date',
  TIME_SERIES_DATA_COL  = 'revenue',
  TIME_SERIES_ID_COL    = 'store_id',
  DATA_FREQUENCY        = 'DAILY',
  HOLIDAY_REGION        = 'IN',
  AUTO_ARIMA            = TRUE,
  -- Trims one-off spikes (a bulk institutional order, a system outage) so they
  -- do not become a seasonal pattern.
  CLEAN_SPIKES_AND_DIPS = TRUE,
  ADJUST_STEP_CHANGES   = TRUE,
  DECOMPOSE_TIME_SERIES = TRUE
) AS
SELECT store_id, txn_date, revenue
FROM `${GCP_PROJECT}.${BQ_DATASET}.v_daily_store_revenue`;


-- ---------------------------------------------------------------------------
-- 3. Per-SKU unit demand model.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE MODEL `${GCP_PROJECT}.${BQ_DATASET}.product_demand_forecast`
OPTIONS (
  MODEL_TYPE            = 'ARIMA_PLUS',
  TIME_SERIES_TIMESTAMP_COL = 'txn_date',
  TIME_SERIES_DATA_COL  = 'units',
  TIME_SERIES_ID_COL    = 'series_id',
  DATA_FREQUENCY        = 'DAILY',
  HOLIDAY_REGION        = 'IN',
  AUTO_ARIMA            = TRUE,
  CLEAN_SPIKES_AND_DIPS = TRUE,
  -- Cap the AUTO_ARIMA search per series; there are many low-volume SKUs and
  -- the default search is not worth the slot time on them.
  MAX_TIME_SERIES_LENGTH = 365
) AS
SELECT series_id, txn_date, units
FROM `${GCP_PROJECT}.${BQ_DATASET}.v_daily_product_units`;


-- ---------------------------------------------------------------------------
-- 4. Materialise the 7-day store revenue forecast at 90 percent confidence.
--    Shape matches the `forecast` array the front end renders:
--    day, predicted, lower, upper.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.demand_forecast_daily` (
  store_id          STRING  NOT NULL,
  forecast_date     DATE    NOT NULL,
  day_label         STRING,
  predicted_revenue FLOAT64,
  lower_bound       FLOAT64,
  upper_bound       FLOAT64,
  confidence_level  FLOAT64,
  -- Kept so a stale forecast is visible as stale rather than silently served.
  model_run_at      TIMESTAMP,
  model_name        STRING
)
PARTITION BY forecast_date
CLUSTER BY store_id;


-- Existing deployments may have the original seven-column table.
ALTER TABLE `${GCP_PROJECT}.${BQ_DATASET}.demand_forecast_daily` ADD COLUMN IF NOT EXISTS day_label STRING;
ALTER TABLE `${GCP_PROJECT}.${BQ_DATASET}.demand_forecast_daily` ADD COLUMN IF NOT EXISTS model_name STRING;

-- Replace only this run's horizon; history of past runs is retained.
DELETE FROM `${GCP_PROJECT}.${BQ_DATASET}.demand_forecast_daily`
WHERE forecast_date >= CURRENT_DATE()
  AND DATE(model_run_at) = CURRENT_DATE();

INSERT INTO `${GCP_PROJECT}.${BQ_DATASET}.demand_forecast_daily`
  (store_id, forecast_date, day_label, predicted_revenue, lower_bound, upper_bound,
   confidence_level, model_run_at, model_name)
SELECT
  store_id,
  DATE(forecast_timestamp)                          AS forecast_date,
  FORMAT_DATE('%a', DATE(forecast_timestamp))       AS day_label,
  CAST(GREATEST(forecast_value, 0) AS NUMERIC)      AS predicted_revenue,
  CAST(GREATEST(prediction_interval_lower_bound, 0) AS NUMERIC) AS lower_bound,
  CAST(prediction_interval_upper_bound AS NUMERIC)  AS upper_bound,
  CAST(confidence_level AS NUMERIC)                 AS confidence_level,
  CURRENT_TIMESTAMP()                               AS model_run_at,
  'store_revenue_forecast'                          AS model_name
FROM ML.FORECAST(
  MODEL `${GCP_PROJECT}.${BQ_DATASET}.store_revenue_forecast`,
  STRUCT(7 AS horizon, 0.9 AS confidence_level)
);


-- ---------------------------------------------------------------------------
-- 5. Materialise the per-SKU unit forecast used for reorder sizing.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE `${GCP_PROJECT}.${BQ_DATASET}.product_forecast_daily`
PARTITION BY forecast_date
CLUSTER BY store_id, product_id
AS
SELECT
  SPLIT(series_id, '|')[OFFSET(0)]                  AS store_id,
  SPLIT(series_id, '|')[OFFSET(1)]                  AS product_id,
  DATE(forecast_timestamp)                          AS forecast_date,
  GREATEST(forecast_value, 0)                       AS predicted_units,
  GREATEST(prediction_interval_lower_bound, 0)      AS lower_bound,
  prediction_interval_upper_bound                   AS upper_bound,
  confidence_level,
  CURRENT_TIMESTAMP()                               AS model_run_at
FROM ML.FORECAST(
  MODEL `${GCP_PROJECT}.${BQ_DATASET}.product_demand_forecast`,
  STRUCT(14 AS horizon, 0.9 AS confidence_level)
);


-- ---------------------------------------------------------------------------
-- 6. Model quality, for the record. ARIMA_PLUS reports AIC and the fitted
--    (p, d, q) per series; ML.EVALUATE without a horizon returns those rather
--    than a holdout error, so track it over time to catch drift.
-- ---------------------------------------------------------------------------
-- SELECT store_id, non_seasonal_p, non_seasonal_d, non_seasonal_q,
--        has_drift, log_likelihood, AIC, variance
-- FROM ML.EVALUATE(MODEL `${GCP_PROJECT}.${BQ_DATASET}.store_revenue_forecast`)
-- ORDER BY store_id;
