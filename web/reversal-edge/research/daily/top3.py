"""Daily Saudi top-3 list (rule fixed on 2026-10-24, before the first daily list; built only from setups validated in rounds 27-29).
Tier 1 Z swing (round 28): first close at stretch Z <= -2.62, ML rank >= 0.5, market model > 0 -> hold 40 sessions, no stop.
Tier 2 trend breakout (round 29 partner): close at a 55-day high and above the 200-day average, ML rank >= 0.7, market model > 0
       -> exit when a close falls below the highest close since entry minus 3 x ATR(20) (ATR fixed at the signal), at most 60 sessions.
Tier 3 ML leader (Core ML sleeve): highest ML rank -> hold 20 sessions.
Liquid, eligible stocks only (60-day median traded value >= SAR 3m). Within a tier, higher ML rank first; a stock appears once.
Market model <= 0: the system would hold cash. Z swing is off (unreliable then, forced.py); breakouts then ML leaders, at half size.
Signal at the last close, entry at the next open (the list's day), costs 0.40% round trip.
Change 2026-10-25 (round 31): Z swing also needs market momentum (market stretch, MS) <= -1.18; above it, dips in single stocks
tended to keep falling (Saudi 2004-26 and an independent US check). MS = equal-weight market 60-day log return / (its daily sd
measured before those 60 days x sqrt 60).
Usage: python top3.py --history   (walk-forward track record of the rule -> rule_stats.json)
       python top3.py             (today's list -> out/<date>.md, appended to out/picks_log.csv)"""
import os, sys, json, glob, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); S = os.path.dirname(H); R27 = os.path.join(S, "r27")
sys.path.insert(0, R27); sys.path.insert(0, os.path.join(S, "strat")); os.chdir(R27)
from core import P, C, dates, cols, PCT, pm, ATR, SMA200, START
from sectors import industry
COST = 0.004; ZLINE = -2.62; MS_GATE, MS_DEEP = -1.18, -2.53
TIERS = {1: dict(name="Z swing", kind=1, h=40), 2: dict(name="Trend breakout", kind=4, h=60, k=3.0), 3: dict(name="ML leader", kind=1, h=20)}
F = pd.read_pickle("F27y.pkl"); ZC = F["zc"].reindex(index=dates, columns=cols)
LIQ = ((P["VAL"].rolling(60, min_periods=20).median() >= 3e6) & P["elig"]).values
ZFIRST = ((ZC <= ZLINE) & ~(ZC <= ZLINE).shift(1, fill_value=False)).values
BRK = ((C >= C.rolling(55, min_periods=55).max()) & (C > SMA200)).values
Of, Cl, A = P["Of"].values.astype(float), C.values.astype(float), ATR.values.astype(float)
T_ = len(dates)
_r = np.log(C).diff().clip(-.25, .25); _mr = _r.where(P["elig"]).mean(1); _msd = _mr.rolling(60, min_periods=40).std()
MS = (_mr.rolling(60, min_periods=48).sum() / (_msd.shift(60) * np.sqrt(60))).values

def ranked(i, pct, pmv, msv):
    """all candidates at close i in list order: [(column index, tier)]; pct = ML rank per column (array), pmv = market model."""
    ok = LIQ[i] & np.isfinite(pct) & np.isfinite(A[i]) & (A[i] > 0); out, seen = [], set()
    masks = ([(1, ok & ZFIRST[i] & (pct >= .5))] if pmv > 0 and msv <= MS_GATE else []) + [(2, ok & BRK[i] & (pct >= .7)), (3, ok)]
    for t, m in masks:
        for j in np.where(m)[0][np.argsort(-pct[m], kind="stable")]:
            if j not in seen: seen.add(j); out.append((j, t))
    return out

def trade(i, j, t):
    """signal at close i, entry at open i+1. Returns dict(ex = index of the exit open (>= T_ means still open), net, peak, stop)."""
    sp = TIERS[t]; e = Of[i + 1, j] if i + 1 < T_ else np.nan
    if not np.isfinite(e) or e <= 0: return None
    a = A[i, j]; peak = e; k = i + 1
    while k < T_:
        c = Cl[k, j]
        if np.isfinite(c):
            peak = max(peak, c)
            if sp["kind"] == 4 and c < peak - sp["k"] * a: return dict(ex=k + 1, e=e, peak=peak, stop=peak - sp["k"] * a, why="trail stop")
        if k - i >= sp["h"]: return dict(ex=k + 1, e=e, peak=peak, stop=None, why=f"{sp['h']} sessions")
        k += 1
    return dict(ex=T_ + 1, e=e, peak=peak, stop=(peak - sp["k"] * a) if sp["kind"] == 4 else None, why=None)

def history():
    """walk-forward ML ranks and market model; each stock held per its tier rule, repeat picks while held are ignored (keep holding)."""
    pct_all = PCT.values; pmv = pm.values; rows = []; held = {}
    for i in range(START, T_ - 1):
        if not np.isfinite(pmv[i]): continue
        for j, t in ranked(i, pct_all[i], pmv[i], MS[i])[:3]:
            if held.get(j, -1) > i: continue
            tr = trade(i, j, t)
            if tr is None: continue
            held[j] = tr["ex"] - 1
            if tr["ex"] < T_ and np.isfinite(Of[tr["ex"], j]):
                rows.append(dict(date=dates[i], sym=cols[j], tier=t, pos=pmv[i] > 0, net=Of[tr["ex"], j] / tr["e"] - 1 - COST, hold=tr["ex"] - i - 1))
    R = pd.DataFrame(rows); out = {}
    def st(x): return dict(n=int(len(x)), win=round(float((x.net > 0).mean()), 3), avg=round(float(x.net.mean()), 4), avg_win=round(float(x.net[x.net > 0].mean()), 4),
                           avg_loss=round(float(x.net[x.net <= 0].mean()), 4), hold=float(x.hold.median()), worst5=round(float(x.net.quantile(.05)), 4)) if len(x) >= 10 else None
    for era, (a, b) in {"2013-19": ("2013", "2019-12-31"), "2020-26": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31"), "2024-26": ("2024", "2026-12-31")}.items():
        x = R[(R.date >= a) & (R.date <= b)]
        for g, y in (("pos", x[x.pos]), ("neg", x[~x.pos])):
            out[f"{era}|{g}|all"] = st(y)
            for t in TIERS: out[f"{era}|{g}|{t}"] = st(y[y.tier == t])
    # random liquid stock on the same days (hold 20 and 40) for comparison
    rnd = np.random.default_rng(0); rr = []
    for i in range(START, T_ - 42, 3):
        js = np.where(LIQ[i] & np.isfinite(Of[min(i + 1, T_ - 1)]))[0]
        if len(js) == 0 or not np.isfinite(pmv[i]): continue
        j = rnd.choice(js)
        for h in (20, 40):
            x = Of[i + 1 + h, j] / Of[i + 1, j] - 1 - COST
            if np.isfinite(x): rr.append(dict(date=dates[i], h=h, pos=pmv[i] > 0, net=x))
    RR = pd.DataFrame(rr)
    for era, (a, b) in {"2013-19": ("2013", "2019-12-31"), "2020-26": ("2020", "2026-12-31"), "2024-26": ("2024", "2026-12-31")}.items():
        for h in (20, 40):
            for g in (True, False):
                x = RR[(RR.date >= a) & (RR.date <= b) & (RR.h == h) & (RR.pos == g)]
                out[f"{era}|{'pos' if g else 'neg'}|random{h}"] = dict(n=int(len(x)), win=round(float((x.net > 0).mean()), 3), avg=round(float(x.net.mean()), 4))
    R.to_csv(os.path.join(H, "rule_trades.csv"), index=False); json.dump(out, open(os.path.join(H, "rule_stats.json"), "w"), indent=1)
    for k, v in out.items(): print(k, v)

def names():
    nm = {}
    meta = json.load(open(os.path.join(S, "tadawul/meta.json"))); ex = json.load(open(os.path.join(S, "edge26/extra_names.json")))
    for s, m in meta.items(): nm[s] = m.get("full") or m.get("name") or s
    for s, n in ex.items(): nm.setdefault(s, n.title())
    for f in sorted(glob.glob(os.path.join(S, "edge26/data/fetch_*.json")))[-1:]:
        for s, v in json.load(open(f)).items():
            if isinstance(v, dict) and v.get("name"): nm[s] = v["name"]
    return nm

BD = pd.offsets.CustomBusinessDay(weekmask="Sun Mon Tue Wed Thu")
def fmt_d(d): return pd.Timestamp(d).strftime("%a %d %b")
def pc(x, d=1): return f"{100 * x:+.{d}f}%"

def live():
    T = json.load(open("today27.json")); last = dates[-1]; assert str(last.date()) == T["date"], (last, T["date"])
    pmv = float(T["pm"]); pct = pd.Series(T["ranks"]).reindex(cols).astype(float).values; i = T_ - 1
    now = pd.Timestamp.now(tz="Asia/Riyadh").tz_localize(None).normalize(); day = BD.rollforward(now) if now > last else last + BD
    nm = names(); St = json.load(open(os.path.join(H, "rule_stats.json")))
    msv = float(MS[i]); cand = ranked(i, pct, pmv, msv); top = cand[:3]; half = pmv <= 0; size = "2.5%" if half else "5%"
    L = [f"**Saudi top 3 for {day.strftime('%A %d %b %Y')}** (prices to the {fmt_d(last)} close; buy at the 10:00 open)", ""]
    if last < day - BD: L += [f"Warning: the newest close in the data is {fmt_d(last)}, not {fmt_d(day - BD)} (Yahoo has not published it yet or the market was closed).", ""]
    L.append(f"Market model: {pc(pmv, 2)} expected 20-day market move -> " + ("**positive**, normal size." if not half else
             "**negative**: the system would hold cash today. If you trade anyway, use half size; Z-swing entries are switched off on such days."))
    L.append("")
    L.append(f"Market momentum (market stretch): {msv:+.2f} -> " + ("**deep mean-reversion zone** (at or below -2.53): dip buys have worked best here." if msv <= MS_DEEP else
             "**mean-reversion zone** (-2.53 to -1.18): dip buys allowed." if msv <= MS_GATE else
             "**momentum zone** (above -1.18): the market is not falling, so single-stock dips tend to keep falling; Z swing is off, breakouts are fine."))
    L += ["", "| # | Stock | Setup | Last close | Plan |", "|---|---|---|---|---|"]
    log_rows = []
    for n, (j, t) in enumerate(top, 1):
        s = cols[j]; c = Cl[i, j]; a = A[i, j]; z = ZC.iloc[i, j]; ml = pct[j]
        setup = {1: f"Z swing: stretch Z {z:.2f}, ML {100 * ml:.0f}%", 2: f"Trend breakout: new 55-day high, ML {100 * ml:.0f}%", 3: f"ML leader: ML {100 * ml:.0f}%"}[t]
        if t == 1: plan = f"{size} of the account. Hold 40 sessions (sell at the open around {fmt_d(day + 40 * BD)}). No stop."
        elif t == 2: plan = (f"{size}. Sell at the next open after a close below (highest close since entry - {3 * a:.2f}); "
                             f"first stop about {c - 3 * a:.2f}. At most 60 sessions.")
        else: plan = f"{size}. Hold 20 sessions (sell at the open around {fmt_d(day + 20 * BD)})."
        L.append(f"| {n} | **{s}** {nm.get(s, s)[:28]} ({industry(s)}) | {setup} | {c:.2f} | {plan} |")
        log_rows.append(dict(signal=str(last.date()), sym=s, tier=t, close=round(float(c), 4), atr=round(float(a), 4), ml=round(float(ml), 3), pm=round(pmv, 5)))
    g = "neg" if half else "pos"; L += ["", f"How these setups did when chosen by this rule, 2020-26, net of costs (market model {'negative' if half else 'positive'} days):"]
    for t in sorted({t for _, t in top}):
        x = St.get(f"2020-26|{g}|{t}"); r = St.get(f"2020-26|{g}|random{40 if t == 1 else 20}")
        y = St.get(f"2024-26|{g}|{t}"); ry = St.get(f"2024-26|{g}|random{40 if t == 1 else 20}")
        if x: L.append(f"- {TIERS[t]['name']}: {100 * x['win']:.0f}% winners, {pc(x['avg'])} per trade (wins {pc(x['avg_win'])}, losses {pc(x['avg_loss'])}, "
                       f"median {x['hold']:.0f} sessions); random liquid stock {pc(r['avg'])}."
                       + (f" Since 2024: {100 * y['win']:.0f}% winners, {pc(y['avg'])} (random {pc(ry['avg'])})." if y and ry else ""))
    more = [(j, t) for j, t in cand[3:] if t < 3][:6]
    if more: L += ["", "Also qualifying today: " + ", ".join(f"{cols[j]} {nm.get(cols[j], '')[:18]} ({TIERS[t]['name']}, ML {100 * pct[j]:.0f}%)" for j, t in more) + "."]
    elif all(t == 3 for _, t in top): L += ["", "No Z-swing or breakout signal at this close; the list is the top ML ranks."]
    # earlier picks: exits due at this open, using the same exit rules (repeat picks while held are ignored)
    lf = os.path.join(H, "out/picks_log.csv"); old = pd.read_csv(lf, dtype={"sym": str}) if os.path.exists(lf) else pd.DataFrame(columns=["signal", "sym", "tier"])
    old = old[old.signal != str(last.date())]; due, still = [], 0; held = {}
    for _, r in old.sort_values("signal").iterrows():
        if r.sym not in cols or pd.Timestamp(r.signal) not in dates: continue
        ii = dates.get_loc(pd.Timestamp(r.signal)); jj = cols.get_loc(r.sym)
        if held.get(r.sym, -1) > ii: continue
        tr = trade(ii, jj, int(r.tier))
        if tr is None: continue
        held[r.sym] = tr["ex"] - 1
        if tr["ex"] == T_: due.append(f"**{r.sym}** {nm.get(r.sym, '')[:18]} ({TIERS[int(r.tier)]['name']} from {fmt_d(dates[ii + 1])}: {tr['why']}, "
                                     f"{pc(Cl[i, jj] / tr['e'] - 1)} so far)")
        elif tr["ex"] > T_: still += 1
    if due: L += ["", "Exits due at today's open (earlier picks, if you bought them): " + "; ".join(due) + "."]
    if still: L += ["", f"{still} earlier pick(s) are still inside their holding rule."]
    L += ["", "Research signals, not financial advice. About 4 in 10 picks lose, so keep each position small"
          + ("; keep at most 5 Z-swing positions open at once (as tested; with the market-momentum gate the worst Z-swing trade lost about 23%)." if any(t == 1 for _, t in top) else ".")]
    md = "\n".join(L); open(os.path.join(H, f"out/{last.date()}.md"), "w").write(md)
    pd.concat([old, pd.DataFrame(log_rows)]).to_csv(lf, index=False); print(md)

if __name__ == "__main__":
    history() if "--history" in sys.argv else live()
