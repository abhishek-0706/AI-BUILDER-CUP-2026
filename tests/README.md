# Tests

Three suites. Two need no credentials, one calls the live model.

```bash
npm install playwright && npx playwright install chromium

# serve the app from the repo root
python -m http.server 5190

# then, from the repo root:
node tests/structural.test.js     # correctness and state. no key needed
node tests/security.test.js       # XSS and prompt-fence hardening. no key needed
GEMINI_API_KEY=... node tests/live.test.js    # grounding and output quality
```

Override the target with `RETAILIQ_URL` if you serve on a different port.

## What each one is for

**`structural.test.js`** covers the defect classes found in audit, so a regression
surfaces here before it reaches a demo. Fixture dates reconciling to a single day,
KPIs deriving from the revenue table rather than drifting beside it, segment baskets
reproducing the daily average, the order valuing at trade price, inputs clamping
before they reach a prompt, planogram state not leaking between visits, a broken
clip leaving the pane usable, and each prompt actually containing the data it asks
the model to reason about.

**`security.test.js`** treats model output as hostile. A shelf photograph can carry
text that steers the model, so the suite feeds crafted markup through the verdict
renderer and asserts nothing executes, probes the parser with malformed and
duplicated output, and verifies untrusted text cannot close the fence that marks it
as evidence rather than instructions.

**`live.test.js`** checks what prompts cannot guarantee on their own: that citations
resolve to real source documents, that the rehearsal buyer stays in character, that
the debrief ignores an injection typed into the store feedback field, that target
arithmetic uses trade price, and that no Markdown leaks into the output. It makes
roughly ten model calls and takes a couple of minutes.

## Note on the compliance score

`security.test.js` asserts the score is computed rather than asserted by the model.
The app parses one verdict per rule and calculates passed over judged, excluding
NOT VISIBLE. If fewer rules parse than the planogram defines, no score is shown at
all, because a confident percentage drawn from a partial parse is worse than none.
