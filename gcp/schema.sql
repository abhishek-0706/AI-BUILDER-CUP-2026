-- RetailIQ - BigQuery DDL
--
-- Placeholders ${GCP_PROJECT} and ${BQ_DATASET} are substituted by deploy.sh
-- (envsubst) so that no project id is committed to the repository.
--
-- Run:  envsubst < schema.sql | bq query --use_legacy_sql=false
--
-- Grain notes:
--   sales_transactions    one row per basket line item
--   inventory_snapshots   one row per store x product x day
--   planogram_audits      one row per audited rule per photo

-- The dataset itself is created by deploy.sh with `bq mk --location`, so the
-- region is set in one place and this script can run in any location.
CREATE SCHEMA IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}`;


-- ============================================================================
-- Reference / dimension tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.stores` (
  store_id              STRING  NOT NULL,
  store_name            STRING  NOT NULL,
  city                  STRING,
  zone                  STRING,
  format_segment        STRING,
  sqft                  INT64,
  open_date             DATE,
  -- Loaded from the merchandising planning system, not derivable from sales.
  daily_revenue_target  NUMERIC,
  -- Latest rolling NPS from the CX survey platform; refreshed weekly.
  latest_nps            INT64,
  nps_as_of             DATE
)
CLUSTER BY store_id;


CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.products` (
  product_id            STRING  NOT NULL,
  product_name          STRING  NOT NULL,
  category              STRING,
  brand                 STRING,
  list_price            NUMERIC,
  -- Retailer margin as a fraction, e.g. 0.20 = 20 percent.
  margin_rate           NUMERIC,
  -- Default replenishment trigger; per-store overrides live in inventory_snapshots.
  default_reorder_point INT64,
  pack_size             STRING,
  is_active             BOOL,
  first_listed_date     DATE
)
CLUSTER BY category, product_id;


CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.sales_reps` (
  rep_id                STRING  NOT NULL,
  rep_name              STRING,
  role_title            STRING,
  territory             STRING,
  quota_month           NUMERIC,
  visits_planned_month  INT64
)
CLUSTER BY rep_id;


CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.accounts` (
  account_id            STRING  NOT NULL,
  account_name          STRING  NOT NULL,
  account_type          STRING,
  store_count           INT64,
  tier                  STRING,
  relationship_years    NUMERIC,
  ytd_value             NUMERIC,
  growth_yoy            NUMERIC,
  contact_name          STRING,
  contact_role          STRING,
  -- Free-text buyer profile; fed to the pitch prompt as tone guidance.
  contact_style         STRING
)
CLUSTER BY account_id;


-- ============================================================================
-- Transactional and time-series tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions` (
  transaction_id        STRING  NOT NULL,
  line_number           INT64   NOT NULL,
  txn_ts                TIMESTAMP NOT NULL,
  txn_date              DATE    NOT NULL,
  store_id              STRING  NOT NULL,
  product_id            STRING  NOT NULL,
  -- NULL for walk-in baskets with no loyalty identifier.
  customer_id           STRING,
  segment_name          STRING,
  quantity              INT64,
  unit_price            NUMERIC,
  discount_amount       NUMERIC,
  -- quantity * unit_price - discount_amount, materialised so revenue rollups
  -- never disagree between widgets.
  line_revenue          NUMERIC,
  promotion_id          STRING,
  channel               STRING,
  is_return             BOOL
)
PARTITION BY txn_date
CLUSTER BY store_id, product_id;


CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.store_traffic_daily` (
  traffic_date          DATE    NOT NULL,
  store_id              STRING  NOT NULL,
  -- Door-counter footfall; denominator for conversion rate.
  footfall              INT64,
  unique_visitors       INT64
)
PARTITION BY traffic_date
CLUSTER BY store_id;


CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.inventory_snapshots` (
  snapshot_date         DATE    NOT NULL,
  store_id              STRING  NOT NULL,
  product_id            STRING  NOT NULL,
  units_on_hand         INT64,
  -- Store-level override of products.default_reorder_point.
  reorder_point         INT64,
  units_on_order        INT64,
  -- Supplier lead time used to turn a stock gap into an urgency level.
  lead_time_days        INT64
)
PARTITION BY snapshot_date
CLUSTER BY store_id, product_id;


CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.customer_segments` (
  as_of_date            DATE    NOT NULL,
  store_id              STRING  NOT NULL,
  segment_name          STRING  NOT NULL,
  -- Share of the store's active customer base, 0-100.
  share_pct             NUMERIC,
  avg_basket_value      NUMERIC,
  visits_per_week       NUMERIC,
  description           STRING
)
PARTITION BY as_of_date
CLUSTER BY store_id, segment_name;


CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.promotions` (
  promotion_id          STRING  NOT NULL,
  promotion_name        STRING  NOT NULL,
  store_id              STRING,
  category              STRING,
  mechanic              STRING,
  discount_label        STRING,
  discount_pct          NUMERIC,
  start_date            DATE,
  end_date              DATE,
  -- e.g. 'Fri,Sat,Sun'. Empty means every day in the window.
  active_weekdays       STRING,
  -- Measured post-hoc against a matched control set of stores.
  observed_uplift_pct   NUMERIC
)
PARTITION BY start_date
CLUSTER BY store_id, category;


-- ============================================================================
-- Field sales tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.visits` (
  visit_id              STRING  NOT NULL,
  account_id            STRING  NOT NULL,
  rep_id                STRING,
  store_id              STRING,
  store_name            STRING,
  visit_date            DATE    NOT NULL,
  visit_time            STRING,
  duration_minutes      INT64,
  status                STRING,
  last_visit_date       DATE,
  -- Cadence rule from the territory index score, kept as text because it is a
  -- policy string the rep reads, not a computed interval.
  visit_frequency       STRING,
  objective             STRING,
  open_tasks            ARRAY<STRING>,
  last_order_value      NUMERIC,
  orders_last_6m        INT64,
  avg_order_value       NUMERIC,
  listings_lost         ARRAY<STRING>
)
PARTITION BY visit_date
CLUSTER BY account_id, store_id;


CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.visit_objections` (
  objection_id          STRING  NOT NULL,
  visit_id              STRING  NOT NULL,
  account_id            STRING,
  objection_text        STRING  NOT NULL,
  -- Coarse bucket (price, velocity, space, supply) used to pick rebuttal docs.
  theme                 STRING,
  raised_on             DATE,
  resolved              BOOL
)
CLUSTER BY visit_id;


CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.kb_documents` (
  doc_id                STRING  NOT NULL,
  title                 STRING  NOT NULL,
  -- The single citable claim. Pitch generation may only assert facts that
  -- appear here, and must cite doc_id.
  fact                  STRING  NOT NULL,
  source_type           STRING,
  category              STRING,
  published_date        DATE,
  -- text-embedding-005 output, populated by ML.GENERATE_EMBEDDING.
  -- Left empty when the service falls back to keyword retrieval.
  embedding             ARRAY<FLOAT64>,
  is_synthetic          BOOL
)
CLUSTER BY doc_id;


CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.planogram_rules` (
  planogram_id          STRING  NOT NULL,
  planogram_name        STRING,
  bay                   STRING,
  rule_id               STRING  NOT NULL,
  rule_name             STRING,
  spec                  STRING,
  -- Contribution of this rule to the overall compliance score; weights per
  -- planogram should sum to 1.
  weight                NUMERIC,
  effective_from        DATE,
  effective_to          DATE
)
CLUSTER BY planogram_id, rule_id;


CREATE TABLE IF NOT EXISTS `${GCP_PROJECT}.${BQ_DATASET}.planogram_audits` (
  audit_id              STRING  NOT NULL,
  visit_id              STRING,
  store_id              STRING  NOT NULL,
  planogram_id          STRING  NOT NULL,
  captured_at           TIMESTAMP NOT NULL,
  -- gs:// object holding the shelf photo the verdict was derived from.
  photo_uri             STRING,
  rule_id               STRING  NOT NULL,
  verdict               STRING,
  confidence            NUMERIC,
  observation           STRING,
  -- Weighted score for the whole photo, repeated on each rule row so a single
  -- row answers "how compliant was this shelf".
  compliance_score      NUMERIC,
  model_version         STRING,
  reviewed_by_human     BOOL
)
PARTITION BY DATE(captured_at)
CLUSTER BY store_id, planogram_id;


-- ============================================================================
-- Optional: semantic RAG retrieval
--
-- The service defaults to keyword retrieval (RAG_MODE=keyword), which needs
-- nothing beyond the table above. Semantic retrieval needs a BigQuery
-- connection to Vertex AI, so it is left commented out and opt-in. Run these
-- three statements by hand, then redeploy with RAG_MODE=vector.
--
--   bq mk --connection --location=$BQ_LOCATION \
--         --connection_type=CLOUD_RESOURCE vertex_ai
--   # grant the connection's service account roles/aiplatform.user, then:
--
-- CREATE OR REPLACE MODEL `${GCP_PROJECT}.${BQ_DATASET}.text_embedding_model`
-- REMOTE WITH CONNECTION `${GCP_PROJECT}.${BQ_LOCATION}.vertex_ai`
-- OPTIONS (ENDPOINT = 'text-embedding-005');
--
-- UPDATE `${GCP_PROJECT}.${BQ_DATASET}.kb_documents` d
-- SET embedding = e.ml_generate_embedding_result
-- FROM (
--   SELECT doc_id, ml_generate_embedding_result
--   FROM ML.GENERATE_EMBEDDING(
--     MODEL `${GCP_PROJECT}.${BQ_DATASET}.text_embedding_model`,
--     (SELECT doc_id, CONCAT(title, '. ', fact) AS content
--      FROM `${GCP_PROJECT}.${BQ_DATASET}.kb_documents`)
--   )
-- ) e
-- WHERE d.doc_id = e.doc_id;
