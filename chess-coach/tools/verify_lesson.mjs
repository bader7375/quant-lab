// Verifies a Learn lesson (data/curriculum/chNN/learn.json) with Stockfish 17.1 before it ships.
//   node tools/verify_lesson.mjs data/curriculum/ch01/learn.json [depth=20]
// For each task: every accepted move must be within MAX_LOSS centipawns of the best move (mover's view, searchmoves) and
// not losing; every "why" move is printed with its score and Stockfish's reply so the text can be checked; and the
// concrete claims in each slide's "claims" ({seq, kind}: a move sequence that must be legal, give check or mate) must hold. Exit 1 on failure.
import fs from 'fs';
import { createRequire } from 'module';
import { Pool } from './sfpool.mjs';
const require = createRequire(import.meta.url);
const { Chess } = require('../chess.js');
const file = process.argv[2]; const depth = +(process.argv[3] || 20); const MAX_LOSS = 60;
const L = JSON.parse(fs.readFileSync(file, 'utf8'));
const pool = new Pool(2); let fails = 0;
const fail = (m) => { fails++; console.log('  FAIL ' + m); };
const uciOf = (fen, san) => { const g = new Chess(fen); const m = g.move(san); return m ? m.from + m.to + (m.promotion || '') : null; };
for (const [i, s] of L.slides.entries()) {
  const g = new Chess(s.fen || undefined); for (const mv of s.moves) if (!g.move(mv)) fail(`slide ${i}: illegal setup move ${mv}`);
  const fen = g.fen(); console.log(`\n[${i}] ${s.title}  (${fen})`);
  for (const { seq, kind } of s.claims || []) {
    const h = new Chess(fen); let ok = true, last = null;
    for (const mv of seq) { last = h.move(mv); if (!last) { ok = false; break; } }
    const holds = ok && (kind === 'legal' || (kind === 'check' && h.in_check()) || (kind === 'mate' && h.in_checkmate()) || (kind === 'stalemate' && h.in_stalemate()));
    console.log(`  claim ${seq.join(' ')} -> ${kind}: ${holds ? 'ok' : 'NO'}`); if (!holds) fail(`slide ${i}: claim ${seq.join(' ')} ${kind}`);
  }
  if (!s.task) continue;
  const best = await pool.analyse(fen, { depth, multipv: 4 });
  const stm = fen.split(' ')[1] === 'w' ? 1 : -1; const b = best.lines[0];
  console.log(`  best: ${b.pv.slice(0, 1).map((u) => new Chess(fen).move({ from: u.slice(0, 2), to: u.slice(2, 4), promotion: u[4] }).san)} ${stm * b.cpWhite}cp; top: ${best.lines.map((l) => new Chess(fen).move({ from: l.pv[0].slice(0, 2), to: l.pv[0].slice(2, 4), promotion: l.pv[0][4] }).san + ' ' + stm * l.cpWhite).join(', ')}`);
  for (const san of [...s.task.accept, ...Object.keys(s.task.why || {})]) {
    const u = uciOf(fen, san); if (!u) { fail(`slide ${i}: ${san} illegal`); continue; }
    const a = await pool.analyse(fen, { depth, searchmoves: [u] }); const cp = stm * a.lines[0].cpWhite;
    const reply = a.lines[0].pv.slice(1, 4); const h = new Chess(fen); h.move(san); const rs = []; for (const r of reply) { const m = h.move({ from: r.slice(0, 2), to: r.slice(2, 4), promotion: r[4] }); if (!m) break; rs.push(m.san); }
    const loss = stm * b.cpWhite - cp; const acc = s.task.accept.includes(san);
    console.log(`  ${acc ? 'ACCEPT' : 'why   '} ${san.padEnd(5)} ${String(cp).padStart(6)}cp  loss ${String(loss).padStart(5)}  reply ${rs.join(' ')}`);
    // with a forced mate on the board, an accepted move must keep it and lose at most one move of the mate distance
    const mateLoss = b.mate > 0 ? (new Chess(fen).move(san).san.includes('#') ? 0 : a.lines[0].mate > 0 ? a.lines[0].mate - b.mate : 99) : null;
    if (mateLoss != null) console.log(`         mate: best in ${b.mate}, this move in ${new Chess(fen).move(san).san.includes('#') ? 1 : a.lines[0].mate}`);
    if (acc && (mateLoss != null ? mateLoss > 1 : loss > MAX_LOSS || cp < -150)) fail(`slide ${i}: accepted ${san} loses ${mateLoss != null ? mateLoss + ' mate moves' : loss + 'cp'} (score ${cp})`);
  }
}
pool.close();
console.log(`\n${fails ? 'FAIL' : 'PASS'} (${fails} failed)`); process.exit(fails ? 1 : 0);
