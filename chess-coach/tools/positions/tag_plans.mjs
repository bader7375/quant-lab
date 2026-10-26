// Chapter 6 pool: keep master positions whose played move is a plan move (open file, worst piece, pawn break, outpost)
// and is sound: Stockfish 17.1 (depth 13) puts it within 40 cp of its best move. Stores b (best), t (tags of the best move
// plus the master's plan tags), mt (the master's tags).   node tools/positions/tag_plans.mjs [depth=13]
import fs from 'fs';
import { createRequire } from 'module';
import { Pool } from '../sfpool.mjs';
const require = createRequire(import.meta.url);
const Tech = require('../../js/techniques.js');
const PLAN = ['openfile', 'worst', 'break', 'outpost'];
const depth = +(process.argv[2] || 13); const pool = new Pool(4);
const file = 'data/positions/ch06-plans.json'; const P = JSON.parse(fs.readFileSync(file, 'utf8'));
const cand = P.items.filter((it) => { it.mt = Tech.tagsOf(it.fen, it.mv).filter((t) => PLAN.includes(t)); return it.mt.length; });
console.log('master plan moves', cand.length, 'of', P.items.length);
const keep = []; const count = {};
await Promise.all(cand.map(async (it) => {
  const a = await pool.analyse(it.fen, { depth, multipv: 1 }); if (!a.best) return;
  const m = it.mv === a.best ? a.lines[0] : (await pool.analyse(it.fen, { depth, searchmoves: [it.mv] })).lines[0]; if (!m) return;
  const loss = a.lines[0].cpWhite * (it.fen.split(' ')[1] === 'w' ? 1 : -1) - m.cpWhite * (it.fen.split(' ')[1] === 'w' ? 1 : -1);
  if (loss > 40 || Math.abs(a.lines[0].cpWhite) > 300) return; // a sound plan move, in a position still in the balance
  it.b = a.best; it.t = [...new Set([...Tech.tagsOf(it.fen, a.best), ...it.mt])]; it.loss = loss; keep.push(it);
  for (const x of it.mt) count[x] = (count[x] || 0) + 1;
}));
P.items = keep; P.n = keep.length;
fs.writeFileSync(file, JSON.stringify(P).replace(/},{"fen"/g, '},\n{"fen"'));
console.log('kept', keep.length, JSON.stringify(count));
pool.close();
