/* Lays each narration clip onto the recorded screen capture at the timestamp the
   recorder logged for it, then encodes to mp4. Each clip is delayed to its own
   start time and the whole set is mixed down, so no clip is stretched or cut. */
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const FF = require('ffmpeg-static');
const REC = path.join(__dirname, 'rec');
const OUT = process.argv[2];

const meta = JSON.parse(fs.readFileSync(path.join(REC, 'scenes.json'), 'utf8'));
// The capture starts before the first beat, so every clip shifts by that amount.
const preRoll = meta.preRollMs || 0;
const scenes = meta.scenes || meta;
// The audit is warmed and injected now, so pre-roll is a couple of seconds of
// setup rather than minutes. Offset the narration by it instead of trimming the
// video, because the Playwright capture is variable frame rate and seeking into
// it is not frame accurate.
console.log(`pre-roll ${(preRoll / 1000).toFixed(1)}s, offsetting narration by it`);
const webm = fs.readdirSync(REC).find(f => f.endsWith('.webm'));
if (!webm) { console.error('no screen recording found in ' + REC); process.exit(1); }

const args = ['-y', '-i', path.join(REC, webm)];
scenes.forEach(s => args.push('-i', path.join(__dirname, 'audio', s.id + '.mp3')));

// Delay each narration clip to the moment its scene began, then mix.
const parts = [], labels = [];
scenes.forEach((s, i) => {
  const idx = i + 1;                         // input 0 is the video
  const delay = Math.max(preRoll + s.startMs, 300);
  parts.push(`[${idx}]adelay=${delay}:all=1[a${idx}]`);
  labels.push(`[a${idx}]`);
});
const filter = parts.join(';') + ';' + labels.join('') +
  `amix=inputs=${scenes.length}:normalize=0:dropout_transition=0[aout]`;

args.push(
  '-filter_complex', filter,
  '-map', '0:v', '-map', '[aout]',
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '22',
  '-pix_fmt', 'yuv420p', '-r', '25',
  '-c:a', 'aac', '-b:a', '160k', '-ar', '44100', '-ac', '2',
  '-movflags', '+faststart',
  OUT
);

console.log(`muxing ${scenes.length} narration clips onto ${webm}`);
execFileSync(FF, args, { stdio: ['ignore', 'ignore', 'inherit'] });

console.log('wrote', OUT, (fs.statSync(OUT).size / 1048576).toFixed(1) + ' MB');
