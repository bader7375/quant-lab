"""Descriptive follow-up (after H2 failed): ABSOLUTE net return and win rate by gauge tercile, and overlap with the market model."""
import pandas as pd, numpy as np, json
S = json.load(open("h2_selection.json"))["res"]
T = pd.read_parquet("h2_eb.parquet"); TL = pd.read_parquet("h2_eb_deep.parquet"); A = pd.concat([TL[TL.date < "2013"], T[T.date >= "2013"]])
pm = pd.read_parquet("../r27/pm27.parquet").pm_old; A["pm"] = A.date.map(pm)
er = {"DEEP": ("2004", "2012-12-31"), "DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "C1": ("2020", "2022-12-31"), "C2": ("2023", "2026-12-31")}
for k in ("G6_mkt60", "G4_mom121", "G1_vr5", "G5_adx14"):
    cuts = S[k]["cuts"]; print(f"\n{k} cuts {cuts[0]:.2f}/{cuts[1]:.2f}: ABSOLUTE net per trade (win%) by tercile low/mid/high, EB hold 20")
    for nm, (a, b) in er.items():
        y = A[(A.date >= a) & (A.date <= b)].dropna(subset=[k]); g = np.digitize(y[k], cuts)
        print(f"  {nm:8s}", " | ".join(f"{100*y.net[g==i].mean():+.2f}% ({100*(y.net[g==i]>0).mean():.0f}%, n {int((g==i).sum())})" for i in range(3)))
y = A[A.date >= "2013"].dropna(subset=["G6_mkt60", "pm"])
print("\ncorr(market stretch, market model):", round(y[["G6_mkt60", "pm"]].corr().iloc[0, 1], 2))
cuts = S["G6_mkt60"]["cuts"]
for nm in ("DESIGN", "CONFIRM"):
    a, b = er[nm]; z = y[(y.date >= a) & (y.date <= b)]; g = np.digitize(z.G6_mkt60, cuts)
    for p, lab in ((z.pm > 0, "pm>0 "), (z.pm <= 0, "pm<=0")):
        print(f"  {nm} {lab}:", " | ".join(f"{100*z.net[(g==i)&p].mean():+.2f}% ({100*(z.net[(g==i)&p]>0).mean():.0f}%, n {int(((g==i)&p).sum())})" for i in range(3)))
