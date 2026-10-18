# Submission source materials

`pitch-slides.pdf` at the repository root is the prepared 13-page prescribed-template presentation; `pitch-slides.html` is its browser PDF viewer. The original supplied template is retained as `AI_Builder_Cup_Original_Template.pdf`. `evidence/prescribed-template-verification.json` records its template-preservation checks and the prepared PDF hash.

`build_template_deck.py` reproduces that prepared deck snapshot using the original PDF, the included prototype screenshots, Python packages `pypdf` and `reportlab`, and Arial or DejaVu Sans fonts. Install those packages and run `python submission/build_template_deck.py` from the root. It writes the root PDF and an ignored `tmp/` build report; it makes no model or cloud calls. The deck snapshot predates the current live rollout; use the root README and `gcp/LIVE_DEPLOYMENT.md` for current provisioning status.

Historical release reports retain their timestamps and original scope. They do not prove the pending live Cloud Run/Firestore/Gemini deployment. The final approved submission MP4 is under `demo/`; raw voice inputs, model weights, working recordings and credentials are excluded from public source.
