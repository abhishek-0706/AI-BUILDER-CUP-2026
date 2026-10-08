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
// The capture starts before the first beat (page load), which would open the
// video on silence. It is cut with a trim filter on decoded frames, which is
// exact even on Playwright's variable frame rate webm, unlike an input seek.
const preRoll = meta.preRollMs || 0;
const scenes = meta.scenes || meta;
console.log(`pre-roll ${(preRoll / 1000).toFixed(1)}s, trimming it from the video`);
const webm = fs.readdirSync(REC).find(f => f.endsWith('.webm'));
if (!webm) { console.error('no screen recording found in ' + REC); process.exit(1); }

const args = ['-y', '-i', path.join(REC, webm)];
scenes.forEach(s => args.push('-i', path.join(__dirname, 'audio', s.id + '.mp3')));

// Delay each narration clip to the moment its scene began, then mix.
const parts = [], labels = [];
scenes.forEach((s, i) => {
  const idx = i + 1;                         // input 0 is the video
  const delay = Math.max(s.startMs, 1);
  parts.push(`[${idx}]adelay=${delay}:all=1[a${idx}]`);
  labels.push(`[a${idx}]`);
});
// Character voices in the spoken rehearsal, logged by record.js as they played.
const voices = meta.voices || [];
voices.forEach((v, i) => {
  const idx = scenes.length + i + 1;
  args.push('-i', v.file);
  parts.push(`[${idx}]adelay=${Math.max(v.startMs, 1)}:all=1[v${i}]`);
  labels.push(`[v${i}]`);
});
const DUR = JSON.parse(fs.readFileSync(path.join(__dirname, 'durations.json'), 'utf8'));
const last = scenes.at(-1);
const end = last.startMs / 1000 + (DUR.find(x => x.id === last.id) || { dur: 6 }).dur + 0.6;
const filter = `[0:v]trim=start=${(preRoll / 1000).toFixed(3)}:duration=${end.toFixed(3)},setpts=PTS-STARTPTS,` +
  `fade=t=in:st=0:d=0.6,fade=t=out:st=${(end - 0.7).toFixed(3)}:d=0.7[v];` +
  parts.join(';') + ';' + labels.join('') +
  `amix=inputs=${labels.length}:normalize=0:dropout_transition=0[aout]`;

args.push(
  '-filter_complex', filter,
  '-map', '[v]', '-map', '[aout]',
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '22',
  '-pix_fmt', 'yuv420p', '-r', '25',
  '-c:a', 'aac', '-b:a', '160k', '-ar', '44100', '-ac', '2',
  '-movflags', '+faststart',
  OUT
);

console.log(`muxing ${scenes.length} narration clips onto ${webm}`);
execFileSync(FF, args, { stdio: ['ignore', 'ignore', 'inherit'] });

console.log('wrote', OUT, (fs.statSync(OUT).size / 1048576).toFixed(1) + ' MB');
