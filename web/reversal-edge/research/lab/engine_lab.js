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

// ------------------------------------------------------------ helpers
const nanArr = (n) => new Array(n).fill(NaN_);
function rollMeanStd(x, W) {
  const n = x.length, m = nanArr(n), s = nanArr(n);
  let sum = 0, sq = 0, cnt = 0;
  for (let t = 0; t < n; t++) {
    const v = x[t];
    if (isF(v)) { sum += v; sq += v * v; cnt++; }
    if (t >= W) { const u = x[t - W]; if (isF(u)) { sum -= u; sq -= u * u; cnt--; } }
    if (t >= W - 1 && cnt === W) { const mu = sum / W; m[t] = mu; s[t] = Math.sqrt(Math.max(0, (sq - W * mu * mu) / (W - 1))); }
  }
  return [m, s];
}
function ewma(x, alpha) {
  const out = nanArr(x.length); let m = NaN_;
  for (let t = 0; t < x.length; t++) { const v = x[t]; if (isF(v)) m = isF(m) ? m + alpha * (v - m) : v; out[t] = m; }
  return out;
}
const hlAlpha = (h) => 1 - Math.pow(0.5, 1 / h);
function rollPct(x, W) { // percentile rank of x[t] within trailing window
  const n = x.length, out = nanArr(n);
  for (let t = W - 1; t < n; t++) {
    if (!isF(x[t])) continue; let below = 0, c = 0;
    for (let k = t - W + 1; k <= t; k++) { if (isF(x[k])) { c++; if (x[k] <= x[t]) below++; } }
    if (c > W / 4) out[t] = below / c;
  }
  return out;
}
function normCdf(z) { // Abramowitz-Stegun 7.1.26 via erf
  const t = 1 / (1 + 0.3275911 * Math.abs(z / Math.SQRT2));
  const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-(z * z) / 2);
  return z >= 0 ? (1 + y) / 2 : (1 - y) / 2;
}
function mackinnonP(stat) { // constant, N=1 (matches statsmodels mackinnonp)
  if (!isF(stat)) return NaN_;
  if (stat > 2.74) return 1; if (stat < -18.83) return 0;
  const poly = stat <= -1.61 ? [2.1659, 1.4412, 0.038269] : [1.7339, 0.93202, -0.12745, -0.010368];
  let v = 0; for (let i = poly.length - 1; i >= 0; i--) v = v * stat + poly[i];
  return normCdf(v);
}
function solve(A, b) { // Gaussian elimination with partial pivoting (small k)
  const n = b.length, M = A.map((r, i) => r.concat([b[i]]));
  for (let c = 0; c < n; c++) {
    let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    [M[c], M[p]] = [M[p], M[c]]; const d = M[c][c] || 1e-12;
    for (let r = 0; r < n; r++) if (r !== c) { const f = M[r][c] / d; if (f) for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k]; }
  }
  return M.map((r, i) => r[n] / (r[i] || 1e-12));
}

// ------------------------------------------------------------ means
function rollingOU(x, W, tauFrac) { // AR(1) fit with Kendall correction; mean only when 1/theta < tauFrac*W
  const n = x.length, mu = nanArr(n), sig = nanArr(n), hl = nanArr(n), th = nanArr(n), z = nanArr(n);
  for (let t = W; t < n; t++) {
    let sx = 0, sy = 0, sxx = 0, syy = 0, sxy = 0, ok = true;
    for (let k = t - W + 1; k <= t; k++) {
      const a = x[k - 1], b = x[k]; if (!isF(a) || !isF(b)) { ok = false; break; }
      sx += a; sy += b; sxx += a * a; syy += b * b; sxy += a * b;
    }
    if (!ok) continue;
    const mx = sx / W, my = sy / W, vx = sxx / W - mx * mx, vy = syy / W - my * my, cv = sxy / W - mx * my;
    if (vx <= 0) continue;
    let b = cv / vx; b = (W * b + 1) / (W - 3);
    const a = my - b * mx, s2 = Math.max(0, vy - 2 * b * cv + b * b * vx) * W / (W - 2);
    if (b > 0 && b < 1) {
      const theta = -Math.log(b); th[t] = theta; hl[t] = Math.min(Math.log(2) / theta, 250);
      if (1 / theta < tauFrac * W) { mu[t] = a / (1 - b); sig[t] = Math.sqrt(s2 / (1 - b * b)); z[t] = (x[t] - mu[t]) / sig[t]; }
    } else hl[t] = 250;
  }
  return { mu, sig, hl, th, z };
}
function kalman(y) { // local linear trend with adaptive R and NIS-inflated Q (port of kernels.kalman_llt)
  const n = y.length, lvl = nanArr(n);
  let L = NaN_, S = 0, p00 = 0, p01 = 0, p11 = 0, R = 1e-4, nis = 1;
  const ra = hlAlpha(30), na = hlAlpha(10);
  for (let t = 0; t < n; t++) {
    const yt = y[t];
    if (!isF(L)) { if (isF(yt)) { L = yt; S = 0; p00 = 1e-2; p01 = 0; p11 = 1e-6; } lvl[t] = L; continue; }
    const k = Math.min(Math.max(nis, 1), 25), ql = 0.01 * R * k, qs = 1e-5 * R * k;
    const lp = L + S, a00 = p00 + 2 * p01 + p11 + ql, a01 = p01 + p11, a11 = p11 + qs;
    if (!isF(yt)) { L = lp; p00 = a00; p01 = a01; p11 = a11; lvl[t] = L; continue; }
    const nu = yt - lp, Sv = a00 + R, k0 = a00 / Sv, k1 = a01 / Sv;
    L = lp + k0 * nu; S = S + k1 * nu; p00 = (1 - k0) * a00; p01 = (1 - k0) * a01; p11 = Math.max(0, a11 - k1 * a01);
    R = (1 - ra) * R + ra * Math.max(nu * nu - a00, 0.05 * R); nis = (1 - na) * nis + na * (nu * nu / Sv);
    lvl[t] = L;
  }
  return lvl;
}
function rollingTrend(y, W) {
  const n = y.length, lv = nanArr(n), sd = nanArr(n);
  const tm = (W - 1) / 2, tv = (W * W - 1) / 12;
  for (let t = W - 1; t < n; t++) {
    let sy = 0, sty = 0, syy = 0; for (let k = 0; k < W; k++) { const v = y[t - W + 1 + k]; sy += v; sty += k * v; syy += v * v; }
    const my = sy / W, cov = sty / W - tm * my, vy = syy / W - my * my, slope = cov / tv;
    lv[t] = my + slope * (W - 1 - tm);
    sd[t] = Math.sqrt(Math.max(1e-12, (vy - slope * cov) * W / (W - 2)));
  }
  return { lv, sd };
}

// ------------------------------------------------------------ stationarity stats on a level series
function rollingStats(V, W) {
  const n = V.length, adfp = nanArr(n), vr4 = nanArr(n), hurst = nanArr(n);
  const dV = V.map((v, i) => i ? v - V[i - 1] : NaN_);
  const qs = [1, 2, 4, 8, 16];
  for (let t = W; t < n; t++) {
    let ok = true; for (let k = t - W; k <= t; k++) if (!isF(V[k])) { ok = false; break; }
    if (!ok) continue;
    // ADF(1) with constant: dV_t = c + g V_{t-1} + d dV_{t-1}
    const X = [], Y = [];
    for (let k = t - W + 2; k <= t; k++) { X.push([1, V[k - 1], dV[k - 1]]); Y.push(dV[k]); }
    const XtX = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], Xty = [0, 0, 0];
    for (let i = 0; i < X.length; i++) for (let a = 0; a < 3; a++) { Xty[a] += X[i][a] * Y[i]; for (let b = 0; b < 3; b++) XtX[a][b] += X[i][a] * X[i][b]; }
    const beta = solve(XtX, Xty); let ss = 0;
    for (let i = 0; i < X.length; i++) { const e = Y[i] - beta[0] * X[i][0] - beta[1] * X[i][1] - beta[2] * X[i][2]; ss += e * e; }
    const s2 = ss / (X.length - 3), inv11 = solve(XtX, [0, 1, 0])[1];
    adfp[t] = mackinnonP(beta[1] / Math.sqrt(s2 * inv11));
    // variance ratio VR(4) (debiased, overlapping) and Hurst from variance scaling
    const nq = W, mu = (V[t] - V[t - W]) / nq; let s1 = 0;
    for (let k = t - W + 1; k <= t; k++) { const d = dV[k] - mu; s1 += d * d; }
    const var1 = s1 / (nq - 1); const lv = [];
    for (const q of qs) {
      let sq = 0, c = 0; for (let k = t - W + q; k <= t; k++) { const d = V[k] - V[k - q] - q * mu; sq += d * d; c++; }
      if (q === 4) { const m = q * (nq - q + 1) * (1 - q / nq); vr4[t] = (sq / m) / var1; }
      lv.push(Math.log(Math.max(sq / c, 1e-300)));
    }
    const lx = qs.map(Math.log), mx = lx.reduce((a, b) => a + b) / 5, my = lv.reduce((a, b) => a + b) / 5;
    let num = 0, den = 0; for (let i = 0; i < 5; i++) { num += (lx[i] - mx) * (lv[i] - my); den += (lx[i] - mx) ** 2; }
    hurst[t] = num / den / 2;
  }
  const hs = nanArr(n); for (let t = 0; t < n; t++) { let s = 0, c = 0; for (let k = Math.max(0, t - 9); k <= t; k++) if (isF(hurst[k])) { s += hurst[k]; c++; } if (isF(hurst[t])) hs[t] = s / c; }
  return { adfp, vr4, hurst: hs };
}
function rollingAcf1(r, W) {
  const n = r.length, out = nanArr(n);
  for (let t = W; t < n; t++) {
    let m = 0; for (let k = t - W + 1; k <= t; k++) m += r[k]; m /= W;
    let num = 0, den = 0; for (let k = t - W + 1; k <= t; k++) { const d = r[k] - m; den += d * d; if (k > t - W + 1) num += d * (r[k - 1] - m); }
    if (den > 0 && isF(num)) out[t] = num / den;
  }
  return out;
}


// ------------------------------------------------------------ research prior (87 US stocks 2013-2017, RSI(2)<10 setups)
const PRIOR = {"cols": ["rel_volume", "range_expansion", "vol_rank", "vol_term", "fear_rank", "down_streak", "drop1_atr", "gap_size", "lower_wick"], "neg": ["gap_size", "lower_wick"], "w": {"rel_volume": 0.84, "range_expansion": 0.763, "vol_rank": 0.0, "vol_term": 1.593, "fear_rank": 1.949, "down_streak": 0.927, "drop1_atr": 0.0, "gap_size": 2.16, "lower_wick": 0.768}, "med": {"rel_volume": 0.4469, "range_expansion": 1.1139, "vol_rank": 0.484, "vol_term": -0.1028, "fear_rank": 0.6088, "down_streak": 3.0, "drop1_atr": 0.6352, "gap_size": -0.2448, "lower_wick": -0.2154}, "iqr": {"rel_volume": 1.4414, "range_expansion": 0.6967, "vol_rank": 0.574, "vol_term": 0.4294, "fear_rank": 0.6526, "down_streak": 2.0, "drop1_atr": 0.7822, "gap_size": 0.4211, "lower_wick": 0.3009}, "calib": {"a": 0.7031, "b": 0.0729}, "thirds": [-1.7889, 0.4356]};
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


// ------------------------------------------------------------ Momentum Pulse (mirrors research/study9.py)
// m_h = log(c_t/c_{t-h}) / (sigma*sqrt(h)) for h = 5,10,20,60 with sigma = Yang-Zhang 20-day daily volatility.
// M = EMA3 of their mean (sigma units). align = horizons agreeing with M's sign. ER = 20-day efficiency ratio.
// State: 1 trend up (M>1, 4/4 aligned, ER>.3), -1 trend down, 2 exhaustion up (M at its 2-year 95th percentile and turning down), -2 exhaustion down, 0 range.
// Thrust: M crosses +1 (or -1) with 4/4 alignment. Divergence: confirmed 5-bar pivots, price makes a new extreme that M does not confirm.
function ema3(x) { const out = nanArr(x.length); let m = NaN_; for (let i = 0; i < x.length; i++) { const v = x[i]; if (isF(v)) m = isF(m) ? m + 0.5 * (v - m) : v; out[i] = isF(v) ? m : NaN_; } return out; }
function pulseCalc(R, h, l, c) {
  const n = c.length, lc = c.map(Math.log), sig = R.yz20f.map((v) => v / Math.sqrt(252)), P = {};
  const H = [5, 10, 20, 60], raw = H.map((hh) => lc.map((v, t) => t >= hh && sig[t] > 0 ? (v - lc[t - hh]) / (sig[t] * Math.sqrt(hh)) : NaN_));
  const mean = lc.map((_, t) => raw.every((a) => isF(a[t])) ? (raw[0][t] + raw[1][t] + raw[2][t] + raw[3][t]) / 4 : NaN_);
  P.M = ema3(mean); P.mh = raw.map(ema3);
  P.align = P.M.map((m, t) => isF(m) ? raw.reduce((a, r) => a + (Math.sign(r[t]) === Math.sign(m) ? 1 : 0), 0) : 0);
  P.er = c.map((v, t) => { if (t < 20) return NaN_; let p = 0; for (let k = t - 19; k <= t; k++) p += Math.abs(c[k] - c[k - 1]); return p > 0 ? Math.abs(v - c[t - 20]) / p : NaN_; });
  P.acc = P.M.map((m, t) => t >= 3 ? m - P.M[t - 3] : NaN_);
  P.pct = rollRankPct(P.M, 500, 250);
  P.q95 = nanArr(n); P.q05 = nanArr(n);
  { const win = []; for (let t = 0; t < n; t++) { const v = P.M[t]; if (isF(v)) win.splice(bisect(win, v), 0, v);
      if (t >= 500 && isF(P.M[t - 500])) { const k = bisect(win, P.M[t - 500]); if (win[k] === P.M[t - 500]) win.splice(k, 1); }
      if (win.length >= 250) { P.q95[t] = quantSorted(win, 0.95); P.q05[t] = quantSorted(win, 0.05); } } }
  P.state = P.M.map((m, t) => { if (!isF(m)) return 0; let s0 = 0;
    if (m > 1 && P.align[t] === 4 && P.er[t] > 0.3) s0 = 1; if (m < -1 && P.align[t] === 4 && P.er[t] > 0.3) s0 = -1;
    if (P.pct[t] >= 0.95 && P.acc[t] < 0) s0 = 2; if (P.pct[t] <= 0.05 && P.acc[t] > 0) s0 = -2; return s0; });
  P.thrust = P.M.map((m, t) => t && P.align[t] === 4 ? (m > 1 && P.M[t - 1] <= 1 ? 1 : m < -1 && P.M[t - 1] >= -1 ? -1 : 0) : 0);
  const L = 5; P.div = new Array(n).fill(0); P.dp0 = new Array(n).fill(-1); P.dp1 = new Array(n).fill(-1); let lastLo = -1, lastHi = -1;
  for (let p = L; p < n - L; p++) { const t = p + L; let lo = Infinity, hi = -Infinity; for (let k = p - L; k <= p + L; k++) { lo = Math.min(lo, l[k]); hi = Math.max(hi, h[k]); }
    if (l[p] === lo) { if (lastLo >= 0 && p - lastLo <= 60 && l[p] < l[lastLo] && P.M[p] > P.M[lastLo] && P.M[lastLo] < -0.5) { P.div[t] = 1; P.dp0[t] = lastLo; P.dp1[t] = p; } lastLo = p; }
    if (h[p] === hi) { if (lastHi >= 0 && p - lastHi <= 60 && h[p] > h[lastHi] && P.M[p] < P.M[lastHi] && P.M[lastHi] > 0.5) { P.div[t] = -1; P.dp0[t] = lastHi; P.dp1[t] = p; } lastHi = p; } }
  P.f10 = c.map((v, t) => t + 10 < n ? Math.log(c[t + 10] / c[t]) : NaN_);   // hindsight, for the evidence table only
  return P;
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
  if (fear) { let j = 0, last = NaN_, lastD = null; const DAY = 864e5;
    for (let i = 0; i < n; i++) { while (j < fear.d.length && fear.d[j] <= ds.d[i]) { last = fear.c[j]; lastD = fear.d[j]; j++; }
      R.vix[i] = lastD && (Date.parse(ds.d[i]) - Date.parse(lastD)) / DAY <= 10 ? last : NaN_; } }
  R.frank = rollRankPct(R.vix, 500, 250);
  // oriented sign values (side +1: long after drops, -1: short after rises)
  const X = {};
  X.rel_volume = R.volz; X.range_expansion = R.rangex; X.vol_rank = R.vrank; X.vol_term = R.vterm; X.fear_rank = R.frank;
  X.down_streak = R.streak.map((x) => Math.max(-10, Math.min(10, -s * x)));
  X.drop1_atr = R.ret1.map((x) => -s * x); X.gap_size = R.gap.map(Math.abs); X.lower_wick = s > 0 ? R.lwick : R.uwick;
  R.X = X;
  R.Z = {}; for (const k of SKEYS) R.Z[k] = X[k].map((x) => { if (!isF(x)) return 0; const xo = NEG.has(k) ? -x : x; return Math.max(-3, Math.min(3, (xo - PRIOR.med[k]) / PRIOR.iqr[k])); });
  // instrument character: rolling 500-day lag-1 autocorrelation of daily returns (point in time).
  // Markets that keep moving the same way day to day (e.g. TASI, about +0.12) get momentum setups instead of reversal setups.
  R.ac = nanArr(n); R.acn = nanArr(n);
  { const r = lc.map((v, i) => i ? v - lc[i - 1] : NaN_);
    for (let t = 250; t < n; t++) { let sx = 0, sy = 0, sxx = 0, syy = 0, sxy = 0, m = 0;
      for (let k = Math.max(2, t - 499); k <= t; k++) { const a = r[k - 1], b = r[k]; if (!isF(a) || !isF(b)) continue; m++; sx += a; sy += b; sxx += a * a; syy += b * b; sxy += a * b; }
      if (m >= 250) { const cv = sxy / m - sx * sy / m / m, va = sxx / m - (sx / m) ** 2, vb = syy / m - (sy / m) ** 2; if (va > 0 && vb > 0) { R.ac[t] = cv / Math.sqrt(va * vb); R.acn[t] = m; } } } }
  R.mode = R.ac.map((a, i) => s < 0 || cfg.mode === "rev" ? 1 : cfg.mode === "mom" ? -1 : isF(a) && (cfg.acRule === "tstat" ? a * Math.sqrt(R.acn[i]) > 2 : a > cfg.acThr) ? -1 : 1);   // 1 reversal, -1 momentum
  R.setup = R.rsi2.map((x, i) => isF(x) && R.mode[i] === 1 && (s > 0 ? x < cfg.trig : x > 100 - cfg.trig) ? 1 : 0);
  R.msetup = R.rsi2.map((x, i) => isF(x) && R.mode[i] === -1 && x > cfg.momTrig ? 1 : 0);
  R.sma10 = rollMean(c, 10);
  const exitHit = (j) => cfg.exit === "prevhigh" ? (s > 0 ? c[j] > h[j - 1] : c[j] < l[j - 1]) : cfg.exit === "rsi70" ? (s > 0 ? R.rsi2[j] > 70 : R.rsi2[j] < 30)
    : cfg.exit === "sma10" ? (s > 0 ? c[j] > R.sma10[j] : c[j] < R.sma10[j]) : (s > 0 ? c[j] > R.sma5[j] : c[j] < R.sma5[j]);
  R.exitName = { prevhigh: "PREV-HIGH", rsi70: "RSI70", sma10: "SMA10", sma5: "SMA5" }[cfg.exit] || "SMA5";
  // reversal trade outcome (hindsight): limit buy limitATR under the close (valid one day) or next open; exit rule, optional ATR stop, maxHold bars
  R.y = nanArr(n); R.tret = nanArr(n); R.thold = nanArr(n); R.texit = new Array(n).fill(""); R.tentry = nanArr(n); R.unfilled = new Array(n).fill(0);
  const cost = (cfg.slippage * 2) / 1e4;
  for (let t = 0; t < n - 2; t++) {
    if (!isF(atr[t])) continue; let e;
    let fd = t + 1;
    if (cfg.entry === "limit") { const lim = c[t] - s * cfg.limitATR * atr[t]; const LD = cfg.limitDays || 1; let ok = false;
      for (fd = t + 1; fd <= Math.min(n - 1, t + LD); fd++) if (!((s > 0 && l[fd] > lim) || (s < 0 && h[fd] < lim))) { ok = true; break; }
      if (!ok) { R.unfilled[t] = 1; continue; } e = s > 0 ? Math.min(o[fd], lim) : Math.max(o[fd], lim); }
    else e = o[t + 1];
    const st = cfg.stopATR > 0 ? e - s * cfg.stopATR * atr[t] : null; let x = null, j = fd, why = "";
    for (; j < Math.min(n, fd + cfg.maxHold); j++) {
      if (cfg.t1 && j === fd) continue;
      if (st != null && ((s > 0 && l[j] <= st) || (s < 0 && h[j] >= st))) { x = j > t + 1 ? (s > 0 ? Math.min(o[j], st) : Math.max(o[j], st)) : st; why = "STOP"; break; }
      if (exitHit(j)) { x = cfg.exitAt === "open" ? (j + 1 < n ? o[j + 1] : c[j]) : c[j]; why = R.exitName; break; }
      if (j === fd - 1 + cfg.maxHold) { x = cfg.exitAt === "open" ? (j + 1 < n ? o[j + 1] : c[j]) : c[j]; why = "TIME"; break; }
    }
    if (x == null) continue;
    const rr = s * Math.log(x / e) - cost; R.tret[t] = rr; R.y[t] = rr > 0 ? 1 : 0; R.thold[t] = j - t; R.texit[t] = why; R.tentry[t] = e;
  }
  // momentum trade outcome (hindsight): buy the next open after a strong close, exit on a close below the 5-day average or after momMaxHold bars
  R.mret = nanArr(n); R.mhold = nanArr(n);
  if (s > 0) for (let t = 0; t < n - 2; t++) { const e = o[t + 1]; let x = null, j = t + 1;
    for (; j < Math.min(n, t + 1 + cfg.momMaxHold); j++) { if (c[j] < R.sma5[j] || j === t + cfg.momMaxHold) { x = c[j]; break; } }
    if (x != null) { R.mret[t] = Math.log(x / e) - cost; R.mhold[t] = j - t; } }
  R.pulse = pulseCalc(R, h, l, c);
  // A+ quality (study 11/12): the day closed in the bottom 13% of its range and the Momentum Pulse is below -0.5 (mirror for shorts)
  R.aq = R.ibs.map((b, i) => { const m = R.pulse.M[i]; return isF(b) && isF(m) && (s > 0 ? b <= 0.13 && m <= -0.5 : b >= 0.87 && m >= 0.5) ? 1 : 0; });
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
  const w = new Array(k).fill(0), res = y.slice(), nn = new Array(k).fill(0); for (let j = 0; j < k; j++) for (const row of Z) nn[j] += row[j] * row[j];
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
  const sig = {}; syms.forEach((s) => { const R = rev[s], m = M[s]; sig[s] = R.setup.map((v, i) => v && isF(m.score[i]) && m.score[i] >= thr && (cfg.grade !== "aplus" || R.aq[i]) ? 1 : R.msetup[i] && isF(m.score[i]) ? 2 : 0); });
  if (cfg.randSig) { let seed = cfg.randSig; const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    syms.forEach((q) => { const a = sig[q], m = M[q]; const elig = a.map((v, i) => isF(m.score[i]) && v !== 2 ? 1 : 0), ne = elig.reduce((x, y) => x + y, 0), k = a.filter((v) => v === 1).length;
      sig[q] = a.map((v, i) => v === 2 ? 2 : elig[i] && rnd() < k / Math.max(1, ne) ? 1 : 0); }); }
  let t0 = n; syms.forEach((s) => { const i = M[s].score.findIndex(isF); if (i >= 0) t0 = Math.min(t0, cal.indexOf(rev[s].d[i])); });
  if (t0 >= n) return { trades: [], eq: [], bh: [], d: [], dd: [], bhdd: [], sig };
  const cost = cfg.slippage / 1e4, s = cfg.side; let cash = 1e6; const pos = {}, trades = [], eq = [], bh = [], days = [];
  const px = (q, t, f) => { const i = idx[q].get(cal[t]); return i == null ? NaN_ : rev[q][f][i]; };
  const bh0 = syms.map((q) => { for (let t = t0; t < n; t++) { const v = px(q, t, "c"); if (isF(v)) return v; } return 1; });
  let bt_inv = null; let pend = [], inMkt = 0; const lastC = syms.map(() => NaN_);   // carry each market's last close across days it does not trade
  for (let t = t0; t < n; t++) {
    // entries: reversal limit orders fill only if the day trades down to the limit; momentum buys at the open
    const keep = [];
    for (const p of pend) { const i = idx[p.s].get(cal[t]); if (i == null) { keep.push(p); continue; } if (pos[p.s]) continue; const R = rev[p.s], op = R.o[i]; if (!isF(op)) continue;
      let fill = op;
      if (p.kind === 1 && cfg.entry === "limit") { const lim = p.c - s * cfg.limitATR * p.atr; if ((s > 0 && R.l[i] > lim) || (s < 0 && R.h[i] < lim)) { p.age = (p.age || 1) + 1; if (p.age <= (cfg.limitDays || 1)) keep.push(p); continue; } fill = s > 0 ? Math.min(op, lim) : Math.max(op, lim); }
      const equity = cash + Object.values(pos).reduce((a, x) => a + x.q * (px(x.s, t, "o") || x.last), 0);
      const dist = (cfg.stopATR > 0 ? cfg.stopATR : 3) * p.atr / fill; let notional = cfg.sizeMode === "fixed" ? equity * Math.min(cfg.maxW, 1 / Math.max(1, Math.min(cfg.maxPos, syms.length))) : Math.min(equity * cfg.riskPct / Math.max(dist, 1e-4), equity * cfg.maxW); const am = p.ap ? (cfg.aplusMult || 1) : (cfg.otherMult == null ? 1 : cfg.otherMult); notional *= am; if (cfg.invVol && isF(p.vol) && p.vol > 0) notional *= Math.max(0.5, Math.min(1.5, 30 / p.vol)); notional = Math.min(notional, Math.max(0, s > 0 ? cash : equity)); if (notional < 100) continue;
      const q = s * notional / fill; cash -= q * fill + notional * cost; pos[p.s] = { s: p.s, kind: p.kind, q, ep: fill, ti: t, stop: cfg.stopATR > 0 && p.kind === 1 ? fill - s * cfg.stopATR * p.atr : null, last: q * fill, sc: p.sc, P: p.P, z: p.z, fear: p.fear, risk: notional * dist, c0: notional * cost }; }
    pend = keep;
    // intraday stop (if any), then close-based exits
    for (const q of Object.keys(pos)) { const p = pos[q], i = idx[q].get(cal[t]); if (i == null) continue; const R = rev[q]; let x = null, why = "";
      if (p.exitNext) { x = R.o[i]; why = p.exitNext; }
      else if (cfg.t1 && t === p.ti) { }
      else {
      if (p.kind === 2) { if (R.c[i] < R.sma5[i]) { x = R.c[i]; why = "MOM-SMA5"; } else if (t - p.ti + 1 >= cfg.momMaxHold) { x = R.c[i]; why = "TIME"; } }
      else if (p.stop != null && ((s > 0 && R.l[i] <= p.stop) || (s < 0 && R.h[i] >= p.stop))) { x = t > p.ti ? (s > 0 ? Math.min(R.o[i], p.stop) : Math.max(R.o[i], p.stop)) : p.stop; why = "STOP"; }
      else { const ex = cfg.exit === "prevhigh" ? (i > 0 && (s > 0 ? R.c[i] > R.h[i - 1] : R.c[i] < R.l[i - 1])) : cfg.exit === "rsi70" ? (s > 0 ? R.rsi2[i] > 70 : R.rsi2[i] < 30) : cfg.exit === "sma10" ? (s > 0 ? R.c[i] > R.sma10[i] : R.c[i] < R.sma10[i]) : (s > 0 ? R.c[i] > R.sma5[i] : R.c[i] < R.sma5[i]);
        if (ex) { x = R.c[i]; why = R.exitName; } else if (t - p.ti + 1 >= cfg.maxHold) { x = R.c[i]; why = "TIME"; } }
      if (x != null && cfg.exitAt === "open" && why !== "STOP") { p.exitNext = why; x = null; } }
      if (x != null) { const fee = Math.abs(p.q * x) * cost; cash += p.q * x - fee; const pnl = p.q * (x - p.ep) - fee - p.c0;
        trades.push({ trade_id: trades.length + 1, symbol: q, direction: p.kind === 2 ? "momentum" : s > 0 ? "long" : "short", entry_date: cal[p.ti], exit_date: cal[t], bars_held: t - p.ti, exit_reason: why, entry_price: p.ep, exit_price: x, R: p.risk > 0 ? pnl / p.risk : NaN_, pnl, weight: Math.abs(p.q * p.ep) / 1e6, p: p.P, score: p.sc, z_entry: p.z, fear: p.fear }); delete pos[q]; } }
    let held = 0; for (const q of Object.keys(pos)) { const v = px(q, t, "c"); if (isF(v)) pos[q].last = pos[q].q * v; held += pos[q].last; }
    eq.push(cash + held); days.push(cal[t]); (bt_inv = bt_inv || []).push(held / (cash + held)); if (Object.keys(pos).length) inMkt++; syms.forEach((q, k) => { const v = px(q, t, "c"); if (isF(v)) lastC[k] = v; }); bh.push(1e6 * syms.reduce((a, q, k) => a + (isF(lastC[k]) ? lastC[k] : bh0[k]) / bh0[k], 0) / syms.length);
    if (t === n - 1) break;
    const cands = []; for (const q of syms) { const i = idx[q].get(cal[t]); if (i == null || pos[q] || !sig[q][i]) continue; cands.push({ s: q, kind: sig[q][i], ap: sig[q][i] === 1 && rev[q].aq[i] === 1, c: rev[q].c[i], sc: sig[q][i] === 2 ? 0 : M[q].score[i], P: M[q].P[i], atr: rev[q].atr[i], z: rev[q].z20[i], fear: rev[q].frank[i], vol: rev[q].yz20[i] }); }
    cands.sort((a, b) => (b.ap - a.ap) || (b.sc - a.sc)); { const live = pend.filter((p) => !cands.some((c) => c.s === p.s)); pend = live.concat(cands).slice(0, Math.max(0, cfg.maxPos - Object.keys(pos).length)); }
  }
  let pk = -Infinity, bpk = -Infinity; const dd = eq.map((v) => { pk = Math.max(pk, v); return (v / pk - 1) * 100; }), bhdd = bh.map((v) => { bpk = Math.max(bpk, v); return (v / bpk - 1) * 100; });
  return { trades, eq, bh, dd, bhdd, d: days, sig, inv: bt_inv || [], exposure: days.length ? inMkt / days.length : NaN };
}

// ------------------------------------------------------------ metrics
function auc(y, p) { const a = y.map((v, i) => [p[i], v]).sort((x, z) => x[0] - z[0]); let r = 0, n1 = 0, n0 = 0; a.forEach(([, v], i) => { if (v) { r += i + 1; n1++; } else n0++; }); return n1 && n0 ? (r - n1 * (n1 + 1) / 2) / (n1 * n0) : NaN_; }
function classMetrics(y, p, plo, thr) {
  const n = y.length; if (!n) return { n: 0 };
  const base = y.reduce((a, b) => a + b, 0) / n, brier = y.reduce((a, v, i) => a + (p[i] - v) ** 2, 0) / n, ref = y.reduce((a, v) => a + (base - v) ** 2, 0) / n;
  const sel = p.map((v) => v >= thr), ns = sel.filter(Boolean).length;
  const order = p.map((v, i) => i).sort((a, b) => p[a] - p[b]), bins = 10, cal = { p_mean: [], y_rate: [], n: [], lo: [], hi: [] };
  for (let b = 0; b < bins; b++) { const ix = order.slice(Math.floor(b * n / bins), Math.floor((b + 1) * n / bins)); if (!ix.length) continue;
    const pm = ix.reduce((a, i) => a + p[i], 0) / ix.length, yr = ix.reduce((a, i) => a + y[i], 0) / ix.length, se = Math.sqrt(yr * (1 - yr) / ix.length);
    cal.p_mean.push(pm); cal.y_rate.push(yr); cal.n.push(ix.length); cal.lo.push(Math.max(0, yr - 1.96 * se)); cal.hi.push(Math.min(1, yr + 1.96 * se)); }
  const ece = cal.n.reduce((a, c, i) => a + c * Math.abs(cal.p_mean[i] - cal.y_rate[i]), 0) / n;
  return { n, base_rate: base, brier, brier_skill: ref > 0 ? 1 - brier / ref : NaN_, roc_auc: auc(y, p), ece, precision_at_thr: ns ? y.filter((v, i) => sel[i]).reduce((a, b) => a + b, 0) / ns : NaN_, coverage_at_thr: ns / n, cal };
}
function tradeMetrics(eq, trades, bh) {
  if (eq.length < 2) return {};
  const r = eq.map((v, i) => i ? v / eq[i - 1] - 1 : 0), m = r.reduce((a, b) => a + b, 0) / r.length, sd = Math.sqrt(r.reduce((a, v) => a + (v - m) ** 2, 0) / (r.length - 1));
  const dn = Math.sqrt(r.reduce((a, v) => a + Math.min(v, 0) ** 2, 0) / r.length), yrs = r.length / 252, tot = eq[eq.length - 1] / eq[0] - 1;
  let pk = -Infinity, mdd = 0; eq.forEach((v) => { pk = Math.max(pk, v); mdd = Math.min(mdd, v / pk - 1); });
  const br = bh.map((v, i) => i ? v / bh[i - 1] - 1 : 0), bm = br.reduce((a, b) => a + b, 0) / br.length, bsd = Math.sqrt(br.reduce((a, v) => a + (v - bm) ** 2, 0) / (br.length - 1));
  let bpk = -Infinity, bmdd = 0; bh.forEach((v) => { bpk = Math.max(bpk, v); bmdd = Math.min(bmdd, v / bpk - 1); });
  const pnl = trades.map((t) => t.pnl), win = pnl.filter((v) => v > 0), loss = pnl.filter((v) => v <= 0), Rs = trades.map((t) => t.R).filter(isF);
  return { sharpe: sd > 0 ? m * 252 / (sd * Math.sqrt(252)) : NaN_, sortino: dn > 0 ? m * 252 / (dn * Math.sqrt(252)) : NaN_, cagr: tot > -1 ? Math.pow(1 + tot, 1 / yrs) - 1 : NaN_, max_drawdown: mdd,
    bh_sharpe: bsd > 0 ? bm * 252 / (bsd * Math.sqrt(252)) : NaN_, bh_max_drawdown: bmdd, n_trades: trades.length, trades_per_year: trades.length / yrs,
    win_rate: trades.length ? win.length / trades.length : NaN_, expectancy_R: Rs.length ? Rs.reduce((a, b) => a + b, 0) / Rs.length : NaN_,
    profit_factor: loss.length && loss.reduce((a, b) => a + b, 0) < 0 ? win.reduce((a, b) => a + b, 0) / -loss.reduce((a, b) => a + b, 0) : NaN_, total_return: tot };
}


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
    cfg.market, cfg.side, cfg.trig, cfg.stopATR, cfg.maxHold, cfg.slippage, cfg.adapt, cfg.n0, cfg.pool, cfg.testDays, cfg.mode, cfg.acThr, cfg.entry, cfg.limitATR, cfg.exit, cfg.momTrig, cfg.momMaxHold]);
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
  const btA = backtest(syms, rev, M, Object.assign({}, cfg, { grade: "aplus" }), Math.max(cfg.scoreThr, PRIOR.thirds[1])), btB = backtest(syms, rev, M, Object.assign({}, cfg, { grade: "all" }), Math.max(cfg.scoreThr, PRIOR.thirds[1]));
  const out = { syms, signs: SIGNS, prior: PRIOR, names: SKEYS, features: SIGNS.map((s) => [s[0], s[2], s[3]]), bt: { trades: bt.trades, inv: bt.inv, eq: bt.eq, bh: bt.bh, dd: bt.dd, bhdd: bt.bhdd, d: bt.d, exposure: bt.exposure }, btAll: { eq: btAll.eq, d: btAll.d, trades: btAll.trades.length }, btA: { eq: btA.eq, d: btA.d, exposure: btA.exposure }, btB: { eq: btB.eq, d: btB.d, exposure: btB.exposure }, symbols: {}, metrics: { symbols: {} }, fearEnd: fear ? fear.d[fear.d.length - 1] : null };
  const Y = [], P = [];
  for (const s of syms) {
    const R = rev[s], m = M[s], C = ctx[s], n = R.d.length, first = m.score.findIndex(isF);
    if (first < 0) { out.symbols[s] = null; continue; }
    const yy = [], pp = [];
    for (let t = first; t < n; t++) if (R.setup[t] && isF(R.y[t]) && isF(m.P[t])) { yy.push(R.y[t]); pp.push(m.P[t]); }
    Y.push(...yy); P.push(...pp);
    const str = bt.trades.filter((t) => t.symbol === s), strAll = btAll.trades.filter((t) => t.symbol === s);
    const tm = (a) => ({ n_trades: a.length, win_rate: a.length ? a.filter((t) => t.pnl > 0).length / a.length : NaN_, expectancy_R: a.length ? a.reduce((x, t) => x + (isF(t.R) ? t.R : 0), 0) / a.length : NaN_, pnl: a.reduce((x, t) => x + t.pnl, 0) });
    out.metrics.symbols[s] = { classification: classMetrics(yy, pp, pp, PRIOR.calib.a ? sigm(PRIOR.calib.a + PRIOR.calib.b * cfg.scoreThr) : 0.6), trading: tm(str), tradingAll: tm(strAll), signals: bt.sig[s].filter((v) => v > 0).length, setups: R.setup.reduce((a, b) => a + b, 0), msetups: R.msetup.reduce((a, b) => a + b, 0) };
    const S = { first, side: cfg.side, exitName: R.exitName, steps: m.steps, garchSteps: R.garchSteps, harSteps: R.harSteps, sig: bt.sig[s] };
    for (const k of ["d", "o", "h", "l", "c", "v", "atr", "rsi2", "rsi14", "streak", "ibs", "lwick", "uwick", "ret1", "gap", "rangex", "volz", "m20", "s20", "z20", "sma5", "vterm", "vrank", "vix", "frank", "setup",
      "y", "tret", "thold", "texit", "tentry", "unfilled", "ac", "mode", "msetup", "mret", "mhold", "sma10", "zone", "ztouch", "zn", "zfwd", "touch", "fwd5", "r", "rv", "cc20", "park20", "gk20", "rs20", "yz5", "yz20", "yz60", "garch", "har5"]) S[k] = Array.from(R[k]);
    S.zq = R.zq.map((a) => Array.from(a)); S.pulse = R.pulse; S.X = {}; S.Z = {}; for (const q of SKEYS) { S.X[q] = Array.from(R.X[q]); S.Z[q] = Array.from(R.Z[q]); }
    S.aplus = R.setup.map((v, i) => v && R.aq[i] && isF(m.score[i]) && m.score[i] >= PRIOR.thirds[1] ? 1 : 0); S.aq = Array.from(R.aq); S.score = m.score; S.P = m.P; S.Pr = m.Pr; S.C = m.C;
    Object.assign(S, C);
    S.lv_primary = R.m20.map(Math.exp); S.sg_primary = R.s20; S.z = R.z20;
    out.symbols[s] = S;
  }
  out.metrics.pooled = classMetrics(Y, P, P, 0.6);
  out.metrics.portfolio = tradeMetrics(bt.eq, bt.trades, bt.bh);
  out.metrics.portfolioAll = tradeMetrics(btAll.eq, btAll.trades, btAll.bh);
  out.metrics.portfolioAPlus = tradeMetrics(btA.eq, btA.trades, btA.bh); out.metrics.portfolioTop = tradeMetrics(btB.eq, btB.trades, btB.bh);
  progress(1, "done");
  return out;
}
