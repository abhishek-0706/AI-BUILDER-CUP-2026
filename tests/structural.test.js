/* Structural and correctness checks. No API key required.
   Covers the defect classes found in audit, so a regression surfaces here first. */
const { chromium } = require('playwright');
const path = require('path');

const URL = process.env.RETAILIQ_URL || 'http://localhost:5190/index.html?role=rep';
const VIDEO = path.resolve(__dirname, '..', 'demo', 'samples', 'shelf_videos', 'shelf_walk_03.mp4');

let pass = 0, fail = 0;
const T = (name, ok) => { ok ? pass++ : fail++; console.log((ok ? 'PASS' : 'FAIL') + '  ' + name); };

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
  const errs = [];
  page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text()); });

  await page.goto(URL, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);

  console.log('\n-- fixture dates all reconcile to one day --');
  // Every stated interval must agree on the same "today", or the planner,
  // targets and coaching prompts each reason about a different date.
  const dates = await page.evaluate(() => {
    const D = RETAIL_DATA;
    const day = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000);
    return {
      impliedByVisits: D.visits.map(v => {
        const t = new Date(v.lastVisit);
        t.setDate(t.getDate() + v.daysSince);
        return t.toISOString().slice(0, 10);
      }),
      elapsed: D.rep.monthDaysElapsed,
      total: D.rep.monthDaysTotal,
    };
  });
  const todays = [...new Set(dates.impliedByVisits)];
  T(`every visit implies the same today (${todays.join(', ')})`, todays.length === 1);
  T(`month day ${dates.elapsed} matches that date`,
    todays.length === 1 && Number(todays[0].slice(8)) === dates.elapsed);
  T('days remaining is consistent',
    new RegExp(String(dates.total - dates.elapsed)).test(await page.textContent('#pace-box')));
  T(`pace shown as day ${dates.elapsed} of ${dates.total}`,
    new RegExp(`Day ${dates.elapsed} of ${dates.total}`).test(await page.textContent('#tgt-cap')));
  T('days since last visit preserved', /41 days ago/.test(await page.textContent('.brief-card')));

  console.log('\n-- KPIs derive from the revenue table --');
  await page.click('#tab-biz'); await page.waitForTimeout(400);
  const kpis = (await page.locator('.kpi').allTextContents()).join(' ').replace(/\s+/g, ' ');
  T('average basket derived, not hardcoded', /₹712/.test(kpis));
  T('transaction count derived', /627 transactions/.test(kpis));
  T('KPI labelled below reorder point', /Below Reorder Point/.test(kpis));
  const belowN = await page.evaluate(() => RETAIL_DATA.products.filter(p => p.stock <= p.reorderAt).length);
  T(`below-reorder count derived from stock (${belowN})`,
    kpis.replace(/\s+/g, ' ').includes('Below Reorder Point ' + belowN));
  T('no NaN or undefined in KPI strip', !/NaN|undefined/.test(kpis));

  console.log('\n-- segment baskets reconcile to the daily average --');
  const recon = await page.evaluate(() => {
    const D = RETAIL_DATA;
    const today = D.revenueWeek[D.revenueWeek.length - 1];
    const actual = today.revenue / today.transactions;
    const weighted = D.segments.reduce((s, x) => s + x.pct / 100 * x.avgBasket, 0);
    return { actual, weighted };
  });
  T(`share-weighted ${recon.weighted.toFixed(0)} matches actual ${recon.actual.toFixed(0)}`,
    Math.abs(recon.weighted - recon.actual) < 5);

  console.log('\n-- forecast confidence band is drawn, not just claimed --');
  T('seven band elements rendered', await page.locator('.bar .band').count() === 7);

  console.log('\n-- planogram is scoped to its own bay --');
  await page.click('#tab-rep'); await page.waitForTimeout(300);
  const bay = await page.evaluate(() => baySKUs().map(p => p.name));
  const assigned = await page.evaluate(() => RETAIL_DATA.planogram.skuIds.length);
  T(`bay holds exactly its ${assigned} planogrammed SKUs`, bay.length === assigned);
  T('bay contains only chilled SKUs, no bars or salads',
    !bay.some(n => /Bar|Salad|Bowl/.test(n)));
  T('only in-bay promotions listed', (await page.evaluate(() => bayPromos().length)) === 1);
  T('facing minimum read from the planogram', await page.evaluate(() => minFacings()) === 2);
  const brands = await page.evaluate(() => RETAIL_DATA.planogram);
  T('our brands named, not inferred from SKU text', brands.ourBrands.length >= 1);
  T('competitor brands named separately', brands.competitorBrands.length >= 1);
  T('no brand is listed as both ours and a competitor',
    !brands.ourBrands.some(b => brands.competitorBrands.includes(b)));

  console.log('\n-- capture input cannot emit nonsense into a prompt --');
  await page.click('.rep-tabs button:nth-child(4)'); await page.waitForTimeout(400);
  await page.fill('#cap-R01 .cap-cnt input', '-5'); await page.waitForTimeout(250);
  T('negative facings clamped to zero', await page.inputValue('#cap-R01 .cap-cnt input') === '0');
  await page.fill('#cap-R01 .cap-cnt input', '999'); await page.waitForTimeout(250);
  T('absurd facings clamped to 40', await page.inputValue('#cap-R01 .cap-cnt input') === '40');
  await page.fill('#cap-R01 .cap-cnt input', ''); await page.waitForTimeout(200);
  await page.locator('#cap-R02 .cap-oos input').check(); await page.waitForTimeout(300);
  const summary = await page.evaluate(() => captureSummary());
  T('no negative count reaches the prompt', !/-\d+ facings/.test(summary));
  T('out of stock contradiction surfaced', /OUT OF STOCK/.test(summary));

  console.log('\n-- order reacts to what was captured in the aisle --');
  await page.click('.rep-tabs button:nth-child(5)'); await page.waitForTimeout(500);
  const flagged = await page.locator('.order-row').filter({ hasText: 'Coffee' }).first().textContent();
  T('shelf finding appears as an order driver', /out of stock on shelf/i.test(flagged));
  const total = await page.textContent('#order-total');
  T('order valued at trade price', /AT TRADE/.test(total));
  const ourCount = await page.evaluate(() => RETAIL_DATA.products.filter(p => p.ours).length);
  const lineCount = await page.locator('.order-row').count();
  T(`order scoped to the rep portfolio, not the store assortment (${lineCount} of ${ourCount})`,
    lineCount > 0 && lineCount <= ourCount);
  const competitorInOrder = await page.locator('.order-row').filter({ hasText: /Hershey|Sofit/ }).count();
  T('no competitor SKU in our order', competitorInOrder === 0);
  await page.locator('.order-row .or-qty input').first().fill('-500'); await page.waitForTimeout(400);
  T('negative quantity cannot make a negative total', !/₹-/.test(await page.textContent('#order-total')));

  console.log('\n-- state does not leak between visits --');
  await page.click('.rep-tabs button:nth-child(4)'); await page.waitForTimeout(300);
  await page.setInputFiles('#shelf-file', VIDEO);
  await page.waitForSelector('#plano-btn', { state: 'visible', timeout: 60000 });
  T('frames sampled and ranked', await page.locator('.strip .frame').count() === 6);
  await page.locator('.visit-card').nth(1).click(); await page.waitForTimeout(700);
  T('frames cleared on visit switch', await page.locator('.strip .frame').count() === 0);
  T('audit button disarmed', !(await page.locator('#plano-btn').isVisible()));
  T('file picker restored', await page.locator('#drop').isVisible());

  console.log('\n-- a broken clip leaves the pane usable --');
  await page.setInputFiles('#shelf-file',
    { name: 'broken.mp4', mimeType: 'video/mp4', buffer: Buffer.from('not a video') });
  await page.waitForTimeout(3500);
  T('failure explained to the user', /could not decode|too long|no readable/i.test(await page.textContent('#sample-status')));
  T('picker available again', await page.locator('#drop').isVisible());
  T('no audit armed on a failed load', !(await page.locator('#plano-btn').isVisible()));

  console.log('\n-- prompts contain what they ask the model to reason about --');
  const rc = await page.evaluate(() => repContext());
  T('competitive intelligence reaches the rep prompt', /Competitive alert/.test(rc));
  T('planogram reaches the rep prompt', /PLANOGRAM FOR THIS STORE/.test(rc));
  const tc = await page.evaluate(() => targetContext());
  const cats = await page.evaluate(() => RETAIL_DATA.targets.byCategory.map(c => c.cat));
  T('every target category reaches the target prompt', cats.every(c => tc.includes(c)));
  T('trade price reaches the target prompt', /trade Rs/.test(tc));
  T('coverage exposure reaches the coaching prompt', /quota exposure/.test(await page.evaluate(() => teamContext())));
  const bc = await page.evaluate(() => bizContext());
  T('reorder SKUs are named for the analyst', /at or below their reorder point/.test(bc));
  T('no deleted fixture field is still read', !/undefined/.test(bc));

  console.log('\n' + (errs.length ? 'JS ERRORS:\n' + errs.join('\n') : 'No JavaScript errors.'));
  console.log(`\n${pass} passed, ${fail} failed`);
  await browser.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
