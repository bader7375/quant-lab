"""Fable daily export: one JSON with everything the Fable brief and the Fable terminal show. It reads the work folder the live
pipeline maintains (prices, the walk-forward ranker and market model) and changes nothing there.

Usage: RE_WORK=<work folder> python3 export.py [--out <file>]     (default <work>/fable/fable_latest.json)

Both rules are replayed with the live engine (research/daily/planbook.py), so each day's output is the tested rule:
  live   = plan Z as you trade it (5 at once, 5% each)
  fable  = the ladder (one buy a day, 12 slots of 2.1%, 4.2% in a deep sell-off), on paper until you say yes
Ranges come from redrawing whole sell-offs (research/r71)."""
import os, sys, json, glob, datetime as dt, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import saudi, book; from engine import perf, block_bootstrap, MS_GATE, ZLINE, WLINE
WORK = saudi.work_dir(); B, PB = saudi.load(); P = PB.P; d = PB.dates; cols = list(PB.cols); T_ = PB.T_; i = T_ - 1; last = d[i]
sys.path.insert(0, os.path.join(WORK, "r27")); from zbands import band_next; from sectors import industry
BD = pd.offsets.CustomBusinessDay(weekmask="Sun Mon Tue Wed Thu"); R = lambda x, n=4: None if x is None or not np.isfinite(x) else round(float(x), n)
now = pd.Timestamp.now(tz="Asia/Riyadh").tz_localize(None); today = now.normalize(); day = BD.rollforward(today) if today > last else last + BD      # the session the list is for
wk_ok = day.to_period("W-THU") != last.to_period("W-THU")
SET = json.load(open(os.path.join(WORK, "daily/settings.json"))); START = SET.get("plan_start") or None; i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01")))
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31")}
# ---------------------------------------------------------------- names, accounts
def names():
    nm = {}; meta = json.load(open(os.path.join(WORK, "tadawul/meta.json"))); ex = json.load(open(os.path.join(WORK, "edge26/extra_names.json")))
    for s, m in meta.items(): nm[s] = m.get("full") or m.get("name") or s
    for s, n in ex.items(): nm.setdefault(s, n.title())
    for f in sorted(glob.glob(os.path.join(WORK, "edge26/data/fetch_*.json")))[-1:]:
        for s, v in json.load(open(f)).items():
            if isinstance(v, dict) and v.get("name"): nm[s] = v["name"]
    return nm
def accounts():
    out = {}
    for f in glob.glob(os.path.join(WORK, "r33/fund/*.json")):
        sy = os.path.basename(f)[:-5]; x = json.load(open(f)); ni = x.get("annualNetIncome", {}); eq = x.get("annualStockholdersEquity", {})
        ks = [k for k in sorted(ni) if pd.Timestamp(k) + pd.Timedelta(days=91) <= last]
        if ks: k = ks[-1]; e = eq.get(k); out[sy] = dict(fy=k[:4], ni_m=R(ni[k] / 1e6, 0), roe=R(ni[k] / e, 3) if e and e > 0 else None)
    return out
NM = names(); FA = accounts(); nm = lambda j: NM.get(cols[j], cols[j])
Cl, Of, MS, VOL, VOLP = PB.Cl, PB.Of, PB.MS, PB.VOL, PB.VOLP; ZC = PB.ZC.values; SIG = PB.signals(loss=True, week_complete=bool(wk_ok))
fdate = lambda t: str(pd.Timestamp(t).date()); sdate = lambda k: fdate(d[k]) if k < T_ else fdate(day + (k - T_) * BD)        # a session index beyond the data = a future Sun-Thu session
# ---------------------------------------------------------------- 1. market weather
MT = PB.MT; msv = float(MS[i]); pmv = float(PB.PMv[i]); E, eid = B.episodes(first=i0); cur = E.iloc[-1]; in_ep = bool(i - int(cur["last"]) <= 20)
state = ("deep storm" if msv <= book.DEEP else "storm") if msv <= MS_GATE else ("clearing" if in_ep else ("clouds" if msv <= MS_GATE / 2 else "calm"))
zl = ZC[i][PB.EL[i]]; idx = np.exp(np.nancumsum(B.mret.values))        # equal-weight index of the liquid stocks, without the gaps opt7 leaves on thin days
weather = dict(state=state, ms=R(msv, 2), gate=MS_GATE, deep=book.DEEP, pm=R(pmv, 4), pm_ok=bool(pmv > 0), n_liquid=int(PB.EL[i].sum()), fear=R(float((zl <= -2).mean()), 3), below_line=int((zl <= ZLINE).sum()),
               dd=R(MT.dd250.iloc[i], 4), bounce=R(MT.bounce.iloc[i], 4), turn=bool(PB.GATE[i]), chg1=R(idx[i] / idx[i - 1] - 1, 4), chg5=R(idx[i] / idx[i - 5] - 1, 4), chg20=R(idx[i] / idx[i - 20] - 1, 4),
               hist=dict(d=[fdate(x) for x in d[-250:]], ms=[R(x, 2) for x in MS[-250:]], idx=[R(100 * x / idx[-250], 2) for x in idx[-250:]], pm=[R(x, 4) for x in PB.PMv[-250:]]))
# ---------------------------------------------------------------- 2. the episode against past sell-offs
def path(a, lo=-10, hi=80): return [R(100 * idx[a + k] / idx[a], 2) if 0 <= a + k < T_ and np.isfinite(idx[a + k]) else None for k in range(lo, hi + 1)]
SHall = PB.shadow(PB.signals(loss=True)); SHall = SHall[SHall.i >= i0].reset_index(drop=True); done = SHall[SHall.ex < T_].reset_index(drop=True)
PLl = PB.plan(done, gate=PB.ALL); PLl["w"] = book.LIVE_SIZE; PLf = book.tested_plan(PB); eql = PB.account(PLl); eqf = PB.account(PLf)
past = []
for k, e in E.iterrows():
    a = int(e.start); b = int(E.start.iloc[k + 1]) if k + 1 < len(E) else T_; cash = float(np.prod(1 + B.rate[a:b]) - 1); res = lambda eq: R(float(eq.iloc[b - 1] / eq.iloc[a - 1] - 1) - cash, 4)
    low = float(np.nanmin(idx[a:min(a + 120, b)]) / idx[a] - 1); x = done[eid[done.i.values] == k]; tl = PLl[PLl.taken & (eid[PLl.i.values] == k)]; tf = PLf[PLf.taken & (eid[PLf.i.values] == k)]
    past.append(dict(start=fdate(d[a]), sessions=int(e.n), depth=R(e.depth, 2), low=R(low, 4), signals=int(len(x)), live=res(eql), fable=res(eqf), live_n=int(len(tl)), fable_n=int(len(tf)), path=path(a), open=bool(k == len(E) - 1 and in_ep)))
closed = [p for p in past if not p["open"]]; arr = np.array([[v if v is not None else np.nan for v in p["path"][10:]] for p in closed], float)
fan = {f"p{q}": [R(x, 2) for x in np.nanpercentile(arr, q, axis=0)] for q in (10, 25, 50, 75, 90)}
a0 = int(cur.start); episode = dict(open=in_ep, start=fdate(d[a0]), day=int(i - a0), stretched=int(cur.n), depth=R(cur.depth, 2), since=R(idx[i] / idx[a0] - 1, 4), low=R(float(np.nanmin(idx[a0:]) / idx[a0] - 1), 4),
                                    deeper_than=int(sum(p["depth"] > cur.depth for p in closed)), of=len(closed), fan=fan)
# ---------------------------------------------------------------- 3. the two books at this close
def row(p, kind):
    j = p["j"]; e = Of[p["d1"], j] if p.get("d1") is not None and p["d1"] < T_ else None
    return dict(sym=cols[j], name=nm(j)[:30], w=R(p["w"], 4), signal=fdate(d[p["i"]]), bought=sdate(p["d1"]) if "d1" in p else None, entry=R(e, 3), last=R(Cl[i, j], 3), ret=R(Cl[i, j] / e - 1, 4) if e else None,
                held=int(i - p["d1"] + 1) if "d1" in p else 0, left=int(p["xo"] - T_) if "xo" in p else book.PB_HOLD, sell=sdate(p["xo"]) if "xo" in p else None, deep=bool(MS[p["i"]] <= book.DEEP))
book.PB_HOLD = PB.HOLD; BOOKS = {}
for rule in ("live", "fable"):
    s = book.state(PB, start=START, week_complete=bool(wk_ok), rule=rule)
    BOOKS[rule] = dict(slots=s["slots"], free=s["free"], start=START, held=[row(p, "held") for p in s["held"]], due=[row(p, "due") for p in s["due"]],
                       buys=[dict(sym=cols[b["j"]], name=nm(b["j"])[:30], w=R(b["w"], 4), close=R(Cl[i, b["j"]], 3), sell=sdate(T_ + PB.HOLD), deep=bool(msv <= book.DEEP)) for b in s["buys"]],
                       skipped=[dict(sym=cols[x["j"]], name=nm(x["j"])[:30], why=x["why"]) for x in s["skipped"]], repeats=[dict(sym=cols[x["j"]], name=nm(x["j"])[:30], kind=x["kind"], since=fdate(d[x["since"]])) for x in s["repeats"]],
                       invested=R(sum(p["w"] for p in s["held"]) + sum(b["w"] for b in s["buys"]), 4))
# ---- the record: what the list told you to buy stays in your book even if a later model refit moves a past gate (round 71: a few
# past signals flip from one daily run to the next because the market model is refit every day and sits near zero on some days)
LEDF = os.path.join(WORK, "fable", "ledger.json"); os.makedirs(os.path.dirname(LEDF), exist_ok=True); LED = json.load(open(LEDF)) if os.path.exists(LEDF) else {}; RECW = []; asof = fdate(last); dix = {fdate(x): k for k, x in enumerate(d)}
for rule, Bk in BOOKS.items():
    L_ = LED.setdefault(rule, []); have = {(e["sym"], e["signal"]) for e in L_}
    for b in Bk["buys"]:
        if (b["sym"], asof) not in have: L_.append(dict(sym=b["sym"], signal=asof, w=b["w"], sell=b["sell"])); have.add((b["sym"], asof))
    for p in Bk["held"] + Bk["due"]:                                         # a first run or a rebuilt folder: take the replay's positions into the record
        if (p["sym"], p["signal"]) not in have: L_.append(dict(sym=p["sym"], signal=p["signal"], w=p["w"], sell=p["sell"], from_replay=True)); have.add((p["sym"], p["signal"]))
    shown = {(p["sym"], p["signal"]) for p in Bk["held"] + Bk["due"]} | {(b["sym"], asof) for b in Bk["buys"]}
    for e in L_:
        if (e["sym"], e["signal"]) in shown or e["signal"] not in dix or e["sym"] not in cols: continue
        i_s = dix[e["signal"]]; d1 = i_s + 1; xo = d1 + PB.HOLD
        if d1 <= i and xo >= T_:                                             # bought, not yet sold, and missing from today's replay
            p = row(dict(j=cols.index(e["sym"]), i=i_s, d1=d1, xo=xo, w=e["w"]), "held"); p["record_only"] = True; (Bk["due"] if xo == T_ else Bk["held"]).append(p)
            RECW.append(dict(rule=rule, sym=e["sym"], name=p["name"], signal=e["signal"], sell=p["sell"]))
    Bk["free"] = int(Bk["slots"] - len(Bk["held"])); Bk["invested"] = R(sum(p["w"] for p in Bk["held"]) + sum(b["w"] for b in Bk["buys"]), 4)
json.dump(LED, open(LEDF, "w"), indent=1)
# the same two rules had they been running through this sell-off (no start date): tells the episode's story; it is a replay, not your account
REPLAY = {}
for rule in ("live", "fable"):
    s = book.state(PB, start=None, week_complete=bool(wk_ok), rule=rule); REPLAY[rule] = dict(held=[row(p, "held") for p in s["held"]], buys=[cols[b["j"]] for b in s["buys"]], free=s["free"], invested=R(sum(p["w"] for p in s["held"]), 4),
                                                                                         pnl=R(sum(p["w"] * (Cl[i, p["j"]] / Of[p["d1"], p["j"]] - 1) for p in s["held"]), 5))
# ---------------------------------------------------------------- 4. signals at this close, with "why this stock"
C_ = PB.C; BDn = band_next(C_, ZLINE).iloc[-1]; B0 = band_next(C_, 0.0).iloc[-1]; fresh = set(int(j) for j in np.where(SIG[i])[0])
act = {r: {x["sym"]: "buy" for x in BOOKS[r]["buys"]} | {x["sym"]: x["why"] for x in BOOKS[r]["skipped"]} | {x["sym"]: ("held" if x["kind"] == "held" else "signalled before") for x in BOOKS[r]["repeats"]} for r in BOOKS}
def card(j, n=90):
    s = cols[j]; c = Cl[i, j]; f = FA.get(s); zw = PB.ZWV[i, j] if np.isfinite(PB.ZWV[i, j]) else None
    return dict(sym=s, name=nm(j)[:34], sector=industry(s), close=R(c, 3), chg=R(c / Cl[i - 1, j] - 1, 4), z=R(ZC[i, j], 2), zw=R(zw, 2), weekly=bool(not PB.ZFIRST[i, j] and PB.WFIRST[i, j]), ml=R(PB.PCTv[i, j], 3),
                vol=R(VOL[i, j], 4), volr=R(VOLP[i, j], 3), val_m=R(float(P["VAL"].iloc[-60:, j].median()) / 1e6, 1), acct=f, loss=bool(PB.LOSS[i, j]), liquid=bool(PB.EL[i, j]),
                band=R(BDn.iloc[j], 3), band0=R(B0.iloc[j], 3), hi52=R(c / np.nanmax(Cl[-250:, j]) - 1, 4), px=[R(x, 3) for x in Cl[-n:, j]], zs=[R(x, 2) for x in ZC[-n:, j]])
signals = []
for j in sorted(fresh, key=lambda j: -np.nan_to_num(VOL[i, j], nan=-9)):
    c = card(j); c.update(live=act["live"].get(cols[j], "paper only"), fable=act["fable"].get(cols[j], "paper only"), w_live=book.LIVE_SIZE, w_fable=R(book.size(msv), 4)); signals.append(c)
# watch list: liquid stocks one close away from a first touch, nearest first, with every gate
gates_now = dict(pm=bool(pmv > 0), ms=bool(msv <= MS_GATE)); open_paper = set(int(j) for j in SHall[(SHall.ex >= T_) & (SHall.i < i)].j); watch = []
for j in np.argsort(np.where(PB.EL[i] & np.isfinite(ZC[i]) & (ZC[i] > ZLINE), ZC[i], np.inf))[:60]:
    if not (PB.EL[i, j] and np.isfinite(ZC[i, j]) and ZC[i, j] > ZLINE) or not np.isfinite(BDn.iloc[j]): continue
    need = BDn.iloc[j] / Cl[i, j] - 1
    if need < -.10: continue                                                 # beyond the daily limit: cannot touch tomorrow
    c = card(j, n=60); c.update(need=R(need, 4), ml_ok=bool(np.nan_to_num(PB.PCTv[i, j], nan=-1) >= .5), paper_open=bool(j in open_paper)); c["ok"] = bool(c["ml_ok"] and not c["loss"] and gates_now["pm"] and gates_now["ms"] and not c["paper_open"]); watch.append(c)
    if len(watch) >= 14: break
CARDS = {}                                                                    # "why this stock" for every stock the books mention
for grp in (BOOKS["live"], BOOKS["fable"], REPLAY["live"], REPLAY["fable"]):
    for p in list(grp.get("held", [])) + list(grp.get("due", [])):
        if p["sym"] not in CARDS: CARDS[p["sym"]] = card(cols.index(p["sym"]), n=60)
# ---------------------------------------------------------------- 5. what the test record expects (fans, ranges, record)
def paths(T):
    out = np.full((len(T), PB.HOLD + 1), np.nan); out[:, 0] = 0
    for n_, r in enumerate(T.itertuples()):
        e = Of[r.d1, r.j]
        for k in range(1, PB.HOLD + 1):
            if r.d1 + k - 1 < T_: out[n_, k] = PB.Cf[r.d1 + k - 1, r.j] / e - 1
    return out
PA = paths(done); net = PB.trade_net(done.assign(xo=done.ex, fill=np.nan)); deepm = MS[done.i.values] <= book.DEEP
expect = dict(n=int(len(done)), fan={f"p{q}": [R(x, 4) for x in np.nanpercentile(PA, q, axis=0)] for q in (5, 25, 50, 75, 95)}, mean=[R(x, 4) for x in np.nanmean(PA, axis=0)],
              final=dict(all=dict(n=int(len(net)), avg=R(net.mean()), win=R((net > 0).mean(), 3), q=[R(np.quantile(net, q)) for q in (.05, .25, .5, .75, .95)]),
                         deep=dict(n=int(deepm.sum()), avg=R(net[deepm].mean()), win=R((net[deepm] > 0).mean(), 3)), shallow=dict(n=int((~deepm).sum()), avg=R(net[~deepm].mean()), win=R((net[~deepm] > 0).mean(), 3))))
def pct_at(ret, k):
    v = PA[:, min(max(k, 1), PB.HOLD)]; v = v[np.isfinite(v)]; return R(float((v < ret).mean()), 3)
blk = eid.copy(); blk[i0:E.start.iloc[0]] = len(E)
def ranges(PL, sizes, key):
    out = []
    for s in sizes:
        eq = PB.account(PL.assign(w=PL.w * s)); bs = block_bootstrap({"x": eq.pct_change().fillna(0).values}, blk, n=1000, seed=71)["x"]; q = lambda v: [R(np.quantile(v, p), 4) for p in (.05, .5, .95)]
        out.append(dict(mult=s, pos=R(PL.w.min() * s, 4), most=R((.25 if key == "live" else .50) * s, 3), g=q(bs[:, 0]), dd=q(bs[:, 1]), eras={e: [R(perf(eq, a, b_)["cagr"], 4), R(perf(eq, a, b_)["dd"], 4)] for e, (a, b_) in ER.items()}))
    return out
sizing = dict(live=ranges(PLl, [.6, .8, 1.0, 1.2, 1.4, 1.6, 2.0], "live"), fable=ranges(PLf, [.5, .75, 1.0, 1.2, 1.5], "fable"), note="range = 5th to 95th percentile over 1,000 redraws of whole sell-offs, 2013-26")
def rec(PL):
    tk = PL[PL.taken]; n = PB.trade_net(tk.assign(fill=np.nan)); y = d[tk.i.values].year; f = lambda m: dict(n=int(m.sum()), win=R((n[m] > 0).mean(), 3), avg=R(n[m].mean()), worst=R(n[m].min())) if m.sum() else None
    return dict(all=f(y >= 2013), a=f(y <= 2019), b=f(y >= 2020), c=f(y >= 2023))
record = dict(live=rec(PLl), fable=rec(PLf))
# ---------------------------------------------------------------- 6. forward scorecard (from the plan's start) and this sell-off's paper trades
def score(rule):
    T = (PB.plan(SHall, gate=PB.ALL, start=START) if rule == "live" else PB.plan(SHall, gate=PB.ALL, slots=book.SLOTS, pace=book.PACE, start=START)); T = T[T.taken & (T.d1 < T_)]; rows = []
    for r in T.itertuples():
        k = int(min(i, r.xo - 1) - r.d1 + 1); e = Of[r.d1, r.j]; closed_ = bool(r.xo < T_); x = (Of[r.xo, r.j] if closed_ else Cl[i, r.j]) / e - 1
        rows.append(dict(sym=cols[r.j], name=nm(r.j)[:26], bought=fdate(d[r.d1]), entry=R(e, 3), ret=R(x, 4), day=k, closed=closed_, pct=pct_at(x, k), w=R(book.size(MS[r.i]) if rule == "fable" else book.LIVE_SIZE, 4)))
    return rows
op = SHall[(SHall.ex >= T_) & (SHall.d1 < T_)]; paper_now = []
for r in op.sort_values("i").itertuples():
    k = int(i - r.d1 + 1); x = Cl[i, r.j] / Of[r.d1, r.j] - 1; paper_now.append(dict(sym=cols[r.j], name=nm(r.j)[:26], bought=fdate(d[r.d1]), ret=R(x, 4), day=k, pct=pct_at(x, k), deep=bool(MS[r.i] <= book.DEEP)))
scorecard = dict(start=START, live=score("live"), fable=score("fable"), paper=paper_now, paper_avg=R(float(np.mean([p["ret"] for p in paper_now])), 4) if paper_now else None,
                 paper_pct=R(float(np.median([p["pct"] for p in paper_now])), 3) if paper_now else None)
# ---------------------------------------------------------------- 7. evidence (static files from the research rounds) and the US part
def rj(*p):
    f = os.path.join(HERE, "..", "research", *p); return json.load(open(f)) if os.path.exists(f) else None
r73 = rj("r73", "r73_results.json"); w72 = rj("r72", "world72b.json"); w73 = rj("r73", "world73.json"); evidence = {}
if r73:
    c = r73["candidates"]; bs = r73["bootstrap"]
    evidence["saudi"] = {k: dict(eras={e: [R(v["cagr"], 4), R(v["dd"], 4)] for e, v in c[k]["equal_risk"].items()}, range={e: dict(g=bs[e][k]["cagr_range"], dd=bs[e][k]["dd_range"], p_growth=bs[e][k].get("p_growth"), p_dd=bs[e][k].get("p_dd"), p_ratio=bs[e][k].get("p_ratio")) for e in bs},
                                 trades=c[k]["trades"], win=c[k]["win"], avg=c[k]["avg"], worst=c[k]["worst"]) for k in ("LIVE", "L12D")}
    evidence["stress"] = dict(passed=r73["stress_passed"], of=len(r73["stress"]))
if w72 and w73:
    evidence["world"] = dict(market_eras=w73["counted"], ladder_beats=w72["vs_A0"]["L12D"]["share"], by_era=w72["vs_A0"]["L12D"]["by_era"], pace3_beats=w72["vs_A0"]["P(5,3)"]["share"], costs=w73["stress"]["costs"]["share"], late=w73["stress"]["late"]["share"],
                             tails=w73["tails"], edge=w72["edge_pooled"])
us = None
try:
    t27 = json.load(open(os.path.join(WORK, "r27/today27.json"))); u = t27.get("us_scan") or {}; u30 = t27.get("us30") or {}
    us = dict(date=u.get("date"), ms=u.get("ms"), gate=u.get("gate"), window=bool(u30.get("window")), etf=(t27.get("us") or {}).get("etf"), near=[dict(sym=r_.get("sym"), z=r_.get("zc"), note=r_.get("act") or r_.get("note")) for r_ in (u.get("rows") or [])[:6]])
except Exception as ex: us = dict(error=str(ex)[:120])
# ---------------------------------------------------------------- write
nlast = int(np.isfinite(Cl[i]).sum())
after_close = today.dayofweek in (6, 0, 1, 2, 3) and (now.hour, now.minute) >= (15, 45)          # Sunday to Thursday, once Yahoo normally has the close
expected = today if after_close else today - BD; stale = bool(last < expected)                    # the newest close should be the last finished session
OUT = dict(v=1, asof=fdate(last), day=fdate(day), made=now.strftime("%Y-%m-%d %H:%M") + " Riyadh", stocks=nlast, stale=stale,
           rule=dict(live=dict(slots=book.LIVE_SLOTS, size=book.LIVE_SIZE, most=.25), fable=dict(slots=book.SLOTS, per_day=1, size=R(book.BASE, 4), deep_size=R(book.BASE * book.MULT, 4), deep=book.DEEP, most=.50, status="paper")),
           weather=weather, episode=episode, past=past, live=BOOKS["live"], fable=BOOKS["fable"], record_warn=RECW, replay=REPLAY, signals=signals, watch=watch, cards=CARDS, expect=expect, sizing=sizing, record=record, scorecard=scorecard, evidence=evidence, us=us)
def clean(x):
    if isinstance(x, dict): return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [clean(v) for v in x]
    if isinstance(x, (np.floating, float)): return None if not np.isfinite(x) else float(x)
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (np.bool_,)): return bool(x)
    return x
out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(WORK, "fable", "fable_latest.json"); os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(clean(OUT), open(out, "w"), allow_nan=False, separators=(",", ":"))
ledger = dict(asof=OUT["asof"], day=OUT["day"], made=OUT["made"], weather=dict(state=state, ms=weather["ms"], pm_ok=weather["pm_ok"]), live=dict(buys=[dict(sym=b["sym"], w=b["w"]) for b in BOOKS["live"]["buys"]], sells=[p["sym"] for p in BOOKS["live"]["due"]], held=[p["sym"] for p in BOOKS["live"]["held"]]),
              fable=dict(buys=[dict(sym=b["sym"], w=b["w"]) for b in BOOKS["fable"]["buys"]], sells=[p["sym"] for p in BOOKS["fable"]["due"]], held=[p["sym"] for p in BOOKS["fable"]["held"]]), signals=[s["sym"] for s in signals])
json.dump(clean(ledger), open(os.path.join(os.path.dirname(out), f"day_{OUT['asof']}.json"), "w"), allow_nan=False, separators=(",", ":"))
print(f"fable export: close {OUT['asof']} for {OUT['day']} | weather {state}, momentum {msv:+.2f}, market model {'positive' if pmv > 0 else 'negative'} | signals {len(signals)} | live buys {len(BOOKS['live']['buys'])}, "
      f"ladder buys {len(BOOKS['fable']['buys'])} | {os.path.getsize(out) / 1024:.0f} KB -> {out}")
