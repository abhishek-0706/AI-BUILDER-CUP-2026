#!/usr/bin/env bash
#
# RetailIQ - stand up the GCP backend.
#
# Safe to re-run. Every step either creates something that does not exist or
# replaces its own output. Nothing here contains a secret; the Gemini key, if
# you use one at all, is read from a file you point at and stored in Secret
# Manager.
#
# Usage:
#   export GCP_PROJECT=my-project
#   ./deploy.sh                 # full run
#   ./deploy.sh schema          # dataset and tables only
#   ./deploy.sh seed            # regenerate and load seed data
#   ./deploy.sh forecast        # train ARIMA_PLUS and materialise the horizon
#   ./deploy.sh service         # build and deploy Cloud Run only
#
set -euo pipefail

: "${GCP_PROJECT:?set GCP_PROJECT to your Google Cloud project id}"

BQ_DATASET="${BQ_DATASET:-retailiq}"
BQ_LOCATION="${BQ_LOCATION:-asia-south1}"
REGION="${REGION:-asia-south1}"
VERTEX_LOCATION="${VERTEX_LOCATION:-asia-south1}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.5-flash-lite}"
SERVICE="${SERVICE:-retailiq-api}"
RUNTIME_SA="${RUNTIME_SA:-retailiq-api}"
PHOTO_BUCKET="${PHOTO_BUCKET:-${GCP_PROJECT}-retailiq-shelf-photos}"
DEFAULT_STORE_ID="${DEFAULT_STORE_ID:-BLR-KOR-014}"
DEMO_AS_OF_DATE="${DEMO_AS_OF_DATE:-2026-09-27}"
RAG_MODE="${RAG_MODE:-keyword}"
ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-*}"
SECRET_NAME="${SECRET_NAME:-retailiq-gemini-key}"
# Optional. Path to a file whose contents are an AI Studio key. Only needed if
# you want the keyed fallback instead of Vertex AI service-account auth.
GEMINI_KEY_FILE="${GEMINI_KEY_FILE:-}"

SEED_DIR="${SEED_DIR:-seed_out}"
SEED_DAYS="${SEED_DAYS:-180}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SA_EMAIL="${RUNTIME_SA}@${GCP_PROJECT}.iam.gserviceaccount.com"

log() { printf '\n== %s\n' "$*"; }

# Substitute the ${...} placeholders in the SQL files. Uses sed rather than
# envsubst so there is no gettext dependency.
render() {
  sed -e "s|\${GCP_PROJECT}|${GCP_PROJECT}|g" \
      -e "s|\${BQ_DATASET}|${BQ_DATASET}|g" \
      -e "s|\${BQ_LOCATION}|${BQ_LOCATION}|g" "$1"
}

bq_script() {
  render "$1" | bq --project_id="${GCP_PROJECT}" --location="${BQ_LOCATION}" \
    query --use_legacy_sql=false --format=none
}

# ---------------------------------------------------------------------------

enable_apis() {
  log "Enabling APIs"
  gcloud services enable \
    bigquery.googleapis.com \
    bigqueryconnection.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    aiplatform.googleapis.com \
    secretmanager.googleapis.com \
    storage.googleapis.com \
    --project="${GCP_PROJECT}"
}

create_schema() {
  log "Creating dataset ${BQ_DATASET} in ${BQ_LOCATION}"
  if ! bq --project_id="${GCP_PROJECT}" show --dataset "${GCP_PROJECT}:${BQ_DATASET}" >/dev/null 2>&1; then
    bq --project_id="${GCP_PROJECT}" mk --dataset \
      --location="${BQ_LOCATION}" \
      --description="RetailIQ retail analytics warehouse (synthetic demo data)" \
      "${GCP_PROJECT}:${BQ_DATASET}"
  else
    echo "dataset already exists, leaving it alone"
  fi

  log "Applying schema.sql"
  bq_script "${HERE}/schema.sql"
}

load_seed() {
  log "Generating seed data (${SEED_DAYS} days)"
  python3 "${HERE}/seed_data.py" --out "${HERE}/${SEED_DIR}" \
    --as-of "${DEMO_AS_OF_DATE}" --days "${SEED_DAYS}"

  log "Loading seed data into ${BQ_DATASET}"
  for file in "${HERE}/${SEED_DIR}"/*.ndjson; do
    table="$(basename "${file}" .ndjson)"
    echo "  ${table}"
    # --replace keeps the load idempotent; the table schema already exists so
    # there is no autodetect and no chance of a silent type change.
    bq --project_id="${GCP_PROJECT}" --location="${BQ_LOCATION}" load \
      --source_format=NEWLINE_DELIMITED_JSON \
      --replace \
      "${GCP_PROJECT}:${BQ_DATASET}.${table}" \
      "${file}"
  done
}

train_forecast() {
  log "Training ARIMA_PLUS models and materialising the forecast"
  bq_script "${HERE}/forecast.sql"
}

create_bucket() {
  log "Shelf photo bucket gs://${PHOTO_BUCKET}"
  if ! gcloud storage buckets describe "gs://${PHOTO_BUCKET}" --project="${GCP_PROJECT}" >/dev/null 2>&1; then
    gcloud storage buckets create "gs://${PHOTO_BUCKET}" \
      --project="${GCP_PROJECT}" \
      --location="${REGION}" \
      --uniform-bucket-level-access
  else
    echo "bucket already exists"
  fi
}

create_service_account() {
  log "Runtime service account ${SA_EMAIL}"
  if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${GCP_PROJECT}" >/dev/null 2>&1; then
    gcloud iam service-accounts create "${RUNTIME_SA}" \
      --project="${GCP_PROJECT}" \
      --display-name="RetailIQ Cloud Run API"
  else
    echo "service account already exists"
  fi

  # Least privilege: read data, run query jobs, call Vertex AI, write photos.
  for role in roles/bigquery.jobUser roles/bigquery.dataViewer roles/aiplatform.user; do
    gcloud projects add-iam-policy-binding "${GCP_PROJECT}" \
      --member="serviceAccount:${SA_EMAIL}" \
      --role="${role}" \
      --condition=None \
      --quiet >/dev/null
  done

  gcloud storage buckets add-iam-policy-binding "gs://${PHOTO_BUCKET}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/storage.objectAdmin \
    --project="${GCP_PROJECT}" \
    --quiet >/dev/null
}

wire_secret() {
  log "Secret Manager: ${SECRET_NAME}"
  if ! gcloud secrets describe "${SECRET_NAME}" --project="${GCP_PROJECT}" >/dev/null 2>&1; then
    gcloud secrets create "${SECRET_NAME}" \
      --project="${GCP_PROJECT}" \
      --replication-policy=automatic
  fi

  if [[ -n "${GEMINI_KEY_FILE}" ]]; then
    if [[ ! -f "${GEMINI_KEY_FILE}" ]]; then
      echo "GEMINI_KEY_FILE=${GEMINI_KEY_FILE} does not exist" >&2
      exit 1
    fi
    log "Adding a new version of ${SECRET_NAME} from ${GEMINI_KEY_FILE}"
    gcloud secrets versions add "${SECRET_NAME}" \
      --project="${GCP_PROJECT}" \
      --data-file="${GEMINI_KEY_FILE}"
  else
    echo "no GEMINI_KEY_FILE given, so no key version is added."
    echo "the service will use Vertex AI with the runtime service account, which is the preferred path."
  fi

  gcloud secrets add-iam-policy-binding "${SECRET_NAME}" \
    --project="${GCP_PROJECT}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/secretmanager.secretAccessor \
    --quiet >/dev/null
}

deploy_service() {
  log "Deploying Cloud Run service ${SERVICE} to ${REGION}"

  local secret_args=()
  # Only mount the key if a version actually exists, otherwise the revision
  # would fail to start.
  if gcloud secrets versions list "${SECRET_NAME}" --project="${GCP_PROJECT}" \
       --filter="state:enabled" --limit=1 --format="value(name)" 2>/dev/null | grep -q .; then
    secret_args=(--set-secrets "GEMINI_API_KEY=${SECRET_NAME}:latest")
    echo "mounting ${SECRET_NAME} as GEMINI_API_KEY"
  else
    echo "no enabled secret version, deploying with Vertex AI auth only"
  fi

  gcloud run deploy "${SERVICE}" \
    --project="${GCP_PROJECT}" \
    --region="${REGION}" \
    --source="${HERE}" \
    --service-account="${SA_EMAIL}" \
    --allow-unauthenticated \
    --cpu=1 --memory=1Gi \
    --concurrency=40 \
    --timeout=300 \
    --min-instances=0 --max-instances=10 \
    --set-env-vars="GCP_PROJECT=${GCP_PROJECT},BQ_DATASET=${BQ_DATASET},BQ_LOCATION=${BQ_LOCATION},VERTEX_LOCATION=${VERTEX_LOCATION},GEMINI_MODEL=${GEMINI_MODEL},DEFAULT_STORE_ID=${DEFAULT_STORE_ID},DEMO_AS_OF_DATE=${DEMO_AS_OF_DATE},RAG_MODE=${RAG_MODE},ALLOWED_ORIGINS=${ALLOWED_ORIGINS},PHOTO_BUCKET=${PHOTO_BUCKET}" \
    "${secret_args[@]}"

  local url
  url="$(gcloud run services describe "${SERVICE}" --project="${GCP_PROJECT}" \
        --region="${REGION}" --format='value(status.url)')"
  log "Service URL: ${url}"
  echo "  health:   ${url}/healthz"
  echo "  kpis:     ${url}/api/kpis"
  echo "  forecast: ${url}/api/forecast"
}

# ---------------------------------------------------------------------------

case "${1:-all}" in
  schema)   create_schema ;;
  seed)     load_seed ;;
  forecast) train_forecast ;;
  service)  create_bucket; create_service_account; wire_secret; deploy_service ;;
  all)
    enable_apis
    create_schema
    load_seed
    train_forecast
    create_bucket
    create_service_account
    wire_secret
    deploy_service
    ;;
  *)
    echo "unknown step: $1 (expected one of: all schema seed forecast service)" >&2
    exit 2
    ;;
esac

log "Done"
