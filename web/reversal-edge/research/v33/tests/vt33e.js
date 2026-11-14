// v33 regression: US stock and TASI (no industry), panel switched off, then on again; no page errors.
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1400, height: 1000 } }); const errs = [];
  p.on('pageerror', e => errs.push(String(e).slice(0, 300)));
  await p.addInitScript(() => {
    const J = (u) => fetch(u).then(r => r.json()), DATA = Promise.all([J('test_ml.json'), J('test_sec.json'), J('test_bars.json')]);
    const snap = (docs) => ({ docs: docs.map(([id, d]) => ({ id, data: () => d })) });
    const col = (name) => { const q = { onSnapshot: (cb) => { DATA.then(([ml, sec, bars]) => setTimeout(() => cb(snap(name === 'ml' ? [['latest', ml], ['sectors', sec]] : name === 'bars' ? Object.entries(bars) : [])), 300)); return () => {} }, orderBy: () => q, limit: () => q, where: () => q }; return q };
    window.claude = { use: async (c) => c === 'db' ? { collection: col } : null };
  });
  await p.goto('http://127.0.0.1:8769/index.html'); await p.waitForTimeout(7000);
  for (const c of ['AAPL', 'TASI', '1120']) { await p.click('#tabs button[data-t=data]'); await p.waitForTimeout(400); await p.fill('#lib-q', c); await p.dispatchEvent('#lib-q', 'input'); await p.waitForTimeout(600);
    const cb = await p.$(`#lib-t input[data-lib="${c}"]`); if (cb) { await cb.check(); await p.waitForTimeout(2500) } else console.log('no row', c) }
  await p.waitForFunction(() => { const m = document.getElementById('runmsg'), r = document.getElementById('run'); return m && /^Done/.test(m.textContent) && r && !r.disabled }, null, { timeout: 240000 }).catch(() => {});
  await p.click('#tabs button[data-t=chart]'); await p.waitForTimeout(800);
  const opts = await p.$$eval('#sym option', o => o.map(x => x.value)); console.log('symbols:', opts.join(', '));
  const H = async () => +(await p.$eval('#lwc-wrap', e => parseInt(e.style.height)));
  for (const s of opts) { await p.selectOption('#sym', s); await p.waitForTimeout(3000); const lg = (await p.innerText('#legend')).replace(/\n/g, ' '); console.log(s, '| chart height', await H(), '| ind Z in legend:', /ind Z/.test(lg)) }
  await p.selectOption('#sym', '1120'); await p.waitForTimeout(2500); const h1 = await H();
  await p.uncheck('#pn input[data-pn="iz"]'); await p.waitForTimeout(2500); const h0 = await H(); const lg0 = /ind Z/.test(await p.innerText('#legend'));
  await p.check('#pn input[data-pn="iz"]'); await p.waitForTimeout(2500); const h2 = await H(); const lg2 = /ind Z/.test(await p.innerText('#legend'));
  console.log(`1120 panel on ${h1}px -> off ${h0}px (legend ind Z ${lg0}) -> on ${h2}px (legend ind Z ${lg2})`);
  console.log('page errors:', errs); await b.close();
})();
