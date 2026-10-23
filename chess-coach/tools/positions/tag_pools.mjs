// Adds Stockfish's best move (b) and its technique tags (t) to every item of the position pools, so a technique drill can
// draw positions where the best move IS that technique.   node tools/positions/tag_pools.mjs [depth=13]
import fs from 'fs';
import { createRequire } from 'module';
import { Pool } from '../sfpool.mjs';
const require = createRequire(import.meta.url);
const Tech = require('../../js/techniques.js');
const depth = +(process.argv[2] || 13); const pool = new Pool(4);
for (const id of ['ch01-opening', 'ch02-safety', 'ch02-punish', 'ch03-mates']) {
  const file = `data/positions/${id}.json`; const P = JSON.parse(fs.readFileSync(file, 'utf8')); const count = {};
  await Promise.all(P.items.map(async (it) => {
    const a = await pool.analyse(it.fen, { depth, multipv: 2 }); if (!a.best) return;
    it.b = a.best; it.t = Tech.tagsOf(it.fen, a.best);
    const gap = a.lines[1] ? Math.abs(a.lines[0].cpWhite - a.lines[1].cpWhite) : 999; if (gap >= 150) it.t.push('only'); // one clearly best move
    for (const x of it.t) count[x] = (count[x] || 0) + 1;
  }));
  fs.writeFileSync(file, JSON.stringify(P, null, 0).replace(/},{"fen"/g, '},\n{"fen"'));
  console.log(id, JSON.stringify(count));
}
pool.close();
