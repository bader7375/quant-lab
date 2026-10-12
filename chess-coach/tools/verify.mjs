// Verify curated positions: legal FEN + Stockfish multipv-3 at fixed depth.
// usage: node tools/verify.mjs positions.json [depth]
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
const require = createRequire(import.meta.url);
const dir = path.dirname(new URL(import.meta.url).pathname);
const { Chess } = require(path.join(dir, '..', 'chess.js'));
const STOCKFISH = require(path.join(dir, 'legacy', 'stockfish10.js'));
const file = process.argv[2], depth = +(process.argv[3] || 20);
const items = JSON.parse(fs.readFileSync(file, 'utf8'));
const sf = STOCKFISH();
let resolve, lines = [];
sf.onmessage = (l) => { lines.push(l); if (l.startsWith('bestmove')) resolve(); };
const send = (c) => sf.postMessage(c, true);
send('uci'); send('setoption name MultiPV value 3');
for (const it of items) {
  const c = new Chess();
  if (!c.load(it.fen)) { console.log(`ILLEGAL ${it.id}: ${c.validate_fen(it.fen).error}`); continue; }
  lines = [];
  await new Promise((r) => { resolve = r; send('ucinewgame'); send('position fen ' + it.fen); send('go depth ' + depth); });
  const best = {};
  for (const l of lines) {
    const m = l.match(/depth (\d+) .*multipv (\d) score (cp|mate) (-?\d+).* pv (.*?)(?: bmc.*)?$/);
    if (m && +m[1] === depth) best[m[2]] = { score: m[3] + ' ' + m[4], pv: m[5].split(' ').slice(0, 6) };
  }
  const out = Object.entries(best).map(([k, v]) => {
    const g = new Chess(it.fen); const san = [];
    for (const u of v.pv) { const mv = g.move({ from: u.slice(0, 2), to: u.slice(2, 4), promotion: u[4] }); if (!mv) break; san.push(mv.san); }
    return `  #${k} ${v.score.padEnd(9)} ${san.join(' ')}`;
  });
  console.log(`${it.id} (${c.turn()} to move) expect=${it.expect || '-'}\n${out.join('\n')}`);
}
process.exit(0);
