#!/usr/bin/env python3
"""Human-level odds model ("your chances at your level") for chess-coach.

Fits an ordered-logit model P(White wins / draw / Black wins | Stockfish-17.1 cp, rating band) on rated Lichess
games and writes data/models/odds.json in the format js/prob.js reads.

Run (end to end, deterministic):
    /tmp/claude-0/venv/bin/python tools/odds/fit_odds.py [--data PATH] [--cache DIR] [--boot 1000]
Stages (each cached under --cache, default /tmp/claude-0/odds/):
    1. parse    : read the ndjson.bz2, replay every rated standard game with python-chess (2 worker processes), compute the
                  app's phase per position, check eval alignment / sign (judgment 'best' moves, puzzle FENs, mate signs).
    2. sample   : stratified sample of positions (one per game) for Stockfish 17.1 re-evaluation; train games -> eval-scale
                  mapping, test games -> final check on real SF17 evals.
    3. rescore  : node tools/odds/sf_rescore.mjs (Stockfish 17.1, depth 14, 2 processes).
    4. mapping  : robust linear fit lichess_cp -> sf17_cp.
    5. fit      : model selection by game-clustered 5-fold CV on the TRAIN games only, final fit on all train games.
    6. evaluate : held-out TEST games (20 % by md5 of the game id): log loss / Brier with game-clustered bootstrap CIs,
                  calibration, draw-rate checks, selection-bias checks; then writes odds.json.
Use --stage parse|sample|rescore to stop early, --force-parse / --force-rescore to ignore caches.
"""
import argparse, bz2, hashlib, json, math, os, pickle, subprocess, sys, time
from multiprocessing import Pool

import numpy as np
from scipy.optimize import minimize

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))  # chess-coach/
DEFAULT_DATA = "/tmp/claude-0/mcognetta_lichess-combined-puzzle-game-db/combined_puzzle_db_first_50k.ndjson.bz2"
SEED = 20261012

# ----------------------------------------------------------------------------------------------------------------------
# Stage 1: parse + replay
# ----------------------------------------------------------------------------------------------------------------------

def _phase_arrays(sans, analysis, puzzle_url, puzzle_fen, puzzle_moves):
    """Replay the game; return per-position (after ply k = 1..n) phase codes and alignment-check counters."""
    import chess
    B = chess.Board()
    n = len(sans)
    phase = np.full(n, -1, np.int8)
    st = dict(best_h0=0, best_h0_legal=0, best_h1=0, best_h1_legal=0, judged_eq_best=0, replay_ok=1, puzzle_off=None, puzzle_move_ok=None)
    BB = chess.BB_SQUARES
    sq = chess.parse_square
    hw = [(BB[sq("b1")], "n"), (BB[sq("g1")], "n"), (BB[sq("c1")], "b"), (BB[sq("f1")], "b")]
    hb = [(BB[sq("b8")], "n"), (BB[sq("g8")], "n"), (BB[sq("c8")], "b"), (BB[sq("f8")], "b")]
    pz_ply = None
    if puzzle_url and "#" in puzzle_url:
        try: pz_ply = int(puzzle_url.rsplit("#", 1)[1])
        except ValueError: pz_ply = None
    pz_key = None
    if puzzle_fen:
        f = puzzle_fen.split()
        pz_key = (f[0], f[1])
    pz_first = puzzle_moves.split()[0] if puzzle_moves else None
    for i, san in enumerate(sans):
        # board = position after i plies
        if pz_key is not None and pz_ply is not None and st["puzzle_off"] is None and abs(i - pz_ply) <= 2:
            if (B.board_fen(), "w" if B.turn else "b") == pz_key:
                st["puzzle_off"] = i - pz_ply
                st["puzzle_start"] = i
        if i < len(analysis) and "best" in analysis[i]:   # H0: analysis[i] = eval after ply i+1, best from position after i plies
            st["best_h0"] += 1
            try:
                mv = chess.Move.from_uci(analysis[i]["best"]); ok = B.is_legal(mv)
            except Exception: ok = False
            st["best_h0_legal"] += ok
        if i + 1 < len(analysis) and "best" in analysis[i + 1]:  # H1 (shift by one): analysis[i+1] judged from position after i plies
            st["best_h1"] += 1
            try:
                mv = chess.Move.from_uci(analysis[i + 1]["best"]); ok = B.is_legal(mv)
            except Exception: ok = False
            st["best_h1_legal"] += ok
        try:
            mv = B.parse_san(san)
        except Exception:
            st["replay_ok"] = 0
            break
        if i < len(analysis) and "best" in analysis[i] and mv.uci() == analysis[i]["best"]:
            st["judged_eq_best"] += 1
        if st.get("puzzle_start") == i and pz_first is not None:
            st["puzzle_move_ok"] = int(mv.uci() == pz_first)
        B.push(mv)
        occW, occB = B.occupied_co[True], B.occupied_co[False]
        kn, bi = B.knights, B.bishops
        npm = 3 * (kn | bi).bit_count() + 5 * B.rooks.bit_count() + 9 * B.queens.bit_count()
        q = B.queens.bit_count()
        ply = i + 1
        if npm <= 26 or (q == 0 and npm <= 32):
            phase[i] = 2
        else:
            und = 0
            for m, t in hw: und += bool((kn if t == "n" else bi) & occW & m)
            for m, t in hb: und += bool((kn if t == "n" else bi) & occB & m)
            dev = 8 - und
            phase[i] = 0 if (ply < 16 or (ply < 26 and dev < 7)) else 1
    st["final_checkmate"] = int(st["replay_ok"] and B.is_checkmate())
    return phase, st


def _parse_line(line):
    x = json.loads(line)
    g = x["game"]
    pz = x.get("puzzle") or {}
    rec = dict(id=g["id"], speed=g.get("speed"), rated=bool(g.get("rated")), variant=g.get("variant"), status=g.get("status"),
               winner=g.get("winner"), created=g.get("createdAt"))
    pl = g.get("players") or {}
    rec["wr"] = (pl.get("white") or {}).get("rating")
    rec["br"] = (pl.get("black") or {}).get("rating")
    rec["wprov"] = bool((pl.get("white") or {}).get("provisional"))
    rec["bprov"] = bool((pl.get("black") or {}).get("provisional"))
    clk = g.get("clock") or {}
    rec["clock"] = (clk.get("initial"), clk.get("increment"))
    an = g.get("analysis") or []
    sans = g.get("moves", "").split()
    rec["n"] = len(sans)
    rec["n_an"] = len(an)
    rec["sans"] = " ".join(sans)
    if rec["variant"] != "standard" or not an or not sans:
        rec["skip"] = "variant/no-analysis"
        return rec
    cp = np.full(len(sans), np.nan, np.float32)
    mate = np.zeros(len(sans), np.int16)
    for i, e in enumerate(an[: len(sans)]):
        if "mate" in e and e["mate"] is not None:
            mate[i] = int(e["mate"]) if int(e["mate"]) != 0 else 0
            if mate[i] == 0:  # mate 0 should not occur; keep as missing
                continue
        elif "eval" in e and e["eval"] is not None:
            cp[i] = float(e["eval"])
    phase, st = _phase_arrays(sans, an, pz.get("GameUrl"), pz.get("FEN"), pz.get("Moves"))
    rec.update(cp=cp, mate=mate, phase=phase, chk=st, pz_moves=len((pz.get("Moves") or "").split()), pz_ply_url=None)
    try: rec["pz_ply_url"] = int((pz.get("GameUrl") or "").rsplit("#", 1)[1])
    except Exception: pass
    return rec


def stage_parse(data_path, cache, force=False):
    out = os.path.join(cache, "parsed.pkl")
    if os.path.exists(out) and not force:
        with open(out, "rb") as f: return pickle.load(f)
    t0 = time.time()
    with bz2.open(data_path, "rt") as f:
        lines = f.readlines()
    print(f"[parse] read {len(lines)} lines in {time.time()-t0:.0f}s; replaying with 2 processes ...", flush=True)
    with Pool(2) as pool:
        recs = pool.map(_parse_line, lines, chunksize=200)
    with open(out, "wb") as f: pickle.dump(recs, f, protocol=4)
    print(f"[parse] done in {time.time()-t0:.0f}s -> {out}", flush=True)
    return recs


# ----------------------------------------------------------------------------------------------------------------------
# helpers: splits, filters, flattening
# ----------------------------------------------------------------------------------------------------------------------

def h100(s):
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % 100

def split_of(gid):
    return "test" if h100(gid) >= 80 else "train"

def fold_of(gid, k=5):
    return int(hashlib.md5(("cv|" + gid).encode()).hexdigest(), 16) % k

RES_CODE = {"black": 0, None: 1, "white": 2}


def eligible(r):
    """Rated standard game with analysis, replay OK, outcome known, not a cheat/abort."""
    if r.get("skip") or not r["rated"] or r["variant"] != "standard": return False
    if not r["chk"]["replay_ok"]: return False
    if r["status"] in ("cheat", "aborted", "noStart", "unknownFinish"): return False
    if r["wr"] is None or r["br"] is None: return False
    return True


def flatten(recs, map_fn, clip):
    """Positions of the given games -> dict of arrays. cp mapped to SF17 units by map_fn, mates -> +-clip, clipped."""
    G, P, CP, M, PH, Y, W, R, D, PRE, POST = [], [], [], [], [], [], [], [], [], [], []
    for gi, r in enumerate(recs):
        cp = r["cp"].astype(np.float64); mate = r["mate"].astype(np.int64)
        ok = ~np.isnan(cp) | (mate != 0)
        idx = np.nonzero(ok)[0]
        if len(idx) == 0: continue
        v = map_fn(np.where(np.isnan(cp[idx]), 0.0, cp[idx]), r)
        mt = mate[idx]
        v = np.where(mt > 0, clip, np.where(mt < 0, -clip, v))
        v = np.clip(v, -clip, clip)
        n = len(idx)
        G.append(np.full(n, gi)); P.append(idx + 1); CP.append(v); M.append(mt); PH.append(r["phase"][idx])
        Y.append(np.full(n, RES_CODE[r["winner"]])); W.append(np.full(n, 1.0 / n))
        R.append(np.full(n, (r["wr"] + r["br"]) / 2.0)); D.append(np.full(n, r["wr"] - r["br"]))
        ps = r["chk"].get("puzzle_start")
        if ps is None:
            PRE.append(np.zeros(n, bool)); POST.append(np.zeros(n, bool))
        else:
            ply = idx + 1
            PRE.append(ply <= ps)        # positions up to (and including) the puzzle FEN: selected on the future blunder
            POST.append(ply >= ps + 1)   # positions after the blunder move (the puzzler never looks past this point)
    cat = lambda L, dt=None: np.concatenate(L).astype(dt) if dt else np.concatenate(L)
    return dict(g=cat(G, np.int64), ply=cat(P, np.int64), cp=cat(CP, np.float64), mate=cat(M, np.int64), phase=cat(PH, np.int64),
                y=cat(Y, np.int64), w=cat(W, np.float64), r=cat(R, np.float64), d=cat(D, np.float64), pre=cat(PRE), post=cat(POST))


def subset(X, mask):
    return {k: v[mask] for k, v in X.items()}


# ----------------------------------------------------------------------------------------------------------------------
# Ordered logit with smooth rating terms
# ----------------------------------------------------------------------------------------------------------------------
# z = a * cp/100, t1 = m - wdt/2, t2 = m + wdt/2;  log a = Fa @ pa, m = Fm @ pm, log wdt = Fw @ pw
# P(Black) = s(t1 - z), P(White) = 1 - s(t2 - z) = s(z - t2), P(draw) = s(t2 - z) - s(t1 - z)

def sig(x):
    return 0.5 * (1.0 + np.tanh(0.5 * x))


def log_sig(x):
    return -np.logaddexp(0.0, -x)


class Design:
    """Feature maps for the three parameter groups. kind: 'pooled' | 'lin' | 'quad' | 'band' ; phases: add phase dummies."""
    def __init__(self, kind, phases=False, bands=None, center=1800.0, scale=400.0):
        self.kind, self.phases, self.bands, self.center, self.scale = kind, phases, bands, center, scale

    def feats(self, r, phase):
        x = (np.asarray(r, float) - self.center) / self.scale
        cols = [np.ones_like(x)]
        if self.kind in ("lin", "quad"): cols.append(x)
        if self.kind == "quad": cols.append(x * x)
        if self.kind == "band":
            b = np.round(np.asarray(r, float) / 100.0) * 100.0
            bands = self.bands
            b = np.clip(b, bands[0], bands[-1])
            cols = [(b == bb).astype(float) for bb in bands]
        if self.phases:
            ph = np.asarray(phase)
            cols += [(ph == 0).astype(float), (ph == 2).astype(float)]
        return np.stack(cols, 1)

    def nparams(self):
        k = {"pooled": 1, "lin": 2, "quad": 3}.get(self.kind, len(self.bands or []))
        return k + (2 if self.phases else 0)


def unpack(theta, k):
    return theta[:k], theta[k:2 * k], theta[2 * k:3 * k]


def params_at(theta, F, k):
    pa, pm, pw = unpack(theta, k)
    a = np.exp(F @ pa); m = F @ pm; wd = np.exp(F @ pw)
    return a, m - wd / 2, m + wd / 2


def probs(a, t1, t2, cp, c=0.0):
    z = a * cp / 100.0 + c
    pl = sig(t1 - z); pw = 1.0 - sig(t2 - z); pd = np.maximum(0.0, 1.0 - pl - pw)
    return pw, pd, pl


def nll_grad(theta, F, cp, y, w, k, l2=1e-6):
    pa, pm, pw_ = unpack(theta, k)
    a = np.exp(F @ pa); m = F @ pm; wd = np.exp(F @ pw_)
    u = cp / 100.0
    z = a * u
    t1 = m - wd / 2; t2 = m + wd / 2
    A = t1 - z; Bv = t2 - z
    s1 = sig(A); s2 = sig(Bv)
    ll = np.empty_like(z); g_t1 = np.zeros_like(z); g_t2 = np.zeros_like(z); g_z = np.zeros_like(z)
    b = y == 0; wn = y == 2; d = y == 1
    ll[b] = log_sig(A[b]); g_t1[b] = 1 - s1[b]; g_z[b] = -(1 - s1[b])
    ll[wn] = log_sig(-Bv[wn]); g_t2[wn] = -s2[wn]; g_z[wn] = s2[wn]
    # draw: log(s2 - s1) computed stably: s2 - s1 = s(B) - s(A) = s(B)(1-s(A)) (1 - e^{A-B})
    Ad, Bd = A[d], Bv[d]
    pdv = np.maximum(s2[d] - s1[d], 1e-300)
    ll[d] = log_sig(Bd) + log_sig(-Ad) + np.log(-np.expm1(Ad - Bd))
    d2 = s2[d] * (1 - s2[d]); d1 = s1[d] * (1 - s1[d])
    g_t2[d] = d2 / pdv; g_t1[d] = -d1 / pdv; g_z[d] = (d1 - d2) / pdv
    W = w.sum()
    f = -(w * ll).sum() / W
    # chain rule: z = a u, a = exp(F pa); t1 = m - wd/2, t2 = m + wd/2, wd = exp(F pw)
    gz = w * g_z; gt1 = w * g_t1; gt2 = w * g_t2
    grad_pa = F.T @ (gz * a * u)
    grad_pm = F.T @ (gt1 + gt2)
    grad_pw = F.T @ ((gt2 - gt1) * wd / 2)
    g = -np.concatenate([grad_pa, grad_pm, grad_pw]) / W
    f += l2 * (theta @ theta); g += 2 * l2 * theta
    return f, g


def fit(X, design, theta0=None):
    F = design.feats(X["r"], X["phase"]); k = design.nparams()
    if theta0 is None:
        theta0 = np.zeros(3 * k)
        if design.kind == "band":
            theta0[:k] = math.log(0.4); theta0[2 * k:] = math.log(0.6)
        else:
            theta0[0] = math.log(0.4); theta0[2 * k] = math.log(0.6)
    res = minimize(nll_grad, theta0, args=(F, X["cp"], X["y"], X["w"], k), jac=True, method="L-BFGS-B",
                   options=dict(maxiter=2000, gtol=1e-9, ftol=1e-13))
    return res.x, res


def predict(theta, design, X):
    F = design.feats(X["r"], X["phase"]); k = design.nparams()
    a, t1, t2 = params_at(theta, F, k)
    return probs(a, t1, t2, X["cp"])


# ----------------------------------------------------------------------------------------------------------------------
# metrics: per-game means, game-clustered bootstrap
# ----------------------------------------------------------------------------------------------------------------------

def per_position_losses(P, y):
    pw, pd, pl = P
    eps = 1e-12
    p_true = np.where(y == 2, pw, np.where(y == 1, pd, pl))
    ll = -np.log(np.clip(p_true, eps, 1.0))
    oh = np.stack([(y == 2), (y == 1), (y == 0)], 1).astype(float)
    pr = np.stack([pw, pd, pl], 1)
    br = ((pr - oh) ** 2).sum(1)
    return ll, br


def game_means(v, g, w):
    """Per-game weighted mean of v (weights w sum to 1 per game) -> array over games (in order of unique g)."""
    ug, inv = np.unique(g, return_inverse=True)
    s = np.bincount(inv, weights=v * w); ws = np.bincount(inv, weights=w)
    return s / ws


def boot_ci(per_game, B, rng, stat=np.mean):
    n = len(per_game)
    idx = rng.integers(0, n, size=(B, n))
    vals = per_game[idx].mean(1)
    return float(stat(per_game)), float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def fmt_ci(t):
    return f"{t[0]:.4f} [{t[1]:.4f}, {t[2]:.4f}]"


# ----------------------------------------------------------------------------------------------------------------------
# JS-equivalent predictor (mirrors js/prob.js Prob.human exactly, for check points)
# ----------------------------------------------------------------------------------------------------------------------

def js_nearest_band(model, band):
    ks = [float(k) for k in model["bands"].keys()]
    ks_sorted = sorted(ks, key=lambda b: abs(b - band))  # Python sort is stable like V8's Array.sort; keys are in ascending order
    return ks_sorted[0]


def js_key(b):
    return str(int(b)) if float(b).is_integer() else repr(b)


def js_human_proposed(model, cp_white, band=None, phase=None):
    """Mirror of the proposed Prob.human in ODDS_REPORT.md: phase-aware; mate-in-n (|cp| >= 9000) counts as +-clip; only an actual
    checkmate on the board (|cp| >= 10000) is certain."""
    if cp_white is None: return [0.5, 0, 0.5]
    if abs(cp_white) >= 10000: return [1, 0, 0] if cp_white > 0 else [0, 0, 1]
    band = band or model["defaultBand"]
    b0 = model["bands"].get(js_key(band)) or model["bands"][js_key(js_nearest_band(model, band))]
    b = (b0.get("phases") or {}).get(phase) if phase else None
    b = b or b0
    cp = max(-model["clip"], min(model["clip"], cp_white))
    z = b["a"] * cp / 100 + (b.get("c") or 0)
    s = lambda x: 1 / (1 + math.exp(-x))
    pl = s(b["t1"] - z); pw = 1 - s(b["t2"] - z); pd = max(0, 1 - pl - pw)
    return [pw, pd, pl]


def js_human(model, cp_white, band=None):
    if cp_white is None: return [0.5, 0, 0.5]
    if abs(cp_white) >= 9000: return [1, 0, 0] if cp_white > 0 else [0, 0, 1]
    band = band or model["defaultBand"]
    b = model["bands"].get(js_key(band)) or model["bands"][js_key(js_nearest_band(model, band))]
    cp = max(-model["clip"], min(model["clip"], cp_white))
    z = b["a"] * cp / 100 + (b.get("c") or 0)
    s = lambda x: 1 / (1 + math.exp(-x))
    pl = s(b["t1"] - z); pw = 1 - s(b["t2"] - z); pd = max(0, 1 - pl - pw)
    return [pw, pd, pl]


# ----------------------------------------------------------------------------------------------------------------------
# Stage 1 report: dataset counts, alignment and sign checks
# ----------------------------------------------------------------------------------------------------------------------

def report_parse(recs):
    from collections import Counter
    META = {}
    print("\n=== DATA ===")
    print(f"lines/games: {len(recs)} (unique ids {len(set(r['id'] for r in recs))})")
    C = Counter((r["variant"], r["rated"], r["speed"]) for r in recs)
    print("variant/rated/speed:", dict(C))
    lens = Counter("eq" if r["n_an"] == r["n"] else "n-1" if r["n_an"] == r["n"] - 1 else "none" if r["n_an"] == 0 else "other" for r in recs)
    print("len(analysis) vs plies:", dict(lens))
    oth = [r for r in recs if r["n_an"] not in (r["n"], r["n"] - 1, 0)]
    if oth:
        dd = Counter(np.sign(r["n_an"] - r["n"]) for r in oth)
        print(f"  'other' games: {len(oth)}; analysis shorter: {dd.get(-1,0)}, longer: {dd.get(1,0)}; e.g. {[(r['id'], r['n'], r['n_an']) for r in oth[:5]]}")
    ok = [r for r in recs if not r.get("skip")]
    rep_fail = sum(1 for r in ok if not r["chk"]["replay_ok"])
    print(f"replay failures: {rep_fail}")
    # checkmate games: analysis length
    cm = [r for r in ok if r["chk"]["final_checkmate"]]
    print(f"games ending in checkmate: {len(cm)}; analysis len == plies-1 for {sum(r['n_an']==r['n']-1 for r in cm)} of them "
          f"(the mated final position has no eval, consistent with analysis[i] = position after ply i+1)")
    # alignment by judgment 'best' moves
    h0 = sum(r["chk"]["best_h0"] for r in ok); h0l = sum(r["chk"]["best_h0_legal"] for r in ok)
    h1 = sum(r["chk"]["best_h1"] for r in ok); h1l = sum(r["chk"]["best_h1_legal"] for r in ok)
    eq = sum(r["chk"]["judged_eq_best"] for r in ok)
    print(f"ALIGNMENT (judgment 'best' moves): H0 analysis[i] = after ply i+1 -> best legal in position after i plies: {h0l}/{h0} = {h0l/max(h0,1):.4%}")
    print(f"                                   H1 shifted by one ply -> best legal: {h1l}/{h1} = {h1l/max(h1,1):.4%}")
    print(f"                                   under H0 the judged move equals 'best' in {eq}/{h0} cases")
    offs = Counter(r["chk"].get("puzzle_off") for r in ok)
    pmo = [r["chk"]["puzzle_move_ok"] for r in ok if r["chk"].get("puzzle_move_ok") is not None]
    print(f"puzzle FEN = position after (url_ply + off) plies, off distribution: {dict(offs)}; puzzle first move == game move: {sum(pmo)}/{len(pmo)}")
    # sign: final mate entries vs winner; last eval vs winner
    sgn = Counter()
    for r in cm:
        mt = r["mate"]; nz = np.nonzero(mt)[0]
        if len(nz): sgn[(r["winner"], int(np.sign(mt[nz[-1]])))] += 1
    print("SIGN: checkmate games, sign of last mate entry by winner:", dict(sgn))
    last = Counter()
    for r in ok:
        if r["winner"] is None: continue
        v = r["cp"]; m = r["mate"]
        vv = [(float(np.sign(m[i])) if m[i] else float(np.sign(v[i]))) for i in range(len(v)) if m[i] or not np.isnan(v[i])]
        if vv: last[(r["winner"], vv[-1])] += 1
    print("SIGN: decisive games, sign of last available eval by winner:", dict(last))
    META.update(alignment=dict(best_legal_H0=[h0l, h0], best_legal_shifted=[h1l, h1], judged_equals_best=eq,
                               puzzle_fen_offset=({str(k): v for k, v in offs.items()}), checkmate_sign=({f"{k[0]}:{k[1]}": v for k, v in sgn.items()})))
    return META


# ----------------------------------------------------------------------------------------------------------------------
# Stage 2/3: Stockfish 17.1 sample + rescoring
# ----------------------------------------------------------------------------------------------------------------------

CP_BINS = [0, 50, 100, 200, 350, 600, 1000, np.inf]


def _fen_at(sans, ply):
    import chess
    B = chess.Board()
    for s in sans[:ply]: B.push_san(s)
    return B


def stage_sample(recs, prim, cache, n_map=2100, n_scale=3000):
    """Positions for Stockfish 17.1 re-evaluation (one per game):
       map   : ~2100 train games, stratified by |lichess cp| bin (7 bins + mate) x phase -> eval-scale mapping (engine vs engine)
       scale : 3000 other train games, one uniformly random post-blunder position -> outcome-based scale check
       test  : every test game, one uniformly random post-blunder position -> held-out check on real SF17 evals"""
    path = os.path.join(cache, "sf_sample_v2.json")
    if os.path.exists(path):
        with open(path) as f: return json.load(f)
    rng = np.random.default_rng(SEED)
    train = [i for i in prim if split_of(recs[i]["id"]) == "train"]
    test = [i for i in prim if split_of(recs[i]["id"]) == "test"]
    nstrata = (len(CP_BINS) - 1 + 1) * 3   # cp bins + mate, x 3 phases
    quota = int(math.ceil(n_map / nstrata))
    need = {(b, p): quota for b in range(len(CP_BINS)) for p in range(3)}
    picks = []; used = set()
    for gi in rng.permutation(train):
        if not any(v > 0 for v in need.values()): break
        r = recs[gi]; cp = r["cp"]; mt = r["mate"]
        valid = np.nonzero(~np.isnan(cp) | (mt != 0))[0]
        if len(valid) == 0: continue
        acp = np.abs(np.nan_to_num(cp[valid]))
        cb = np.where(mt[valid] != 0, len(CP_BINS) - 1, np.searchsorted(CP_BINS, acp, side="right") - 1)
        st = list(zip(cb.tolist(), r["phase"][valid].tolist()))
        avail = sorted({s for s in st if need.get(s, 0) > 0})
        if not avail: continue
        s = avail[rng.integers(len(avail))]
        cand = [valid[j] for j in range(len(valid)) if st[j] == s]
        k = int(cand[rng.integers(len(cand))])
        picks.append((int(gi), k + 1, "map", f"{s[0]}/{s[1]}")); need[s] -= 1; used.add(int(gi))
    rng2 = np.random.default_rng(SEED + 100)
    def post_pick(gi):
        r = recs[gi]; ps = r["chk"].get("puzzle_start")
        if ps is None: return None
        valid = np.nonzero(~np.isnan(r["cp"]) | (r["mate"] != 0))[0]
        valid = valid[valid + 1 >= ps + 1]
        if len(valid) == 0: return None
        return int(valid[rng2.integers(len(valid))]) + 1
    n_sc = 0
    for gi in rng2.permutation([i for i in train if i not in used]):
        if n_sc >= n_scale: break
        ply = post_pick(int(gi))
        if ply is None: continue
        picks.append((int(gi), ply, "scale", "post-uniform")); n_sc += 1
    for gi in sorted(test):
        ply = post_pick(int(gi))
        if ply is None: continue
        picks.append((int(gi), ply, "test", "post-uniform"))
    items = []
    for gi, ply, sset, stratum in picks:
        r = recs[gi]; B = _fen_at(r["sans"].split(), ply)
        if B.is_game_over(): continue
        cp = r["cp"]; mt = r["mate"]
        nb = lambda j: (None if j < 0 or j >= len(cp) else (None if np.isnan(cp[j]) and mt[j] == 0 else (float(cp[j]) if mt[j] == 0 else None)))
        items.append(dict(key=f"{r['id']}:{ply}", gi=gi, id=r["id"], ply=ply, fen=B.fen(), set=sset, stratum=stratum,
                          lcp=nb(ply - 1), lmate=int(mt[ply - 1]), l_prev=nb(ply - 2), l_next=nb(ply),
                          phase=int(r["phase"][ply - 1]), r=(r["wr"] + r["br"]) / 2, y=RES_CODE[r["winner"]],
                          year=time.gmtime(r["created"] / 1000).tm_year, speed=r["speed"],
                          post=bool(ply >= r["chk"].get("puzzle_start", 10 ** 9) + 1)))
    with open(path, "w") as f: json.dump(items, f)
    from collections import Counter
    print(f"[sample] {dict(Counter(i['set'] for i in items))} positions -> {path}")
    return items


def stage_rescore(items, cache, force=False):
    inp = os.path.join(cache, "sf_sample_v2.json"); out = os.path.join(cache, "sf_rescored_d14.ndjson")
    if force and os.path.exists(out): os.remove(out)
    have = set()
    if os.path.exists(out):
        for l in open(out):
            if l.strip(): have.add(json.loads(l)["key"])
    if any(it["key"] not in have for it in items):
        cmd = ["node", os.path.join(HERE, "sf_rescore.mjs"), inp, out, "--depth", "14", "--procs", "2"]
        print("[rescore] running", " ".join(cmd), flush=True)
        subprocess.run(cmd, check=True)
    res = {}
    for l in open(out):
        if l.strip():
            d = json.loads(l); res[d["key"]] = d
    return res


# ----------------------------------------------------------------------------------------------------------------------
# Stage 4: eval-scale mapping lichess cp -> SF17 cp
# ----------------------------------------------------------------------------------------------------------------------

def huber_fit(x, y, k=1.345, iters=100):
    X = np.stack([np.ones_like(x), x], 1)
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    for _ in range(iters):
        r = y - X @ b; s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-9
        w = np.minimum(1.0, k * s / np.maximum(np.abs(r), 1e-12))
        bn = np.linalg.lstsq(X * np.sqrt(w)[:, None], y * np.sqrt(w), rcond=None)[0]
        if np.max(np.abs(bn - b)) < 1e-10: b = bn; break
        b = bn
    return b  # intercept, slope


def stage_mapping(items, res, rng):
    from scipy.stats import theilslopes, spearmanr
    M = {}
    rows = []
    for it in items:
        d = res.get(it["key"])
        if not d or d["cpWhite"] is None: continue
        rows.append((it, d))
    mp = [(it, d) for it, d in rows if it["set"] == "map"]
    print("\n=== EVAL SCALE: Lichess server cp -> Stockfish 17.1 (depth 14) cp ===")
    print(f"mapping sample: {len(mp)} positions from {len(set(it['gi'] for it, d in mp))} train games (one per game), stratified by |cp| bin x phase")
    # alignment / sign check against SF17 (positions after ply k vs lichess entries k-2, k-1, k)
    al = {}
    for name, key in (("analysis[k-2] (one ply earlier)", "l_prev"), ("analysis[k-1] (H0: after ply k)", "lcp"), ("analysis[k] (one ply later)", "l_next")):
        xs, ys = [], []
        for it, d in mp:
            if it[key] is None or d["mate"] is not None or abs(d["cpWhite"]) >= 9000: continue
            xs.append(it[key]); ys.append(d["cpWhite"])
        rho = spearmanr(xs, ys).statistic
        al[name] = dict(n=len(xs), spearman=round(float(rho), 4))
        print(f"  Spearman(SF17 eval of position after ply k, lichess {name}) = {rho:.4f}  (n={len(xs)})")
    M["sf17_alignment_check"] = al
    # mate agreement
    lm = [(it, d) for it, d in mp if it["lmate"] != 0]
    agree = sum(1 for it, d in lm if np.sign(d["cpWhite"]) == np.sign(it["lmate"]))
    sfm = sum(1 for it, d in lm if d["mate"] is not None)
    print(f"  lichess mate positions: {len(lm)}; SF17 same sign: {agree}; SF17 also reports mate: {sfm}")
    M["lichess_mate_positions"] = dict(n=len(lm), sf17_same_sign=agree, sf17_mate=sfm)
    # linear fit on |cp| < 1000 (both engines non-mate)
    sel = [(it, d) for it, d in mp if it["lcp"] is not None and abs(it["lcp"]) < 1000 and d["mate"] is None and abs(d["cpWhite"]) < 9000]
    x = np.array([it["lcp"] for it, d in sel], float); y = np.array([d["cpWhite"] for it, d in sel], float)
    sel2 = np.abs(y) < 1000
    b_h = huber_fit(x, y)
    ts = theilslopes(y, x)
    ols = np.polyfit(x, y, 1)
    ols_rev = np.polyfit(y, x, 1)
    res_h = y - (b_h[0] + b_h[1] * x)
    r2 = 1 - np.sum((y - np.polyval(ols, x)) ** 2) / np.sum((y - y.mean()) ** 2)
    r2h = 1 - np.sum(res_h ** 2) / np.sum((y - y.mean()) ** 2)
    rsd = float(np.std(res_h)); rmad = float(1.4826 * np.median(np.abs(res_h - np.median(res_h))))
    # bootstrap CI for the Huber slope
    bs = []
    for _ in range(300):
        ii = rng.integers(0, len(x), len(x)); bs.append(huber_fit(x[ii], y[ii], iters=30)[1])
    print(f"  fit set: {len(x)} positions with |lichess cp| < 1000 and no mate in either engine")
    print(f"  Huber (robust) sf17 = {b_h[0]:.2f} + {b_h[1]:.4f} * lichess   slope 95% CI [{np.percentile(bs,2.5):.4f}, {np.percentile(bs,97.5):.4f}]  R^2 = {r2h:.4f}")
    print(f"  residual SD = {rsd:.1f} cp, robust SD (1.4826 MAD) = {rmad:.1f} cp")
    print(f"  Theil-Sen slope = {ts.slope:.4f} (intercept {ts.intercept:.2f}); OLS sf~L slope = {ols[0]:.4f} (R^2 {r2:.4f}); 1/OLS(L~sf) slope = {1/ols_rev[0]:.4f}")
    gm = math.sqrt(ols[0] / ols_rev[0])
    print(f"  geometric-mean (scale-ratio) slope = {gm:.4f}")
    # linearity: binned medians
    print("  binned check (lichess bin -> median SF17, median ratio SF17/lichess):")
    lin_tab = []
    for lo, hi in [(-1000, -600), (-600, -350), (-350, -200), (-200, -100), (-100, -50), (-50, 0), (0, 50), (50, 100), (100, 200), (200, 350), (350, 600), (600, 1000)]:
        m = (x >= lo) & (x < hi)
        if m.sum() < 5: continue
        ratio = np.median(y[m] / x[m]) if (lo >= 50 or hi <= -50) else float("nan")
        lin_tab.append([lo, hi, int(m.sum()), round(float(np.median(x[m])), 1), round(float(np.median(y[m])), 1), round(float(b_h[0] + b_h[1] * np.median(x[m])), 1)])
        print(f"    [{lo:5d},{hi:5d}) n={m.sum():4d}  median L {np.median(x[m]):7.1f}  median SF17 {np.median(y[m]):7.1f}  Huber line {b_h[0]+b_h[1]*np.median(x[m]):7.1f}  median ratio {ratio:.3f}")
    # by year and by phase
    yrs = np.array([it["year"] for it, d in sel]); phs = np.array([it["phase"] for it, d in sel])
    by_year = {}
    for yv in sorted(set(yrs.tolist())):
        m = yrs == yv
        if m.sum() >= 40:
            bh = huber_fit(x[m], y[m]); by_year[str(yv)] = [int(m.sum()), round(float(bh[1]), 4), round(float(bh[0]), 2)]
    by_phase = {}
    for pv, pn in ((0, "opening"), (1, "middlegame"), (2, "endgame")):
        m = phs == pv
        if m.sum() >= 40:
            bh = huber_fit(x[m], y[m]); by_phase[pn] = [int(m.sum()), round(float(bh[1]), 4), round(float(bh[0]), 2)]
    print(f"  Huber slope by game year [n, slope, intercept]: {by_year}")
    print(f"  Huber slope by phase [n, slope, intercept]: {by_phase}")
    M.update(method="Huber robust linear regression of SF17 depth-14 cp on Lichess server cp, |lichess cp| < 1000, no mate in either engine",
             n=int(len(x)), intercept=round(float(b_h[0]), 3), slope=round(float(b_h[1]), 5),
             slope_ci95=[round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
             r2=round(float(r2h), 4), resid_sd=round(rsd, 1), resid_robust_sd=round(rmad, 1),
             theil_sen_slope=round(float(ts.slope), 4), ols_slope=round(float(ols[0]), 4), inv_ols_rev_slope=round(float(1 / ols_rev[0]), 4),
             geometric_mean_slope=round(gm, 4), binned=lin_tab, slope_by_year=by_year, slope_by_phase=by_phase)
    # nonlinear candidates: power law (global, and with a per-year scale; alpha and p shared)
    from scipy.optimize import least_squares
    powf = lambda q, xx: q[0] + q[1] * np.sign(xx) * np.abs(xx) ** q[2]
    rp = least_squares(lambda q: powf(q, x) - y, [5.0, 1.5, 0.85], loss="huber", f_scale=40.0)
    rr = y - powf(rp.x, x)
    r2p = 1 - np.sum(rr ** 2) / np.sum((y - y.mean()) ** 2)
    print(f"  power law (Huber): sf17 = {rp.x[0]:.2f} + {rp.x[1]:.4f} * sign(L)|L|^{rp.x[2]:.4f}; R^2 = {r2p:.4f}; residual SD {np.std(rr):.1f}, robust SD {1.4826*np.median(np.abs(rr-np.median(rr))):.1f}")
    beta_year = {}
    for yv in sorted(set(yrs.tolist())):
        m = yrs == yv
        if m.sum() >= 30:
            rb_ = least_squares(lambda q: powf([rp.x[0], q[0], rp.x[2]], x[m]) - y[m], [rp.x[1]], loss="huber", f_scale=40.0)
            beta_year[int(yv)] = float(rb_.x[0])
    ry = y - np.array([powf([rp.x[0], beta_year.get(int(yv), rp.x[1]), rp.x[2]], xv) for xv, yv in zip(x, yrs)])
    r2y = 1 - np.sum(ry ** 2) / np.sum((y - y.mean()) ** 2)
    print(f"  power law, per-year beta: {{{', '.join(f'{k}: {v:.3f}' for k, v in beta_year.items())}}}; R^2 = {r2y:.4f}; robust SD {1.4826*np.median(np.abs(ry-np.median(ry))):.1f}")
    print("  binned medians vs power fits:", [[t[3], t[4], round(float(powf(rp.x, t[3])), 1)] for t in lin_tab])
    M["power"] = dict(alpha=round(float(rp.x[0]), 4), beta=round(float(rp.x[1]), 5), p=round(float(rp.x[2]), 5), r2=round(float(r2p), 4),
                      resid_sd=round(float(np.std(rr)), 1), resid_robust_sd=round(float(1.4826 * np.median(np.abs(rr - np.median(rr)))), 1))
    M["power_by_year"] = dict(beta_by_year={str(k): round(v, 5) for k, v in beta_year.items()}, r2=round(float(r2y), 4),
                              resid_robust_sd=round(float(1.4826 * np.median(np.abs(ry - np.median(ry)))), 1))
    cands = {"linear": Mapping("linear", b_h[0], b_h[1]), "power": Mapping("power", rp.x[0], rp.x[1], rp.x[2]),
             "power_by_year": Mapping("power", rp.x[0], rp.x[1], rp.x[2], beta_year)}
    return M, cands, rows


def select_mapping(recs, tr_idx, sfrows, cands, clip=800.0):
    """Choose the lichess->SF17 mapping with TRAIN data only: fit the 'lin' model (clip 800) on train post-blunder positions mapped with
    each candidate, then score it on the 'scale' sample (train games, real SF17 depth-14 evals, known outcomes)."""
    Sc = [(it, d) for it, d in sfrows if it["set"] == "scale"]
    sf = np.array([d["cpWhite"] for it, d in Sc], float); ys = np.array([it["y"] for it, d in Sc]); rs_ = np.array([it["r"] for it, d in Sc], float)
    sf = np.where(np.abs(sf) >= 9000, np.sign(sf) * 1e6, sf)
    Xs = dict(r=rs_, phase=np.ones(len(Sc), int), cp=np.clip(sf, -clip, clip))
    lin = Design("lin"); out = {}; lls = {}
    for nm, mp in cands.items():
        XA = flatten_mapped(recs, tr_idx, mp); X = subsample_per_game(subset_rew(XA, XA["post"]), 16, np.random.default_rng(SEED + 1))
        th, _ = fit(with_clip(X, clip), lin)
        ll, br = per_position_losses(predict(th, lin, Xs), ys); lls[nm] = ll
        out[nm] = dict(scale_sample_log_loss=round(float(ll.mean()), 5), brier=round(float(br.mean()), 5))
    for nm in cands:
        out[nm]["minus_linear_ci95"] = [round(v, 5) for v in boot_ci(lls[nm] - lls["linear"], 1000, np.random.default_rng(SEED + 30))]
    best = min(cands, key=lambda k: lls[k].mean())
    if best != "linear" and out[best]["minus_linear_ci95"][2] >= 0: best = "linear"   # keep the simplest unless clearly better
    print(f"  mapping selection on the TRAIN 'scale' sample ({len(Sc)} positions with real SF17 evals): {out} -> {best}")
    return best, out


# ----------------------------------------------------------------------------------------------------------------------
# Stage 5/6: model selection (train CV), final fit, held-out evaluation, export
# ----------------------------------------------------------------------------------------------------------------------

def with_clip(X, clip):
    """cp column for a given clip: mapped cp clipped, mates -> +-clip."""
    Y = dict(X)
    v = np.clip(X["cpm"], -clip, clip)
    Y["cp"] = np.where(X["mate"] > 0, clip, np.where(X["mate"] < 0, -clip, v))
    return Y


def year_of(r):
    return time.gmtime(r["created"] / 1000).tm_year


class Mapping:
    """lichess cp -> SF17 cp. kind 'linear': alpha + beta*L ; 'power': alpha + beta*sign(L)*|L|^p ; beta may depend on the game year."""
    def __init__(self, kind, alpha, beta, p=1.0, beta_year=None):
        self.kind, self.alpha, self.beta, self.p, self.beta_year = kind, float(alpha), float(beta), float(p), beta_year or {}

    def beta_for(self, year):
        if not self.beta_year: return self.beta
        ys = sorted(self.beta_year)
        return self.beta_year[min(ys, key=lambda y: (abs(y - year), y))]

    def __call__(self, v, year):
        v = np.asarray(v, float); b = self.beta_for(year)
        if self.kind == "linear": return self.alpha + b * v
        return self.alpha + b * np.sign(v) * np.abs(v) ** self.p

    def describe(self):
        if self.kind == "linear": f = f"sf17 = {self.alpha:.3f} + {self.beta:.5f} * L"
        else: f = f"sf17 = {self.alpha:.3f} + beta * sign(L) * |L|^{self.p:.4f}"
        d = dict(kind=self.kind, formula=f, alpha=round(self.alpha, 4), beta=round(self.beta, 5), p=round(self.p, 5))
        if self.beta_year: d["beta_by_year"] = {str(k): round(v, 5) for k, v in sorted(self.beta_year.items())}; d["year_rule"] = "games from other years use the nearest fitted year"
        return d


def flatten_mapped(recs, idx, mapping):
    X = flatten([recs[i] for i in idx], lambda v, r: mapping(v, year_of(r)), 1e9)
    X["cpm"] = X.pop("cp")
    X["gid"] = np.asarray(idx)[X["g"]]
    return X


def subsample_per_game(X, k, rng):
    """Keep at most k random positions per game; re-weight so each game sums to 1."""
    g = X["g"]; order = rng.permutation(len(g))
    gs = g[order]
    srt = np.argsort(gs, kind="stable"); order = order[srt]; gs = gs[srt]
    first = np.r_[0, np.nonzero(np.diff(gs))[0] + 1]
    rank = np.arange(len(gs)) - np.repeat(first, np.diff(np.r_[first, len(gs)]))
    keep = np.sort(order[rank < k])
    Y = subset(X, np.isin(np.arange(len(g)), keep))
    cnt = np.bincount(Y["g"]); Y["w"] = 1.0 / cnt[Y["g"]]
    return Y


def cv_oof(X, design, folds, clip, theta0=None):
    """Out-of-fold predictions (5 folds by game). Returns per-position log loss, brier and predicted (pw,pd,pl)."""
    Xc = with_clip(X, clip)
    ll = np.zeros(len(Xc["y"])); br = np.zeros(len(Xc["y"])); P = np.zeros((len(Xc["y"]), 3))
    for f in range(5):
        tr = folds != f; va = ~tr
        th, _ = fit(subset(Xc, tr), design, theta0)
        p = predict(th, design, subset(Xc, va))
        l, b = per_position_losses(p, Xc["y"][va]); ll[va] = l; br[va] = b; P[va] = np.stack(p, 1)
    return ll, br, P


def provisional(cp_sf):
    """js/prob.js provisional model on SF-scale cp (mates already mapped to +-2000 by the caller)."""
    cp = np.clip(cp_sf, -2000, 2000)
    wc = 2 / (1 + np.exp(-0.00368208 * cp)) - 1; es = (wc + 1) / 2
    d = 0.06 * (1 - np.abs(wc))
    w = np.maximum(0, es - d / 2)
    return w, d, np.maximum(0, 1 - w - d)


def weighted_deciles(es, w, nq=10):
    o = np.argsort(es); cw = np.cumsum(w[o]) / w.sum()
    q = np.minimum((cw * nq).astype(int), nq - 1)
    out = np.empty(len(es), int); out[o] = q
    return out


def calib_table(es_pred, y, w, g, nq=10):
    q = weighted_deciles(es_pred, w, nq)
    score = y / 2.0
    rows = []
    for k in range(nq):
        m = q == k
        if not m.any(): continue
        rows.append([k + 1, int(m.sum()), int(len(np.unique(g[m]))), round(float(np.average(es_pred[m], weights=w[m])), 4),
                     round(float(np.average(score[m], weights=w[m])), 4)])
    return rows


CP_TAB = [("mate-", -2e6, -9e5), ("<-1000", -9e5, -1000), ("-1000..-600", -1000, -600), ("-600..-300", -600, -300), ("-300..-150", -300, -150),
          ("-150..-50", -150, -50), ("-50..50", -50, 50), ("50..150", 50, 150), ("150..300", 150, 300), ("300..600", 300, 600),
          ("600..1000", 600, 1000), (">1000", 1000, 9e5), ("mate+", 9e5, 2e6)]


def subset_rew(X, m):
    Y = subset(X, m)
    cnt = np.bincount(Y["g"], minlength=(X["g"].max() + 1)); Y["w"] = 1.0 / cnt[Y["g"]]
    return Y


def emp_table(X, mask):
    """Game-weighted outcome shares (White win / draw / Black win) by SF17-scale cp bin; mates as their own bins."""
    Y = subset_rew(X, mask)
    cp = np.where(Y["mate"] > 0, 1e6, np.where(Y["mate"] < 0, -1e6, Y["cpm"]))
    rows = []
    for lab, lo, hi in CP_TAB:
        m = (cp >= lo) & (cp < hi)
        if not m.any(): continue
        w = Y["w"][m]; y = Y["y"][m]
        rows.append([lab, int(m.sum()), round(float(np.average(y == 2, weights=w)), 3), round(float(np.average(y == 1, weights=w)), 3),
                     round(float(np.average(y == 0, weights=w)), 3)])
    return rows


def signed_slope(X, clip=1000.0):
    """Weighted binary logit P(White wins | decisive) = s(b0 + b1*cp/100), cp clipped; b1 is allowed to be negative."""
    d = X["y"] != 1
    cp = np.clip(np.where(X["mate"] > 0, clip, np.where(X["mate"] < 0, -clip, X["cpm"])), -clip, clip)[d] / 100.0
    yy = (X["y"][d] == 2).astype(float); w = X["w"][d]
    def f(b):
        z = b[0] + b[1] * cp; p = sig(z)
        return -(w * (yy * log_sig(z) + (1 - yy) * log_sig(-z))).sum() / w.sum(), -np.array([(w * (yy - p)).sum(), (w * (yy - p) * cp).sum()]) / w.sum()
    return minimize(f, np.zeros(2), jac=True, method="BFGS").x


def run_rest(recs, args, meta0):
    from collections import Counter
    from scipy.optimize import minimize_scalar
    rng = np.random.default_rng(SEED)
    META = dict(meta0)
    mr = lambda r: (r["wr"] + r["br"]) / 2
    # ---------------------------------------------------------------- filters / sets
    elig = [i for i, r in enumerate(recs) if eligible(r)]
    close = [i for i in elig if abs(recs[i]["wr"] - recs[i]["br"]) <= 150]
    prim = [i for i in close if recs[i]["speed"] in ("rapid", "classical") and mr(recs[i]) >= 1450]
    blitz = [i for i in close if recs[i]["speed"] == "blitz" and mr(recs[i]) >= 1450]
    bullet = [i for i in close if recs[i]["speed"] == "bullet" and mr(recs[i]) >= 1450]
    low = [i for i in close if mr(recs[i]) < 1450]
    print("\n=== FILTERS ===")
    excl = Counter(("skip" if r.get("skip") else "unrated" if not r["rated"] else "replay" if not r["chk"]["replay_ok"] else r["status"] if r["status"] in ("cheat", "aborted", "noStart", "unknownFinish") else "ok") for r in recs)
    print("eligibility:", dict(excl))
    print(f"eligible rated standard games with analysis: {len(elig)}; |white-black| <= 150: {len(close)} ({len(close)/len(elig):.1%})")
    sp = Counter(recs[i]["speed"] for i in close)
    print(f"  by speed (|diff|<=150): {dict(sp)}")
    print(f"PRIMARY set (rapid+classical, |diff|<=150, mean rating >= 1450): {len(prim)} games; blitz: {len(blitz)}; bullet: {len(bullet)}; mean rating < 1450 (all speeds): {len(low)}")
    tr_idx = [i for i in prim if split_of(recs[i]["id"]) == "train"]
    te_idx = [i for i in prim if split_of(recs[i]["id"]) == "test"]
    print(f"split by md5(game id) % 100 < 80: train {len(tr_idx)} games, test {len(te_idx)} games")
    META["data"] = dict(source=os.path.basename(args.data), games_total=len(recs), eligibility=dict(excl), eligible=len(elig),
                        abs_diff_le_150=len(close), by_speed_abs_diff_le_150=dict(sp), primary=len(prim), primary_train=len(tr_idx),
                        primary_test=len(te_idx), blitz=len(blitz), bullet=len(bullet), below_1450=len(low),
                        filters="rated, standard, server analysis present, replay OK, status not cheat, |white-black| <= 150, speed rapid or classical, mean rating >= 1450; "
                                "positions: only those AFTER the puzzle's blunder move (see selection_bias)",
                        split="md5(game id) % 100 >= 80 -> test (20 %), else train; CV folds md5('cv|'+id) % 5 on train only")
    print("\n=== OUTCOMES (game level) ===")
    out_rates = {}
    for name, S in (("primary", prim), ("blitz", blitz), ("all eligible", elig)):
        y = np.array([RES_CODE[recs[i]["winner"]] for i in S])
        out_rates[name] = dict(n=len(S), white=round(float(np.mean(y == 2)), 4), draw=round(float(np.mean(y == 1)), 4), black=round(float(np.mean(y == 0)), 4))
        print(f"  {name}: n={len(S)} white {np.mean(y==2):.3f} draw {np.mean(y==1):.3f} black {np.mean(y==0):.3f}")
    st = Counter(recs[i]["status"] for i in prim)
    print(f"  primary status: {dict(st)}; decided on time (outoftime/timeout): {(st['outoftime']+st['timeout'])/len(prim):.3f}")
    META["outcomes"] = dict(rates=out_rates, primary_status=dict(st))

    # ---------------------------------------------------------------- SF17 sample + mapping
    items = stage_sample(recs, prim, args.cache)
    if args.stage == "sample": return
    res = stage_rescore(items, args.cache, args.force_rescore)
    if args.stage == "rescore": return
    MAP, cands, sfrows = stage_mapping(items, res, rng)
    META["eval_scale"] = MAP
    mname, msel = select_mapping(recs, tr_idx, sfrows, cands)
    mapping = cands[mname]
    MAP["selection"] = dict(rule="lowest log loss of a clip-800 'lin' model on the TRAIN scale sample (real SF17 evals); linear kept unless the CI of the difference excludes 0",
                            candidates=msel, chosen=mname, chosen_mapping=mapping.describe())
    MAP["model_units"] = (f"Every Lichess eval is converted to SF17 units with the chosen mapping ({mapping.describe()['formula']}) BEFORE fitting; "
                          "the fitted a, t1, t2, clip are in Stockfish-17.1 centipawns (then multiplied by the outcome-based SF17 rescale s if that rule fires; see sf17_rescale) "
                          "and c = 0. Lichess mate scores count as +-clip.")

    # ---------------------------------------------------------------- flatten; post-blunder subsets
    XtrA = flatten_mapped(recs, tr_idx, mapping); XteA = flatten_mapped(recs, te_idx, mapping)
    Xtr = subset_rew(XtrA, XtrA["post"]); Xte = subset_rew(XteA, XteA["post"])

    # ---------------------------------------------------------------- selection bias (train games only)
    print("\n=== PUZZLE-SELECTION BIAS (train games) ===")
    print("  lichess-puzzler generator.py: walks the game in order, returns the FIRST puzzle found (one per game), never reads moves after the")
    print("  puzzle position or the result; a candidate needs the solver NOT winning before the blunder (prev score <= +300 cp, not up in material)")
    print("  and a jump of > 0.6 in win chances; games with any player rated <= 1500 or <= 60 s total time are skipped (tier 0).")
    tpre = emp_table(XtrA, XtrA["pre"]); tpost = emp_table(XtrA, XtrA["post"])
    print("  game-weighted outcome shares [cp bin (SF17 units), positions, White, draw, Black]:")
    print("   BEFORE the puzzle blunder (ply <= puzzle FEN ply):")
    for r_ in tpre: print("    ", r_)
    print("   AFTER the puzzle blunder:")
    for r_ in tpost: print("    ", r_)
    s_pre = signed_slope(subset_rew(XtrA, XtrA["pre"])); s_post = signed_slope(subset_rew(XtrA, XtrA["post"]))
    print(f"  signed logit slope of P(White win | decisive) per 100 cp (clip 1000): before {s_pre[1]:+.4f}, after {s_post[1]:+.4f}")
    G = np.array([RES_CODE[recs[i]["winner"]] for i in tr_idx]); Pz = np.array([recs[i]["chk"]["puzzle_start"] for i in tr_idx])
    wb = Pz % 2 == 0
    o_wb = [round(float(np.mean(G[wb] == k)), 3) for k in (2, 1, 0)]; o_bb = [round(float(np.mean(G[~wb] == k)), 3) for k in (2, 1, 0)]
    print(f"  games where White makes the puzzle blunder: {wb.mean():.3f}; outcome W/D/B then {o_wb}; when Black blunders {o_bb}")
    npost = np.bincount(Xtr["g"]);
    print(f"  train positions: all {len(XtrA['y'])}, before {int(XtrA['pre'].sum())}, after {int(XtrA['post'].sum())} "
          f"(games with >= 1 position after: {len(np.unique(Xtr['g']))}/{len(tr_idx)}); puzzle FEN ply quantiles 5/25/50/75/95%: {np.percentile(Pz,[5,25,50,75,95]).tolist()}")
    ph_c = Counter(Xtr["phase"].tolist())
    print(f"  phases of post-blunder train positions: opening {ph_c[0]}, middlegame {ph_c[1]}, endgame {ph_c[2]}; plies <= 10: {int((Xtr['ply'] <= 10).sum())}")
    META["selection_bias"] = dict(
        source="https://github.com/ornicar/lichess-puzzler/blob/master/generator/generator.py (fetched 2026-10-12): analyze_game returns the first puzzle in move order; "
               "analyze_position requires prev_score <= +300 (unless mate soon), solver not up in material, score >= +200 and win-chance jump > 0.6; "
               "main() skips tier-0 games (a player rated <= 1500, or base+40*inc <= 60 s)",
        decision="fit and evaluate on positions AFTER the puzzle blunder only (their future is not used by the selection); positions before it are biased by construction",
        before=tpre, after=tpost, signed_slope_per_100cp=dict(before=round(float(s_pre[1]), 4), after=round(float(s_post[1]), 4)),
        outcome_when_white_blunders=o_wb, outcome_when_black_blunders=o_bb,
        positions_train=dict(all=int(len(XtrA["y"])), before=int(XtrA["pre"].sum()), after=int(XtrA["post"].sum())),
        post_phase_counts_train=dict(opening=ph_c[0], middlegame=ph_c[1], endgame=ph_c[2]))

    folds = np.array([fold_of(recs[i]["id"]) for i in tr_idx])
    print(f"\npost-blunder positions: train {len(Xtr['y'])} ({len(np.unique(Xtr['g']))} games), test {len(Xte['y'])} ({len(np.unique(Xte['g']))} games)")
    bands_all = list(range(1500, 2600, 100))
    def band_counts(X):
        bb = np.round(X["r"] / 100) * 100
        out = {}
        for b in sorted(set(bb.tolist())):
            m = bb == b
            out[str(int(b))] = [int(len(np.unique(X["g"][m]))), int(m.sum())]
        return out
    META["sample_sizes"] = dict(note="post-blunder positions per band (round(mean rating/100)*100): [games, positions]",
                                train=band_counts(Xtr), test=band_counts(Xte),
                                phases_train=dict(Counter({["opening", "middlegame", "endgame"][k]: v for k, v in Counter(Xtr["phase"].tolist()).items()})),
                                phases_test=dict(Counter({["opening", "middlegame", "endgame"][k]: v for k, v in Counter(Xte["phase"].tolist()).items()})))
    print("per band [games, positions] train:", META["sample_sizes"]["train"])
    print("per band [games, positions] test :", META["sample_sizes"]["test"])
    Xcv = subsample_per_game(Xtr, 16, np.random.default_rng(SEED + 1))
    fcv = folds[Xcv["g"]]
    print(f"CV uses at most 16 random post-blunder positions per train game ({len(Xcv['y'])} positions), 5 folds by md5('cv|'+id)")
    oof_game = lambda v, X: game_means(v, X["g"], X["w"])

    # ---------------------------------------------------------------- CV: clip
    print("\n=== MODEL SELECTION (5-fold CV on TRAIN games only; game-weighted out-of-fold log loss) ===")
    lin = Design("lin"); linp = Design("lin", phases=True)
    cv = {}
    for clip in (400, 600, 800, 1000, 1500, 2000):
        ll, br, _ = cv_oof(Xcv, lin, fcv, clip)
        cv[clip] = oof_game(ll, Xcv)
        print(f"  clip {clip:5d}: OOF log loss {cv[clip].mean():.5f}  brier {oof_game(br, Xcv).mean():.5f}")
    best_clip = min(cv, key=lambda c: cv[c].mean())
    rb = np.random.default_rng(SEED + 2)
    clip_tab = {str(c): [round(float(gl.mean()), 5)] + [round(v, 5) for v in boot_ci(gl - cv[best_clip], 1000, rb)[1:]] for c, gl in cv.items()}
    print(f"  -> clip = {best_clip}; [OOF log loss, 95% CI of difference to best]: {clip_tab}")
    CLIP = best_clip
    # ---------------------------------------------------------------- CV: rating dependence
    designs = {"pooled": Design("pooled"), "lin": lin, "quad": Design("quad"), "band": Design("band", bands=bands_all)}
    dres = {}
    for nm, ds in designs.items():
        ll, br, _ = cv_oof(Xcv, ds, fcv, CLIP)
        dres[nm] = (oof_game(ll, Xcv), oof_game(br, Xcv))
        print(f"  design {nm:6s}: OOF log loss {dres[nm][0].mean():.5f}  brier {dres[nm][1].mean():.5f}")
    des_tab = {nm: [round(float(dres[nm][0].mean()), 5)] + [round(v, 5) for v in boot_ci(dres[nm][0] - dres["lin"][0], 1000, rb)] for nm in dres}
    print(f"  [OOF log loss, mean/lo/hi of difference vs 'lin']: {des_tab}")
    # ---------------------------------------------------------------- CV: phases
    llp, brp, _ = cv_oof(Xcv, linp, fcv, CLIP)
    gp = oof_game(llp, Xcv); g0 = dres["lin"][0]
    red = g0 - gp; rel = red.mean() / g0.mean(); ci = boot_ci(red, 1000, rb)
    ci_rel = (ci[1] / g0.mean(), ci[2] / g0.mean())
    use_phases_cv = bool(rel >= 0.005 and ci[1] > 0)
    print(f"  phases: OOF log loss {gp.mean():.5f} vs {g0.mean():.5f}; reduction {red.mean():.5f} [{ci[1]:.5f}, {ci[2]:.5f}] = {rel:.3%} relative "
          f"[{ci_rel[0]:.3%}, {ci_rel[1]:.3%}] -> rule (>= 0.5% and CI > 0) {'MET' if use_phases_cv else 'NOT met'} on train CV")
    META["model_selection"] = dict(note="5-fold CV by game on TRAIN games only (<=16 post-blunder positions per game, each game weight 1); values: [OOF log loss, lo, hi of the "
                                        "95% game-bootstrap CI of the difference to the best clip / to 'lin']",
                                   clip=clip_tab, chosen_clip=CLIP, design=des_tab,
                                   phases=dict(oof_ll_without=round(float(g0.mean()), 5), oof_ll_with=round(float(gp.mean()), 5),
                                               reduction=round(float(red.mean()), 5), reduction_ci95=[round(ci[1], 5), round(ci[2], 5)],
                                               relative=round(float(rel), 5), relative_ci95=[round(ci_rel[0], 5), round(ci_rel[1], 5)], rule_met=use_phases_cv),
                                   first_plies="not applicable: post-blunder positions start after the puzzle (5% quantile of the puzzle ply = 20); "
                                               f"{int((Xtr['ply'] <= 10).sum())} train positions have ply <= 10; all kept")
    print("  -> design: lin (log a, mid-cut, log draw-width linear in rating): the extrapolation form for bands below the data")

    # ---------------------------------------------------------------- checks on train data
    print("\n=== CHECKS ON TRAIN DATA (post-blunder positions) ===")
    grid_cp = np.array([-500, -300, -200, -100, -50, 0, 50, 100, 200, 300, 500], float)
    def es_curve(th, ds, band):
        F = ds.feats(np.full(len(grid_cp), float(band)), np.ones(len(grid_cp), int)); k = ds.nparams()
        a, t1, t2 = params_at(th, F, k); pw, pd, pl = probs(a, t1, t2, np.clip(grid_cp, -CLIP, CLIP)); return pw + pd / 2, pd
    th_tr, _ = fit(with_clip(Xcv, CLIP), lin)
    checks = {}
    def compare(name, Xo):
        th_o, _ = fit(with_clip(Xo, CLIP), lin)
        rows = {}
        for band in (1500, 1800, 2100):
            e0, d0 = es_curve(th_tr, lin, band); e1, d1 = es_curve(th_o, lin, band)
            rows[str(band)] = dict(max_abs_es_diff=round(float(np.max(np.abs(e1 - e0))), 4), es_at_100=[round(float(e0[7]), 4), round(float(e1[7]), 4)],
                                   es_at_300=[round(float(e0[9]), 4), round(float(e1[9]), 4)], draw_at_0=[round(float(d0[5]), 4), round(float(d1[5]), 4)])
        print(f"  {name} ({len(np.unique(Xo['g']))} games): vs primary, per band: max |dES| over cp -500..500, [primary, this] ES@+100, ES@+300, P(draw)@0:")
        for b_, v_ in rows.items(): print(f"     {b_}: {v_}")
        return th_o, rows
    XblA = flatten_mapped(recs, [i for i in blitz if split_of(recs[i]["id"]) == "train"], mapping)
    Xbl = subsample_per_game(subset_rew(XblA, XblA["post"]), 16, np.random.default_rng(SEED + 3))
    th_bl, checks["blitz_vs_rapid_classical"] = compare("blitz, train games", Xbl)
    l_pr, _ = per_position_losses(predict(th_tr, lin, with_clip(Xcv, CLIP)), Xcv["y"]); l_bl, _ = per_position_losses(predict(th_bl, lin, with_clip(Xcv, CLIP)), Xcv["y"])
    cib = boot_ci(game_means(l_bl - l_pr, Xcv["g"], Xcv["w"]), 1000, rb)
    print(f"  blitz-fitted model on rapid/classical train positions: log loss higher by {fmt_ci(cib)} ({cib[0]/game_means(l_pr, Xcv['g'], Xcv['w']).mean():.2%}; in-sample for the primary fit)")
    checks["blitz_model_on_rapid_classical_ll_increase"] = [round(v, 5) for v in cib]
    sp_arr = np.array([recs[i]["speed"] for i in tr_idx])[Xcv["g"]]
    _, checks["classical_only"] = compare("classical only, train", subset_rew(Xcv, sp_arr == "classical"))
    _, checks["rapid_only"] = compare("rapid only, train", subset_rew(Xcv, sp_arr == "rapid"))
    stat_arr = np.array([recs[i]["status"] for i in tr_idx])[Xcv["g"]]
    _, checks["without_flag_losses"] = compare("excluding outoftime/timeout games, train", subset_rew(Xcv, ~np.isin(stat_arr, ["outoftime", "timeout"])))
    pzl = np.array([recs[i]["chk"]["puzzle_start"] + max(recs[i]["pz_moves"], 1) for i in tr_idx])[Xcv["g"]]
    _, checks["after_whole_puzzle_line"] = compare("positions after the whole puzzle line, train", subset_rew(Xcv, Xcv["ply"] >= pzl))
    META["checks_train"] = checks

    # ---------------------------------------------------------------- final fits on all train post-blunder positions
    print("\n=== FINAL FIT (all train post-blunder positions, each game weight 1) ===")
    Xtr_c = with_clip(Xtr, CLIP); Xte_c = with_clip(Xte, CLIP)
    th_fin, r_fin = fit(Xtr_c, lin)
    print(f"  lin   : converged={r_fin.success} nll={r_fin.fun:.6f} theta={np.round(th_fin, 5).tolist()}")
    th_pool, r_pool = fit(Xtr_c, Design("pooled"))
    print(f"  pooled: converged={r_pool.success} nll={r_pool.fun:.6f} theta={np.round(th_pool, 5).tolist()}")
    th_ph, r_ph = fit(Xtr_c, linp)
    print(f"  lin+phases: converged={r_ph.success} nll={r_ph.fun:.6f} theta={np.round(th_ph, 5).tolist()}")
    nb = 100
    rbp = np.random.default_rng(SEED + 4)
    Xcvc = with_clip(Xcv, CLIP)
    ug, start = np.unique(Xcvc["g"], return_index=True); ends = np.r_[start[1:], len(Xcvc["g"])]
    assert np.all(np.diff(Xcvc["g"]) >= 0)
    boot_th, boot_thp = [], []
    for _ in range(nb):
        pick = rbp.integers(0, len(ug), len(ug))
        ii = np.concatenate([np.arange(start[j], ends[j]) for j in pick])
        Xb = {k: v[ii] for k, v in Xcvc.items()}
        boot_th.append(fit(Xb, lin, th_fin)[0]); boot_thp.append(fit(Xb, linp, th_ph)[0])
    boot_th = np.array(boot_th); boot_thp = np.array(boot_thp)
    print(f"  parameter bootstrap: {nb} game-bootstrap refits (<= 16 positions per game)")

    # ---------------------------------------------------------------- SF17 rescale (TRAIN 'scale' sample: real SF17 evals + outcomes)
    print("\n=== SF17 RESCALE CHECK (TRAIN 'scale' sample: one random post-blunder position per game, real SF17 depth-14 evals) ===")
    cl = lambda v: np.clip(v, -CLIP, CLIP)
    Sc = [(it, d) for it, d in sfrows if it["set"] == "scale"]
    s_cp = np.array([d["cpWhite"] for it, d in Sc], float); ys = np.array([it["y"] for it, d in Sc]); rs_ = np.array([it["r"] for it, d in Sc], float)
    ph_s = np.array([it["phase"] for it, d in Sc]); s_cp = np.where(np.abs(s_cp) >= 9000, np.sign(s_cp) * 1e6, s_cp)
    def nll_s(sv, ii, th_, ds_):
        P = predict(th_, ds_, dict(r=rs_[ii], phase=ph_s[ii], cp=cl(sv * s_cp[ii])))
        return per_position_losses(P, ys[ii])[0].mean()
    alli = np.arange(len(ys)); resc = {}
    for nm, th_, ds_ in (("model", th_fin, lin), ("model_with_phases", th_ph, linp)):
        s_hat = minimize_scalar(lambda sv: nll_s(sv, alli, th_, ds_), bounds=(0.3, 3.0), method="bounded").x
        rsb = np.random.default_rng(SEED + 15); sb = []
        for _ in range(200):
            ii = rsb.integers(0, len(ys), len(ys)); sb.append(minimize_scalar(lambda sv: nll_s(sv, ii, th_, ds_), bounds=(0.3, 3.0), method="bounded").x)
        resc[nm] = dict(multiplier=round(float(s_hat), 4), ci95=[round(float(np.percentile(sb, 2.5)), 4), round(float(np.percentile(sb, 97.5)), 4)],
                        ll_at_1=round(float(nll_s(1.0, alli, th_, ds_)), 5), ll_at_s=round(float(nll_s(s_hat, alli, th_, ds_)), 5))
        print(f"  {nm}: likelihood-maximising multiplier on SF17 cp s = {s_hat:.3f} [{np.percentile(sb,2.5):.3f}, {np.percentile(sb,97.5):.3f}]; "
              f"log loss at s=1 {resc[nm]['ll_at_1']:.5f}, at s {resc[nm]['ll_at_s']:.5f}  (n={len(ys)})")
    ci_s = resc["model"]["ci95"]
    S_MULT = float(resc["model"]["multiplier"]) if (ci_s[0] > 1 or ci_s[1] < 1) else 1.0
    print(f"  rule: apply s (from the top-level model) to every exported parameter set if its 95% CI excludes 1 -> s = {S_MULT:.4f} "
          f"(exported a = a*s, clip = {CLIP}/s; i.e. P(outcome | SF17 cp) = fitted model at s*cp)")
    META["eval_scale"]["sf17_rescale"] = dict(rule="multiplier s on SF17 cp maximising the likelihood on the TRAIN scale sample; applied if its 95% bootstrap CI excludes 1",
                                              n=len(ys), checks=resc, applied=S_MULT)

    # ---------------------------------------------------------------- held-out test evaluation
    print("\n=== HELD-OUT TEST GAMES (post-blunder positions; untouched until now) ===")
    P_fin = predict(th_fin, lin, Xte_c); P_pool = predict(th_pool, Design("pooled"), Xte_c); P_ph = predict(th_ph, linp, Xte_c)
    def prov_on(X):
        return provisional(np.where(X["mate"] > 0, 2000.0, np.where(X["mate"] < 0, -2000.0, X["cpm"])))
    P_prov = prov_on(Xte)
    gte, wte = Xte["g"], Xte["w"]
    metr = {}; pg = {}
    for nm, P in (("model", P_fin), ("provisional", P_prov), ("pooled", P_pool), ("model_with_phases", P_ph)):
        ll, br = per_position_losses(P, Xte["y"])
        pg[nm] = (game_means(ll, gte, wte), game_means(br, gte, wte))
        a1 = boot_ci(pg[nm][0], args.boot, np.random.default_rng(SEED + 6)); a2 = boot_ci(pg[nm][1], args.boot, np.random.default_rng(SEED + 7))
        metr[nm] = dict(log_loss=[round(v, 5) for v in a1], brier=[round(v, 5) for v in a2])
        print(f"  {nm:18s} log loss {fmt_ci(a1)}   brier {fmt_ci(a2)}")
    for nm in ("provisional", "pooled", "model_with_phases"):
        dl = boot_ci(pg[nm][0] - pg["model"][0], args.boot, np.random.default_rng(SEED + 8))
        db = boot_ci(pg[nm][1] - pg["model"][1], args.boot, np.random.default_rng(SEED + 9))
        metr[f"{nm}_minus_model"] = dict(log_loss=[round(v, 5) for v in dl], brier=[round(v, 5) for v in db], relative_ll=round(dl[0] / pg["model"][0].mean(), 5))
        print(f"  {nm} - model: log loss {fmt_ci(dl)} ({dl[0]/pg['model'][0].mean():+.2%}), brier {fmt_ci(db)}")
    red_t = pg["model"][0] - pg["model_with_phases"][0]
    rel_t = red_t.mean() / pg["model"][0].mean(); ci_t = boot_ci(red_t, args.boot, np.random.default_rng(SEED + 10))
    use_phases_test = bool(rel_t >= 0.005 and ci_t[1] > 0)
    USE_PHASES = use_phases_cv and use_phases_test
    print(f"  phases on TEST: reduction {fmt_ci(ci_t)} = {rel_t:.3%} relative [{ci_t[1]/pg['model'][0].mean():.3%}, {ci_t[2]/pg['model'][0].mean():.3%}] -> rule {'MET' if use_phases_test else 'NOT met'}")
    print(f"  -> phases included in odds.json: {USE_PHASES} (decided on train CV, confirmed on test; both required)")
    metr["phases_rule"] = dict(test_reduction=[round(v, 5) for v in ci_t], test_relative=round(float(rel_t), 5),
                               test_relative_ci95=[round(ci_t[1] / pg["model"][0].mean(), 5), round(ci_t[2] / pg["model"][0].mean(), 5)],
                               met_on_test=use_phases_test, met_on_train_cv=use_phases_cv, included=USE_PHASES)
    bg_edges = [(1450, 1700), (1700, 1900), (1900, 2100), (2100, 2700)]
    rg = np.array([mr(recs[i]) for i in te_idx]); ug_te = np.unique(gte); rg_g = rg[ug_te]
    per_group = {}
    for lo, hi in bg_edges:
        m = (rg_g >= lo) & (rg_g < hi)
        row = {"games": int(m.sum())}
        for nm in ("model", "provisional", "pooled", "model_with_phases"):
            row[nm] = [round(v, 5) for v in boot_ci(pg[nm][0][m], args.boot, np.random.default_rng(SEED + 11))]
        per_group[f"{lo}-{hi-1}"] = row
        print(f"  band {lo}-{hi-1}: games {m.sum()}  log loss model {fmt_ci(row['model'])}  provisional {fmt_ci(row['provisional'])}  pooled {fmt_ci(row['pooled'])}  +phases {fmt_ci(row['model_with_phases'])}")
    metr["log_loss_by_band_group"] = per_group
    # transparency: the same models on test positions BEFORE the blunder (biased by construction) and on all positions
    print("  for comparison only, test positions BEFORE the puzzle blunder (selection-biased) and ALL test positions:")
    other_sets = {}
    for setname, msk in (("before_blunder", XteA["pre"]), ("all_positions", np.ones(len(XteA["y"]), bool))):
        Xo = subset_rew(XteA, msk); Xoc = with_clip(Xo, CLIP); row = {}
        for nm, P in (("model", predict(th_fin, lin, Xoc)), ("provisional", prov_on(Xo)), ("pooled", predict(th_pool, Design("pooled"), Xoc))):
            ll, br = per_position_losses(P, Xo["y"])
            row[nm] = dict(log_loss=[round(v, 5) for v in boot_ci(game_means(ll, Xo["g"], Xo["w"]), args.boot, np.random.default_rng(SEED + 19))],
                           brier=[round(v, 5) for v in boot_ci(game_means(br, Xo["g"], Xo["w"]), args.boot, np.random.default_rng(SEED + 20))])
        other_sets[setname] = row
        print(f"   {setname}: " + "; ".join(f"{k} LL {fmt_ci(v['log_loss'])}" for k, v in row.items()))
    metr["other_position_sets"] = other_sets
    # calibration
    print("\n  calibration on test (game-weighted deciles of predicted expected score; [decile, positions, games, mean predicted ES, observed score]):")
    cal = {}
    for nm, P in (("model", P_fin), ("provisional", P_prov), ("pooled", P_pool), ("model_with_phases", P_ph)):
        cal[nm] = calib_table(P[0] + P[1] / 2, Xte["y"], wte, gte)
        print(f"   {nm}:")
        for row in cal[nm]: print("    ", row)
    def gap(rows): return round(float(sum(r[1] * abs(r[3] - r[4]) for r in rows) / sum(r[1] for r in rows)), 4)
    print("   mean |predicted - observed| over deciles (position-weighted):", {k: gap(v) for k, v in cal.items()})
    cal_bg = {}
    for lo, hi in bg_edges:
        m = (Xte["r"] >= lo) & (Xte["r"] < hi)
        cal_bg[f"{lo}-{hi-1}"] = calib_table((P_fin[0] + P_fin[1] / 2)[m], Xte["y"][m], wte[m], gte[m], nq=5)
        print(f"   model, band {lo}-{hi-1} (quintiles):", cal_bg[f"{lo}-{hi-1}"])
    cal_ph = {}
    for pv, pn in ((0, "opening"), (1, "middlegame"), (2, "endgame")):
        m = Xte["phase"] == pv
        cal_ph[pn] = dict(model=calib_table((P_fin[0] + P_fin[1] / 2)[m], Xte["y"][m], wte[m], gte[m], nq=5),
                          model_with_phases=calib_table((P_ph[0] + P_ph[1] / 2)[m], Xte["y"][m], wte[m], gte[m], nq=5))
        print(f"   {pn} (quintiles): model {cal_ph[pn]['model']}\n{'':18s}with phases {cal_ph[pn]['model_with_phases']}")
    # draw check
    print("\n  draw-rate check on test (game-weighted): observed draw share vs mean predicted P(draw)")
    drw = {}
    acp = np.where(Xte["mate"] != 0, 1e9, np.abs(Xte["cpm"]))
    groups = [("all", np.ones(len(acp), bool))] + [(f"|cp| {lo}-{hi}", (acp >= lo) & (acp < hi)) for lo, hi in ((0, 50), (50, 150), (150, 300), (300, 600), (600, 1e8))] + \
             [("mate score", acp >= 1e8)] + [(f"band {lo}-{hi-1}", (Xte["r"] >= lo) & (Xte["r"] < hi)) for lo, hi in bg_edges] + \
             [(pn, Xte["phase"] == pv) for pv, pn in ((0, "opening"), (1, "middlegame"), (2, "endgame"))]
    for nm, m in groups:
        if not m.any(): continue
        ww = wte[m]
        row = dict(n=int(m.sum()), observed=round(float(np.average(Xte["y"][m] == 1, weights=ww)), 4),
                   model=round(float(np.average(P_fin[1][m], weights=ww)), 4), model_with_phases=round(float(np.average(P_ph[1][m], weights=ww)), 4),
                   provisional=round(float(np.average(P_prov[1][m], weights=ww)), 4), pooled=round(float(np.average(P_pool[1][m], weights=ww)), 4))
        drw[nm] = row; print(f"   {nm:16s} {row}")
    # mate-score positions: how often the side with the mate score wins (test, post-blunder)
    mm = Xte["mate"] != 0
    side_wins = np.where(Xte["mate"][mm] > 0, Xte["y"][mm] == 2, Xte["y"][mm] == 0)
    side_draws = Xte["y"][mm] == 1
    mate_rows = {"all": [int(mm.sum()), round(float(np.average(side_wins, weights=wte[mm])), 4), round(float(np.average(side_draws, weights=wte[mm])), 4)]}
    for lo, hi in bg_edges:
        m2 = (Xte["r"][mm] >= lo) & (Xte["r"][mm] < hi)
        if m2.any(): mate_rows[f"{lo}-{hi-1}"] = [int(m2.sum()), round(float(np.average(side_wins[m2], weights=wte[mm][m2])), 4), round(float(np.average(side_draws[m2], weights=wte[mm][m2])), 4)]
    pw_c, pd_c, pl_c = predict(th_fin, lin, dict(r=np.array([1800.0]), phase=np.array([1]), cp=np.array([float(CLIP)])))
    print(f"  Lichess mate-score positions (test): [positions, share won by the side with the mate score, draw share]: {mate_rows}; "
          f"model at +clip, band 1800: win {pw_c[0]:.4f} draw {pd_c[0]:.4f}")
    metr["calibration_deciles"] = cal; metr["calibration_by_band_group_model"] = cal_bg; metr["calibration_by_phase"] = cal_ph
    metr["calibration_mean_abs_gap"] = {k: gap(v) for k, v in cal.items()}; metr["draw_check"] = drw; metr["mate_positions"] = mate_rows

    # ---------------------------------------------------------------- real SF17 evals on test positions
    print(f"\n  test: one random post-blunder position per test game, re-evaluated by Stockfish 17.1 depth 14 (models as exported, i.e. at s*cp with s = {S_MULT:.4f}):")
    T = [(it, d) for it, d in sfrows if it["set"] == "test"]
    sf_cp = np.array([d["cpWhite"] for it, d in T], float); y_t = np.array([it["y"] for it, d in T]); r_t = np.array([it["r"] for it, d in T], float)
    ph_t = np.array([it["phase"] for it, d in T])
    sf_mate = np.array([d["mate"] is not None or abs(d["cpWhite"]) >= 9000 for it, d in T])
    l_m = np.array([it["lmate"] != 0 for it, d in T])
    l_cp = np.array([(it["lcp"] if it["lcp"] is not None else 0.0) for it, d in T], float)
    l_mapped = np.where(l_m, np.sign([it["lmate"] for it, d in T]) * 1e6, np.array([float(mapping(v, it["year"])) for v, (it, d) in zip(l_cp, T)]))
    sf_v = np.where(sf_mate, np.sign(sf_cp) * 1e6, sf_cp)
    Xs = dict(r=r_t, phase=ph_t, cp=cl(S_MULT * sf_v)); Xl = dict(r=r_t, phase=ph_t, cp=cl(l_mapped)); Xs1 = dict(r=r_t, phase=ph_t, cp=cl(sf_v))
    sfP = {"model on SF17 cp": predict(th_fin, lin, Xs), "model on mapped Lichess cp (same positions)": predict(th_fin, lin, Xl),
           "model on SF17 cp without rescale (s=1)": predict(th_fin, lin, Xs1),
           "model_with_phases on SF17 cp": predict(th_ph, linp, Xs), "provisional on SF17 cp": provisional(np.where(sf_mate, np.sign(sf_cp) * 2000, sf_cp)),
           "pooled on SF17 cp": predict(th_pool, Design("pooled"), Xs)}
    sfres = {}; sfl = {}
    for nm, P in sfP.items():
        ll, br = per_position_losses(P, y_t); sfl[nm] = ll
        a1 = boot_ci(ll, args.boot, np.random.default_rng(SEED + 12)); a2 = boot_ci(br, args.boot, np.random.default_rng(SEED + 13))
        sfres[nm] = dict(log_loss=[round(v, 5) for v in a1], brier=[round(v, 5) for v in a2])
        print(f"   {nm:46s} n={len(T)} log loss {fmt_ci(a1)} brier {fmt_ci(a2)}")
    for nm in ("provisional on SF17 cp", "pooled on SF17 cp", "model on mapped Lichess cp (same positions)", "model on SF17 cp without rescale (s=1)", "model_with_phases on SF17 cp"):
        c_ = boot_ci(sfl[nm] - sfl["model on SF17 cp"], args.boot, np.random.default_rng(SEED + 14))
        sfres[f"{nm} minus model on SF17 cp"] = [round(v, 5) for v in c_]
        print(f"   {nm} - model on SF17 cp: {fmt_ci(c_)}")
    nsm = int(sf_mate.sum()); won = int((((sf_cp > 0) & (y_t == 2)) | ((sf_cp < 0) & (y_t == 0)))[sf_mate].sum())
    print(f"   SF17 mate scores among these positions: {nsm}; the side with the mate score won {won} of them")
    sfres["n"] = len(T); sfres["sf17_mates"] = [nsm, won]
    sfres["calibration_model_on_sf17"] = calib_table(sfP["model on SF17 cp"][0] + sfP["model on SF17 cp"][1] / 2, y_t, np.ones(len(T)), np.arange(len(T)))
    print("   calibration (model on SF17 cp):", sfres["calibration_model_on_sf17"])
    metr["sf17_test_sample"] = sfres
    # ---------------------------------------------------------------- blitz test + low-rating games
    print("\n  other held-out checks (post-blunder positions):")
    XbtA = flatten_mapped(recs, [i for i in blitz if split_of(recs[i]["id"]) == "test"], mapping); Xbt = with_clip(subset_rew(XbtA, XbtA["post"]), CLIP)
    l1, _ = per_position_losses(predict(th_fin, lin, Xbt), Xbt["y"]); l2, _ = per_position_losses(predict(th_bl, lin, Xbt), Xbt["y"])
    cbt = boot_ci(game_means(l1 - l2, Xbt["g"], Xbt["w"]), args.boot, np.random.default_rng(SEED + 16))
    m1 = game_means(l1, Xbt['g'], Xbt['w']).mean(); m2 = game_means(l2, Xbt['g'], Xbt['w']).mean()
    print(f"   blitz TEST games ({len(np.unique(Xbt['g']))}): rapid/classical model {m1:.5f} vs blitz-fitted {m2:.5f}; difference {fmt_ci(cbt)}")
    metr["blitz_test"] = dict(games=int(len(np.unique(Xbt["g"]))), primary_model=round(float(m1), 5), blitz_model=round(float(m2), 5), diff_ci95=[round(v, 5) for v in cbt])
    lowinfo = {}
    if low:
        XloA = flatten_mapped(recs, low, mapping); Xlo = with_clip(subset_rew(XloA, XloA["post"]), CLIP)
        variants = {"model, extrapolated to the game's rating": predict(th_fin, lin, Xlo),
                    "model at 1500 (flat extrapolation)": predict(th_fin, lin, dict(Xlo, r=np.full(len(Xlo["r"]), 1500.0))),
                    "provisional": prov_on(subset_rew(XloA, XloA["post"])), "pooled": predict(th_pool, Design("pooled"), Xlo)}
        base_l = None
        print(f"   games with mean rating < 1450 (n={len(low)}, all splits, never used for fitting; mean rating {np.mean([mr(recs[i]) for i in low]):.0f}; "
              f"{len(np.unique(Xlo['g']))} with post-blunder positions):")
        for nm, P in variants.items():
            ll, _ = per_position_losses(P, Xlo["y"]); gl = game_means(ll, Xlo["g"], Xlo["w"])
            if base_l is None: base_l = gl
            ci_ = boot_ci(gl, args.boot, np.random.default_rng(SEED + 17)); cd = boot_ci(gl - base_l, args.boot, np.random.default_rng(SEED + 18))
            lowinfo[nm] = dict(log_loss=[round(v, 5) for v in ci_], minus_extrapolated=[round(v, 5) for v in cd])
            print(f"     {nm:42s} {fmt_ci(ci_)}  minus extrapolated {fmt_ci(cd)}")
        yl = np.array([RES_CODE[recs[i]['winner']] for i in low])
        lowinfo["outcomes"] = dict(white=int((yl == 2).sum()), draw=int((yl == 1).sum()), black=int((yl == 0).sum()), speeds=dict(Counter(recs[i]["speed"] for i in low)))
    metr["low_rating_games"] = lowinfo
    META["held_out"] = metr
    export(recs, args, META, th_fin, th_ph, lin, linp, CLIP, USE_PHASES, boot_th, boot_thp, mapping, S_MULT)


def export(recs, args, META, th, th_ph, lin, linp, CLIP0, USE_PHASES, boot_th, boot_thp, mapping, S_MULT):
    bands = list(range(800, 2300, 100))
    data_lo = 1500
    CLIP = round(CLIP0 / S_MULT, 1) if S_MULT != 1.0 else CLIP0      # exported clip in SF17 cp
    CLIP = int(CLIP) if float(CLIP).is_integer() else CLIP
    model = {"kind": "ordered-logit", "clip": CLIP, "defaultBand": 1100, "bands": {}}
    def band_params(theta, ds, band, phase=1):
        F = ds.feats(np.array([float(band)]), np.array([phase])); k = ds.nparams()
        a, t1, t2 = params_at(theta, F, k)
        return float(a[0]) * S_MULT, float(t1[0]), float(t2[0])
    PH = ((0, "opening"), (1, "middlegame"), (2, "endgame"))
    for b in bands:
        a, t1, t2 = band_params(th, lin, b)
        e = {"a": round(a, 6), "t1": round(t1, 6), "t2": round(t2, 6), "c": 0}
        if USE_PHASES:
            e["phases"] = {}
            for pv, pn in PH:
                a_, t1_, t2_ = band_params(th_ph, linp, b, pv)
                e["phases"][pn] = {"a": round(a_, 6), "t1": round(t1_, 6), "t2": round(t2_, 6), "c": 0}
        model["bands"][str(b)] = e
    cps = [-500, -300, -200, -100, -50, 0, 50, 100, 200, 300, 500]
    def es_of(p):  # p: dict a,t1,t2
        out = []
        for c in cps:
            cc = max(-CLIP, min(CLIP, c)); z = p["a"] * cc / 100
            pl = 1 / (1 + math.exp(-(p["t1"] - z))); pw = 1 - 1 / (1 + math.exp(-(p["t2"] - z))); pd = max(0, 1 - pl - pw)
            out.append(round(pw + pd / 2, 4))
        return out
    def boot_es(TH, ds, b, phase=1):
        lo, hi = [], []
        for c in cps:
            vals = []
            for tb in TH:
                a, t1, t2 = band_params(tb, ds, b, phase)
                pw, pd, pl = probs(np.array([a]), np.array([t1]), np.array([t2]), np.array([float(max(-CLIP, min(CLIP, c)))]))
                vals.append(float(pw[0] + pd[0] / 2))
            lo.append(round(float(np.percentile(vals, 2.5)), 4)); hi.append(round(float(np.percentile(vals, 97.5)), 4))
        return lo, hi
    conv = {}
    print("\n=== EXPECTED SCORE (W + D/2, White's view) at SF17 cp, exported parameters (95% CI: 100 game-bootstrap refits, statistical only) ===")
    print("  band         " + " ".join(f"{c:>6d}" for c in cps))
    for b in (1100, 1500, 1900):
        bp = model["bands"][str(b)]
        es = []
        for c in cps:
            w, d, l = js_human(model, float(c), b); es.append(round(w + d / 2, 4))
        lo, hi = boot_es(boot_th, lin, b)
        conv[str(b)] = dict(es=es, ci95_lo=lo, ci95_hi=hi, draw_at_0=round(js_human(model, 0.0, b)[1], 4))
        tag = "  (EXTRAPOLATED)" if b < data_lo else ""
        print(f"  {b:4d}         " + " ".join(f"{v:6.3f}" for v in es) + f"   P(draw)@0 = {conv[str(b)]['draw_at_0']:.3f}{tag}")
        print(f"   ci lo       " + " ".join(f"{v:6.3f}" for v in lo))
        print(f"   ci hi       " + " ".join(f"{v:6.3f}" for v in hi))
        if USE_PHASES:
            conv[str(b)]["phases"] = {}
            for pv, pn in PH:
                p = bp["phases"][pn]; e2 = es_of(p); lo2, hi2 = boot_es(boot_thp, linp, b, pv)
                z0 = 0.0; pl0 = 1 / (1 + math.exp(-(p["t1"] - z0))); pw0 = 1 - 1 / (1 + math.exp(-(p["t2"] - z0)))
                conv[str(b)]["phases"][pn] = dict(es=e2, ci95_lo=lo2, ci95_hi=hi2, draw_at_0=round(max(0, 1 - pl0 - pw0), 4))
                print(f"   {pn:10s} " + " ".join(f"{v:6.3f}" for v in e2) + f"   P(draw)@0 = {max(0, 1 - pl0 - pw0):.3f}")
    print("\n  exported band parameters (a per 100 cp, t1, t2; c = 0):")
    for b in bands:
        e = model["bands"][str(b)]
        w1, d1, _ = js_human(model, 100.0, b)
        print(f"   {b}: a={e['a']:.4f} t1={e['t1']:.4f} t2={e['t2']:.4f}  ES@+100={w1 + d1/2:.4f}  P(draw)@0={js_human(model, 0.0, b)[1]:.4f}" + ("  EXTRAPOLATED" if b < data_lo else ""))
    # check points for tools/odds/check_prob.mjs
    pts = []
    for band in (800, 1100, 1500, 1900, 2200):
        for cp in (-CLIP - 500, -CLIP, -CLIP + 1, -500, -100, -1, 0, 37, 250, CLIP - 1, CLIP, CLIP + 2000):
            pts.append([float(cp), band])
    pts += [[9990.0, 1100], [-9990.0, 1900], [9000.0, 1500], [-8999.0, 1500], [10000.0, 800], [120.0, 1150], [-80.0, 1250], [300.0, 600], [-300.0, 3000],
            [55.5, None], [-1234.25, None], [5.0, 1949], [5.0, 1951]]
    check = [[cp, band] + js_human(model, cp, band) for cp, band in pts]
    ppts = []
    for band in (1100, 1900, None):
        for phase in (None, "opening", "middlegame", "endgame"):
            for cp in (-9990.0, -CLIP - 1.0, -250.0, 0.0, 120.0, CLIP + 0.0, 9995.0, 10000.0):
                ppts.append([cp, band, phase] + js_human_proposed(model, cp, band, phase))
    mx = 0.0
    for b in bands:
        a, t1, t2 = band_params(th, lin, b)
        for c in (-700.0, -50.0, 0.0, 80.0, 400.0):
            pw, pd, pl = probs(np.array([a]), np.array([t1]), np.array([t2]), np.array([max(-CLIP, min(CLIP, c))]))
            j = js_human(model, c, b); mx = max(mx, abs(j[0] - pw[0]), abs(j[2] - pl[0]))
    print(f"\n  max |exported (rounded to 1e-6) - fitted| probability over bands x 5 cps: {mx:.2e}")
    meta = META
    meta["bands_extrapolated"] = [b for b in bands if b < data_lo]
    meta["bands_data_range"] = ("the puzzle generator skips games with any player rated <= 1500, so fitted games have mean ratings 1501..2650 (bulk 1600..2300); "
                                "bands 800..1400 are EXTRAPOLATED from the linear-in-rating trend (log a, mid-cut, log draw-width); band 1500 is at the lower edge "
                                "(only games with mean rating 1501..1549 in its bin)")
    meta["parametrisation"] = dict(form="x=(rating-1800)/400; a=s*exp(pa0+pa1*x); m=pm0+pm1*x; wd=exp(pw0+pw1*x); t1=m-wd/2; t2=m+wd/2; c=0; clip=clip_fit/s"
                                        + ("; phases: dummies for opening / endgame (middlegame = reference) added to pa, pm, pw" if USE_PHASES else ""),
                                   theta=[round(float(v), 6) for v in th], theta_phases=[round(float(v), 6) for v in th_ph], clip_fit=CLIP0, s=S_MULT, clip_exported=CLIP)
    meta["expected_score_table"] = dict(cp=cps, bands=conv, note="expected score W+D/2 for White at SF17 cp (top-level band parameters"
                                        + ("; 'phases' = phase-specific parameters" if USE_PHASES else "") + "); ci95 from 100 game-bootstrap refits, statistical only")
    meta["check_points"] = dict(note="[cpWhite, band (null = defaultBand), win, draw, loss] from the Python mirror of Prob.human; tools/odds/check_prob.mjs asserts js/prob.js reproduces them within 1e-9",
                                points=check, proposed_points=ppts)
    meta["fitted"] = time.strftime("%Y-%m-%d", time.gmtime())
    meta["mate_handling"] = ("fit/evaluation: Lichess mate scores count as +-clip (contract). js/prob.js currently returns certainty for |cp| >= 9000 "
                             "(engine mate-in-n); the data say the side with a mate score wins less often (held_out.mate_positions). See ODDS_REPORT.md.")
    meta["usage"] = "Prob.human(cpWhite_sf17, {band}) with band = the student's rating band (Lichess rapid scale)" + \
                    ("; optional ctx.phase in {opening, middlegame, endgame} needs the JS change in ODDS_REPORT.md" if USE_PHASES else "")
    model["meta"] = meta
    s = json.dumps(model, separators=(",", ":"), allow_nan=False)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f: f.write(s)
    print(f"\nwrote {args.out} ({len(s)} bytes)")


# ----------------------------------------------------------------------------------------------------------------------
# main pipeline
# ----------------------------------------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=DEFAULT_DATA)
    ap.add_argument("--cache", default="/tmp/claude-0/odds")
    ap.add_argument("--out", default=os.path.join(REPO, "data", "models", "odds.json"))
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--stage", default="all", choices=["parse", "sample", "rescore", "all"])
    ap.add_argument("--force-parse", action="store_true")
    ap.add_argument("--force-rescore", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.cache, exist_ok=True)
    np.set_printoptions(linewidth=160, suppress=True)
    recs = stage_parse(args.data, args.cache, args.force_parse)
    meta0 = report_parse(recs)
    if args.stage == "parse": return
    run_rest(recs, args, meta0)


if __name__ == "__main__":
    main()
