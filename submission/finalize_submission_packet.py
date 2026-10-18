"""Refresh submission text and artifact metadata without touching demo media."""
from pathlib import Path
import hashlib,json
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/name).read_text(encoding="utf-8"))
def write(name,text):(ROOT/name).write_text(text.rstrip()+"\n",encoding="utf-8",newline="\n")
def sha(name):return hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
proof=read("submission/evidence/prescribed-template-verification.json")
assert proof["passed"] and proof["pages"]==13 and proof["final_pdf_sha256"]==sha("pitch-slides.pdf")
brief=(ROOT/"SUBMISSION_BRIEF.txt").read_text(encoding="utf-8").strip()
assert len(brief)<=1024
live=read("submission/evidence/eval-live-backend.json")
assert live["model_calls"]==10 and live["summary"]=={"passed":8,"total":10,"expected_cases":10,"failed_assertions":2}
config=read("submission/evidence/live-deployment-config.json")
cfg=f'{config["summary"]["passed"]}/{config["summary"]["total"]}'
pdf_bytes=(ROOT/"pitch-slides.pdf").stat().st_size
fields=f"""RETAILIQ - FIVE SUBMISSION FORM FIELDS
Team RetailIQ: Abhishek Agarwal (leader); Vivek Sharma (member).

1. PROTOTYPE / WORKING SOLUTION LINK
https://retailiq-free-20261018-7ce297.web.app/
Live Firebase Hosting -> Cloud Run -> Gemini / Firestore.
Commercial catalogue, customer figures and forecasts are explicitly synthetic.

2. SOLUTION PRESENTATION (PDF, MAXIMUM 5 MB)
Upload: pitch-slides.pdf
Hosted PDF: https://retailiq-free-20261018-7ce297.web.app/pitch-slides.pdf
Prepared local PDF: 13 original-template pages; {pdf_bytes:,} bytes; below 5 MB.
SHA256: {proof["final_pdf_sha256"]}
Original template logos, headers and prompts retained; 26 preservation checks passed.
Public release/hash verification is recorded separately from local preparation.

3. PUBLIC GITHUB SOURCE LINK
https://github.com/abhishek-0706/AI-BUILDER-CUP-2026
Exact user-selected repository verified public.

4. DEMO VIDEO LINK (FORM REQUIRES THREE TO FOUR MINUTES)
https://retailiq-free-20261018-7ce297.web.app/demo.html
Existing project video is user-managed and unchanged in this release.
Video content/duration validation is separate from this deployment and deck release.

5. SOLUTION DESCRIPTION ({len(brief)} CHARACTERS; LIMIT 1,024)
{brief}
"""
write("submission/FORM_FIELDS.txt",fields)
readiness=f"""RETAILIQ SUBMISSION READINESS
Prepared 18 October 2026
Team RetailIQ: Abhishek Agarwal (team leader), Vivek Sharma (team member).

SOLUTION AND USERS
Challenge: Retail & Commerce - Intelligent Customer and Business Experiences.
Primary user: CPG field representative. Manager reviews; authorized buyer approves.
Secondary user: shopper comparing catalogue products.
Closed loop: shelf evidence -> qualify -> verify stock -> choose an action -> explain -> human approval -> save -> manager review.
Sensing, execution and empowerment are the problem-solving design rationale.

CURRENT LIVE DEPLOYMENT
Prototype: https://retailiq-free-20261018-7ce297.web.app/
Firebase Hosting provides the frontend and same-origin API rewrites.
Cloud Run/FastAPI: retailiq-live, us-central1, revision retailiq-live-00001-bx7.
Direct backend: https://retailiq-live-olhqdslz2q-uc.a.run.app
Gemini 3.5 Flash-Lite uses the gemini_free provider and a separate unbilled AI project.
Firestore stores records and rate-limit state in signed anonymous workspaces.
Fresh-client same-workspace reads and different-workspace isolation were actually verified.
Workspace cookies are scoping, not employee/enterprise authentication.
Catalogue, people, commercial figures and forecasts are synthetic_fixture data.
No BigQuery or Vertex inference is on this live path. No live photo retention.
BigQuery/BQML, Vertex and private Cloud Storage remain optional reference code.

REVIEWABLE SUBMISSION ARTIFACTS
pitch-slides.pdf: 13 original-template pages, {pdf_bytes:,} bytes; below 5 MB.
SHA256: {proof["final_pdf_sha256"]}
pitch-slides.html: browser PDF viewer with current live prototype and source links.
submission/AI_Builder_Cup_Original_Template.pdf: supplied original 16-page template.
submission/build_template_deck.py: blank-region overlays over original vector pages.
submission/verify_template_deck.py: reproducible artwork/prompt preservation checks.
SUBMISSION_BRIEF.txt: {len(brief)} description characters, {len(brief)+1} including final newline.
submission/FORM_FIELDS.txt: the five paste-ready form fields.
submission/TEMPLATE_COMPLIANCE.txt: original-page mapping and every required prompt.
The final local PDF/hash is verified; public byte matching is a separate release check.
Public repository: https://github.com/abhishek-0706/AI-BUILDER-CUP-2026
Video URL retained: https://retailiq-free-20261018-7ce297.web.app/demo.html
No demo video, voice or narration was edited, generated or reviewed in this release.

CURRENT EVIDENCE AND LIMITATIONS
submission/evidence/live-deployment-smoke.json
  14/14 actual API/deployment checks. Real Gemini response; actual Firestore write,
  fresh-client same-workspace read, separate-workspace isolation, private-path checks.
submission/evidence/live-ui-deployment-qa.json
  Actual rep shelf-video audit, buyer opening/reply and fresh manager persistence
  were observed. Durable follow-up verifies a labelled synthetic QA capture saved
  and read by a fresh same-workspace manager, plus an actual shopper comparison.
  Four total model calls. The first run's full payload was not retained; the report
  explicitly records that limitation. Three actual public-app screenshots retained.
submission/evidence/eval-live-backend.json
  Current Gemini 3.5 Flash-Lite: 8/10 selected synthetic contracts; exactly ten calls,
  no failure retries. Facts 2/2; arithmetic 3/3; grounding 1/1; unknown/injection 2/2.
  Budget discovery failed 0/1: S02/S03 exceeded the stated price limit.
  Short-life order failed 0/1: model returned 21 units; expected deterministic result 5.
  These failures remain visible in the deck. Do not execute model-generated quantities.
  Only code-validated, human-approved draft orders are eligible for action.
  Per-case latency was 1.230-2.233 seconds in this run, not end-to-end visit latency.
  This is not RAGAS, general accuracy, vision accuracy or a complete injection defence.
submission/evidence/eval-offline.json and evaluator-regressions.json
  38 deterministic acceptance/rejection assertions; no model execution.
submission/evidence/software-regressions.json
  Six suites passed: 157 browser + seven policy checks. Mocked API/UI contracts.
submission/evidence/python-regressions.json
  105 offline checks across two runs: 87 existing and 18 live-deployment guards.
  Cloud clients are doubles; this is distinct from actual endpoint proof.
submission/evidence/live-deployment-config.json
  Latest retained configuration audit: {cfg}. Read individual checks and timestamps;
  subsequent publication/cache hardening is established by its own release proof.
submission/evidence/prescribed-template-verification.json
  13 original header/logo pixel comparisons and 13 full original-prompt checks passed.
submission/evidence/public-source-smoke.json
  User-selected repository publicly accessible without authentication.
Earlier free-hosting/public-functionality/media reports describe the earlier static
release. They do not supersede the current live API/UI proofs or validate new media.
Historical Vertex reference: 10/10 synthetic cases on retired paid Gemini 3.6 route.
Historical BQML: seven synthetic holdout days; WAPE 1.249% vs seasonal-naive 2.824%.
Neither historical result establishes current-model quality or real-store forecasting.

GUARDRAILS AND COST BOUNDARY
Typed output validation and evidence qualification; abstain when evidence is missing.
Own-brand compliance is distinct from competitor benchmarking.
Observed shelf facings are distinct from recorded inventory units.
Code checks demand, inbound, shelf life and case rules; orders remain human drafts.
Saved records are workspace-scoped; model key and secrets remain server-side.
Anonymous synthetic judge mode is not enterprise identity/authorization.
The unbilled AI project is checked; quota errors stop requests; no paid/Vertex fallback.
Runtime: min 0/max 1 instance, one CPU, 512 MiB, concurrency two.
Persistent limits: 50 AI/day, 500 API/day, 200 saves/day and six AI requests/minute.
These controls are not a hard financial cap and do not guarantee zero charges.
The old reference project's billing is disabled. Current Hosting/Cloud Run/Firestore
billing is enabled under the user's accepted possible-overage consent.
Actual cloud cost, previous invoices, company credit balance and savings are unverified.

VALUE SCENARIO - ASSUMPTIONS, NOT ACHIEVED RESULTS
10 reps x six visits/day x 22 days = 1,320 visits/month.
Scoped audit/debrief: assumed 12-minute baseline vs five-minute target.
Seven minutes saved per visit would release 154 hours/month.
At assumed INR 300/hour: INR 46,200 capacity value.
At target INR 5/visit: INR 6,600 monthly operating budget.
Difference: INR 39,600 illustrative net capacity value; not guaranteed cash savings.
Engineering, integration, training and devices are excluded.
Use an independent baseline and assisted period to measure corrections, time,
productive reuse, discrepancy closure, waste risk, latency and cost per workflow.
No real sales uplift, stockout reduction, customer outcome or selection rank is claimed.
"""
write("SUBMISSION_READINESS.txt",readiness)
compliance=f"""PRESCRIBED TEMPLATE COMPLIANCE
Original: Submission Template _ AI Builder Cup.pdf, 16 pages, 720 x 405 points.
Original SHA256: {proof["original_template_sha256"]}
Final: pitch-slides.pdf, 13 substantive pages, {pdf_bytes:,} bytes (<5 MB).
Final SHA256: {proof["final_pdf_sha256"]}

FORMAT: ORIGINAL PDF ARTWORK RETAINED
Original vector pages are the actual underlay, not a recreated visual theme.
Google Cloud, AI Builder Cup and H2S branding, original headings, question prompts
and original page geometry remain intact. Solution content fills unused body regions.
All 13 original header/title pixel comparisons and all 13 full original-prompt text
checks passed. Font wrapping and text-box overflow guards ran during PDF generation.
See submission/evidence/prescribed-template-verification.json.
Only original page 2 (download/edit instructions) and blank pages 15-16 are omitted.
Both optional substantive sections are retained.

ORIGINAL PAGE -> FINAL PAGE -> REQUIRED CONTENT AND ANSWER
01 -> 01 -> Team Details:
  a. Team RetailIQ; b. Abhishek Agarwal, team leader;
  c. Retail & Commerce: Intelligent Customer and Business Experiences.
  Known additional member: Vivek Sharma.
03 -> 02 -> Brief about the idea:
  Primary rep, manager/buyer decision owners, shopper discovery and the closed loop.
04 -> 03 -> Opportunities:
  All three original questions remain: differentiation, how it solves the problem,
  and USP. Separate answer columns include synthetic stock-reconciliation example.
05 -> 04 -> List of features offered by the solution:
  Rep shelf audit/pitch/debrief; manager Firestore review; shopper discovery.
06 -> 05 -> Process flow diagram or Use-case diagram:
  Connected eight-step rep-to-manager loop plus secondary shopper journey.
07 -> 06 -> Wireframes/Mock diagrams (optional):
  Three role surfaces and action controls; labelled explanatory wireframes.
08 -> 07 -> Architecture diagram:
  Actual Hosting -> Cloud Run -> Gemini path, Firestore and synthetic data source;
  code/human guardrails and anonymous-workspace boundary explicitly identified.
09 -> 08 -> Technologies:
  Separate actual live services from optional BigQuery/Vertex/Storage reference code.
10 -> 09 -> Estimated implementation cost (optional):
  Metered cost limits, unverified actual cost and explicit assumption-based capacity
  scenario; implementation estimate remains unmeasured and requires scoping.
11 -> 10 -> Snapshots of the prototype:
  Actual live rep, manager and shopper PNGs; manager record is labelled QA capture.
12 -> 11 -> Prototype Performance report/Benchmarking:
  Actual current-model 8/10 contract matrix with two visible failures.
  Live API/UI proof and offline regressions are separate from model-quality claims.
13 -> 12 -> Additional Details/Future Development:
  Permissioned data feeds, shelf labels, enterprise identity, ERP draft handoffs,
  expanded evaluation and a falsifiable measured pilot.
14 -> 13 -> Links:
  Exact public GitHub repository, existing project video URL and live product BASE URL.

CLAIMS AND MEDIA BOUNDARY
Synthetic catalogue, customer figures and forecasts are explicit.
No achieved uplift, savings, general accuracy or production forecast quality is claimed.
The original 'Demo Video Link (3 Minutes)' prompt remains unchanged.
The form/user requirements specify three to four minutes and a working-solution video.
Media is user-managed and excluded from this release; these template checks do not
certify the existing video's contents, duration or alignment to the current live path.
"""
write("submission/TEMPLATE_COMPLIANCE.txt",compliance)
names=["pitch-slides.pdf","pitch-slides.html","SUBMISSION_BRIEF.txt","SUBMISSION_READINESS.txt",
"submission/FORM_FIELDS.txt","submission/TEMPLATE_COMPLIANCE.txt","submission/build_template_deck.py",
"submission/verify_template_deck.py","submission/AI_Builder_Cup_Original_Template.pdf",
"assets/submission/prototype-rep-live.png","assets/submission/prototype-manager-live.png","assets/submission/prototype-shopper-live.png"]
artifacts=[{"path":name,"bytes":(ROOT/name).stat().st_size,"sha256":sha(name)} for name in names]
metadata={"prepared_at":datetime.now(timezone.utc).isoformat(),"scope":"local final non-media artifacts; publication byte matching recorded separately","template_substantive_sections":13,"pdf_below_5MB":True,"description_characters":len(brief),"description_file_characters":len((ROOT/"SUBMISSION_BRIEF.txt").read_text(encoding="utf-8")),"current_model_evaluation":{"passed":8,"total":10,"model_calls":10,"report":"submission/evidence/eval-live-backend.json"},"public_repository":"https://github.com/abhishek-0706/AI-BUILDER-CUP-2026","artifacts":artifacts}
write("submission/evidence/final-artifacts.json",json.dumps(metadata,indent=2))
write("tmp/deck-final-release.json",json.dumps(metadata,indent=2))
print(json.dumps({"packet_ready":True,"pdf_bytes":pdf_bytes,"pdf_sha256":sha("pitch-slides.pdf"),"description_characters":len(brief),"files":len(names)}))
