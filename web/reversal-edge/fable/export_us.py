"""Fable US view (round 84): the 200 US stocks with the most options activity, beside the Saudi market in the Fable terminal.
Price-only (the US has no ML rank, market model or company-accounts check), on paper, for watching. It reads the US prices in the
work folder (fetch_us.py), the US formulas (us_model.json) and the round 84 results, and writes <work>/fable/us/: us_latest.json
(weather, paper book, scanner, record, evidence), us_market.json and us_chart_<n>.json (chart data, 10 stocks a document).
The book is the swing exactly as round 84 tested it with no history cut (research/r84/r84_nocut.py): the same prices, the same 183
stocks with 3+ years of prices, the same market momentum, idle money earning nothing. Following it day by day reproduces those trades.
Stocks with less history are shown (stretch Z, buy line, chart) and marked new; the book never buys them.
Usage: RE_WORK=<work folder> python3 export_us.py"""
import os, sys, json, datetime as dt, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, "..", "research"); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(RES, "r72"))
import wpanel, swingbook as SBk, swingrule as SR, swing as SWm, rebound as RBD, holdedge as HED; from engine import Book, perf
WORK = os.environ["RE_WORK"]; sys.path.insert(0, os.path.join(WORK, "r27")); from zbands import band_next
FOLDER = os.path.join(WORK, "edge26", "data", "us200"); LST = json.load(open(os.path.join(WORK, "edge26", "data", "us200_list.json")))
R = lambda x, n=4: None if x is None or not np.isfinite(x) else round(float(x), n); fdate = lambda t: str(pd.Timestamp(t).date())
rp = lambda x: None if x is None or not np.isfinite(x) else (round(float(x), 2) if abs(x) >= 20 else round(float(x), 3))
START = "2026-11-23"            # the US view began after this close: buys from the 2026-11-24 open on are its forward (paper) record
NYSE_HOL = ["2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
            "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18", "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24"]
BDU = pd.offsets.CustomBusinessDay(holidays=NYSE_HOL)            # New York sessions (future dates only: past ones come from the data)
# ---------------------------------------------------------------- prices: the tested panel and the shown panel share every session
PT = wpanel.panel(FOLDER, jump=np.inf); PD = wpanel.panel(FOLDER, min_rows=130, jump=np.inf)
assert PD["C"].index.equals(PT["C"].index), "the tested and the shown panels must have the same sessions"
cols = list(PD["C"].columns); tested = set(PT["C"].columns); N = len(cols)
EL = PT["elig"].reindex(columns=cols).fillna(False).astype(bool)                       # only the tested stocks trade, and only they make the market
B = Book(C=PD["C"], O=PD["O"], elig=EL, week="W-FRI"); d = B.dates; T_ = B.T; i = T_ - 1; last = d[i]
ELD = PD["elig"].values.astype(bool); Cl, Of, MS = B.Cl, B.Of, np.asarray(B.MS, float); S_ = SBk.prep(B); Zs, wx = S_["Z"], S_["wx"]
NM = LST.get("names", {}); RANK = {s: k + 1 for k, s in enumerate(LST["list"])}; nm = lambda j: (NM.get(cols[j]) or cols[j])
def highs():
    H = {}
    for s in cols:
        x = pd.read_csv(os.path.join(FOLDER, s + ".csv"), index_col=0, parse_dates=True); x = x[~x.index.duplicated(keep="last")].sort_index(); x = x[(x.close > 0) & x.adjclose.notna() & (x.adjclose > 0)]
        H[s] = x.high * x.adjclose / x.close
    H = pd.DataFrame(H).reindex(index=d, columns=cols); return np.fmax(H.values.astype(float), np.fmax(PD["O"].values, PD["C"].values)).astype(float)
# ---------------------------------------------------------------- the swing, as round 84 tested it (no cut, price-only, idle money earning nothing)
eqS, TRS, ORS = SBk.simulate(B, wplan=SR.WPLAN, slots=SR.SLOTS, per_day=SR.PER_DAY, base=SR.BASE, start="2001-01-01", cash=False, want_orders=True)
ER = {"2001-09": ("2001-01-01", "2009-12-31"), "2010-19": ("2010-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2001-26": ("2001-01-01", "2026-12-31")}
chk = json.load(open(os.path.join(RES, "r84", "r84_nocut.json")))["accounts"]["swing (round 78 rule, price-only)"]["trades"]
REPRO = []                                                                     # closed eras must match round 84; a later Yahoo revision of old prices is reported, not hidden
for e, (a, b) in ER.items():
    n_ = int(((d[TRS.d1.values] >= a) & (d[TRS.d1.values] <= b)).sum())
    if pd.Timestamp(b) < last and n_ != chk[e]["n"]: REPRO.append(f"{e}: {n_} trades now, {chk[e]['n']} when tested")
print("reproduces round 84 (closed eras):", "yes" if not REPRO else "NO: " + "; ".join(REPRO))
# ---------------------------------------------------------------- market weather (the equal-weight market of the tested stocks)
now = dt.datetime.now(ZoneInfo("America/New_York")); ny_today = pd.Timestamp(now.date()); is_sess = bool(BDU.is_on_offset(ny_today))
expected = ny_today if (is_sess and (now.hour, now.minute) >= (16, 30)) else BDU.rollback(ny_today - pd.Timedelta(days=1)); stale = bool(last < expected)
day = last + BDU; day_open = pd.Timestamp(day.date()).tz_localize("America/New_York") + pd.Timedelta(hours=9, minutes=30); opened = bool(pd.Timestamp(now) >= day_open)
sdate = lambda k: fdate(d[k]) if k < T_ else fdate(last + (k - i) * BDU)
GATE, DEEP = SWm.GATE, SWm.DEEP; i0 = int(np.searchsorted(d.values, np.datetime64("2001-01-01"))); msv = float(MS[i])
E, eid = B.episodes(first=i0); cur = E.iloc[-1]; in_ep = bool(i - int(cur["last"]) <= 20)
state = ("deep storm" if msv <= DEEP else "storm") if msv <= GATE else ("clearing" if in_ep else ("clouds" if msv <= GATE / 2 else "calm"))
idx = np.exp(np.nancumsum(B.mret.values)); shown = [j for j in range(N) if np.isfinite(Cl[i, j]) and np.isfinite(Zs[i, j])]; zl = Zs[i, shown]
weather = dict(state=state, ms=R(msv, 2), gate=GATE, deep=DEEP, n_liquid=int(EL.values[i].sum()), n_shown=len(shown), fear=R(float((zl <= -2).mean()), 3), below_line=int((zl <= SR.LINE).sum()),
               dd=R(idx[i] / np.nanmax(idx[max(0, i - 249):i + 1]) - 1, 4), chg1=R(idx[i] / idx[i - 1] - 1, 4), chg5=R(idx[i] / idx[i - 5] - 1, 4), chg20=R(idx[i] / idx[i - 20] - 1, 4),
               storm_since=(fdate(d[int(cur.start)]) if in_ep else None), hist=dict(d=[fdate(x) for x in d[-250:]], ms=[R(x, 2) for x in MS[-250:]], idx=[R(100 * x / idx[-250], 2) for x in idx[-250:]]))
# ---------------------------------------------------------------- the two indicators (formulas from the 23 foreign markets, no US data)
UM = json.load(open(os.path.join(HERE, "us_model.json"))); MR, MH = UM["rebound"], UM["hold"]
RF = RBD.inputs(B); REDGE = np.where((np.nan_to_num(RF["Z"], nan=9.) <= RBD.LINE) & np.isfinite(RF["MS"]) & ELD, RBD.edge(MR, RF), np.nan); RUNIT = RF["unit"]
def he_of(j, n):
    x = HED.read(MH, None, float(Zs[i, j]), msv, n, unit=RUNIT[i, j])
    if x is None: return None
    return dict(edge=R(x["edge"], 4), up=R(x["up"], 3), togo=R(x["togo"], 0), fur=R(x["fur"], 4), fur_bad=R(x["fur_bad"], 4), word=("weak" if x["edge"] < MH["zones"][0] else "strong" if x["edge"] >= MH["zones"][1] else "fair"))
# ---------------------------------------------------------------- the paper book (the tested book, replayed to this close) and its orders
inzL, ageL = SBk.zone_age(B, SR.LINE); BLn = band_next(PD["C"], SR.LINE).iloc[-1].values; SLn = band_next(PD["C"], SR.TARGET).iloc[-1].values     # tomorrow's close for Z = the buy line / the sell level
def spos(p):
    j = p["j"]; e = p["entry"]; k = int(i - p["d1"] + 1); SLn_ = SLn[j]
    return dict(sym=cols[j], name=nm(j)[:30], w=R(p["w"], 4), signal=fdate(d[p["i"]]), si=int(p["i"]), bought=fdate(d[p["d1"]]), entry=R(e, 3), last=R(Cl[i, j], 3), ret=R(Cl[i, j] / e - 1, 4), held=k, left=int(p["cap"] - k),
                z=R(Zs[i, j], 2), sellpx=R(SLn_, 3), latest=sdate(p["d1"] + p["cap"]), deep=bool(wx[p["i"]] == 3), fwd=bool(fdate(d[p["i"]]) >= START), he=he_of(j, k),
                why=({0: "the stretch is gone", 1: "40 sessions done"}.get(p["flag"]) if p["flag"] is not None else None))
sells = {j for j, _ in ORS["sells"]}; held = [spos(p) for p in ORS["held"] if p["j"] not in sells]; due = [spos(p) for p in ORS["held"] if p["j"] in sells]; bj = [b["j"] for b in ORS["buys"]]
buys = [dict(sym=cols[b["j"]], name=nm(b["j"])[:30], w=R(b["w"], 4), close=R(Cl[i, b["j"]], 3), z=R(Zs[i, b["j"]], 2), deep=bool(wx[i] == 3), latest=sdate(T_ + SR.CAP)) for b in ORS["buys"]]
heldj = {p["j"] for p in ORS["held"]}; full = len(held) + len(buys) >= SR.SLOTS
skipped = [dict(sym=cols[j], name=nm(j)[:30], why=("already held" if j in heldj else "no free slot" if full else "one buy a day: a more volatile signal was taken")) for j in ORS["cands"] if j not in bj]
cl = TRS.sort_values("ex").tail(40)
closed = [dict(sym=cols[r.j], name=nm(r.j)[:26], bought=fdate(d[r.d1]), sold=fdate(d[r.ex]), ret=R(r.ret - .004, 4), held=int(r.ex - r.d1), w=R(r.w, 4), why=("stretch gone" if r.why == 0 else "40 sessions"), fwd=bool(fdate(d[r.i]) >= START)) for r in cl.itertuples()][::-1]
book = dict(slots=SR.SLOTS, free=int(SR.SLOTS - len(held)), start=START, held=held, due=due, buys=buys, skipped=skipped, closed=closed, invested=R(sum(p["w"] for p in held) + sum(b["w"] for b in buys), 4),
            pnl=R(sum(p["w"] * p["ret"] for p in held + due), 5))
def st_(a, b):
    y = d[TRS.d1.values]; m = (y >= a) & (y <= b); x = TRS[m]; n = x.ret.values - .004
    return dict(n=int(len(x)), win=R((n > 0).mean(), 3), avg=R(n.mean()), worst=R(n.min()), held=R((x.ex - x.d1).mean(), 1)) if len(x) else dict(n=0)
netT = TRS.ret.values - .004
record = dict(eras={e: dict(g=R(perf(eqS, a, b)["cagr"], 4), dd=R(perf(eqS, a, b)["dd"], 4), **st_(a, b)) for e, (a, b) in ER.items()}, by_year={int(k): int(v) for k, v in pd.Series(d[TRS.d1.values].year).value_counts().sort_index().items()},
              expect=dict(n=int(len(netT)), avg=R(netT.mean()), win=R((netT > 0).mean(), 3), q=[R(np.quantile(netT, q)) for q in (.05, .25, .5, .75, .95)], held=[R(np.quantile((TRS.ex - TRS.d1).values, q), 0) for q in (.25, .5, .75)]))
# ---------------------------------------------------------------- the scanner: every stock with a price and a stretch Z at this close
s_due = {p["sym"] for p in due}; s_held = {p["sym"] for p in held}; s_buy = {b["sym"] for b in buys}; s_cand = {cols[j] for j in ORS["cands"]}
scan = []
for j in shown:
    s = cols[j]; c = Cl[i, j]; need = BLn[j] / c - 1 if np.isfinite(BLn[j]) else None; inz = bool(inzL[i, j]); e = REDGE[i, j]; u = RUNIT[i, j]
    st = "sell" if s in s_due else "held" if s in s_held else "buy" if s in s_buy else "cand" if s in s_cand else "zone" if inz else "near" if need is not None and need >= -.05 else ""
    scan.append(dict(sym=s, name=nm(j)[:26], opt=RANK.get(s), c=R(c, 3), chg=R(c / Cl[i - 1, j] - 1, 4) if np.isfinite(Cl[i - 1, j]) else None, z=R(Zs[i, j], 2), zp=R(Zs[i - 1, j], 2), line=R(BLn[j], 3), need=R(need, 4),
                     inz=inz, age=int(ageL[i, j]) if inz else None, cross=bool(inz and ageL[i, j] == 0), st=st, sellpx=R(SLn[j], 3), re=R(e, 4) if np.isfinite(e) else None, ru=R(u, 4) if np.isfinite(u) else None,
                     new=bool(s not in tested), dv=R((LST.get("dv_m") or {}).get(s), 0), oi=(LST.get("oi") or {}).get(s), ov=(LST.get("vol") or {}).get(s)))
scan.sort(key=lambda r: (r["z"] if r["z"] is not None else 9))
missing = sorted(set(LST["list"]) - {r["sym"] for r in scan}); why_missing = {}
for s in missing:
    if s not in cols: why_missing[s] = "too little price history for a stretch Z"
    else: j = cols.index(s); k = int(np.where(np.isfinite(Cl[:, j]))[0].max()); why_missing[s] = f"no price from Yahoo since {fdate(d[k])}"
scan_sum = dict(n=len(scan), inzone=int(sum(r["inz"] for r in scan)), crossed=int(sum(r["cross"] for r in scan)), cands=len(s_cand), near=int(sum(r["st"] == "near" for r in scan)), window=bool(wx[i] in SR.WPLAN),
                tested=int(sum(not r["new"] for r in scan)), new=int(sum(r["new"] for r in scan)), missing=[dict(sym=s, why=why_missing[s]) for s in missing])
# ---------------------------------------------------------------- chart data: the last NB sessions of every shown stock, 10 stocks a document
NB = 380; a0 = T_ - NB; Hh = highs(); Ll = PD["L"].values.astype(float); Oo = PD["O"].values.astype(float)
BLs = band_next(PD["C"], SR.LINE).shift(1).values; SLs = band_next(PD["C"], SR.TARGET).shift(1).values; CIN = SWm.cross_in(Zs, SR.LINE)
bought = {(int(r.i), int(r.j)) for r in TRS.itertuples()} | {(p["i"], p["j"]) for p in ORS["held"]}
def bits(t, j):
    b = 0
    if wx[t] not in SR.WPLAN: b |= 1
    if cols[j] not in tested: b |= 32
    elif not EL.values[t, j]: b |= 16
    return b
def he_path(j, d1, end):
    out = []
    for t in range(max(d1, a0), min(end, T_)):
        if not (np.isfinite(Zs[t, j]) and np.isfinite(MS[t])): continue
        x = HED.read(MH, None, float(Zs[t, j]), float(MS[t]), t - d1 + 1)
        if x is not None: out += [int(t - a0), round(100 * x["edge"], 1)]
    return out
def chart_doc(j):
    sl = slice(a0, T_); tr = []; hv = []
    for r in TRS[(TRS.j == j) & (TRS.ex > a0)].itertuples():
        tr.append([int(r.d1 - a0), int(r.ex - a0), rp(Of[r.d1, j]), rp(Of[r.ex, j]), R(r.ret - .004, 4), R(r.w, 4), int(r.why), int(fdate(d[r.i]) >= START)]); hv += he_path(j, int(r.d1), int(r.ex))
    for p in ORS["held"]:
        if p["j"] == j: tr.append([int(p["d1"] - a0), None, rp(p["entry"]), None, R(Cl[i, j] / p["entry"] - 1, 4), R(p["w"], 4), -1, int(fdate(d[p["i"]]) >= START)]); hv += he_path(j, int(p["d1"]), T_)
    xs = [[int(t - a0), 0 if (t, j) in bought else (bits(t, j) or -1)] for t in range(a0, T_) if CIN[t, j]]
    return dict(o=[rp(x) for x in Oo[sl, j]], h=[rp(x) for x in Hh[sl, j]], l=[rp(x) for x in Ll[sl, j]], c=[rp(x) for x in Cl[sl, j]], z=[R(x, 2) for x in Zs[sl, j]], bl=[rp(x) for x in BLs[sl, j]], sl=[rp(x) for x in SLs[sl, j]],
                nbl=rp(BLn[j]), nsl=rp(SLn[j]), tr=[v for r in tr for v in r], x=[v for r in xs for v in r], ev=[v for t in range(a0, T_) if np.isfinite(REDGE[t, j]) for v in (int(t - a0), round(float(100 * REDGE[t, j]), 1))],
                hv=hv, name=nm(j)[:34], sec=("new: under 3 years of prices" if cols[j] not in tested else ""))
outdir = os.path.join(WORK, "fable", "us"); os.makedirs(outdir, exist_ok=True)
for f in os.listdir(outdir):
    if f.startswith("us_chart_"): os.remove(os.path.join(outdir, f))
cj = sorted([j for j in range(N) if np.isfinite(Cl[a0:, j]).any()], key=lambda j: cols[j]); CH = 10; chart_index = {}
for n_ in range(0, len(cj), CH):
    part = cj[n_:n_ + CH]; json.dump(dict(n=n_ // CH, asof=fdate(last), stocks={cols[j]: chart_doc(j) for j in part}), open(os.path.join(outdir, f"us_chart_{n_ // CH}.json"), "w"), separators=(",", ":"), allow_nan=False)
    for j in part: chart_index[cols[j]] = n_ // CH
json.dump(dict(asof=fdate(last), d=[int(x.strftime("%Y%m%d")) for x in d[a0:]], ms=[R(x, 2) for x in MS[a0:]], wx=[int(x) for x in wx[a0:]], idx=[R(100 * x / idx[a0], 2) for x in idx[a0:]]),
          open(os.path.join(outdir, "us_market.json"), "w"), separators=(",", ":"), allow_nan=False)
# ---------------------------------------------------------------- evidence (round 84) and the indicator tables
def ev84(f):
    x = json.load(open(os.path.join(RES, "r84", f))); A = x["accounts"]; K = {"swing": "swing (round 78 rule, price-only)", "a0": "live plan's shape (A0: 5 x 5%, hold 40)", "basket": "the 200 held, equal weight"}
    acc = {k: {e: [R(v["cagr"], 5), R(v["dd"], 5)] for e, v in A[n]["perf"].items()} for k, n in K.items()}
    tr = {k: {e: dict(n=v["n"], py=R(v["per_year"], 1), win=R(v["win"], 3), avg=R(v["avg"], 4), held=R(v["held"], 0), worst=R(v["worst"], 4)) for e, v in A[n]["trades"].items()} for k, n in K.items() if A[n]["trades"]}
    ind = {k: dict(n=v["n"], top=R(v["separation"][3], 5), bottom=R(v["separation"][4], 5), lo=R(v["separation"][1], 5), hi=R(v["separation"][2], 5), corr=R(v["beats"]["odds"], 3), corr_ms=R(v["beats"]["momentum"]["corr"], 3),
                    lead_p5=R(v["beats"]["momentum"]["lead_p5"], 3)) for k, v in x["indicators"].items()}
    return dict(stocks=x["stocks"], acc=acc, trades=tr, ind=ind)
cx = json.load(open(os.path.join(RES, "r84", "r84_context.json")))
evidence = dict(nocut=ev84("r84_nocut.json"), planned=ev84("r84.json"), context={e: {k: R(v, 4) for k, v in c.items()} for e, c in cx["context"].items()}, cut=cx["cut"], verdict="DESCRIPTIVE at best")
rnd = lambda v, k=4: [R(x, k) for x in v]
rebound = dict(line=RBD.LINE, horizons=list(RBD.HORIZONS), band_edges=rnd(MR["band_edges"], 5), zones=rnd(MR["zones"], 4), saudi=False, gate=0.0, cases_world=int(MR["cases"]), markets=int(MR["markets"]), cases_saudi=0,
               bands=[dict(edge=R(b["edge"], 4), gain=R(b["gain"], 4), win=R(b["win"], 3), days=R(b["days"], 0), dz=R(b["dipz_med"], 3), dzb=R(b["dipz_bad"], 3), cone={q: rnd(v, 3) for q, v in b["cone"].items()}, n=int(b["n"])) for b in MR["bands"]],
               raw={k: (R(v, 5) if not isinstance(v, dict) else {a: rnd(b, 2) for a, b in v.items()}) for k, v in MR["raw"].items()}, stretched=int(np.isfinite(REDGE[i]).sum()), strong=int((REDGE[i] >= MR["zones"][1]).sum()), against=int((REDGE[i] < 0).sum()))
hold = dict(zones=rnd(MH["zones"], 4), cases_world=int(MH["cases"]), markets=int(MH["markets"]), bands=[dict(edge=R(b["edge"], 4), rest=R(b["rest"], 4), up=R(b["up"], 3), togo=R(b["togo"], 0), fz=R(b["furz_med"], 3), fzb=R(b["furz_bad"], 3)) for b in MH["bands"]])
OUT = dict(v=1, market="us", asof=fdate(last), day=fdate(day), opened=opened, repro=REPRO, made=dt.datetime.now(ZoneInfo("Asia/Riyadh")).strftime("%Y-%m-%d %H:%M") + " Riyadh", stale=stale,
           list=dict(date=LST["date"], n=len(LST["list"]), rule=LST["rule"]), weather=weather, swing=dict(rule=dict(line=SR.LINE, target=SR.TARGET, cap=SR.CAP, slots=SR.SLOTS, per_day=SR.PER_DAY, size=R(SR.BASE, 4), deep_size=R(SR.BASE * SR.DEEP_MULT, 4), start=START, status="paper"),
           book=book, record=record), scan=scan, scan_sum=scan_sum, rebound=rebound, hold=hold, chart=dict(index=chart_index, chunks=int(max(chart_index.values()) + 1), bars=NB), evidence=evidence)
def clean(x):
    if isinstance(x, dict): return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [clean(v) for v in x]
    if isinstance(x, (np.floating, float)): return None if not np.isfinite(x) else float(x)
    if isinstance(x, np.integer): return int(x)
    if isinstance(x, np.bool_): return bool(x)
    return x
out = os.path.join(outdir, "us_latest.json"); json.dump(clean(OUT), open(out, "w"), allow_nan=False, separators=(",", ":"))
print(f"fable US export: close {OUT['asof']} for {OUT['day']}{' (that open has passed)' if opened else ''} | weather {state}, momentum {msv:+.2f} | book: buys {len(buys)}, sells {len(due)}, held {len(held)} | "
      f"in the zone {scan_sum['inzone']}, near {scan_sum['near']} | shown {len(scan)} ({scan_sum['new']} new), missing {len(missing)}: {', '.join(f'{s} ({why_missing[s]})' for s in missing)} | "
      f"chart documents {OUT['chart']['chunks']} (largest {max(os.path.getsize(os.path.join(outdir, f)) for f in os.listdir(outdir) if f.startswith('us_chart_')) / 1024:.0f} KB) | {os.path.getsize(out) / 1024:.0f} KB -> {out}")
