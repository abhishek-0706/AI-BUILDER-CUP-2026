-- RetailIQ - dashboard analytics queries
--
-- One labelled block per dashboard widget. main.py reads this file and splits
-- it on the "-- name:" markers, so this file is the single source of truth for
-- what every number on the screen means.
--
-- Placeholders ${GCP_PROJECT} and ${BQ_DATASET} are substituted by deploy.sh
-- before the file is baked into the container image.
--
-- Query parameters (named, never string-interpolated):
--   @store_id    STRING  store to report on
--   @as_of_date  DATE    the "today" of the report, so demos are reproducible
--   @limit       INT64   row cap for list widgets
--   @query       STRING  free text, RAG only
--   @top_k       INT64   result count, RAG only


-- ===========================================================================
-- name: revenue_week
-- Widget: "Revenue, last 7 days" bar chart.
-- Grain out: one row per day. Returns fewer than 7 rows if a day had no sales,
-- which the API surfaces as-is rather than back-filling zeros.
-- ===========================================================================
SELECT
  FORMAT_DATE('%a', txn_date)                  AS day,
  txn_date                                     AS date,
  CAST(ROUND(SUM(line_revenue)) AS INT64)      AS revenue,
  COUNT(DISTINCT transaction_id)               AS transactions,
  CAST(ROUND(SAFE_DIVIDE(SUM(line_revenue),
       COUNT(DISTINCT transaction_id))) AS INT64) AS avg_basket
FROM `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions`
WHERE store_id = @store_id
  AND NOT is_return
  AND txn_date BETWEEN DATE_SUB(@as_of_date, INTERVAL 6 DAY) AND @as_of_date
GROUP BY txn_date
ORDER BY txn_date;


-- ===========================================================================
-- name: forecast_read
-- Widget: "7-day demand forecast" with confidence band.
-- Reads the materialised output of forecast.sql. It does not run the model,
-- so the dashboard stays fast and the forecast is auditable after the fact.
-- ===========================================================================
SELECT
  FORMAT_DATE('%a', forecast_date)             AS day,
  forecast_date                                AS date,
  CAST(ROUND(predicted_revenue) AS INT64)      AS predicted,
  CAST(ROUND(lower_bound) AS INT64)            AS lower,
  CAST(ROUND(upper_bound) AS INT64)            AS upper,
  confidence_level,
  model_run_at
FROM `${GCP_PROJECT}.${BQ_DATASET}.demand_forecast_daily`
WHERE store_id = @store_id
  AND forecast_date > @as_of_date
QUALIFY model_run_at = MAX(model_run_at) OVER ()
ORDER BY forecast_date
LIMIT 7;


-- ===========================================================================
-- name: reorder_alerts
-- Widget: "Inventory alerts".
-- Urgency comes from two independent signals: the stock level against the
-- store's reorder point, and days of cover against supplier lead time. A SKU
-- above its reorder point can still be critical if it will run dry before the
-- next delivery lands.
-- ===========================================================================
WITH latest_snapshot AS (
 SELECT MAX(snapshot_date) AS snapshot_date
 FROM `${GCP_PROJECT}.${BQ_DATASET}.inventory_snapshots`
 WHERE store_id=@store_id AND snapshot_date BETWEEN DATE_SUB(@as_of_date, INTERVAL 14 DAY) AND @as_of_date
), velocity AS (
 SELECT product_id,SUM(quantity)/30.0 AS daily
 FROM `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions`
 WHERE store_id=@store_id AND NOT is_return
 AND txn_date BETWEEN DATE_SUB(@as_of_date, INTERVAL 29 DAY) AND @as_of_date
 GROUP BY product_id
), predictions AS (
 SELECT product_id,AVG(GREATEST(predicted_units,0)) AS daily
 FROM `${GCP_PROJECT}.${BQ_DATASET}.product_forecast_daily`
 WHERE store_id=@store_id AND forecast_date>@as_of_date
 AND forecast_date<=DATE_ADD(@as_of_date, INTERVAL 14 DAY)
 GROUP BY product_id
), stock AS (
 SELECT p.product_id,p.product_name,p.category,i.units_on_hand,i.reorder_point,
 IFNULL(i.units_on_order,0) AS units_on_order,IFNULL(i.lead_time_days,7) AS lead_time_days,
 GREATEST(COALESCE(f.daily,v.daily,0),0) AS daily,
 IF(f.daily IS NOT NULL,'forecast','30-day sales average') AS demand_basis,
 LEAST(21,IF(p.shelf_life_days>0,p.shelf_life_days,21)) AS cover_target,
 IF(p.shelf_life_days BETWEEN 1 AND 20,1,GREATEST(IFNULL(p.case_size,12),1)) AS case_size
 FROM `${GCP_PROJECT}.${BQ_DATASET}.inventory_snapshots` i
 JOIN latest_snapshot USING(snapshot_date)
 JOIN `${GCP_PROJECT}.${BQ_DATASET}.products` p USING(product_id)
 LEFT JOIN velocity v USING(product_id)
 LEFT JOIN predictions f USING(product_id)
 WHERE i.store_id=@store_id AND p.is_active AND p.is_tracked AND p.is_ours
), sized AS (
 SELECT *,SAFE_DIVIDE(units_on_hand,NULLIF(daily,0)) AS cover,
 GREATEST(0,CAST(CEIL(daily*cover_target) AS INT64)-units_on_hand-units_on_order) AS gap
 FROM stock
)
SELECT product_id,product_name AS product,category,units_on_hand AS stock,
 reorder_point AS reorder_at,units_on_order,ROUND(daily,1) AS units_per_day,
 ROUND(cover,1) AS days_of_cover,demand_basis,cover_target AS cover_target_days,case_size,
 CASE WHEN units_on_hand<=reorder_point OR cover<lead_time_days THEN 'critical'
 WHEN units_on_hand<=reorder_point*1.5 OR cover<cover_target THEN 'warning' ELSE 'watch' END AS level,
 CAST(CEIL(SAFE_DIVIDE(gap,case_size))*case_size AS INT64) AS recommended_order_units
FROM sized
WHERE units_on_hand<=reorder_point*1.5 OR cover<cover_target
ORDER BY IF(units_on_hand<=reorder_point OR cover<lead_time_days,0,1),cover
LIMIT @limit;

-- ===========================================================================
-- name: segment_stats
-- Widget: "Customer segments".
-- Share, average basket and visit frequency are owned by the segmentation job
-- and read from customer_segments as-is. The observed columns are a live
-- cross-check from the last 90 days of transactions, so a segment whose stated
-- profile has drifted away from its actual behaviour is visible rather than
-- hidden behind a single averaged number.
-- ===========================================================================
WITH latest_segmentation AS (
  SELECT MAX(as_of_date) AS as_of_date
  FROM `${GCP_PROJECT}.${BQ_DATASET}.customer_segments`
  WHERE store_id = @store_id
    AND as_of_date <= @as_of_date
),
observed AS (
  SELECT
    segment_name,
    COUNT(DISTINCT customer_id)    AS customers_90d,
    COUNT(DISTINCT transaction_id) AS baskets_90d,
    SUM(line_revenue)              AS revenue_90d
  FROM `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions`
  WHERE store_id = @store_id
    AND NOT is_return
    AND segment_name IS NOT NULL
    AND txn_date BETWEEN DATE_SUB(@as_of_date, INTERVAL 89 DAY) AND @as_of_date
  GROUP BY segment_name
)
SELECT
  s.segment_name                            AS name,
  CAST(ROUND(s.share_pct) AS INT64)         AS pct,
  CAST(ROUND(s.avg_basket_value) AS INT64)  AS avg_basket,
  ROUND(s.visits_per_week, 1)               AS visits,
  s.description                             AS descr,
  o.customers_90d,
  o.baskets_90d,
  CAST(ROUND(o.revenue_90d) AS INT64)       AS revenue_90d,
  ROUND(SAFE_DIVIDE(o.revenue_90d, SUM(o.revenue_90d) OVER ()), 3) AS revenue_share_90d
FROM `${GCP_PROJECT}.${BQ_DATASET}.customer_segments` s
JOIN latest_segmentation USING (as_of_date)
LEFT JOIN observed o USING (segment_name)
WHERE s.store_id = @store_id
ORDER BY s.share_pct DESC;


-- ===========================================================================
-- name: top_movers
-- Widget: "Top movers".
-- "trending" is a real comparison, last 7 days against the 7 before it, not a
-- stored flag.
-- ===========================================================================
WITH window_sales AS (
  SELECT
    product_id,
    SUM(quantity)     AS units_30d,
    SUM(line_revenue) AS revenue_30d,
    SUM(IF(txn_date > DATE_SUB(@as_of_date, INTERVAL 7 DAY),  quantity, 0)) AS units_last_7d,
    SUM(IF(txn_date <= DATE_SUB(@as_of_date, INTERVAL 7 DAY)
           AND txn_date > DATE_SUB(@as_of_date, INTERVAL 14 DAY), quantity, 0)) AS units_prior_7d
  FROM `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions`
  WHERE store_id = @store_id
    AND NOT is_return
    AND txn_date BETWEEN DATE_SUB(@as_of_date, INTERVAL 29 DAY) AND @as_of_date
  GROUP BY product_id
)
SELECT
  p.product_id                                   AS id,
  p.product_name                                 AS name,
  p.category                                     AS cat,
  CAST(p.list_price AS INT64)                    AS price,
  w.units_30d                                    AS units_sold_last_30d,
  CAST(ROUND(w.revenue_30d) AS INT64)            AS revenue_last_30d,
  ROUND(p.margin_rate, 2)                        AS margin,
  CAST(ROUND(w.revenue_30d * p.margin_rate) AS INT64) AS margin_value_last_30d,
  ROUND(SAFE_DIVIDE(w.units_last_7d - w.units_prior_7d,
                    NULLIF(w.units_prior_7d, 0)), 3) AS wow_growth,
  COALESCE(w.units_last_7d > w.units_prior_7d, FALSE) AS trending
FROM window_sales w
JOIN `${GCP_PROJECT}.${BQ_DATASET}.products` p USING (product_id)
WHERE p.is_active AND p.is_tracked
ORDER BY w.units_30d DESC
LIMIT @limit;


-- ===========================================================================
-- name: kpi_rollup
-- Widget: KPI strip.
-- Every figure is derived from a table except the revenue target and NPS, which
-- are loaded onto stores from the planning system and the survey platform.
-- ===========================================================================
WITH today AS (
  SELECT
    SUM(line_revenue)              AS revenue,
    COUNT(DISTINCT transaction_id) AS transactions
  FROM `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions`
  WHERE store_id = @store_id AND NOT is_return AND txn_date = @as_of_date
),
traffic_today AS (
  SELECT SUM(footfall) AS footfall
  FROM `${GCP_PROJECT}.${BQ_DATASET}.store_traffic_daily`
  WHERE store_id = @store_id AND traffic_date = @as_of_date
),
-- A basket counts as "returning" when that customer bought at this store in the
-- 90 days before today. Anonymous baskets are excluded from the denominator.
returning_today AS (
  SELECT
    COUNT(DISTINCT t.transaction_id) AS identified_txns,
    COUNT(DISTINCT IF(h.customer_id IS NOT NULL, t.transaction_id, NULL)) AS returning_txns
  FROM `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions` t
  LEFT JOIN (
    SELECT DISTINCT customer_id
    FROM `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions`
    WHERE store_id = @store_id
      AND txn_date BETWEEN DATE_SUB(@as_of_date, INTERVAL 90 DAY)
                       AND DATE_SUB(@as_of_date, INTERVAL 1 DAY)
  ) h ON h.customer_id = t.customer_id
  WHERE t.store_id = @store_id
    AND t.txn_date = @as_of_date
    AND NOT t.is_return
    AND t.customer_id IS NOT NULL
),
latest_snapshot AS (
  SELECT MAX(snapshot_date) AS snapshot_date
  FROM `${GCP_PROJECT}.${BQ_DATASET}.inventory_snapshots`
  WHERE store_id = @store_id
    AND snapshot_date BETWEEN DATE_SUB(@as_of_date, INTERVAL 14 DAY) AND @as_of_date
),
stock_health AS (
  SELECT
    COUNTIF(units_on_hand <= 0)     AS out_of_stock_skus,
    COUNT(DISTINCT product_id)      AS total_skus
  FROM `${GCP_PROJECT}.${BQ_DATASET}.inventory_snapshots`
  JOIN latest_snapshot USING (snapshot_date)
  WHERE store_id = @store_id
)
SELECT
  CAST(ROUND(t.revenue) AS INT64)                            AS revenue_today,
  CAST(ROUND(s.daily_revenue_target) AS INT64)               AS revenue_target,
  t.transactions                                             AS transactions_today,
  CAST(ROUND(SAFE_DIVIDE(t.revenue, t.transactions)) AS INT64) AS avg_basket,
  ROUND(SAFE_DIVIDE(t.transactions, tr.footfall), 3)         AS conversion_rate,
  ROUND(SAFE_DIVIDE(r.returning_txns, r.identified_txns), 3) AS return_customer_pct,
  s.latest_nps                                               AS nps,
  sh.out_of_stock_skus,
  sh.total_skus
FROM today t
CROSS JOIN traffic_today tr
CROSS JOIN returning_today r
CROSS JOIN stock_health sh
CROSS JOIN `${GCP_PROJECT}.${BQ_DATASET}.stores` s
WHERE s.store_id = @store_id;


-- ===========================================================================
-- name: promotions_active
-- Widget: "Active promotions".
-- ===========================================================================
SELECT
  promotion_id      AS id,
  promotion_name    AS name,
  discount_label    AS discount,
  category,
  IFNULL(NULLIF(active_weekdays, ''), 'All week') AS validity,
  ROUND(observed_uplift_pct, 1)                   AS uplift_pct
FROM `${GCP_PROJECT}.${BQ_DATASET}.promotions`
WHERE (store_id = @store_id OR store_id IS NULL)
  AND @as_of_date BETWEEN start_date AND IFNULL(end_date, @as_of_date)
ORDER BY observed_uplift_pct DESC;


-- ===========================================================================
-- name: product_catalog
-- Grounding payload for the shopper assistant: live price and stock so the
-- model can only recommend what is actually on the shelf.
-- ===========================================================================
WITH latest_snapshot AS (
 SELECT MAX(snapshot_date) AS snapshot_date
 FROM `${GCP_PROJECT}.${BQ_DATASET}.inventory_snapshots`
 WHERE store_id=@store_id AND snapshot_date BETWEEN DATE_SUB(@as_of_date, INTERVAL 14 DAY) AND @as_of_date
), velocity AS (
 SELECT product_id, SUM(quantity) AS units30,
 SUM(IF(txn_date > DATE_SUB(@as_of_date, INTERVAL 7 DAY),quantity,0)) AS recent,
 SUM(IF(txn_date <= DATE_SUB(@as_of_date, INTERVAL 7 DAY) AND txn_date > DATE_SUB(@as_of_date, INTERVAL 14 DAY),quantity,0)) AS prior
 FROM `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions`
 WHERE store_id=@store_id AND NOT is_return AND txn_date BETWEEN DATE_SUB(@as_of_date, INTERVAL 29 DAY) AND @as_of_date
 GROUP BY product_id
), predictions AS (
 SELECT product_id, AVG(predicted_units) AS daily
 FROM `${GCP_PROJECT}.${BQ_DATASET}.product_forecast_daily`
 WHERE store_id=@store_id AND forecast_date > @as_of_date AND forecast_date <= DATE_ADD(@as_of_date, INTERVAL 14 DAY)
 GROUP BY product_id
)
SELECT p.product_id AS id,p.product_name AS name,p.category AS cat,p.pack_size AS pack,
 CAST(p.list_price AS FLOAT64) AS price,i.units_on_hand AS stock,i.reorder_point AS reorderAt,
 CAST(p.margin_rate AS FLOAT64) AS margin,p.protein_grams AS protein,p.added_sugar_grams AS addedSugar,
 p.is_ours AS ours,p.shelf_life_days AS shelfLifeDays,IFNULL(v.units30,0) AS unitsSoldLast30d,
 IFNULL(v.recent > v.prior,FALSE) AS trending,f.daily AS predictedUnitsPerDay,
 i.units_on_order AS unitsOnOrder,i.lead_time_days AS leadTimeDays,
 IF(p.shelf_life_days BETWEEN 1 AND 20,1,GREATEST(IFNULL(p.case_size,12),1)) AS caseSize
FROM `${GCP_PROJECT}.${BQ_DATASET}.products` p
JOIN `${GCP_PROJECT}.${BQ_DATASET}.inventory_snapshots` i USING(product_id)
JOIN latest_snapshot USING(snapshot_date)
LEFT JOIN velocity v USING(product_id)
LEFT JOIN predictions f USING(product_id)
WHERE i.store_id=@store_id AND p.is_active AND p.is_tracked
ORDER BY p.category,p.product_id;



-- ===========================================================================
-- name: visit_brief
-- Pre-visit context for the sales rep surface: the plan, the account, the buyer
-- and the objections that were raised last time.
-- ===========================================================================
SELECT
  v.visit_id,
  v.visit_date,
  v.visit_time,
  v.duration_minutes,
  v.status,
  v.store_name,
  v.store_id,
  v.objective,
  v.open_tasks,
  v.last_visit_date,
  DATE_DIFF(@as_of_date, v.last_visit_date, DAY) AS days_since_last_visit,
  v.visit_frequency,
  v.last_order_value,
  v.orders_last_6m,
  v.avg_order_value,
  v.listings_lost,
  a.account_id,
  a.account_name,
  a.account_type,
  a.tier,
  a.store_count,
  a.ytd_value,
  a.growth_yoy,
  a.contact_name,
  a.contact_role,
  a.contact_style,
  ARRAY(
    SELECT AS STRUCT o.objection_text, o.theme
    FROM `${GCP_PROJECT}.${BQ_DATASET}.visit_objections` o
    WHERE o.visit_id = v.visit_id
    ORDER BY o.raised_on DESC
  ) AS past_objections
FROM `${GCP_PROJECT}.${BQ_DATASET}.visits` v
JOIN `${GCP_PROJECT}.${BQ_DATASET}.accounts` a USING (account_id)
WHERE v.visit_id = @visit_id;


-- ===========================================================================
-- name: planogram_spec
-- The rules a shelf photo is scored against.
-- ===========================================================================
SELECT
  planogram_id   AS id,
  planogram_name AS name,
  bay,
  rule_id,
  rule_name      AS rule,
  spec,
  weight
FROM `${GCP_PROJECT}.${BQ_DATASET}.planogram_rules`
WHERE planogram_id = @planogram_id
  AND @as_of_date BETWEEN IFNULL(effective_from, @as_of_date)
                      AND IFNULL(effective_to, @as_of_date)
ORDER BY rule_id;


-- ===========================================================================
-- name: rag_search_keyword
-- RAG retrieval, default mode. No embedding model or BigQuery connection
-- required, which keeps first-run setup to one bq load. Scores a document by
-- how many query tokens appear in its title or fact.
-- ===========================================================================
WITH terms AS (
  SELECT DISTINCT term
  FROM UNNEST(REGEXP_EXTRACT_ALL(LOWER(@query), r'[a-z0-9]{3,}')) AS term
)
SELECT
  d.doc_id,
  d.title,
  d.fact,
  d.source_type,
  d.published_date,d.url,d.is_synthetic,
  (SELECT COUNT(*) FROM terms t
   WHERE STRPOS(LOWER(CONCAT(d.title, ' ', d.fact)), t.term) > 0) AS match_score
FROM `${GCP_PROJECT}.${BQ_DATASET}.kb_documents` d
WHERE (SELECT COUNT(*) FROM terms t
       WHERE STRPOS(LOWER(CONCAT(d.title, ' ', d.fact)), t.term) > 0) > 0
ORDER BY match_score DESC, d.published_date DESC
LIMIT @top_k;


-- ===========================================================================
-- name: rag_search_vector
-- RAG retrieval, semantic mode. Requires the remote embedding model and
-- populated kb_documents.embedding (see the optional section of schema.sql).
-- Selected by setting RAG_MODE=vector on the Cloud Run service.
-- ===========================================================================
SELECT
  base.doc_id,
  base.title,
  base.fact,
  base.source_type,
  base.published_date,base.url,base.is_synthetic,
  ROUND(1 - distance, 4) AS match_score
FROM VECTOR_SEARCH(
  TABLE `${GCP_PROJECT}.${BQ_DATASET}.kb_documents`,
  'embedding',
  (
    SELECT ml_generate_embedding_result AS embedding
    FROM ML.GENERATE_EMBEDDING(
      MODEL `${GCP_PROJECT}.${BQ_DATASET}.text_embedding_model`,
      (SELECT @query AS content)
    )
  ),
  top_k => @top_k,
  distance_type => 'COSINE'
)
ORDER BY distance;


-- name: knowledge_docs
SELECT doc_id AS id,title,fact,url,publisher,published_label AS published
FROM `${GCP_PROJECT}.${BQ_DATASET}.kb_documents` ORDER BY doc_id;

-- name: bootstrap_promotions
SELECT promotion_name AS name,discount_label AS discount,validity_label AS validity,
 uplift_label AS uplift,sku_ids AS skuIds,CAST(start_date AS STRING) AS startDate,CAST(end_date AS STRING) AS endDate
FROM `${GCP_PROJECT}.${BQ_DATASET}.promotions`
WHERE (store_id=@store_id OR store_id IS NULL)
AND @as_of_date BETWEEN start_date AND IFNULL(end_date,@as_of_date);
