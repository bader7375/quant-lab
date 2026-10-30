// Chapter 7 pool, step 2: keep master positions with a recognised pawn structure (js/techniques.js structure()), at most
// 700 per structure, where Stockfish 17.1 (depth 13) puts the master's move within 40 cp of best in a balanced position.
// Stores s (structure), sp (the structure plan the master's move follows, if any), b (best), t (tags of the best move).
//   node tools/positions/tag_structures.mjs raw.json data/positions/ch07-structures.json
import fs from 'fs';
import { createRequire } from 'module';
import { Pool } from '../sfpool.mjs';
const require = createRequire(import.meta.url);
const Tech = require('../../js/techniques.js');
const [, , rawFile, outFile] = process.argv; const raw = JSON.parse(fs.readFileSync(rawFile, 'utf8'));
const by = {}; for (const it of raw) { const s = Tech.structure(it.fen); if (!s) continue; it.s = s; (by[s.id] = by[s.id] || []).push(it); }
console.log('found', Object.fromEntries(Object.entries(by).map(([k, v]) => [k, v.length])));
let seed = 7; const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
const cand = []; for (const v of Object.values(by)) { v.sort(() => rnd() - 0.5); cand.push(...v.slice(0, 900)); }
const pool = new Pool(4); const keep = [];
await Promise.all(cand.map(async (it) => {
  const a = await pool.analyse(it.fen, { depth: 13 }); if (!a.best) return;
  const sgn = it.fen.split(' ')[1] === 'w' ? 1 : -1;
  const m = it.mv === a.best ? a.lines[0] : (await pool.analyse(it.fen, { depth: 13, searchmoves: [it.mv] })).lines[0]; if (!m) return;
  if (sgn * (a.lines[0].cpWhite - m.cpWhite) > 40 || Math.abs(a.lines[0].cpWhite) > 300) return;
  it.b = a.best; it.t = Tech.tagsOf(it.fen, a.best); it.sp = Tech.structPlan(it.fen, it.mv, it.s); keep.push(it);
}));
const per = {}; const out = []; for (const it of keep) { per[it.s.id] = (per[it.s.id] || 0) + 1; if (per[it.s.id] <= 700) out.push(it); }
fs.writeFileSync(outFile, JSON.stringify({ id: 'ch07-structures', source: 'KingBase 2017 master games (players 2300+), moves 12-30', n: out.length, items: out }).replace(/},{"fen"/g, '},\n{"fen"'));
const sp = {}; for (const it of out) if (it.sp) sp[it.sp] = (sp[it.sp] || 0) + 1;
console.log('kept', out.length, JSON.stringify(per), 'master follows the plan:', JSON.stringify(sp));
pool.close();
