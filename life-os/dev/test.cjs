// Run: node life-os/dev/test.cjs   (needs Playwright; uses a simulated Claude runtime, never the real one)
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('fs'); const path = require('path');
const DIR = __dirname; const OUT = path.join(DIR, '.out'); const SHOTS = path.join(OUT, 'shots'); fs.mkdirSync(SHOTS, {recursive: true});
const SEED = fs.readFileSync(path.join(DIR, '../seed/starter-data.json'), 'utf8');
const MOCK = fs.readFileSync(path.join(DIR, 'mock.js'), 'utf8');
// Wrap the page the way claude.ai does at publish time (doctype, viewport meta, small reset).
const PAGE = fs.readFileSync(path.join(DIR, '../index.html'), 'utf8');
fs.writeFileSync(path.join(OUT, 'page.html'), '<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style></head><body>' + PAGE + '</body></html>');
const URL = 'file://' + path.join(OUT, 'page.html');
const results = []; const errors = [];
async function step(name, fn) { try { await fn(); results.push(['PASS', name]); } catch (e) { results.push(['FAIL', name, String(e && e.message || e).split('\n')[0]]); } }
async function ctx(browser, opts, withMock = true, seed = true) {
  const c = await browser.newContext(opts);
  if (withMock) { await c.addInitScript(`window.__SEED__ = ${seed ? SEED : 'null'};`); await c.addInitScript(MOCK); }
  const p = await c.newPage();
  p.on('pageerror', e => errors.push('pageerror: ' + e.message));
  p.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  return p;
}
const overflow = p => p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
(async () => {
  const browser = await chromium.launch();
  const p = await ctx(browser, {viewport: {width: 1366, height: 900}, colorScheme: 'light'});
  await p.goto(URL); await p.waitForSelector('text=Prepare my briefing', {timeout: 8000});
  await p.waitForTimeout(400);
  await p.screenshot({path: SHOTS + '/01-today-empty.png', fullPage: false});

  await step('briefing generates and renders', async () => {
    await p.click('text=Prepare my briefing');
    await p.waitForSelector('text=The final decision', {timeout: 5000});
    const t = await p.textContent('#view');
    if (!t.includes('Turn guidelines into protocol checks')) throw new Error('theme missing');
    if (!t.includes('KDIGO 2026 Clinical Practice Guideline')) throw new Error('source link missing');
    if (t.includes('bogus-id')) throw new Error('invalid source id shown');
    await p.screenshot({path: SHOTS + '/02-today-briefing.png', fullPage: true});
  });
  await step('briefing section done toggle persists', async () => {
    await p.click('[data-act="brief-done"][data-idx="0"]'); await p.waitForTimeout(150);
    const pressed = await p.getAttribute('[data-act="brief-done"][data-idx="0"]', 'aria-pressed');
    if (pressed !== 'true') throw new Error('not pressed');
  });
  await step('check-in saves', async () => {
    await p.click('[data-act="ck-set"][data-id="energy"][data-v="4"]');
    await p.click('[data-act="ck-set"][data-id="mood"][data-v="3"]');
    await p.fill('#ck-sleep', '7'); await p.fill('#ck-focus', '90');
    await p.click('[data-act="ck-set"][data-id="oneThing"][data-v="yes"]');
    await p.fill('#ck-note', 'Calm morning');
    await p.click('[data-act="ck-save"]'); await p.waitForTimeout(250);
    const n = await p.evaluate(() => [...window.__store.keys()].filter(k => k.includes('/os/checkins/')).length);
    if (n !== 1) throw new Error('checkins ' + n);
    const t = await p.textContent('#view'); if (!t.includes('Update check-in')) throw new Error('button not updated');
  });
  await step('wheel scoring saves a snapshot', async () => {
    await p.click('[data-act="go"][data-id="wheel"] >> nth=0');
    await p.waitForSelector('.wheel-svg');
    for (const [k, s, d] of [['career', 6, 9], ['health', 5, 8], ['growth', 6, 8], ['finance', 4, 7], ['family', 7, 8], ['love', 6, 8], ['fun', 3, 6], ['spirit', 6, 8]]) {
      await p.click(`.dimrow[data-id="${k}"]`); await p.waitForSelector(`#wr-score-${k}`);
      await p.evaluate(([k, s, d]) => { for (const [f, v] of [['score', s], ['desired', d]]) { const r = document.getElementById(`wr-${f}-${k}`); r.value = v; r.dispatchEvent(new Event('input', {bubbles: true})); r.dispatchEvent(new Event('change', {bubbles: true})); } }, [k, s, d]);
    }
    await p.click('[data-act="wheel-status"][data-id="spirit"][data-v="maintain"]');
    await p.click('[data-act="wheel-save"]'); await p.waitForTimeout(250);
    const t = await p.textContent('#view'); if (!t.includes('last scored')) throw new Error('no snapshot');
    await p.screenshot({path: SHOTS + '/03-wheel.png', fullPage: true});
  });
  await step('goal proposal accepted from ladder', async () => {
    await p.click('.dimrow[data-id="career"]'); await p.waitForTimeout(100);
    await p.click('[data-act="goal-status"][data-v="active"] >> nth=0'); await p.waitForTimeout(150);
    const st = await p.evaluate(() => JSON.parse(JSON.stringify([...window.__store.entries()].filter(([k]) => k.endsWith('/g-seed-01'))[0][1])).status);
    if (st !== 'active') throw new Error(st);
  });
  await step('assess dimension with Claude', async () => {
    await p.click('[data-act="assess"][data-id="career"]'); await p.waitForSelector('text=Thin evidence so far.', {timeout: 4000});
  });
  await step('learning session: answer, AI grade, rate', async () => {
    await p.click('[data-act="go"][data-id="learn"] >> nth=0'); await p.waitForSelector('text=Learning engine');
    await p.screenshot({path: SHOTS + '/04-learn.png', fullPage: true});
    await p.click('[data-act="learn-start"] >> nth=0'); await p.waitForSelector('.flash');
    for (let i = 0; i < 3; i++) {
      await p.fill('.flash textarea', 'Loading 25 mg/kg then 500 mg after each session.');
      await p.click('[data-act="conf"][data-v="3"]'); await p.click('[data-act="reveal"]');
      await p.click('[data-act="ai-grade"]'); await p.waitForSelector('text=Transfer question', {timeout: 4000});
      if (i === 0) await p.screenshot({path: SHOTS + '/05-session.png', fullPage: true});
      await p.click(`[data-act="grade"][data-v="${i === 1 ? 1 : 3}"]`); await p.waitForTimeout(150);
    }
    await p.click('[data-act="session-end"]'); await p.waitForSelector('text=Session complete');
    await p.click('[data-act="session-close"]');
    const logs = await p.evaluate(() => [...window.__store.entries()].filter(([k]) => k.includes('/os/cards/')).reduce((s, [, v]) => s + (v.log || []).length, 0));
    if (logs !== 3) throw new Error('logs ' + logs);
  });
  await step('generate cards dedupes', async () => {
    await p.click('[data-act="sheet"][data-id="gen-cards"]'); await p.click('[data-act="gen-run"]');
    await p.waitForSelector('text=1 card added', {timeout: 4000});
    await p.click('[data-act="sheet-close"]');
  });
  await step('learn page charts render after answers', async () => {
    await p.waitForSelector('.constellation'); await p.screenshot({path: SHOTS + '/06-learn-after.png', fullPage: true});
  });
  await step('experiment create + logs + analysis', async () => {
    await p.click('[data-act="go"][data-id="lab"] >> nth=0');
    await p.click('[data-act="sheet"][data-id="exp-new"]');
    await p.fill('#xf-title', 'Morning first action'); await p.fill('#xf-measure', 'minutes to start'); await p.fill('#xf-unit', 'min');
    await p.click('[data-act="exp-create"]'); await p.waitForTimeout(200);
    const id = await p.evaluate(() => [...window.__store.keys()].find(k => k.includes('/os/experiments/x-') && !k.includes('seed')).split('/').pop());
    for (const [v, d] of [[30, '2026-10-01'], [25, '2026-10-02'], [35, '2026-10-03'], [28, '2026-10-04'], [32, '2026-10-05']]) { await p.fill(`#xl-v-${id}`, String(v)); await p.fill(`#xl-d-${id}`, d); await p.click(`[data-act="exp-log"][data-id="${id}"]`); await p.waitForTimeout(80); }
    await p.click(`[data-act="exp-phase"][data-id="${id}"]`); await p.waitForTimeout(120);
    for (const [v, d] of [[15, '2026-10-06'], [12, '2026-10-07'], [18, '2026-10-08'], [10, '2026-10-09'], [14, '2026-10-10']]) { await p.fill(`#xl-v-${id}`, String(v)); await p.fill(`#xl-d-${id}`, d); await p.click(`[data-act="exp-log"][data-id="${id}"]`); await p.waitForTimeout(80); }
    const t = await p.textContent('#view'); if (!t.includes('standardised difference')) throw new Error('no analysis');
    await p.screenshot({path: SHOTS + '/07-lab.png', fullPage: true});
  });
  await step('decision record + review', async () => {
    await p.click('[data-act="lab-tab"][data-id="decisions"]'); await p.click('[data-act="sheet"][data-id="dec-new"]');
    await p.fill('#df-title', 'Switch study block to mornings'); await p.fill('#df-reviewOn', '2026-10-01');
    await p.click('[data-act="dec-create"]'); await p.waitForTimeout(200);
    await p.click('[data-act="dec-review"][data-v="yes"]'); await p.waitForTimeout(150);
    const t = await p.textContent('#view'); if (!t.includes('Brier score')) throw new Error('no brier');
  });
  await step('library filters, flags, research request', async () => {
    await p.click('[data-act="go"][data-id="library"] >> nth=0'); await p.waitForSelector('.lib');
    await p.screenshot({path: SHOTS + '/08-library.png', fullPage: true});
    await p.click('[data-act="lib-flag"][data-id="lib-kdigo-anemia-2026"][data-v="applied"]'); await p.waitForTimeout(120);
    const l = await p.evaluate(() => [...window.__store.entries()].find(([k]) => k.endsWith('/lib-kdigo-anemia-2026'))[1]);
    if (!l.applied || !l.read) throw new Error('flags');
    await p.click('[data-act="lib-cat"][data-id="disputed"]'); await p.waitForTimeout(150); const n = await p.locator('.lib').count(); if (n !== 2) throw new Error('disputed count ' + n);
    await p.click('[data-act="lib-cat"][data-id="all"]');
    await p.click('[data-act="sheet"][data-id="research-req"]'); await p.fill('#rq-q', 'Any 2026 change to ferric carboxymaltose dosing in HD?'); await p.click('[data-act="queue-add"]'); await p.waitForTimeout(150);
    const t = await p.textContent('#view'); if (!t.includes('research request waiting')) throw new Error('queue not shown');
  });
  await step('model: proposals keep, memory edit, import', async () => {
    await p.click('[data-act="go"][data-id="model"] >> nth=0');
    await p.click('[data-act="model-tab"][data-id="pending"]'); await p.click('[data-act="mem-approve"] >> nth=0'); await p.waitForTimeout(120);
    await p.click('[data-act="model-tab"][data-id="memory"]'); await p.screenshot({path: SHOTS + '/09-model.png', fullPage: true});
    await p.click('[data-act="model-tab"][data-id="import"]');
    await p.fill('#imp-paste', '## Hobbies\nI want to learn calligraphy.\n\n\n## Work\nI want AI pharmacy tools.');
    await p.click('[data-act="imp-paste"]'); await p.click('[data-act="imp-run"]'); await p.waitForSelector('text=proposed', {timeout: 4000});
    const t = await p.textContent('#view'); if (!t.includes('1 memory proposed, 1 duplicate skipped')) throw new Error('import result: ' + t.match(/\d+ memor[^.]*\./));
  });
  await step('review save + synthesis', async () => {
    await p.click('[data-act="go"][data-id="review"] >> nth=0'); await p.fill('#rv-week-0', 'Finished the wheel.');
    await p.click('[data-act="review-save"]'); await p.waitForTimeout(100);
    await p.click('[data-act="review-ai"]'); await p.waitForSelector('text=A quiet week.', {timeout: 4000});
    await p.screenshot({path: SHOTS + '/10-review.png', fullPage: true});
  });
  await step('settings: test, export, privacy', async () => {
    await p.click('[data-act="go"][data-id="settings"] >> nth=0'); await p.click('[data-act="ai-test"]'); await p.waitForTimeout(400);
    const t = await p.textContent('#view'); if (!t.includes('claude-opus-5-5')) throw new Error('model not shown');
    await p.click('[data-act="export"]'); await p.waitForTimeout(150);
    const dl = await p.evaluate(() => window.__download); if (!dl || !dl.filename.endsWith('.json')) throw new Error('no download');
    await p.check('[data-privacy="relationships"]'); await p.waitForTimeout(150);
    const pv = await p.evaluate(() => [...window.__store.entries()].find(([k]) => k.endsWith('/settings'))[1].privacy.relationships); if (!pv) throw new Error('privacy');
    await p.screenshot({path: SHOTS + '/11-settings.png', fullPage: true});
  });
  await step('update intelligence runs, then is idempotent', async () => {
    await p.click('.update-btn'); await p.click('[data-act="update-run"]');
    await p.waitForSelector('text=Update report', {timeout: 8000});
    await p.screenshot({path: SHOTS + '/12-update.png', fullPage: true});
    const before = await p.evaluate(() => window.__store.size);
    await p.click('[data-act="update-run"]'); await p.waitForSelector('text=Nothing meaningful has changed', {timeout: 4000});
    const after = await p.evaluate(() => window.__store.size); if (after !== before) throw new Error(`records changed ${before}->${after}`);
    await p.click('[data-act="update-run"][data-v="force"]'); await p.waitForSelector('text=Update report', {timeout: 8000}); await p.waitForTimeout(300);
    const cards = await p.evaluate(() => [...window.__store.keys()].filter(k => k.includes('/os/cards/')).length);
    const after2 = await p.evaluate(() => window.__store.size);
    if (after2 - after > 2) throw new Error('forced rerun created duplicates: ' + (after2 - after));
    await p.click('[data-act="sheet-close"]');
  });
  await step('coach replies', async () => {
    await p.click('[data-act="sheet"][data-id="coach"]'); await p.fill('#coach-in', 'What am I neglecting?'); await p.click('[data-act="coach-send"]');
    await p.waitForSelector('.msg.ai >> text=Score the wheel', {timeout: 4000}); await p.click('[data-act="sheet-close"]');
  });
  await step('prompt sizes and model routing', async () => {
    const pr = await p.evaluate(() => window.__prompts);
    const big = Math.max(...pr.map(x => x.len)); if (big > 200000) throw new Error('prompt too big ' + big);
    const deep = pr.filter(x => x.model === 'claude-opus-5-5').length; if (!deep) throw new Error('opus never requested');
    results.push(['INFO', `prompts ${pr.length}, largest ${big} chars, deep(opus) ${deep}, routine ${pr.filter(x => !x.model).length}`]);
  });
  await step('desktop no horizontal overflow', async () => { const o = await overflow(p); if (o > 1) throw new Error('overflow ' + o); });
  await p.click('[data-act="go"][data-id="today"] >> nth=0'); await p.waitForTimeout(200);
  await p.screenshot({path: SHOTS + '/13-today-after.png', fullPage: true});

  // phone, dark
  const m = await ctx(browser, {viewport: {width: 390, height: 844}, colorScheme: 'dark', deviceScaleFactor: 2, isMobile: true, hasTouch: true});
  await m.goto(URL); await m.waitForSelector('text=Prepare my briefing', {timeout: 8000}); await m.waitForTimeout(300);
  await m.screenshot({path: SHOTS + '/20-phone-today.png'});
  await step('phone no overflow (today)', async () => { const o = await overflow(m); if (o > 1) throw new Error('overflow ' + o); });
  for (const v of ['wheel', 'learn', 'library', 'lab']) {
    await m.evaluate(v => { location.hash = v; }, v); await m.click(`.tabbar [data-id="${v}"], .tabbar [data-id="more"]`).catch(() => {});
    if (['library'].includes(v)) { await m.click(`.sheet [data-act="go"][data-id="${v}"]`).catch(() => {}); }
    await m.waitForTimeout(300);
    await m.screenshot({path: SHOTS + `/21-phone-${v}.png`, fullPage: true});
    await step('phone no overflow (' + v + ')', async () => { const o = await overflow(m); if (o > 1) throw new Error('overflow ' + o); });
  }
  // no runtime at all
  const n = await ctx(browser, {viewport: {width: 1200, height: 800}}, false);
  await n.goto(URL); await n.waitForTimeout(500);
  await step('no-runtime view explains itself', async () => { const t = await n.textContent('#view'); if (!t.includes('Open this page in Claude')) throw new Error(t.slice(0, 80)); });
  // empty db → onboarding
  const e = await ctx(browser, {viewport: {width: 1200, height: 800}}, true, false);
  await e.goto(URL); await e.waitForSelector('text=Start LIFE OS', {timeout: 6000});
  await step('onboarding creates profile', async () => { await e.fill('#ob-role', 'Pharmacist'); await e.click('[data-act="ob-pri"][data-id="career"]'); await e.click('[data-act="ob-start"]'); await e.waitForSelector('text=Prepare my briefing', {timeout: 4000}); });
  await e.screenshot({path: SHOTS + '/30-onboarded.png'});
  await browser.close();
  console.log(results.map(r => r.join(' | ')).join('\n'));
  console.log('ERRORS:', errors.length ? '\n' + [...new Set(errors)].join('\n') : 'none');
})();
