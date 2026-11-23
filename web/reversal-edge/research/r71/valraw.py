"""Round 71 finding: traded value from the dividend-adjusted close vs the raw close. Size of the gap and its effect on the Z score plan
(liquidity filter only; ML ranks and the market model unchanged here)."""
import os, sys, glob, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daily")); import planbook as PB
d, cols = PB.dates, PB.cols; raw = {}
for s in cols:
    f = os.path.join(PB.S, f"edge26/data/d/{s}.SR.csv")
    if os.path.exists(f): x = pd.read_csv(f, index_col=0, parse_dates=True); raw[s] = x["close"]
RC = pd.DataFrame(raw).reindex(index=d, columns=cols); F = (PB.C / RC).where(RC > 0)            # adjustment factor = adjusted / raw close
VAL_adj = PB.P["VAL"]; VAL_raw = (VAL_adj / F).where(F > 0)
yr = F.groupby(d.year).median().median(1); print("median adjustment factor (adjusted / raw close) by year: " + ", ".join(f"{y}: {v:.2f}" for y, v in yr.items() if y >= 2012))
EL_adj = PB.EL; med = VAL_raw.rolling(60, min_periods=20).median(); C_ = PB.C
elig_raw = C_.notna() & (C_.notna().cumsum() >= 120) & (med >= 3e6); EL_raw = elig_raw.values   # eligibility rebuilt from raw value
r_ = np.log(C_).diff().clip(-.25, .25); mr_ = r_.where(elig_raw).mean(1); msd_ = mr_.rolling(60, min_periods=40).std()
MS_raw = (mr_.rolling(60, min_periods=48).sum() / (msd_.shift(60) * np.sqrt(60))).values; MS_adj = PB.MS
print(f"market momentum: days on the other side of -1.18 (2013-26): {int(((MS_raw <= -1.18) != (MS_adj <= -1.18))[np.searchsorted(d.values, np.datetime64('2013-01-01')):].sum())}")
i0 = np.searchsorted(d.values, np.datetime64("2013-01-01")); diff = (EL_adj != EL_raw)[i0:]
print(f"stock-days 2013-26 whose 'liquid' flag differs: {diff.sum()} of {(EL_adj | EL_raw)[i0:].sum()} liquid stock-days ({100 * diff.sum() / max((EL_adj | EL_raw)[i0:].sum(), 1):.1f}%); "
      f"liquid only with raw value: {(EL_raw & ~EL_adj)[i0:].sum()}, only with adjusted: {(EL_adj & ~EL_raw)[i0:].sum()}")
S_adj = PB.signals(); PB.EL = EL_raw; PB.MS = MS_raw; S_raw = PB.signals(); PB.EL = EL_adj; PB.MS = MS_adj
print(f"Z score signals 2013-26: adjusted {S_adj[i0:].sum()}, raw {S_raw[i0:].sum()}, only raw {(S_raw & ~S_adj)[i0:].sum()}, only adjusted {(S_adj & ~S_raw)[i0:].sum()}")
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31")}
for nm, S_ in (("adjusted value (live)", S_adj), ("raw value", S_raw)):
    SH = PB.shadow(S_); SH = SH[(SH.ex < PB.T_) & (SH.i >= i0)]; PL = PB.plan(SH, gate=PB.ALL); eq = PB.account(PL, w=.05); tk = PL[PL.taken]; n = PB.trade_net(tk)
    print(f"  {nm:22s} " + " | ".join(f"{e} {100 * PB.perf(eq, a, b)['cagr']:+.1f}% DD {100 * PB.perf(eq, a, b)['dd']:.1f}%" for e, (a, b) in ER.items()) + f" | trades {len(tk)}, winners {100 * (n > 0).mean():.0f}%, average {100 * n.mean():+.1f}%")
