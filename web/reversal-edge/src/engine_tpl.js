/* QuantLab Reversal Edge engine, browser edition (runs in a Web Worker).
 *
 * Signal = short-term oversold trigger (RSI(2)) x Reversal Edge Score: nine reversal signs whose
 * direction is fixed by out-of-sample evidence (87 US stocks 2013-2017 + TSLA 2011-2026) and whose
 * weights start from that research and adapt to each uploaded stock, walk-forward.
 * Exit: first close back above the 5-day average, a 3-ATR stop, or 10 bars.
 * Also: adaptive z-zones from each stock's own history, a professional volatility suite
 * (close-close, Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang, GARCH(1,1), HAR),
 * and the earlier fair-value means and stationarity statistics for context.
 * Every value at bar t uses bars <= t only; outcome arrays (y, tret, touch, fwd5) are labelled as hindsight.
 */
"use strict";
const NaN_ = NaN, isF = Number.isFinite;
let CACHE = { key: null, model: null };

self.onmessage = (e) => {
  const { cmd, datasets, cfg, fear } = e.data;
  if (cmd !== "run") return;
  try {
    const res = run(datasets, cfg, fear);
    self.postMessage({ type: "result", res });
  } catch (err) {
    self.postMessage({ type: "error", message: String(err && err.stack || err) });
  }
};
const progress = (frac, msg) => self.postMessage({ type: "progress", frac, msg });

{{OLD_HELPERS_MEANS_STATS}}

// ------------------------------------------------------------ research prior (87 US stocks 2013-2017, RSI(2)<10 setups)
const PRIOR = {{PRIOR_JSON}};
// key, label, family, meaning, research evidence: avg-trade difference top vs bottom third (bp) in [87 stocks, TSLA 2011-17, TSLA 2018-26]
const SIGNS = [
  ["rel_volume", "Relative volume", "volume", "Volume versus its 60-day normal. Heavy selling volume marks forced sellers; the bounce tends to be larger.", [31, 64, 19]],
  ["range_expansion", "Range expansion", "volume", "Today's true range versus the average range (ATR). A wide-range down day is a capitulation sign.", [19, 103, 48]],
  ["vol_rank", "Volatility rank", "volatility", "Yang-Zhang 20-day volatility as a percentile of this stock's last two years.", [12, 86, 204]],
  ["vol_term", "Volatility rising", "volatility", "5-day volatility versus 60-day volatility. Rising short-term volatility means stress, when liquidity providers earn the most.", [42, 59, 21]],
  ["fear_rank", "Market fear (VIX)", "fear", "VIX as a percentile of its last two years. Reversals pay more when the market is afraid (Nagel 2012).", [40, 1, 133]],
  ["down_streak", "Down streak", "oversold", "Consecutive lower closes.", [26, 42, 39]],
  ["drop1_atr", "One-day drop", "oversold", "Today's fall measured in ATRs.", [10, 4, 69]],
  ["gap_size", "News-like gap", "news", "Size of the opening gap in ATRs. Big gaps usually mean news; news moves tend to drift, not revert (Chan 2003). Counts against the trade.", [-24, -46, -31]],
  ["lower_wick", "Lower wick", "candle", "Share of the day's range below the body. A long wick means the bounce already happened intraday. Counts against the trade.", [-24, -17, -19]],
];
const SKEYS = SIGNS.map((s) => s[0]);
const NEG = new Set(PRIOR.neg);
const sigm = (s) => 1 / (1 + Math.exp(-s));

// ------------------------------------------------------------ rolling helpers
function rollRankPct(x, W, minP) { // pandas rolling(W, min_periods=minP).rank(pct=True), average ties
  const n = x.length, out = nanArr(n);
  for (let t = 0; t < n; t++) {
    const v = x[t]; if (!isF(v)) continue;
    let less = 0, eq = 0, cnt = 0;
    for (let k = Math.max(0, t - W + 1); k <= t; k++) { const u = x[k]; if (!isF(u)) continue; cnt++; if (u < v) less++; else if (u === v) eq++; }
    if (cnt >= minP) out[t] = (less + (eq + 1) / 2) / cnt;
  }
  return out;
}
function rollMean(x, W) { // NaN unless all W values finite (pandas default)
  const n = x.length, out = nanArr(n); let s = 0, c = 0;
  for (let t = 0; t < n; t++) { if (isF(x[t])) { s += x[t]; c++; } if (t >= W && isF(x[t - W])) { s -= x[t - W]; c--; } if (t >= W - 1 && c === W) out[t] = s / W; }
  return out;
}
function rollVar(x, W) { const [, s] = rollMeanStd(x, W); return s.map((v) => v * v); }
function wilderRSI(c, n) { // pandas ewm(alpha=1/n, adjust=False) on gains and losses
  const out = nanArr(c.length); let up = NaN_, dn = NaN_;
  for (let t = 1; t < c.length; t++) {
    const d = c[t] - c[t - 1], u = Math.max(d, 0), w = Math.max(-d, 0);
    up = isF(up) ? up + (u - up) / n : u; dn = isF(dn) ? dn + (w - dn) / n : w;
    out[t] = dn === 0 ? NaN_ : 100 - 100 / (1 + up / dn);
  }
  return out;
}
function quantSorted(a, q) { if (!a.length) return NaN_; const p = q * (a.length - 1), i = Math.floor(p), f = p - i; return i + 1 < a.length ? a[i] + f * (a[i + 1] - a[i]) : a[i]; }
function bisect(a, v) { let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >> 1; if (a[m] < v) lo = m + 1; else hi = m; } return lo; }

// ------------------------------------------------------------ volatility models
function garchFit(r) { // GARCH(1,1) by Nelder-Mead on transformed params; r in percent, demeaned
  const n = r.length; let v0 = 0; for (const x of r) v0 += x * x; v0 /= n;
  const unpack = (p) => { const psi = 0.999 * sigm(p[1]), a = psi * sigm(p[2]); return { omega: Math.exp(p[0]), alpha: a, beta: psi - a }; };
  const nll = (p) => { const { omega, alpha, beta } = unpack(p); let s2 = v0, L = 0;
    for (let t = 0; t < n; t++) { if (t) s2 = omega + alpha * r[t - 1] * r[t - 1] + beta * s2; if (!(s2 > 0)) return 1e12; L += Math.log(s2) + r[t] * r[t] / s2; } return 0.5 * L; };
  // start: alpha .08, beta .9, omega = v0*(1-.98)
  let simplex = [[Math.log(v0 * 0.02), 3.9, -2.4]]; for (let i = 0; i < 3; i++) { const p = simplex[0].slice(); p[i] += i === 0 ? 0.5 : 0.6; simplex.push(p); }
  let f = simplex.map(nll);
  for (let it = 0; it < 400; it++) {
    const idx = [0, 1, 2, 3].sort((a, b) => f[a] - f[b]); simplex = idx.map((i) => simplex[i]); f = idx.map((i) => f[i]);
    if (Math.abs(f[3] - f[0]) < 1e-7 * (1 + Math.abs(f[0]))) break;
    const cen = [0, 1, 2].map((k) => (simplex[0][k] + simplex[1][k] + simplex[2][k]) / 3);
    const pt = (t) => cen.map((c, k) => c + t * (simplex[3][k] - c));
    const xr = pt(-1), fr = nll(xr);
    if (fr < f[0]) { const xe = pt(-2), fe = nll(xe); if (fe < fr) { simplex[3] = xe; f[3] = fe; } else { simplex[3] = xr; f[3] = fr; } }
    else if (fr < f[2]) { simplex[3] = xr; f[3] = fr; }
    else { const xc = pt(0.5), fc = nll(xc); if (fc < f[3]) { simplex[3] = xc; f[3] = fc; } else { for (let i = 1; i < 4; i++) { simplex[i] = simplex[i].map((v, k) => simplex[0][k] + 0.5 * (v - simplex[0][k])); f[i] = nll(simplex[i]); } } }
  }
  const best = unpack(simplex[0]); return Object.assign(best, { nll: f[0], n });
}
function volSuite(o, h, l, c) {
  const n = c.length, A = Math.sqrt(252) * 100;
  const lo = o.map(Math.log), lh = h.map(Math.log), ll = l.map(Math.log), lc = c.map(Math.log);
  const r = lc.map((v, i) => i ? v - lc[i - 1] : NaN_);
  const co = lo.map((v, i) => i ? v - lc[i - 1] : NaN_), oc = lc.map((v, i) => v - lo[i]);
  const rs = lc.map((_, i) => (lh[i] - lc[i]) * (lh[i] - lo[i]) + (ll[i] - lc[i]) * (ll[i] - lo[i]));
  const hl2 = lh.map((v, i) => (v - ll[i]) ** 2), gk = hl2.map((v, i) => 0.5 * v - (2 * Math.log(2) - 1) * oc[i] ** 2);
  const yz = (W) => { const k = 0.34 / (1.34 + (W + 1) / (W - 1)), a = rollVar(co, W), b = rollVar(oc, W), m = rollMean(rs, W);
    return a.map((v, i) => isF(v) && isF(b[i]) && isF(m[i]) ? Math.sqrt(Math.max(0, v + k * b[i] + (1 - k) * m[i]) * 252) : NaN_); };
  const V = { r, rv: co.map((v, i) => isF(v) ? v * v + rs[i] : NaN_) };
  V.cc20 = rollMeanStd(r, 20)[1].map((v) => v * A);
  V.park20 = rollMean(hl2, 20).map((v) => Math.sqrt(v / (4 * Math.log(2))) * A);
  V.gk20 = rollMean(gk, 20).map((v) => Math.sqrt(Math.max(v, 0)) * A);
  V.rs20 = rollMean(rs, 20).map((v) => Math.sqrt(Math.max(v, 0)) * A);
  V.yz5f = yz(5); V.yz20f = yz(20); V.yz60f = yz(60);
  V.yz5 = V.yz5f.map((v) => v * 100); V.yz20 = V.yz20f.map((v) => v * 100); V.yz60 = V.yz60f.map((v) => v * 100);
  // GARCH(1,1): refit every 250 bars on the last <= 2500 returns once 500 are available (point in time)
  V.garch = nanArr(n); V.garchSteps = []; let P = null, s2 = NaN_, mu = 0;
  for (let t = 1; t < n; t++) {
    if (t >= 500 && (t - 500) % 250 === 0) {
      const seg = r.slice(Math.max(1, t - 2500), t + 1).filter(isF); mu = seg.reduce((a, b) => a + b, 0) / seg.length;
      const fit = garchFit(seg.map((x) => 100 * (x - mu))); P = fit; const pers = fit.alpha + fit.beta;
      V.garchSteps.push({ i: t, omega: fit.omega, alpha: fit.alpha, beta: fit.beta, pers, half: pers < 1 ? Math.log(0.5) / Math.log(pers) : Infinity, lr: pers < 1 ? Math.sqrt(fit.omega / (1 - pers) * 252) : NaN_, mu });
      if (!isF(s2)) s2 = seg.reduce((a, x) => a + 1e4 * (x - mu) ** 2, 0) / seg.length;
    }
    if (P && isF(r[t])) { s2 = P.omega + P.alpha * (100 * (r[t] - mu)) ** 2 + P.beta * s2; V.garch[t] = Math.sqrt(s2 * 252); } // forecast for t+1, annualised %
  }
  // HAR on an OHLC daily variance proxy (overnight^2 + Rogers-Satchell): 5-day-ahead forecast
  V.har5 = nanArr(n); V.harSteps = []; let hb = null;
  const rvd = V.rv, rvw = rollMean(rvd, 5), rvm = rollMean(rvd, 22), tgt = rvd.map((_, i) => { if (i + 5 >= n) return NaN_; let s = 0; for (let k = 1; k <= 5; k++) s += rvd[i + k]; return s / 5; });
  for (let t = 0; t < n; t++) {
    if (t >= 400 && (t - 400) % 250 === 0) {
      const XtX = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], Xty = [0, 0, 0, 0]; let m = 0;
      for (let i = 22; i + 5 < t; i++) { const x = [1, rvd[i], rvw[i], rvm[i]], y = tgt[i]; if (!x.every(isF) || !isF(y)) continue; m++; for (let a = 0; a < 4; a++) { Xty[a] += x[a] * y; for (let b = 0; b < 4; b++) XtX[a][b] += x[a] * x[b]; } }
      if (m > 100) { for (let a = 1; a < 4; a++) XtX[a][a] *= 1.0001; hb = solve(XtX, Xty); V.harSteps.push({ i: t, b: hb, n: m }); }
    }
    if (hb && isF(rvd[t]) && isF(rvw[t]) && isF(rvm[t])) { const f = hb[0] + hb[1] * rvd[t] + hb[2] * rvw[t] + hb[3] * rvm[t]; V.har5[t] = Math.sqrt(Math.max(f, 1e-10) * 252) * 100; }
  }
  return V;
}

// ------------------------------------------------------------ reversal features (mirrors research/feats.py + prior.py exactly)
function buildRev(ds, fear, cfg) {
  const { o, h, l, c, v } = ds, n = c.length, s = cfg.side;
  const lc = c.map(Math.log);
  const tr = c.map((_, i) => i ? Math.max(h[i] - l[i], Math.abs(h[i] - c[i - 1]), Math.abs(l[i] - c[i - 1])) : h[i] - l[i]);
  const atr = nanArr(n); let a = NaN_; for (let i = 0; i < n; i++) { a = isF(a) ? a + (tr[i] - a) / 14 : tr[i]; atr[i] = a; }
  const R = { atr, tr };
  R.rsi2 = wilderRSI(c, 2); R.rsi14 = wilderRSI(c, 14);
  R.streak = new Array(n).fill(0); for (let i = 1; i < n; i++) { const sg = Math.sign(c[i] - c[i - 1]); R.streak[i] = sg === 0 ? 0 : Math.sign(R.streak[i - 1]) === sg ? R.streak[i - 1] + sg : sg; }
  const rng = h.map((x, i) => x - l[i]);
  R.ibs = c.map((x, i) => rng[i] > 0 ? (x - l[i]) / rng[i] : NaN_);
  R.lwick = c.map((x, i) => rng[i] > 0 ? (Math.min(o[i], x) - l[i]) / rng[i] : NaN_);
  R.uwick = c.map((x, i) => rng[i] > 0 ? (h[i] - Math.max(o[i], x)) / rng[i] : NaN_);
  R.ret1 = c.map((x, i) => i ? (x - c[i - 1]) / atr[i - 1] : NaN_);
  R.gap = o.map((x, i) => i ? (x - c[i - 1]) / atr[i - 1] : NaN_);
  R.rangex = tr.map((x, i) => i ? x / atr[i - 1] : NaN_);
  const lv = v.map((x) => x > 0 ? Math.log(x) : NaN_), [lvm, lvs] = rollMeanStd(lv, 60);
  R.volz = lv.map((x, i) => isF(x) && lvs[i] > 0 ? (x - lvm[i]) / lvs[i] : NaN_);
  const [m20, s20] = rollMeanStd(lc, 20);
  R.m20 = m20; R.s20 = s20; R.z20 = lc.map((x, i) => (x - m20[i]) / s20[i]);
  R.sma5 = rollMean(c, 5);
  const V = volSuite(o, h, l, c); Object.assign(R, V);
  R.vterm = V.yz5f.map((x, i) => Math.log(x / V.yz60f[i]));
  R.vrank = rollRankPct(V.yz20f, 500, 250);
  // fear index aligned to this stock's dates, carried forward at most 7 sessions
  R.vix = nanArr(n);
  if (fear) { let j = 0, last = NaN_, age = 99; for (let i = 0; i < n; i++) { while (j < fear.d.length && fear.d[j] <= ds.d[i]) { last = fear.c[j]; age = fear.d[j] === ds.d[i] ? 0 : 1; j++; } if (fear.d[j - 1] !== ds.d[i]) age++; R.vix[i] = isF(last) && age <= 7 ? last : NaN_; } }
  R.frank = rollRankPct(R.vix, 500, 250);
  // oriented sign values (side +1: long after drops, -1: short after rises)
  const X = {};
  X.rel_volume = R.volz; X.range_expansion = R.rangex; X.vol_rank = R.vrank; X.vol_term = R.vterm; X.fear_rank = R.frank;
  X.down_streak = R.streak.map((x) => Math.max(-10, Math.min(10, -s * x)));
  X.drop1_atr = R.ret1.map((x) => -s * x); X.gap_size = R.gap.map(Math.abs); X.lower_wick = s > 0 ? R.lwick : R.uwick;
  R.X = X;
  R.Z = {}; for (const k of SKEYS) R.Z[k] = X[k].map((x) => { if (!isF(x)) return 0; const xo = NEG.has(k) ? -x : x; return Math.max(-3, Math.min(3, (xo - PRIOR.med[k]) / PRIOR.iqr[k])); });
  R.setup = R.rsi2.map((x) => isF(x) && (s > 0 ? x < cfg.trig : x > 100 - cfg.trig) ? 1 : 0);
  // trade outcome (hindsight): enter next open, exit first close beyond the 5-day average, stop k*ATR, or after maxHold bars
  R.y = nanArr(n); R.tret = nanArr(n); R.thold = nanArr(n); R.texit = new Array(n).fill("");
  const cost = (cfg.slippage * 2) / 1e4;
  for (let t = 0; t < n - 2; t++) {
    if (!isF(atr[t])) continue; const e = o[t + 1], st = e - s * cfg.stopATR * atr[t]; let x = null, j = t + 1, why = "";
    for (; j < Math.min(n, t + 1 + cfg.maxHold); j++) {
      if ((s > 0 && l[j] <= st) || (s < 0 && h[j] >= st)) { x = j > t + 1 ? (s > 0 ? Math.min(o[j], st) : Math.max(o[j], st)) : st; why = "STOP"; break; }
      if ((s > 0 && c[j] > R.sma5[j]) || (s < 0 && c[j] < R.sma5[j])) { x = c[j]; why = "SMA5"; break; }
      if (j === t + cfg.maxHold) { x = c[j]; why = "TIME"; break; }
    }
    if (x == null) continue;
    const rr = s * Math.log(x / e) - cost; R.tret[t] = rr; R.y[t] = rr > 0 ? 1 : 0; R.thold[t] = j - t; R.texit[t] = why;
  }
  // adaptive z-zones: percentiles of this stock's own z20 over the last 750 bars (point in time)
  const QS = [0.025, 0.10, 0.25, 0.75, 0.90, 0.975]; R.zq = QS.map(() => nanArr(n)); R.zone = new Array(n).fill(-1);
  const win = [];
  for (let t = 0; t < n; t++) {
    const z = R.z20[t];
    if (isF(z)) win.splice(bisect(win, z), 0, z);
    if (t >= 750 && isF(R.z20[t - 750])) { const k = bisect(win, R.z20[t - 750]); if (win[k] === R.z20[t - 750]) win.splice(k, 1); }
    if (win.length >= 250 && isF(z)) { const q = QS.map((p) => quantSorted(win, p)); q.forEach((v, k) => R.zq[k][t] = v); let zi = 0; while (zi < 6 && z > q[zi]) zi++; R.zone[t] = zi; }
  }
  // hindsight outcomes for zone statistics: did price touch the 20-day mean within 10 bars; 5-day return
  R.touch = nanArr(n); R.fwd5 = nanArr(n);
  for (let t = 0; t < n; t++) {
    if (t + 5 < n) R.fwd5[t] = c[t + 5] / c[t] - 1;
    if (t + 10 >= n || !isF(m20[t])) continue; const below = lc[t] < m20[t]; let hit = 0;
    for (let k = t + 1; k <= t + 10; k++) { const mk = Math.exp(m20[k]); if (below ? h[k] >= mk : l[k] <= mk) { hit = 1; break; } }
    R.touch[t] = hit;
  }
  // point-in-time stats of the current zone (only outcomes resolved by bar t)
  R.ztouch = nanArr(n); R.zn = new Array(n).fill(0); R.zfwd = nanArr(n);
  const zc = new Array(7).fill(0), zt = new Array(7).fill(0), zf = new Array(7).fill(0);
  for (let t = 0; t < n; t++) {
    const j = t - 10; if (j >= 0 && R.zone[j] >= 0 && isF(R.touch[j])) { const zi = R.zone[j]; zc[zi]++; zt[zi] += R.touch[j]; zf[zi] += R.fwd5[j]; }
    const zi = R.zone[t]; if (zi >= 0 && zc[zi]) { R.ztouch[t] = zt[zi] / zc[zi]; R.zn[t] = zc[zi]; R.zfwd[t] = zf[zi] / zc[zi]; }
  }
  return R;
}

// ------------------------------------------------------------ model: evidence-weighted score, adapted walk-forward
function nnls(Z, y, k) { // coordinate descent, w >= 0
  const w = new Array(k).fill(0), res = y.slice(), nn = Z.map((_, j) => 0); for (let j = 0; j < k; j++) for (const row of Z) nn[j] += row[j] * row[j];
  for (let it = 0; it < 200; it++) { let mx = 0;
    for (let j = 0; j < k; j++) { if (!nn[j]) continue; let g = 0; for (let i = 0; i < Z.length; i++) g += Z[i][j] * res[i]; const nw = Math.max(0, w[j] + g / nn[j]), d = nw - w[j]; if (d) { for (let i = 0; i < Z.length; i++) res[i] -= d * Z[i][j]; w[j] = nw; mx = Math.max(mx, Math.abs(d)); } }
    if (mx < 1e-7) break; }
  return w;
}
function fitCalib(s, y, a0, b0) { // logistic y ~ a + b*s by Newton, light ridge toward the prior
  let a = a0, b = b0; const lam = 5;
  for (let it = 0; it < 25; it++) { let ga = lam * (a - a0), gb = lam * (b - b0), haa = lam, hab = 0, hbb = lam;
    for (let i = 0; i < s.length; i++) { const p = sigm(a + b * s[i]), r = p - y[i], w = p * (1 - p); ga += r; gb += r * s[i]; haa += w; hab += w * s[i]; hbb += w * s[i] * s[i]; }
    const det = haa * hbb - hab * hab; if (!(det > 0)) break; const da = (hbb * ga - hab * gb) / det, db = (haa * gb - hab * ga) / det; a -= da; b -= db; if (Math.abs(da) + Math.abs(db) < 1e-8) break; }
  return [a, b];
}
function model(syms, rev, cfg) {
  const k = SKEYS.length, w0 = SKEYS.map((s) => PRIOR.w[s]), out = {};
  const cal = Array.from(new Set(syms.flatMap((s) => rev[s].d))).sort(), pos = new Map(cal.map((d, i) => [d, i]));
  // events: setup bars with a resolved trade outcome
  const ev = []; syms.forEach((s, si) => { const R = rev[s]; for (let t = 0; t < R.d.length; t++) if (R.setup[t] && isF(R.tret[t])) ev.push({ si, p: pos.get(R.d[t]), e: pos.get(R.d[Math.min(R.d.length - 1, t + R.thold[t])]), z: SKEYS.map((q) => R.Z[q][t]), y: R.y[t], r: R.tret[t] }); });
  syms.forEach((s, si) => {
    const R = rev[s], n = R.d.length, M = { score: nanArr(n), P: nanArr(n), Pr: nanArr(n), steps: [], C: {} };
    for (const q of SKEYS) M.C[q] = nanArr(n);
    let w = w0.slice(), A = PRIOR.calib.a, B = PRIOR.calib.b, nextFit = 0;
    const scoreAt = (t, ww) => { let sc = 0; for (let j = 0; j < k; j++) sc += ww[j] * R.Z[SKEYS[j]][t]; return sc; };
    for (let t = 0; t < n; t++) {
      if (cfg.adapt && t >= nextFit && t >= 260) {
        const now = pos.get(R.d[t]);
        const tr = ev.filter((q) => q.e < now && (q.si === si || cfg.pool > 0));
        const own = tr.filter((q) => q.si === si).length;
        let wb = w0.slice(), lam = 0;
        if (own >= 30) {
          const Z = [], y = []; const rs = tr.map((q) => q.r).sort((x, z) => x - z), lo = quantSorted(rs, 0.02), hi = quantSorted(rs, 0.98);
          const wt = tr.map((q) => q.si === si ? 1 : cfg.pool); let my = 0, sw = 0; tr.forEach((q, i) => { my += wt[i] * Math.max(lo, Math.min(hi, q.r)); sw += wt[i]; }); my /= sw;
          tr.forEach((q, i) => { const sq = Math.sqrt(wt[i]); Z.push(q.z.map((v) => v * sq)); y.push(sq * (Math.max(lo, Math.min(hi, q.r)) - my)); });
          let ws = nnls(Z, y, k); const tot = ws.reduce((x, z) => x + z, 0); ws = tot > 0 ? ws.map((v) => v / tot * k) : w0.slice();
          lam = own / (own + cfg.n0); wb = w0.map((v, j) => (1 - lam) * v + lam * ws[j]);
        }
        w = wb;
        const sc = [], yy = []; tr.forEach((q) => { if (q.si === si || cfg.pool > 0) { let v = 0; for (let j = 0; j < k; j++) v += w[j] * q.z[j]; sc.push(v); yy.push(q.y); } });
        [A, B] = sc.length >= 30 ? fitCalib(sc, yy, PRIOR.calib.a, PRIOR.calib.b) : [PRIOR.calib.a, PRIOR.calib.b];
        // historical average trade by score third, from resolved own events
        const third = [[], [], []]; tr.forEach((q) => { if (q.si !== si) return; let v = 0; for (let j = 0; j < k; j++) v += w[j] * q.z[j]; third[v <= PRIOR.thirds[0] ? 0 : v <= PRIOR.thirds[1] ? 1 : 2].push(q.r); });
        M.steps.push({ d: R.d[t], i: t, n: tr.length, own, lam, coef: w.slice(), a: A, b: B, base: yy.length ? yy.reduce((x, z) => x + z, 0) / yy.length : PRIOR.calib.a,
          thirds: third.map((a) => ({ n: a.length, avg: a.length ? a.reduce((x, z) => x + z, 0) / a.length : NaN_, win: a.length ? a.filter((x) => x > 0).length / a.length : NaN_ })) });
        nextFit = t + cfg.testDays;
      }
      if (t < 260) continue;
      const sc = scoreAt(t, w); M.score[t] = sc; M.P[t] = sigm(A + B * sc); M.Pr[t] = sigm(PRIOR.calib.a + PRIOR.calib.b * scoreAt(t, w0));
      for (let j = 0; j < k; j++) M.C[SKEYS[j]][t] = w[j] * R.Z[SKEYS[j]][t];
    }
    out[s] = M;
  });
  return out;
}

// ------------------------------------------------------------ backtest (portfolio, next-open fills, 5-day-average exit, ATR stop, time stop)
function backtest(syms, rev, M, cfg, thr) {
  const cal = Array.from(new Set(syms.flatMap((s) => rev[s].d))).sort(), n = cal.length;
  const idx = {}; syms.forEach((s) => idx[s] = new Map(rev[s].d.map((d, i) => [d, i])));
  const sig = {}; syms.forEach((s) => { const R = rev[s], m = M[s]; sig[s] = R.setup.map((v, i) => v && isF(m.score[i]) && m.score[i] >= thr ? 1 : 0); });
  let t0 = n; syms.forEach((s) => { const i = M[s].score.findIndex(isF); if (i >= 0) t0 = Math.min(t0, cal.indexOf(rev[s].d[i])); });
  if (t0 >= n) return { trades: [], eq: [], bh: [], d: [], dd: [], bhdd: [], sig };
  const cost = cfg.slippage / 1e4, s = cfg.side; let cash = 1e6; const pos = {}, trades = [], eq = [], bh = [], days = [];
  const px = (q, t, f) => { const i = idx[q].get(cal[t]); return i == null ? NaN_ : rev[q][f][i]; };
  const bh0 = syms.map((q) => { for (let t = t0; t < n; t++) { const v = px(q, t, "c"); if (isF(v)) return v; } return 1; });
  let pend = [];
  for (let t = t0; t < n; t++) {
    // entries at the open
    for (const p of pend) { const op = px(p.s, t, "o"); if (!isF(op) || pos[p.s]) continue; const equity = cash + Object.values(pos).reduce((a, x) => a + x.q * (px(x.s, t, "o") || x.last), 0);
      const dist = cfg.stopATR * p.atr / op; let notional = Math.min(equity * cfg.riskPct / Math.max(dist, 1e-4), equity * cfg.maxW); notional = Math.min(notional, Math.max(0, s > 0 ? cash : equity)); if (notional < 100) continue;
      const q = s * notional / op; cash -= q * op + notional * cost; pos[p.s] = { s: p.s, q, ep: op, ti: t, stop: op - s * cfg.stopATR * p.atr, last: q * op, sc: p.sc, P: p.P, z: p.z, fear: p.fear, risk: notional * dist, c0: notional * cost }; }
    pend = [];
    // intraday stop, then close-based exits
    for (const q of Object.keys(pos)) { const p = pos[q], i = idx[q].get(cal[t]); if (i == null) continue; const R = rev[q]; let x = null, why = "";
      if ((s > 0 && R.l[i] <= p.stop) || (s < 0 && R.h[i] >= p.stop)) { x = t > p.ti ? (s > 0 ? Math.min(R.o[i], p.stop) : Math.max(R.o[i], p.stop)) : p.stop; why = "STOP"; }
      else if ((s > 0 && R.c[i] > R.sma5[i]) || (s < 0 && R.c[i] < R.sma5[i])) { x = R.c[i]; why = "SMA5"; }
      else if (t - p.ti + 1 >= cfg.maxHold) { x = R.c[i]; why = "TIME"; }
      if (x != null) { const fee = Math.abs(p.q * x) * cost; cash += p.q * x - fee; const pnl = p.q * (x - p.ep) - fee - p.c0;
        trades.push({ trade_id: trades.length + 1, symbol: q, direction: s > 0 ? "long" : "short", entry_date: cal[p.ti], exit_date: cal[t], bars_held: t - p.ti, exit_reason: why, entry_price: p.ep, exit_price: x, R: p.risk > 0 ? pnl / p.risk : NaN_, pnl, weight: Math.abs(p.q * p.ep) / 1e6, p: p.P, score: p.sc, z_entry: p.z, fear: p.fear }); delete pos[q]; } }
    let held = 0; for (const q of Object.keys(pos)) { const v = px(q, t, "c"); if (isF(v)) pos[q].last = pos[q].q * v; held += pos[q].last; }
    eq.push(cash + held); days.push(cal[t]); bh.push(1e6 * syms.reduce((a, q, k) => a + (px(q, t, "c") || bh0[k]) / bh0[k], 0) / syms.length);
    if (t === n - 1) break;
    const cands = []; for (const q of syms) { const i = idx[q].get(cal[t]); if (i == null || pos[q] || !sig[q][i]) continue; cands.push({ s: q, sc: M[q].score[i], P: M[q].P[i], atr: rev[q].atr[i], z: rev[q].z20[i], fear: rev[q].frank[i] }); }
    cands.sort((a, b) => b.sc - a.sc); pend = cands.slice(0, Math.max(0, cfg.maxPos - Object.keys(pos).length));
  }
  let pk = -Infinity, bpk = -Infinity; const dd = eq.map((v) => { pk = Math.max(pk, v); return (v / pk - 1) * 100; }), bhdd = bh.map((v) => { bpk = Math.max(bpk, v); return (v / bpk - 1) * 100; });
  return { trades, eq, bh, dd, bhdd, d: days, sig };
}

{{OLD_METRICS}}

// ------------------------------------------------------------ orchestration
function contextMeans(ds, mkt) { // fair-value means and stationarity statistics kept from the earlier system, for context
  const n = ds.c.length, y = ds.c.map(Math.log), out = {};
  const [sma] = rollMeanStd(y, 20), ema = ewma(y, 2 / 21), kf = kalman(y), ou = rollingOU(y, 250, 0.5), tr = rollingTrend(y, 100);
  const kdev = y.map((v, i) => v - kf[i]), ksig = ewma(kdev.map((v) => v * v), hlAlpha(63)).map((v, i) => i < 60 ? NaN_ : Math.sqrt(v));
  out.lv_kalman = kf.map(Math.exp); out.zz_kalman = kdev.map((v, i) => v / ksig[i]); out.lv_ou = ou.mu.map(Math.exp); out.zz_ou = ou.z; out.hl = ou.hl;
  out.lv_trend = tr.lv.map(Math.exp); out.zz_trend = y.map((v, i) => (v - tr.lv[i]) / tr.sd[i]); out.lv_sma20 = sma.map(Math.exp); out.lv_ema20 = ema.map(Math.exp);
  if (mkt) {
    const map = new Map(mkt.d.map((d, i) => [d, i])), my = ds.d.map((d) => { const i = map.get(d); return i == null ? NaN_ : Math.log(mkt.c[i]); });
    for (let i = 1; i < n; i++) if (!isF(my[i])) my[i] = my[i - 1];
    const r = y.map((v, i) => i ? v - y[i - 1] : 0), mr = my.map((v, i) => i && isF(v) && isF(my[i - 1]) ? v - my[i - 1] : 0), W = 250, V = nanArr(n); let acc = 0, started = false, beta = NaN_;
    for (let t = 1; t < n; t++) { if (isF(beta)) { acc += r[t] - beta * mr[t]; started = true; } if (started) V[t] = acc;
      if (t >= W) { let sx = 0, sy = 0, sxx = 0, sxy = 0; for (let k = t - W + 1; k <= t; k++) { sx += mr[k]; sy += r[k]; sxx += mr[k] * mr[k]; sxy += mr[k] * r[k]; } const vx = sxx / W - (sx / W) ** 2; beta = vx > 0 ? (sxy / W - sx * sy / W / W) / vx : NaN_; } }
    const fo = rollingOU(V, 60, 0.5); out.zz_factor = fo.z; out.lv_factor = y.map((v, i) => Math.exp(v - fo.z[i] * fo.sig[i]));
  }
  const st = rollingStats(y, 250); out.hurst = st.hurst; out.adf = st.adfp; out.vr4 = st.vr4;
  return out;
}
function run(datasets, cfg, fear) {
  const all = Object.keys(datasets), mkt = cfg.market && datasets[cfg.market] ? datasets[cfg.market] : null;
  const syms = all.filter((s) => s !== cfg.market || all.length === 1);
  if (!syms.length) throw new Error("Upload at least one price file besides the market file.");
  const key = JSON.stringify([all.map((s) => [s, datasets[s].d.length, datasets[s].d[datasets[s].d.length - 1], datasets[s].c[datasets[s].c.length - 1]]), fear ? [fear.d.length, fear.d[fear.d.length - 1]] : 0,
    cfg.market, cfg.side, cfg.trig, cfg.stopATR, cfg.maxHold, cfg.slippage, cfg.adapt, cfg.n0, cfg.pool, cfg.testDays]);
  let base;
  if (CACHE.key === key) { base = CACHE.model; progress(0.9, "reusing features and model (only trading settings changed)"); }
  else {
    const rev = {}, ctx = {};
    syms.forEach((s, i) => { progress(0.02 + 0.6 * i / syms.length, `features, zones and volatility models: ${s}`);
      rev[s] = Object.assign(buildRev(datasets[s], fear, cfg), { d: datasets[s].d, o: datasets[s].o, h: datasets[s].h, l: datasets[s].l, c: datasets[s].c, v: datasets[s].v });
      ctx[s] = contextMeans(datasets[s], s === cfg.market ? null : mkt); });
    progress(0.7, "fitting the reversal model walk-forward");
    const M = model(syms, rev, cfg);
    base = { rev, ctx, M }; CACHE = { key, model: base };
  }
  const { rev, ctx, M } = base;
  progress(0.93, "backtest");
  const bt = backtest(syms, rev, M, cfg, cfg.scoreThr), btAll = backtest(syms, rev, M, cfg, -Infinity);
  const out = { syms, signs: SIGNS, prior: PRIOR, names: SKEYS, features: SIGNS.map((s) => [s[0], s[2], s[3]]), bt: { trades: bt.trades, eq: bt.eq, bh: bt.bh, dd: bt.dd, bhdd: bt.bhdd, d: bt.d }, btAll: { eq: btAll.eq, d: btAll.d, trades: btAll.trades.length }, symbols: {}, metrics: { symbols: {} }, fearEnd: fear ? fear.d[fear.d.length - 1] : null };
  const Y = [], P = [];
  for (const s of syms) {
    const R = rev[s], m = M[s], C = ctx[s], n = R.d.length, first = m.score.findIndex(isF);
    if (first < 0) { out.symbols[s] = null; continue; }
    const yy = [], pp = [];
    for (let t = first; t < n; t++) if (R.setup[t] && isF(R.y[t]) && isF(m.P[t])) { yy.push(R.y[t]); pp.push(m.P[t]); }
    Y.push(...yy); P.push(...pp);
    const str = bt.trades.filter((t) => t.symbol === s), strAll = btAll.trades.filter((t) => t.symbol === s);
    const tm = (a) => ({ n_trades: a.length, win_rate: a.length ? a.filter((t) => t.pnl > 0).length / a.length : NaN_, expectancy_R: a.length ? a.reduce((x, t) => x + (isF(t.R) ? t.R : 0), 0) / a.length : NaN_, pnl: a.reduce((x, t) => x + t.pnl, 0) });
    out.metrics.symbols[s] = { classification: classMetrics(yy, pp, pp, PRIOR.calib.a ? sigm(PRIOR.calib.a + PRIOR.calib.b * cfg.scoreThr) : 0.6), trading: tm(str), tradingAll: tm(strAll), signals: bt.sig[s].reduce((a, b) => a + b, 0), setups: R.setup.reduce((a, b) => a + b, 0) };
    const S = { first, side: cfg.side, steps: m.steps, garchSteps: R.garchSteps, harSteps: R.harSteps, sig: bt.sig[s] };
    for (const k of ["d", "o", "h", "l", "c", "v", "atr", "rsi2", "rsi14", "streak", "ibs", "lwick", "uwick", "ret1", "gap", "rangex", "volz", "m20", "s20", "z20", "sma5", "vterm", "vrank", "vix", "frank", "setup",
      "y", "tret", "thold", "texit", "zone", "ztouch", "zn", "zfwd", "touch", "fwd5", "r", "rv", "cc20", "park20", "gk20", "rs20", "yz5", "yz20", "yz60", "garch", "har5"]) S[k] = Array.from(R[k]);
    S.zq = R.zq.map((a) => Array.from(a)); S.X = {}; S.Z = {}; for (const q of SKEYS) { S.X[q] = Array.from(R.X[q]); S.Z[q] = Array.from(R.Z[q]); }
    S.score = m.score; S.P = m.P; S.Pr = m.Pr; S.C = m.C;
    Object.assign(S, C);
    S.lv_primary = R.m20.map(Math.exp); S.sg_primary = R.s20; S.z = R.z20;
    out.symbols[s] = S;
  }
  out.metrics.pooled = classMetrics(Y, P, P, 0.6);
  out.metrics.portfolio = tradeMetrics(bt.eq, bt.trades, bt.bh);
  out.metrics.portfolioAll = tradeMetrics(btAll.eq, btAll.trades, btAll.bh);
  progress(1, "done");
  return out;
}
