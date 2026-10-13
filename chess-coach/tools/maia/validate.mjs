#!/usr/bin/env node
/*
 * End-to-end validation of the Maia-1 JavaScript port (engines/maia/maia.js).
 *
 *   node tools/maia/validate.mjs [--workers 2] [--per-band 1500] [--dev-per-band 300] [--special 2000]
 *                                [--out /tmp/maia_validate.json] [--quick]
 *
 *   1. JS vs numpy reference (tools/maia/ref.py, same float16 .bin) on >= 300 positions with deliberately
 *      included Black-to-move, castling available / just castled, promotion possible, en passant possible,
 *      < 8 plies of history, repetitions, non-standard start FENs and terminal positions; plus JS (fp16) vs
 *      the original protobuf (fp32, unfolded batch norm).
 *   2. Move-matching top-1 accuracy, every net x mover-rating band (test split, bullet excluded, plies >= 10),
 *      Wilson 95% CIs; castling / promotion moves (with the alternative encodings as a control), the puzzle
 *      trigger moves (dataset selection bias), Lichess judgment classes, and the opening plies 0-9 with both
 *      history-fill modes.
 *   3. Value head: Brier score of the expected score vs the final result, by band, against constant and
 *      Stockfish-eval baselines (baseline parameters fitted on the dev split only); temperature fit (dev) and
 *      test log-likelihood for emulating lower ratings.
 *   4. Speed (ms per evaluation, Node, single thread) and file sizes.
 *
 * Dataset: Lichess games behind the Lichess puzzles (mcognetta combined puzzle/game DB, first 50k).
 * Split: sha1(game id) % 5 == 0 -> dev (used for any fitted constant), else test (all reported accuracies).
 */
import fs from 'fs';
import path from 'path';
import os from 'os';
import crypto from 'crypto';
import zlib from 'zlib';
import readline from 'readline';
import { spawn, execFileSync } from 'child_process';
import { Worker, isMainThread, parentPort, workerData } from 'worker_threads';
import { createRequire } from 'module';
import { fileURLToPath, pathToFileURL } from 'url';

const require = createRequire(import.meta.url);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const ENG = path.join(ROOT, 'engines/maia');
const MaiaNet = require(path.join(ENG, 'maia.js'));
const { Chess } = require(path.join(ROOT, 'chess.js'));
const RATINGS = [1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900];
const TGRID = [0.5, 0.7, 0.85, 1.0, 1.15, 1.3, 1.5, 1.75, 2.0, 2.5];
const REC = 10 + 2 * TGRID.length;           // floats per (position, net)
const TOFF = 10;                              // offset of the temperature block
const START = MaiaNet.STARTPOS;
const BANDS = ['<1000', ...Array.from({ length: 11 }, (_, i) => `${1000 + 100 * i}-${1099 + 100 * i}`), '2100+'];
const band = (r) => (r < 1000 ? 0 : r >= 2100 ? 12 : 1 + Math.floor((r - 1000) / 100));
const matchedNet = (r) => Math.min(1900, Math.max(1100, Math.floor(r / 100) * 100));

function loadNets() {
  const man = JSON.parse(fs.readFileSync(path.join(ENG, 'manifest.json'), 'utf8'));
  return { man, nets: RATINGS.map((r) => MaiaNet.load(fs.readFileSync(path.join(ENG, man.files[r].file)), man)) };
}

// ================================================================== worker: evaluate positions
if (!isMainThread) {
  const { nets } = loadNets();
  const { movePlane } = MaiaNet._internal;
  const jobs = workerData.jobs;
  let done = 0, chunk = [], badGames = 0, consistencyChecked = 0, consistencyBad = 0;
  for (const job of jobs) {
    const c = new Chess();
    const uci = [];
    const maxPly = job.positions[job.positions.length - 1].ply;
    let ok = true;
    for (let i = 0; i <= maxPly; i++) {
      const m = c.move(job.san[i]);
      if (!m) { ok = false; break; }
      uci.push(m.from + m.to + (m.promotion || ''));
    }
    if (!ok) { badGames++; continue; }
    for (const pos of job.positions) {
      const i = pos.ply, played = uci[i], moverWhite = i % 2 === 0;
      for (const fill of pos.fills) {
        const res = MaiaNet.evaluateMany(nets, START, uci.slice(0, i), { historyFill: fill });
        if (consistencyChecked < 40 && fill === 'fen_only') {          // public single-net path must agree
          consistencyChecked++;
          const k = consistencyChecked % nets.length, single = nets[k].evaluate(START, uci.slice(0, i));
          if (single.policy[0].uci !== res[k].policy[0].uci || Math.abs(single.policy[0].p - res[k].policy[0].p) > 1e-12) consistencyBad++;
          MaiaNet.evaluateMany(nets, START, uci.slice(0, i), { historyFill: fill });   // restore per-net buffers
        }
        const data = new Float32Array(nets.length * REC);
        const legal = (pos.castle || pos.promo) ? nets[0].cache.game.moves({ verbose: true }) : null;
        for (let k = 0; k < nets.length; k++) {
          const r = res[k], o = k * REC;
          const idx = r.policy.findIndex((m) => m.uci === played);
          const pp = idx >= 0 ? r.policy[idx].p : 0;
          data[o] = idx === 0 ? 1 : 0; data[o + 1] = pp; data[o + 2] = idx + 1;
          data[o + 3] = r.value.w; data[o + 4] = r.value.d; data[o + 5] = r.value.l;
          if (legal) {      // control: the alternative castling / promotion encodings
            const black = !moverWhite;
            const alt = legal.map((m) => {
              let mm = m;
              if (pos.castle && (m.flags.includes('k') || m.flags.includes('q'))) mm = Object.assign({}, m, { flags: 'n' });
              if (pos.promo && m.promotion) mm = Object.assign({}, m, { promotion: m.promotion === 'q' ? 'n' : m.promotion === 'n' ? 'q' : m.promotion });
              const mp = movePlane(mm, black);
              return nets[k].policyLogit(mp.plane, mp.sq);
            });
            const mx = Math.max(...alt), ex = alt.map((z) => Math.exp(z - mx)), s = ex.reduce((a, b) => a + b, 0);
            const pi = legal.findIndex((m) => m.from + m.to + (m.promotion || '') === played);
            let best = 0;
            for (let j = 1; j < ex.length; j++) if (ex[j] > ex[best]) best = j;
            data[o + 6] = best === pi ? 1 : 0; data[o + 7] = pi >= 0 ? ex[pi] / s : 0;
          } else { data[o + 6] = NaN; data[o + 7] = NaN; }
          if (pos.promo) {  // p of the knight / queen promotion with the played move's from-to squares
            const ft = played.slice(0, 4);
            data[o + 8] = (r.policy.find((m) => m.uci === ft + 'n') || { p: NaN }).p;
            data[o + 9] = (r.policy.find((m) => m.uci === ft + 'q') || { p: NaN }).p;
          } else { data[o + 8] = NaN; data[o + 9] = NaN; }
          // tempered distributions p_T ~ p^(1/T): log p_T(played) and p_T(played)
          const lps = r.policy.map((m) => Math.log(Math.max(m.p, 1e-300)));
          const lpPlayed = Math.log(Math.max(pp, 1e-300));
          TGRID.forEach((T, t) => {
            let mx = -Infinity;
            for (const lp of lps) if (lp / T > mx) mx = lp / T;
            let s = 0;
            for (const lp of lps) s += Math.exp(lp / T - mx);
            const lpt = lpPlayed / T - mx - Math.log(s);
            data[o + TOFF + t] = lpt; data[o + TOFF + TGRID.length + t] = Math.exp(lpt);
          });
        }
        chunk.push({ g: job.gid, ply: i, sets: pos.sets, fill, data });
      }
      done++;
    }
    if (chunk.length >= 400) { parentPort.postMessage({ type: 'chunk', recs: chunk, done }); chunk = []; }
  }
  parentPort.postMessage({ type: 'chunk', recs: chunk, done });
  parentPort.postMessage({ type: 'done', badGames, consistencyChecked, consistencyBad });
}

// ================================================================== main thread
function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  if (i < 0) return def;
  const v = process.argv[i + 1];
  return v === undefined || v.startsWith('--') ? true : v;
}
function rng32(seed) {           // mulberry32
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
function shuffle(a, rnd) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
function wilson(k, n, z = 1.96) {
  if (!n) return [NaN, NaN];
  const p = k / n, d = 1 + z * z / n, c = p + z * z / (2 * n), h = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n));
  return [(c - h) / d, (c + h) / d];
}
const pct = (x, d = 1) => (Number.isFinite(x) ? (100 * x).toFixed(d) : ' n/a');
const fmtAcc = (k, n) => { const [lo, hi] = wilson(k, n); return `${pct(k / n)} [${pct(lo)}-${pct(hi)}]`; };
const mean = (a) => a.reduce((s, x) => s + x, 0) / a.length;
const pad = (s, n) => String(s).padStart(n);
const padr = (s, n) => String(s).padEnd(n);

async function readDataset(file) {
  const games = [];
  const child = spawn('bzip2', ['-dc', file], { stdio: ['ignore', 'pipe', 'inherit'] });
  const rl = readline.createInterface({ input: child.stdout, crlfDelay: Infinity });
  for await (const line of rl) {
    if (!line) continue;
    const d = JSON.parse(line), g = d.game, p = d.puzzle || {};
    const m = /#(\d+)$/.exec(p.GameUrl || '');
    const an = g.analysis || [];
    const san = (g.moves || '').split(' ').filter(Boolean);
    const clk = [];
    const re = /\[%clk (\d+):(\d+):(\d+)\]/g;
    let cm;
    while ((cm = re.exec(g.pgn || ''))) clk.push(3600 * +cm[1] + 60 * +cm[2] + +cm[3]);
    games.push({
      id: g.id, san, clk: clk.length === san.length ? clk : null, clockInitial: g.clock ? g.clock.initial : null,
      wr: g.players?.white?.rating, br: g.players?.black?.rating, winner: g.winner || null,
      speed: g.speed, rated: g.rated, variant: g.variant, initialFen: g.initialFen || null, status: g.status,
      pzPly: m ? +m[1] : null, pzFen: p.FEN, pzMoves: (p.Moves || '').split(' ').filter(Boolean),
      ev: an.map((a) => ('eval' in a ? a.eval : 'mate' in a ? (a.mate > 0 ? 2000 : -2000) : null)),
      judg: an.map((a) => (a.judgment ? a.judgment.name : '')),
      split: parseInt(crypto.createHash('sha1').update(g.id).digest('hex').slice(0, 8), 16) % 5 === 0 ? 'dev' : 'test',
    });
  }
  return games;
}

function runRef(python, args) {
  execFileSync(python, ['-I', path.join(HERE, 'ref.py'), 'eval', ...args], {
    stdio: ['ignore', 'inherit', 'inherit'],
    env: Object.assign({}, process.env, { OPENBLAS_NUM_THREADS: '1', OMP_NUM_THREADS: '1', MKL_NUM_THREADS: '1' }),
  });
}

// ------------------------------------------------------------------ step 1: JS vs numpy reference
function buildRefCases(games, rnd, quick) {
  const target = quick
    ? { short_history: 8, black_to_move: 8, castling_available: 8, just_castled: 6, promotion_possible: 8, ep_possible: 8, repetition: 4, fen_start: 8, random: 8, terminal: 4 }
    : { short_history: 40, black_to_move: 50, castling_available: 40, just_castled: 30, promotion_possible: 40, ep_possible: 40, repetition: 25, fen_start: 40, random: 60, terminal: 12 };
  const cand = Object.fromEntries(Object.keys(target).map((k) => [k, []]));
  const dev = shuffle(games.filter((g) => g.split === 'dev' && g.variant === 'standard' && !g.initialFen && g.san.length > 0), rnd);
  for (const g of dev.slice(0, quick ? 150 : 700)) {
    const c = new Chess(), uci = [], seen = new Map();
    let prevCastle = false, okGame = true;
    for (let i = 0; i <= g.san.length; i++) {
      const key = c.fen().split(' ').slice(0, 4).join(' ');
      const rep = seen.has(key);
      seen.set(key, true);
      const legal = c.moves({ verbose: true });
      const cs = { startFen: START, moves: uci.slice(), cat: '' };
      if (!legal.length) { if (i === g.san.length) cand.terminal.push(cs); }
      else {
        if (i < 8) cand.short_history.push(cs);
        if (i % 2 === 1) cand.black_to_move.push(cs);
        if (legal.some((m) => m.flags.includes('k') || m.flags.includes('q'))) cand.castling_available.push(cs);
        if (prevCastle) cand.just_castled.push(cs);
        if (legal.some((m) => m.promotion)) cand.promotion_possible.push(cs);
        if (legal.some((m) => m.flags.includes('e'))) cand.ep_possible.push(cs);
        if (rep) cand.repetition.push(cs);
        if (i >= 8) cand.random.push(cs);
      }
      if (i === g.san.length) break;
      const m = c.move(g.san[i]);
      if (!m) { okGame = false; break; }
      uci.push(m.from + m.to + (m.promotion || ''));
      prevCastle = m.flags.includes('k') || m.flags.includes('q');
    }
    if (!okGame) continue;
  }
  // non-standard start FENs: puzzle positions (+ 0..3 moves of the puzzle line) -> lc0 fen_only history fill
  const pz = shuffle(dev.filter((g) => g.pzFen), rnd);
  const withEp = pz.filter((g) => g.pzFen.split(' ')[3] !== '-');
  for (const g of [...withEp.slice(0, 10), ...pz]) {
    const k = Math.floor(rnd() * Math.min(4, g.pzMoves.length + 1));
    cand.fen_start.push({ startFen: g.pzFen, moves: g.pzMoves.slice(0, k), cat: '' });
    if (cand.fen_start.length >= 4 * target.fen_start) break;
  }
  const cases = [];
  for (const [cat, n] of Object.entries(target)) {
    const pool = cat === 'fen_start' ? cand[cat] : shuffle(cand[cat], rnd);
    for (const cs of pool.slice(0, n)) cases.push(Object.assign({}, cs, { cat }));
  }
  return { cases, available: Object.fromEntries(Object.entries(cand).map(([k, v]) => [k, v.length])) };
}

function compareRef(jsOut, refOut, cases) {
  const s = { n: 0, top1Same: 0, sameMoveSet: 0, maxDp: 0, maxDwdl: 0, empty: 0, byCat: {} };
  cases.forEach((cs, i) => {
    const a = jsOut[i], b = refOut[i];
    const cat = (s.byCat[cs.cat] = s.byCat[cs.cat] || { n: 0, top1Same: 0, maxDp: 0 });
    s.n++; cat.n++;
    if (!a.policy.length && !b.policy.length) { s.empty++; s.top1Same++; s.sameMoveSet++; cat.top1Same++; return; }
    const pb = new Map(b.policy.map(([u, p]) => [u, p]));
    const same = a.policy.length === pb.size && a.policy.every((m) => pb.has(m.uci));
    if (same) s.sameMoveSet++;
    if (a.policy[0].uci === b.policy[0][0]) { s.top1Same++; cat.top1Same++; }
    let dp = 0;
    for (const m of a.policy) dp = Math.max(dp, Math.abs(m.p - (pb.get(m.uci) ?? Infinity)));
    s.maxDp = Math.max(s.maxDp, dp); cat.maxDp = Math.max(cat.maxDp, dp);
    if (!a.terminal) s.maxDwdl = Math.max(s.maxDwdl, Math.abs(a.value.w - b.wdl[0]), Math.abs(a.value.d - b.wdl[1]), Math.abs(a.value.l - b.wdl[2]));
  });
  return s;
}

async function main() {
  const t00 = Date.now();
  const quick = !!arg('quick', false);
  const dataset = arg('dataset', '/tmp/claude-0/mcognetta_lichess-combined-puzzle-game-db/combined_puzzle_db_first_50k.ndjson.bz2');
  const python = arg('python', '/tmp/claude-0/venv/bin/python');
  const nWorkers = +arg('workers', 2);
  const perBand = +arg('per-band', quick ? 60 : 1500);
  const devPerBand = +arg('dev-per-band', quick ? 20 : 300);
  const nSpecial = +arg('special', quick ? 60 : 2000);
  const outFile = arg('out', path.join(os.tmpdir(), 'maia_validate.json'));
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'maia-validate-'));
  const results = { config: { quick, dataset, perBand, devPerBand, nSpecial, nWorkers, node: process.version, cpus: os.cpus().length } };
  const rnd = rng32(20261012);
  console.log(`# Maia JS port validation  (node ${process.version}, ${os.cpus().length} CPUs, quick=${quick})`);

  const games = await readDataset(dataset);
  const speeds = {};
  for (const g of games) speeds[g.speed] = (speeds[g.speed] || 0) + 1;
  console.log(`dataset: ${games.length} games; speeds ${JSON.stringify(speeds)}; dev split ${games.filter((g) => g.split === 'dev').length}, test split ${games.filter((g) => g.split === 'test').length}`);
  results.dataset = { games: games.length, speeds };

  // ---------------------------------------------------------------- step 1
  console.log('\n## 1. JS (maia.js) vs numpy reference (ref.py)');
  const { cases, available } = buildRefCases(games, rnd, quick);
  const catCount = {};
  for (const c of cases) catCount[c.cat] = (catCount[c.cat] || 0) + 1;
  console.log(`cases: ${cases.length}  ${JSON.stringify(catCount)}  (candidates available: ${JSON.stringify(available)})`);
  fs.writeFileSync(path.join(tmp, 'cases.json'), JSON.stringify(cases.map((c) => ({ startFen: c.startFen, moves: c.moves }))));
  const { man, nets } = loadNets();
  const step1 = {};
  const jsOutAll = {};
  for (let k = 0; k < RATINGS.length; k++) {
    const r = RATINGS[k];
    jsOutAll[r] = cases.map((c) => nets[k].evaluate(c.startFen, c.moves));
    runRef(python, ['--bin', path.join(ENG, man.files[r].file), '--manifest', path.join(ENG, 'manifest.json'),
      '--cases', path.join(tmp, 'cases.json'), '--out', path.join(tmp, `ref_bin_${r}.json`)]);
    runRef(python, ['--pb', path.join(arg('weights', '/tmp/claude-0/maia-chess/maia_weights'), `maia-${r}.pb.gz`),
      '--cases', path.join(tmp, 'cases.json'), '--out', path.join(tmp, `ref_pb_${r}.json`)]);
    const sBin = compareRef(jsOutAll[r], JSON.parse(fs.readFileSync(path.join(tmp, `ref_bin_${r}.json`))), cases);
    const sPb = compareRef(jsOutAll[r], JSON.parse(fs.readFileSync(path.join(tmp, `ref_pb_${r}.json`))), cases);
    step1[r] = { vsBin: sBin, vsPb: sPb };
    console.log(`maia-${r}: vs ref(same fp16 .bin): top-1 identical ${sBin.top1Same}/${sBin.n}, legal-move sets identical ${sBin.sameMoveSet}/${sBin.n}, max|p_js-p_ref| ${sBin.maxDp.toExponential(2)}, max|wdl diff| ${sBin.maxDwdl.toExponential(2)} (non-terminal)` +
      `  |  vs ref(original pb, fp32, unfolded BN): top-1 identical ${sPb.top1Same}/${sPb.n}, max|dp| ${sPb.maxDp.toExponential(2)}, max|dwdl| ${sPb.maxDwdl.toExponential(2)}`);
  }
  const cats = Object.keys(catCount);
  console.log('per category (all 9 nets pooled): ' + cats.map((c) => {
    let n = 0, t = 0, dp = 0;
    for (const r of RATINGS) { const x = step1[r].vsBin.byCat[c]; n += x.n; t += x.top1Same; dp = Math.max(dp, x.maxDp); }
    return `${c} ${t}/${n} max|dp| ${dp.toExponential(1)}`;
  }).join('; '));
  results.step1 = { cases: cases.length, categories: catCount, perNet: step1 };

  // ---------------------------------------------------------------- step 2/3 sampling
  const eligible = (g) => g.rated && g.speed !== 'bullet' && g.variant === 'standard' && !g.initialFen && g.wr && g.br && g.san.length > 0;
  const posMap = new Map();   // key gid:ply -> {gi, ply, sets:Set, fills:Set}
  const addPos = (gi, ply, set, fills = ['fen_only']) => {
    const k = gi + ':' + ply;
    let p = posMap.get(k);
    if (!p) posMap.set(k, (p = { gi, ply, sets: new Set(), fills: new Set() }));
    p.sets.add(set);
    fills.forEach((f) => p.fills.add(f));
  };
  const gidx = games.map((g, i) => i);
  // <= 4 random plies (>= 10) per game; a band with no more eligible positions than the cap is taken in full
  const sampleBands = (split, cap, setName) => {
    const cnt = new Array(BANDS.length).fill(0), avail = new Array(BANDS.length).fill(0), gset = BANDS.map(() => new Set());
    const order = shuffle(gidx.filter((i) => games[i].split === split && eligible(games[i])), rnd);
    for (const gi of order) {
      const g = games[gi];
      for (let i = 10; i < g.san.length; i++) avail[band(i % 2 === 0 ? g.wr : g.br)]++;
    }
    const takeAll = avail.map((a) => a <= cap);
    for (const gi of order) {
      const g = games[gi];
      const plies = shuffle(Array.from({ length: Math.max(0, g.san.length - 10) }, (_, j) => j + 10), rnd);
      let taken = 0;
      for (const i of plies) {
        const b = band(i % 2 === 0 ? g.wr : g.br);
        if (cnt[b] >= cap || (!takeAll[b] && taken >= 4)) continue;
        if (!takeAll[b]) taken++;
        cnt[b]++; gset[b].add(gi); addPos(gi, i, setName);
      }
    }
    return { cnt, avail, games: gset.map((x) => x.size) };
  };
  const mainS = sampleBands('test', perBand, 'main');
  const devS = sampleBands('dev', devPerBand, 'dev');
  console.log(`\nmain sample (test split, plies >= 10, <= 4 positions/game): ${mainS.cnt.reduce((a, b) => a + b)} positions; per band ${JSON.stringify(mainS.cnt)}`);
  console.log(`  distinct games per band: ${JSON.stringify(mainS.games)}; eligible test positions per band: ${JSON.stringify(mainS.avail)}`);
  console.log(`  (bands with no more eligible positions than the cap are taken in full, i.e. many positions per game)`);
  console.log(`dev sample (for fitted constants only): ${devS.cnt.reduce((a, b) => a + b)} positions; per band ${JSON.stringify(devS.cnt)}`);
  const testGames = gidx.filter((i) => games[i].split === 'test' && eligible(games[i]));
  const castles = [], promos = [], triggers = [], openings = [];
  for (const gi of testGames) {
    const g = games[gi];
    g.san.forEach((s, i) => { if (s.startsWith('O-O')) castles.push([gi, i]); if (s.includes('=')) promos.push([gi, i]); });
    if (g.pzPly && g.pzPly - 1 < g.san.length && g.pzPly - 1 >= 0) triggers.push([gi, g.pzPly - 1]);
    for (let i = 0; i < Math.min(10, g.san.length); i++) openings.push([gi, i]);
  }
  const nKnightPromo = promos.filter(([gi, i]) => games[gi].san[i].includes('=N')).length;
  console.log(`special sets available (test): castling moves ${castles.length}, promotions ${promos.length} (=N ${nKnightPromo}), puzzle-trigger moves ${triggers.length}, opening plies 0-9 ${openings.length}`);
  shuffle(castles, rnd).slice(0, nSpecial).forEach(([gi, i]) => addPos(gi, i, 'castle'));
  const promoSel = shuffle(promos, rnd).slice(0, quick ? nSpecial : Math.max(nSpecial, 3000));
  const knightSel = promos.filter(([gi, i]) => games[gi].san[i].includes('=N')).slice(0, quick ? 10 : Infinity);
  [...promoSel, ...knightSel].forEach(([gi, i]) => addPos(gi, i, 'promo'));
  shuffle(triggers, rnd).slice(0, nSpecial).forEach(([gi, i]) => addPos(gi, i, 'trigger'));
  shuffle(openings, rnd).slice(0, nSpecial).forEach(([gi, i]) => addPos(gi, i, 'opening', ['fen_only', 'always']));

  // jobs per game
  const byGame = new Map();
  for (const p of posMap.values()) {
    if (!byGame.has(p.gi)) byGame.set(p.gi, []);
    const g = games[p.gi];
    byGame.get(p.gi).push({ ply: p.ply, sets: [...p.sets], fills: [...p.fills], castle: g.san[p.ply].startsWith('O-O'), promo: g.san[p.ply].includes('=') });
  }
  const jobs = [...byGame.entries()].map(([gi, positions]) => {
    positions.sort((a, b) => a.ply - b.ply);
    return { gid: gi, san: games[gi].san.slice(0, positions[positions.length - 1].ply + 1), positions };
  });
  const nEvals = jobs.reduce((s, j) => s + j.positions.reduce((t, p) => t + p.fills.length, 0), 0);
  console.log(`evaluating ${posMap.size} positions (${nEvals} position-evaluations x 9 nets) from ${jobs.length} games with ${nWorkers} worker threads ...`);
  const t1 = Date.now();
  const recs = [];
  const wstats = [];
  await Promise.all(Array.from({ length: nWorkers }, (_, w) => new Promise((resolve, reject) => {
    const mine = jobs.filter((_, j) => j % nWorkers === w);
    const wk = new Worker(fileURLToPath(import.meta.url), { workerData: { jobs: mine } });
    let last = Date.now();
    wk.on('message', (m) => {
      if (m.type === 'chunk') {
        recs.push(...m.recs);
        if (w === 0 && Date.now() - last > 60000) { last = Date.now(); console.log(`  progress: ${recs.length}/${nEvals} evaluations, ${((Date.now() - t1) / 1000).toFixed(0)} s`); }
      } else if (m.type === 'done') { wstats.push(m); resolve(); }
    });
    wk.on('error', reject);
    wk.on('exit', (code) => { if (code !== 0) reject(new Error('worker exit ' + code)); });
  })));
  const evalSec = (Date.now() - t1) / 1000;
  console.log(`done: ${recs.length} evaluations in ${evalSec.toFixed(0)} s; unparsable games ${wstats.reduce((s, x) => s + x.badGames, 0)}; evaluate() vs evaluateMany() consistency mismatches ${wstats.reduce((s, x) => s + x.consistencyBad, 0)}/${wstats.reduce((s, x) => s + x.consistencyChecked, 0)}`);

  // annotate
  const R = recs.map((r) => {
    const g = games[r.g], i = r.ply, moverWhite = i % 2 === 0, rating = moverWhite ? g.wr : g.br;
    const outcome = !g.winner ? 0.5 : (g.winner === 'white') === moverWhite ? 1 : 0;
    const evPrev = i >= 1 ? g.ev[i - 1] : null;
    const cp = evPrev === null || evPrev === undefined ? null : (moverWhite ? evPrev : -evPrev);
    const clk = g.clk ? (i >= 2 ? g.clk[i - 2] : g.clockInitial) : null;     // mover's clock before the move
    return Object.assign(r, { rating, band: band(rating), outcome, cp, judg: g.judg[i] || '', san: g.san[i], moverWhite, clk });
  });
  const get = (r, k, f) => r.data[k * REC + f];
  const inSet = (s, fill = 'fen_only') => R.filter((r) => r.sets.includes(s) && r.fill === fill);

  // ---------------------------------------------------------------- step 2: accuracy matrix
  console.log('\n## 2. Move-matching top-1 accuracy (test split, bullet excluded, plies >= 10), % [Wilson 95% CI]');
  const main = inSet('main');
  const matrix = [];
  console.log(padr('mover band', 11) + pad('n', 6) + RATINGS.map((r) => pad('maia-' + r, 19)).join('') + '   best net');
  for (let b = 0; b < BANDS.length; b++) {
    const rows = main.filter((r) => r.band === b);
    const n = rows.length;
    const hits = RATINGS.map((_, k) => rows.reduce((s, r) => s + get(r, k, 0), 0));
    const best = hits.indexOf(Math.max(...hits));
    matrix.push({ band: BANDS[b], n, hits, acc: hits.map((h) => h / n), ci: hits.map((h) => wilson(h, n)), best: RATINGS[best] });
    console.log(padr(BANDS[b], 11) + pad(n, 6) + hits.map((h) => pad(fmtAcc(h, n), 19)).join('') + '   ' + RATINGS[best]);
  }
  const allHits = RATINGS.map((_, k) => main.reduce((s, r) => s + get(r, k, 0), 0));
  console.log(padr('all', 11) + pad(main.length, 6) + allHits.map((h) => pad(fmtAcc(h, main.length), 19)).join(''));
  // matched net and paired best-vs-matched difference
  let mk = 0;
  const pairedLines = [];
  for (let b = 0; b < BANDS.length; b++) {
    const rows = main.filter((r) => r.band === b);
    if (!rows.length) continue;
    const km = RATINGS.indexOf(matchedNet(b === 0 ? 999 : b === 12 ? 2100 : 1000 + 100 * (b - 1)));
    const kb = RATINGS.indexOf(matrix[b].best);
    let bOnly = 0, mOnly = 0;
    for (const r of rows) { const x = get(r, kb, 0), y = get(r, km, 0); if (x && !y) bOnly++; if (y && !x) mOnly++; }
    const n = rows.length, diff = (bOnly - mOnly) / n, se = Math.sqrt(bOnly + mOnly - (bOnly - mOnly) ** 2 / n) / n;
    mk += rows.reduce((s, r) => s + get(r, km, 0), 0);
    pairedLines.push(`${BANDS[b]}: matched maia-${RATINGS[km]} ${pct(matrix[b].acc[km])}%, best maia-${matrix[b].best} ${pct(matrix[b].acc[kb])}% (paired diff ${pct(diff, 2)} +- ${pct(1.96 * se, 2)} pp)`);
  }
  console.log('matched net = clamp(floor(rating/100)*100, 1100, 1900):');
  pairedLines.forEach((l) => console.log('  ' + l));
  console.log(`matched-net accuracy, all bands pooled: ${fmtAcc(mk, main.length)}`);
  results.step2 = { bands: BANDS, matrix, all: { n: main.length, hits: allHits }, matchedPooled: { n: main.length, hits: mk } };

  // castling
  const castle = inSet('castle');
  console.log(`\ncastling moves (test, all plies; n=${castle.length}; ${castle.filter((r) => r.ply >= 10).length} at ply >= 10):`);
  console.log('  encoding king->rook (e1h1, used):   ' + RATINGS.map((r, k) => `${r} ${pct(mean(castle.map((x) => get(x, k, 0))))}`).join('  '));
  console.log('  encoding king two squares (e1g1):   ' + RATINGS.map((r, k) => `${r} ${pct(mean(castle.map((x) => get(x, k, 6))))}`).join('  '));
  console.log('  mean p(played castle), used / alt:  ' + RATINGS.map((r, k) => `${r} ${mean(castle.map((x) => get(x, k, 1))).toFixed(3)}/${mean(castle.map((x) => get(x, k, 7))).toFixed(3)}`).join('  '));
  const castleMatched = castle.reduce((s, x) => s + get(x, RATINGS.indexOf(matchedNet(x.rating)), 0), 0);
  console.log(`  matched net: ${fmtAcc(castleMatched, castle.length)} (O-O ${castle.filter((x) => !x.san.startsWith('O-O-O')).length}, O-O-O ${castle.filter((x) => x.san.startsWith('O-O-O')).length})`);
  // promotions
  const promo = inSet('promo');
  const byPiece = (p) => promo.filter((x) => x.san.includes('=' + p));
  console.log(`promotion moves (test, all plies; n=${promo.length}: =Q ${byPiece('Q').length}, =N ${byPiece('N').length}, =R ${byPiece('R').length}, =B ${byPiece('B').length}):`);
  for (const [lab, set] of [['all', promo], ['=Q', byPiece('Q')], ['=N', byPiece('N')], ['=R', byPiece('R')], ['=B', byPiece('B')]]) {
    if (!set.length) continue;
    const km = set.reduce((s, x) => s + get(x, RATINGS.indexOf(matchedNet(x.rating)), 0), 0);
    const ka = set.reduce((s, x) => s + get(x, RATINGS.indexOf(matchedNet(x.rating)), 6), 0);
    console.log(`  ${padr(lab, 4)} n=${pad(set.length, 4)}  matched net top-1 ${fmtAcc(km, set.length)} | control (queen<->knight planes swapped) ${fmtAcc(ka, set.length)} | mean p(played) ${mean(set.map((x) => get(x, RATINGS.indexOf(matchedNet(x.rating)), 1))).toFixed(3)}`);
  }
  {
    const kM = (x) => RATINGS.indexOf(matchedNet(x.rating));
    const nN = byPiece('N'), nQ = byPiece('Q');
    const mN = nN.length ? mean(nN.map((x) => get(x, kM(x), 8))) : NaN, mQn = mean(nQ.map((x) => get(x, kM(x), 8)));
    const rankN = nN.map((x) => get(x, kM(x), 2)).sort((a, b) => a - b);
    console.log(`  knight promotion = bare queen-move plane: p(knight promotion) where =N was played ${mN.toFixed(4)} (n=${nN.length}, median rank ${rankN.length ? rankN[Math.floor(rankN.length / 2)] : '-'}) vs p(knight promotion, same squares) where =Q was played ${mQn.toFixed(4)} (n=${nQ.length}); p(queen promotion) where =N was played ${nN.length ? mean(nN.map((x) => get(x, kM(x), 9))).toFixed(4) : '-'}`);
    results.step2.knight = { nN: nN.length, pKnightWhereN: mN, pKnightWhereQ: mQn };
  }
  results.step2.castle = { n: castle.length, used: RATINGS.map((_, k) => mean(castle.map((x) => get(x, k, 0)))), alt: RATINGS.map((_, k) => mean(castle.map((x) => get(x, k, 6)))), matched: castleMatched };
  results.step2.promo = { n: promo.length, q: byPiece('Q').length, n_: byPiece('N').length, r: byPiece('R').length, b: byPiece('B').length };

  // selection bias: puzzle trigger moves and Lichess judgments
  const trig = inSet('trigger');
  const trigM = trig.reduce((s, x) => s + get(x, RATINGS.indexOf(matchedNet(x.rating)), 0), 0);
  const mainNoTrig = main.filter((x) => !(games[x.g].pzPly - 1 === x.ply));
  const mainNoTrigM = mainNoTrig.reduce((s, x) => s + get(x, RATINGS.indexOf(matchedNet(x.rating)), 0), 0);
  console.log(`\nselection bias (every game produced a puzzle):`);
  console.log(`  puzzle-trigger moves (the error that created the puzzle, n=${trig.length}): matched-net top-1 ${fmtAcc(trigM, trig.length)}; mean p(played) ${mean(trig.map((x) => get(x, RATINGS.indexOf(matchedNet(x.rating)), 1))).toFixed(3)}`);
  console.log(`  main sample without trigger moves (n=${mainNoTrig.length}): ${fmtAcc(mainNoTrigM, mainNoTrig.length)}; trigger moves are ${(100 * (main.length - mainNoTrig.length) / main.length).toFixed(2)}% of the main sample`);
  for (const j of ['', 'Inaccuracy', 'Mistake', 'Blunder']) {
    const s = main.filter((x) => x.judg === j);
    const k = s.reduce((a, x) => a + get(x, RATINGS.indexOf(matchedNet(x.rating)), 0), 0);
    console.log(`  Lichess judgment "${j || 'none'}": n=${s.length} (${(100 * s.length / main.length).toFixed(1)}% of main), matched-net top-1 ${fmtAcc(k, s.length)}`);
  }
  for (const [lo, hi] of [[0, 10], [10, 30], [30, 60], [60, 1e9]]) {
    const s = main.filter((x) => x.clk !== null && x.clk >= lo && x.clk < hi);
    const k = s.reduce((a, x) => a + get(x, RATINGS.indexOf(matchedNet(x.rating)), 0), 0);
    console.log(`  mover's clock before the move ${lo}-${hi >= 1e9 ? 'inf' : hi} s: n=${s.length}, matched-net top-1 ${fmtAcc(k, s.length)}`);
  }
  console.log(`  (no clock data: ${main.filter((x) => x.clk === null).length} positions)`);
  const gl = testGames.map((gi) => games[gi]);
  const draws = gl.filter((g) => !g.winner).length;
  console.log(`  test games: ${gl.length}, draws ${(100 * draws / gl.length).toFixed(1)}%, mean length ${mean(gl.map((g) => g.san.length)).toFixed(1)} plies`);
  results.step2.selection = { trigger: { n: trig.length, hits: trigM }, mainNoTrigger: { n: mainNoTrig.length, hits: mainNoTrigM }, drawRate: draws / gl.length };

  // openings with both history-fill modes
  const op0 = inSet('opening', 'fen_only'), op1 = inSet('opening', 'always');
  console.log(`\nopening plies 0-9 (n=${op0.length}), top-1 by net, history fill "fen_only" (zeros, lc0 default; used) vs "always" (copies of the start position):`);
  console.log('  fen_only: ' + RATINGS.map((r, k) => `${r} ${pct(mean(op0.map((x) => get(x, k, 0))))}`).join('  '));
  console.log('  always:   ' + RATINGS.map((r, k) => `${r} ${pct(mean(op1.map((x) => get(x, k, 0))))}`).join('  '));
  console.log('  mean log-likelihood of played move, fen_only / always: ' + RATINGS.map((r, k) => `${r} ${mean(op0.map((x) => get(x, k, TOFF + 3))).toFixed(3)}/${mean(op1.map((x) => get(x, k, TOFF + 3))).toFixed(3)}`).join('  '));
  results.step2.opening = { n: op0.length, fenOnly: RATINGS.map((_, k) => mean(op0.map((x) => get(x, k, 0)))), always: RATINGS.map((_, k) => mean(op1.map((x) => get(x, k, 0)))) };

  // ---------------------------------------------------------------- step 3: value head
  console.log('\n## 3. Value head: expected score es = W + D/2 (side to move) vs final result; Brier score (lower = better)');
  const dev = inSet('dev');
  const brier = (rows, f) => mean(rows.map((r) => (f(r) - r.outcome) ** 2));
  const devConst = mean(dev.map((r) => r.outcome));
  const devCp = dev.filter((r) => r.cp !== null);
  let bestS = 0, bestB = Infinity;
  for (let s = 50; s <= 1500; s += 10) { const b = brier(devCp, (r) => 1 / (1 + Math.exp(-r.cp / s))); if (b < bestB) { bestB = b; bestS = s; } }
  console.log(`baselines: constant 0.5; constant ${devConst.toFixed(4)} (dev mean outcome); Lichess/Stockfish eval logistic 1/(1+exp(-cp/${bestS})) (scale fitted on dev, n=${devCp.length})`);
  console.log(padr('mover band', 11) + pad('n', 6) + pad('net', 6) + pad('Brier net', 11) + pad('B(0.5)', 9) + pad('B(dev c)', 10) + pad('skill', 8) + pad('n(cp)', 7) + pad('B net', 8) + pad('B eval', 8) + pad('mean es', 9) + pad('mean z', 8) + pad('mean D', 8) + pad('draws', 7));
  const vrows = [];
  for (let b = 0; b <= BANDS.length; b++) {
    const rows = b < BANDS.length ? main.filter((r) => r.band === b) : main;
    if (!rows.length) continue;
    const kOf = (r) => RATINGS.indexOf(matchedNet(r.rating));
    const es = (r) => get(r, kOf(r), 3) + 0.5 * get(r, kOf(r), 4);
    const bn = brier(rows, es), b5 = brier(rows, () => 0.5), bc = brier(rows, () => devConst);
    const rc = rows.filter((r) => r.cp !== null);
    const bnc = brier(rc, es), be = brier(rc, (r) => 1 / (1 + Math.exp(-r.cp / bestS)));
    const lab = b < BANDS.length ? BANDS[b] : 'all';
    vrows.push({ band: lab, n: rows.length, brierNet: bn, brierHalf: b5, brierDevConst: bc, skill: 1 - bn / b5, nCp: rc.length, brierNetCp: bnc, brierEval: be });
    console.log(padr(lab, 11) + pad(rows.length, 6) + pad(b < BANDS.length ? (b === 0 ? 1100 : b === 12 ? 1900 : Math.min(1900, Math.max(1100, 900 + 100 * b))) : 'match', 6) + pad(bn.toFixed(4), 11) + pad(b5.toFixed(4), 9) + pad(bc.toFixed(4), 10) + pad(pct(1 - bn / b5), 8) + pad(rc.length, 7) + pad(bnc.toFixed(4), 8) + pad(be.toFixed(4), 8) +
      pad(mean(rows.map(es)).toFixed(3), 9) + pad(mean(rows.map((r) => r.outcome)).toFixed(3), 8) + pad(mean(rows.map((r) => get(r, kOf(r), 4))).toFixed(3), 8) + pad(pct(mean(rows.map((r) => (r.outcome === 0.5 ? 1 : 0)))), 7));
  }
  console.log('Brier by net, all bands pooled: ' + RATINGS.map((r, k) => `${r} ${brier(main, (x) => get(x, k, 3) + 0.5 * get(x, k, 4)).toFixed(4)}`).join('  '));
  const kOfAll = (r) => RATINGS.indexOf(matchedNet(r.rating));
  const calib = [];
  for (let i = 0; i < 10; i++) {
    const rows = main.filter((r) => { const e = get(r, kOfAll(r), 3) + 0.5 * get(r, kOfAll(r), 4); return e >= i / 10 && (e < (i + 1) / 10 || i === 9); });
    calib.push(`${(i / 10).toFixed(1)}-${((i + 1) / 10).toFixed(1)}: n=${rows.length} es ${rows.length ? mean(rows.map((r) => get(r, kOfAll(r), 3) + 0.5 * get(r, kOfAll(r), 4))).toFixed(3) : '-'} result ${rows.length ? mean(rows.map((r) => r.outcome)).toFixed(3) : '-'}`);
  }
  console.log('calibration (matched net, main sample), es bin: mean es vs mean result\n  ' + calib.join('\n  '));
  results.step3 = { devConst, evalScale: bestS, rows: vrows };

  // temperature (emulating other ratings)
  console.log('\n### Temperature: p_T ~ p^(1/T); T fitted per band on the DEV split (max mean log-likelihood of the played move), reported on TEST');
  console.log(padr('mover band', 11) + pad('net', 6) + pad('T*(dev)', 9) + pad('LL T=1', 9) + pad('LL T*', 9) + pad('p(played) T=1', 15) + pad('p(played) T*', 14) + pad('top-1', 8));
  const trows = [];
  for (const [b, nr] of [[0, 1100], [1, 1100], [2, 1100], [3, 1200], [6, 1500], [10, 1900], [11, 1900], [12, 1900], [0, 1500], [0, 1900]]) {
    const k = RATINGS.indexOf(nr);
    const dv = dev.filter((r) => r.band === b), ts = main.filter((r) => r.band === b);
    if (!dv.length || !ts.length) continue;
    const llDev = TGRID.map((_, t) => mean(dv.map((r) => get(r, k, TOFF + t))));
    const tb = llDev.indexOf(Math.max(...llDev));
    const ll = (t) => mean(ts.map((r) => get(r, k, TOFF + t))), pp = (t) => mean(ts.map((r) => get(r, k, TOFF + TGRID.length + t)));
    const t1i = TGRID.indexOf(1.0);
    trows.push({ band: BANDS[b], net: nr, Tdev: TGRID[tb], llT1: ll(t1i), llTstar: ll(tb), pT1: pp(t1i), pTstar: pp(tb), top1: mean(ts.map((r) => get(r, k, 0))) });
    console.log(padr(BANDS[b], 11) + pad(nr, 6) + pad(TGRID[tb], 9) + pad(ll(t1i).toFixed(4), 9) + pad(ll(tb).toFixed(4), 9) + pad(pct(pp(t1i)), 15) + pad(pct(pp(tb)), 14) + pad(pct(mean(ts.map((r) => get(r, k, 0)))), 8));
  }
  results.temperature = { grid: TGRID, rows: trows };

  const ucache = new Map();
  const uciOf = (gi) => {
    if (!ucache.has(gi)) { const c = new Chess(); ucache.set(gi, games[gi].san.map((x) => { const m = c.move(x); return m ? m.from + m.to + (m.promotion || '') : null; })); }
    return ucache.get(gi);
  };

  // ---------------------------------------------------------------- encoding ablations (matched net)
  {
    const nAb = +arg('ablation', quick ? 60 : 3000);
    const { movePlane } = MaiaNet._internal;
        // one matched-net evaluation with the shipped encoding and with the rule-50 plane divided by 99
    const run = (r) => {
      const net = nets[RATINGS.indexOf(matchedNet(r.rating))], u = uciOf(r.g), played = u[r.ply];
      const res = net.evaluate(START, u.slice(0, r.ply));
      const g = net.cache.game, legal = g.moves({ verbose: true }), black = r.ply % 2 === 1;
      const X = new Float32Array(net.encode(net.cache));
      for (let i = 109 * 64; i < 110 * 64; i++) X[i] /= 99;
      net.forwardPlanes(X);
      const z = legal.map((m) => { const mp = movePlane(m, black); return net.policyLogit(mp.plane, mp.sq); });
      const mx = Math.max(...z), lse = mx + Math.log(z.reduce((a, b) => a + Math.exp(b - mx), 0));
      const pi = legal.findIndex((m) => m.from + m.to + (m.promotion || '') === played);
      const pShip = (res.policy.find((m) => m.uci === played) || { p: 1e-300 }).p;
      return { net, played, fen: g.fen(), used: res.policy[0].uci === played, r99: z.indexOf(mx) === pi,
        llUsed: Math.log(pShip), ll99: z[pi] - lse };
    };
    const abl = shuffle(main.slice(), rnd).slice(0, nAb);
    const cnt = { used: 0, fenFill: 0, fenZero: 0 };
    for (const r of abl) {
      const x = run(r);
      cnt.used += x.used;
      cnt.fenFill += x.net.evaluate(x.fen, [], { historyFill: 'fen_only' }).policy[0].uci === x.played;
      cnt.fenZero += x.net.evaluate(x.fen, [], { historyFill: 'no' }).policy[0].uci === x.played;
    }
    const hmAll = [];
    for (const gi of testGames) {
      const g = games[gi];
      let hm = 0;
      for (let i = 0; i < g.san.length; i++) {
        if (i >= 10 && hm >= 20) hmAll.push({ g: gi, ply: i, rating: i % 2 === 0 ? g.wr : g.br });
        hm = /x|^[a-h]/.test(g.san[i]) ? 0 : hm + 1;
      }
    }
    const hmSet = shuffle(hmAll, rnd).slice(0, Math.ceil(nAb / 2));
    const h = { n: hmSet.length, used: 0, r99: 0, llUsed: 0, ll99: 0 };
    for (const r of hmSet) { const x = run(r); h.used += x.used; h.r99 += x.r99; h.llUsed += x.llUsed / hmSet.length; h.ll99 += x.ll99 / hmSet.length; }
    console.log(`\n### Encoding ablations (matched net)`);
    console.log(`  ${abl.length} random main-sample positions: shipped encoding (full game history) ${fmtAcc(cnt.used, abl.length)}; ` +
      `FEN only with history = copies of the position (lc0 fen_only, maia.js default for a non-start FEN) ${fmtAcc(cnt.fenFill, abl.length)}; FEN only with zero history ${fmtAcc(cnt.fenZero, abl.length)}`);
    console.log(`  ${h.n} test positions (of ${hmAll.length}, plies >= 10) with half-move clock >= 20: rule-50 plane raw (shipped) ${fmtAcc(h.used, h.n)}, mean log-lik ${h.llUsed.toFixed(4)} | rule-50 plane / 99 ${fmtAcc(h.r99, h.n)}, mean log-lik ${h.ll99.toFixed(4)}`);
    results.ablation = { n: abl.length, counts: cnt, rule50: h };
  }

  // ---------------------------------------------------------------- strength of sampled moves (Stockfish)
  if (!arg('no-sf', false)) {
    const sfDepth = +arg('sf-depth', 14), perB = +arg('strength-per-band', quick ? 12 : 250);
    const { Pool } = await import(pathToFileURL(path.join(ROOT, 'tools/sfpool.mjs')).href);
    console.log(`\n### Move quality (Stockfish 17.1 depth ${sfDepth}, same positions): played human move vs Maia argmax / samples at temperature T`);
    const sbands = [0, 6, 8, 10, 12];
    const pick = [];
    for (const b of sbands) shuffle(main.filter((r) => r.band === b), rnd).slice(0, perB).forEach((r) => pick.push(r));
    const trio = [1100, 1500, 1900].map((r) => nets[RATINGS.indexOf(r)]);
    const modes = [['am', 0], ['T1', 1], ['T1.5', 1.5], ['T2', 2]];
    const srnd = rng32(777);
    const items = pick.map((r) => {
      const u = uciOf(r.g);
      const res = MaiaNet.evaluateMany(trio, START, u.slice(0, r.ply));
      const fen = trio[0].cache.game.fen();
      const choice = {};
      res.forEach((x, k) => modes.forEach(([lab, T]) => { choice[`${[1100, 1500, 1900][k]}:${lab}`] = T === 0 ? x.policy[0].uci : MaiaNet.sample(x.policy, T, srnd).uci; }));
      return { r, fen, human: u[r.ply], choice };
    });
    const pool = new Pool(2);
    const clampCp = (l) => Math.max(-1000, Math.min(1000, l.mate != null ? (l.mate > 0 ? 1000 : -1000) : l.cp));
    const esOf = (l) => (l.wdl ? (l.wdl[0] + 0.5 * l.wdl[1]) / 1000 : 1 / (1 + Math.exp(-clampCp(l) / 250)));
    const tS = Date.now();
    await Promise.all(items.map(async (it) => {
      const cands = [...new Set([it.human, ...Object.values(it.choice)])];
      const [a, b] = await Promise.all([pool.analyse(it.fen, { depth: sfDepth }), pool.analyse(it.fen, { depth: sfDepth, multipv: cands.length, searchmoves: cands })]);
      const sc = new Map(b.lines.map((l) => [l.pv[0], l]));
      const bestCp = Math.max(clampCp(a.lines[0]), ...b.lines.map(clampCp)), bestEs = Math.max(esOf(a.lines[0]), ...b.lines.map(esOf));
      it.loss = {};
      for (const m of cands) {
        const l = sc.get(m);
        it.loss[m] = l ? { cpl: Math.max(0, bestCp - clampCp(l)), esl: Math.max(0, bestEs - esOf(l)) } : null;
      }
    }));
    pool.close();
    const cols = ['human', ...[1100, 1500, 1900].flatMap((n) => modes.map(([lab]) => `${n}:${lab}`))];
    const val = (it, c) => it.loss[c === 'human' ? it.human : it.choice[c]];
    console.log(`(${items.length} positions, ${((Date.now() - tS) / 1000).toFixed(0)} s; cp loss clamped to [0,1000]; blunder = cp loss >= 300; columns maia-<rating>:<am = argmax | T = temperature sample>)`);
    const strength = {};
    for (const [metric, f, fmt] of [['mean cp loss', (l) => l.cpl, (x) => x.toFixed(0)], ['blunder rate %', (l) => (l.cpl >= 300 ? 1 : 0), (x) => (100 * x).toFixed(1)], ['mean expected-score loss (pp)', (l) => l.esl, (x) => (100 * x).toFixed(1)]]) {
      console.log(metric);
      console.log(padr('band', 11) + pad('n', 5) + cols.map((c) => pad(c.replace('human', 'human'), 11)).join(''));
      for (const b of [...sbands, -1]) {
        const its = items.filter((it) => (b < 0 ? true : it.r.band === b));
        if (!its.length) continue;
        const row = cols.map((c) => { const v = its.map((it) => val(it, c)).filter(Boolean).map(f); return v.length ? mean(v) : NaN; });
        (strength[metric] = strength[metric] || {})[b < 0 ? 'all' : BANDS[b]] = { n: its.length, values: Object.fromEntries(cols.map((c, i) => [c, row[i]])) };
        console.log(padr(b < 0 ? 'all' : BANDS[b], 11) + pad(its.length, 5) + row.map((x) => pad(fmt(x), 11)).join(''));
      }
    }
    const missing = items.reduce((s, it) => s + Object.values(it.loss).filter((x) => !x).length, 0);
    console.log(`(moves without a searchmoves score: ${missing})`);
    results.strength = { depth: sfDepth, positions: items.length, table: strength };
  }

  // ---------------------------------------------------------------- step 4: speed and sizes
  console.log('\n## 4. Speed (Node, single thread, this machine; other jobs may share the 4 CPUs) and sizes');
  const tl = [];
  for (const r of RATINGS) { const t = process.hrtime.bigint(); MaiaNet.load(fs.readFileSync(path.join(ENG, man.files[r].file)), man); tl.push(Number(process.hrtime.bigint() - t) / 1e6); }
  const net = nets[RATINGS.indexOf(1500)];
  const sg = shuffle(testGames.slice(), rnd).slice(0, quick ? 3 : 12).map((gi) => {
    const c = new Chess(); return games[gi].san.map((s) => { const m = c.move(s); return m ? m.from + m.to + (m.promotion || '') : null; }).filter(Boolean);
  });
  for (let i = 0; i < 30; i++) net.evaluate(START, sg[0].slice(0, i));   // warm-up / JIT
  const warm = [], cold = [], fwd = [];
  for (const g of sg) for (let i = 0; i < g.length; i++) { const r = net.evaluate(START, g.slice(0, i)); if (r.policy.length) warm.push(r.ms); }
  for (const g of sg) for (let i = 10; i < g.length; i += 7) { net.cache = null; const r = net.evaluate(START, g.slice(0, i)); if (r.policy.length) cold.push(r.ms); }
  const X = new Float32Array(net.X);
  for (let i = 0; i < 200; i++) { const t = process.hrtime.bigint(); net.forwardPlanes(X); fwd.push(Number(process.hrtime.bigint() - t) / 1e6); }
  const q = (a, p) => { const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; };
  const sp = { loadMs: mean(tl), warm: { n: warm.length, mean: mean(warm), p50: q(warm, 0.5), p95: q(warm, 0.95) }, cold: { n: cold.length, mean: mean(cold), p50: q(cold, 0.5), p95: q(cold, 0.95) }, forward: { n: fwd.length, mean: mean(fwd), p50: q(fwd, 0.5) } };
  console.log(`load + Winograd weight transform: mean ${sp.loadMs.toFixed(1)} ms per net`);
  console.log(`evaluate(), history grows by one ply per call (game play): n=${sp.warm.n} mean ${sp.warm.mean.toFixed(2)} ms, median ${sp.warm.p50.toFixed(2)}, p95 ${sp.warm.p95.toFixed(2)}`);
  console.log(`evaluate(), cold (history cache cleared, full replay of 10-${Math.max(...sg.map((g) => g.length))} plies): n=${sp.cold.n} mean ${sp.cold.mean.toFixed(2)} ms, median ${sp.cold.p50.toFixed(2)}, p95 ${sp.cold.p95.toFixed(2)}`);
  console.log(`network forward pass only: mean ${sp.forward.mean.toFixed(2)} ms, median ${sp.forward.p50.toFixed(2)}`);
  const sizes = {};
  for (const f of [...RATINGS.map((r) => man.files[r].file), 'manifest.json', 'maia.js', 'worker.js']) {
    const b = fs.readFileSync(path.join(ENG, f));
    sizes[f] = { bytes: b.length, gzip: zlib.gzipSync(b, { level: 9 }).length };
  }
  const totalBin = RATINGS.reduce((s, r) => s + sizes[man.files[r].file].bytes, 0);
  console.log(`files: each maia-<r>.bin ${sizes[man.files[1100].file].bytes} bytes (${man.dtype}; gzip -9 ~${sizes[man.files[1100].file].gzip}), all 9: ${totalBin} bytes (${(totalBin / 1048576).toFixed(2)} MiB); manifest.json ${sizes['manifest.json'].bytes}; maia.js ${sizes['maia.js'].bytes}; worker.js ${sizes['worker.js'].bytes}`);
  results.speed = sp; results.sizes = sizes;

  results.elapsedSec = (Date.now() - t00) / 1000;
  fs.writeFileSync(outFile, JSON.stringify(results, null, 1));
  console.log(`\nresults written to ${outFile}; total ${results.elapsedSec.toFixed(0)} s`);
  fs.rmSync(tmp, { recursive: true, force: true });
}

if (isMainThread) main().catch((e) => { console.error(e); process.exit(1); });
