// Lines to memorise (the line trainer, js/lines.js): every leaf of the repertoire tree (data/curriculum/ch08/repertoire.json)
// as one line from the first move, with
//   w    how often you meet it: 0.5 (your colour) x the product of the opponent's master reply shares along the line
//        (Black lines also x the share of White's first move), so White and Black lines can be ordered together;
//   sh   the master share of every move of the line in its position (yours and the opponent's);
//   name the opening name at the end of the line (lichess chess-openings, CC0), fam = the part before ":";
//   cont what masters play next from the end of the line: the most played move while 50+ master games reach the position,
//        up to 4 more of your moves. Each of your moves in it is checked with Stockfish 17.1 (depth 14): it must be within
//        50 cp of Stockfish's best, otherwise the continuation stops before it. csh = master shares of those moves;
//   end  Stockfish at the end of the line (depth 16): cp from White's view and its best line (8 plies, SAN).
// node tools/repertoire/build_lines.mjs  ->  data/curriculum/ch08/lines.json
import fs from 'fs';
import { createRequire } from 'module';
import { Pool } from '../sfpool.mjs';
const require = createRequire(import.meta.url);
const { Chess } = require('../../chess.js'); const Masters = require('../../js/masters.js');
const REP = JSON.parse(fs.readFileSync('data/curriculum/ch08/repertoire.json', 'utf8')).positions;
const pool = new Pool(4); const START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const fnv = (s) => { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } return h.toString(36); };
const kids = {}; for (const v of Object.values(REP)) { const t = v.p ? v.p.split(' ') : []; if (!t.length) continue; const parent = t.slice(0, -1).join(' '); (kids[parent] = kids[parent] || []).push(v); }
const leaves = Object.values(REP).filter((v) => !(kids[(v.p ? v.p + ' ' : '') + v.m] || []).length);
const root = await Masters.lookup(START); const firstShare = Object.fromEntries(root.moves.map((m) => [m.san, m.share]));
const MAX_CONT_OWN = 4, MIN_GAMES = 50, MAX_DROP = 50;
const sanToUci = (fen, san) => { const m = new Chess(fen).move(san, { sloppy: true }); return m ? m.from + m.to + (m.promotion || '') : null; };
const out = []; let k = 0, cut = 0;
for (const l of leaves) {
  const mv = [...(l.p ? l.p.split(' ') : []), l.m]; const me = l.g === 'w' ? 'w' : 'b';
  const g = new Chess(); const sh = []; let w = 0.5 * (me === 'b' ? firstShare[mv[0]] || 0 : 1);
  for (const s of mv) { const ms = await Masters.lookup(g.fen()); const x = ms && ms.moves.find((m) => m.san === s); sh.push(x ? +x.share.toFixed(3) : 0); if (g.turn() !== me && !(me === 'b' && g.history().length === 0)) w *= x ? x.share : 0.05; g.move(s); }
  // what masters play next, your moves checked by Stockfish
  const cont = [], csh = []; let own = 0; const h = new Chess(g.fen());
  for (let i = 0; i < 2 * MAX_CONT_OWN + 1; i++) {
    const ms = await Masters.lookup(h.fen()); if (!ms || ms.total < MIN_GAMES || !ms.moves[0]) break;
    const top = ms.moves[0];
    if (h.turn() === me) {
      if (own >= MAX_CONT_OWN) break;
      const fen = h.fen(); const a = await pool.analyse(fen, { depth: 14, multipv: 1 }); const u = sanToUci(fen, top.san);
      let e = a.lines[0].cpWhite; if (u !== a.best) e = (await pool.analyse(fen, { depth: 14, searchmoves: [u] })).lines[0].cpWhite;
      const drop = (me === 'w' ? 1 : -1) * (a.lines[0].cpWhite - e); if (drop > MAX_DROP) { cut++; break; }
      own++;
    }
    cont.push(top.san); csh.push(+top.share.toFixed(3)); h.move(top.san);
  }
  const endA = await pool.analyse(g.fen(), { depth: 16, multipv: 1 });
  const pv = []; { const p = new Chess(g.fen()); for (const u of endA.lines[0].pv.slice(0, 8)) { const m = p.move({ from: u.slice(0, 2), to: u.slice(2, 4), promotion: u[4] || 'q' }); if (!m) break; pv.push(m.san); } }
  const o = await Masters.openingAlong(START, mv);
  const name = o ? o.name : ''; const fam = name.split(':')[0];
  out.push({ id: fnv(mv.join(' ')), g: l.g, mv, sh, w: +w.toFixed(5), name, eco: o ? o.eco : '', fam, cont, csh, end: { cp: endA.lines[0].cpWhite, pv } });
  if (++k % 25 === 0) console.log(k, '/', leaves.length);
}
out.sort((a, b) => b.w - a.w);
const doc = { note: 'Lines of the repertoire for the line trainer. w = 0.5 x the product of master reply shares (how often you meet the line); sh = master share of each move; cont = masters\' most played continuation (50+ games), your moves within 50 cp of Stockfish 17.1 depth 14; end = Stockfish depth 16 at the end of the line (cp White view, best line).', lines: out };
fs.writeFileSync('data/curriculum/ch08/lines.json', JSON.stringify(doc));
console.log('lines', out.length, 'continuations cut by Stockfish', cut, 'bytes', fs.statSync('data/curriculum/ch08/lines.json').size);
for (const x of out.slice(0, 12)) console.log(x.w, x.g, x.name, '|', x.mv.join(' '), '| cont', x.cont.join(' '), '| end', x.end.cp, x.end.pv.slice(0, 4).join(' '));
pool.close();
