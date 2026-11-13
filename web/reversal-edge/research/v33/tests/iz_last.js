const fs = require('fs'); const H = fs.readFileSync('../index.html', 'utf8');
const grab = (start) => { const i = H.indexOf(start); let j = H.indexOf('{', i), dep = 0; for (let k = j; k < H.length; k++) { if (H[k] === '{') dep++; else if (H[k] === '}') { dep--; if (!dep) return H.slice(i, k + 1); } } };
const blk = H.slice(H.indexOf('// ---------- v33 (round 72, H3)'), H.indexOf('function msZone(v){'));
const mk = () => new Function('UPD_ALIAS','LIBMETA','chart','UI','st','ARR','esc','fmt','msOn','refreshOverlays', 'let UPD={},SECT=null;const isF=Number.isFinite;' + grab('function stretchZ(c,clip=.25){') + grab('function updSeries(doc){') + blk + 'return {izPeer, indOf, setU:(u)=>{UPD=u}, setS:(s)=>{SECT=s}};')({},null,null,{pn:{}},{},null,x=>x,x=>x,()=>true,()=>{});
const sec = JSON.parse(fs.readFileSync('../db/ml/sectors.json', 'utf8')); const A = mk(), B = mk();
const db = JSON.parse(fs.readFileSync('db_docs.json', 'utf8')), yh = JSON.parse(fs.readFileSync('yahoo_docs.json', 'utf8'));
A.setU(db); A.setS(sec.data || sec); B.setU(yh); B.setS(sec.data || sec);
const g = process.argv[2] || 'Energy', t = process.argv[3] || '2026-11-12';
for (const k of Object.keys(db).filter(k => /^\d{4}$/.test(k) && A.indOf(k) === g)) { const a = A.izPeer(k), b = B.izPeer(k); const ia = a ? a.d.indexOf(t) : -1, ib = b ? b.d.indexOf(t) : -1;
  const ra = db[k].rows, rb = (yh[k] || {rows: []}).rows; const la = ra.slice(-3).map(r => r[4]), lb = rb.slice(-3).map(r => r[4]);
  console.log(k, 'DB z', ia >= 0 ? a.z[ia].toFixed(2) : '-', a && ia >= 0 && a.liq[ia] ? 'liq' : '   ', '| Yahoo z', ib >= 0 ? b.z[ib].toFixed(2) : '-', b && ib >= 0 && b.liq[ib] ? 'liq' : '   ', '| last closes DB', la.join(','), 'Yahoo', lb.join(','), '| DB fetched', db[k].fetched_at); }
