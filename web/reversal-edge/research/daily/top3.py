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
Change 2026-10-25 (round 33): tier 1 also takes WEEKLY Z swings - first weekly close (weeks ending Thursday) at weekly stretch Z <= -2.08
(same formula on weekly bars), same filters, hold 40 sessions (2013-19 85% winners +19.1%, 2020-26 86% +11.2%, 2004-12 price-only +18.4%).
Each pick also shows its latest annual accounts (Yahoo, FY usable 91 days after year end).
Change 2026-10-25 (round 36, the user's choice): companies whose latest usable annual result is a LOSS are skipped (next candidate moves up).
Accounts exist only from FY2022 (usable from April 2023), so the filter acts from then on; earlier history is unchanged.
Two signal sets (2026-11-08, the user's choice; switches in settings.json): "Z score" = tier 1 above (the live Z-swing rule, named Z score in the list)
and "Market returned" = option 7 (round 47/49): the same signals, taken only while the market-turn window is open and skipping stocks the live rule
bought before the turn (opt7.py). It has its own section, record and log (tier 4), at most 5 positions; a stock in both is one trade.
Change 2026-11-09 (round 66, the user's choice): Z score signals are listed most volatile first (60-day volatility = daily sd of returns)
instead of highest ML rank; ML rank >= 50% stays a filter. Market returned keeps the ML order (volatility did not clearly help there).
settings.json "zscore_order": "volatility" (default) or "ml". Each Z score row shows its volatility and its rank among liquid stocks.
Change 2026-11-09 (round 67, the user's choice: plan A): buy only Market returned signals, 10% of the account each (settings.json mr_size),
at most 5, most volatile first; Z score signals off (they still run as the shadow book that decides the blocked stocks); the top-3 table
(ML leaders / breakouts) is printed after them for reference only; idle money in a SAR money-market fund. settings.json "plan": "A".
Change 2026-11-10 (round 68): the Market returned section comes from planbook.py, which replays the tested rule to the last close:
held positions and free slots (from settings.json plan_start), sells due, buys in tested order up to the free slots, and the reason
for every skipped signal (already held / no free slot / paper trade from before the turn). ML ranks and the market model in the
export are the walk-forward values the tests used.
Change 2026-11-10 (the user: "Let's go back to previous strategy stretch with ML"): plan Z. The Z score rule is the plan again (settings.json
plan "Z", z_size 0.05, plan_start 2026-11-10): 5 positions, most volatile first, hold 40 sessions, no stop; its section comes from the plan book
(kind "Z": every paper trade, not only those inside a turn window); the turn window is shown as context; ML leaders / breakouts for reference.
Usage: python top3.py --history   (walk-forward track record of the rule -> rule_stats.json)
       python top3.py             (today's list -> out/<date>.md, appended to out/picks_log.csv)"""
import os, sys, json, glob, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); S = os.path.dirname(H); R27 = os.path.join(S, "r27")
sys.path.insert(0, R27); sys.path.insert(0, os.path.join(S, "strat")); os.chdir(R27)
from core import P, C, dates, cols, PCT, pm, ATR, SMA200, START
from sectors import industry
COST = 0.004; ZLINE = -2.62; MS_GATE, MS_DEEP = -1.18, -2.53
TIERS = {4: dict(name="Market returned", kind=1, h=40), 1: dict(name="Z score", kind=1, h=40), 2: dict(name="Trend breakout", kind=4, h=60, k=3.0), 3: dict(name="ML leader", kind=1, h=20)}
F = pd.read_pickle("F27y.pkl"); ZC = F["zc"].reindex(index=dates, columns=cols)
LIQ = ((P["VAL"].rolling(60, min_periods=20).median() >= 3e6) & P["elig"]).values
ZFIRST = ((ZC <= ZLINE) & ~(ZC <= ZLINE).shift(1, fill_value=False)).values
BRK = ((C >= C.rolling(55, min_periods=55).max()) & (C > SMA200)).values
Of, Cl, A = P["Of"].values.astype(float), C.values.astype(float), ATR.values.astype(float)
T_ = len(dates)
_r = np.log(C).diff().clip(-.25, .25); _mr = _r.where(P["elig"]).mean(1); _msd = _mr.rolling(60, min_periods=40).std()
MS = (_mr.rolling(60, min_periods=48).sum() / (_msd.shift(60) * np.sqrt(60))).values
VOLD = _r.rolling(60, min_periods=40).std().values                            # round 66: 60-day volatility (daily sd of returns)
VOLP = pd.DataFrame(VOLD).where(LIQ).rank(axis=1, pct=True).values            # its rank among the liquid stocks that day (1 = most volatile)
from opt7 import settings as _o7s
ZORDER = _o7s()["zscore_order"]                                               # "volatility" (round 66) or "ml"
def _vt(i, j): return f", vol {100 * VOLD[i, j]:.1f}%/day (rank {100 * VOLP[i, j]:.0f}%)" if np.isfinite(VOLD[i, j]) and np.isfinite(VOLP[i, j]) else ""
WLINE = -2.08
def _zc_bars(Cb):
    r = np.log(Cb).diff().clip(-.6, .6); sd = r.rolling(60, min_periods=40).std()
    z = [r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]
    return (z[0] + z[1] + z[2]) / 3
_wk = dates.to_period("W-THU"); _wend = pd.Series(dates, index=dates).groupby(_wk).max(); _Cw = C.groupby(_wk).last(); _Cw.index = _wend.reindex(_Cw.index).values
ZW = _zc_bars(_Cw); _wf = (ZW <= WLINE) & ~(ZW <= WLINE).shift(1, fill_value=False)
WFIRST = np.zeros(C.shape, dtype=bool); _ix = np.searchsorted(dates.values, _wf.index.values); WFIRST[_ix] = _wf.values
ZWV = np.full(C.shape, np.nan); ZWV[_ix] = ZW.values
def _loss_mask():
    """True where the latest annual accounts usable at that date show a loss (Yahoo FY2022+; usable 91 days after the fiscal year end)."""
    M = np.zeros(C.shape, dtype=bool); cix = {c: j for j, c in enumerate(cols)}
    for f in glob.glob(os.path.join(S, "r33/fund/*.json")):
        sy = os.path.basename(f)[:-5]
        if sy not in cix: continue
        ni = json.load(open(f)).get("annualNetIncome", {}); j = cix[sy]
        for k in sorted(ni):
            a = np.searchsorted(dates.values, np.datetime64(pd.Timestamp(k) + pd.Timedelta(days=91))); M[a:, j] = ni[k] <= 0
    return M
LOSS = _loss_mask()

def ranked(i, pct, pmv, msv, wk_ok=True, zmask=None):
    """all candidates at close i in list order: [(column index, tier)]; pct = ML rank per column (array), pmv = market model."""
    ok = LIQ[i] & np.isfinite(pct) & np.isfinite(A[i]) & (A[i] > 0) & ~LOSS[i]; out, seen = [], set()
    masks = ([(1, ok & (ZFIRST[i] | (WFIRST[i] & wk_ok)) & (pct >= .5) & (True if zmask is None else zmask))] if pmv > 0 and msv <= MS_GATE else []) + [(2, ok & BRK[i] & (pct >= .7)), (3, ok)]
    for t, m in masks:
        key = VOLD[i] if t == 1 and ZORDER == "volatility" else pct          # round 66: Z score most volatile first
        for j in np.where(m)[0][np.argsort(-np.nan_to_num(key[m], nan=-1.0), kind="stable")]:
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

def accounts():
    """latest usable annual accounts per stock (Yahoo; FY usable 91 days after its end) -> short text."""
    out = {}; now = pd.Timestamp.now()
    for f in glob.glob(os.path.join(S, "r33/fund/*.json")):
        sy = os.path.basename(f)[:-5]; d = json.load(open(f)); ni = d.get("annualNetIncome", {}); eq = d.get("annualStockholdersEquity", {})
        ks = [k for k in sorted(ni) if pd.Timestamp(k) + pd.Timedelta(days=91) <= now]
        if not ks: continue
        k = ks[-1]; v = ni[k]; e = eq.get(k); roe = f", ROE {100 * v / e:.0f}%" if e and e > 0 else ""
        out[sy] = (f"profit SAR {v / 1e6:,.0f}m{roe} (FY{k[:4]})" if v > 0 else f"LOSS SAR {v / 1e6:,.0f}m (FY{k[:4]})")
    return out

BD = pd.offsets.CustomBusinessDay(weekmask="Sun Mon Tue Wed Thu")
def fmt_d(d): return pd.Timestamp(d).strftime("%a %d %b")
def pc(x, d=1): return f"{100 * x:+.{d}f}%"

def live():
    T = json.load(open("today27.json")); last = dates[-1]; assert str(last.date()) == T["date"], (last, T["date"])
    pmv = float(T["pm"]); pct = pd.Series(T["ranks"]).reindex(cols).astype(float).values; i = T_ - 1
    now = pd.Timestamp.now(tz="Asia/Riyadh").tz_localize(None).normalize(); day = BD.rollforward(now) if now > last else last + BD
    nm = names(); St = json.load(open(os.path.join(H, "rule_stats.json")))
    wk_ok = day.to_period("W-THU") != last.to_period("W-THU")   # the last week is complete only when the list day is in a new week
    from opt7 import settings as o7settings
    SET = o7settings(); O7 = T.get("opt7"); mron = bool(SET["market_returned"]) and O7 is not None
    PLAN = SET["plan"]; KIND = "Z" if PLAN == "Z" else "A"
    msv = float(MS[i]); cand = ranked(i, pct, pmv, msv, wk_ok, None if (SET["zscore"] and PLAN not in ("A", "Z")) else np.zeros(len(cols), bool)); top = cand[:3]   # in a plan the book section owns the Z score signals
    import planbook as PB                                                            # round 68: the tested rule replayed to this close
    assert PB.T_ == T_ and list(PB.cols) == list(cols) and PB.dates[-1] == last, 'plan book and list use different data'
    psz = SET["z_size"] if KIND == "Z" else SET["mr_size"]; mrsz = f"{100 * psz:.0f}%"; lab = "Z score" if KIND == "Z" else "Market returned"
    ST = PB.state(loss=True, week_complete=bool(wk_ok), start=SET["plan_start"] or None, kind=KIND)
    cand = [(j, t) for j, t in cand if not (t == 1 and j in ST["blocked"])]; top = cand[:3]   # a signal while the stock's paper trade is open is not a new trade
    FA = accounts(); half = pmv <= 0; size = "2.5%" if half else "5%"
    L = [f"**Saudi {dict(A='plan A list', Z='Z score list').get(PLAN, 'top 3')} for {day.strftime('%A %d %b %Y')}** (prices to the {fmt_d(last)} close; buy at the 10:00 open)", ""]
    if last < day - BD: L += [f"Warning: the newest close in the data is {fmt_d(last)}, not {fmt_d(day - BD)} (Yahoo has not published it yet or the market was closed).", ""]
    L.append(f"Market model: {pc(pmv, 2)} expected 20-day market move -> " + ("**positive**, normal size." if not half else
             "**negative**: the system would hold cash today. If you trade anyway, use half size; Z-swing entries are switched off on such days."))
    L.append("")
    L.append(f"Market momentum (market stretch): {msv:+.2f} -> " + ("**deep mean-reversion zone** (at or below -2.53): dip buys have worked best here." if msv <= MS_DEEP else
             "**mean-reversion zone** (-2.53 to -1.18): dip buys allowed." if msv <= MS_GATE else
             "**momentum zone** (above -1.18): the market is not falling, so single-stock dips tend to keep falling; Z swing is off, breakouts are fine."))
    if PLAN == "A":
        L += ["", f"**Your plan: A** (round 67): buy only the **Market returned** signals, **{mrsz} of the account each**, at most 5 at once (most volatile first), "
                  "hold 40 sessions, no stop. Keep all idle money in a SAR money-market fund. ML leaders and breakouts are shown at the end for reference only. "
                  "Tested on the whole account (idle money at T-bill interest): 2013-19 +6.8% a year, worst drawdown 9.7%; 2020-26 +6.5%, 6.3%; 2016-26 +8.7%, 6.3%."]
    elif PLAN == "Z":
        L += ["", f"**Your plan: Z score** (stretch Z with ML): buy the **Z score** signals, **{mrsz} of the account each**, at most 5 at once (most volatile first), "
                  "hold 40 sessions, no stop. Keep idle money in a SAR money-market fund. ML leaders and breakouts are shown at the end for reference only. "
                  "Tested on the whole account (idle money at T-bill interest, round 70): 2013-19 +3.2% a year, worst drawdown 6.1%; 2020-26 +4.9%, 4.9%."]
    elif not SET["zscore"]: L += ["", "Z score signals are switched off (settings.json): the list below has no Z score picks."]
    L0 = L; L = []
    L += ["", "| # | Stock | Setup | Last close | Plan | Latest accounts |", "|---|---|---|---|---|---|"]
    log_rows = []
    for n, (j, t) in enumerate(top, 1):
        s = cols[j]; c = Cl[i, j]; a = A[i, j]; z = ZC.iloc[i, j]; ml = pct[j]
        wkly = t == 1 and not ZFIRST[i, j]
        setup = {1: (f"Z score (weekly candles): weekly stretch Z {ZWV[i, j]:.2f}, ML {100 * ml:.0f}%" if wkly else f"Z score: stretch Z {z:.2f}, ML {100 * ml:.0f}%") + _vt(i, j), 2: f"Trend breakout: new 55-day high, ML {100 * ml:.0f}%", 3: f"ML leader: ML {100 * ml:.0f}%"}[t]
        if t == 1: plan = f"{size} of the account. Hold 40 sessions (sell at the open around {fmt_d(day + 40 * BD)}). No stop."
        elif t == 2: plan = (f"{size}. Sell at the next open after a close below (highest close since entry - {3 * a:.2f}); "
                             f"first stop about {c - 3 * a:.2f}. At most 60 sessions.")
        else: plan = f"{size}. Hold 20 sessions (sell at the open around {fmt_d(day + 20 * BD)})."
        L.append(f"| {n} | **{s}** {nm.get(s, s)[:28]} ({industry(s)}) | {setup} | {c:.2f} | {plan} | {FA.get(s, '—')} |")
        log_rows.append(dict(signal=str(last.date()), sym=s, tier=t, close=round(float(c), 4), atr=round(float(a), 4), ml=round(float(ml), 3), pm=round(pmv, 5)))
    if any(t == 1 for _, t in top) and ZORDER == "volatility":
        L += ["", "Z score order: **most volatile first** (60-day volatility; ML rank 50%+ stays a filter). With more signals than free slots, take them from the top. "
                  "Tested 2013-26 (round 66, 5 slots x 5%): return/drawdown 0.39 / 0.37 (2013-19 / 2020-26) vs 0.24 / 0.27 in ML order; a yearly walk-forward chose it every year."]
    g = "neg" if half else "pos"; L += ["", f"How these setups did when chosen by this rule, 2020-26, net of costs (market model {'negative' if half else 'positive'} days):"]
    for t in sorted({t for _, t in top}):
        x = St.get(f"2020-26|{g}|{t}"); r = St.get(f"2020-26|{g}|random{40 if t == 1 else 20}")
        y = St.get(f"2024-26|{g}|{t}"); ry = St.get(f"2024-26|{g}|random{40 if t == 1 else 20}")
        if x: L.append(f"- {TIERS[t]['name']}: {100 * x['win']:.0f}% winners, {pc(x['avg'])} per trade (wins {pc(x['avg_win'])}, losses {pc(x['avg_loss'])}, "
                       f"median {x['hold']:.0f} sessions); random liquid stock {pc(r['avg'])}."
                       + (f" Since 2024: {100 * y['win']:.0f}% winners, {pc(y['avg'])} (random {pc(ry['avg'])})." if y and ry else ""))
    if any("LOSS" in FA.get(cols[j], "") for j, _ in top): L += ["", "Loss-making companies: in 2023-26 dips in loss-makers won 35-50% of the time vs 51-72% for profitable ones (one period only, so a caution, not a rule)."]
    more = [(j, t) for j, t in cand[3:] if t < 3][:6]
    if more: L += ["", "Also qualifying today: " + ", ".join(f"{cols[j]} {nm.get(cols[j], '')[:18]} ({TIERS[t]['name']}, ML {100 * pct[j]:.0f}%{_vt(i, j) if t == 1 else ''})" for j, t in more) + "."]
    elif all(t == 3 for _, t in top): L += ["", "No Z score or breakout signal at this close; the list is the top ML ranks."]
    TOPB = L; L = []
    if mron or KIND == "Z":   # ---- the plan book (planbook.py): Market returned (plan A) or Z score (plan Z)
        fdt = lambda x: pd.Timestamp(x).strftime("%a %d %b") if x else "-"
        nmj = lambda j: f"{cols[j]} {nm.get(cols[j], '')[:18]}".strip()
        turn = "" if O7 is None else (f"Market index (equal-weight liquid Saudi stocks): {pc(O7['bounce'])} above its 20-day low, {pc(O7['dd'], 0)} from its 1-year high -> "
              + (f"turn window **open** since {fdt(O7.get('window_start'))}, until about {fdt(O7.get('window_end'))}." if O7["gate"] else
                 "turn window **closed**" + (": no market-returned buys" if KIND == "A" else "") + " (it opens on a close 4% above the 20-day low after a fall of 10% or more)."))
        if KIND == "A": L += ["", "**Market returned signals** (Z score signals taken only after the market turns; at most 5 positions, most volatile first)", "", turn]
        else: L += ["", "**Z score signals** (first close at stretch Z -2.62 daily / -2.08 weekly, ML rank 50%+, market model positive, market momentum -1.18 or lower, "
                    "profitable company; at most 5 positions, most volatile first)"] + (["", turn + " For the Z score plan this is context only."] if turn else [])
        keep, due_p = ST["keep"], ST["due"]; tierk = 1 if KIND == "Z" else 4
        L += ["", f"Plan book: **{len(keep)} of {PB.SLOTS} slots in use**, {ST['free']} free" + (f" (your plan started on {fdt(SET['plan_start'])})" if SET["plan_start"] else "") + "."]
        if len(keep):
            L += ["", "| Held | Bought at the open of | Entry | Last close | So far | Sell at the open of |", "|---|---|---|---|---|---|"]
            for r in keep.sort_values("d1").itertuples():
                e = Of[r.d1, r.j]; L.append(f"| **{cols[r.j]}** {nm.get(cols[r.j], '')[:24]} | {fmt_d(dates[r.d1])} | {e:.2f} | {Cl[i, r.j]:.2f} | {pc(Cl[i, r.j] / e - 1)} | {fmt_d(day + (r.xo - T_) * BD)} |")
        if len(due_p): L += ["", "**SELL at today's open** (40 sessions done): " + "; ".join(f"**{cols[r.j]}** {nm.get(cols[r.j], '')[:18]} ({pc(Cl[i, r.j] / Of[r.d1, r.j] - 1)} so far)" for r in due_p.itertuples()) + "."]
        buys = [j for j, a in ST["new"] if a == "buy"]; nos = [j for j, a in ST["new"] if a == "noslot"]; wait = [j for j, a in ST["new"] if a == "wait"]; held_back = [j for j, a in ST["new"] if a == "rule"]
        if buys:
            L += ["", "**BUY at today's open:**", "", "| # | Stock | Setup | Last close | Plan | Latest accounts |", "|---|---|---|---|---|---|"]
            for n, j in enumerate(buys, 1):
                s_ = cols[j]; wk_ = not ZFIRST[i, j]
                setup = (f"{lab} (weekly candles): weekly stretch Z {ZWV[i, j]:.2f}" if wk_ else f"{lab}: stretch Z {ZC.iloc[i, j]:.2f}") + f", ML {100 * PB.PCTv[i, j]:.0f}%" + _vt(i, j)
                if KIND == "Z": setup += "; after the market turn" if ST["turn"] else "; before the market turn"
                L.append(f"| {n} | **{s_}** {nm.get(s_, s_)[:28]} ({industry(s_)}) | {setup} | {Cl[i, j]:.2f} | {mrsz} of the account. Hold 40 sessions (sell at the open around {fmt_d(day + 40 * BD)}). No stop. | {FA.get(s_, '—')} |")
                log_rows.append(dict(signal=str(last.date()), sym=s_, tier=tierk, close=round(float(Cl[i, j]), 4), atr=round(float(A[i, j]), 4), ml=round(float(PB.PCTv[i, j]), 3), pm=round(pmv, 5)))
        elif ST["gate"]: L += ["", f"No new {'Z score' if KIND == 'Z' else 'market-returned'} signal at this close."]
        if nos: L += ["", f"Not bought, no free slot ({PB.SLOTS} positions is the tested limit): " + ", ".join(nmj(j) for j in nos) + "."]
        if held_back: L += ["", "Not bought, held back by the plan's own limits: " + ", ".join(nmj(j) for j in held_back) + "."]
        if wait: L += ["", "Z score signals at this close, not bought (the market has not turned; each stays blocked for 40 sessions): " + ", ".join(nmj(j) for j in wait) + "."]
        for kind, txt in (("held", "Signal again in a stock you hold: keep holding, no second buy (the tested rule ignores it)"),
                          ("repeat", "Skipped, it signalled before and was not bought then (no second signal within its 40 sessions)"),
                          ("blocked", "Skipped, its paper trade started before the turn (blocked until that paper trade ends)")):
            xs = [(j, s0) for j, k, s0 in ST["rep"] if k == kind]
            if xs: L += ["", txt + ": " + ", ".join(f"{nmj(j)} (signal {fmt_d(dates[s0])})" for j, s0 in xs) + "."]
        if PLAN in ("A", "Z") and not buys: L += ["", "**Nothing to buy in your plan at this close.**" + ("" if len(keep) else " Idle money stays in the money-market fund.")]
        if KIND == "A":
            L += ["", "Plan record as traded (5 slots, most volatile first, round 68): 2013-19 26 trades, 73% winners, +16.8% per trade, worst -12.6%; "
                  "2020-26 25 trades, 84%, +9.4%, worst -12.3%. About 4 trades a year and none in 5 of the 14 years; it misses fast V-shaped rebounds "
                  "(April 2025) and lost in late 2015. No stop: 36 stop rules were tested (round 69) and none improved the plan; a position typically "
                  "closes about 6% below its entry at some point before it ends, and the plan's worst periods were about -10% of the account."]
        else:
            L += ["", "Plan record as traded (5 slots, most volatile first, round 70): 2013-19 33 trades, 70% winners, +10.4% per trade, worst -21.6%; "
                  "2020-26 36 trades, 72%, +7.8%, worst -15.5%. Trades in every year since 2014 (1 to 10 a year). About 3 in 10 trades lose."]
    MRB = L
    L = L0 + (MRB + ["", "---", "", "**For reference only, not in your plan** (ML leaders / breakouts: they add losing years and deeper drawdowns, round 67):"] + TOPB
              if PLAN in ("A", "Z") else TOPB + MRB)
    # earlier picks: exits due at this open, using the same exit rules (repeat picks while held are ignored)
    lf = os.path.join(H, "out/picks_log.csv"); old = pd.read_csv(lf, dtype={"sym": str}) if os.path.exists(lf) else pd.DataFrame(columns=["signal", "sym", "tier"])
    old = old[old.signal != str(last.date())]; due, still = [], 0; held = {}
    for _, r in old.sort_values("signal").iterrows():
        if r.sym not in cols or pd.Timestamp(r.signal) not in dates: continue
        if PLAN in ("A", "Z") and SET["plan_start"] and r.signal >= SET["plan_start"]: continue   # from the plan's start the plan book reports its positions; other picks are not in the plan
        if int(r.tier) == 4 and not SET["plan_start"]: continue                                      # Market returned positions without a plan: the book above reports them
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
          + (f"; your plan: at most 5 {lab} positions of {mrsz} (at most {5 * 100 * psz:.0f}% of the account in stocks), the rest in the money-market fund." if PLAN in ("A", "Z") else
             "; keep at most 5 Z score positions open at once, taking them from the top (as tested; with the market-momentum gate the worst Z-swing trade lost about 23%)." if any(t == 1 for _, t in top) else ".")]
    md = "\n".join(L); open(os.path.join(H, f"out/{last.date()}.md"), "w").write(md)
    pd.concat([old, pd.DataFrame(log_rows)]).to_csv(lf, index=False); print(md)

if __name__ == "__main__":
    history() if "--history" in sys.argv else live()
