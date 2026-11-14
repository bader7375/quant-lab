// Browser test of v33 through the real UI: mock database (ml/latest, ml/sectors, all stored bars), the built-in library, then the chart.
const { chromium } = require('playwright'); const path = require('path'); const page = process.argv[2] || 'index.html';
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1400, height: 1000 } }); const errs = [];
  p.on('pageerror', e => errs.push(String(e).slice(0, 300))); p.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text().slice(0, 200)); });
  await p.addInitScript(() => {
    const J = (u) => fetch(u).then(r => r.json()), DATA = Promise.all([J('test_ml.json'), J('test_sec.json'), J('test_bars.json')]);
    const snap = (docs) => ({ docs: docs.map(([id, d]) => ({ id, data: () => d })) });
    const col = (name) => { const q = { onSnapshot: (cb) => { DATA.then(([ml, sec, bars]) => setTimeout(() => cb(snap(name === 'ml' ? [['latest', ml], ['sectors', sec]] : name === 'bars' ? Object.entries(bars) : [])), 300)); return () => {} },
      orderBy: () => q, limit: () => q, where: () => q }; return q };
    window.claude = { use: async (c) => c === 'db' ? { collection: col } : null };
  });
  await p.goto('http://127.0.0.1:8769/' + page); await p.waitForTimeout(7000);
  const done = () => p.waitForFunction(() => { const m = document.getElementById('runmsg'), r = document.getElementById('run'); return m && /^Done/.test(m.textContent) && r && !r.disabled }, null, { timeout: 240000 }).catch(() => console.log('(engine wait timed out)'));
  await p.click('#tabs button[data-t=data]'); await p.waitForTimeout(500);
  for (const c of ['1120', '2222', '4190', '3030']) {
    await p.click('#tabs button[data-t=data]'); await p.waitForTimeout(400); await p.fill('#lib-q', c); await p.dispatchEvent('#lib-q', 'input'); await p.waitForTimeout(600);
    const cb = await p.$(`#lib-t input[data-lib="${c}"]`); if (!cb) { console.log('no library row for', c); continue }
    await cb.check(); await p.waitForTimeout(2500); console.log(c, '->', (await p.innerText('#lib-msg')).slice(0, 140).replace(/\n/g, ' '));
  }
  await done(); await p.click('#tabs button[data-t=chart]'); await p.waitForTimeout(1000);
  for (const s of ['1120', '2222', '4190', '3030']) {
    await p.selectOption('#sym', s).catch(e => console.log('select failed', s)); await p.waitForTimeout(4000);
    const lg = (await p.innerText('#legend')).replace(/\n/g, ' ');
    const iz = (lg.match(/ind Z\s*([−\-]?\d+\.\d+)/) || [])[1], dt = (lg.match(/\d{4}-\d\d-\d\d/) || [])[0], zs = (lg.match(/Stretch Z\s*([−\-]?\d+\.\d+)/) || [])[1];
    const title = await p.evaluate(() => { const el = [...document.querySelectorAll('#legend span[title]')].find(e => /industry Z/.test(e.title)); return el ? el.title : null });
    console.log(`${s}: legend date ${dt}, ind Z ${iz ?? '(none)'}, stretch Z ${zs} | ${title}`);
  }
  await p.selectOption('#sym', '1120'); await p.waitForTimeout(3000);
  await (await p.$('#lwc-wrap')).screenshot({ path: path.join(__dirname, 'v33_chart.png') });
  const pn = await p.evaluate(() => [...document.querySelectorAll('#pn label')].map(l => l.innerText.trim()).join(' | ')); console.log('panel switches:', pn);
  console.log('research section present:', await p.evaluate(() => document.body.innerHTML.includes('Industry Z (round 72')));
  await p.setViewportSize({ width: 390, height: 900 }); await p.waitForTimeout(1500);
  console.log('phone horizontal scroll:', await p.evaluate(() => document.documentElement.scrollWidth > innerWidth));
  await (await p.$('#lwc-wrap')).screenshot({ path: path.join(__dirname, 'v33_phone.png') });
  console.log('page errors:', errs.slice(0, 8)); await b.close();
})();
