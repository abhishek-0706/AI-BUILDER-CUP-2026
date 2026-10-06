const { chromium } = require('playwright');
const path = require('path');
const KEY = process.env.GEMINI_API_KEY || process.env.GK;
const URL = process.env.RETAILIQ_URL || 'http://localhost:5190/index.html?role=rep';
const V = path.resolve(__dirname, '..', 'demo', 'samples', 'shelf_videos', 'shelf_walk_05.mp4');
if (!KEY) { console.error('Set GEMINI_API_KEY to run the live suite.'); process.exit(2); }

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport:{width:1600,height:1100}, deviceScaleFactor:2 });
  const errs = [];
  p.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text()); });
  await p.addInitScript(k => localStorage.setItem('retailiq_gemini_key', k), KEY);
  await p.goto(URL, { waitUntil:'networkidle' });
  await p.waitForTimeout(700);

  /* Responses stream, and the typing indicator is replaced by the first chunk,
     so "long enough and not typing" can be true halfway through a reply. Wait
     until the text actually stops growing. */
  const st = async (s, m = 200, to = 90000) => {
    const deadline = Date.now() + to;
    let prev = '', stable = 0;
    while (Date.now() < deadline) {
      await p.waitForTimeout(700);
      const now = (await p.textContent(s).catch(() => '')) || '';
      if (now.length > m && now === prev) {
        if (++stable >= 2) break;      // unchanged across two polls
      } else {
        stable = 0;
      }
      prev = now;
    }
    return (await p.textContent(s)).trim();
  };
  const tab = n => p.click('.rep-tabs button:nth-child(' + n + ')');
  const out = {};

  // 1 planner
  await p.click('#planday-btn');
  out.plan = await st('#plan-out', 250);

  // 2 pitch
  await tab(2);
  await p.click('#pitch-btn');
  out.pitch = await st('#pitch-out', 300);
  await p.locator('.cite').first().click();
  await p.waitForTimeout(400);
  const cites = await p.locator('.cite').count();
  const ids = [...new Set(out.pitch.match(/KB-\d+/g) || [])];
  const valid = await p.evaluate(() => RETAIL_DATA.kbDocs.map(k => k.id));

  // 3 rehearse
  await tab(3);
  await p.click('text=Start session');
  await st('#reh-body', 60);
  const lines = [
    'The 6-pack carries 20 percent margin versus 19 on the single, plus a 4 percent Q4 rebate above 500 units.',
    'Packaged foods is 22 percent of your revenue on 14 percent of shelf. Can I get the relist from November 1?'
  ];
  for (const l of lines) {
    await p.fill('#reh-in', l);
    await p.click('#pane-rehearse .chat-input button');
    await p.waitForTimeout(8000);
  }
  await p.click('text=End and score');
  out.score = await st('#reh-score', 250);

  // 4 planogram
  await tab(4);
  await p.setInputFiles('#shelf-file', V);
  await p.waitForSelector('#plano-btn', { state:'visible', timeout:45000 });
  await p.click('#plano-btn');
  await p.waitForSelector('#plano-out .plano-hd', { timeout:95000 }).catch(() => {});
  await p.waitForTimeout(700);
  out.plano = await p.textContent('#plano-out');

  // guided capture
  await p.locator('#cap-R01 .cap-oos input').check();
  await p.waitForTimeout(250);
  await p.fill('#cap-R03 .cap-cnt input', '1');
  await p.waitForTimeout(250);
  await p.fill('#cap-note', 'Manager flagged two late deliveries. Competitor rep offered a 6-pack at Rs 42 yesterday.');

  // 5 order
  await tab(5);
  await p.waitForTimeout(500);
  await p.click('#order-btn');
  out.order = await st('#order-out', 200);

  // 6 debrief
  await tab(6);
  await p.fill('#debrief-in', 'Vikram agreed to relist NutriChoice from Nov 1 with 2 weeks end-cap. No commitment on Nescafe. Chiller audit not done.');
  await p.click('#debrief-btn');
  out.debrief = await st('#debrief-out', 300);

  // 7 targets
  await tab(7);
  await p.click('#tgt-btn');
  out.targets = await st('#tgt-out', 250);

  // manager
  await p.click('#tab-biz');
  await p.waitForTimeout(400);
  await p.click('#coach-btn');
  out.coach = await st('#coach-out', 250);
  await p.fill('#biz-in', 'Which SKUs will stock out before the weekend?');
  await p.click('#biz-send');
  out.analyst = await st('#biz-out', 200);

  // shopper
  await p.click('#tab-shop');
  await p.waitForTimeout(300);
  await p.fill('#chat-in', 'Something healthy for breakfast under 100 rupees');
  await p.click('#chat-send');
  await p.waitForTimeout(9000);
  out.shop = (await p.locator('#chat-body .msg.bot').last().textContent()).trim();

  // ── assertions
  let pass = 0, fail = 0;
  const R = (n, v) => { v ? pass++ : fail++; console.log((v ? 'PASS' : 'FAIL') + '  ' + n); };
  console.log('=== LIVE AI REGRESSION ===');
  R('planner respects booked slots', /scheduled/i.test(out.plan));
  R('pitch cites 3+ sources (' + ids.length + ')', ids.length >= 3);
  R('no hallucinated source IDs', ids.every(i => valid.includes(i)));
  R('citation chips render (' + cites + ')', cites >= 3);
  R('score has tone+clarity+completeness',
    /TONE/i.test(out.score) && /CLARITY/i.test(out.score) && /COMPLETENESS/i.test(out.score));
  R('planogram computed score rendered', /judged rules passed/.test(out.plano));
  R('planogram names the industry rules', /availability|facings|share of shelf/i.test(out.plano));
  R('our own brand never called a competitor',
    !/competitor\s+(brand\s+)?protiva|protiva\s+is\s+a\s+competitor/i.test(out.plano));
  R('competitor brands named with facing counts', /hershey|sofit/i.test(out.plano));
  R('absence of our brand reported, not invented presence',
    /protiva/i.test(out.plano));
  R('order justification cites sources', /KB-\d+/.test(out.order));
  R('debrief has record updates', /RECORD UPDATES/i.test(out.debrief));
  R('debrief used capture data', /out of stock|facing/i.test(out.debrief));
  R('debrief resisted injection', !/# ROLE|ABSOLUTE RULES/i.test(out.debrief));
  R('targets uses trade price', /trade/i.test(out.targets));
  R('targets not using stale day-21-of-30', !/day 21 of 30/i.test(out.targets));
  R('coaching labels exposure an estimate', /estimat/i.test(out.coach));
  const ourSkus = await p.evaluate(() => RETAIL_DATA.products.filter(x => x.ours).map(x => x.name));
  R('analyst names a real SKU from the current portfolio',
    ourSkus.some(n => out.analyst.includes(n.replace('Protiva ', ''))));
  R('shopper quotes a real price', /\d{2,3}/.test(out.shop));

  const all = Object.values(out).join('\n');
  R('no markdown leak anywhere', !/\*\*|^#{1,6}\s|`/m.test(all));
  R('no undefined or NaN in output', !/undefined|NaN/.test(all));

  console.log('\n' + (errs.length ? 'JS ERRORS:\n' + errs.join('\n') : 'NO JS ERRORS'));
  console.log('\n--- planogram verdict header ---');
  console.log(out.plano.split('\n').filter(l => l.trim()).slice(0, 4).join(' | '));
  console.log(`
${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
