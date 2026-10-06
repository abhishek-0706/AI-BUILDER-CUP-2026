/* Cold-open recorder.
   The audit is run and the AI content pre-generated in a warm-up pass BEFORE
   recording starts, so the video opens on the strongest frame instead of on a
   loading state. Every scene is then held for exactly the length of its
   narration clip, and scenes.json records the real start time of each. */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const KEY = process.env.GK;
const OUT = process.argv[2];
const DUR = JSON.parse(fs.readFileSync(path.join(__dirname, 'durations.json'), 'utf8'));
const d = id => (DUR.find(x => x.id === id) || { dur: 6 }).dur * 1000;
const CLIP = 'C:/Users/abhishek.q.agarwal/Downloads/retail-iq/demo/samples/shelf_videos/shelf_walk_05.mp4';
const REP_LINES = [
  'Protiva is 20g of protein at Rs 70. That is Rs 3.50 a gram against Rs 9 for the Hershey milkshake beside it.',
  'Ready to drink protein grew 31 percent year on year while packaged dairy beverages grew under 5. Give me 6 facings at eye level from 3 November and I will fund the chiller cling.',
];

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
    await run();
    await settle(w, sel, min);
    cache[label] = await w.textContent(sel);
    console.log('  cached', label, cache[label].length, 'chars');
  };
  await grab('pitch', async () => { await w.click('.rep-tabs button:nth-child(2)'); await w.click('#pitch-btn'); }, '#pitch-out', 300);
  await grab('order', async () => { await w.click('.rep-tabs button:nth-child(5)'); await w.click('#order-btn'); }, '#order-out', 200);
  await grab('debrief', async () => {
    await w.click('.rep-tabs button:nth-child(6)');
    await w.fill('#debrief-in', 'Vikram agreed to trial 6 facings from 3 November if we fund the chiller cling. Would not move on the 330ml. Salad shrink still unresolved.');
    await w.click('#debrief-btn');
  }, '#debrief-out', 300);
  await grab('coach', async () => { await w.click('#tab-biz'); await w.click('#coach-btn'); }, '#coach-out', 250);
  await w.click('#tab-rep');
  await w.click('.rep-tabs button:nth-child(4)');
  await w.waitForTimeout(400);
  await w.setInputFiles('#shelf-file', CLIP);
  await w.waitForSelector('#plano-btn', { state: 'visible', timeout: 60000 });
  await w.click('#plano-btn');
  await w.waitForSelector('#plano-out .plano-hd', { timeout: 120000 }).catch(() => {});
  await w.waitForTimeout(900);
  cache.plano = await w.evaluate(() => ({
    status: document.getElementById('sample-status').innerHTML,
    strip: document.getElementById('frame-strip').innerHTML,
    verdict: document.getElementById('plano-out').innerHTML,
  }));
  console.log('  cached audit verdict', cache.plano.verdict.length, 'chars');
  // The rehearsal needs a real exchange before it can be scored, so run the
  // whole thing here and keep both the transcript and the score.
  await w.click('#tab-rep');
  await w.click('.rep-tabs button:nth-child(3)');
  await w.click('text=Start session');
  await settle(w, '#reh-body', 60);
  for (const line of REP_LINES) {
    await w.fill('#reh-in', line);
    await w.click('#pane-rehearse .chat-input button');
    await settle(w, '#reh-body', 300);
  }
  cache.buyer = await w.evaluate(() => {
    const m = [...document.querySelectorAll('#reh-body .msg')];
    return m.map(x => ({ who: x.classList.contains('user') ? 'rep' : 'buyer', text: x.textContent }));
  });
  console.log('  cached rehearsal turns', cache.buyer.length);
  await w.click('text=End and score');
  await settle(w, '#reh-score', 250);
  cache.score = await w.textContent('#reh-score');
  console.log('  cached score', cache.score.length, 'chars');
  await warm.close();

  /* ── recorded pass ──────────────────────────────────────────────────── */
  const ctx = await browser.newContext({
    viewport: { width: 1600, height: 900 },
    recordVideo: { dir: OUT, size: { width: 1600, height: 900 } },
  });
  const recStart = Date.now();   // capture begins here, not at the first beat
  const p = await ctx.newPage();
  await p.addInitScript(k => localStorage.setItem('retailiq_gemini_key', k), KEY);
  await p.goto('http://localhost:5190/index.html?role=rep', { waitUntil: 'networkidle' });
  await p.waitForTimeout(700);

  // Put the warmed audit on screen instantly, so the capture opens on the result.
  await p.click('.rep-tabs button:nth-child(4)');
  await p.waitForTimeout(400);
  await p.evaluate(c => {
    document.getElementById('sample-status').style.display = 'block';
    document.getElementById('sample-status').innerHTML = c.status;
    document.getElementById('frame-strip').innerHTML = c.strip;
    const o = document.getElementById('plano-out');
    o.style.display = 'block';
    o.innerHTML = c.verdict;
    document.getElementById('plano-btn').style.display = 'inline-block';
    document.getElementById('plano-reset').style.display = 'inline-block';
    document.getElementById('drop').style.display = 'none';
  }, cache.plano);
  await p.waitForTimeout(500);
  await p.evaluate(() => {
    const el = document.querySelector('#plano-out .plano-hd');
    if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 86 });
  });
  await p.waitForTimeout(700);

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
  const tab = async n => { await p.click(`.rep-tabs button:nth-child(${n})`); await p.waitForTimeout(450); };
  const scroll = async (y, ms = 850) => {
    await p.evaluate(v => window.scrollTo({ top: v, behavior: 'smooth' }), y);
    await p.waitForTimeout(ms);
  };
  // Replace a pane's text with the warmed result so nothing waits on the model.
  const inject = async (sel, label) => {
    await p.evaluate(([s, t]) => {
      const el = document.querySelector(s);
      el.style.display = 'block';
      el.textContent = t;
    }, [sel, cache[label]]);
    await p.waitForTimeout(300);
  };

  // 00 hook, 01 problem, 02 honesty: all on the audit verdict
  await beat('00_hook', 'cold open on the verdict');
  await beat('01_problem', 'reset drift');
  await p.evaluate(() => {
    const el = document.querySelector('#plano-out .plano-rules-out');
    if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 110, behavior: 'smooth' });
  });
  await p.waitForTimeout(850);
  await beat('02_honest', 'computed score, honest refusal');

  // 03 phantom stock
  await p.locator('#cap-R01').scrollIntoViewIfNeeded();
  await p.evaluate(() => window.scrollBy({ top: -150 }));
  await p.waitForTimeout(700);
  await p.locator('#cap-R01 .cap-oos input').check();
  await p.waitForTimeout(900);
  await beat('03_phantom', 'phantom stock');

  // 04 pitch, 05 citation
  await scroll(0, 500);
  await tab(2);
  await inject('#pitch-out', 'pitch');
  await p.evaluate(t => renderCitations(t, document.getElementById('pitch-cites')), cache.pitch);
  await p.waitForTimeout(500);
  await scroll(300);
  await beat('04_pitch', 'cite or stay silent');
  const verified = await p.evaluate(() => {
    const chips = [...document.querySelectorAll('#pitch-cites .cite')];
    const v = chips.find(c => c.querySelector('.vfy')) || chips[0];
    if (v) { v.click(); return !!v.querySelector('.vfy'); }
    return false;
  });
  console.log('    opened a verified source:', verified);
  await p.waitForTimeout(800);
  await scroll(560);
  await beat('05_cite', 'the source opens');

  // 06 rehearse, 07 score
  await scroll(0, 500);
  await tab(3);
  // Replay the warmed exchange turn by turn so it reads as a conversation
  // without waiting on the model on camera.
  await p.evaluate(() => {
    const b = document.getElementById('reh-body');
    b.innerHTML = ''; b.dataset.clean = '1';
  });
  const showTurn = async turn => {
    await p.evaluate(t => {
      const b = document.getElementById('reh-body');
      const d = document.createElement('div');
      d.className = 'msg ' + (t.who === 'rep' ? 'user' : 'bot');
      d.style.maxWidth = '90%';
      d.textContent = t.text;
      b.appendChild(d); b.scrollTop = b.scrollHeight;
    }, turn);
  };
  // First turn before the beat so the panel is not empty on the cut.
  await showTurn(cache.buyer[0]);
  await p.waitForTimeout(600);
  await beat('06_rehearse', 'the buyer pushes back', async () => {
    const rest = cache.buyer.slice(1);
    const gap = Math.max(900, (d('06_rehearse') - 1500) / Math.max(rest.length, 1));
    for (const turn of rest) {
      await showTurn(turn);
      await p.waitForTimeout(gap);
    }
  });
  await inject('#reh-score', 'score');
  await scroll(430);
  await beat('07_score', 'separate scorer');

  // 08 order
  await scroll(0, 500);
  await tab(5);
  await inject('#order-out', 'order');
  await scroll(330);
  await beat('08_order', 'order from findings');

  // 09 debrief
  await scroll(0, 500);
  await tab(6);
  await p.fill('#debrief-in', 'Vikram agreed to trial 6 facings from 3 November if we fund the chiller cling. Would not move on the 330ml. Salad shrink still unresolved.');
  await inject('#debrief-out', 'debrief');
  await scroll(340);
  await beat('09_debrief', 'post-visit record');

  // 10 manager
  await scroll(0, 500);
  await p.click('#tab-biz');
  await p.waitForTimeout(700);
  await inject('#coach-out', 'coach');
  await scroll(540);
  await beat('10_manager', 'team, coverage, coaching');

  // 11 close
  await scroll(0, 600);
  await p.click('#tab-rep');
  await p.waitForTimeout(500);
  await tab(2);
  await beat('11_close', 'closing');
  await p.waitForTimeout(500);

  await ctx.close();
  await browser.close();
  const preRollMs = t0 - recStart;
  fs.writeFileSync(path.join(OUT, 'scenes.json'),
    JSON.stringify({ preRollMs, scenes }, null, 1));
  console.log(`pre-roll before the first beat: ${(preRollMs / 1000).toFixed(1)}s`);
  const total = (preRollMs + scenes.at(-1).startMs) / 1000 + DUR.at(-1).dur;
  console.log(`\n${scenes.length} beats, runtime about ${Math.floor(total / 60)}:${String(Math.round(total % 60)).padStart(2, '0')}`);
})();
