// v33: the plan text on a daily Z-touch day carries the Industry Z sentence.
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1400, height: 1000 } }); const errs = [];
  p.on('pageerror', e => errs.push(String(e).slice(0, 300)));
  await p.addInitScript(() => {
    const CUT = +(new URLSearchParams(location.search).get('cut') || 99999999), J = (u) => fetch(u).then(r => r.json()), DATA = Promise.all([J('test_ml.json'), J('test_sec.json'), J('test_bars.json').then(B => { for (const d of Object.values(B)) if (d.rows) d.rows = d.rows.filter(r => +r[0] <= CUT); return B })]);
    const snap = (docs) => ({ docs: docs.map(([id, d]) => ({ id, data: () => d })) });
    const col = (name) => { const q = { onSnapshot: (cb) => { DATA.then(([ml, sec, bars]) => setTimeout(() => cb(snap(name === 'ml' ? [['latest', ml], ['sectors', sec]] : name === 'bars' ? Object.entries(bars) : [])), 300)); return () => {} }, orderBy: () => q, limit: () => q, where: () => q }; return q };
    window.claude = { use: async (c) => c === 'db' ? { collection: col } : null };
  });
  await p.goto('http://127.0.0.1:8769/index.html?cut=20261103'); await p.waitForTimeout(7000);
  const cases = [['4004', '2026-11-03'], ['3050', '2026-11-03']];
  for (const [c] of cases) { await p.click('#tabs button[data-t=data]'); await p.waitForTimeout(400); await p.fill('#lib-q', c); await p.dispatchEvent('#lib-q', 'input'); await p.waitForTimeout(600);
    const cb = await p.$(`#lib-t input[data-lib="${c}"]`); if (cb) { await cb.check(); await p.waitForTimeout(2500) } }
  await p.waitForFunction(() => { const m = document.getElementById('runmsg'), r = document.getElementById('run'); return m && /^Done/.test(m.textContent) && r && !r.disabled }, null, { timeout: 240000 }).catch(() => {});
  await p.click('#tabs button[data-t=chart]'); await p.waitForTimeout(800);
  for (const [c, day] of cases) {
    await p.selectOption('#sym', c); await p.waitForTimeout(3500);
    const max = +(await p.$eval('#scrub', e => e.max)); let hit = null;
    for (let v = max; v >= Math.max(0, max - 40); v--) { await p.$eval('#scrub', (e, v) => { e.value = v; e.dispatchEvent(new Event('input', { bubbles: true })) }, v); const t = await p.innerText('#scrubd'); if (t.startsWith(day)) { hit = v; break } }
    await p.waitForTimeout(800);
    const txt = (await p.evaluate(() => document.body.innerText)).replace(/\n/g, ' ');
    const k = txt.indexOf('Stretch Z reached an extreme'), j = txt.indexOf('Industry Z ', k);
    const lg = (await p.innerText('#legend')).replace(/\n/g, ' '); const iz = (lg.match(/ind Z\s*([−\-]?\d+\.\d+)/) || [])[1];
    console.log(`${c} at ${day} (scrub ${hit}): legend ind Z ${iz} | plan: ${k >= 0 ? txt.slice(k, k + 90) + ' … ' + (j >= 0 ? txt.slice(j, j + 260) : '(no Industry Z sentence)') : '(no Z-extreme plan text found)'}`);
    if (c === '4004') await (await p.$('#lwc-wrap')).screenshot({ path: path.join(__dirname, 'v33_touch.png') });
  }
  console.log('page errors:', errs); await b.close();
})();
