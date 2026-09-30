# RetailIQ on Google Cloud

This folder is the production path for RetailIQ. It is not running today.

The submitted demo is a static single page app, `index.html` plus
`retail_data.js`, that works with no cloud account. Every number it shows comes
from synthetic fixtures held in the browser, and the Gemini calls go straight
from the browser to the Gemini API using a key the judge pastes in, stored in
`localStorage`. That was a deliberate choice, so the demo opens and works for
anyone with a key and nothing else.

What lives here is the same product with real infrastructure underneath. The
schema, the queries, the forecasting model, the API service and the deployment
script are complete and runnable, but they activate only when you point them at
a Google Cloud project. Until you run `deploy.sh`, nothing in this folder is
live and the app continues to read its fixtures.

## Which service does what

| Service | Role in RetailIQ |
| --- | --- |
| BigQuery | The warehouse. Sales at line item grain, inventory snapshots, customer segments, promotions, accounts, visits, the sales knowledge base and planogram audits. Every dashboard number is a query against it. |
| BigQuery ML | Demand forecasting with `ARIMA_PLUS`. One model for daily store revenue, one for per SKU unit demand. No separate training infrastructure, the model lives next to the data. |
| Vertex AI | Gemini inference for all three surfaces, the shopper assistant, the pitch and rehearsal flows, the shelf photo vision check and the business analyst. Called from Cloud Run with the service account, so there is no key in the browser. |
| Cloud Run | The API. A single FastAPI container that serves the dashboard widgets, the retrieval endpoint and the streaming Gemini proxy. Scales to zero between demos. |
| Secret Manager | Holds the Gemini API key if you use the keyed fallback. Mounted into the service as an environment variable, never baked into the image and never sent to the client. |
| Cloud Storage | Shelf photos from the planogram compliance check. The photo is uploaded to a bucket, and the `gs://` URI is passed to Gemini and recorded on the audit row, so a compliance verdict can be re-checked against the exact image it came from. |
| AlloyDB for PostgreSQL | Not used by this folder, noted as the operational option. BigQuery is the right place for analytics and forecasting, but basket writes, order placement and visit check ins are transactional and want row level reads and writes with low latency. The natural split is AlloyDB for operational state, streamed into BigQuery for analysis. |

## Architecture

```
                         Browser (index.html)
                                  |
              static fixtures     |     cloud path
              retail_data.js  <---+--->  HTTPS, CORS
              (shipped demo)            |
                                        v
                          +-----------------------------+
                          |  Cloud Run: retailiq-api    |
                          |  FastAPI, non-root, 1 vCPU  |
                          +-----------------------------+
                            |            |            |
              widget reads  |            | Gemini     | photo write
              and retrieval |            | streaming  |
                            v            v            v
                  +-----------------+  +-----------+  +-----------------+
                  |    BigQuery     |  | Vertex AI |  | Cloud Storage   |
                  |  dataset:       |  |  Gemini   |  |  shelf photos   |
                  |  retailiq       |  +-----------+  +-----------------+
                  |                 |        ^
                  |  sales_transac. |        |
                  |  inventory_snap.|   +---------------+
                  |  customer_segm. |   | Secret Manager|
                  |  kb_documents   |   | gemini key,   |
                  |  planogram_*    |   | optional      |
                  |  visits, accts  |   +---------------+
                  +-----------------+
                          |
                          | BigQuery ML, scheduled daily
                          v
                  +-----------------------------+
                  |  ARIMA_PLUS models          |
                  |  store_revenue_forecast     |
                  |  product_demand_forecast    |
                  |         |                   |
                  |         v                   |
                  |  demand_forecast_daily      |
                  |  product_forecast_daily     |
                  +-----------------------------+
```

The forecast is trained on a schedule and materialised into
`demand_forecast_daily`. The API only reads that table. A dashboard load never
triggers model training, so the page is fast and yesterday's forecast stays on
the record instead of being silently recomputed.

## Files

| File | What it is |
| --- | --- |
| `schema.sql` | Dataset and table DDL. Partitioned on date columns, clustered on the columns the widget queries filter by. |
| `queries.sql` | One labelled query per dashboard widget, plus retrieval and the sales rep reads. This file is loaded at runtime by `main.py`, so the query you read is the query that runs. |
| `forecast.sql` | `CREATE MODEL` for both `ARIMA_PLUS` models, then `ML.FORECAST` at 90 percent confidence materialised into the forecast tables. |
| `main.py` | The Cloud Run service. Widget endpoints, `/api/rag/search`, and the streaming `/api/chat` Gemini proxy. |
| `seed_data.py` | Generates newline delimited JSON seed files from the demo fixture. |
| `deploy.sh` | The gcloud and bq commands, in order, re-runnable. |
| `Dockerfile` | Slim Python base, non-root user, single uvicorn worker. |
| `requirements.txt`, `.gcloudignore` | Runtime dependencies and build context filter. |

## Endpoints

| Method | Path | Returns |
| --- | --- | --- |
| GET | `/healthz` | Config echo and the list of query blocks loaded from `queries.sql`. |
| GET | `/api/config` | Non secret settings the front end needs, including the pinned demo date. |
| GET | `/api/kpis` | KPI strip: revenue today against target, average basket, conversion, returning customer share, NPS, out of stock count. |
| GET | `/api/revenue/week` | Daily revenue and basket count for the last 7 days. |
| GET | `/api/forecast` | The materialised 7 day forecast with lower and upper bounds. |
| GET | `/api/alerts` | Reorder alerts with days of cover, urgency level and a recommended order quantity. |
| GET | `/api/segments` | Segment share and profile, with a live 90 day revenue cross-check. |
| GET | `/api/promotions` | Promotions active on the report date. |
| GET | `/api/top-movers` | Units, revenue and margin value over 30 days, with a real week on week trend. |
| GET | `/api/products` | Live catalogue with price and stock, used to ground the shopper assistant. |
| GET | `/api/visits/{visit_id}` | Pre visit brief: plan, account, buyer profile, past objections. |
| GET | `/api/planogram/{planogram_id}` | The rules a shelf photo is scored against. |
| POST | `/api/rag/search` | Citable knowledge base passages for grounded pitch generation. |
| POST | `/api/chat` | Streaming Gemini proxy via Vertex AI. |

All read endpoints accept `store_id` and `date` query parameters. `date` pins
the report date so a demo is reproducible.

### The Gemini proxy

`/api/chat` emits server sent events in the same envelope as the Gemini REST
streaming API, `candidates[0].content.parts[].text`, followed by `[DONE]`. The
existing parser in `index.html` works against it by changing only the URL, so
moving off the browser key is a one line change on the front end rather than a
rewrite. The request body carries the system prompt, up to eight turns of
history, and optionally an image, either inline base64 or a `gs://` URI for a
shelf photo already in Cloud Storage.

When `GCP_PROJECT` is set and no key is mounted, the service authenticates to
Vertex AI with the Cloud Run service account. That is the path to prefer. There
is no credential to leak because there is no credential. The keyed path exists
for local development and for teams that would rather keep an AI Studio key in
Secret Manager.

### Failure behaviour

If BigQuery is unreachable, not seeded, or the service account lacks a role,
the endpoint returns HTTP 503 with the query name, the dataset it tried to
read, the underlying error and a hint. If the forecast table has no rows for
the requested horizon, `/api/forecast` returns 404 and says to run
`forecast.sql`. No endpoint substitutes a sample value for a real one. A blank
widget is recoverable, a plausible wrong number is not.

## Standing it up

Prerequisites: a Google Cloud project with billing enabled, `gcloud` and `bq`
authenticated, Python 3.10 or newer for the seed generator.

```bash
cd gcp
export GCP_PROJECT=your-project-id

# Optional overrides, these are the defaults.
export BQ_DATASET=retailiq
export BQ_LOCATION=asia-south1
export REGION=asia-south1
export VERTEX_LOCATION=asia-south1

./deploy.sh
```

That runs, in order:

1. Enables BigQuery, Cloud Run, Cloud Build, Artifact Registry, Vertex AI,
   Secret Manager and Cloud Storage.
2. Creates the dataset in `BQ_LOCATION` and applies `schema.sql`.
3. Runs `seed_data.py` and loads each table with `bq load --replace`.
4. Runs `forecast.sql`, which trains both models and writes the horizon.
5. Creates the shelf photo bucket and the `retailiq-api` service account, with
   `bigquery.jobUser`, `bigquery.dataViewer`, `aiplatform.user` on the project
   and `storage.objectAdmin` on the bucket only.
6. Creates the `retailiq-gemini-key` secret and grants the service account
   access to it. No key version is added unless you set `GEMINI_KEY_FILE` to a
   file containing one.
7. Builds from source and deploys Cloud Run, mounting the secret only if an
   enabled version exists.

Individual steps can be re-run on their own:

```bash
./deploy.sh schema
./deploy.sh seed
./deploy.sh forecast
./deploy.sh service
```

Check it:

```bash
URL=$(gcloud run services describe retailiq-api --region "$REGION" --format='value(status.url)')
curl "$URL/healthz"
curl "$URL/api/revenue/week"
curl "$URL/api/kpis"
```

To point the front end at the API instead of the fixtures, set the base URL and
`ALLOWED_ORIGINS` to the page origin rather than `*`. The front end change is
out of scope for this folder, `index.html` and `retail_data.js` are untouched.

Keeping the forecast fresh, once you are past the demo:

```bash
bq mk --transfer_config \
  --project_id="$GCP_PROJECT" \
  --data_source=scheduled_query \
  --display_name="RetailIQ nightly forecast" \
  --schedule="every 24 hours" \
  --params="{\"query\":\"$(cat forecast.sql)\",\"use_legacy_sql\":false}"
```

Use the rendered SQL, with the placeholders already substituted, when you create
the transfer config.

## About the seed data

Everything loaded by `seed_data.py` is synthetic. There is no customer data of
any kind in this repository.

The fixture in `retail_data.js` holds 7 daily revenue totals, which is nowhere
near enough history to fit a seasonal model, so the generator synthesises 180
days. It is built to be checkable rather than convenient:

- Net revenue and basket count for the last 7 days match `revenueWeek` exactly,
  so the revenue chart in the cloud path reproduces the chart in the demo.
- The 10 named SKUs hit their `unitsSoldLast30d` velocities to within a few
  percent, so top movers and reorder alerts are about real products.
- The rest of the day's revenue is carried by a generated long tail catalogue of
  50 additional SKUs, because 10 products cannot add up to a 48,000 rupee day.
- Inventory is a single snapshot on the report date, with the named SKUs at their
  fixture stock levels. In production this is a daily extract, not a generated
  history.

Two places where the cloud path will not match the fixture number, on purpose:

- Average basket is derived as revenue divided by baskets, which on the fixture's
  own figures is about 150 rupees, not the 820 the fixture's KPI block states.
  The derived number is the one the query returns.
- Alert levels are computed from days of cover against supplier lead time, so a
  SKU the fixture labels a warning can come back as critical when the arithmetic
  says it will run dry before the next delivery. The rule is in `queries.sql` and
  can be read and argued with.

The default report date is 2026-09-27, a Sunday, so the 7 day window ends on the
peak day the fixture treats as today and both planned visits are still in the
future. Change it with `DEMO_AS_OF_DATE`.

## Retrieval

Pitch citations come from `kb_documents`, where each row holds one citable
claim. The retrieval endpoint has two modes:

- `keyword`, the default, scores documents by query token overlap. It needs
  nothing beyond the loaded table, so the first run works immediately.
- `vector` uses `ML.GENERATE_EMBEDDING` with `text-embedding-005` and
  `VECTOR_SEARCH` over a populated `embedding` column. It needs a BigQuery
  connection to Vertex AI, so it is opt in. The three statements are in the
  commented section at the end of `schema.sql`. Run them, then redeploy with
  `RAG_MODE=vector`.

An empty result is a real answer. If nothing in the knowledge base supports a
claim, there is nothing to cite, and the pitch generator should stop rather than
improvise.

## Configuration

The service reads everything from the environment. No value below has a default
that contains a credential, and none is committed.

| Variable | Default | Purpose |
| --- | --- | --- |
| `GCP_PROJECT` | none, required | Project that owns the dataset and the Vertex AI calls. |
| `BQ_DATASET` | `retailiq` | Dataset name. |
| `BQ_LOCATION` | `asia-south1` | Dataset region. Query jobs must run in the same region. |
| `VERTEX_LOCATION` | `asia-south1` | Vertex AI region for Gemini. |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Model id, matching the one the demo uses. |
| `DEFAULT_STORE_ID` | `BLR-KOR-014` | Store used when a request omits `store_id`. |
| `DEMO_AS_OF_DATE` | unset | Pins the report date. Unset means today. |
| `RAG_MODE` | `keyword` | `keyword` or `vector`. |
| `ALLOWED_ORIGINS` | `*` | Comma separated CORS origins. Narrow this for anything real. |
| `GEMINI_API_KEY` | unset | Injected from Secret Manager. Absent means Vertex AI service account auth, which is the preferred path. |

## Cost and operational notes

- The service scales to zero, so an idle deployment costs storage only.
- Widget queries are partition pruned and clustered. With the seed data each one
  scans well under a megabyte, inside the BigQuery free tier.
- `ARIMA_PLUS` training reads the full history range, so it is a scheduled job,
  not a request path. Train nightly at most.
- The per SKU model fits one series for every store and product pair. Cap the
  catalogue or the history before running it against a real chain.
- The Cloud Run service is deployed with `--allow-unauthenticated` so a judge can
  curl it. For anything beyond a demo, put Identity Aware Proxy or an API
  gateway in front of it and narrow `ALLOWED_ORIGINS`.
