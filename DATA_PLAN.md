# RetailIQ, public data migration plan

Verified 1 October 2026. Every dataset below was checked against a live source before being
recommended. Where a claim could not be confirmed it is marked unconfirmed rather than repeated.
Datasets that turned out to be gated, dead, or licence-restricted are named as such instead of
being quietly dropped, because knowing what not to try is worth as much as the shortlist.

Judging is roughly 18 October 2026, so the working budget is about 17 days.

---

## Decision taken, 1 October 2026

Section 5 raises geographic coherence as the biggest risk and offers two resolutions. Neither is
adopted as written. The chosen path is a third option, and it is a decision, not an option list.

**Keep the demo in Bengaluru, and make the Indian data real rather than relabelling foreign data.**

The problem statement is CPG field sales for one territory rep. That narrative needs a single
coherent territory, so presenting the manager surface as an Iowa retail network would fracture the
story the submission exists to tell. The route to coherence is therefore to replace the Indian
fixtures with real Indian sources, not to reframe around whatever dataset is largest.

Priority order changes accordingly:

1. **Overture Maps for real Bengaluru outlets.** Promoted to first. Zero ingestion, permissive
   licence, and it puts genuine Bengaluru store names into the visit planner, which is the primary
   surface. Highest coherence gain per hour of the whole plan.
2. **`kb_documents` from real Indian public sources** (MoSPI, Agmarknet, Census). The citation chips
   are the one thing a judge can independently verify by clicking, so these must be real. This also
   removes the fabricated Nielsen citation, which is the weakest item currently in the repo given
   Nielsen is a paid product.
3. **Open Food Facts India catalogue.** 24,613 verified Indian products with images and real brands.
   Prices are absent from the source and stay modelled, labelled as modelled.

**Iowa liquor sales is retained, but only as a labelled validation set for the forecasting engine.**
It proves the BigQuery ML ARIMA_PLUS path works against 30 million rows of real public retail
transactions at real store and SKU grain. It is presented as exactly that, on its own footing, with
its own provenance stated. No Iowa row is ever re-expressed as Bengaluru revenue, and no store
number is relabelled as a FreshMart outlet.

**dunnhumby is dropped.** US household panels cannot be reconciled with a Bengaluru territory
without exactly the silent relabelling this plan forbids, and section 5 already rates it the first
thing to cut on effort grounds.

Everything section 6 lists as having no public source stays synthetic and stays labelled.

---

## 0. Corrections to the candidate list

Three of the starting assumptions need fixing before anything else.

**`thelook_ecommerce` is itself synthetic.** The dataset ID is right,
`bigquery-public-data.thelook_ecommerce`, and it has the seven tables expected, but Google
describes it as a fictitious ecommerce clothing site built by the Looker team, and the contents are
explicitly stated to be synthetic. Swapping RetailIQ's fixtures for it would replace labelled
synthetic data with unlabelled synthetic data, which is a step backwards for a submission whose
README currently makes a virtue of honest labelling. It is also womenswear and menswear apparel,
not grocery. Do not use it as the product catalogue.

**The GA4 dataset ID was misspelled.** It is
`bigquery-public-data.ga4_obfuscated_sample_ecommerce`, not "obfoscated". It covers 1 November 2020
to 31 January 2021 only, about 92 daily `events_YYYYMMDD` tables and roughly 4.3 million events,
from the Google Merchandise Store. Three months of five-year-old clickstream from a company selling
branded t-shirts and drinkware does not support daily SKU demand forecasting, and many fields are
blanked to `<Other>` by the obfuscation. It is a poor fit here.

**`iowa_liquor_sales` is the strongest thing on the list, and it was the one you were least sure
about.** The real ID is `bigquery-public-data.iowa_liquor_sales`, single table `.sales`. It is real,
it is large, it is openly licensed, and it is already in BigQuery.

---

## 1. Recommended stack

One primary dataset per surface, and the reason it beats the alternatives.

### Business surface: `bigquery-public-data.iowa_liquor_sales.sales`

This is the anchor of the whole migration and the only swap that is genuinely low risk and high
payoff.

It holds every wholesale liquor purchase by Iowa retailers since 1 January 2012, roughly 30 million
rows across 24 columns, at one row per store per item per invoice date. It carries
`date`, `store_number`, `store_name`, `city`, `zip_code`, `item_number`, `item_description`,
`category_name`, `vendor_name`, `bottles_sold`, `sale_dollars`, `state_bottle_cost` and
`state_bottle_retail`.

Why it wins:

- It is already inside `bigquery-public-data`, so ingestion effort is zero and the GCP-native story
  is reinforced rather than undermined. Nothing to download, nothing to stage, nothing to schema-map.
- It is CC BY 4.0, which permits commercial use with attribution. Every Kaggle alternative for this
  job is non-commercial or competition-restricted.
- It has the exact grain `ARIMA_PLUS` needs, store by SKU by day, with more than thirteen years of
  history. Holiday effect modelling in BigQuery ML requires daily or weekly data spanning more than
  a year, and this clears that comfortably, which M5 and Favorita also do but only after you have
  wrestled them into BigQuery first.
- It has both units (`bottles_sold`) and revenue (`sale_dollars`), so it drives the revenue chart
  and the per-SKU reorder forecast from one table.
- It carries real retailer cost and retail price, so `products.margin_rate` becomes a computed
  figure rather than an invented one.

Why not the alternatives. **M5** is 42,840 series, 3,049 products, 10 stores, 1,941 days, and is
confirmed non-commercial: the competition rules restrict the data to non-commercial purposes
including academic research and education. It also arrives in wide format, 1,919 date columns, and
needs an unpivot before it is a time series at all. **Favorita** is 125,497,040 rows and about
4.65 GB uncompressed, competition-restricted, with winners required to sign licence and
non-disclosure terms. Either would consume days of the seventeen on ETL alone and neither can be
used commercially. **Walmart Recruiting** is weekly and department-level, not daily and SKU-level,
so it cannot feed a per-SKU reorder forecast.

The honest cost of this choice: it is Iowa, and it is liquor. See section 5.

### Shopper surface: Open Food Facts, India subset

Live-verified on 1 October 2026 by calling the search API directly:
`https://world.openfoodfacts.org/api/v2/search?countries_tags_en=india` returns
`"count":24613`. The first results are Parle-G, Parle G, and Britannia Bourbon, all with populated
`image_url`. That is exactly the shelf of a Bengaluru grocery store, with real barcodes, real
brands, real categories, product photographs, and Nutri-Score and per-100g nutrient data.

Why it wins: it is the only verified source that is simultaneously real, Indian, image-bearing,
nutrition-bearing and openly licensed. `thelook_ecommerce` is synthetic apparel. Instacart has
49,000 real grocery product names but no prices at all and no absolute dates, and is non-commercial.
UCI Online Retail II is a UK giftware wholesaler. The Kaggle BigBasket and Flipkart scrapes have the
right geography but were scraped against those platforms' terms of service, and a CC0 label applied
by an uploader does not override the originating site's terms, so they carry real risk for a public
submission.

The gap you must be honest about: Open Food Facts contains no prices. The companion Open Prices
project exists at `prices.openfoodfacts.org` under ODbL with a daily Parquet export, but coverage is
overwhelmingly French and European and Indian coverage is negligible. Prices therefore stay modelled,
anchored to a real public reference (see the Department of Consumer Affairs and Agmarknet rows in
section 2) and labelled as modelled.

### Sales Rep surface: `bigquery-public-data.overture_maps.place`

This was not on your candidate list and it is the best find in this exercise.

Overture Maps places data is mirrored into BigQuery public data by CARTO under the Google Cloud
Public Dataset Program, as `bigquery-public-data.overture_maps.place`, synced to the latest monthly
Overture release. It holds more than 64 million real-world place records with `names.primary`,
`taxonomy.primary`, `phones`, addresses, brand and geometry. A documented example query is:

```sql
SELECT id, phones.list[0].element AS phone, names.primary AS name
FROM `bigquery-public-data.overture_maps.place`
WHERE taxonomy.primary = "restaurant"
LIMIT 100;
```

Why it wins: real named retail outlets in Bengaluru, filterable by retail category and bounded by a
Bengaluru bounding box, with zero ingestion, inside BigQuery. Critically, the places theme is
published under CDLA Permissive 2.0 and Apache 2.0 and contains no OpenStreetMap data, so it carries
**none of the ODbL share-alike obligations** that raw OSM would impose on a derived database. That
makes it cleaner for a public repository than the Overpass or Geofabrik routes, and it beats both on
coverage, since Overture blends several commercial POI sources.

The two other Sales Rep needs resolve differently and neither resolves to a public dataset.

**Shelf photographs: keep your own.** No public dataset pairs a planogram specification with a
matching shelf photograph and a compliance label. This is confirmed not just by absence but by the
planogram compliance literature stating it directly, that existing retail detection datasets are
unsuitable because they lack category annotations and reference planograms. The 2025 work in this
area used 15,232 shelf images from 7-Eleven stores that were never publicly released. SKU-110K has
by far the best real shelf photography, 11,743 densely packed images and about 1.73 million boxes,
but its annotations are **single class**, every box is labelled `object` with no product identity,
so it cannot verify that product X sits in slot Y. Worse for you, its licence grants use solely for
academic and non-commercial purposes, so those images cannot ship in a public submission repo. You
already have `demo/samples/shelf_compliant.jpg`, `demo/samples/shelf_sample_2.jpg` and six shelf
videos you captured yourself. Those are licence-clean, they are Indian, and the vision-model approach
needs no training labels. Keep them and add a few more.

**Citable market statistics: swap fiction for public statistics.** The current `kb_documents`
fixtures cite `[SYNTHETIC] Nielsen Retail Audit`. Nielsen, NielsenIQ, Kantar, Euromonitor and
Circana are all commercial subscription products with no public API or bulk data, so a real Nielsen
citation was never achievable. Replace those documents with genuinely citable public statistics:
the US Census Monthly Retail Trade Survey via `https://api.census.gov/data/timeseries/eits/mrts`,
which is a US federal work in the public domain and needs no API key, and the BLS CPI API for
category-level food price series. For Indian grounding, the data.gov.in Agmarknet commodity price
API and MoSPI CPI releases are authoritative and openly reusable under NDSAP.

---

## 2. Dataset reference table

Access method abbreviations: BQ means already in BigQuery public data with zero ingestion, API means
REST pull, DL means direct download, KG means Kaggle CLI.

| Dataset | Contains | Size | Licence | Access | Verified URL |
|---|---|---|---|---|---|
| Iowa Liquor Sales | Store by SKU by day wholesale purchases since 2012-01-01, 24 cols incl. cost, retail price, bottles sold, sale dollars, city, zip | ~30.3M rows | CC BY 4.0 | BQ, `bigquery-public-data.iowa_liquor_sales.sales` | https://catalog.data.gov/dataset/iowa-liquor-sales |
| Overture Maps Places | 64M+ real POIs, names, taxonomy, phones, addresses, brand, geometry; monthly refresh by CARTO | 64M+ rows | CDLA Permissive 2.0 and Apache 2.0, no OSM, no share-alike | BQ, `bigquery-public-data.overture_maps.place` | https://docs.overturemaps.org/getting-data/data-mirrors/bigquery/ |
| Open Food Facts | Barcode, name, brand, categories, images, Nutri-Score, nutrients per 100g; 24,613 India products live-verified | 1.7M products global; 7.93 GB Parquet, ~0.9 GB CSV gz | ODbL 1.0 database, DbCL contents, CC BY-SA images | API and DL and Parquet | https://world.openfoodfacts.org/data |
| dunnhumby The Complete Journey | 2,500 households, ~2 years, basket transactions, household demographics, campaigns, coupons, causal display and feature data | 8 tables, several hundred MB | CC BY 4.0 on the Mendeley mirror; no explicit licence on dunnhumby.com | DL | https://data.mendeley.com/datasets/7myy93ym6k/1 |
| dunnhumby Breakfast at the Frat | Sales with promotion, display and feature flags across five products | Small | Not explicitly stated | DL | https://www.dunnhumby.com/source-files/ |
| Google Trends | `top_terms`, `top_rising_terms`, `international_top_terms`, rolling 5-year, weekly, by region | Large | Google public dataset terms | BQ, `bigquery-public-data.google_trends` | https://support.google.com/trends/answer/12764470 |
| US Census MARTS | Monthly US retail trade turnover by NAICS category | API | Public domain, US federal work | API, no key | https://www.census.gov/retail/ |
| BLS CPI | Monthly US CPI by item category, food series under `CUUR0000SAF` | API | Public domain | API, free key for 500 queries/day | https://www.bls.gov/cpi/ |
| data.gov.in Agmarknet mandi prices | Daily min, max and modal wholesale commodity prices by state, district and market | Large, since 2013 | NDSAP, open incl. commercial, attribution | API, free key required | https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi |
| Dept of Consumer Affairs retail prices | Daily retail and wholesale prices, 22 essential commodities, 555 market centres | Daily tables | Government of India, not explicitly labelled | Web tables only, no API | https://fcainfoweb.nic.in/Reports/DB/DBprices.aspx |
| MoSPI CPI | Monthly India CPI, state and item level, base 2024=100 | PDF and XLSX | Open Government Data India | DL | https://esankhyiki.mospi.gov.in/ |
| UCI Online Retail II | UK online giftware invoices, 2009-12-01 to 2011-12-09, with UnitPrice and InvoiceDate | 1,067,371 rows, 43.5 MB zip, XLSX | CC BY 4.0 | DL | https://archive.ics.uci.edu/dataset/502/online+retail+ii |
| Grocery Store Dataset, Klasson et al. | 5,125 smartphone product images, 81 fine classes, 42 coarse, plus one iconic reference image and text description per class | 5,125 images | MIT | DL, git clone | https://github.com/marcusklasson/GroceryStoreDataset |
| Freiburg Groceries | 4,947 images, 25 food classes, 256x256, plus 37 cluttered scenes | <1 GB | CC BY 4.0 | DL via script | https://github.com/PhilJd/freiburg_groceries_dataset |
| SKU-110K | 11,743 real dense shelf photos, ~1.73M boxes, all single class `object` | ~13.6 GB | Academic and non-commercial only | DL | https://github.com/eg4000/SKU110K_CVPR19 |
| RPC Retail Product Checkout | 83,739 images, 200 SKU classes, checkout tray scenes not shelves | ~15 GB | CC BY-NC-SA 4.0 | KG | https://rpc-dataset.github.io/ |
| Instacart Market Basket | 3.2M orders, ~49k products, aisles and departments; no prices, no absolute dates | ~700 MB | Non-commercial, competition rules | KG, rules acceptance | https://www.kaggle.com/competitions/instacart-market-basket-analysis |
| M5 Forecasting Accuracy | 42,840 series, 3,049 products, 10 stores, 1,941 days, weekly sell prices, SNAP and event flags | ~450 MB | Non-commercial, competition rules confirmed | KG, rules acceptance | https://www.kaggle.com/competitions/m5-forecasting-accuracy |
| Corporación Favorita | item by store by day units with promotion flag, plus oil and holidays | 125,497,040 rows, ~4.65 GB | Competition-restricted, NDA for winners | KG, rules acceptance | https://www.kaggle.com/competitions/favorita-grocery-sales-forecasting |
| Retailrocket | 2,756,101 view, add-to-cart and transaction events; item properties all hashed | ~1 GB | CC BY-NC-SA 4.0 | KG | https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset |
| Walmart Recruiting Store Sales | Weekly store and department sales, MarkDown1-5, IsHoliday, CPI, unemployment | ~30 MB | Competition rules | KG, rules acceptance | https://www.kaggle.com/competitions/walmart-recruiting-store-sales-forecasting |
| Rossmann Store Sales | 1,017,209 daily store rows, 1,115 stores, `Promo`, `Promo2`, holiday flags | ~40 MB | Competition rules | KG, rules acceptance | https://www.kaggle.com/c/rossmann-store-sales |
| thelook_ecommerce | Synthetic apparel ecommerce, 7 tables, ~29,120 products | Moderate | Google public dataset terms | BQ | https://docs.cloud.google.com/bigquery/public-data |
| GA4 obfuscated sample | 92 days of GA4 ecommerce events, 2020-11-01 to 2021-01-31 | ~4.3M events | Google public dataset terms | BQ | https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset |

Named and rejected as unusable: RP2K, official site `pinlandata.com/rp2k_dataset` returns 404 and no
licence is stated on any mirror. Locount, behind a GitLab login. GroZi-120 and GroZi-3.2k, no
confirmed live download. `UniDataPro/grocery-shelves` on Hugging Face has real shelf photos with
facing annotations but is CC BY-NC-ND 4.0 and gated behind contacting a commercial vendor. Open Food
Facts is **not** in BigQuery public data, despite being widely assumed to be. No BigQuery public
dataset was confirmed for BLS CPI, USDA food data, or FDA food enforcement.

---

## 3. Per-surface mapping

Widget names are the render functions in `index.html`; table names are from `gcp/schema.sql`.

### Shopper

| Widget | Source | Transformation |
|---|---|---|
| `renderReco`, `renderSuggest` product cards | Open Food Facts India subset | Filter `countries_tags_en=india`, keep `code`, `product_name`, `brands`, `categories_tags`, `image_url`, `nutriscore_grade`, nutrients. Map the OFF category taxonomy onto the five existing `categories` strings. Load into `products` as `product_id` from barcode, `product_name`, `category`, `brand`. |
| Price shown on every card | Modelled, anchored to public reference | OFF has no prices. Derive `list_price` per category from Agmarknet modal prices and the Consumer Affairs retail series, then hold constant per SKU. Must render with a "modelled price" marker. |
| `renderBasket` totals | `sales_transactions` | Unchanged arithmetic, new product IDs. |
| "Customers also bought" | dunnhumby `transaction_data` | Compute item co-occurrence per basket, keep the top N pairs per product, store as a lookup. dunnhumby product IDs need a category-level bridge to OFF SKUs, since the two catalogues do not share barcodes. Join on category, not on product. |
| Personalisation, `shopperProfiles` | dunnhumby `hh_demographic` plus `transaction_data` | Pick two real households with demographics populated and replay their actual purchase history as `recentBuys`. Only 801 of 2,500 households have demographics, so filter on `has_demographics` first. Names stay invented, the behaviour becomes real. |
| Low-stock flag | `inventory_snapshots` | Stays synthetic, see section 6. |

### Sales Rep

| Widget | Source | Transformation |
|---|---|---|
| `renderRepSide` account and outlet list | `bigquery-public-data.overture_maps.place` | Filter `taxonomy.primary` to retail grocery and convenience types, bound to a Bengaluru bounding box with `ST_WITHIN`, take `names.primary`, address and geometry into `stores` and `accounts`. Real outlet names, real coordinates. |
| Territory grouping, `zone` | Overture geometry | Cluster outlets by ward or distance to derive `territory` rather than hardcoding "Bengaluru South". |
| `renderBrief` store history | `visits`, `accounts` | Stays synthetic. No public source for account order history. |
| `renderPlanoRules` and `loadShelf` vision scoring | Your own `demo/samples/*.jpg` plus new captures | No change to the pipeline. Rules in `planogram_rules` stay modelled on published merchandising practice. Do not ingest SKU-110K into the repo. |
| `renderCitations` citation chips | US Census MARTS, BLS CPI, Agmarknet, MoSPI | Replace the seven `[SYNTHETIC] Nielsen` rows in `kb_documents` with real retrieved statistics. Each becomes one row with a real `title`, a real one-sentence `fact`, `source_type` set to the agency, a real `published_date`, and `is_synthetic` set to `FALSE`. This is the single highest-credibility swap on this surface, because a judge can click through and check the number. |
| Rehearsal buyer and objections | `visit_objections` | Stays synthetic. |

### Business

| Widget | Source | Transformation |
|---|---|---|
| `renderBars` revenue last 7 days | Iowa `sales` | `GROUP BY date, store_number`, `SUM(sale_dollars)`. Feeds `v_daily_store_revenue` with no view rewrite, only a column rename. |
| 7-day forecast with confidence band | Iowa via `ARIMA_PLUS` | `v_daily_store_revenue` already matches. **Change `HOLIDAY_REGION` from `'IN'` to `'US'`** in `forecast.sql`, since the data is Iowan. Leaving it as `'IN'` would model Diwali against Iowa liquor sales, which a sharp judge would catch. |
| Per-SKU reorder quantities | Iowa via `ARIMA_PLUS` | `v_daily_product_units` maps to `GROUP BY date, store_number, item_number`, `SUM(bottles_sold)`. Restrict to the top 200 SKU and store pairs by volume before training, see section 5 on cost. |
| `renderMovers` top movers | Iowa `sales` | Rank by `SUM(sale_dollars)` over trailing 30 days. Real category names from `category_name`. |
| `renderKPIs` revenue, basket, SKU count | Iowa `sales` | Average basket from `sale_dollars` per `invoice_and_item_number` grouping. `totalSKUs` from `COUNT(DISTINCT item_number)`. Conversion rate, NPS and footfall stay synthetic. |
| `renderSegments` customer segments | dunnhumby `hh_demographic` plus `transaction_data` | Derive real segments by clustering households on basket value and visit frequency, then label the clusters. `share_pct`, `avg_basket_value` and `visits_per_week` all become computed. Segment names stay editorial. |
| `renderPromos` promotion uplift | dunnhumby `causal_data`, optionally Breakfast at the Frat | `causal_data` carries real display and feature flags per product, store and week. Compute `observed_uplift_pct` as promoted-week versus matched non-promoted-week sales. This replaces the invented "+22% category sales" with a number you calculated. |
| `renderAlerts` inventory alerts | `inventory_snapshots` | Stays synthetic. |
| Margin figures | Iowa `state_bottle_cost` and `state_bottle_retail` | `margin_rate` becomes `(retail - cost) / retail`, a real computed margin. |

---

## 4. Ingestion path

### Zero ingestion, query in place

Three of the four primary sources need no pipeline at all. Reference them directly, or create views
in your own dataset that project them into the `gcp/schema.sql` column names so the Cloud Run
service and `queries.sql` do not change:

```sql
CREATE OR REPLACE VIEW `${GCP_PROJECT}.${BQ_DATASET}.sales_transactions` AS
SELECT
  invoice_and_item_number                       AS transaction_id,
  1                                             AS line_number,
  TIMESTAMP(date)                               AS txn_ts,
  date                                          AS txn_date,
  CAST(store_number AS STRING)                  AS store_id,
  CAST(item_number AS STRING)                   AS product_id,
  CAST(NULL AS STRING)                          AS customer_id,
  bottles_sold                                  AS quantity,
  state_bottle_retail                           AS unit_price,
  sale_dollars                                  AS line_revenue,
  FALSE                                         AS is_return
FROM `bigquery-public-data.iowa_liquor_sales.sales`
WHERE date >= '2023-01-01';
```

That view alone converts the entire Business surface to real data without moving a byte. The same
trick applies to `overture_maps.place` for `stores`, and to `google_trends` if you want a demand
signal. No auth beyond a GCP project, no licence acceptance, and public dataset storage is not
billed to you. Only query bytes count against the 1 TB per month free tier, so put a `WHERE date >=`
filter on Iowa from the start: the table is partition-friendly by date and scanning all thirteen
years repeatedly is the one way this gets expensive.

### API pull, then load

**Open Food Facts.** Do not use the search API for the bulk pull. The documented limits are about
10 requests per minute for search and 15 per minute for product reads, and exceeding them risks an
IP ban. Two viable routes:

1. Preferred for 24,613 records: paginate the search endpoint at `page_size=100`, which is roughly
   247 requests, and sleep to stay under 10 per minute. That is about 25 minutes unattended, and it
   gives you only Indian products with only the fields you asked for. Send a real `User-Agent` of
   the form `RetailIQ/0.1 (your-email)`, which is required. No API key needed for reads.
2. Or take the nightly static export, `https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz`
   at about 0.9 GB compressed and 9 GB uncompressed, or the 7.93 GB Parquet on Hugging Face, then
   filter to India locally. Heavier, but immune to rate limits.

Land the filtered result as newline-delimited JSON or Parquet in GCS, then `bq load`. Note that
loading from a local file through the console caps at 100 MB, and a compressed CSV cannot exceed
4 GB, so stage via GCS for anything non-trivial.

**Census MARTS and BLS CPI.** Small JSON pulls. MARTS needs no key. BLS gives 25 queries per day
unregistered and 500 registered, and registration is free. Write the handful of retrieved facts
straight into `kb_documents` rows; there is no bulk load here, you want perhaps twenty good citable
sentences, not a corpus.

**Agmarknet via data.gov.in.** Requires free registration and an API key, passed as
`?api-key=...&format=json`. Flag this as the one Indian source with an auth step.

### Download, then load

**dunnhumby The Complete Journey.** Download from the Mendeley mirror, unzip, upload the CSVs to
GCS, `bq load --autodetect` into staging tables, then transform into `customer_segments` and the
co-occurrence lookup. Take the Mendeley copy specifically: dunnhumby.com hosts the files with no
registration but also with no explicit licence statement, whereas the Mendeley record is labelled
CC BY 4.0. Cite the Mendeley DOI.

### Requires auth or licence acceptance, flagged

- Every Kaggle **competition** dataset, M5, Favorita, Instacart, Walmart Recruiting, Rossmann,
  needs a `kaggle.json` token **and** a one-time click-through of the rules page in a browser before
  `kaggle competitions download -c <slug>` will work at all. It returns 403 until you do.
- Kaggle **datasets**, Retailrocket and the dunnhumby mirror, need only `kaggle.json`.
- data.gov.in needs a free API key.
- `UniDataPro/grocery-shelves` needs you to contact a commercial vendor. Do not plan around it.
- SKU-110K needs no auth but its licence forbids non-academic use, which is the blocker.

---

## 5. Effort and risk

Ranked by payoff per day spent.

**Do these. High payoff, low effort.**

1. **Iowa liquor sales into the Business surface. About half a day.** One view, one `HOLIDAY_REGION`
   change, one `WHERE date >=` filter. Converts the revenue chart, the forecast, top movers, margin
   and most of the KPI strip to real data in a single stroke, and makes the BQML ARIMA_PLUS claim
   genuinely load-bearing instead of decorative. This is the highest payoff item on the list by a
   wide margin.
2. **`kb_documents` citations from Census, BLS, Agmarknet and MoSPI. About half a day.** Roughly
   twenty hand-picked real facts. Disproportionate credibility gain, because the citation chips are
   the one part of the demo a judge can independently verify by clicking. It also removes the
   awkwardness of a fake Nielsen citation, given Nielsen is a paid product.
3. **Overture Maps for real Bengaluru outlets. About half a day.** One filtered query, real store
   names on the rep's list, permissively licensed, zero ingestion, and it demonstrates a BigQuery
   public dataset most judges will not have seen.

**Do this if the first three land. Medium effort, good payoff.**

4. **Open Food Facts India catalogue. One to two days.** The pull is straightforward but the
   category mapping onto your five existing categories is fiddly, and you must decide how prices are
   presented. Big visible payoff on the Shopper surface, since real product names, real brands and
   real photographs are immediately obvious to a viewer.
5. **dunnhumby for segments and promotion uplift. Two to three days.** Real clustering and a real
   computed uplift number are strong, but this is genuine analytical work plus a category bridge
   between two unrelated catalogues. Cut this first if time runs short.

**Traps. Do not start these.**

- **Corporación Favorita.** 125,497,040 rows, about 4.65 GB uncompressed, competition-restricted.
  Loading and reshaping it will eat three or four days and cannot be used commercially. There is no
  version of this that pays off before 18 October.
- **M5.** Cleaner than Favorita but still wide-format with 1,919 date columns needing an unpivot,
  still non-commercial, and it gives you nothing Iowa does not already give you inside BigQuery.
- **SKU-110K.** Tempting because the shelf photography is the best available, but single-class
  annotations cannot support product-identity compliance, and the academic-only licence means the
  images cannot ship in a public repo. Your own photos are better on both counts.
- **Kaggle BigBasket and Flipkart scrapes.** Right geography, wrong provenance. Scraped against
  platform terms of service, and an uploader-applied CC0 tag does not cure that. Not worth the
  exposure on a submission with your name on it.
- **Instacart.** Widely recommended for basket analysis, but it has no prices and no absolute dates,
  which rules out both the price display and any time series. Also non-commercial, and the
  standalone `instacart.com/datasets/grocery-shopping-2017` URL currently returns 404, so only the
  Kaggle route works.
- **Retailrocket.** Every item property is hashed, so there are no readable product names, prices or
  descriptions. Useless for a surface whose whole point is showing products to a shopper.
- **fcainfoweb.nic.in.** Genuinely useful Indian retail prices, but there is no API and no bulk
  download, only web tables. Scraping it is a half-day detour for data you can reference instead.

**The single biggest risk: geographic and category coherence.**

This is the thing most likely to be noticed and it is not a technical problem. The README, the
fixtures and the deck all say Bengaluru modern-trade grocery. The recommended stack forecasts Iowa
liquor, segments US households, and catalogues Indian packaged food. If you present that as one
store, the first judge who reads a column header will find Iowa, and the whole honesty framing the
README leans on collapses at once.

Two defensible resolutions, and you must pick one explicitly:

- **Preferred: change the framing, not the data.** Present the Business surface as operating on a
  real Iowa retail network and the Shopper surface on a real Indian catalogue, and say plainly that
  RetailIQ is warehouse-portable, the same schema and the same models against whichever market's
  data is loaded. That turns the mismatch into a feature and it is true.
- **Or: keep Bengaluru and label every derived figure.** Keep Iowa as the statistical engine but
  state in the UI that volumes are drawn from a real public retail dataset and re-expressed, and
  never imply the rupee figures are observed Bengaluru revenue.

What you must not do is silently relabel `store_number 2633` as "FreshMart Express Koramangala".
That is exactly the kind of mocking-as-real the README promises not to do.

Second risk, smaller but concrete: **per-SKU ARIMA_PLUS cost.** BigQuery ML supports up to 100
million time series, so volume is not a hard limit, but Iowa has thousands of stores and thousands
of items, and the cross product trained at full history will burn slot time and query bytes on
hundreds of thousands of low-volume series to no benefit. Restrict `v_daily_product_units` to the
top few hundred store and SKU pairs by volume, keep the existing `MAX_TIME_SERIES_LENGTH = 365`, and
schedule retraining daily rather than per request, as `forecast.sql` already advises.

---

## 6. What should stay synthetic

Your instinct was right, and the list is slightly longer than you guessed. There is no public source
for any of the following, and for several of them there should not be, because a real version would
be personal or commercially confidential data.

**Field sales records.** `visits` and `visit_objections` in full. Buyer objection history, visit
objectives, open tasks, visit cadence policy, last order value, orders in the last six months, lost
listings. This is CRM data. No retailer or CPG company publishes it, and the commercial panels that
come closest, Nielsen and Kantar, sell aggregates rather than visit logs.

**Buyer and rep identities.** `accounts.contact_name`, `contact_role`, `contact_style`, and the
`sales_reps` table. These must stay invented, not because no data exists but because real named
buyers with a description of how to persuade them would be personal data used without consent. Note
that even after Overture supplies real outlet names, the people inside them stay fictional. Say so.

**Store operational targets and experience metrics.** `stores.daily_revenue_target`,
`stores.latest_nps`, `nps_as_of`. These come from a merchandising planning system and a CX survey
platform. The schema comments already say this, which is good, keep them.

**Footfall.** `store_traffic_daily`, and therefore `kpis.conversionRate`. Door-counter data is not
published. Aggregate mobility indices exist in `bigquery-public-data.covid19_open_data`, but they are
a regional index rather than store entries, and using them as a conversion denominator would be a
fabrication dressed as a source. Keep it synthetic rather than borrow false precision.

**Inventory positions.** `inventory_snapshots`, units on hand, reorder points, units on order,
supplier lead times, and so the whole `renderAlerts` widget. Iowa gives you wholesale purchases, not
shelf stock, and no public dataset carries live on-hand quantities. The reorder recommendation stays
a synthetic overlay on a real forecast, which is worth stating in exactly those terms.

**Planogram specifications.** `planogram_rules`. Real planograms are proprietary merchandising
assets. The five rules you have are modelled on standard practice and that is the right approach.
The scoring against them is real, since the vision model genuinely evaluates a genuine photograph.

**Segment names.** Even after dunnhumby makes `share_pct`, `avg_basket_value` and `visits_per_week`
real computed figures, "Weekend Warriors" and "Deal Seekers" remain editorial labels you assigned to
clusters. That is normal analytical practice, but do not present the names as discovered.

**Prices on Indian products.** As covered above, Open Food Facts has no prices and Open Prices has
no meaningful Indian coverage. Prices stay modelled against a public reference.

### Labelling requirement

The current fixtures label synthetic knowledge-base documents with a `[SYNTHETIC]` title prefix and
the schema already carries `kb_documents.is_synthetic`. After this migration the codebase contains a
mixture, so that single flag is no longer enough. Recommended minimum:

- Add a provenance marker per table or per view, real, derived, or synthetic, and surface it in the
  UI wherever a figure is displayed.
- Keep the `[SYNTHETIC]` prefix on every remaining invented knowledge-base document, and remove it
  only from rows that carry a real agency, a real publication date and a resolvable URL.
- Update the README data note, which currently says all figures are synthetic. After this work that
  statement becomes false in the other direction, which is its own credibility problem. It should
  name which surfaces run on which public dataset, with licences and attribution.
- Attribution is a licence obligation, not a courtesy. Iowa liquor sales requires CC BY 4.0
  attribution, Open Food Facts requires ODbL attribution for the database and CC BY-SA for images,
  which also means a share-alike obligation if you publish an enriched product database, Overture
  requires CDLA Permissive 2.0 attribution, and the dunnhumby Mendeley record requires CC BY 4.0
  attribution. Put all four in the README before submission.
