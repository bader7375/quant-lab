// Re-evaluate sampled positions with Stockfish 17.1 (the app's engine build, engines/sf17-lite) at a fixed depth.
// Usage: node tools/odds/sf_rescore.mjs <in.json> <out.ndjson> [--depth 14] [--procs 2]
//   in.json  : [{key, fen, ...}, ...]  (written by fit_odds.py, stage "sample")
//   out.ndjson: one line per position {key, cpWhite, cp, mate, wdlWhite, depth, best}; resumable (keys already present are skipped).
// cpWhite follows tools/sfpool.mjs: White's view, mate encoded as +-(10000 - 10*n) like the app (js/core.js scoreCp).
// Each search starts with ucinewgame (empty hash) and Threads=1, so results are deterministic for a given depth.
import fs from 'fs';
import path from 'path';
import { Pool } from '../sfpool.mjs';

const argv = process.argv.slice(2);
const opt = (name, def) => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : def; };
const [inp, out] = argv.filter((a, i) => !a.startsWith('--') && !(i > 0 && argv[i - 1].startsWith('--')));
if (!inp || !out) { console.error('usage: node sf_rescore.mjs in.json out.ndjson [--depth 14] [--procs 2]'); process.exit(2); }
const depth = +opt('--depth', 14), procs = Math.min(2, +opt('--procs', 2));

const items = JSON.parse(fs.readFileSync(inp, 'utf8'));
const done = new Set();
if (fs.existsSync(out)) for (const l of fs.readFileSync(out, 'utf8').split('\n')) { if (l.trim()) { try { done.add(JSON.parse(l).key); } catch {} } }
const todo = items.filter((x) => !done.has(x.key));
console.log(`[sf_rescore] ${items.length} positions, ${done.size} cached, ${todo.length} to evaluate at depth ${depth} with ${procs} processes`);
if (!todo.length) process.exit(0);
fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
const ws = fs.createWriteStream(out, { flags: 'a' });
const pool = new Pool(procs);
const t0 = Date.now(); let n = 0;
await Promise.all(todo.map(async (it) => {
  const a = await pool.analyse(it.fen, { depth });
  const l = a.lines[0];
  const rec = l ? { key: it.key, cpWhite: l.cpWhite, cp: l.cp, mate: l.mate, wdlWhite: l.wdlWhite, depth: l.depth, best: a.best }
    : { key: it.key, cpWhite: null, cp: null, mate: null, wdlWhite: null, depth: 0, best: null };
  ws.write(JSON.stringify(rec) + '\n');
  if (++n % 250 === 0) console.log(`[sf_rescore] ${n}/${todo.length}  ${((Date.now() - t0) / 1000).toFixed(0)} s`);
}));
await new Promise((r) => ws.end(r));
pool.close();
console.log(`[sf_rescore] done: ${n} positions in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
