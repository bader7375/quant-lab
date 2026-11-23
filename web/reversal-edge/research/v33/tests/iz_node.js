// Runs the page's own Industry Z code (extracted from v33/index.html) on test 'bars' documents and compares with the research values.
const fs = require('fs'); const H = fs.readFileSync(process.argv[2], 'utf8');
const grab = (start) => { const i = H.indexOf(start); if (i < 0) throw new Error('missing ' + start); let j = H.indexOf('{', i), dep = 0;
  for (let k = j; k < H.length; k++) { if (H[k] === '{') dep++; else if (H[k] === '}') { dep--; if (!dep) return H.slice(i, k + 1); } } };
const blk = H.slice(H.indexOf('// ---------- v33 (round 72, H3)'), H.indexOf('function msZone(v){'));
const code = ['const isF=Number.isFinite;', grab('function stretchZ(c,clip=.25){'), grab('function updSeries(doc){'), blk,
  'return {izSeries, indOf, setU:(u)=>{UPD=u}, setS:(s)=>{SECT=s}};'].join('\n');
const E = new Function('UPD_ALIAS', 'LIBMETA', 'chart', 'UI', 'st', 'ARR', 'esc', 'fmt', 'msOn', 'refreshOverlays', 'let UPD={},SECT=null;' + code)({}, null, null, {pn: {}}, {}, null, x => x, x => x, () => true, () => {});
const docs = JSON.parse(fs.readFileSync(process.argv[3], 'utf8')), sec = JSON.parse(fs.readFileSync(process.argv[4], 'utf8')), py = JSON.parse(fs.readFileSync(process.argv[5], 'utf8'));
E.setU(docs); E.setS(sec.data || sec);
const t0 = Date.now(); const res = {};
for (const s of Object.keys(py.raw)) res[s] = E.izSeries(s, py.dates);
console.log('compute time for', Object.keys(res).length, 'stocks:', Date.now() - t0, 'ms');
const cmp = (a, b) => { let n = 0, mx = 0, sa = 0, side = 0, onlyA = 0, onlyB = 0, sx = 0, sy = 0, sxx = 0, syy = 0, sxy = 0;
  for (let i = 0; i < a.length; i++) { const x = a[i], y = b[i]; const fx = Number.isFinite(x), fy = y !== null && Number.isFinite(y);
    if (fx && !fy) onlyA++; if (!fx && fy) onlyB++; if (!(fx && fy)) continue; n++; const d = Math.abs(x - y); mx = Math.max(mx, d); sa += d;
    if ((x <= -1) === (y <= -1) && (x > -0.5) === (y > -0.5)) side++; sx += x; sy += y; sxx += x * x; syy += y * y; sxy += x * y; }
  const r = (n * sxy - sx * sy) / Math.sqrt((n * sxx - sx * sx) * (n * syy - sy * sy));
  return `n ${n}, corr ${r.toFixed(4)}, mean |diff| ${(sa / n).toFixed(3)}, max ${mx.toFixed(2)}, same zone ${(100 * side / n).toFixed(1)}%, page-only ${onlyA}, research-only ${onlyB}`; };
for (const s of Object.keys(res)) { const R = res[s]; if (!R) { console.log(s, 'no result'); continue; }
  console.log(`${s} ${R.g.padEnd(24)} peers ${String(R.peers).padStart(2)} | vs research (raw value): ${cmp(R.v, py.raw[s])}\n${' '.repeat(36)}| vs adjusted value:      ${cmp(R.v, py.adj[s])}`); }
const last = py.dates.length - 1; console.log('last date', py.dates[last], Object.keys(res).map(s => `${s} page ${res[s] && Number.isFinite(res[s].v[last]) ? res[s].v[last].toFixed(2) : '–'} / research ${py.raw[s][last] == null ? '–' : py.raw[s][last].toFixed(2)}`).join(' · '));
