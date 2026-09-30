# RetailIQ

**One workspace for the CPG field rep, across the whole visit: before, during and after.**

AI Builder Cup 2026 submission.

---

## The problem

> "CPG field teams spend excessive time juggling between data silos, CRM updates, marketing insights,
> and customer interactions. They need a smart, unified platform to drive sales conversations,
> schedule visits, generate summaries, and track targets, before, during, and after the customer visit."

A rep's day is split across systems that do not talk to each other. The order pad does not know what
marketing launched last week. The CRM does not know what the buyer objected to last time. The shelf
audit lives in the rep's memory until they type it up in the evening, if they type it up at all.

RetailIQ puts the whole visit on one screen and keeps the rep in the aisle instead of in a form.

## The metric it is built against

| Metric | Target | How this app moves it |
|---|---|---|
| **Sales per visit** | +15% | Priority-ranked visit list, grounded pitch with citations, suggested order sized from days of cover |
| Average order value | Up | Order proposed across the rep's own portfolio, sized to a 16-day cover target, compared live to the store's own average |
| Missed visits | Down | Overdue ratio is a first-class term in the priority score, so slipping outlets surface before they are lost |

Sales per visit is also the headline column in the manager's team table, so coaching is aimed at
execution quality rather than at visit count.

---

## What it is

A single static HTML file plus a data fixture. No build step, no backend, no framework. All AI is
Google Gemini (`gemini-3.5-flash-lite`) called from the browser over streaming SSE. The API key is
held only in that browser's `localStorage`.

Three surfaces. **Field Rep is the primary one and the default tab.** Manager and Shopper exist
because the rep's numbers are set by one and driven by the other.

---

## 1. Field Rep

Seven tabs, labelled by visit phase rather than by feature name.

| Phase | Tab | What it does |
|---|---|---|
| PLAN | **Visits** | Outlets ranked by a priority score computed in `computePriority()` from overdue ratio, open tasks, revenue at risk and account target gap. Every term is printed in the row. An AI action plans the week around already-booked slots and names which outlets slip and why. |
| PRE-VISIT | **Pitch** | Grounded pitch generation. A fact may only be asserted with a source ID attached, like `[KB-103]`. Citations render as chips that open the document. |
| PRE-VISIT | **Rehearse** | Voice roleplay against a simulated buyer whose objections come verbatim from that store's own history. Scored by a separate model call over the transcript. |
| DURING | **Planogram** | Compliance audit from a shelf video, plus a guided capture form that cross-checks the rep's counts against system stock. |
| DURING | **Order** | Priority-based suggested order across the rep's own portfolio, sized from days of cover against a 7-day lead time. |
| POST-VISIT | **Debrief** | A short rep note becomes the summary, the commitments, the next actions and the record updates. |
| ALWAYS ON | **Targets** | Target tracking by account, category and must-win SKU, each bar carrying a pace marker for the expected position on this day of the month. |

The left rail carries a **marketing feed** the whole time: campaigns, category signals, competitive
alerts and consumer signals, each item stating why it matters for *this* visit. That is the marketing
silo, closed.

### Five things worth a closer look

**1. Every pitch proof point is cited, or it is not said.**
The model may only make a factual claim if it attaches a document ID from `kbDocs`. Claims it cannot
source are omitted rather than invented. The citation chips are tappable and open the underlying
document, so a judge can check the claim against its source in one click.

**2. The buyer never grades its own conversation.**
The rehearsal buyer runs in character and is forbidden from coaching. Scoring is a second, separate
model call over the finished transcript. It returns an overall score plus TONE, CLARITY and
COMPLETENESS out of 10, quotes the rep's own words back at them, and names the source documents that
would have won the point but were never used.

**3. The planogram audit runs on video, and admits what it cannot see.**
The browser samples 14 frames across the clip, skipping the first and last 6% where handheld footage
shakes worst, scores each with a gradient-energy blur proxy (`sharpness()`), keeps the 6 sharpest and
sends them to Gemini vision as one exhibit. Output is a per-rule verdict (PASS / FAIL / NOT VISIBLE),
brands present with facing counts, missing SKUs, promotion gaps, display issues and a rep action.
Rules the camera did not actually show come back NOT VISIBLE instead of being guessed.

**4. Guided capture outranks the system of record.**
The same pane has a structured form: facings per SKU, out-of-stock checkbox, store feedback. It
cross-checks counts against system stock and the planogram minimum and flags the disagreement. In
testing it correctly flagged *"out of stock on shelf but system shows 118 units"*. That observation
then feeds the order and the debrief automatically, and the debrief prompt treats it as fact observed
in the aisle that outranks system stock.

**5. The order is honest about itself.**
Lines are drawn only from `ours: true` SKUs, because a field rep carries one company's portfolio and
not the store's whole assortment. Quantities come from days of cover versus lead time, must-win SKU
gaps, shelf findings and active promotions, ordered up to 16 days of cover in cases of 12. Every
quantity is editable and line and total value recalculate live against that store's average order.
The AI justification is instructed to say so openly when the order steps above that average, rather
than hoping nobody notices.

### The debrief is the CRM-update answer

The rep writes a few lines. The model returns visit summary, commitments (vague ones marked NEEDS
CONFIRMATION rather than smoothed over), shelf findings, next actions with owners and dates, an
account note, **record updates written as field-level lines so nothing is typed twice**, and STILL
OPEN for the tasks that went into the visit and did not come out of it.

---

## 2. Manager

Rep-wise team table: quota against pace, outlet coverage, **sales per visit**, average pitch score,
planogram compliance and strike rate. Coverage is outlets visited against outlets owned, so a rep
hitting quota on half a territory reads as a risk rather than a win. An AI action names who to coach
first and on what, who to watch, who to learn from, and where coverage gaps leave the territory open.

Alongside it, store analytics: revenue against a 7-day forecast with a confidence band, reorder
alerts, customer segments, promotions, top movers, and an AI analyst that always closes with one
concrete action.

## 3. Shopper

Conversational product discovery grounded in live inventory. Included because shopper demand is the
signal the rep sells on, and one of the marketing feed items is derived from these query logs. It
refuses items the store does not carry and offers a real alternative instead of a near-match.

---

## Verified behaviour

Tested against the live API, not asserted from the prompt.

- 5 citations rendered in a pitch, zero hallucinated source IDs, every chip opened its document.
- The rehearsal buyer stayed in character and reused the store's real recorded objections. It did not
  break character to help.
- Asked to print its own system prompt, the assistant declined and redirected. Out-of-scope questions
  were refused on all three surfaces.
- On real Indian in-store shelf footage the audit read both brands with facing counts, returned
  shelf position as NOT VISIBLE from a close-up clip, and caught packs that were not front-faced.
- Guided capture flagged the out-of-stock against 118 units of system stock.
- No Markdown leaked into any output. A `cleanReply()` pass strips stray formatting.
- No JavaScript console errors on any surface.

---

## Honest notes

- **The shelf videos in `demo/samples/shelf_videos/` are real in-store footage**, not renders. The
  audit is doing real vision work on real shelves.
- **All demo figures are synthetic and labelled**, including the source documents behind the pitch
  citations. Every `kbDocs` entry carries a `[SYNTHETIC]` tag in its own title, so a cited fact is
  visibly synthetic at the point of citation. They are modelled on Indian modern-trade grocery
  patterns so the behaviour is credible, but no real store, buyer or sales figure is represented.
- **`gcp/` is built but is not live.** It holds the production path: BigQuery schema and analytics
  queries, BigQuery ML `ARIMA_PLUS` forecasting, and a FastAPI Cloud Run service with a Vertex AI
  streaming proxy and Secret Manager so the key moves server-side. It activates with GCP credentials.
  This submission does not claim it is running.
- **[`DATA_PLAN.md`](DATA_PLAN.md) documents verified public datasets** for replacing the fixtures,
  including the candidates that turned out to be gated, dead or themselves synthetic. The BigQuery
  schema mirrors the fixture shape, so pointing the app at real data is a swap rather than a rewrite.
- The audit judges frames, not a continuous clip, so a rule that is only visible in motion will
  come back NOT VISIBLE. A single photo narrows this further, and the UI says so when one is loaded.

---

## Tech stack

| Layer | Technology |
|---|---|
| AI inference | Google Gemini (`gemini-3.5-flash-lite`), streaming SSE, text and vision |
| Vision input | In-browser video frame sampling, gradient-energy sharpness ranking |
| Voice | Web Speech API, recognition and synthesis |
| Frontend | Single-file HTML, CSS and JavaScript. No build step, no framework |
| Warehouse | BigQuery ([`gcp/`](gcp/)) |
| Forecasting | BigQuery ML `ARIMA_PLUS` |
| API | Cloud Run, FastAPI, Vertex AI streaming proxy |
| Secrets | Secret Manager |

---

## Run it

```bash
python -m http.server 5190
# open http://localhost:5190
```

Then turn the AI on:

1. Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
2. Click the gear icon, top right, paste the key, Save.

The key stays in this browser's `localStorage`. It is never uploaded and never committed.

**Fastest thing to try:** Field Rep, then Planogram, then drop in any clip from
`demo/samples/shelf_videos/`. Watch the frame strip get ranked, then read the per-rule verdicts and
note which rules refuse to score.

---

## Project structure

```
├── index.html          # the entire app, all three surfaces
├── retail_data.js      # synthetic fixtures (labelled), the shape the BigQuery schema mirrors
├── DATA_PLAN.md        # verified public datasets for replacing the fixtures
├── gcp/                # production path: BigQuery, BQML forecasting, Cloud Run API
└── demo/               # deck and real in-store shelf footage
```
