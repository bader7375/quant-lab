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
def rj(*p):
    f = os.path.join(HERE, "..", "research", *p); return json.load(open(f)) if os.path.exists(f) else None
# ---------------------------------------------------------------- 6b. the Fable swing (rounds 76-78): paper book, record, scanner, chart data
import swingrule as SR, swingbook as SBk, swing as SWm
G_ = SR.gate(B); wxA = SBk.prep(B)["wx"]; Zs = SBk.prep(B)["Z"]; wnow = int(wxA[i])
eqT, TRT, ORT = SR.run(B)                                                    # the tested book since 2013 (a replay)
eqF, TRF, ORF = SR.run(B, start=SR.START)                                     # the paper book since the rule was fixed
BLn = band_next(C_, SR.LINE).iloc[-1].values; SLn = band_next(C_, SR.TARGET).iloc[-1].values     # tomorrow's close for stretch Z = the buy line / the sell level
def spos(p):
    j = p["j"]; e = p["entry"]; k = int(i - p["d1"] + 1)
    return dict(sym=cols[j], name=nm(j)[:30], w=R(p["w"], 4), signal=fdate(d[p["i"]]), bought=fdate(d[p["d1"]]), entry=R(e, 3), last=R(Cl[i, j], 3), ret=R(Cl[i, j] / e - 1, 4), held=k, left=int(p["cap"] - k), z=R(Zs[i, j], 2),
                sellpx=R(SLn[j], 3), latest=sdate(p["d1"] + p["cap"]), deep=bool(wxA[p["i"]] == 3), why=({0: "the stretch is gone", 1: "40 sessions done"}.get(p["flag"]) if p["flag"] is not None else None))
def sbook(OR, TR, start):
    sells = {j for j, _ in OR["sells"]}; heldj = {p["j"] for p in OR["held"]}; held = [spos(p) for p in OR["held"] if p["j"] not in sells]; due = [spos(p) for p in OR["held"] if p["j"] in sells]; bj = [b["j"] for b in OR["buys"]]
    buys = [dict(sym=cols[b["j"]], name=nm(b["j"])[:30], w=R(b["w"], 4), close=R(Cl[i, b["j"]], 3), z=R(Zs[i, b["j"]], 2), deep=bool(wnow == 3), latest=sdate(T_ + SR.CAP)) for b in OR["buys"]]
    full = len(held) + len(buys) >= SR.SLOTS
    skipped = [dict(sym=cols[j], name=nm(j)[:30], why=("already held" if j in heldj else "no free slot" if full else "one buy a day: a more volatile signal was taken")) for j in OR["cands"] if j not in bj]
    cl = TR.sort_values("ex").tail(40) if len(TR) else TR
    closed = [dict(sym=cols[r.j], name=nm(r.j)[:26], bought=fdate(d[r.d1]), sold=fdate(d[r.ex]), ret=R(r.ret - .004, 4), held=int(r.ex - r.d1), w=R(r.w, 4), why=("stretch gone" if r.why == 0 else "40 sessions")) for r in cl.itertuples()][::-1]
    return dict(slots=SR.SLOTS, free=int(SR.SLOTS - len(held)), start=start, held=held, due=due, buys=buys, skipped=skipped, closed=closed, invested=R(sum(p["w"] for p in held) + sum(b["w"] for b in buys), 4),
                pnl=R(sum(p["w"] * p["ret"] for p in held + due), 5))
SWB = sbook(ORF, TRF, SR.START); SWR = sbook(ORT, TRT, None); SWR["closed"] = SWR["closed"][:12]
Ls = LED.setdefault("swing", []); haveS = {(e["sym"], e["signal"]): e for e in Ls}                 # the record of listed swing buys (see section 3)
for b in SWB["buys"]:
    if (b["sym"], asof) not in haveS: e = dict(sym=b["sym"], signal=asof, w=b["w"]); Ls.append(e); haveS[(b["sym"], asof)] = e
for p in SWB["held"] + SWB["due"]:
    if (p["sym"], p["signal"]) not in haveS: e = dict(sym=p["sym"], signal=p["signal"], w=p["w"], from_replay=True); Ls.append(e); haveS[(p["sym"], p["signal"])] = e
for p in SWB["due"]: haveS[(p["sym"], p["signal"])]["sold_on"] = fdate(day)
shownS = {(p["sym"], p["signal"]) for p in SWB["held"] + SWB["due"]} | {(b["sym"], asof) for b in SWB["buys"]}
for e in Ls:
    if e.get("sold_on") or (e["sym"], e["signal"]) in shownS or e["signal"] not in dix or e["sym"] not in cols: continue
    i_s = dix[e["signal"]]; j = cols.index(e["sym"])
    if i_s + 1 > i: continue
    st_, x_ = SR.status(B, i_s, j); p = spos(dict(j=j, i=i_s, d1=i_s + 1, entry=Of[i_s + 1, j], w=e["w"], cap=SR.CAP, flag=None)); p["record_only"] = True
    if st_ == "held": SWB["held"].append(p); RECW.append(dict(rule="swing", sym=e["sym"], name=p["name"], signal=e["signal"], sell=p["latest"]))
    else: p["why"] = "the stretch is gone or 40 sessions are done"; SWB["due"].append(p); e["sold_on"] = fdate(day); RECW.append(dict(rule="swing", sym=e["sym"], name=p["name"], signal=e["signal"], sell=fdate(day), overdue=bool(st_ == "sold")))
SWB["free"] = int(SR.SLOTS - len(SWB["held"])); json.dump(LED, open(LEDF, "w"), indent=1)
def sw_stats(TR, a, b):
    y = d[TR.d1.values]; m = (y >= a) & (y <= b); x = TR[m]; n = x.ret.values - .004
    return dict(n=int(len(x)), win=R((n > 0).mean(), 3), avg=R(n.mean()), worst=R(n.min()), held=R((x.ex - x.d1).mean(), 1)) if len(x) else dict(n=0)
netT = TRT.ret.values - .004; yT = d[TRT.d1.values].year
swing = dict(rule=dict(line=SR.LINE, target=SR.TARGET, cap=SR.CAP, slots=SR.SLOTS, per_day=SR.PER_DAY, size=R(SR.BASE, 4), deep_size=R(SR.BASE * SR.DEEP_MULT, 4), most=.50, start=SR.START, status="paper"),
             book=SWB, replay=SWR, record=dict(eras={e: dict(g=R(perf(eqT, a, b_)["cagr"], 4), dd=R(perf(eqT, a, b_)["dd"], 4), **sw_stats(TRT, a, b_)) for e, (a, b_) in ER.items()},
                                               by_year={int(k): int(v) for k, v in pd.Series(yT).value_counts().sort_index().items()}, years=sorted(set(int(y_) for y_ in range(2013, int(d[-1].year) + 1)))),
             expect=dict(n=int(len(netT)), avg=R(netT.mean()), win=R((netT > 0).mean(), 3), q=[R(np.quantile(netT, q)) for q in (.05, .25, .5, .75, .95)], held=[R(np.quantile((TRT.ex - TRT.d1).values, q), 0) for q in (.25, .5, .75)]))
def ranges_sw(mults):
    out = []
    for k in mults:
        eq = SR.run(B, k=k)[0]; bs = block_bootstrap({"x": eq.pct_change().fillna(0).values}, blk, n=1000, seed=71)["x"]; q = lambda v: [R(np.quantile(v, p), 4) for p in (.05, .5, .95)]
        out.append(dict(mult=k, pos=R(SR.BASE * k, 4), most=R(.50 * k, 3), g=q(bs[:, 0]), dd=q(bs[:, 1]), eras={e: [R(perf(eq, a, b_)["cagr"], 4), R(perf(eq, a, b_)["dd"], 4)] for e, (a, b_) in ER.items()}))
    return out
sizing["swing"] = ranges_sw([.5, .75, 1.0, 1.25, 1.5])
for k_, p_ in zip(range(len(past)), past):                                    # the swing's result in each sell-off, beside the other two
    a = int(E.start.iloc[k_]); b_ = int(E.start.iloc[k_ + 1]) if k_ + 1 < len(E) else T_; p_["swing"] = R(float(eqT.iloc[b_ - 1] / eqT.iloc[a - 1] - 1) - float(np.prod(1 + B.rate[a:b_]) - 1), 4); p_["swing_n"] = int(((TRT.d1 >= a) & (TRT.d1 < b_)).sum())
# ---- the edge score: average next-5-session result of a gated liquid stock by stretch and weather, Saudi pulled toward the other markets
EDG = np.array([-99, -3.5, -3.0, -2.5, -2.0, -1.5, -1.0, -.5, 0, .5, 1.0, 2.0, 99]); ELAB = ["<-3.5", "-3.5..-3", "-3..-2.5", "-2.5..-2", "-2..-1.5", "-1.5..-1", "-1..-.5", "-.5..0", "0..0.5", "0.5..1", "1..2", ">2"]
F5 = SWm.fwd(Of, 5); Ssum = np.zeros((4, 12)); Sn = np.zeros((4, 12)); Gm = PB.EL & G_
for t in range(max(i0, 260), T_ - 7):
    if wxA[t] < 0: continue
    m = Gm[t] & np.isfinite(Zs[t]) & np.isfinite(F5[t])
    if m.any(): k = np.digitize(Zs[t][m], EDG) - 1; np.add.at(Ssum[wxA[t]], k, F5[t][m]); np.add.at(Sn[wxA[t]], k, 1)
wmap = (rj("r76", "map76.json") or {}).get("world", {}); KSH = 300.0; EMAP = np.full((4, 12), np.nan); edge_rows = []
for w_ in range(4):
    for k in range(12):
        mw = (wmap.get(f"{SWm.WEATHER[w_]}|{ELAB[k]}") or {}).get("r"); ms_ = Ssum[w_, k] / Sn[w_, k] if Sn[w_, k] > 0 else None
        if mw is None and ms_ is None: continue
        v = ms_ if mw is None else mw if ms_ is None else (Sn[w_, k] * ms_ + KSH * mw) / (Sn[w_, k] + KSH); EMAP[w_, k] = v
        edge_rows.append(dict(w=w_, k=k, e=R(v, 4), saudi=R(ms_, 4), n=int(Sn[w_, k]), world=R(mw, 4)))
def edge_of(j): return R(EMAP[wnow, int(np.digitize(Zs[i, j], EDG) - 1)], 4) if wnow >= 0 and np.isfinite(Zs[i, j]) else None
# ---- the scanner: every liquid stock at this close
inzL, ageL = SBk.zone_age(B, SR.LINE); fw_h = {p["sym"] for p in SWB["held"]}; fw_s = {p["sym"] for p in SWB["due"]}; fw_b = {b["sym"] for b in SWB["buys"]}; rp_h = {p["sym"] for p in SWR["held"] + SWR["due"]}; cand_now = set(cols[j] for j in ORF["cands"])
scan = []; liqj = [j for j in range(len(cols)) if PB.EL[i, j] and np.isfinite(Zs[i, j])]
for j in liqj:
    s_ = cols[j]; c = Cl[i, j]; z = float(Zs[i, j]); need = BLn[j] / c - 1 if np.isfinite(BLn[j]) else None; inz = bool(inzL[i, j]); bits = SR.gate_bits(B, i, j)
    st_ = "sell" if s_ in fw_s else "held" if s_ in fw_h else "buy" if s_ in fw_b else "cand" if s_ in cand_now else "zone" if inz else "near" if need is not None and need >= -.05 else ""
    scan.append(dict(sym=s_, name=nm(j)[:26], sec=industry(s_), c=R(c, 3), chg=R(c / Cl[i - 1, j] - 1, 4), z=R(z, 2), zp=R(Zs[i - 1, j], 2), line=R(BLn[j], 3), need=R(need, 4), inz=inz, age=int(ageL[i, j]) if inz else None,
                     cross=bool(inz and ageL[i, j] == 0), ml=R(PB.PCTv[i, j], 2), loss=bool(PB.LOSS[i, j]), vr=R(VOLP[i, j], 2), gb=int(bits), e=edge_of(j), st=st_, rp=bool(s_ in rp_h), sellpx=R(SLn[j], 3)))
scan.sort(key=lambda r: (r["z"] if r["z"] is not None else 9))
scan_sum = dict(n=len(scan), inzone=int(sum(r["inz"] for r in scan)), crossed=int(sum(r["cross"] for r in scan)), cands=int(len(cand_now)), near=int(sum(r["st"] == "near" for r in scan)), window=bool(wnow in SR.WPLAN), pm_ok=bool(pmv > 0))
# ---- chart data: the last NB sessions of every liquid stock (and every stock a book holds), in a few documents
NB = 380; a0 = T_ - NB; Hh = P["H"].values.astype(float); Ll = P["L"].values.astype(float); Oo = P["O"].values.astype(float); rp = lambda x: None if not np.isfinite(x) else (round(float(x), 2) if abs(x) >= 20 else round(float(x), 3))
BLs = band_next(C_, SR.LINE).shift(1).values; SLs = band_next(C_, SR.TARGET).shift(1).values; CIN = SWm.cross_in(Zs, SR.LINE); bought = {(int(r.i), int(r.j)) for r in TRT.itertuples()} | {(p["i"], p["j"]) for p in ORT["held"]}
fwd_set = {(int(r.i), int(r.j)) for r in TRF.itertuples()} | {(p["i"], p["j"]) for p in ORF["held"]}
def chart_doc(j):
    sl = slice(a0, T_); tr = []
    for r in TRT[(TRT.j == j) & (TRT.ex > a0)].itertuples(): tr.append([int(r.d1 - a0), int(r.ex - a0), rp(Of[r.d1, j]), rp(Of[r.ex, j]), R(r.ret - .004, 4), R(r.w, 4), int(r.why), int((int(r.i), j) in fwd_set)])
    for p in ORT["held"]:
        if p["j"] == j: tr.append([int(p["d1"] - a0), None, rp(p["entry"]), None, R(Cl[i, j] / p["entry"] - 1, 4), R(p["w"], 4), -1, int((p["i"], j) in fwd_set)])
    xs = [[int(t - a0), 0 if (t, j) in bought else (-1 if SR.gate_bits(B, t, j) == 0 else int(SR.gate_bits(B, t, j)))] for t in range(a0, T_) if CIN[t, j]]
    return dict(o=[rp(x) for x in Oo[sl, j]], h=[rp(x) for x in Hh[sl, j]], l=[rp(x) for x in Ll[sl, j]], c=[rp(x) for x in Cl[sl, j]], z=[R(x, 2) for x in Zs[sl, j]], bl=[rp(x) for x in BLs[sl, j]], sl=[rp(x) for x in SLs[sl, j]],
                nbl=rp(BLn[j]), nsl=rp(SLn[j]), tr=[v for r in tr for v in r], x=[v for r in xs for v in r], name=nm(j)[:34], sec=industry(cols[j]))    # tr: 8 values a trade, x: 2 values a cross (flat: the database takes no list inside a list)
extra = {cols.index(p["sym"]) for g_ in (BOOKS["live"], BOOKS["fable"], REPLAY["live"], REPLAY["fable"], SWB, SWR) for p in list(g_.get("held", [])) + list(g_.get("due", []))}
cj = sorted(set(liqj) | extra, key=lambda j: cols[j]); CH = 12; chart_index = {}; outdir_ = os.path.join(WORK, "fable"); os.makedirs(outdir_, exist_ok=True)
for f_ in glob.glob(os.path.join(outdir_, "chart_*.json")): os.remove(f_)
for n_ in range(0, len(cj), CH):
    part = cj[n_:n_ + CH]; doc = dict(n=n_ // CH, asof=fdate(last), stocks={cols[j]: chart_doc(j) for j in part}); json.dump(doc, open(os.path.join(outdir_, f"chart_{n_ // CH}.json"), "w"), separators=(",", ":"))
    for j in part: chart_index[cols[j]] = n_ // CH
market = dict(asof=fdate(last), d=[int(x.strftime("%Y%m%d")) for x in d[a0:]], ms=[R(x, 2) for x in MS[a0:]], wx=[int(x) for x in wxA[a0:]], idx=[R(100 * x / idx[a0], 2) for x in idx[a0:]], pm=[R(x, 4) for x in PB.PMv[a0:]])
json.dump(market, open(os.path.join(outdir_, "market.json"), "w"), separators=(",", ":"))
# ---------------------------------------------------------------- 7. evidence (static files from the research rounds) and the US part
r73 = rj("r73", "r73_results.json"); w72 = rj("r72", "world72b.json"); w73 = rj("r73", "world73.json"); evidence = {}
if r73:
    c = r73["candidates"]; bs = r73["bootstrap"]
    evidence["saudi"] = {k: dict(eras={e: [R(v["cagr"], 4), R(v["dd"], 4)] for e, v in c[k]["equal_risk"].items()}, range={e: dict(g=bs[e][k]["cagr_range"], dd=bs[e][k]["dd_range"], p_growth=bs[e][k].get("p_growth"), p_dd=bs[e][k].get("p_dd"), p_ratio=bs[e][k].get("p_ratio")) for e in bs},
                                 trades=c[k]["trades"], win=c[k]["win"], avg=c[k]["avg"], worst=c[k]["worst"]) for k in ("LIVE", "L12D")}
    evidence["stress"] = dict(passed=r73["stress_passed"], of=len(r73["stress"]))
if w72 and w73:
    evidence["world"] = dict(market_eras=w73["counted"], ladder_beats=w72["vs_A0"]["L12D"]["share"], by_era=w72["vs_A0"]["L12D"]["by_era"], pace3_beats=w72["vs_A0"]["P(5,3)"]["share"], costs=w73["stress"]["costs"]["share"], late=w73["stress"]["late"]["share"],
                             tails=w73["tails"], edge=w72["edge_pooled"])
r78 = rj("r78", "r78_confirm.json"); w78 = rj("r78", "world78.json")
if r78:
    evidence["swing"] = dict(eras={k: {e: [R(v["cagr"], 5), R(v["dd"], 5)] for e, v in r78["equal"][k].items()} for k in ("LIVE", "LADDER", "SWING")}, cash={e: R(v, 5) for e, v in r78["cash"].items()}, verdict_live=r78["verdict_live"], verdict_ladder=r78["verdict_ladder"],
                             sound=r78["sound"], boot={e: {k: dict(g=r78["bootstrap"][e][k]["g"], dd=r78["bootstrap"][e][k]["dd"], vs_live=r78["bootstrap"][e][k].get("vs_LIVE"), vs_ladder=r78["bootstrap"][e][k].get("vs_LADDER")) for k in ("LIVE", "LADDER", "SWING")} for e in r78["bootstrap"]},
                             stats=r78["swing_stats"], stress={k: [R(v["cagr"], 4), R(v["dd"], 4), v["trades"]] for k, v in r78["stress"].items()}, stress_above=r78["stress_above_live"], stress_n=len(r78["stress"]), wf=r78["walk_forward"]["picks"],
                             world=(dict(vs_live_shape=w78["swing as tested"]["vsA0"], vs_ladder=w78["swing as tested"]["vsL12D"], costs=w78["swing, 0.8% costs"]["vsA0"], late=w78["swing, one session late"]["vsA0"], vs_hold=w78["swing vs hold"]) if w78 else None))
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
           weather=weather, episode=episode, past=past, live=BOOKS["live"], fable=BOOKS["fable"], swing=swing, scan=scan, scan_sum=scan_sum, edge=dict(rows=edge_rows, labels=ELAB, k=KSH), chart=dict(index=chart_index, chunks=int(max(chart_index.values()) + 1) if chart_index else 0, bars=NB), record_warn=RECW, replay=REPLAY, signals=signals, watch=watch, cards=CARDS, expect=expect, sizing=sizing, record=record, scorecard=scorecard, evidence=evidence, us=us)
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
              swing=dict(buys=[dict(sym=b["sym"], w=b["w"]) for b in SWB["buys"]], sells=[p["sym"] for p in SWB["due"]], held=[p["sym"] for p in SWB["held"]]), fable=dict(buys=[dict(sym=b["sym"], w=b["w"]) for b in BOOKS["fable"]["buys"]], sells=[p["sym"] for p in BOOKS["fable"]["due"]], held=[p["sym"] for p in BOOKS["fable"]["held"]]), signals=[s["sym"] for s in signals])
json.dump(clean(ledger), open(os.path.join(os.path.dirname(out), f"day_{OUT['asof']}.json"), "w"), allow_nan=False, separators=(",", ":"))
print(f"fable export: close {OUT['asof']} for {OUT['day']} | weather {state}, momentum {msv:+.2f}, market model {'positive' if pmv > 0 else 'negative'} | signals {len(signals)} | swing buys {len(SWB['buys'])}, sells {len(SWB['due'])}, in the zone {scan_sum['inzone']} | chart documents {OUT['chart']['chunks']} | live buys {len(BOOKS['live']['buys'])}, "
      f"ladder buys {len(BOOKS['fable']['buys'])} | {os.path.getsize(out) / 1024:.0f} KB -> {out}")
