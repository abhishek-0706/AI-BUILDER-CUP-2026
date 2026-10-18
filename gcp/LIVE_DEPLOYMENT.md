# Allowance-limited live judge deployment

Status: the direct Cloud Run service (https://retailiq-live-olhqdslz2q-uc.a.run.app) passed 14 actual backend checks, including real Gemini, Firestore save/read and session isolation. The Firebase base URL now passed actual browser Gemini, shopper, buyer and Firestore persistence checks; see `submission/evidence/live-ui-deployment-qa.json`. The actual configuration audit passed 14/14, including `private, no-store` headers for dynamic Firebase rewrites; see `submission/evidence/live-deployment-config.json`. Recorded walkthroughs and historical cloud results do not prove this rollout works.

The hosting project has explicit approval to use free-tier allowances with possible overages. These allowances are not a zero-cost guarantee. The retired project must stay unbilled. Gemini uses a separate key project whose billing must remain disabled; the runtime checks that project before every inference and fails closed on lookup failure. There is no Vertex or paid-model fallback.

`deploy_live.py` is separate from the unbilled-only Spark helper. Use an absolute Cloud SDK executable path and the explicitly authorized account. Run these phases with `--project YOUR_APPROVED_HOSTING_PROJECT --account YOUR_APPROVED_ACCOUNT --gcloud ABSOLUTE_GCLOUD_PATH`:

```text
python gcp/deploy_live.py prepare --accept-free-tier-overages [account/project/CLI arguments above]
python gcp/deploy_live.py build --accept-free-tier-overages [arguments]
python gcp/deploy_live.py build-status [arguments]
python gcp/deploy_live.py deploy --accept-free-tier-overages [arguments]
python gcp/deploy_live.py publish --accept-free-tier-overages [arguments]
```

The helper obtains OAuth in memory, creates service-restricted API keys directly into Secret Manager, and stores resource IDs and secret-version references in ignored `tmp/live-deployment.json`. Never put key values, tokens or session secrets in arguments or source. The helper enforces the current release's named retired-project billing guard.

Cloud Run uses request-based CPU, minimum zero and maximum one instance at both service and revision scope. The default-pool build pins E2_STANDARD_2 and a ten-minute timeout. Daily Firestore reservations limit the shared demo to 50 model calls, 500 API requests and 200 event saves, plus six model requests per minute. Provider 429 errors stop inference for the UTC day. Quotas can limit availability; budget limits are not proof of a zero bill.

The catalogue is an explicit synthetic snapshot, never a fallback for a failed warehouse. Visit events use real Firestore under isolated signed HttpOnly `__session` browser sessions. Manager reads are capped at 20 events. Public photo retention is disabled. The profile needs no BigQuery, Vertex or runtime Cloud Storage permissions; private build-source storage is separate.

Firebase Hosting rewrites `/api/**`, `/runtime-config.js` and `/health` to Cloud Run. Its static version deliberately omits runtime-config.js because static files take priority over rewrites. Confirm the Firestore visit_events composite index is READY before manager testing.

Before declaring the rollout available, verify anonymous browser bootstrap, actual Gemini output, server-side Firestore save/read after reload, session isolation and final published runtime metadata. Do not substitute recorded answers for those checks.

Current selected structured-model baseline: 8/10, with budget-discovery and short-life-replenishment failures retained in `submission/evidence/eval-live-backend.json`. Offline evaluator 38/38 makes no model calls. These results are not general accuracy, RAGAS or measured ROI.
