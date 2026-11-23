"""Plan A go-live (the user's choice 2026-11-09, round 67): buy only Market returned signals, 10% each, at most 5, most volatile first;
ML leader / breakout rows shown for reference only; idle money in a SAR money-market fund."""
import os, json
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def patch(path, pairs):
    s = open(path).read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, old[:80], s.count(old)); s = s.replace(old, new)
    open(path, "w").write(s)
patch(f"{S}/daily/opt7.py", [
    ('    d = {"zscore": True, "market_returned": False, "zscore_order": "volatility"}   # zscore_order (round 66): "volatility" or "ml"\n',
     '    d = {"zscore": True, "market_returned": False, "zscore_order": "volatility", "mr_size": 0.05, "plan": ""}   # zscore_order (round 66); mr_size, plan (round 67)\n'),
    ('    d.update({k: bool(v) for k, v in f.items() if k in d and k != "zscore_order"}); d["option7"] = d["market_returned"]\n',
     '    d.update({k: bool(v) for k, v in f.items() if k in ("zscore", "market_returned")}); d["option7"] = d["market_returned"]\n'
     '    if isinstance(f.get("mr_size"), (int, float)) and 0 < f["mr_size"] <= .2: d["mr_size"] = float(f["mr_size"])\n'
     '    if isinstance(f.get("plan"), str): d["plan"] = f["plan"]\n')])
json.dump({"zscore": False, "market_returned": True, "zscore_order": "volatility", "mr_size": 0.10, "plan": "A"}, open(f"{S}/daily/settings.json", "w"))
patch(f"{S}/daily/top3.py", [
    ("settings.json \"zscore_order\": \"volatility\" (default) or \"ml\". Each Z score row shows its volatility and its rank among liquid stocks.\n",
     "settings.json \"zscore_order\": \"volatility\" (default) or \"ml\". Each Z score row shows its volatility and its rank among liquid stocks.\n"
     "Change 2026-11-09 (round 67, the user's choice: plan A): buy only Market returned signals, 10% of the account each (settings.json mr_size),\n"
     "at most 5, most volatile first; Z score signals off (they still run as the shadow book that decides the blocked stocks); the top-3 table\n"
     "(ML leaders / breakouts) is printed after them for reference only; idle money in a SAR money-market fund. settings.json \"plan\": \"A\".\n"),
    ('    mr = sorted([j for j in zs_all if mron and O7["gate"] and cols[j] not in set(O7["blocked"])], key=lambda j: -pct[j])[:5]  # Market returned (its own list, ML order)\n',
     '    mr = [j for j in zs_all if mron and O7["gate"] and cols[j] not in set(O7["blocked"])]   # Market returned (its own list)\n'
     '    mr = (mr if ZORDER == "volatility" else sorted(mr, key=lambda j: -pct[j]))[:5]          # plan A (round 67): most volatile first, as tested\n'
     '    PLAN = SET["plan"]; mrsz = f"{100 * SET[\'mr_size\']:.0f}%"\n'),
    ('    if not SET["zscore"]: L += ["", "Z score signals are switched off (settings.json): the list below has no Z score picks."]\n'
     '    L += ["", "| # | Stock | Setup | Last close | Plan | Latest accounts |", "|---|---|---|---|---|---|"]\n',
     '    if PLAN == "A":\n'
     '        L += ["", f"**Your plan: A** (round 67): buy only the **Market returned** signals, **{mrsz} of the account each**, at most 5 at once (most volatile first), "\n'
     '                  "hold 40 sessions, no stop. Keep all idle money in a SAR money-market fund. ML leaders and breakouts are shown at the end for reference only. "\n'
     '                  "Tested on the whole account (idle money at T-bill interest): 2013-19 +6.8% a year, worst drawdown 9.7%; 2020-26 +6.5%, 6.3%; 2016-26 +8.7%, 6.3%."]\n'
     '    elif not SET["zscore"]: L += ["", "Z score signals are switched off (settings.json): the list below has no Z score picks."]\n'
     '    L0 = L; L = []\n'
     '    L += ["", "| # | Stock | Setup | Last close | Plan | Latest accounts |", "|---|---|---|---|---|---|"]\n'),
    ('    if mron:   # ---- Market returned signals: their own list\n',
     '    TOPB = L; L = []\n    if mron:   # ---- Market returned signals: their own list\n'),
    ('                L.append(f"| {n} | **{s_}** {nm.get(s_, s_)[:28]} ({industry(s_)}) | {setup} | {Cl[i, j]:.2f} | {size} of the account. Hold 40 sessions',
     '                L.append(f"| {n} | **{s_}** {nm.get(s_, s_)[:28]} ({industry(s_)}) | {setup} | {Cl[i, j]:.2f} | {mrsz} of the account. Hold 40 sessions'),
    ('        elif O7["gate"]: L += ["", "No new market-returned signal at this close."]\n',
     '        elif O7["gate"]: L += ["", "No new market-returned signal at this close."]\n'
     '        if PLAN == "A" and not mr: L += ["", "**Nothing to buy in your plan at this close.** Idle money stays in the money-market fund."]\n'),
    ('    # earlier picks: exits due at this open, using the same exit rules (repeat picks while held are ignored)\n',
     '    MRB = L\n'
     '    L = L0 + (MRB + ["", "---", "", "**For reference only, not in your plan A** (ML leaders / breakouts: they add losing years and deeper drawdowns, round 67):"] + TOPB\n'
     '              if PLAN == "A" else TOPB + MRB)\n'
     '    # earlier picks: exits due at this open, using the same exit rules (repeat picks while held are ignored)\n'),
    ('        if r.sym not in cols or pd.Timestamp(r.signal) not in dates: continue\n',
     '        if r.sym not in cols or pd.Timestamp(r.signal) not in dates: continue\n'
     '        if PLAN == "A" and r.signal >= "2026-11-09" and int(r.tier) != 4 and not (SET["zscore"] and int(r.tier) == 1): continue   # plan A: only its own picks from its start\n'),
    ('          + ("; keep at most 5 Z score positions open at once, taking them from the top (as tested; with the market-momentum gate the worst Z-swing trade lost about 23%)." if any(t == 1 for _, t in top) else ".")]\n',
     '          + (f"; plan A: at most 5 Market returned positions of {mrsz} (at most {5 * 100 * SET[\'mr_size\']:.0f}% of the account in stocks), the rest in the money-market fund." if PLAN == "A" else\n'
     '             "; keep at most 5 Z score positions open at once, taking them from the top (as tested; with the market-momentum gate the worst Z-swing trade lost about 23%)." if any(t == 1 for _, t in top) else ".")]\n')])
patch(f"{S}/r27/final27.py", [
    ('    OPT7 = dict(on=bool(o7settings()["market_returned"]), zscore=bool(o7settings()["zscore"]), blocked=O7B, **o7status(MT),',
     '    OPT7 = dict(on=bool(o7settings()["market_returned"]), zscore=bool(o7settings()["zscore"]), mr_size=o7settings()["mr_size"], plan=o7settings()["plan"], blocked=O7B, **o7status(MT),')])
patch(f"{S}/daily/top3.py", [("    L = [f\"**Saudi top 3 for {day.strftime('%A %d %b %Y')}**", "    L = [f\"**Saudi {'plan A list' if PLAN == 'A' else 'top 3'} for {day.strftime('%A %d %b %Y')}**")]) if "plan A list" not in open(f"{S}/daily/top3.py").read() else None
print("patched")
