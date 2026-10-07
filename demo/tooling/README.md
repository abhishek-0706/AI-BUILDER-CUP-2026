# Demo video pipeline

Regenerates the narrated walkthrough end to end. Four files, run in order.

| File | Does |
|---|---|
| `script.json` | The narration, 12 beats, each written as issue then solution |
| `gen.py` | Renders each beat to mp3 with Edge TTS, `en-IN-NeerjaNeural` at +16% |
| `record.js` | Drives the app with Playwright and captures the screen |
| `mux.js` | Lays each clip onto the capture at the timestamp the recorder logged |

```bash
pip install edge-tts
cd demo/tooling
npm install && npx playwright install chromium   # deps stay here, never at the repo root

# serve the app from the repo root, in another terminal
python -m http.server 5190

python gen.py                       # writes audio/*.mp3
GK=your-gemini-key node record.js ./rec   # writes rec/*.webm and rec/scenes.json
node mux.js ../RetailIQ_demo.mp4    # combines them

# normalise speech to a comfortable level
ffmpeg -i ../RetailIQ_demo.mp4 -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
  -c:v copy -c:a aac -b:a 160k -movflags +faststart ../RetailIQ_demo_final.mp4
```

`gen.py` expects a `durations.json` to be written after it runs; `record.js` reads that
file to hold each scene for exactly the length of its narration clip, so nothing is
stretched or cut off. Measure the clips with ffmpeg and write `[{id, dur}]`.

## Three problems this pipeline exists to avoid

Each of these produced a broken cut before it was fixed, so they are worth knowing
before changing anything here.

**Live model calls on camera.** Generating the pitch, the order, the debrief, the
coaching, the rehearsal and the shelf audit during the recording left minutes of dead
screen time, once a single 126 second gap waiting for a rehearsal score. Everything is
now produced in a warm-up pass against a separate browser context, then replayed. The
`cache` object holds the results and `inject()` writes them in.

**The capture starts before the first beat.** Playwright begins recording when the
context is created, not when you start your timeline. The recorder measures that
pre-roll and writes it into `scenes.json`, and `mux.js` offsets every clip by it.
Ignoring this shifts all narration out of sync with the visuals.

**Do not trim the capture with a seek.** The webm Playwright produces is variable frame
rate, so `ffmpeg -ss` is not frame accurate on it and a trim lands somewhere other than
where you asked. That is why the shelf audit is warmed and injected rather than run on
camera and cut out afterwards. Keep pre-roll small instead of trying to remove it.

## Two smaller things

Waiting for a streamed reply needs several consecutive unchanged polls, not two. A
response can pause mid-sentence for over a second, and a short stability window caches
half an answer.

Rehearsal scoring refuses to score fewer than two rep turns, by design. The warm-up
sends two lines, the second one making the actual commercial ask, otherwise the score
panel shows a refusal rather than a score.
