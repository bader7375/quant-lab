"""Plan Z go-live (the user's choice 2026-11-10: "Let's go back to previous strategy stretch with ML"): the Z score rule is the plan again
(5 positions of 5%, most volatile first, hold 40 sessions, no stop), now reported through the plan book like plan A was."""
import os, json
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def patch(path, pairs):
    s = open(path).read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, old[:90], s.count(old)); s = s.replace(old, new)
    open(path, "w").write(s)
def cut(path, a, b, new):
    s = open(path).read(); assert s.count(a) == 1 and s.count(b) == 1, (path, a[:60], s.count(a), b[:60], s.count(b))
    i, j = s.index(a), s.index(b); assert i < j; open(path, "w").write(s[:i] + new + s[j:])
patch(f"{S}/daily/opt7.py", [
    ('"mr_size": 0.05, "plan": "", "plan_start": ""}', '"mr_size": 0.05, "z_size": 0.05, "plan": "", "plan_start": ""}'),
    ('    if isinstance(f.get("plan"), str): d["plan"] = f["plan"]\n',
     '    if isinstance(f.get("z_size"), (int, float)) and 0 < f["z_size"] <= .2: d["z_size"] = float(f["z_size"])   # plan Z position size (round 70)\n'
     '    if isinstance(f.get("plan"), str): d["plan"] = f["plan"]\n')])
json.dump({"zscore": True, "market_returned": True, "zscore_order": "volatility", "mr_size": 0.10, "z_size": 0.05, "plan": "Z", "plan_start": "2026-11-10"}, open(f"{S}/daily/settings.json", "w"))
T3 = f"{S}/daily/top3.py"
patch(T3, [
    ("for every skipped signal (already held / no free slot / paper trade from before the turn). ML ranks and the market model in the\nexport are the walk-forward values the tests used.\n",
     "for every skipped signal (already held / no free slot / paper trade from before the turn). ML ranks and the market model in the\nexport are the walk-forward values the tests used.\n"
     "Change 2026-11-10 (the user: \"Let's go back to previous strategy stretch with ML\"): plan Z. The Z score rule is the plan again (settings.json\n"
     "plan \"Z\", z_size 0.05, plan_start 2026-11-10): 5 positions, most volatile first, hold 40 sessions, no stop; its section comes from the plan book\n"
     "(kind \"Z\": every paper trade, not only those inside a turn window); the turn window is shown as context; ML leaders / breakouts for reference.\n"),
    ("    msv = float(MS[i]); cand = ranked(i, pct, pmv, msv, wk_ok, None if SET[\"zscore\"] else np.zeros(len(cols), bool)); top = cand[:3]\n",
     "    PLAN = SET[\"plan\"]; KIND = \"Z\" if PLAN == \"Z\" else \"A\"\n"
     "    msv = float(MS[i]); cand = ranked(i, pct, pmv, msv, wk_ok, None if (SET[\"zscore\"] and PLAN not in (\"A\", \"Z\")) else np.zeros(len(cols), bool)); top = cand[:3]   # in a plan the book section owns the Z score signals\n"),
    ("    PLAN = SET[\"plan\"]; mrsz = f\"{100 * SET['mr_size']:.0f}%\"\n    ST = PB.state(loss=True, week_complete=bool(wk_ok), start=SET[\"plan_start\"] or None)\n",
     "    psz = SET[\"z_size\"] if KIND == \"Z\" else SET[\"mr_size\"]; mrsz = f\"{100 * psz:.0f}%\"; lab = \"Z score\" if KIND == \"Z\" else \"Market returned\"\n"
     "    ST = PB.state(loss=True, week_complete=bool(wk_ok), start=SET[\"plan_start\"] or None, kind=KIND)\n"),
    ("{'plan A list' if PLAN == 'A' else 'top 3'}", "{dict(A='plan A list', Z='Z score list').get(PLAN, 'top 3')}"),
    ("    elif not SET[\"zscore\"]: L += [\"\", \"Z score signals are switched off (settings.json): the list below has no Z score picks.\"]\n",
     "    elif PLAN == \"Z\":\n"
     "        L += [\"\", f\"**Your plan: Z score** (stretch Z with ML): buy the **Z score** signals, **{mrsz} of the account each**, at most 5 at once (most volatile first), \"\n"
     "                  \"hold 40 sessions, no stop. Keep idle money in a SAR money-market fund. ML leaders and breakouts are shown at the end for reference only. \"\n"
     "                  \"Tested on the whole account (idle money at T-bill interest, round 70): 2013-19 +3.2% a year, worst drawdown 6.1%; 2020-26 +4.9%, 4.9%.\"]\n"
     "    elif not SET[\"zscore\"]: L += [\"\", \"Z score signals are switched off (settings.json): the list below has no Z score picks.\"]\n")])
cut(T3, "    if mron:   # ---- Market returned signals: the plan book (planbook.py)", "    MRB = L\n",
    "    if mron or KIND == \"Z\":   # ---- the plan book (planbook.py): Market returned (plan A) or Z score (plan Z)\n"
    "        fdt = lambda x: pd.Timestamp(x).strftime(\"%a %d %b\") if x else \"-\"\n"
    "        nmj = lambda j: f\"{cols[j]} {nm.get(cols[j], '')[:18]}\".strip()\n"
    "        turn = \"\" if O7 is None else (f\"Market index (equal-weight liquid Saudi stocks): {pc(O7['bounce'])} above its 20-day low, {pc(O7['dd'], 0)} from its 1-year high -> \"\n"
    "              + (f\"turn window **open** since {fdt(O7.get('window_start'))}, until about {fdt(O7.get('window_end'))}.\" if O7[\"gate\"] else\n"
    "                 \"turn window **closed**\" + (\": no market-returned buys\" if KIND == \"A\" else \"\") + \" (it opens on a close 4% above the 20-day low after a fall of 10% or more).\"))\n"
    "        if KIND == \"A\": L += [\"\", \"**Market returned signals** (Z score signals taken only after the market turns; at most 5 positions, most volatile first)\", \"\", turn]\n"
    "        else: L += [\"\", \"**Z score signals** (first close at stretch Z -2.62 daily / -2.08 weekly, ML rank 50%+, market model positive, market momentum -1.18 or lower, \"\n"
    "                    \"profitable company; at most 5 positions, most volatile first)\"] + ([\"\", turn + \" For the Z score plan this is context only.\"] if turn else [])\n"
    "        keep, due_p = ST[\"keep\"], ST[\"due\"]; tierk = 1 if KIND == \"Z\" else 4\n"
    "        L += [\"\", f\"Plan book: **{len(keep)} of {PB.SLOTS} slots in use**, {ST['free']} free\" + (f\" (your plan started on {fdt(SET['plan_start'])})\" if SET[\"plan_start\"] else \"\") + \".\"]\n"
    "        if len(keep):\n"
    "            L += [\"\", \"| Held | Bought at the open of | Entry | Last close | So far | Sell at the open of |\", \"|---|---|---|---|---|---|\"]\n"
    "            for r in keep.sort_values(\"d1\").itertuples():\n"
    "                e = Of[r.d1, r.j]; L.append(f\"| **{cols[r.j]}** {nm.get(cols[r.j], '')[:24]} | {fmt_d(dates[r.d1])} | {e:.2f} | {Cl[i, r.j]:.2f} | {pc(Cl[i, r.j] / e - 1)} | {fmt_d(day + (r.xo - T_) * BD)} |\")\n"
    "        if len(due_p): L += [\"\", \"**SELL at today's open** (40 sessions done): \" + \"; \".join(f\"**{cols[r.j]}** {nm.get(cols[r.j], '')[:18]} ({pc(Cl[i, r.j] / Of[r.d1, r.j] - 1)} so far)\" for r in due_p.itertuples()) + \".\"]\n"
    "        buys = [j for j, a in ST[\"new\"] if a == \"buy\"]; nos = [j for j, a in ST[\"new\"] if a == \"noslot\"]; wait = [j for j, a in ST[\"new\"] if a == \"wait\"]; held_back = [j for j, a in ST[\"new\"] if a == \"rule\"]\n"
    "        if buys:\n"
    "            L += [\"\", \"**BUY at today's open:**\", \"\", \"| # | Stock | Setup | Last close | Plan | Latest accounts |\", \"|---|---|---|---|---|---|\"]\n"
    "            for n, j in enumerate(buys, 1):\n"
    "                s_ = cols[j]; wk_ = not ZFIRST[i, j]\n"
    "                setup = (f\"{lab} (weekly candles): weekly stretch Z {ZWV[i, j]:.2f}\" if wk_ else f\"{lab}: stretch Z {ZC.iloc[i, j]:.2f}\") + f\", ML {100 * PB.PCTv[i, j]:.0f}%\" + _vt(i, j)\n"
    "                if KIND == \"Z\": setup += \"; after the market turn\" if ST[\"turn\"] else \"; before the market turn\"\n"
    "                L.append(f\"| {n} | **{s_}** {nm.get(s_, s_)[:28]} ({industry(s_)}) | {setup} | {Cl[i, j]:.2f} | {mrsz} of the account. Hold 40 sessions (sell at the open around {fmt_d(day + 40 * BD)}). No stop. | {FA.get(s_, '—')} |\")\n"
    "                log_rows.append(dict(signal=str(last.date()), sym=s_, tier=tierk, close=round(float(Cl[i, j]), 4), atr=round(float(A[i, j]), 4), ml=round(float(PB.PCTv[i, j]), 3), pm=round(pmv, 5)))\n"
    "        elif ST[\"gate\"]: L += [\"\", f\"No new {'Z score' if KIND == 'Z' else 'market-returned'} signal at this close.\"]\n"
    "        if nos: L += [\"\", f\"Not bought, no free slot ({PB.SLOTS} positions is the tested limit): \" + \", \".join(nmj(j) for j in nos) + \".\"]\n"
    "        if held_back: L += [\"\", \"Not bought, held back by the plan's own limits: \" + \", \".join(nmj(j) for j in held_back) + \".\"]\n"
    "        if wait: L += [\"\", \"Z score signals at this close, not bought (the market has not turned; each stays blocked for 40 sessions): \" + \", \".join(nmj(j) for j in wait) + \".\"]\n"
    "        for kind, txt in ((\"held\", \"Signal again in a stock you hold: keep holding, no second buy (the tested rule ignores it)\"),\n"
    "                          (\"repeat\", \"Skipped, it signalled before and was not bought then (no second signal within its 40 sessions)\"),\n"
    "                          (\"blocked\", \"Skipped, its paper trade started before the turn (blocked until that paper trade ends)\")):\n"
    "            xs = [(j, s0) for j, k, s0 in ST[\"rep\"] if k == kind]\n"
    "            if xs: L += [\"\", txt + \": \" + \", \".join(f\"{nmj(j)} (signal {fmt_d(dates[s0])})\" for j, s0 in xs) + \".\"]\n"
    "        if PLAN in (\"A\", \"Z\") and not buys: L += [\"\", \"**Nothing to buy in your plan at this close.**\" + (\"\" if len(keep) else \" Idle money stays in the money-market fund.\")]\n"
    "        if KIND == \"A\":\n"
    "            L += [\"\", \"Plan record as traded (5 slots, most volatile first, round 68): 2013-19 26 trades, 73% winners, +16.8% per trade, worst -12.6%; \"\n"
    "                  \"2020-26 25 trades, 84%, +9.4%, worst -12.3%. About 4 trades a year and none in 5 of the 14 years; it misses fast V-shaped rebounds \"\n"
    "                  \"(April 2025) and lost in late 2015. No stop: 36 stop rules were tested (round 69) and none improved the plan; a position typically \"\n"
    "                  \"closes about 6% below its entry at some point before it ends, and the plan's worst periods were about -10% of the account.\"]\n"
    "        else:\n"
    "            L += [\"\", \"Plan record as traded (5 slots, most volatile first, round 70): 2013-19 33 trades, 70% winners, +10.4% per trade, worst -21.6%; \"\n"
    "                  \"2020-26 36 trades, 72%, +7.8%, worst -15.5%. Trades in every year since 2014 (1 to 10 a year). About 3 in 10 trades lose.\"]\n")
patch(T3, [
    ("    L = L0 + (MRB + [\"\", \"---\", \"\", \"**For reference only, not in your plan A** (ML leaders / breakouts: they add losing years and deeper drawdowns, round 67):\"] + TOPB\n              if PLAN == \"A\" else TOPB + MRB)\n",
     "    L = L0 + (MRB + [\"\", \"---\", \"\", \"**For reference only, not in your plan** (ML leaders / breakouts: they add losing years and deeper drawdowns, round 67):\"] + TOPB\n              if PLAN in (\"A\", \"Z\") else TOPB + MRB)\n"),
    ("        if int(r.tier) == 4 and (not SET[\"plan_start\"] or r.signal >= SET[\"plan_start\"]): continue      # Market returned positions: the plan book above reports them\n"
     "        if PLAN == \"A\" and SET[\"plan_start\"] and r.signal >= SET[\"plan_start\"] and not (SET[\"zscore\"] and int(r.tier) == 1): continue   # not in the plan\n",
     "        if PLAN in (\"A\", \"Z\") and SET[\"plan_start\"] and r.signal >= SET[\"plan_start\"]: continue   # from the plan's start the plan book reports its positions; other picks are not in the plan\n"
     "        if int(r.tier) == 4 and not SET[\"plan_start\"]: continue                                      # Market returned positions without a plan: the book above reports them\n"),
    ("          + (f\"; plan A: at most 5 Market returned positions of {mrsz} (at most {5 * 100 * SET['mr_size']:.0f}% of the account in stocks), the rest in the money-market fund.\" if PLAN == \"A\" else\n",
     "          + (f\"; your plan: at most 5 {lab} positions of {mrsz} (at most {5 * 100 * psz:.0f}% of the account in stocks), the rest in the money-market fund.\" if PLAN in (\"A\", \"Z\") else\n")])
F27 = f"{S}/r27/final27.py"
patch(F27, [
    ("    _set = o7settings(); ST = PB.state(loss=True, week_complete=bool(wk_done), start=_set[\"plan_start\"] or None); _T = PB.T_;",
     "    _set = o7settings(); _kind = \"Z\" if _set[\"plan\"] == \"Z\" else \"A\"; ST = PB.state(loss=True, week_complete=bool(wk_done), start=_set[\"plan_start\"] or None, kind=_kind); _T = PB.T_;"),
    ("    BOOK = dict(slots=PB.SLOTS, free=int(ST[\"free\"]), start=_set[\"plan_start\"],",
     "    BOOK = dict(kind=_kind, size=_set[\"z_size\"] if _kind == \"Z\" else _set[\"mr_size\"], slots=PB.SLOTS, free=int(ST[\"free\"]), start=_set[\"plan_start\"],")])
print("patched")
