"""Round 66 go-live (the user's choice 2026-11-09): Z score signals most volatile first; volatility shown in the list and the scan."""
import os, json
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def patch(path, pairs):
    s = open(path).read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, old[:80], s.count(old)); s = s.replace(old, new)
    open(path, "w").write(s)
# ---------------------------------------------------------------- opt7.settings: the order switch
patch(f"{S}/daily/opt7.py", [
    ('    d = {"zscore": True, "market_returned": False}\n',
     '    d = {"zscore": True, "market_returned": False, "zscore_order": "volatility"}   # zscore_order (round 66): "volatility" or "ml"\n'),
    ('    d.update({k: bool(v) for k, v in f.items() if k in d}); d["option7"] = d["market_returned"]; return d',
     '    d.update({k: bool(v) for k, v in f.items() if k in d and k != "zscore_order"}); d["option7"] = d["market_returned"]\n'
     '    if f.get("zscore_order") in ("volatility", "ml"): d["zscore_order"] = f["zscore_order"]\n    return d')])
json.dump({"zscore": True, "market_returned": True, "zscore_order": "volatility"}, open(f"{S}/daily/settings.json", "w"))
# ---------------------------------------------------------------- top3.py
patch(f"{S}/daily/top3.py", [
    ('bought before the turn (opt7.py). It has its own section, record and log (tier 4), at most 5 positions; a stock in both is one trade.\n',
     'bought before the turn (opt7.py). It has its own section, record and log (tier 4), at most 5 positions; a stock in both is one trade.\n'
     'Change 2026-11-09 (round 66, the user\'s choice): Z score signals are listed most volatile first (60-day volatility = daily sd of returns)\n'
     'instead of highest ML rank; ML rank >= 50% stays a filter. Market returned keeps the ML order (volatility did not clearly help there).\n'
     'settings.json "zscore_order": "volatility" (default) or "ml". Each Z score row shows its volatility and its rank among liquid stocks.\n'),
    ('MS = (_mr.rolling(60, min_periods=48).sum() / (_msd.shift(60) * np.sqrt(60))).values\n',
     'MS = (_mr.rolling(60, min_periods=48).sum() / (_msd.shift(60) * np.sqrt(60))).values\n'
     'VOLD = _r.rolling(60, min_periods=40).std().values                            # round 66: 60-day volatility (daily sd of returns)\n'
     'VOLP = pd.DataFrame(VOLD).where(LIQ).rank(axis=1, pct=True).values            # its rank among the liquid stocks that day (1 = most volatile)\n'
     'from opt7 import settings as _o7s\n'
     'ZORDER = _o7s()["zscore_order"]                                               # "volatility" (round 66) or "ml"\n'
     'def _vt(i, j): return f", vol {100 * VOLD[i, j]:.1f}%/day (rank {100 * VOLP[i, j]:.0f}%)" if np.isfinite(VOLD[i, j]) and np.isfinite(VOLP[i, j]) else ""\n'),
    ('    for t, m in masks:\n        for j in np.where(m)[0][np.argsort(-pct[m], kind="stable")]:\n',
     '    for t, m in masks:\n        key = VOLD[i] if t == 1 and ZORDER == "volatility" else pct          # round 66: Z score most volatile first\n'
     '        for j in np.where(m)[0][np.argsort(-np.nan_to_num(key[m], nan=-1.0), kind="stable")]:\n'),
    ('    mr = [j for j in zs_all if mron and O7["gate"] and cols[j] not in set(O7["blocked"])][:5]  # Market returned signals (its own list)\n',
     '    mr = sorted([j for j in zs_all if mron and O7["gate"] and cols[j] not in set(O7["blocked"])], key=lambda j: -pct[j])[:5]  # Market returned (its own list, ML order)\n'),
    ('setup = {1: (f"Z score (weekly candles): weekly stretch Z {ZWV[i, j]:.2f}, ML {100 * ml:.0f}%" if wkly else f"Z score: stretch Z {z:.2f}, ML {100 * ml:.0f}%"),',
     'setup = {1: (f"Z score (weekly candles): weekly stretch Z {ZWV[i, j]:.2f}, ML {100 * ml:.0f}%" if wkly else f"Z score: stretch Z {z:.2f}, ML {100 * ml:.0f}%") + _vt(i, j),'),
    ('    g = "neg" if half else "pos"; L += ["", f"How these setups did',
     '    if any(t == 1 for _, t in top) and ZORDER == "volatility":\n'
     '        L += ["", "Z score order: **most volatile first** (60-day volatility; ML rank 50%+ stays a filter). With more signals than free slots, take them from the top. "\n'
     '                  "Tested 2013-26 (round 66, 5 slots x 5%): return/drawdown 0.39 / 0.37 (2013-19 / 2020-26) vs 0.24 / 0.27 in ML order; a yearly walk-forward chose it every year."]\n'
     '    g = "neg" if half else "pos"; L += ["", f"How these setups did'),
    ('"Also qualifying today: " + ", ".join(f"{cols[j]} {nm.get(cols[j], \'\')[:18]} ({TIERS[t][\'name\']}, ML {100 * pct[j]:.0f}%)" for j, t in more)',
     '"Also qualifying today: " + ", ".join(f"{cols[j]} {nm.get(cols[j], \'\')[:18]} ({TIERS[t][\'name\']}, ML {100 * pct[j]:.0f}%{_vt(i, j) if t == 1 else \'\'})" for j, t in more)'),
    ('else f"Market returned: stretch Z {ZC.iloc[i, j]:.2f}") + f", ML {100 * pct[j]:.0f}%" + (',
     'else f"Market returned: stretch Z {ZC.iloc[i, j]:.2f}") + f", ML {100 * pct[j]:.0f}%" + _vt(i, j) + ('),
    ('"; keep at most 5 Z score positions open at once (as tested;',
     '"; keep at most 5 Z score positions open at once, taking them from the top (as tested;')])
# ---------------------------------------------------------------- final27.py: volatility in the scan, scan order
patch(f"{S}/r27/final27.py", [
    ('zscan = []\ndef _ztm(',
     'try:   # round 66: 60-day volatility (daily sd of returns) and its rank among liquid stocks; Z score order: most volatile first\n'
     '    _cv = PP["C"].where(PP["C"] > 0); _rv = np.log(_cv).diff().clip(-.25, .25); VOLL = _rv.rolling(60, min_periods=40).std().iloc[-1]\n'
     '    _lq = (PP["elig"] & (PP["VAL"].rolling(60, min_periods=20).median() >= 3e6)).iloc[-1]; VRL = VOLL.where(_lq).rank(pct=True)\n'
     '    ZORDER = o7settings()["zscore_order"]\n'
     'except Exception as ex:\n'
     '    print("volatility failed:", ex); VOLL = VRL = None; ZORDER = "ml"\n'
     'zscan = []\ndef _ztm('),
    ('    for s_ in sorted(fresh, key=lambda x: ((x in LOSSY) or float(tv.loc[x, "pct"]) < .5, -float(tv.loc[x, "pct"])) if x in tv.index else (True, 0)) + rest:',
     '    _vk = lambda x: -float(VOLL.get(x, np.nan)) if ZORDER == "volatility" and VOLL is not None and np.isfinite(VOLL.get(x, np.nan)) else (0.0 if ZORDER == "volatility" and VOLL is not None else -float(tv.loc[x, "pct"]))\n'
     '    for s_ in sorted(fresh, key=lambda x: ((x in LOSSY) or float(tv.loc[x, "pct"]) < .5, _vk(x)) if x in tv.index else (True, 0)) + rest:   # round 66: buyable ones most volatile first'),
    ('"loss": s_ in LOSSY, "val_m": round(float(r.val) / 1e6, 1), "sector": industry(s_), "b7": s_ in O7B})',
     '"loss": s_ in LOSSY, "val_m": round(float(r.val) / 1e6, 1), "sector": industry(s_), "b7": s_ in O7B})\n'
     '        if VOLL is not None and np.isfinite(VOLL.get(s_, np.nan)):\n'
     '            zscan[-1].update(vol=round(float(VOLL[s_]), 4), vr=round(float(VRL.get(s_, np.nan)), 3) if np.isfinite(VRL.get(s_, np.nan)) else None)'),
    ('"fin": FIN, "zscan": zscan, "opt7": OPT7',
     '"fin": FIN, "zscan": zscan, "opt7": OPT7, "zorder": ZORDER')])
print("patched")
