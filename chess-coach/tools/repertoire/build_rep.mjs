// The user's repertoire (chapter 8): Italian Game with White, 1...e5 against 1.e4, the QGD against 1.d4, built from the
// masters tree (KingBase, positions with 75+ games) and checked with Stockfish 17.1. At each of "my" positions the chosen
// move is the first move of a preference list that masters play (5%+ of games) and Stockfish puts within 35 cp of its best;
// otherwise the most-played master move within 35 cp; otherwise Stockfish's best. Opponent replies with 8%+ of master games
// are followed (at most 4), up to my 8th move.  node tools/repertoire/build_rep.mjs  ->  data/curriculum/ch08/repertoire.json
import fs from 'fs';
import { createRequire } from 'module';
import { Pool } from '../sfpool.mjs';
const require = createRequire(import.meta.url);
const { Chess } = require('../../chess.js'); const Masters = require('../../js/masters.js');
const pool = new Pool(4); const START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const PREF = {
  w: ['e4', 'Nf3', 'Bc4', 'c3', 'd3', 'O-O', 'Re1', 'Bb3', 'a4', 'h3', 'Nbd2', 'Nf1', 'Ng3', 'd4'],
  e5: ['e5', 'Nc6', 'Bc5', 'Nf6', 'd6', 'a6', 'O-O', 'Be7', 'h6', 'Ba7', 'Re8', 'Be6'],
  d5: ['d5', 'e6', 'Nf6', 'Be7', 'O-O', 'h6', 'b6', 'Nbd7', 'c6', 'dxc4'],
};
const rep = {}; let sf = 0;
async function choose(fen, prefs, ply) {
  const ms = await Masters.lookup(fen); const g = new Chess(fen); const stm = g.turn() === 'w' ? 1 : -1;
  const a = await pool.analyse(fen, { depth: 14, multipv: 1 }); sf++;
  const best = a.lines[0]; const evalOf = async (san) => { const m = new Chess(fen).move(san); if (!m) return null; const u = m.from + m.to + (m.promotion || ''); if (u === a.best) return best.cpWhite; const r = await pool.analyse(fen, { depth: 14, searchmoves: [u] }); sf++; return r.lines[0] ? r.lines[0].cpWhite : null; };
  const cands = ms ? ms.moves.filter((x) => x.share >= 0.05) : [];
  const ordered = [...prefs.map((p) => cands.find((c) => c.san === p)).filter(Boolean), ...cands.slice().sort((x, y) => y.n - x.n)];
  for (const c of ordered) { const e = await evalOf(c.san); if (e != null && stm * (best.cpWhite - e) <= 35) return { m: c.san, n: c.n, share: +c.share.toFixed(3), score: +c.scoreStm.toFixed(3), cp: stm * e, alt: cands.filter((x) => x.san !== c.san).slice(0, 3).map((x) => [x.san, +x.share.toFixed(2)]), total: ms.total }; }
  const san = new Chess(fen).move({ from: a.best.slice(0, 2), to: a.best.slice(2, 4), promotion: a.best[4] || 'q' }).san;
  return { m: san, n: 0, share: 0, score: null, cp: stm * best.cpWhite, alt: cands.slice(0, 3).map((x) => [x.san, +x.share.toFixed(2)]), total: ms ? ms.total : 0, sf: true };
}
const W_OTHER = ['e4', 'Nf3', 'd4', 'Nc3', 'Bc4', 'Be2', 'O-O'];
let GROUP = 'w';
async function walk(fen, me, prefs, myMoves, path = []) {
  const key = Masters.keyOf(fen); const g = new Chess(fen);
  if (g.game_over()) return;
  if (g.turn() === me) {
    if (rep[key] || myMoves >= 8) return;
    // with White, the Italian move list only after 1.e4 e5; against other defences the main classical moves
    const pf = me === 'w' && path.length >= 2 && path[1] !== 'e5' ? W_OTHER : prefs;
    const c = await choose(fen, pf, myMoves); c.g = GROUP; c.p = path.join(' '); rep[key] = c;
    const h = new Chess(fen); h.move(c.m); await walk(h.fen(), me, prefs, myMoves + 1, [...path, c.m]);
  } else {
    const ms = await Masters.lookup(fen); if (!ms) return;
    for (const x of ms.moves.filter((y) => y.share >= 0.08).slice(0, 4)) { const h = new Chess(fen); if (!h.move(x.san)) continue; await walk(h.fen(), me, prefs, myMoves, [...path, x.san]); }
  }
}
// White: the Italian (1.e4 2.Nf3 3.Bc4 ...)
GROUP = 'w'; await walk(START, 'w', PREF.w, 0);
// Black: 1...e5 against 1.e4, the QGD against 1.d4, and the main other first moves
for (const [first, prefs] of [['e4', PREF.e5], ['d4', PREF.d5], ['c4', ['e5', 'Nf6', 'e6', 'd5', ...PREF.d5]], ['Nf3', ['d5', 'Nf6', ...PREF.d5]]]) {
  GROUP = first === 'e4' ? 'e5' : first === 'd4' ? 'qgd' : 'b-other'; const g = new Chess(); g.move(first); await walk(g.fen(), 'b', prefs, 0, [first]);
}
const out = { note: 'Repertoire built from KingBase master statistics and checked with Stockfish 17.1 (depth 14). Key = FEN fields 1-4 (Masters.keyOf). m = your move; g = group (w, e5, qgd, b-other); p = the moves that first reached it; n/share/score = master games, share of the position, score for the side to move; alt = other master moves; sf = no master move within 35 cp, Stockfish chose.', positions: rep };
fs.mkdirSync('data/curriculum/ch08', { recursive: true }); fs.writeFileSync('data/curriculum/ch08/repertoire.json', JSON.stringify(out));
const w = Object.keys(rep).filter((k) => k.split(' ')[1] === 'w').length;
console.log('positions', Object.keys(rep).length, 'white', w, 'black', Object.keys(rep).length - w, 'stockfish calls', sf, 'sf fallbacks', Object.values(rep).filter((x) => x.sf).length, 'bytes', fs.statSync('data/curriculum/ch08/repertoire.json').size);
pool.close();
