"""Round 68 live fix: the daily list and the export follow the plan book (planbook.py = the tested rule replayed), and use the
walk-forward ranker / market model the tests used. Fixes: a repeat signal in a held stock was listed as a new buy; no slot count;
the blocked list ignored weekly paper trades and the one-trade-per-stock chain; fresh-fit model values differed from the tested ones."""
import os, json
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def patch(path, pairs):
    s = open(path).read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, old[:90], s.count(old)); s = s.replace(old, new)
    open(path, "w").write(s)
def cut(path, a, b, new):
    """replace everything from marker a (inclusive) up to marker b (exclusive)"""
    s = open(path).read(); assert s.count(a) == 1 and s.count(b) == 1, (path, a[:60], s.count(a), b[:60], s.count(b))
    i, j = s.index(a), s.index(b); assert i < j; open(path, "w").write(s[:i] + new + s[j:])
# ---------------------------------------------------------------- settings
patch(f"{S}/daily/opt7.py", [
    ('"mr_size": 0.05, "plan": ""}', '"mr_size": 0.05, "plan": "", "plan_start": ""}'),
    ('    if isinstance(f.get("plan"), str): d["plan"] = f["plan"]\n',
     '    if isinstance(f.get("plan"), str): d["plan"] = f["plan"]\n'
     '    if isinstance(f.get("plan_start"), str): d["plan_start"] = f["plan_start"]   # first signal date of the plan account (round 68)\n')])
st = json.load(open(f"{S}/daily/settings.json")); st["plan_start"] = "2026-11-09"; json.dump(st, open(f"{S}/daily/settings.json", "w"))
# ---------------------------------------------------------------- top3.py
T3 = f"{S}/daily/top3.py"
patch(T3, [("(ML leaders / breakouts) is printed after them for reference only; idle money in a SAR money-market fund. settings.json \"plan\": \"A\".\n",
            "(ML leaders / breakouts) is printed after them for reference only; idle money in a SAR money-market fund. settings.json \"plan\": \"A\".\n"
            "Change 2026-11-10 (round 68): the Market returned section comes from planbook.py, which replays the tested rule to the last close:\n"
            "held positions and free slots (from settings.json plan_start), sells due, buys in tested order up to the free slots, and the reason\n"
            "for every skipped signal (already held / no free slot / paper trade from before the turn). ML ranks and the market model in the\n"
            "export are the walk-forward values the tests used.\n")])
cut(T3, "    zs_all = [j for j, t in ranked(i, pct, pmv, msv, wk_ok) if t == 1]", "    FA = accounts(); half = pmv <= 0",
    "    import planbook as PB                                                            # round 68: the tested rule replayed to this close\n"
    "    assert PB.T_ == T_ and list(PB.cols) == list(cols) and PB.dates[-1] == last, 'plan book and list use different data'\n"
    "    PLAN = SET[\"plan\"]; mrsz = f\"{100 * SET['mr_size']:.0f}%\"\n"
    "    ST = PB.state(loss=True, week_complete=bool(wk_ok), start=SET[\"plan_start\"] or None)\n"
    "    cand = [(j, t) for j, t in cand if not (t == 1 and j in ST[\"blocked\"])]; top = cand[:3]   # a signal while the stock's paper trade is open is not a new trade\n")
cut(T3, "    if mron:   # ---- Market returned signals: their own list", "    MRB = L\n",
    "    if mron:   # ---- Market returned signals: the plan book (planbook.py)\n"
    "        fdt = lambda x: pd.Timestamp(x).strftime(\"%a %d %b\") if x else \"-\"\n"
    "        nmj = lambda j: f\"{cols[j]} {nm.get(cols[j], '')[:18]}\".strip()\n"
    "        L += [\"\", \"**Market returned signals** (Z score signals taken only after the market turns; at most 5 positions, most volatile first)\", \"\",\n"
    "              f\"Market index (equal-weight liquid Saudi stocks): {pc(O7['bounce'])} above its 20-day low, {pc(O7['dd'], 0)} from its 1-year high -> \"\n"
    "              + (f\"turn window **open** since {fdt(O7.get('window_start'))}, until about {fdt(O7.get('window_end'))}.\" if O7[\"gate\"] else\n"
    "                 \"turn window **closed**: no market-returned buys (it opens on a close 4% above the 20-day low after a fall of 10% or more).\")]\n"
    "        keep, due_p = ST[\"keep\"], ST[\"due\"]\n"
    "        L += [\"\", f\"Plan book: **{len(keep)} of {PB.SLOTS} slots in use**, {ST['free']} free\" + (f\" (your plan started on {fdt(SET['plan_start'])})\" if SET[\"plan_start\"] else \"\") + \".\"]\n"
    "        if len(keep):\n"
    "            L += [\"\", \"| Held | Bought at the open of | Entry | Last close | So far | Sell at the open of |\", \"|---|---|---|---|---|---|\"]\n"
    "            for r in keep.sort_values(\"d1\").itertuples():\n"
    "                e = Of[r.d1, r.j]; L.append(f\"| **{cols[r.j]}** {nm.get(cols[r.j], '')[:24]} | {fmt_d(dates[r.d1])} | {e:.2f} | {Cl[i, r.j]:.2f} | {pc(Cl[i, r.j] / e - 1)} | {fmt_d(day + (r.xo - T_) * BD)} |\")\n"
    "        if len(due_p): L += [\"\", \"**SELL at today's open** (40 sessions done): \" + \"; \".join(f\"**{cols[r.j]}** {nm.get(cols[r.j], '')[:18]} ({pc(Cl[i, r.j] / Of[r.d1, r.j] - 1)} so far)\" for r in due_p.itertuples()) + \".\"]\n"
    "        buys = [j for j, a in ST[\"new\"] if a == \"buy\"]; nos = [j for j, a in ST[\"new\"] if a == \"noslot\"]; wait = [j for j, a in ST[\"new\"] if a == \"wait\"]\n"
    "        if buys:\n"
    "            L += [\"\", \"**BUY at today's open:**\", \"\", \"| # | Stock | Setup | Last close | Plan | Latest accounts |\", \"|---|---|---|---|---|---|\"]\n"
    "            for n, j in enumerate(buys, 1):\n"
    "                s_ = cols[j]; wk_ = not ZFIRST[i, j]\n"
    "                setup = (f\"Market returned (weekly candles): weekly stretch Z {ZWV[i, j]:.2f}\" if wk_ else f\"Market returned: stretch Z {ZC.iloc[i, j]:.2f}\") + f\", ML {100 * PB.PCTv[i, j]:.0f}%\" + _vt(i, j)\n"
    "                L.append(f\"| {n} | **{s_}** {nm.get(s_, s_)[:28]} ({industry(s_)}) | {setup} | {Cl[i, j]:.2f} | {mrsz} of the account. Hold 40 sessions (sell at the open around {fmt_d(day + 40 * BD)}). No stop. | {FA.get(s_, '—')} |\")\n"
    "                log_rows.append(dict(signal=str(last.date()), sym=s_, tier=4, close=round(float(Cl[i, j]), 4), atr=round(float(A[i, j]), 4), ml=round(float(PB.PCTv[i, j]), 3), pm=round(pmv, 5)))\n"
    "        elif ST[\"gate\"]: L += [\"\", \"No new market-returned signal at this close.\"]\n"
    "        if nos: L += [\"\", f\"Not bought, no free slot ({PB.SLOTS} positions is the tested limit): \" + \", \".join(nmj(j) for j in nos) + \".\"]\n"
    "        if wait: L += [\"\", \"Z score signals at this close, not bought (the market has not turned; each stays blocked for 40 sessions): \" + \", \".join(nmj(j) for j in wait) + \".\"]\n"
    "        for kind, txt in ((\"held\", \"Signal again in a stock you hold: keep holding, no second buy (the tested rule ignores it)\"),\n"
    "                          (\"repeat\", \"Skipped, signalled after the turn before and was not bought then (no second signal within its 40 sessions)\"),\n"
    "                          (\"blocked\", \"Skipped, its paper trade started before the turn (blocked until that paper trade ends)\")):\n"
    "            xs = [(j, s0) for j, k, s0 in ST[\"rep\"] if k == kind]\n"
    "            if xs: L += [\"\", txt + \": \" + \", \".join(f\"{nmj(j)} (signal {fmt_d(dates[s0])})\" for j, s0 in xs) + \".\"]\n"
    "        if PLAN == \"A\" and not buys: L += [\"\", \"**Nothing to buy in your plan at this close.**\" + (\"\" if len(keep) else \" Idle money stays in the money-market fund.\")]\n"
    "        L += [\"\", \"Plan record as traded (5 slots, most volatile first, round 68): 2013-19 26 trades, 73% winners, +16.8% per trade, worst -12.6%; \"\n"
    "              \"2020-26 25 trades, 84%, +9.4%, worst -12.3%. About 4 trades a year and none in 5 of the 14 years; it misses fast V-shaped rebounds \"\n"
    "              \"(April 2025) and lost in late 2015.\"]\n")
patch(T3, [("        if PLAN == \"A\" and r.signal >= \"2026-11-09\" and int(r.tier) != 4 and not (SET[\"zscore\"] and int(r.tier) == 1): continue   # plan A: only its own picks from its start\n",
            "        if int(r.tier) == 4 and (not SET[\"plan_start\"] or r.signal >= SET[\"plan_start\"]): continue      # Market returned positions: the plan book above reports them\n"
            "        if PLAN == \"A\" and SET[\"plan_start\"] and r.signal >= SET[\"plan_start\"] and not (SET[\"zscore\"] and int(r.tier) == 1): continue   # not in the plan\n")])
# ---------------------------------------------------------------- final27.py
F27 = f"{S}/r27/final27.py"
patch(F27, [
    ("if PICK == \"C\":\n    pick = _Ens([lgb.LGBMRegressor(**_LGB).fit(",
     "if PICK == \"C\":\n  def _fitC():\n    return _Ens([lgb.LGBMRegressor(**_LGB).fit("),
    ("pm = float(mkt.predict(M.loc[[last], FE[\"market\"]])[0]); hist = pd.Series(mkt.predict(M.loc[dates[-60]:, FE[\"market\"]]), M.loc[dates[-60]:].index)\n",
     "pm = float(mkt.predict(M.loc[[last], FE[\"market\"]])[0]); hist = pd.Series(mkt.predict(M.loc[dates[-60]:, FE[\"market\"]]), M.loc[dates[-60]:].index)\n"
     "_pmw = pd.read_parquet(\"pm27.parquet\").pm_old.dropna()                      # round 68: the walk-forward market model the tests used (mkt27.py, refit each January)\n"
     "if len(_pmw) and pd.Timestamp(_pmw.index[-1]) == pd.Timestamp(last): pm_fresh = pm; pm = float(_pmw.iloc[-1]); hist = _pmw.iloc[-60:]\n"),
    ("today = D[D.date == last].copy(); today[\"score\"] = pick.predict(today[FEATS]); today[\"pct\"] = today.score.rank(pct=True)\n",
     "today = D[D.date == last].copy(); _wfs = None\n"
     "if PICK == \"C\" and os.path.exists(\"preds/C.parquet\"):                         # round 68: the walk-forward ranker the tests used (wfC.py, quarterly refits)\n"
     "    _w = pd.read_parquet(\"preds/C.parquet\"); _w = _w[_w.date == pd.Timestamp(last)].set_index(\"sym\").pred\n"
     "    if len(_w) and today.sym.isin(_w.index).all(): _wfs = today.sym.map(_w).values\n"
     "if _wfs is None and PICK == \"C\": pick = _fitC(); print(\"walk-forward ranks missing for the last date: fresh fit used\")\n"
     "today[\"score\"] = _wfs if _wfs is not None else pick.predict(today[FEATS]); today[\"pct\"] = today.score.rank(pct=True)\n")])
s = open(F27).read(); a = "# live Z-swing trades (round 28): qualifying first touches in the last 40 sessions"; b = "zwx = []\n"; assert s.count(a) == 1 and s.count(b) == 1
i, j = s.index(a), s.index(b)
new = '''# round 68: the paper (shadow) book and the plan book come from daily/planbook.py = the tested rule replayed to this close
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../daily")); from opt7 import market_turn, status as o7status, settings as o7settings
    import planbook as PB
    from core import P as PP
    assert pd.Timestamp(PB.dates[-1]) == pd.Timestamp(last), (PB.dates[-1], last)
    _set = o7settings(); ST = PB.state(loss=True, week_complete=bool(wk_done), start=_set["plan_start"] or None); _T = PB.T_; _i = _T - 1; _ds = PB.dates; _c = PB.cols
    _sh = ST["SH"]; _op = _sh[(_sh.ex >= _T) & (_sh.i < _i)]; _held = set(int(x) for x in ST["keep"].j) | set(int(x) for x in ST["due"].j)
    zact = [dict(sym=_c[r.j], signal=str(_ds[r.i].date()), entry=round(float(PB.Of[r.d1, r.j]), 3), ret=round(float(PB.Cl[_i, r.j] / PB.Of[r.d1, r.j] - 1), 4),
                 left=int(r.ex - _T + 1), ml=round(float(PB.PCTv[r.i, r.j]), 3), g=bool(PB.GATE[r.i]), plan=int(r.j) in _held, **({} if PB.ZFIRST[r.i, r.j] else {"tf": "W"}))
            for r in _op.sort_values(["i", "j"]).itertuples()]
    MT = PB.MT; O7B = sorted(_c[j] for j, v in ST["blocked"].items() if not v[1])          # paper trade opened before the turn: blocked until it ends
    _pos = lambda r: dict(sym=_c[r.j], signal=str(_ds[r.i].date()), bought=str(_ds[r.d1].date()), entry=round(float(PB.Of[r.d1, r.j]), 3), ret=round(float(PB.Cl[_i, r.j] / PB.Of[r.d1, r.j] - 1), 4), left=int(r.xo - _T))
    BOOK = dict(slots=PB.SLOTS, free=int(ST["free"]), start=_set["plan_start"], held=[_pos(r) for r in ST["keep"].sort_values("d1").itertuples()], due=[_pos(r) for r in ST["due"].itertuples()],
                today=[dict(sym=_c[j], act=a) for j, a in ST["new"]] + [dict(sym=_c[j], act=a, since=str(_ds[s0].date())) for j, a, s0 in ST["rep"]])
    PA = {x["sym"]: x for x in BOOK["today"]}
    _sp = MT.iloc[-90:]; _b0 = float(_sp.idx.dropna().iloc[0])
    OPT7 = dict(on=bool(_set["market_returned"]), zscore=bool(_set["zscore"]), mr_size=_set["mr_size"], plan=_set["plan"], blocked=O7B, book=BOOK, **o7status(MT),
                spark=dict(dates=[str(d_.date()) for d_ in _sp.index], idx=[None if not np.isfinite(v_) else round(100 * v_ / _b0, 2) for v_ in _sp.idx],
                           trig=[None if not np.isfinite(v_) else round(104 * v_ / _b0, 2) for v_ in _sp.low20], gate=[bool(v_) for v_ in _sp.gate]))
except Exception as ex:
    print("plan book failed:", ex); OPT7 = None; O7B = []; zact = []; PA = {}
    def o7settings(): return {"zscore_order": "ml"}
'''
s = s[:i] + new + s[j:]
a = "try:   # weekly Z-swing trades still inside their 40 sessions"; b = "# scanner table (v22)"; assert s.count(a) == 1 and s.count(b) == 1
i, j = s.index(a), s.index(b); s = s[:i] + s[j:]                                      # weekly paper trades are in the plan book's shadow book now
old = "            zscan[-1].update(vol=round(float(VOLL[s_]), 4), vr=round(float(VRL.get(s_, np.nan)), 3) if np.isfinite(VRL.get(s_, np.nan)) else None)"
assert s.count(old) == 1; s = s.replace(old, old + "\n        if s_ in PA: zscan[-1].update(pa=PA[s_][\"act\"], ps=PA[s_].get(\"since\"))   # round 68: the plan book's decision for this signal")
open(F27, "w").write(s); print("patched")
