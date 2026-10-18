# Verification

Install the locked dependencies and Chromium once, then run:

```bash
npm ci
npx playwright install chromium
npm test
```

`npm test` starts a temporary localhost server on a free port, runs every offline
JavaScript suite, and closes the server. It does not require a separately running
Python server or API credentials. Browser model/backend responses are test doubles;
the guided sample is deterministic. Video decoding uses the checked-in three-second synthetic H.264 clip at `tests/fixtures/synthetic-motion.mp4`; legacy/user recordings and FFmpeg are not needed to run the tests. No model or Google Cloud operations are called.

For backend regressions using in-memory cloud doubles:

```bash
python -m pip install -r gcp/requirements.txt -r tests/requirements.txt
python -m pytest tests/test_api.py tests/test_synthetic.py tests/test_deploy.py tests/test_deploy_free.py tests/test_deploy_live.py -q -p no:cacheprovider
```

CI runs both commands with Node 22 and Python 3.12. Dependencies are locked by
`package-lock.json`; test-only Python dependency versions are in
`tests/requirements.txt`.

## Suite coverage

- `structural.test.js`: fixture reconciliation, computed KPIs, prompt context,
  planogram scope, input bounds, order eligibility/trade pricing, video sampling,
  failed media recovery, and state reset.
- `security.test.js`: hostile model markup, malformed/partial/duplicate audit
  verdicts, unavailable evidence, prompt-fence delimiters, and key display.
- `integration.test.js`: frontend/backend data and streaming contracts, forecast
  replenishment with inbound inventory, saved capture evidence, write errors,
  unavailable warehouse handling, native response-schema forwarding on both adapters,
  verbatim JSON evidence across streaming/fences, model-compatible sampling, output
  budgets, and exact trade-price rounding.
- `workflow.test.js`: exact chart interval geometry, mobile overflow, shopper
  and audit races, visit-note isolation, guided own-brand audit and persisted
  rule evidence, warehouse markup, executable source URLs, pitch context limits, the pitch agent,
  private-photo bearer authentication/blob rendering/revocation,
  and zero API/model traffic in explicit recorded judge mode.
- `free-mode.test.js`: cached-key confirmation, fingerprint binding, free-profile
  transport, quota hard-stop, no backend/model fallback, and CLI policy guards.
- `eval.js`: a structured factual assertion evaluator and its adversarial
  acceptance/rejection regressions against the canonical `retail_data.js`.

## What the evaluator measures

```bash
node tests/eval.js
```

The default mode tests **the evaluator**, not the model. Ten canonical golden
answers must pass; corrupted answers and malformed input must fail. Assertions
cover selected catalog facts (price, protein, stock, sugar), discovery eligibility,
basket/trade arithmetic, stock cover, perishable order sizing, own-brand order
eligibility, citation identity, an exact cited passage and synthetic provenance,
missing-product uncertainty, absent expiry evidence, and instruction disclosure.

Known invalid citations and absent citations fail the cited-evidence case.
A real source ID attached to a fabricated passage also fails. Every required
assertion contributes to the result; any failed case exits nonzero.

These are deterministic contract checks, **not RAGAS scores**. They do not measure
broad semantic faithfulness, natural-language recommendation quality, complete
prompt-injection resistance, live shelf-recognition accuracy, or business impact.

Evaluate previously collected JSON responses without calling a model:

```bash
node tests/eval.js --responses path/to/responses.json
```

The input is an object keyed by the ten case IDs exported in `eval-core.js`;
each value is the structured answer for that case. Missing answers fail.
No expected answers are substituted during replay.

## Optional free-quota model checks

```bash
GEMINI_API_KEY=YOUR_UNBILLED_AI_STUDIO_KEY node tests/eval.js --live --confirm-free-tier
```

This is an explicit operator attestation that the key belongs to an unbilled
Google AI Studio project. The application cannot independently verify billing
status. Do not supply a key from a billed project. The default evaluation path
continues to make zero model calls.

The live runner permits only the free-only static profile and its selected
`gemini-3.5-flash-lite` model. It refuses backend/Vertex inference and known paid
backend targets, blocks application API requests, and binds confirmation to the
provided key fingerprint. Quota errors stop the run immediately; there is no
retry, alternate model, or paid backend fallback.

It uses production `callGemini` and shopper/rep context plus the product identity
map. Native response schemas contain requested field names and types only.
Expected prices, product IDs, quantities and passages are never supplied as
schema values. Expected answers remain independent assertions. Structured JSON
preserves quoted source symbols and punctuation instead of applying prose styling.

Credentials remain in the environment/browser storage and are not written to
reports. Set `RETAILIQ_URL` only for an appropriate free static deployment;
without a URL, the runner starts and stops its own localhost server. A catalog
that differs from the golden dataset is refused before inference.

`node tests/live.test.js --confirm-free-tier` is a compatibility entry point with
the same restrictions. Passing these selected structured tasks does not establish
full UI or shelf-recognition quality. The optional free-profile model has not
been measured by the offline suites.


## Evidence artifacts

Reports are written under the ignored `tmp/` directory:

- `test-report.json`: suite results, durations, mode, and limitations.
- `eval-offline-report.json`: evaluator regression assertions, with zero model calls.
- `eval-replay-report.json`: saved-response assertions.
- `eval-free-live-report.json`: optional free-profile live assertions and call counts.
- `eval-vertex-reference-report.json`: archived Vertex reference from before the
  free-only profile; this is not evidence of free-profile model quality.

Only a report explicitly labeled `live` represents model execution. Offline
passes and cloud-double tests do not establish deployed cloud availability,
sales uplift, time savings, or model accuracy. Measure those separately before
making submission claims.

Audit scores are computed from one recognized verdict per assigned rule.
Unseen rules are marked NOT VISIBLE and excluded from the judged denominator.
Missing/unknown rules cannot produce a complete score; a fully unseen shelf is
reported as not assessable.
