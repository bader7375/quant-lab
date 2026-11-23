"""Option 7 examples: market index (round 47 definition, rebuilt to the latest close), the turn gate, and Z-swing trades before/after the turn."""
import os, sys, json, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../r48")); sys.path.insert(0, os.path.join(H, "../r47"))
from zswing import *
from mk47 import measures
os.chdir(H)
EL_ = P["elig"] & (P["VAL"].rolling(60, min_periods=20).median() >= 3e6); MK = measures(C, P["VAL"], EL_)
ov = SA.idx.dropna().index.intersection(MK.index); ratio = (MK.idx[ov] / SA.idx[ov]); print("rebuilt index vs stored (ratio range):", round(ratio.min(), 6), round(ratio.max(), 6), "| last", MK.index[-1].date())
idx = MK.idx; low20 = idx.rolling(20, min_periods=15).min(); bounce = idx / low20 - 1; ddmin = MK.dd250.rolling(20, min_periods=15).min()
turn = (bounce >= .04) & (ddmin <= -.10); gate = turn.astype(float).rolling(20, min_periods=1).max() > 0
G4x = g4_mask(MK); same = (G4x[:len(G4)] == G4)[np.isfinite(SA.idx.reindex(dates).values)].mean(); print("gate matches the stored gate on", f"{100 * same:.1f}% of days")
T = pd.read_csv("trades_g4.csv", parse_dates=["date"], dtype={"sym": str})
from sectors import industry
sys.path.insert(0, "../strat")
def pick_typical(g): m = g.net.median(); return g.iloc[(g.net - m).abs().argsort().iloc[0]]
eps = {"2020": ("2020-03-01", "2020-05-31"), "2025": ("2025-04-01", "2025-06-30")}
ex = []
g20 = T[(T.date >= "2020-03-01") & (T.date <= "2020-05-31")]
ex.append(("covid-skip", "March 2020: signal before the turn", pick_typical(g20[~g20.g4]), g20))
ex.append(("covid-buy", "March-April 2020: signal after the turn", pick_typical(g20[g20.g4]), g20))
g25 = T[(T.date >= "2025-04-01") & (T.date <= "2025-06-30")]
ex.append(("tariff-skip", "April 2025: signal before the turn, and the market snapped back", pick_typical(g25[~g25.g4]), g25))
Cv, Ov, Hv, Lv = (P[k].reindex(index=dates, columns=cols) for k in ("C", "O", "H", "L"))
def series(a, b): s = idx.loc[a:b]; return s
out = {"examples": []}
def pack(key, title, d0i, d1i, j, sig_i, entry_i, exit_i, net, taken, group):
    a, b = dates[max(0, d0i)], dates[min(len(dates) - 1, d1i)]; m = (idx.index >= a) & (idx.index <= b); base = idx[m].iloc[0]
    sym = cols[j]; st = lambda X: [None if not np.isfinite(v) else round(float(v), 4) for v in X]
    sel = (dates >= a) & (dates <= b)
    ex = dict(key=key, title=title, sym=sym, sector=industry(sym), dates=[str(x.date()) for x in dates[sel]],
              mkt=st(100 * idx[m] / base), low=st(100 * low20[m] / base), trig=st(104 * low20[m] / base), gate=[bool(x) for x in gate[m]],
              turn=[bool(x) for x in turn[m]], dd=st(100 * MK.dd250[m]), o=st(Ov.values[sel, j]), h=st(Hv.values[sel, j]), l=st(Lv.values[sel, j]), c=st(Cv.values[sel, j]),
              z=st(M["Z"][sel, j]), signal=str(dates[sig_i].date()), entry=str(dates[entry_i].date()) if entry_i is not None else None,
              exit=str(dates[exit_i].date()) if exit_i is not None and exit_i < len(dates) else None,
              entry_px=round(float(M["Of"][entry_i, j]), 3) if entry_i is not None else None, exit_px=round(float(M["Of"][exit_i, j]), 3) if exit_i is not None and exit_i < len(dates) else None,
              net=None if net is None else round(float(net), 4), taken=bool(taken), gate_at_signal=bool(gate.iloc[sig_i]),
              group=dict(n=int(len(group)), skip_n=int((~group.g4).sum()), skip_avg=float(group[~group.g4].net.mean()) if (~group.g4).any() else None,
                         skip_win=float((group[~group.g4].net > 0).mean()) if (~group.g4).any() else None, take_n=int(group.g4.sum()),
                         take_avg=float(group[group.g4].net.mean()) if group.g4.any() else None, take_win=float((group[group.g4].net > 0).mean()) if group.g4.any() else None) if group is not None else None,
              other_signals=[dict(date=str(r.date.date()), sym=r.sym, taken=bool(r.g4), net=round(float(r.net), 4)) for r in group.itertuples()] if group is not None else [])
    out["examples"].append(ex); print(f"{key}: {sym} signal {ex['signal']} entry {ex['entry']} exit {ex['exit']} net {ex['net']} option7 {'BUY' if taken else 'SKIP'} gate {ex['gate_at_signal']}")
for key, title, r, grp in ex:
    i = int(r.i); pack(key, title, i - 45, int(r.ex) + 5, int(r.j), i, int(r.d1), int(r.ex), r.net, bool(r.g4), grp)
# live now: the October 2026 sell-off and this week's signals (trades still open)
L = live_trades.__globals__["trades"](S_LIVE, M)
L = L[dates[L.i.values] >= pd.Timestamp("2026-10-01")].copy(); L["date"] = dates[L.i.values]; L["sym"] = [cols[j] for j in L.j.values]; L["g4"] = gate.reindex(L.date).values
print(L[["date", "sym", "g4", "d1", "ex"]].assign(date=lambda x: x.date.dt.date).to_string())
out["now_signals"] = [dict(date=str(r.date.date()), sym=r.sym, taken=bool(r.g4)) for r in L.itertuples()]
# summary of every sell-off (finished trades)
out["episodes"] = []
T = T.sort_values("i"); T["ep"] = (T.i.diff() > 30).cumsum().values
for e, g in T.groupby("ep"):
    if len(g) < 5: continue
    sk, tk = g[~g.g4], g[g.g4]
    out["episodes"].append(dict(start=str(g.date.min().date()), end=str(g.date.max().date()), skip_n=len(sk), skip_avg=float(sk.net.mean()) if len(sk) else None, skip_win=float((sk.net > 0).mean()) if len(sk) else None,
                                take_n=len(tk), take_avg=float(tk.net.mean()) if len(tk) else None, take_win=float((tk.net > 0).mean()) if len(tk) else None))
out["last_date"] = str(dates[-1].date()); out["gate_now"] = bool(gate.iloc[-1]); lt = turn[turn].index; out["last_turn"] = str(lt[-1].date())
out["now_bounce"] = float(bounce.iloc[-1]); out["now_dd"] = float(MK.dd250.iloc[-1])
json.dump(out, open("opt7.json", "w")); print("gate now", out["gate_now"], "last turn", out["last_turn"], "bounce off 20d low", round(out["now_bounce"], 4), "dd250", round(out["now_dd"], 4))
