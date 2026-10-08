/* Cold-open recorder.
   The audit is run and the AI content pre-generated in a warm-up pass BEFORE
   recording starts, so the video opens on the strongest frame instead of on a
   loading state. Every scene is then held for exactly the length of its
   narration clip, and scenes.json records the real start time of each. */
const { chromium } = require('playwright');
const { spawnSync } = require('child_process');
const FF = require('ffmpeg-static');
const fs = require('fs');
const path = require('path');

const KEY = process.env.GK;
const OUT = process.argv[2];
const DUR = JSON.parse(fs.readFileSync(path.join(__dirname, 'durations.json'), 'utf8'));
const d = id => (DUR.find(x => x.id === id) || { dur: 6 }).dur * 1000;
const CLIPS = [1, 2, 3, 4, 5, 6].map(i => `C:/Users/abhishek.q.agarwal/Downloads/retail-iq/demo/samples/shelf_videos/shelf_walk_0${i}.mp4`);
const FLYER_IMG = 'C:/Users/abhishek.q.agarwal/Downloads/retail-iq/demo/samples/protiva_flyer_shakes.png';
const FLYER_B64 = fs.readFileSync(FLYER_IMG).toString('base64');
const FLYER_MIME = 'image/png';
// errMsg() text from the app; a warm-up result containing one of these is retried, never cached.
const API_ERR = /Gemini is returning|Gemini is limiting|Gemini rejected|Gemini denied|Could not reach Gemini|key was rejected/;
// Spoken rehearsal: the rep first quotes the bar's 12g for the shake, the coach
// catches it, and she restates it correctly before sending.
const FUMBLE = 'So, Protiva has twelve grams of protein at seventy rupees, which makes it cheaper per gram than the Hershey milkshake beside it.';
const REP_LINES = [
  'Protiva is twenty grams of protein at seventy rupees. That is three rupees fifty a gram, against nine rupees for the Hershey milkshake beside it.',
  'Ready to drink protein grew 31 percent year on year while packaged dairy beverages grew under 5. Give me 6 facings at eye level from 3 November and I will fund the chiller cling.',
];
const VOICE = { buyer: ['en-IN-PrabhatNeural', '+6%', '+0Hz'], rep: ['en-IN-NeerjaExpressiveNeural', '+8%', '+12Hz'], coach: ['en-US-AndrewNeural', '+0%', '+0Hz'] };

const settle = async (p, sel, min = 200, to = 110000) => {
  const end = Date.now() + to;
  let prev = '', stable = 0;
  while (Date.now() < end) {
    await p.waitForTimeout(600);
    const now = (await p.textContent(sel).catch(() => '')) || '';
    if (now.length > min && now === prev) { if (++stable >= 5) break; } else stable = 0;
    prev = now;
  }
};

(async () => {
  const browser = await chromium.launch();

  /* ── warm-up: generate everything once, off camera ──────────────────── */
  console.log('warm-up pass, generating AI content off camera');
  const warm = await browser.newContext({ viewport: { width: 1600, height: 900 } });
  const w = await warm.newPage();
  await w.addInitScript(k => localStorage.setItem('retailiq_gemini_key', k), KEY);
  await w.goto('http://localhost:5190/index.html?role=rep', { waitUntil: 'networkidle' });
  await w.waitForTimeout(800);
  const cache = {};
  const grab = async (label, run, sel, min) => {
    for (let attempt = 1; ; attempt++) {
      await run();
      await settle(w, sel, min);
      cache[label] = await w.textContent(sel);
      if (!API_ERR.test(cache[label])) break;
      if (attempt === 4) throw new Error(`${label}: Gemini kept failing, not recording an error on camera`);
      console.log(`  ${label}: "${cache[label].trim().slice(0, 90)}", retrying in 8s`);
      await w.waitForTimeout(8000);
    }
    console.log('  cached', label, cache[label].length, 'chars');
  };
  await grab('pitch', async () => { await w.click('.rep-tabs button:nth-child(2)'); await w.click('#pitch-btn'); }, '#pitch-out', 300);
  // Flyer-enriched pitch: inject flyer into flyerFrames, re-run pitch gen
  await w.evaluate(({ b64, mime }) => {
    flyerFrames = [{ b64, mime, url: 'data:' + mime + ';base64,' + b64 }];
    document.getElementById('flyer-drop').style.display = 'none';
    document.getElementById('flyer-preview').style.display = 'block';
    document.getElementById('flyer-img').src = 'data:' + mime + ';base64,' + b64;
  }, { b64: FLYER_B64, mime: FLYER_MIME });
  await w.waitForTimeout(300);
  await grab('pitch_flyer', async () => { await w.click('#pitch-btn'); }, '#pitch-out', 300);
  await w.evaluate(() => {
    flyerFrames = [];
    document.getElementById('flyer-drop').style.display = 'block';
    document.getElementById('flyer-preview').style.display = 'none';
  });
  await grab('coach', async () => { await w.click('#tab-biz'); await w.click('#coach-btn'); }, '#coach-out', 250);
  await w.click('#tab-rep');
  await w.click('.rep-tabs button:nth-child(4)');
  await w.waitForTimeout(400);
  // Audit every real clip off camera, then show the best and the worst result,
  // so the video proves the audit separates a compliant shelf from a poor one.
  const audits = [];
  for (const clip of CLIPS) {
    for (let attempt = 1; attempt <= 3; attempt++) {
      await w.setInputFiles('#shelf-file', clip);
      await w.waitForSelector('#plano-btn', { state: 'visible', timeout: 60000 });
      await w.click('#plano-btn');
      await w.waitForSelector('#plano-out .plano-hd', { timeout: 120000 }).catch(() => {});
      await w.waitForTimeout(900);
      const r = await w.evaluate(() => ({
        status: document.getElementById('sample-status').innerHTML,
        strip: document.getElementById('frame-strip').innerHTML,
        verdict: document.getElementById('plano-out').innerHTML,
        score: lastAudit ? lastAudit.score : null,
        label: lastAudit ? lastAudit.status : '',
      }));
      if (/plano-hd/.test(r.verdict) && !API_ERR.test(r.verdict) && r.score !== null) {
        audits.push({ clip, ...r });
        console.log(`  audited ${path.basename(clip)}: ${r.score}% ${r.label}`);
        break;
      }
      console.log(`  ${path.basename(clip)}: no scored verdict (attempt ${attempt})`);
      await w.waitForTimeout(8000);
    }
  }
  if (audits.length < 2) throw new Error('fewer than two clips produced a scored audit');
  audits.sort((x, y) => y.score - x.score);
  cache.planoGood = audits[0];
  cache.planoPoor = audits.at(-1);
  console.log(`  showing ${path.basename(cache.planoGood.clip)} (${cache.planoGood.score}%) then ${path.basename(cache.planoPoor.clip)} (${cache.planoPoor.score}%)`);
  if (cache.planoGood.score - cache.planoPoor.score < 30) console.log('  warning: the two results are close; check the narration still fits');
  // The debrief should reflect the last audit shown on camera, so rerun it last.
  await w.setInputFiles('#shelf-file', cache.planoPoor.clip);
  await w.waitForSelector('#plano-btn', { state: 'visible', timeout: 60000 });
  await w.click('#plano-btn');
  await w.waitForSelector('#plano-out .plano-hd', { timeout: 120000 }).catch(() => {});
  // Order and debrief come after the audit in the story, so generate them from
  // the same findings shown on camera: the audit plus R01 counted out of stock.
  await w.locator('#cap-R01 .cap-oos input').check();
  await grab('order', async () => { await w.click('.rep-tabs button:nth-child(5)'); await w.click('#order-btn'); }, '#order-out', 200);
  await grab('debrief', async () => {
    await w.click('.rep-tabs button:nth-child(6)');
    await w.fill('#debrief-in', 'Vikram agreed to trial 6 facings from 3 November if we fund the chiller cling. Would not move on the 330ml. Salad shrink still unresolved.');
    await w.click('#debrief-btn');
  }, '#debrief-out', 300);
  // The rehearsal needs a real exchange before it can be scored, so run the
  // whole thing here and keep both the transcript and the score.
  await w.click('#tab-rep');
  await w.click('.rep-tabs button:nth-child(3)');
  for (let attempt = 1; ; attempt++) {
    await w.click('text=Start session');
    await settle(w, '#reh-body', 60);
    if (!API_ERR.test(await w.textContent('#reh-body'))) break;
    if (attempt === 4) throw new Error('rehearsal: Gemini kept failing on the buyer opening');
    console.log('  rehearsal opening: API error, retrying in 8s');
    await w.waitForTimeout(8000);
  }
  // Coach warm-up on the wrong figure. The video shows the coach catching it,
  // so a tip that does not correct 12 to 20 is retried, never faked.
  await w.click('#coach-toggle');
  for (let attempt = 1; ; attempt++) {
    await w.fill('#reh-in', '');
    await w.fill('#reh-in', FUMBLE);
    await w.waitForTimeout(1200);
    await w.waitForSelector('#coach-tip', { state: 'visible', timeout: 30000 }).catch(() => {});
    await settle(w, '#coach-tip', 10, 20000);
    cache.coachTip = ((await w.textContent('#coach-tip').catch(() => '')) || '').trim();
    if (/\b20\b|twenty/i.test(cache.coachTip) && !API_ERR.test(cache.coachTip)) break;
    console.log(`  coach tip did not correct the figure: "${cache.coachTip}"`);
    if (attempt === 4) throw new Error('coach never corrected the wrong protein figure');
    await w.waitForTimeout(3000);
  }
  console.log('  cached coach tip:', cache.coachTip);
  await w.click('#coach-toggle'); // off for main rehearsal
  await w.fill('#reh-in', '');
  for (const line of REP_LINES) {
    await w.fill('#reh-in', line);
    await w.click('#pane-rehearse .chat-input button');
    await settle(w, '#reh-body', 300);
  }
  cache.buyer = await w.evaluate(() => {
    const m = [...document.querySelectorAll('#reh-body .msg')];
    return m.map(x => ({ who: x.classList.contains('user') ? 'rep' : 'buyer', text: x.textContent }));
  });
  if (cache.buyer.some(t => API_ERR.test(t.text))) throw new Error('rehearsal: a buyer turn came back as an API error, rerun');
  console.log('  cached rehearsal turns', cache.buyer.length);
  const VDIR = path.join(__dirname, 'voices');
  fs.rmSync(VDIR, { recursive: true, force: true });
  fs.mkdirSync(VDIR);
  const say = (id, text, who) => {
    const file = path.join(VDIR, id + '.mp3');
    const [voice, rate, pitch] = VOICE[who];
    const r = spawnSync('python', ['-c',
      'import sys,asyncio,edge_tts;asyncio.run(edge_tts.Communicate(sys.argv[1],sys.argv[2],rate=sys.argv[3],pitch=sys.argv[4]).save(sys.argv[5]))',
      text.replace(/₹/g, 'rupees '), voice, rate, pitch, file], { encoding: 'utf8' });
    if (r.status !== 0) throw new Error(`voice ${id} failed: ${(r.stderr || '').slice(0, 200)}`);
    const m = spawnSync(FF, ['-i', file], { encoding: 'utf8' }).stderr.match(/Duration: (\d+):(\d+):([\d.]+)/);
    return { file, ms: Math.round((+m[1] * 3600 + +m[2] * 60 + +m[3]) * 1000) };
  };
  cache.voice = {
    buyerOpen: say('buyer_open', cache.buyer[0].text, 'buyer'),
    fumble: say('rep_fumble', FUMBLE, 'rep'),
    coach: say('coach_tip', cache.coachTip, 'coach'),
    fix: say('rep_fix', 'Right, twenty grams. ' + REP_LINES[0], 'rep'),
    buyerReply: say('buyer_reply', cache.buyer[2].text, 'buyer'),
  };
  console.log('  voiced the exchange:', Object.entries(cache.voice).map(([k, v]) => `${k} ${(v.ms / 1000).toFixed(1)}s`).join(', '));
  await grab('score', async () => { await w.click('text=End and score'); }, '#reh-score', 250);
  console.log('  cached score', cache.score.length, 'chars');
  await warm.close();

  /* ── recorded pass: pre-visit, during, post-visit, in that order ────── */
  // Every transition runs inside its beat, while the line is being spoken, so
  // narration clips sit back to back with no silent hand-offs between them.
  const ctx = await browser.newContext({
    viewport: { width: 1600, height: 900 },
    recordVideo: { dir: OUT, size: { width: 1600, height: 900 } },
  });
  const recStart = Date.now();   // capture begins here; mux.js trims up to the first beat
  const p = await ctx.newPage();
  await p.addInitScript(k => localStorage.setItem('retailiq_gemini_key', k), KEY);
  await p.goto('http://localhost:5190/index.html', { waitUntil: 'networkidle' });
  await p.waitForTimeout(400);

  const t0 = Date.now();
  const scenes = [];
  const beat = async (id, label, during) => {
    const at = (Date.now() - t0) / 1000;
    scenes.push({ id, startMs: Math.round(at * 1000), label });
    console.log(`${at.toFixed(1)}s  ${id}  ${label}`);
    const started = Date.now();
    if (during) await during();
    const left = d(id) - (Date.now() - started);
    if (left > 0) await p.waitForTimeout(left);
    else console.log(`    warning: ${id} overran its narration by ${Math.round(-left)}ms`);
  };
  const tab = async n => { await p.click(`.rep-tabs button:nth-child(${n})`); await p.waitForTimeout(350); };
  const scroll = async (y, ms = 700) => {
    await p.evaluate(v => window.scrollTo({ top: v, behavior: 'smooth' }), y);
    await p.waitForTimeout(ms);
  };
  const scrollTo = async (sel, offset, ms = 700) => {
    await p.evaluate(([s, o]) => {
      const el = document.querySelector(s);
      if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - o, behavior: 'smooth' });
    }, [sel, offset]);
    await p.waitForTimeout(ms);
  };
  // Replace a pane's text with the warmed result so nothing waits on the model.
  const inject = async (sel, label) => {
    await p.evaluate(([s, t]) => {
      const el = document.querySelector(s);
      el.style.display = 'block';
      el.textContent = t;
    }, [sel, cache[label]]);
    await p.waitForTimeout(150);
  };
  // Phase label that fades in over the app and out again, without blocking.
  const chapter = (kicker, title) => p.evaluate(([k, t]) => {
    const o = document.createElement('div');
    // Lime on the content area: dark green would vanish into the dark app header.
    o.innerHTML = `<b style="color:#0C6B5F;letter-spacing:2px;font-size:14px;font-weight:900">${k}</b>` +
      `<span style="width:1px;height:22px;background:rgba(10,58,51,.25)"></span><span>${t}</span>`;
    o.style.cssText = 'position:fixed;top:150px;left:66%;transform:translateX(-50%);z-index:2147483647;' +
      'display:flex;gap:16px;align-items:center;background:#C6F04A;color:#0A3A33;padding:18px 30px;' +
      'border-radius:16px;box-shadow:0 18px 44px rgba(10,58,51,.35);font:800 21px Inter,"Segoe UI",sans-serif;' +
      'white-space:nowrap;opacity:0;transition:opacity .45s';
    document.body.appendChild(o);
    requestAnimationFrame(() => { o.style.opacity = '1'; });
    setTimeout(() => { o.style.opacity = '0'; setTimeout(() => o.remove(), 500); }, 3400);
  }, [kicker, title]);
  const showTurn = turn => p.evaluate(t => {
    const b = document.getElementById('reh-body');
    const el = document.createElement('div');
    el.className = 'msg ' + (t.who === 'rep' ? 'user' : 'bot');
    el.style.maxWidth = '90%';
    el.textContent = t.text;
    b.appendChild(el); b.scrollTop = b.scrollHeight;
  }, turn);

  // Intro on the role picker
  // The problem is spoken first; each card lifts as "the rep, the manager and
  // the brand team" are named, then the rep card again for "follow one rep".
  await beat('00_intro', 'the problem, then three roles', async () => {
    const at = f => d('00_intro') * f;
    let t = 0;
    for (const [frac, n] of [[0.6, 1], [0.66, 2], [0.72, 3], [0.82, 1]]) {
      await p.waitForTimeout(Math.max(0, at(frac) - t));
      t = at(frac);
      await p.hover(`.sp-role:nth-child(${n})`);
    }
  });

  // PRE-VISIT
  await beat('01_plan', 'pre-visit: ranked day', async () => {
    await p.click('.sp-role:nth-child(1)');
    await p.waitForTimeout(500);
    await chapter('PRE-VISIT', 'Know the store before you knock');
    await p.waitForTimeout(Math.max(0, d('01_plan') / 2 - 900));
    await scroll(420);
  });
  await beat('02_pitch', 'cite or stay silent', async () => {
    await scroll(0, 300);
    await tab(2);
    await inject('#pitch-out', 'pitch');
    await p.evaluate(t => renderCitations(t, document.getElementById('pitch-cites')), cache.pitch);
    await scroll(300);
  });
  await beat('03_cite', 'the source opens', async () => {
    const verified = await p.evaluate(() => {
      const chips = [...document.querySelectorAll('#pitch-cites .cite')];
      const v = chips.find(c => c.querySelector('.vfy')) || chips[0];
      if (v) { v.click(); return !!v.querySelector('.vfy'); }
      return false;
    });
    console.log('    opened a verified source:', verified);
    await p.waitForTimeout(300);
    await scroll(560);
  });
  await beat('04_flyer', 'flyer enriches pitch', async () => {
    await scroll(0, 400);
    await p.evaluate(({ b64, mime }) => {
      flyerFrames = [{ b64, mime, url: 'data:' + mime + ';base64,' + b64 }];
      document.getElementById('flyer-drop').style.display = 'none';
      document.getElementById('flyer-preview').style.display = 'block';
      document.getElementById('flyer-img').src = 'data:' + mime + ';base64,' + b64;
    }, { b64: FLYER_B64, mime: FLYER_MIME });
    await p.waitForTimeout(500);
    await inject('#pitch-out', 'pitch_flyer');
    await p.evaluate(t => renderCitations(t, document.getElementById('pitch-cites')), cache.pitch_flyer);
    await scroll(220);
  });
  await beat('05_rehearse', 'practise the pitch out loud', async () => {
    await scroll(0, 300);
    await tab(3);
    await p.evaluate(() => { const b = document.getElementById('reh-body'); b.innerHTML = ''; b.dataset.clean = '1'; });
    await p.waitForTimeout(Math.max(0, d('05_rehearse') - 2500));
    await p.click('#coach-toggle');
  });

  // Live spoken exchange, no narration over it. Each clip is logged so mux.js
  // lays it at the moment it plays. The transcript is written without firing
  // input events, so no real coach call is made on camera.
  const voices = [];
  const play = async v => { voices.push({ file: v.file, startMs: Date.now() - t0 }); await p.waitForTimeout(v.ms); };
  const mic = on => p.evaluate(on => {
    document.getElementById('mic-dot').classList.toggle('live', on);
    document.getElementById('mic-btn').textContent = on ? 'Stop' : 'Voice input';
  }, on);
  const transcribe = async (text, v) => {
    voices.push({ file: v.file, startMs: Date.now() - t0 });
    const words = text.split(' ');
    const step = v.ms / words.length;
    for (let i = 1; i <= words.length; i++) {
      await p.evaluate(t => { document.getElementById('reh-in').value = t; }, words.slice(0, i).join(' '));
      await p.waitForTimeout(step);
    }
  };
  console.log(`${((Date.now() - t0) / 1000).toFixed(1)}s  (live)  spoken rehearsal`);
  await showTurn(cache.buyer[0]);
  await play(cache.voice.buyerOpen);
  await p.waitForTimeout(350);
  await mic(true);
  await transcribe(FUMBLE, cache.voice.fumble);
  await mic(false);
  await p.waitForTimeout(450);
  await p.evaluate(tip => {
    const el = document.getElementById('coach-tip');
    el.style.display = 'block'; el.style.opacity = '1';
    el.textContent = tip;
  }, cache.coachTip);
  await play(cache.voice.coach);
  await p.waitForTimeout(500);
  await mic(true);
  await transcribe('Right, twenty grams. ' + REP_LINES[0], cache.voice.fix);
  await mic(false);
  await p.waitForTimeout(250);
  await showTurn({ who: 'rep', text: REP_LINES[0] });
  await p.evaluate(() => {
    document.getElementById('reh-in').value = '';
    document.getElementById('coach-tip').style.display = 'none';
  });
  await p.waitForTimeout(400);
  await showTurn(cache.buyer[2]);
  await play(cache.voice.buyerReply);
  await p.waitForTimeout(400);

  await beat('06_coach', 'the coach caught it', async () => {});
  await beat('07_score', 'separate scorer', async () => {
    await p.fill('#reh-in', '');
    await p.evaluate(() => { document.getElementById('coach-tip').style.display = 'none'; });
    await p.click('#coach-toggle');
    await inject('#reh-score', 'score');
    await scroll(430);
  });

  // DURING VISIT
  const showAudit = c => p.evaluate(a => {
    document.getElementById('sample-status').style.display = 'block';
    document.getElementById('sample-status').innerHTML = a.status;
    document.getElementById('frame-strip').innerHTML = a.strip;
    const o = document.getElementById('plano-out');
    o.style.display = 'block';
    o.innerHTML = a.verdict;
    document.getElementById('plano-btn').style.display = 'inline-block';
    document.getElementById('plano-reset').style.display = 'inline-block';
    document.getElementById('drop').style.display = 'none';
  }, c);
  await beat('08_audit', 'during: compliant shelf', async () => {
    await scroll(0, 300);
    await tab(4);
    await showAudit(cache.planoGood);
    await chapter('DURING VISIT', 'Act on what is actually on the shelf');
    await p.waitForTimeout(Math.max(0, d('08_audit') / 2 - 1500));
    await scrollTo('#plano-out .plano-hd', 86);
  });
  await beat('09_honest', 'non-compliant shelf, computed score', async () => {
    await scrollTo('#plano-cap', 140, 500);
    await showAudit(cache.planoPoor);
    await p.waitForTimeout(1200);
    await scrollTo('#plano-out .plano-hd', 86);
    await p.waitForTimeout(Math.max(0, d('09_honest') / 2 - 2500));
    await scrollTo('#plano-out .plano-rules-out', 110);
  });
  await beat('10_phantom', 'phantom stock', async () => {
    await p.locator('#cap-R01').scrollIntoViewIfNeeded();
    await p.evaluate(() => window.scrollBy({ top: -150, behavior: 'smooth' }));
    await p.waitForTimeout(600);
    await p.locator('#cap-R01 .cap-oos input').check();
  });
  await beat('11_order', 'order from findings', async () => {
    await scroll(0, 300);
    await tab(5);
    await inject('#order-out', 'order');
    await scroll(330);
  });

  // POST-VISIT
  await beat('12_debrief', 'post-visit record', async () => {
    await scroll(0, 300);
    await tab(6);
    await chapter('POST-VISIT', 'Close the loop automatically');
    await p.fill('#debrief-in', 'Vikram agreed to trial 6 facings from 3 November if we fund the chiller cling. Would not move on the 330ml. Salad shrink still unresolved.');
    await inject('#debrief-out', 'debrief');
    await scroll(340);
  });
  await beat('13_manager', 'team, coverage, coaching', async () => {
    await scroll(0, 300);
    await p.click('#tab-biz');
    await p.waitForTimeout(500);
    await inject('#coach-out', 'coach');
    await scroll(540);
  });
  await beat('14_close', 'closing', async () => {
    await scroll(0, 300);
    await p.click('#tab-rep');
    await p.waitForTimeout(400);
    await tab(2);
  });
  await p.waitForTimeout(600);

  await ctx.close();
  await browser.close();
  const preRollMs = t0 - recStart;
  fs.writeFileSync(path.join(OUT, 'scenes.json'),
    JSON.stringify({ preRollMs, scenes, voices }, null, 1));
  console.log(`pre-roll before the first beat: ${(preRollMs / 1000).toFixed(1)}s`);
  const total = (preRollMs + scenes.at(-1).startMs) / 1000 + DUR.at(-1).dur;
  console.log(`\n${scenes.length} beats, runtime about ${Math.floor(total / 60)}:${String(Math.round(total % 60)).padStart(2, '0')}`);
})();
