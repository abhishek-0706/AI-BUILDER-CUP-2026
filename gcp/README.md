# RetailIQ on Google Cloud

## Current release and hosting status

The current browser release uses the **free static profile**: `backend:false`, `free_only:true`, and optional direct Gemini requests with an explicitly confirmed unbilled Google AI Studio key. The [public recorded walkthrough](https://retailiq-free-20261018-7ce297.web.app/?demo=recorded) and [free static workspace](https://retailiq-free-20261018-7ce297.web.app/) are deployed on Firebase Spark in an unbilled personal project. The no-key recorded walkthrough also works locally. The selected free-profile model has **not** received a live quality evaluation; offline transport and quota-stop tests use intercepted responses.

Company credits are approved for use, but the available credit balance has not been verified. An optional future company backend needs an organization-approved sandbox project ID and the required project permissions. An authenticated company Google account alone does not establish those permissions or a credit balance. The current public release is the free Firebase static site, not a company backend.

The previous personal cloud deployment is a **historical reference**, not the current hosting destination. Billing on the earlier Cloud Run reference project has been disabled; the new Firebase Spark project is unbilled. Disabling billing does not verify or settle any previously accrued charges; the historical balance remains unverified. Retired personal URLs must not be presented as live submission links.

## Run the free static profile

From the repository root:

```powershell
python -m http.server 5190 --bind 127.0.0.1
```

Open `http://localhost:5190/index.html?role=rep` and choose **Try guided demo**. Static visit events stay in this browser. Cloud evidence retention and server analytics are unavailable in this profile.

Live AI is optional. Settings requires confirmation that the supplied key belongs to an unbilled AI Studio project; the browser cannot independently verify billing. HTTP 429 stops further requests in the page. There is no automatic retry, alternate model or paid backend fallback. An unbilled project is necessary for the provider's free-quota limit to prevent paid usage.

The separate Firebase Hosting helper accepts only an explicitly verified unbilled project and uploads allowlisted public files. It does not link billing or use Cloud Build, Cloud Run or Vertex AI. The current release uses this path for the allowlisted application, deck and final demo video, with billing-disabled checks at four deployment checkpoints. The [public video player](https://retailiq-free-20261018-7ce297.web.app/demo.html) and [presentation PDF](https://retailiq-free-20261018-7ce297.web.app/pitch-slides.pdf) share the same free site.

```powershell
# Entirely local validation; no Google or model calls:
.\.venv\Scripts\python.exe gcp/deploy_free.py --project YOUR_UNBILLED_PROJECT --check-only

# Deployment example for an approved unbilled project and explicitly selected account:
.\.venv\Scripts\python.exe gcp/deploy_free.py --project YOUR_UNBILLED_PROJECT --account YOUR_APPROVED_GOOGLE_ACCOUNT
```

The helper checks `billingEnabled:false` before provisioning and again before finalization and release, keeps OAuth tokens in memory, and stops on quota errors. See the [official Hosting REST flow](https://firebase.google.com/docs/hosting/api-deploy) and [Hosting usage limits](https://firebase.google.com/docs/hosting/usage-quotas-pricing).

## Connect an approved company account

Authentication uses Google's browser sign-in flow. Do not place passwords, verification codes or private keys in chat or repository files. A portable CLI can be used from ignored `tmp/cloud-tools/google-cloud-sdk/bin/gcloud.cmd`; see the [official installation guide](https://docs.cloud.google.com/sdk/docs/install-sdk).

```powershell
.\gcp\connect-account.ps1 -Account "YOUR_COMPANY_GOOGLE_ACCOUNT"
```

Once the company provides an approved sandbox project, verify access with its actual ID. The helper can select that account/project in the local CLI configuration. Selection is not proof that company billing permissions or credit balance are sufficient.

## Company backend deployment path

The following is a prepared implementation path, **not a completed company deployment**. It requires the approved sandbox ID, company billing authorization and service-provisioning permissions. Use the explicitly selected company account; do not deploy against the retired personal project.

```powershell
.\gcp\deploy.ps1 -ProjectId "APPROVED_COMPANY_SANDBOX_ID" -Account "YOUR_COMPANY_GOOGLE_ACCOUNT" -Mode all
```

The wrapper sets and restores the process account/project/Python environment. It does not link a billing account. `all` enables APIs, applies BigQuery schema migrations, loads labelled synthetic rows, trains forecasts, provisions Firestore and its index, creates private evidence storage, grants runtime/build permissions, and deploys the container. These services can generate billable usage; company credit coverage remains unverified until checked against the approved project.

`service` updates an application after warehouse prerequisites exist. `schema`, `seed`, `forecast`, `evaluate` and `infrastructure` operate on their named components. Re-seeding replaces synthetic table contents; use a dedicated demonstration dataset.

Private Cloud Run IAM access is the default. For an explicitly selected shared-demo deployment, supply `-PublicDemo -TokenFile PATH_TO_ACCESS_TOKEN`. Keep the token outside the repository or inside ignored `tmp/`. The script mounts it through Secret Manager and never prints it. Open a private deployment with an IAM-authenticated Cloud Run proxy.

## Configuration

| Variable | Purpose |
| --- | --- |
| `GCP_PROJECT` | Explicitly approved target project |
| `CLOUDSDK_CORE_ACCOUNT` | Account pinned by the Windows wrapper |
| `BQ_DATASET` / `BQ_LOCATION` | Warehouse dataset and location; default `retailiq` / `asia-south1` |
| `REGION` / `FIRESTORE_LOCATION` | Commerce service locations; default Mumbai |
| `GEMINI_MODEL` / `VERTEX_LOCATION` | Backend defaults: `gemini-3.6-flash` / `global` |
| `DEMO_AS_OF_DATE` | Pinned report date for synthetic history |
| `RETAILIQ_API_KEY` | Shared-demo bearer token mounted from Secret Manager |
| `RETAILIQ_TRUST_IAM` | Trust IAM enforcement on a private deployment |
| `RETAILIQ_OPEN_DEMO` | Unprotected local test option; never enabled by the deployment script |
| `PHOTO_BUCKET` / `PHOTO_RETENTION_DAYS` | Private evidence bucket and lifecycle target |
| `AI_REQUESTS_PER_MINUTE` | Per-instance inference request limit |
| `BQ_MAX_BYTES_BILLED` | Per-query BigQuery scan ceiling |

A company backend uses its Cloud Run service account for Vertex AI. `GEMINI_API_KEY` is an optional server credential; it is distinct from the browser's application bearer token. The static free profile instead uses its optional operator-provided AI Studio key and no server inference.

## Historical reference evidence and current verification

The archived `submission/evidence/cloud-reference-smoke.json` records successful service checks on the earlier personal reference deployment. `vertex-reference-evaluation.json` records 10 selected structured cases passing on Gemini 3.6 Flash through that backend. These results predate the free-only profile and **do not establish current hosting availability or free-profile model quality**. They are not evidence of business uplift or general shelf-recognition accuracy.

`fixtures.py` reads the canonical synthetic fixture. Forecasting uses BigQuery ML; its holdout compares MAE/WAPE with a seasonal-naive baseline. Results on generated history are diagnostic rather than production-accuracy evidence. Replenishment uses forecast demand when available, deducts inbound stock, caps short-life cover and respects case sizes. A missing facing first triggers a stockroom check rather than assuming inventory was sold.

Configured backend visit events retain originating IDs and structured evidence. Optional photos remain private and are retrieved through authenticated `/api/evidence/image`. Proposed orders remain drafts. `/health` is the application health route; the earlier cloud frontend intercepted `/healthz`.

Run the reproducible offline backend, deployment and free-hosting safety checks without credentials:

```powershell
.\.venv\Scripts\python.exe -m pip install -r gcp/requirements.txt -r tests/requirements.txt
.\.venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_deploy.py tests/test_deploy_free.py -q -p no:cacheprovider
```

The recorded run has 60 passing checks using cloud/command doubles. It does not validate a company deployment, current credit balance, historical personal charges or the optional free-profile model's live quality. See [tests/README.md](../tests/README.md) for verification limits.
