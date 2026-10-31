const { chromium } = require('playwright'); const fs = require('fs');
const SP = "/tmp/claude-0/-home-user-quant-lab/9205d36d-68a1-5401-8852-b575f8097dc2/scratchpad";
const ML = fs.readFileSync(`${SP}/r27/today27.json`, "utf8");
const MOCK = `window.__ML=${ML};window.claude={use:async k=>k==='db'?{collection:n=>({onSnapshot:(cb)=>{setTimeout(()=>cb({docs:n==='ml'?[{id:'latest',data:()=>window.__ML}]:[]}),300);return()=>{}},doc:()=>({get:async()=>({exists:false}),set:async()=>{}}),get:async()=>({docs:[]})})}:null};`;
(async () => {
  const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 1400, height: 2400 } }); const errs = [];
  pg.on("pageerror", e => errs.push(String(e))); await pg.addInitScript(MOCK);
  await pg.goto("http://127.0.0.1:8765/index.html"); await pg.waitForTimeout(5000);
  await pg.click("#tabs button[data-t=scan]"); await pg.waitForTimeout(1000);
  console.log("u30 hidden:", await pg.evaluate("document.getElementById('u30-box').hidden"), "| zsa hidden:", await pg.evaluate("document.getElementById('zsa-box').hidden"), "| zus hidden:", await pg.evaluate("document.getElementById('zus-box').hidden"));
  console.log("NOTE:", (await pg.innerText("#u30-note")).slice(0, 260));
  const rows = await pg.evaluate("[...document.querySelectorAll('#u30-t tr')].map(r=>[...r.cells].map(c=>c.innerText).join(' | '))"); console.log(rows.length - 1, "rows");
  for (const r of rows.slice(0, 4).concat(rows.slice(-2))) console.log("  ", r);
  await pg.selectOption("#u30-h", "10"); await pg.waitForTimeout(300);
  console.log("10-session F row:", await pg.evaluate("[...document.querySelectorAll('#u30-t tr')][1].innerText.replace(/\\t/g,' | ')"));
  const el = await pg.$("#u30-box"); await el.screenshot({ path: `${SP}/v23/u30.png` });
  await pg.setViewportSize({ width: 390, height: 900 }); await pg.waitForTimeout(400); console.log("phone hscroll:", await pg.evaluate("document.documentElement.scrollWidth>innerWidth"));
  console.log("errors:", errs.slice(0, 5)); await b.close();
})();
