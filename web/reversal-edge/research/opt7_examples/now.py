import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, "../r48"); sys.path.insert(0, "../r47"); sys.path.insert(0, "../strat"); from zswing import *
from mk47 import measures
from sectors import industry
os.chdir(os.path.dirname(os.path.abspath(__file__)))
EL_ = P["elig"] & (P["VAL"].rolling(60, min_periods=20).median() >= 3e6); MK = measures(C, P["VAL"], EL_); gate = g4_mask(MK)
low20 = MK.idx.rolling(20, min_periods=15).min(); turn = ((MK.idx / low20 - 1 >= .04) & (MK.dd250.rolling(20, min_periods=15).min() <= -.10)).values
ii, jj = np.where(S_LIVE); o = np.lexsort((jj, ii)); ii, jj = ii[o], jj[o]; m = dates[ii] >= pd.Timestamp("2026-08-01"); ii, jj = ii[m], jj[m]
busy, book = {}, []
for i, j in zip(ii, jj):                       # the live rule on paper: one position per stock, held 40 sessions from the next open
    if busy.get(j, -1) > i: continue
    busy[j] = i + 1 + 40; book.append((i, j))
rows = []
for i, j in book:
    d1 = i + 1; px = M["Of"][d1, j] if d1 < len(dates) else np.nan; last = M["Cf"][-1, j]
    rows.append(dict(date=str(dates[i].date()), sym=cols[j], sector=industry(cols[j]), option7=bool(gate[i]), ml=round(float(RANK[i, j]), 2), entry=str(dates[d1].date()) if d1 < len(dates) else None,
                     entry_px=None if not np.isfinite(px) else round(float(px), 3), now=round(float(last), 3), ret_now=None if not np.isfinite(px) else round(float(last / px - 1), 4)))
B = pd.DataFrame(rows); print(B.to_string())
skipped = B[~B.option7]; taken = B[B.option7]
print(f"\nskipped (paper trades before the turn): {len(skipped)}, open result so far avg {100 * skipped.ret_now.mean():+.1f}%; taken after the turn: {len(taken)}, avg {100 * taken.ret_now.mean():+.1f}%")
j = json.load(open("opt7.json")); j["now_book"] = rows
best = taken.sort_values("ml", ascending=False).iloc[0]; print("now example stock (highest ML among option-7 buys):", best.sym, best.date)
jc = cols.get_loc(best.sym); i = int(np.where(dates == pd.Timestamp(best.date))[0][0]); a = max(0, i - 45); b = len(dates) - 1
sel = slice(a, b + 1); base = MK.idx.iloc[a]; st = lambda X: [None if not np.isfinite(v) else round(float(v), 4) for v in X]
rx = lambda k: P[k].reindex(index=dates, columns=cols).values[sel, jc]
j["now"] = dict(key="now", title="October-November 2026: the sell-off now", sym=best.sym, sector=industry(best.sym), dates=[str(x.date()) for x in dates[sel]],
                mkt=st(100 * MK.idx.values[sel] / base), low=st(100 * low20.values[sel] / base), trig=st(104 * low20.values[sel] / base), gate=[bool(x) for x in gate[sel]], turn=[bool(x) for x in turn[sel]],
                o=st(rx("O")), h=st(rx("H")), l=st(rx("L")), c=st(rx("C")), z=st(M["Z"][sel, jc]), signal=best.date, entry=best.entry, entry_px=best.entry_px, now_px=best.now, ret_now=best.ret_now,
                taken=True, gate_at_signal=True)
json.dump(j, open("opt7.json", "w")); print("saved")
