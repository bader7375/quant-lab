const fs = require('fs'); const H = fs.readFileSync('../index.html', 'utf8');
const grab = (start) => { const i = H.indexOf(start); let j = H.indexOf('{', i), dep = 0; for (let k = j; k < H.length; k++) { if (H[k] === '{') dep++; else if (H[k] === '}') { dep--; if (!dep) return H.slice(i, k + 1); } } };
const blk = H.slice(H.indexOf('// ---------- v33 (round 72, H3)'), H.indexOf('function msZone(v){'));
const E = new Function('UPD_ALIAS','LIBMETA','chart','UI','st','ARR','esc','fmt','msOn','refreshOverlays', 'let UPD={},SECT=null;const isF=Number.isFinite;' + grab('function stretchZ(c,clip=.25){') + grab('function updSeries(doc){') + blk + 'return {izPeer, indOf, setU:(u)=>{UPD=u}, setS:(s)=>{SECT=s}};')({},null,null,{pn:{}},{},null,x=>x,x=>x,()=>true,()=>{});
const docs = JSON.parse(fs.readFileSync('yahoo_docs.json', 'utf8')), sec = JSON.parse(fs.readFileSync('../db/ml/sectors.json', 'utf8')); E.setU(docs); E.setS(sec.data || sec);
const bad = [];
for (const k of Object.keys(docs)) { const P = E.izPeer(k); if (!P) continue; for (let i = 0; i < P.d.length; i++) if (P.liq[i] && Math.abs(P.z[i]) > 12) bad.push([k, E.indOf(k), P.d[i], +P.z[i].toFixed(1)]); }
console.log('liquid stock-days with |stretch Z| > 12:', bad.length); console.log(bad.slice(0, 12));
const k = bad.length ? bad[0][0] : null; if (k) { const r = docs[k].rows; const i = r.findIndex(x => String(x[0]) === bad[0][2].replace(/-/g, '')); console.log(k, 'rows around', r.slice(Math.max(0, i - 70), i + 2).filter((x, j, a) => j < 3 || j > a.length - 6 || x[5] === 0).slice(0, 14)); }
