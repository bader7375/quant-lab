// Checks that js/prob.js, fed data/models/odds.json, reproduces the Python predictions of tools/odds/fit_odds.py.
// Usage: node tools/odds/check_prob.mjs [path/to/odds.json]     -> prints PASS or FAIL (exit code 1 on FAIL)
// js/prob.js is a browser script (top-level `const Prob`); it runs here in a Node vm context with a fake fetch.
import fs from 'fs';
import path from 'path';
import vm from 'vm';

const root = path.join(path.dirname(new URL(import.meta.url).pathname), '..', '..');   // chess-coach/
const oddsPath = process.argv[2] ? path.resolve(process.argv[2]) : path.join(root, 'data/models/odds.json');
const TOL = 1e-9;
let fails = 0, checks = 0;
const fail = (msg) => { fails++; console.log('  FAIL ' + msg); };
const ok = (cond, msg) => { checks++; if (!cond) fail(msg); };

// ---------------------------------------------------------------- static checks of odds.json
const raw = fs.readFileSync(oddsPath, 'utf8');
const M = JSON.parse(raw);
console.log(`odds.json: ${oddsPath} (${raw.length} bytes)`);
ok(raw.length < 50 * 1024, `size ${raw.length} >= 50 KB`);
ok(M.kind === 'ordered-logit', `kind is ${M.kind}`);
ok(Number.isFinite(M.clip) && M.clip > 0, 'clip');
ok(M.bands && M.bands[M.defaultBand], 'defaultBand present in bands');
for (const [k, b] of Object.entries(M.bands)) {
  for (const p of [b, ...Object.values(b.phases || {})]) {
    ok(['a', 't1', 't2'].every((f) => Number.isFinite(p[f])), `band ${k}: finite a,t1,t2`);
    ok(p.a > 0 && p.t1 < p.t2, `band ${k}: a > 0 and t1 < t2 (a=${p.a}, t1=${p.t1}, t2=${p.t2})`);
  }
}

// ---------------------------------------------------------------- load js/prob.js in a vm with a fake fetch
const src = fs.readFileSync(path.join(root, 'js/prob.js'), 'utf8');
const fetched = [];
const ctx = vm.createContext({
  console, Math, JSON,
  fetch: async (url) => { fetched.push(url); const p = path.join(root, url); return { ok: url === 'data/models/odds.json', json: async () => JSON.parse(fs.readFileSync(url === 'data/models/odds.json' ? oddsPath : p, 'utf8')) }; },
});
vm.runInContext(src, ctx, { filename: 'js/prob.js' });
const Prob = vm.runInContext('Prob', ctx);
ok(Prob.model.kind === 'provisional', 'model is provisional before load()');
await Prob.load();
ok(fetched.length === 1 && fetched[0] === 'data/models/odds.json', `fetched ${JSON.stringify(fetched)}`);
ok(Prob.model.kind === 'ordered-logit', `model after load(): ${Prob.model.kind}`);

// ---------------------------------------------------------------- Python mirror (phase-aware, mate-in-n = +-clip)
// This is the exact function body proposed for js/prob.js; it is verified here against the Python mirror.
function nearestBand(Mo, band) { const ks = Object.keys(Mo.bands || {}).map(Number); return ks.sort((a, b) => Math.abs(a - band) - Math.abs(b - band))[0]; }
function humanProposed(Mo, cpWhite, ctx = {}) {
  if (cpWhite == null) return [0.5, 0, 0.5];
  if (Mo.kind === 'ordered-logit') {
    if (Math.abs(cpWhite) >= 10000) return cpWhite > 0 ? [1, 0, 0] : [0, 0, 1];   // checkmate on the board: the game is over
    const band = ctx.band || Mo.defaultBand; const b0 = (Mo.bands && (Mo.bands[band] || Mo.bands[nearestBand(Mo, band)])) || Mo;
    const b = (ctx.phase && b0.phases && b0.phases[ctx.phase]) || b0;      // ctx.phase: Facts.phaseOf(...) = "opening" | "middlegame" | "endgame"
    const cp = Math.max(-Mo.clip, Math.min(Mo.clip, cpWhite));              // mate-in-n (|cp| >= 9000) counts as +-clip, as fitted
    const z = b.a * cp / 100 + (b.c || 0);
    const s = (x) => 1 / (1 + Math.exp(-x));
    const pl = s(b.t1 - z), pw = 1 - s(b.t2 - z); const pd = Math.max(0, 1 - pl - pw);
    return [pw, pd, pl];
  }
  return null;
}
// ---------------------------------------------------------------- the shipped Prob.human vs the Python mirror
// js/prob.js implements the phase-aware rule: mate-in-n (|cp| >= 9000) counts as +-clip, checkmate on the board (|cp| >= 10000)
// is certain. The Python "proposed" points (with phases) and the phase-less points (band only) must both be reproduced.
const pts = (M.meta && M.meta.check_points && M.meta.check_points.points) || [];
ok(pts.length >= 30, `only ${pts.length} check points`);
let maxErr = 0;
const bandsSeen = new Set(), signs = new Set();
for (const [cp, band, w0, d0, l0] of pts) {
  const exp = humanProposed(M, cp, band == null ? {} : { band }); // phase-less expectation under the adopted mate rule
  const got = Prob.human(cp, band == null ? {} : { band });
  const err = Math.max(Math.abs(got[0] - exp[0]), Math.abs(got[1] - exp[1]), Math.abs(got[2] - exp[2]));
  if (Math.abs(cp) < 9000) ok(Math.max(Math.abs(exp[0] - w0), Math.abs(exp[1] - d0), Math.abs(exp[2] - l0)) <= TOL, `mirror vs python at (${cp}, ${band})`);
  maxErr = Math.max(maxErr, err); bandsSeen.add(band); signs.add(Math.sign(cp));
  ok(err <= TOL, `Prob.human(${cp}, ${band}) = ${got.map((x) => x.toFixed(12))} expected ${exp.map((x) => x.toFixed(12))} (err ${err.toExponential(2)})`);
  ok(Math.abs(got[0] + got[1] + got[2] - 1) < 1e-12 && got.every((x) => x >= 0), `probabilities of (${cp}, ${band}) sum to 1`);
}
ok(bandsSeen.size >= 5 && signs.has(1) && signs.has(-1) && signs.has(0), 'coverage of bands and signs');
ok(pts.some(([cp]) => Math.abs(cp) >= 9000) && pts.some(([cp]) => Math.abs(cp) > M.clip && Math.abs(cp) < 9000), 'coverage of mate and beyond-clip points');
console.log(`Prob.human (js/prob.js), phase-less points: ${pts.length}, max abs error ${maxErr.toExponential(2)}`);
// expected-score helpers agree with human()
const es0 = Prob.esFor(150, 'w', { band: 1500 }), h = Prob.human(150, { band: 1500 });
ok(Math.abs(es0 - 100 * (h[0] + h[1] / 2)) < 1e-12 && Math.abs(Prob.esFor(150, 'b', { band: 1500 }) - (100 - es0)) < 1e-12, 'esFor consistent with human');

const pp = (M.meta && M.meta.check_points && M.meta.check_points.proposed_points) || [];
let maxErr2 = 0;
for (const [cp, band, phase, w, d, l] of pp) {
  const c = {}; if (band != null) c.band = band; if (phase != null) c.phase = phase;
  const got = humanProposed(M, cp, c), shipped = Prob.human(cp, c);
  const err = Math.max(Math.abs(got[0] - w), Math.abs(got[1] - d), Math.abs(got[2] - l), ...shipped.map((x, i) => Math.abs(x - [w, d, l][i])));
  maxErr2 = Math.max(maxErr2, err);
  ok(err <= TOL, `human(${cp}, ${band}, ${phase}) = ${shipped} expected ${[w, d, l]} (err ${err.toExponential(2)})`);
}
if (pp.length) console.log(`Prob.human (js/prob.js) with phases: ${pp.length} points, max abs error ${maxErr2.toExponential(2)}`);

console.log(`${checks} checks, ${fails} failed`);
console.log(fails ? 'FAIL' : 'PASS');
process.exit(fails ? 1 : 0);
