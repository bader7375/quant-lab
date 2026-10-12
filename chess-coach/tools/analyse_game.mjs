// Per-move analysis of a demo game, the grounding data for narration.
// usage: node tools/analyse_game.mjs in.json out.json [depth=20]
// in.json: {id, sans:[...], start?, narrated:'w'|'b', ...meta}
// For each ply: the position before the move, Stockfish 17.1 multipv 3 (+WDL), what the opponent threatened
// (null-move search), computed facts, and the evaluation after the move.
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import { Pool } from './sfpool.mjs';
const require = createRequire(import.meta.url);
const root = path.join(path.dirname(new URL(import.meta.url).pathname), '..');
const { Chess } = require(path.join(root, 'chess.js'));
const Facts = require(path.join(root, 'js/facts.js'));
const [, , inFile, outFile, depthArg] = process.argv;
const DEPTH = +(depthArg || 20);
const G = JSON.parse(fs.readFileSync(inFile, 'utf8'));
const pool = new Pool(4);
const START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

function sanLine(fen, pv, max = 10) { const g = new Chess(fen); const out = []; for (const u of pv.slice(0, max)) { const m = g.move({ from: u.slice(0, 2), to: u.slice(2, 4), promotion: u[4] }); if (!m) break; out.push(m.san); } return out; }
function nullFen(fen) { const p = fen.split(' '); p[1] = p[1] === 'w' ? 'b' : 'w'; p[3] = '-'; return p.join(' '); }
const slim = (l, fen) => ({ san: sanLine(fen, l.pv), cp: l.cpWhite, wdl: l.wdlWhite, depth: l.depth });

const g = new Chess(G.start || START); const plies = [];
for (const san of G.sans) { const fenBefore = g.fen(); const m = g.move(san); if (!m) throw new Error('illegal ' + san); plies.push({ fenBefore, san: m.san, uci: m.from + m.to + (m.promotion || ''), color: m.color, fen: g.fen() }); }
const finalTerminal = g.game_over();

const t0 = Date.now();
await Promise.all(plies.map(async (p, i) => {
  const a = await pool.analyse(p.fenBefore, { depth: DEPTH, multipv: 3 });
  p.lines = a.lines.map((l) => slim(l, p.fenBefore));
  // what the opponent was threatening: give them a free move (skip when in check: the threat is the check itself)
  const gb = new Chess(p.fenBefore);
  if (!gb.in_check()) {
    const nf = nullFen(p.fenBefore);
    if (new Chess(nf).validate_fen(nf).valid) {
      const t = await pool.analyse(nf, { depth: Math.min(DEPTH, 16), multipv: 1 });
      if (t.lines[0]) p.threat = { san: sanLine(nf, t.lines[0].pv, 4), cp: t.lines[0].cpWhite, wdl: t.lines[0].wdlWhite };
    }
  }
  p.factsBefore = Facts.positionFacts(p.fenBefore, i);
  // the move's own evaluation (searchmoves), so a played move outside the top 3 still has an exact score
  const own = p.lines.find((l) => l.san[0] === p.san) ? null : await pool.analyse(p.fenBefore, { depth: DEPTH, multipv: 1, searchmoves: [p.uci] });
  if (own && own.lines[0]) p.played = slim(own.lines[0], p.fenBefore);
  process.stdout.write('.');
}));
// evaluation after each move = analysis of the next position (or the terminal result)
for (let i = 0; i < plies.length; i++) {
  const nxt = plies[i + 1];
  if (nxt) { p_after(plies[i], nxt.lines[0]); continue; }
  const gg = new Chess(plies[i].fen);
  if (gg.game_over()) { const mated = gg.in_checkmate(); const whiteToMove = gg.turn() === 'w'; plies[i].after = { cp: mated ? (whiteToMove ? -10000 : 10000) : 0, wdl: mated ? (whiteToMove ? [0, 0, 1000] : [1000, 0, 0]) : [0, 1000, 0], terminal: mated ? 'mate' : 'draw' }; }
  else { const a = await pool.analyse(plies[i].fen, { depth: DEPTH, multipv: 1 }); p_after(plies[i], slim(a.lines[0], plies[i].fen)); }
  plies[i].factsAfter = Facts.positionFacts(plies[i].fen, i + 1);
}
function p_after(p, best) { p.after = { cp: best.cp, wdl: best.wdl, line: best.san }; }
for (let i = 0; i < plies.length; i++) if (!plies[i].factsAfter) plies[i].factsAfter = Facts.positionFacts(plies[i].fen, i + 1);
pool.close();
const out = { ...G, start: G.start || START, depth: DEPTH, engine: 'Stockfish 17.1 (lite NNUE, WASM)', analysedAt: new Date().toISOString(), finalTerminal, plies };
delete out.sans;
fs.writeFileSync(outFile, JSON.stringify(out, null, 1));
console.log(`\n${plies.length} plies analysed at depth ${DEPTH} in ${Math.round((Date.now() - t0) / 1000)} s -> ${outFile}`);
process.exit(0);
