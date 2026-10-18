-- Seven-day holdout versus a same-weekday seasonal-naive baseline.
-- Runs against the warehouse, never against the forecast fixture chart.
-- Seed history is synthetic; these metrics cannot establish real business lift.
DECLARE evaluation_date DATE DEFAULT (
 SELECT MAX(txn_date) FROM `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions`
);
DECLARE cutoff_date DATE DEFAULT DATE_SUB(evaluation_date, INTERVAL 7 DAY);
CREATE OR REPLACE MODEL `${GCP_PROJECT}.${BQ_DATASET}.revenue_holdout_model`
OPTIONS(MODEL_TYPE='ARIMA_PLUS',TIME_SERIES_TIMESTAMP_COL='txn_date',
 TIME_SERIES_DATA_COL='revenue',TIME_SERIES_ID_COL='store_id',DATA_FREQUENCY='DAILY',
 HOLIDAY_REGION='IN',AUTO_ARIMA=TRUE) AS
SELECT store_id,txn_date,SUM(line_revenue) AS revenue
FROM `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions`
WHERE NOT is_return AND txn_date<=cutoff_date GROUP BY store_id,txn_date;

CREATE OR REPLACE TABLE `${GCP_PROJECT}.${BQ_DATASET}.forecast_evaluation` AS
WITH actuals AS (
 SELECT store_id,txn_date,SUM(line_revenue) AS revenue
 FROM `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions`
 WHERE NOT is_return GROUP BY store_id,txn_date
), predictions AS (
 SELECT store_id,DATE(forecast_timestamp) AS forecast_date,forecast_value,
 prediction_interval_lower_bound AS lower_bound,prediction_interval_upper_bound AS upper_bound
 FROM ML.FORECAST(MODEL `${GCP_PROJECT}.${BQ_DATASET}.revenue_holdout_model`,
 STRUCT(7 AS horizon,0.9 AS confidence_level))
)
SELECT p.store_id,cutoff_date AS trained_through,evaluation_date AS evaluated_through,
 COUNT(*) AS observations,AVG(ABS(a.revenue-p.forecast_value)) AS mae,
 SAFE_DIVIDE(SUM(ABS(a.revenue-p.forecast_value)),SUM(ABS(a.revenue))) AS wape,
 AVG(ABS(a.revenue-b.revenue)) AS seasonal_naive_mae,
 SAFE_DIVIDE(SUM(ABS(a.revenue-b.revenue)),SUM(ABS(a.revenue))) AS seasonal_naive_wape,
 AVG(CAST(a.revenue BETWEEN p.lower_bound AND p.upper_bound AS INT64)) AS interval_coverage,
 CURRENT_TIMESTAMP() AS evaluated_at
FROM predictions p JOIN actuals a ON a.store_id=p.store_id AND a.txn_date=p.forecast_date
JOIN actuals b ON b.store_id=p.store_id AND b.txn_date=DATE_SUB(p.forecast_date,INTERVAL 7 DAY)
WHERE p.forecast_date>cutoff_date AND p.forecast_date<=evaluation_date
GROUP BY p.store_id;
SELECT * FROM `${GCP_PROJECT}.${BQ_DATASET}.forecast_evaluation`;
