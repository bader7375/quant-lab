"""Fable daily brief: the morning list in plain sentences, written from the Fable export (so the brief and the terminal never disagree).
Usage: RE_WORK=<work folder> python3 brief.py [--json <export file>]   -> prints the brief and saves <work>/fable/brief_<close date>.md"""
import os, sys, json, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); WORK = os.path.abspath(os.environ.get("RE_WORK", "."))
src = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else os.path.join(WORK, "fable", "fable_latest.json"); X = json.load(open(src))
D = lambda s: pd.Timestamp(s).strftime("%a %d %b"); pc = lambda x, n=1: "n/a" if x is None else f"{100 * x:+.{n}f}%"; p0 = lambda x, n=1: "n/a" if x is None else f"{100 * x:.{n}f}%"
W, E, LV, FB, RP = X["weather"], X["episode"], X["live"], X["fable"], X["replay"]; L = []
WORD = {"deep storm": "DEEP STORM", "storm": "STORM", "clearing": "CLEARING", "clouds": "CLOUDS", "calm": "CALM"}
MEAN = {"deep storm": "a deep market sell-off; the buy window is open and steps are double size on the ladder", "storm": "a market sell-off; the buy window is open", "clearing": "the sell-off has eased; the buy window is closed for now",
        "clouds": "the market is weak but not in a sell-off; no buys", "calm": "no sell-off; no buys, idle money stays in the money-market fund"}
L += [f"# Fable brief for {pd.Timestamp(X['day']).strftime('%A %d %b %Y')}", "", f"Prices to the {D(X['asof'])} close ({X['stocks']} stocks). Orders are for the 10:00 open."]
if X.get("stale"): L += ["", f"**Warning: the newest close in the data is {D(X['asof'])}. Yahoo has not published a later one yet, or the market was closed. Treat the lines below as yesterday's picture.**"]
for w_ in X.get("record_warn", []):
    L += ["", f"**Note on {w_['sym']} {w_['name']} ({'your plan' if w_['rule'] == 'live' else 'a paper book'}):** today's replay no longer shows the signal of {D(w_['signal'])} (a model refit moved a gate that sat on the line). The record stands: it stays in the book until its sale at the open of {D(w_['sell'])}."]
nb, ns = len(LV["buys"]), len(LV["due"])
L += ["", "**Today in your live plan: " + (f"BUY {nb}" if nb else "nothing to buy") + ", " + (f"SELL {ns}" if ns else "nothing to sell") + f", {len(LV['held'])} held, {LV['free']} of {LV['slots']} slots free.**"]
# ---- weather
L += ["", f"## 1. Market weather: {WORD[W['state']]}", "", f"- {MEAN[W['state']].capitalize()}.",
      f"- Market momentum is {W['ms']:+.2f} (how far the whole market has moved in 60 sessions, in units of its normal swing). Buys are allowed at {W['gate']} or lower; \"deep\" is {W['deep']} or lower.",
      f"- Market model (a 20-session market forecast): {pc(W['pm'])} -> " + ("**positive**, signals are allowed." if W["pm_ok"] else "**negative**: no buys today, whatever the stocks do."),
      f"- The market moved {pc(W['chg1'])} at the last close, {pc(W['chg5'])} in 5 sessions, {pc(W['chg20'])} in 20. It is {p0(-W['dd'], 0)} under its 1-year high.",
      f"- Fear gauge: {p0(W['fear'], 0)} of the {W['n_liquid']} liquid stocks are stretched below -2 today; {W['below_line']} sit at or below the -2.62 line."]
if E["open"]: L += [f"- This sell-off began on {D(E['start'])} (session {E['day']} now). The market is {pc(E['since'])} from that day and was {pc(E['low'])} at its low. It is deeper than {E['deeper_than']} of the {E['of']} sell-offs since 2013."]
# ---- orders
L += ["", "## 2. Orders for the 10:00 open (your live plan: up to 5 at once, 5% each)", ""]
if ns: L += ["| SELL | Bought | Entry | Last close | So far |", "|---|---|---|---|---|"] + [f"| **{p['sym']}** {p['name']} | {D(p['bought'])} | {p['entry']:.2f} | {p['last']:.2f} | {pc(p['ret'])} |" for p in LV["due"]] + [""]
if nb:
    cards = {s["sym"]: s for s in X["signals"]}
    L += ["| BUY | Size | Why | Last close | Sell at the open of |", "|---|---|---|---|---|"]
    for b in LV["buys"]:
        c = cards.get(b["sym"], {}); why = (f"weekly stretch Z {c.get('zw')}" if c.get("weekly") else f"stretch Z {c.get('z')}") + f", ML rank {p0(c.get('ml'), 0)}, volatility rank {p0(c.get('volr'), 0)}"
        L.append(f"| **{b['sym']}** {b['name']} | {p0(b['w'], 0)} of the account | {why} | {b['close']:.2f} | {D(b['sell'])} |")
else: L.append("No new signal passed every gate at this close. **Nothing to buy.**" + ("" if LV["held"] else " Idle money stays in the money-market fund."))
if LV["skipped"]: L += ["", "Signals not bought: " + "; ".join(f"{x['sym']} {x['name']} ({x['why']})" for x in LV["skipped"]) + "."]
if LV["repeats"]: L += ["", "Repeat signals (no second buy): " + ", ".join(f"{x['sym']} {x['name']}" for x in LV["repeats"]) + "."]
# ---- book
L += ["", f"## 3. Your plan book: {len(LV['held'])} of {LV['slots']} slots in use" + (f" (plan started {D(LV['start'])})" if LV.get("start") else ""), ""]
if LV["held"]: L += ["| Held | Bought | Entry | Last | So far | Sessions left | Sell at the open of |", "|---|---|---|---|---|---|---|"] + [f"| **{p['sym']}** {p['name']} | {D(p['bought'])} | {p['entry']:.2f} | {p['last']:.2f} | {pc(p['ret'])} | {p['left']} | {D(p['sell'])} |" for p in LV["held"]]
else: L.append("No positions.")
# ---- the Fable swing on paper
SWX = X.get("swing")
if SWX:
    SR_, SBK, SRP = SWX["rule"], SWX["book"], SWX["replay"]; SS = X["scan_sum"]; z = lambda v: str(v).replace("-", "\u2212")
    L += ["", "## 4. The Fable swing (on paper until you say yes)", "",
          f"Rule: buy at the open after a stock first closes in the buy zone (stretch Z {SR_['line']} or lower) in storm or deep weather, with the gates. **One buy a day**, the most volatile first, up to {SR_['slots']} positions of {p0(SR_['size'])} ({p0(SR_['deep_size'])} in deep weather). "
          f"**Sell at the open after the first close with stretch Z at {SR_['target']:.0f} or higher**, or after {SR_['cap']} sessions.", ""]
    if SBK["due"]: L += ["| SELL (paper) | Bought | Entry | Last close | So far | Why |", "|---|---|---|---|---|---|"] + [f"| **{p['sym']}** {p['name']} | {D(p['bought'])} | {p['entry']:.2f} | {p['last']:.2f} | {pc(p['ret'])} | {p.get('why') or ''} |" for p in SBK["due"]] + [""]
    if SBK["buys"]: L += ["| BUY (paper) | Size | Stretch Z | Last close | Sells |", "|---|---|---|---|---|"] + [f"| **{b['sym']}** {b['name']} | {p0(b['w'])} | {b['z']} | {b['close']:.2f} | when the stretch is gone, by {D(b['latest'])} |" for b in SBK["buys"]] + [""]
    if not SBK["due"] and not SBK["buys"]: L.append("- Today on paper: nothing to buy, nothing to sell." + (f" Buy window {'open' if SS['window'] else 'closed'}; {SS['inzone']} of {SS['n']} liquid stocks are in the buy zone, {SS['near']} within 5% of it."))
    if SBK["skipped"]: L.append("- Crossed and not bought: " + "; ".join(f"{x['sym']} {x['name']} ({x['why']})" for x in SBK["skipped"]) + ".")
    if SBK["held"]:
        L += ["", "| Held (paper) | Bought | Entry | Last | So far | Sells at a close of | At the latest |", "|---|---|---|---|---|---|---|"] + [f"| **{p['sym']}** {p['name']} | {D(p['bought'])} | {p['entry']:.2f} | {p['last']:.2f} | {pc(p['ret'])} | {p['sellpx']:.2f} or higher | {D(p['latest'])} |" for p in SBK["held"]]
    else: L.append(f"- Paper book since {D(SBK['start'])}: no position, {SBK['free']} of {SBK['slots']} steps free.")
    if E["open"] and (SRP["held"] or SRP["due"]):
        L.append(f"- Had it run through this sell-off (a replay): {len(SRP['held']) + len(SRP['due'])} positions, {p0(SRP['invested'], 0)} of the account in stocks, {pc(SRP['pnl'], 2)} of the account so far" + (f"; it would sell {', '.join(p['sym'] for p in SRP['due'])} today" if SRP["due"] else "") + ".")
    near = [r for r in X["scan"] if r["st"] in ("near", "zone", "cand")][:6]
    if near:
        L += ["", "Scanner, nearest the buy zone:", "", "| Stock | Stretch Z | Last close | Buy line (tomorrow's close) | Needs | ML rank | Loss-making |", "|---|---|---|---|---|---|---|"]
        L += [f"| **{r['sym']}** {r['name'][:24]} | {r['z']:.2f} | {r['c']:.2f} | {r['line']:.2f} | {'in the zone' if r['inz'] else pc(r['need'])} | {p0(r['ml'], 0)} | {'yes' if r['loss'] else 'no'} |" for r in near]
    es = X.get("evidence", {}).get("swing")
    if es: L += ["", f"Tested record: {es['stats']['2013-26']['n']} swings since 2013, {p0(es['stats']['2013-26']['win'], 0)} winners, {pc(es['stats']['2013-26']['avg'])} each, about {es['stats']['2013-26']['held']:.0f} sessions each. Against your live rule it passed the strict test in both periods; "
                     "it is on paper since " + D(SR_["start"]) + "."]
# ---- the ladder on paper
R = X["rule"]["fable"]; fb, fs = len(FB["buys"]), len(FB["due"])
L += ["", "## 5. The ladder (on paper)", "", f"Rule: the same signals, **one buy a day** (the most volatile), up to {R['slots']} positions of {p0(R['size'])}, or {p0(R['deep_size'])} when market momentum is {R['deep']} or lower. Hold 40 sessions, no stop.", "",
      "- Today it would: " + (("buy " + ", ".join(f"**{b['sym']}** {b['name']} ({p0(b['w'])})" for b in FB["buys"])) if fb else "buy nothing") + (("; sell " + ", ".join(p["sym"] for p in FB["due"])) if fs else "") + f". Paper book since {D(FB['start']) if FB.get('start') else 'the start'}: {len(FB['held'])} of {FB['slots']} steps in use."]
if E["open"] and (RP["live"]["held"] or RP["fable"]["held"]):
    f_ = lambda r: f"{len(r['held'])} positions, {p0(r['invested'], 0)} of the account in stocks, {pc(r['pnl'], 2)} of the account so far"
    L += [f"- Had both rules run through this sell-off (a replay, not your account): live rule {f_(RP['live'])}; ladder {f_(RP['fable'])}."]
# ---- watch
if X["watch"]:
    L += ["", "## 6. One close away for your live rule", "", "Liquid stocks nearest a first touch of the -2.62 line. \"Signals at\" is the close that would put them on the line tomorrow.", "", "| Stock | Stretch Z | Last close | Signals at | Needs | Would it pass the other gates? |", "|---|---|---|---|---|---|"]
    for c in X["watch"][:8]:
        no = [t for t, bad in (("ML rank below 50%", not c["ml_ok"]), ("loss-making", c["loss"]), ("market model negative", not W["pm_ok"]), ("market not in a sell-off", W["ms"] > W["gate"]), ("signalled in the last 40 sessions", c["paper_open"])) if bad]
        L.append(f"| **{c['sym']}** {c['name'][:24]} | {c['z']:.2f} | {c['close']:.2f} | {c['band']:.2f} | {pc(c['need'])} | {'yes' if c['ok'] else 'no: ' + ', '.join(no)} |")
# ---- expectations
ev = X.get("evidence", {}).get("saudi")
if ev:
    L += ["", "## 7. What the test record expects (growth a year / worst drawdown; ranges from redrawing whole sell-offs)", "", "| | 2013-19 | 2020-26 | 2023-26 | 2013-26 | range 2013-26 |", "|---|---|---|---|---|---|"]
    es = X.get("evidence", {}).get("swing")
    if es:
        for k, lab in (("LIVE", "Live rule, 5 x 5%"), ("SWING", "Swing, 2.1% / 4.2%, sold when the stretch is gone"), ("LADDER", "Ladder, 2.1% / 4.2%, held 40 sessions")):
            e = es["eras"][k]; r = es["boot"]["2013-26"][k]
            L.append(f"| {lab} | " + " | ".join(f"{pc(e[p][0])} / {p0(e[p][1])}" for p in ("2013-19", "2020-26", "2023-26", "2013-26")) + f" | {pc(r['g'][0])} to {pc(r['g'][1])} / {p0(r['dd'][0])} to {p0(r['dd'][1])} |")
    else:
        for k, lab in (("LIVE", "Live rule, 5 x 5%"), ("L12D", "Ladder, 2.1% / 4.2% steps")):
            e = ev[k]["eras"]; r = ev[k]["range"]["2013-26"]
            L.append(f"| {lab} | " + " | ".join(f"{pc(e[p][0])} / {p0(e[p][1])}" for p in ("2013-19", "2020-26", "2023-26", "2013-26")) + f" | {pc(r['g'][0])} to {pc(r['g'][1])} / {p0(r['dd'][0])} to {p0(r['dd'][1])} |")
    q = X["expect"]["final"]["all"]
    L += ["", f"One signal, held 40 sessions ({q['n']} in the record): half ended above {pc(q['q'][2])}, {p0(q['win'], 0)} made money, 1 in 20 ended below {pc(q['q'][0])}. About 3 in 10 of the trades you take lose."]
# ---- scorecard
S = X["scorecard"]; L += ["", f"## 8. Scorecard since {D(S['start']) if S.get('start') else 'the start'}", ""]
if S["live"]:
    L += ["| Live pick | Bought | Result so far | Session | Rank against the record at that session |", "|---|---|---|---|---|"] + [f"| **{t['sym']}** {t['name']} | {D(t['bought'])} | {pc(t['ret'])}{' (closed)' if t['closed'] else ''} | {t['day']} | better than {p0(t['pct'], 0)} of past signals |" for t in S["live"]]
else: L.append("No live pick yet.")
if S["paper"]: L += ["", f"This sell-off's {len(S['paper'])} signals on paper (not bought; your plan started later): average {pc(S['paper_avg'])} so far. The middle one ranks better than {p0(S['paper_pct'], 0)} of past signals at the same session, so " + ("it is running in line with the record." if .35 <= S["paper_pct"] <= .65 else "it is running ahead of the record." if S["paper_pct"] > .65 else "it is running behind the record.")]
L += ["", "Research signals, not financial advice. Nothing here changes what is live: the swing and the ladder are paper books until you say yes."]
for f in ("daily/out/us_latest.md", "daily/out/us30_latest.md"):          # the US part, exactly as the live list prints it
    p = os.path.join(WORK, f)
    if os.path.exists(p): L += ["", "---", "", open(p).read().strip()]
md = "\n".join(L); open(os.path.join(os.path.dirname(src), f"brief_{X['asof']}.md"), "w").write(md); print(md)
