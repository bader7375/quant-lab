"""Round 76 (PREREG.md): the anatomy of a buy-zone cross. Other markets 2001-26 and Saudi 2013-19 only. A description; nothing is judged.
Usage: RE_WORK=<work folder> python3 r76.py <world data folder>"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../r72")); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import swing as SW; from engine import Book; import wpanel, saudi
ROOT = sys.argv[1]; WORK = os.environ["RE_WORK"]; HS = (1, 2, 3, 5, 10, 20, 40); LINES = (-1.5, -2.0, -2.5, -3.0); TG = (-1.0, 0.0, 1.0); COST = .004
def events(B, mk, a, b, extra=None):
    """one row per IN / UP cross of each line between dates a and b whose 41-session window ends inside [a, b]."""
    d = B.dates; Z = B.ZC.values; T = B.T; EL = B.EL; i0 = int(np.searchsorted(d.values, np.datetime64(a))); i1 = int(np.searchsorted(d.values, np.datetime64(b), side="right")) - 1
    F = {h: SW.fwd(B.Of, h) for h in HS}; M = {h: np.nanmean(np.where(EL, F[h], np.nan), axis=1) for h in HS}
    sma = pd.DataFrame(B.Cl).rolling(200, min_periods=160).mean().values; up = B.Cl > sma; wx = SW.weather_code(B.MS); mon = (d.year * 12 + d.month).values; rows = []
    for L in LINES:
        for kind, X in (("IN", SW.cross_in(Z, L)), ("UP", SW.cross_up(Z, L))):
            X = X & EL; X[:max(i0, 260)] = False; X[max(i1 - 41, 0):] = False; I, J = np.where(X)
            if not len(I): continue
            r = dict(market=mk, L=L, kind=kind, i=I, j=J, month=mon[I], w=wx[I], up=up[I, J].astype(np.int8), z=Z[I, J].astype(np.float32))
            for h in HS: r[f"r{h}"] = (F[h][I, J] - COST).astype(np.float32); r[f"x{h}"] = (F[h][I, J] - M[h][I]).astype(np.float32)
            if kind == "IN":
                for tg in TG:
                    e = SW.run_exits(B, I, J, target=tg, cap=40); k = {-1.0: "a", 0.0: "b", 1.0: "c"}[tg]
                    r["t" + k] = (e["ret"] - COST).astype(np.float32); r["h" + k] = e["held"].astype(np.int16); r["y" + k] = (e["why"] == 0).astype(np.int8); r["m" + k] = e["mae"].astype(np.float32)
            if extra:
                for nm, A in extra.items(): r[nm] = A[I, J] if A.ndim == 2 else A[I]
            rows.append(pd.DataFrame(r))
    base = {h: [float(np.nanmean(M[h][i0:i1 - 41][wx[i0:i1 - 41] == k]) - COST) if (wx[i0:i1 - 41] == k).any() else np.nan for k in range(4)] for h in HS}
    return pd.concat(rows, ignore_index=True), base
def cell(x, cols):
    out = {"n": int(len(x))}
    for c in cols: m, (lo, hi) = SW.month_ranges(x[c].values, x["mk_month"].values); out[c] = [m, lo, hi]
    return out
def show(E, title, split=None):
    print(f"\n=== {title}")
    for kind in ("IN", "UP"):
        print(f"-- {kind} cross: net return after h sessions (average, 5%-95% range by month) | excess over the average liquid stock at 5 / 20")
        for L in LINES:
            for k, wn in enumerate(SW.WEATHER):
                x = E[(E.kind == kind) & (E.L == L) & (E.w == k)]
                if split is not None: x = x[split(x)]
                if len(x) < 30: continue
                c = cell(x, ["r1", "r3", "r5", "r10", "r20", "r40", "x5", "x20"]); f = lambda v: f"{100 * v[0]:+5.2f}% ({100 * v[1]:+5.2f}..{100 * v[2]:+5.2f})"
                print(f"  L {L:4.1f} {wn:6s} n {c['n']:6d} | 1: {100 * c['r1'][0]:+5.2f}% 3: {100 * c['r3'][0]:+5.2f}% 5: {f(c['r5'])} 10: {f(c['r10'])} 20: {f(c['r20'])} 40: {f(c['r40'])} | xs5 {f(c['x5'])} xs20 {f(c['x20'])}")
def way_back(E, title):
    print(f"\n=== {title}: the way back after an IN cross (sold at the open after stretch Z closes at or above the target, 40 sessions at most)")
    out = {}
    for L in LINES:
        for k, wn in enumerate(SW.WEATHER):
            x = E[(E.kind == "IN") & (E.L == L) & (E.w == k) & (E.hb >= 0)]
            if len(x) < 30: continue
            s = f"  L {L:4.1f} {wn:6s} n {len(x):6d}"
            for tg, key in ((-1, "a"), (0, "b"), (1, "c")):
                m, (lo, hi) = SW.month_ranges(x["t" + key].values, x["mk_month"].values); held = float(x["h" + key].mean()); rch = float(x["y" + key].mean()); win = float((x["t" + key] > 0).mean())
                out[f"{L}|{wn}|{tg}"] = dict(n=int(len(x)), avg=m, lo=lo, hi=hi, held=held, reached=rch, win=win, per_session=m / held, mae_med=float(x["m" + key].median()), mae_p10=float(x["m" + key].quantile(.1)))
                s += f" | Z>={tg:+d}: {100 * m:+5.2f}% ({100 * lo:+5.2f}..{100 * hi:+5.2f}) win {100 * win:3.0f}% reached {100 * rch:3.0f}% held {held:4.1f} -> {1e4 * m / held:+5.1f} bp/session, pain med {100 * x['m' + key].median():+5.1f}% p10 {100 * x['m' + key].quantile(.1):+5.1f}%"
            print(s)
    return out
if __name__ == "__main__":
    OUT = {}; W = []; baseW = {}
    books = {mk: wpanel.panel(os.path.join(ROOT, mk)) for mk in sorted(os.listdir(ROOT)) if os.path.isdir(os.path.join(ROOT, mk))}; books["us"] = wpanel.panel(os.path.join(WORK, "edge26/data/us100"))
    for mk, P in books.items():
        if P is None: continue
        B = Book(C=P["C"], O=P["O"], elig=P["elig"], week=wpanel.WEEK.get(mk, "W-FRI")); E, base = events(B, mk, "2001-01-01", "2026-12-31"); E["mk_month"] = E.market + ":" + E.month.astype(str); W.append(E); baseW[mk] = base
    W = pd.concat(W, ignore_index=True); print(f"other markets: {W.market.nunique()} markets, {len(W)} cross events 2001-26")
    SB, PB = saudi.load(); S, baseS = events(SB, "saudi", "2013-01-01", "2019-12-31", extra=dict(ml=np.nan_to_num(SB.PCT, nan=-1.0), pm=SB.PM)); S["mk_month"] = "saudi:" + S.month.astype(str)
    print(f"Saudi 2013-19: {len(S)} cross events (the window of every event ends by 2019-12-31)")
    print("\naverage liquid stock from a day of that weather, net of costs (the bar a cross has to clear), sessions 5 / 20 / 40:")
    print("  Saudi 2013-19: " + " | ".join(f"{wn} {100 * baseS[5][k]:+.2f}% / {100 * baseS[20][k]:+.2f}% / {100 * baseS[40][k]:+.2f}%" for k, wn in enumerate(SW.WEATHER)))
    bw = {h: np.nanmean([baseW[m][h] for m in baseW], axis=0) for h in (5, 20, 40)}; print("  other markets: " + " | ".join(f"{wn} {100 * bw[5][k]:+.2f}% / {100 * bw[20][k]:+.2f}% / {100 * bw[40][k]:+.2f}%" for k, wn in enumerate(SW.WEATHER)))
    show(W, "other markets, all stocks"); show(S, "Saudi 2013-19, all liquid stocks")
    show(W, "other markets, stock above its 200-session average", lambda x: x.up == 1); show(W, "other markets, stock below its 200-session average", lambda x: x.up == 0)
    show(S, "Saudi 2013-19, stock above its 200-session average", lambda x: x.up == 1); show(S, "Saudi 2013-19, stock below its 200-session average", lambda x: x.up == 0)
    show(S, "Saudi 2013-19, ML rank 50%+ and market model positive", lambda x: (x.ml >= .5) & (x.pm > 0)); show(S, "Saudi 2013-19, ML rank below 50% or market model negative", lambda x: ~((x.ml >= .5) & (x.pm > 0)))
    OUT["way_back_world"] = way_back(W, "other markets"); OUT["way_back_saudi"] = way_back(S, "Saudi 2013-19")
    OUT["way_back_saudi_gated"] = way_back(S[(S.ml >= .5) & (S.pm > 0)], "Saudi 2013-19, ML rank 50%+ and market model positive")
    W.drop(columns=["mk_month"]).to_parquet(os.path.join(WORK, "r76_world_events.parquet")); S.drop(columns=["mk_month"]).to_parquet(os.path.join(WORK, "r76_saudi_design_events.parquet"))
    json.dump(OUT, open(os.path.join(HERE, "r76_results.json"), "w"), indent=1, default=float)
