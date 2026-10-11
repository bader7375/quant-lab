// Build the training data files from the Lichess puzzle database (CC0).
// Source: first 50k puzzles + their games, github.com/mcognetta/lichess-combined-puzzle-game-db,
// pre-flattened to ndjson lines {id, fen, moves, r, rd, pop, plays, th, gm, op, url}.
//
// usage: node tools/build_data.mjs /path/to/pz.ndjson
// writes: data/puzzles.json, data/playout.json, data/structures.json, data/opposition.json
//
// Every position that is not a Lichess puzzle (whose solution Lichess already verified with
// Stockfish) is checked here with our own Stockfish before it is written.
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
const require = createRequire(import.meta.url);
const dir = path.dirname(new URL(import.meta.url).pathname);
const root = path.join(dir, '..');
const { Chess } = require(path.join(root, 'chess.js'));
const STOCKFISH = require(path.join(root, 'stockfish.js'));
fs.mkdirSync(path.join(root, 'data'), { recursive: true });

// ---------- engine ----------
const sf = STOCKFISH();
let resolve, lines = [];
sf.onmessage = (l) => { lines.push(l); if (l.startsWith('bestmove')) resolve(); };
const send = (c) => sf.postMessage(c, true);
send('uci');
async function analyse(fen, depth, multipv = 1) {
  lines = [];
  send('setoption name MultiPV value ' + multipv);
  await new Promise((r) => { resolve = r; send('position fen ' + fen); send('go depth ' + depth); });
  const out = {};
  for (const l of lines) {
    const m = l.match(/depth (\d+) .*multipv (\d+) score (cp|mate) (-?\d+).* pv (.*?)(?: bmc.*)?$/);
    if (m && !/bound/.test(l)) out[m[2]] = { cp: m[3] === 'cp' ? +m[4] : (+m[4] > 0 ? 10000 - 10 * +m[4] : -10000 - 10 * +m[4]), mate: m[3] === 'mate' ? +m[4] : null, pv: m[5].split(' ') };
  }
  return Object.keys(out).sort().map((k) => out[k]); // scores from side to move
}

// ---------- read puzzles ----------
const rows = fs.readFileSync(process.argv[2], 'utf8').trim().split('\n').map((l) => JSON.parse(l));
const KEEP = new Set(['mateIn1', 'mateIn2', 'mateIn3', 'backRankMate', 'smotheredMate', 'hookMate', 'anastasiaMate', 'arabianMate', 'fork', 'pin', 'skewer',
  'discoveredAttack', 'doubleCheck', 'hangingPiece', 'trappedPiece', 'deflection', 'attraction', 'capturingDefender', 'intermezzo', 'xRayAttack', 'clearance',
  'interference', 'promotion', 'advancedPawn', 'defensiveMove', 'quietMove', 'zugzwang', 'attackingF2F7', 'sacrifice', 'kingsideAttack', 'exposedKing',
  'pawnEndgame', 'rookEndgame', 'queenEndgame', 'bishopEndgame', 'knightEndgame', 'endgame', 'middlegame', 'opening', 'mate', 'crushing', 'advantage',
  'equality', 'short', 'long', 'veryLong', 'oneMove']);

function prep(d) {
  const g = new Chess(d.fen); const mv = d.moves.split(' ');
  const first = g.move({ from: mv[0].slice(0, 2), to: mv[0].slice(2, 4), promotion: mv[0][4] });
  if (!first) return null;
  const pfen = g.fen();
  const sol = mv.slice(1); const g2 = new Chess(pfen); const sans = [];
  for (const u of sol) { const m = g2.move({ from: u.slice(0, 2), to: u.slice(2, 4), promotion: u[4] }); if (!m) return null; sans.push(m.san); }
  const t = d.th.split(' ').filter((x) => KEEP.has(x));
  // Greek gift: the first solution move is a bishop capture on h7/h2 with check
  const s0 = sans[0];
  if (/^Bx(h7|h2)\+/.test(s0)) t.push('greekGift');
  return { i: d.id, f: pfen, l: mv[0], ls: first.san, s: sol.join(' '), r: d.r, t, end: g2.fen() };
}

const pool = rows.filter((d) => d.r >= 450 && d.r <= 1650 && d.pop >= 80 && d.plays >= 150).map(prep).filter(Boolean);
console.log('eligible puzzles', pool.length);

// stable pseudo-random shuffle
let seed = 7; const rnd = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
const shuffle = (a) => { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
shuffle(pool);

const chosen = new Map();
// 1) per-theme sets, spread over rating buckets
const CHUNK_THEMES = ['mateIn1', 'mateIn2', 'backRankMate', 'smotheredMate', 'hookMate', 'anastasiaMate', 'fork', 'pin', 'skewer', 'discoveredAttack', 'doubleCheck',
  'hangingPiece', 'trappedPiece', 'deflection', 'attraction', 'capturingDefender', 'intermezzo', 'xRayAttack', 'clearance', 'interference', 'promotion',
  'defensiveMove', 'quietMove', 'zugzwang', 'attackingF2F7', 'greekGift', 'pawnEndgame', 'rookEndgame', 'queenEndgame', 'bishopEndgame', 'knightEndgame'];
for (const th of CHUNK_THEMES) {
  const xs = pool.filter((p) => p.t.includes(th));
  const buckets = {};
  for (const p of xs) { const b = Math.floor(p.r / 150); (buckets[b] = buckets[b] || []).push(p); }
  let took = 0; const keys = Object.keys(buckets).sort();
  for (let round = 0; took < 40 && round < 40; round++) for (const k of keys) { const p = buckets[k][round]; if (p && took < 40) { chosen.set(p.i, p); took++; } }
  console.log(th.padEnd(18), xs.length, '->', took);
}
// 2) general pool, uniform over rating buckets
const byB = {};
for (const p of pool) { const b = Math.floor(p.r / 100); (byB[b] = byB[b] || []).push(p); }
for (const k of Object.keys(byB)) for (const p of byB[k].slice(0, 160)) chosen.set(p.i, p);
const puzzles = [...chosen.values()].map(({ end, ...p }) => p).sort((a, b) => a.r - b.r);
fs.writeFileSync(path.join(root, 'data/puzzles.json'), JSON.stringify(puzzles));
console.log('puzzles written', puzzles.length);

// ---------- play-out positions: puzzle end positions that are clearly won but not yet over ----------
const playCands = pool.filter((p) => p.t.includes('crushing') && !p.t.includes('mate')).slice(0, 220);
const playout = [];
for (const p of playCands) {
  if (playout.length >= 40) break;
  const g = new Chess(p.end); if (g.game_over()) continue;
  // the side that solved the puzzle is the side that moved last in the solution, i.e. NOT to move now
  const [best] = await analyse(p.end, 14);
  if (!best) continue;
  const solverCp = -best.cp;
  if (solverCp >= 350 && solverCp <= 2500) {
    const phase = p.t.includes('endgame') ? 'endgame' : 'middlegame';
    playout.push({ i: 'po-' + p.i, f: p.end, side: g.turn() === 'w' ? 'b' : 'w', cp: solverCp, phase, from: p.i });
  }
}
// textbook conversions (verified below)
const BASIC = [
  { i: 'po-kqk', f: '8/8/8/4k3/8/8/8/3QK3 w - - 0 1', note: 'KQK' },
  { i: 'po-krk', f: '8/8/8/4k3/8/8/8/R3K3 w - - 0 1', note: 'KRK' },
  { i: 'po-kpk', f: '8/8/4k3/8/8/4K3/4P3/8 w - - 0 1', note: 'KPK' },
  { i: 'po-lucena', f: '1K6/1P1k4/8/8/8/8/r7/2R5 w - - 0 1', note: 'Lucena' },
  { i: 'po-kbbk', f: '8/8/8/4k3/8/8/8/2B1KB2 w - - 0 1', note: 'KBBK' },
];
for (const b of BASIC) {
  const [best] = await analyse(b.f, 18);
  const ok = best && best.cp >= 500;
  console.log('basic', b.i, ok ? 'won' : 'NOT WON', best && best.cp);
  if (ok) playout.unshift({ i: b.i, f: b.f, side: 'w', cp: best.cp, phase: 'endgame', basic: b.note });
}
fs.writeFileSync(path.join(root, 'data/playout.json'), JSON.stringify(playout));
console.log('playout written', playout.length);

// ---------- pawn structures from the puzzle games ----------
function pawnsOf(g, color) { const out = []; for (const f of 'abcdefgh') for (let r = 1; r <= 8; r++) { const p = g.get(f + r); if (p && p.type === 'p' && p.color === color) out.push(f + r); } return out; }
function pieceCount(g) { let n = 0; for (const f of 'abcdefgh') for (let r = 1; r <= 8; r++) { const p = g.get(f + r); if (p && p.type !== 'p' && p.type !== 'k') n++; } return n; }
const hasFile = (ps, f) => ps.some((s) => s[0] === f);
function structureOf(g) {
  const W = pawnsOf(g, 'w'), B = pawnsOf(g, 'b');
  if (pieceCount(g) < 8) return null;
  if (W.includes('d4') && !hasFile(W, 'c') && !hasFile(W, 'e') && !hasFile(B, 'd')) return 'iqp-w';
  if (B.includes('d5') && !hasFile(B, 'c') && !hasFile(B, 'e') && !hasFile(W, 'd')) return 'iqp-b';
  if (W.includes('d4') && !hasFile(W, 'c') && B.includes('c6') && B.includes('d5') && !hasFile(B, 'e') && W.includes('b2') && B.includes('b7')) return 'carlsbad';
  return null;
}
const structs = { 'iqp-w': [], 'iqp-b': [], carlsbad: [], none: [] };
for (const d of rows.slice(0, 20000)) {
  if (!d.gm) continue;
  const g = new Chess(); const sans = d.gm.trim().split(' '); let found = null;
  for (let ply = 0; ply < Math.min(sans.length, 44); ply++) {
    if (!g.move(sans[ply], { sloppy: true })) break;
    if (ply < 15) continue;
    const s = structureOf(g);
    if (s && structs[s].length < 14) { found = { s, f: g.fen(), op: d.op }; break; }
    if (!s && ply === 26 && structs.none.length < 24 && pieceCount(g) >= 10 && rnd() < 0.05) { found = { s: 'none', f: g.fen(), op: d.op }; break; }
  }
  if (found) structs[found.s].push(found);
  if (Object.values(structs).every((a) => a.length >= 14) && structs.none.length >= 24) break;
}
// sanity: structure positions should not be tactically decided (|eval| < 2.5), so the question is about the plan
const structures = [];
for (const [k, xs] of Object.entries(structs)) for (const x of xs) {
  const [best] = await analyse(x.f, 12);
  if (best && Math.abs(best.cp) < 250) structures.push({ s: k, f: x.f, op: x.op, cp: x.f.split(' ')[1] === 'w' ? best.cp : -best.cp });
}
fs.writeFileSync(path.join(root, 'data/structures.json'), JSON.stringify(structures));
console.log('structures', Object.fromEntries(Object.keys(structs).map((k) => [k, structures.filter((x) => x.s === k).length])));

// ---------- opposition: random K+P vs K with exactly one result-preserving king move ----------
const files = 'abcdefgh'; const opp = [];
for (let tries = 0; tries < 900 && opp.length < 14; tries++) {
  const pf = files[1 + Math.floor(rnd() * 6)], pr = 2 + Math.floor(rnd() * 3);
  const wk = files[Math.floor(rnd() * 8)] + (1 + Math.floor(rnd() * 6)), bk = files[Math.floor(rnd() * 8)] + (3 + Math.floor(rnd() * 6));
  const stm = rnd() < 0.5 ? 'w' : 'b';
  const g = new Chess('8/8/8/8/8/8/8/8 w - - 0 1'); g.clear();
  if (!g.put({ type: 'k', color: 'w' }, wk) || !g.put({ type: 'k', color: 'b' }, bk) || !g.put({ type: 'p', color: 'w' }, pf + pr)) continue;
  const fen = g.fen().replace(' w ', ' ' + stm + ' ');
  const chk = new Chess(); if (!chk.load(fen) || chk.in_check() || chk.game_over()) continue;
  const dist = Math.max(Math.abs(files.indexOf(wk[0]) - files.indexOf(bk[0])), Math.abs(+wk[1] - +bk[1])); if (dist < 2 || dist > 3) continue;
  const res = await analyse(fen, 20, 2);
  if (res.length < 2) continue;
  const cls = (cp) => (cp >= 500 ? 'win' : cp <= -500 ? 'loss' : Math.abs(cp) <= 60 ? 'draw' : 'unclear');
  const a = cls(res[0].cp), b = cls(res[1].cp);
  if (a === 'unclear' || b === 'unclear' || a === b) continue;
  const san = new Chess(fen).move({ from: res[0].pv[0].slice(0, 2), to: res[0].pv[0].slice(2, 4) }).san;
  if (!san.startsWith('K')) continue;
  opp.push({ i: 'opp-' + opp.length, f: fen, best: res[0].pv[0], san, result: a === 'win' ? (stm === 'w' ? 'white wins' : 'white wins') : a === 'draw' ? 'draw' : a, stm });
}
fs.writeFileSync(path.join(root, 'data/opposition.json'), JSON.stringify(opp));
console.log('opposition', opp.length, opp.map((o) => o.f + ' ' + o.san + ' ' + o.result).join('\n'));
process.exit(0);
