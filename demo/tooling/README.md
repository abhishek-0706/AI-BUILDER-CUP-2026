# Submission video tooling

The current baseline video, `demo/RetailIQ_submission_walkthrough.mp4`, is a 117-second narrated recording of the labelled no-key scenario. It uses the app's real controls and synthetic commercial context. No live AI request is made while recording. The baseline narration uses the Windows system voice.

The submission story is the rep's complete visit: capture shelf evidence, verify the stock discrepancy, save the action, inspect the manager record, review a proposed order and explore shopper discovery. A proposed order remains a draft for a human buyer.

## Regenerate the walkthrough locally

From the repository root:

```powershell
npm ci
npm --prefix demo/tooling ci
npx playwright install chromium
.\demo\tooling\narrate_submission.ps1
node demo/tooling/record_submission.js
```

The recorder uses the root Playwright installation, starts and stops its own local test server and blocks external application requests. FFmpeg is supplied by the tooling dependency. `submission_script.json` contains the scene narration. WAVs, timings and raw recordings stay under ignored `tmp/`. It writes the resulting video under `demo/`. Duration follows the current narration script; the retained 117-second baseline is a historical artifact.

## Optional creator-voice version

The creator supplied their own voice sample for an AI-assisted narration version. The conversion is performed locally on the CPU with OpenVoice; the sample is not uploaded to a voice API. Model/dependency downloads are separate from voice processing. Private reference audio, embeddings and generated intermediate WAVs remain under ignored `tmp/`.

`clone_narration.py` creates a short preview by default. After listening review, `--all-scenes` converts the scene WAVs and writes `converted-scenes.json`. It requires the locally prepared model manifest, model files and compatible Python environment; see the script's `--help` for arguments.

The recorder supports alternate narration and a separate output so the baseline is preserved:

```powershell
node demo/tooling/record_submission.js --narration tmp/voice-output-abhishek-final/converted-scenes.json --output demo/RetailIQ_Abhishek_voice_demo.mp4 --voice-label "AI narration from creator-provided voice sample"
```

The final creator-voice artifact is demo/RetailIQ_Abhishek_voice_demo.mp4: 222.44 seconds (3:42.44), nine synchronized scenes, 8,781,377 bytes, with full audio/video decoding passed. Its public player is https://retailiq-free-20261018-7ce297.web.app/demo.html. It is disclosed as AI-assisted narration, not an unedited personal recording. Voice similarity and pronunciation still require listening judgment.

## Historical pipeline

`script.json`, `gen.py`, `record.js` and `mux.js` produced the earlier `RetailIQ_demo_final.mp4`. That historical workflow warms live model results and replays cached responses. It is distinct from the current recorded no-key scenario. Do not run its model warm-up under a free-only or no-personal-spend requirement.

Re-record from the current application rather than labelling historical cached responses as a new live session. The newer submission recorder measures scene lengths and keeps pre-roll timing; variable-rate browser video should not be trimmed using an assumed frame-accurate seek.
