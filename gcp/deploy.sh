#!/usr/bin/env bash
# RetailIQ reproducible Google Cloud deployment. Private IAM access is default.
# Full setup: GCP_PROJECT=my-project bash gcp/deploy.sh all
# Judge access: PUBLIC_DEMO=true APP_KEY_FILE=/secure/token.txt bash gcp/deploy.sh all
# APP_KEY_FILE must contain a private, independently shared access token (24+ chars).
set -euo pipefail

: "${GCP_PROJECT:?set GCP_PROJECT to your Google Cloud project id}"
BQ_DATASET="${BQ_DATASET:-retailiq}"
BQ_LOCATION="${BQ_LOCATION:-asia-south1}"
REGION="${REGION:-asia-south1}"
FIRESTORE_LOCATION="${FIRESTORE_LOCATION:-${REGION}}"
VERTEX_LOCATION="${VERTEX_LOCATION:-global}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.6-flash}"
SERVICE="${SERVICE:-retailiq-api}"
RUNTIME_SA="${RUNTIME_SA:-retailiq-api}"
PHOTO_BUCKET="${PHOTO_BUCKET:-${GCP_PROJECT}-retailiq-shelf-photos}"
PHOTO_RETENTION_DAYS="${PHOTO_RETENTION_DAYS:-30}"
DEFAULT_STORE_ID="${DEFAULT_STORE_ID:-BLR-KOR-014}"
DEMO_AS_OF_DATE="${DEMO_AS_OF_DATE:-2026-10-22}"
RAG_MODE="${RAG_MODE:-keyword}"
ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-}"
SECRET_NAME="${SECRET_NAME:-retailiq-gemini-key}"
GEMINI_KEY_FILE="${GEMINI_KEY_FILE:-}"
APP_SECRET_NAME="${APP_SECRET_NAME:-retailiq-access-key}"
APP_KEY_FILE="${APP_KEY_FILE:-}"
PUBLIC_DEMO="${PUBLIC_DEMO:-false}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SEED_DIR="${SEED_DIR:-seed_out}"
SEED_DAYS="${SEED_DAYS:-180}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SA_EMAIL="${RUNTIME_SA}@${GCP_PROJECT}.iam.gserviceaccount.com"
WORK_DIR="$(mktemp -d)"
trap 'rm -f -- "${WORK_DIR}/env.json" "${WORK_DIR}/lifecycle.json" "${WORK_DIR}/indexes.json"; rmdir -- "${WORK_DIR}"' EXIT

log() { printf '\n== %s\n' "$*"; }
# Only identifiers reach SQL substitution. Values and dates use named parameters in the API.
[[ "$GCP_PROJECT" =~ ^[a-z][a-z0-9-]{4,61}[a-z0-9]$ ]] || { echo "Invalid Google Cloud project ID" >&2; exit 2; }
[[ "$BQ_DATASET" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || { echo "Invalid BigQuery dataset ID" >&2; exit 2; }
[[ "$PHOTO_RETENTION_DAYS" =~ ^[1-9][0-9]*$ ]] || { echo "PHOTO_RETENTION_DAYS must be a positive integer" >&2; exit 2; }
[[ "$PUBLIC_DEMO" == true || "$PUBLIC_DEMO" == false ]] || { echo "PUBLIC_DEMO must be true or false" >&2; exit 2; }

render() {
  sed -e "s|\${GCP_PROJECT}|${GCP_PROJECT}|g" \
      -e "s|\${BQ_DATASET}|${BQ_DATASET}|g" \
      -e "s|\${BQ_LOCATION}|${BQ_LOCATION}|g" "$1"
}
bq_script() {
  render "$1" | bq --project_id="${GCP_PROJECT}" --location="${BQ_LOCATION}" query --use_legacy_sql=false --format=none
}
enable_apis() {
  log "Enabling application APIs"
  gcloud services enable bigquery.googleapis.com bigqueryconnection.googleapis.com \
    run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
    aiplatform.googleapis.com secretmanager.googleapis.com storage.googleapis.com \
    firestore.googleapis.com --project="${GCP_PROJECT}" --quiet
}
create_schema() {
  if ! bq --project_id="${GCP_PROJECT}" show --dataset "${GCP_PROJECT}:${BQ_DATASET}" >/dev/null 2>&1; then
    bq --project_id="${GCP_PROJECT}" mk --dataset --location="${BQ_LOCATION}" \
      --description="RetailIQ analytics (synthetic demonstration dataset)" "${GCP_PROJECT}:${BQ_DATASET}"
  fi
  log "Applying warehouse schema and idempotent migrations"
  bq_script "${HERE}/schema.sql"
}
load_seed() {
  log "Generating explicitly synthetic seed history (${SEED_DAYS} days)"
  "${PYTHON_BIN}" "${HERE}/seed_data.py" --out "${HERE}/${SEED_DIR}" --as-of "${DEMO_AS_OF_DATE}" --days "${SEED_DAYS}"
  for file in "${HERE}/${SEED_DIR}"/*.ndjson; do
    local table
    table="$(basename "${file}" .ndjson)"
    bq --project_id="${GCP_PROJECT}" --location="${BQ_LOCATION}" load \
      --source_format=NEWLINE_DELIMITED_JSON --replace "${GCP_PROJECT}:${BQ_DATASET}.${table}" "${file}"
  done
}
train_forecast() { log "Training ARIMA_PLUS and materialising forecasts"; bq_script "${HERE}/forecast.sql"; }

create_firestore() {
  log "Provisioning the default Firestore database and manager-events index"
  if ! gcloud firestore databases describe --database='(default)' --project="${GCP_PROJECT}" >/dev/null 2>&1; then
    gcloud firestore databases create --database='(default)' --location="${FIRESTORE_LOCATION}" \
      --type=firestore-native --project="${GCP_PROJECT}" --quiet
  fi
  gcloud firestore indexes composite list --database='(default)' --filter=COLLECTION_GROUP:visit_events \
    --project="${GCP_PROJECT}" --format=json > "${WORK_DIR}/indexes.json"
  if ! "${PYTHON_BIN}" -c 'import json,sys; rows=json.load(open(sys.argv[1])); ok=any([(f.get("fieldPath"),f.get("order")) for f in r.get("fields",[]) if f.get("fieldPath")!="__name__"]==[("store_id","ASCENDING"),("created_at","DESCENDING")] and r.get("queryScope")=="COLLECTION" and r.get("state") in ("READY","CREATING") for r in rows); sys.exit(0 if ok else 1)' "${WORK_DIR}/indexes.json"; then
    gcloud firestore indexes composite create --database='(default)' --collection-group=visit_events \
      --query-scope=collection --field-config=field-path=store_id,order=ascending \
      --field-config=field-path=created_at,order=descending --project="${GCP_PROJECT}" --quiet
  fi
}
create_bucket() {
  log "Provisioning private shelf evidence storage with ${PHOTO_RETENTION_DAYS}-day lifecycle deletion"
  if ! gcloud storage buckets describe "gs://${PHOTO_BUCKET}" --project="${GCP_PROJECT}" >/dev/null 2>&1; then
    gcloud storage buckets create "gs://${PHOTO_BUCKET}" --project="${GCP_PROJECT}" \
      --location="${REGION}" --uniform-bucket-level-access --public-access-prevention
  fi
  "${PYTHON_BIN}" -c 'import json,sys; json.dump({"rule":[{"action":{"type":"Delete"},"condition":{"age":int(sys.argv[2]),"matchesPrefix":["shelf-evidence/"]}}]},open(sys.argv[1],"w"))' "${WORK_DIR}/lifecycle.json" "${PHOTO_RETENTION_DAYS}"
  gcloud storage buckets update "gs://${PHOTO_BUCKET}" --uniform-bucket-level-access \
    --public-access-prevention --clear-soft-delete --lifecycle-file="${WORK_DIR}/lifecycle.json" --project="${GCP_PROJECT}" --quiet
}
create_service_account() {
  if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${GCP_PROJECT}" >/dev/null 2>&1; then
    gcloud iam service-accounts create "${RUNTIME_SA}" --project="${GCP_PROJECT}" --display-name="RetailIQ Cloud Run API"
  fi
  for role in roles/bigquery.jobUser roles/bigquery.dataViewer roles/aiplatform.user roles/datastore.user; do
    gcloud projects add-iam-policy-binding "${GCP_PROJECT}" --member="serviceAccount:${SA_EMAIL}" \
      --role="${role}" --condition=None --quiet >/dev/null
  done
  gcloud storage buckets add-iam-policy-binding "gs://${PHOTO_BUCKET}" --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/storage.objectCreator --project="${GCP_PROJECT}" --quiet >/dev/null
  gcloud storage buckets add-iam-policy-binding "gs://${PHOTO_BUCKET}" --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/storage.objectViewer --project="${GCP_PROJECT}" --quiet >/dev/null
}
secret_exists() {
  gcloud secrets versions list "$1" --project="${GCP_PROJECT}" --filter='state:enabled' \
    --limit=1 --format='value(name)' 2>/dev/null | grep -q .
}
wire_one_secret() {
  local name="$1" file="$2"
  if ! gcloud secrets describe "$name" --project="${GCP_PROJECT}" >/dev/null 2>&1; then
    gcloud secrets create "$name" --project="${GCP_PROJECT}" --replication-policy=automatic --quiet
  fi
  if [[ -n "$file" ]]; then
    [[ -f "$file" ]] || { echo "Secret input file does not exist" >&2; exit 2; }
    # Contents go straight to Secret Manager. Never echo or place them in CLI arguments.
    gcloud secrets versions add "$name" --project="${GCP_PROJECT}" --data-file="$file" --quiet >/dev/null
  fi
  gcloud secrets add-iam-policy-binding "$name" --project="${GCP_PROJECT}" \
    --member="serviceAccount:${SA_EMAIL}" --role=roles/secretmanager.secretAccessor --quiet >/dev/null
}
wire_secrets() {
  if [[ -n "$GEMINI_KEY_FILE" ]]; then wire_one_secret "$SECRET_NAME" "$GEMINI_KEY_FILE"; fi
  if [[ -n "$APP_KEY_FILE" ]]; then
    "${PYTHON_BIN}" -c 'import pathlib,sys; raw=pathlib.Path(sys.argv[1]).read_text().strip(); sys.exit(0 if len(raw)>=24 and "\n" not in raw else "Application token must be one line with at least 24 characters")' "$APP_KEY_FILE"
    wire_one_secret "$APP_SECRET_NAME" "$APP_KEY_FILE"
  elif [[ "$PUBLIC_DEMO" == true ]]; then
    secret_exists "$APP_SECRET_NAME" || { echo "PUBLIC_DEMO requires APP_KEY_FILE or an existing application-token secret. Refusing anonymous deployment." >&2; exit 2; }
    wire_one_secret "$APP_SECRET_NAME" ""
  fi
}
preflight_service() {
  # The service-only command is explicit about prerequisites; it never claims to provision warehouse data.
  bq --project_id="${GCP_PROJECT}" show "${GCP_PROJECT}:${BQ_DATASET}.product_forecast_daily" >/dev/null || {
    echo "Warehouse/forecasts are missing. Run: bash gcp/deploy.sh all" >&2; exit 2;
  }
}
provision_build_account() {
  local project_number build_sa
  project_number="$(gcloud projects describe "${GCP_PROJECT}" --format='value(projectNumber)')"
  [[ "$project_number" =~ ^[0-9]+$ ]] || { echo "Could not resolve the project number for Cloud Build permissions" >&2; exit 2; }
  build_sa="${project_number}-compute@developer.gserviceaccount.com"
  gcloud projects add-iam-policy-binding "${GCP_PROJECT}" --member="serviceAccount:${build_sa}" \
    --role=roles/run.builder --condition=None --quiet >/dev/null
}
deploy_service() {
  provision_build_account
  local secrets=() access=(--no-allow-unauthenticated) trust_iam=true
  if [[ -n "$GEMINI_KEY_FILE" ]] && secret_exists "$SECRET_NAME"; then secrets+=("GEMINI_API_KEY=${SECRET_NAME}:latest"); fi
  if [[ "$PUBLIC_DEMO" == true || -n "$APP_KEY_FILE" ]]; then
    secrets+=("RETAILIQ_API_KEY=${APP_SECRET_NAME}:latest")
  fi
  if [[ "$PUBLIC_DEMO" == true ]]; then access=(--allow-unauthenticated); trust_iam=false; fi
  export GCP_PROJECT BQ_DATASET BQ_LOCATION VERTEX_LOCATION GEMINI_MODEL DEFAULT_STORE_ID DEMO_AS_OF_DATE RAG_MODE ALLOWED_ORIGINS PHOTO_BUCKET PHOTO_RETENTION_DAYS
  "${PYTHON_BIN}" -c 'import json,os,sys; names="GCP_PROJECT BQ_DATASET BQ_LOCATION VERTEX_LOCATION GEMINI_MODEL DEFAULT_STORE_ID DEMO_AS_OF_DATE RAG_MODE ALLOWED_ORIGINS PHOTO_BUCKET PHOTO_RETENTION_DAYS".split(); env={k:os.environ[k] for k in names}; env.update(RETAILIQ_TRUST_IAM=sys.argv[2],RETAILIQ_OPEN_DEMO="false",DATA_IS_SYNTHETIC="true",AI_REQUESTS_PER_MINUTE="10"); json.dump(env,open(sys.argv[1],"w"))' "${WORK_DIR}/env.json" "$trust_iam"
  local secret_args=(--clear-secrets)
  if [[ ${#secrets[@]} -gt 0 ]]; then local joined; joined="$(IFS=,; echo "${secrets[*]}")"; secret_args=(--set-secrets "$joined"); fi
  log "Deploying Cloud Run (${PUBLIC_DEMO}: application-token judge access; false: private IAM access)"
  gcloud run deploy "${SERVICE}" --project="${GCP_PROJECT}" --region="${REGION}" \
    --source="${HERE}/.." --service-account="${SA_EMAIL}" "${access[@]}" \
    --cpu=1 --memory=1Gi --concurrency=20 --timeout=300 --min-instances=0 --max-instances=3 \
    --env-vars-file="${WORK_DIR}/env.json" "${secret_args[@]}" --quiet
  local url
  url="$(gcloud run services describe "${SERVICE}" --project="${GCP_PROJECT}" --region="${REGION}" --format='value(status.url)')"
  log "Service URL: ${url}"
  if [[ "$PUBLIC_DEMO" == true ]]; then echo "Share the access token separately through your approved channel. It is not printed or embedded in the site."; else echo "Use an IAM-authenticated Cloud Run proxy to open the application."; fi
}
case "${1:-all}" in
  schema) enable_apis; create_schema ;;
  seed) load_seed ;;
  forecast) train_forecast ;;
  evaluate) bq_script "${HERE}/evaluate_forecast.sql" ;;
  infrastructure) enable_apis; create_bucket; create_firestore; create_service_account ;;
  service) enable_apis; preflight_service; create_bucket; create_firestore; create_service_account; wire_secrets; deploy_service ;;
  all) enable_apis; create_schema; load_seed; train_forecast; create_bucket; create_firestore; create_service_account; wire_secrets; deploy_service ;;
  *) echo "Unknown step: $1 (all, schema, seed, forecast, evaluate, infrastructure, service)" >&2; exit 2 ;;
esac
log "Done"
