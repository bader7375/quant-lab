"""Round 32: VWAP Z with quarterly / yearly windows (rolling or calendar-anchored), normalised by volatility, VWAP sd or ATR (see PREREG.md)."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("../r28", "../r27", "../r31"): sys.path.insert(0, os.path.join(HERE, p))
os.chdir(os.path.join(HERE, "../r27"))
from core import P, C, dates, cols, PCT, pm, ATR
from sim28 import trades, stats
from base import library
os.chdir(HERE)
ERAS = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "C1": ("2020", "2022-12-31"), "C2": ("2023", "2026-12-31"), "DEEP": ("2004", "2012-12-31")}
first = lambda x: x & ~x.shift(1, fill_value=False)
def atr20(Pn):
    tr = pd.concat([Pn["H"] - Pn["L"], (Pn["H"] - Pn["C"].shift()).abs(), (Pn["L"] - Pn["C"].shift()).abs()]).groupby(level=0).max().reindex(Pn["C"].index)
    return tr.rolling(20, min_periods=15).mean()
def ms_of(Pn):
    r = np.log(Pn["C"]).diff().clip(-.25, .25); mr = r.where(Pn["elig"]).mean(1); msd = mr.rolling(60, min_periods=40).std()
    return mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))
def variants(Pn):
    Cn, Hn, Ln, Vn = Pn["C"], Pn["H"], Pn["L"], Pn["V"]; idx = Cn.index
    TP = (Hn + Ln + Cn) / 3; ok = TP.notna() & (Vn > 0); Vz = Vn.where(ok, 0).fillna(0); TPz = TP.where(ok, 0).fillna(0)
    r = np.log(Cn).diff().clip(-.25, .25); sd = r.rolling(60, min_periods=40).std(); A = atr20(Pn)
    def norms(vw, sig, k, sdpre):
        sc = np.sqrt((k - 1) * (2 * k - 1) / (6 * k))
        return {"vol": np.log(Cn / vw) / (sdpre * sc), "sd": (Cn - vw) / sig.where(sig > 1e-9), "atr": (Cn - vw) / A}
    base = {}
    for w, k in (("Q", 63), ("Y", 250)):
        mp = int(.8 * k); s1 = (TPz * Vz).rolling(k, min_periods=mp).sum(); s0 = Vz.rolling(k, min_periods=mp).sum(); s2 = (TPz * TPz * Vz).rolling(k, min_periods=mp).sum()
        vw = (s1 / s0).where(s0 > 0); sig = np.sqrt((s2 / s0 - vw ** 2).clip(lower=0)); base[("roll", w)] = norms(vw, sig, float(k), sd.shift(k))
    for w, f, mb in (("Q", "Q", 10), ("Y", "Y", 20)):
        key = idx.to_period(f); s1 = (TPz * Vz).groupby(key).cumsum(); s0 = Vz.groupby(key).cumsum(); s2 = (TPz * TPz * Vz).groupby(key).cumsum()
        n = ok.astype(float).groupby(key).cumsum(); vw = (s1 / s0).where((s0 > 0) & (n >= mb)); sig = np.sqrt((s2 / s0 - vw ** 2).clip(lower=0))
        sdA = sd.shift(1).groupby(key).transform("first"); base[("anch", w)] = norms(vw, sig, n.where(n >= mb), sdA)
    V = {}
    for a in ("roll", "anch"):
        for nm in ("vol", "sd", "atr"):
            q, y = base[(a, "Q")][nm], base[(a, "Y")][nm]
            V[f"{a}-Q-{nm}"] = q; V[f"{a}-Y-{nm}"] = y; V[f"{a}-QY-{nm}"] = (q + y) / 2
    return V
P["liq"] = P["VAL"].rolling(60, min_periods=20).median() >= 3e6; el = P["elig"] & P["liq"]
L_ = library(); L_["liq"] = L_["VAL"].rolling(60, min_periods=20).median() >= 3e6; ATRL = atr20(L_)
F = pd.read_pickle("../r27/F27y.pkl"); zc = F["zc"].reindex(index=dates, columns=cols)
from feat31 import zc_of
zcl = zc_of(L_)
bc = lambda s, cc: pd.DataFrame(np.repeat(s.values[:, None], len(cc), 1), index=s.index, columns=cc)
GATE = (PCT >= .5) & bc(pm > 0, cols) & bc(ms_of(P) <= -1.18, cols)
V = variants(P); VL = variants(L_)
def row(nm, z, zl, line_):
    o = {"variant": nm, "line": round(line_, 3)}
    T = trades(P, ATR, first(z <= line_) & GATE, "X2 hold40"); Tp = trades(P, ATR, first(z <= line_), "X2 hold40"); Td = trades(L_, ATRL, first(zl <= line_), "X2 hold40")
    for e in ("DESIGN", "CONFIRM", "C1", "C2"):
        s = stats(T, *ERAS[e]) or {}; o[f"{e}_n"] = s.get("n", 0); o[f"{e}_peryr"] = round(s.get("per_yr", 0), 1); o[f"{e}_win"] = s.get("win", np.nan); o[f"{e}_exp"] = s.get("exp", np.nan)
        o[f"{e}_avgw"] = s.get("avg_win", np.nan); o[f"{e}_avgl"] = s.get("avg_loss", np.nan)
    for e in ("DESIGN", "CONFIRM"):
        s = stats(Tp, *ERAS[e]) or {}; o[f"po_{e}_win"] = s.get("win", np.nan); o[f"po_{e}_exp"] = s.get("exp", np.nan)
    s = stats(Td, *ERAS["DEEP"]) or {}; o["po_DEEP_n"] = s.get("n", 0); o["po_DEEP_win"] = s.get("win", np.nan); o["po_DEEP_exp"] = s.get("exp", np.nan)
    d = pd.concat([z.where(el).loc["2013":"2019"].stack().rename("v"), zc.where(el).loc["2013":"2019"].stack().rename("z")], axis=1).dropna()
    o["corr_zc"] = round(float(d.corr().iloc[0, 1]), 2); return o
rows = [row("stretch Z (reference)", zc, zcl, -2.62)]
for nm, z in V.items():
    q = float(z.where(el).loc["2013":"2019"].stack().quantile(.02)); rows.append(row(nm, z, VL[nm], q))
R = pd.DataFrame(rows); R.to_csv("vq_grid.csv", index=False)
pd.set_option("display.width", 260)
show = R[["variant", "line", "corr_zc", "DESIGN_peryr", "DESIGN_win", "DESIGN_exp", "CONFIRM_win", "CONFIRM_exp", "C1_exp", "C2_win", "C2_exp", "po_DESIGN_exp", "po_CONFIRM_exp", "po_DEEP_win", "po_DEEP_exp"]].copy()
for c in show.columns:
    if c.endswith("_win") or c.endswith("_exp"): show[c] = (100 * show[c]).round(1)
print(show.to_string(index=False))
ref = R.iloc[0]; cand = R.iloc[1:]; ok = cand[(cand.DESIGN_peryr >= 20) & (cand.DESIGN_win >= .6)]
sel = ok.loc[ok.DESIGN_exp.idxmax()] if len(ok) else None
print("\nSELECTED on DESIGN:", None if sel is None else sel.variant)
if sel is not None:
    a = sel.DESIGN_exp > ref.DESIGN_exp; b = sel.CONFIRM_exp >= ref.CONFIRM_exp and sel.CONFIRM_win >= ref.CONFIRM_win; c = sel.po_DEEP_exp >= ref.po_DEEP_exp
    print(f"(a) beats stretch Z on DESIGN expectancy: {a} ({100 * sel.DESIGN_exp:+.1f}% vs {100 * ref.DESIGN_exp:+.1f}%)")
    print(f"(b) not worse on CONFIRM: {b} (exp {100 * sel.CONFIRM_exp:+.1f}% vs {100 * ref.CONFIRM_exp:+.1f}%, win {100 * sel.CONFIRM_win:.0f}% vs {100 * ref.CONFIRM_win:.0f}%)")
    print(f"(c) DEEP price-only not below stretch Z: {c} ({100 * sel.po_DEEP_exp:+.1f}% vs {100 * ref.po_DEEP_exp:+.1f}%)")
    print("ADOPT AS TRIGGER:", bool(a and b and c))
    z = V[sel.variant]; zl = VL[sel.variant]; q10 = float(z.where(el).loc["2013":"2019"].stack().quantile(.10))
    base = first(zc <= -2.62) & GATE; Tb = trades(P, ATR, base, "X2 hold40"); Tf = trades(P, ATR, base & (z <= q10), "X2 hold40"); Tr = trades(P, ATR, base & ~(z <= q10), "X2 hold40")
    bd = first(zcl <= -2.62); Dd = trades(L_, ATRL, bd, "X2 hold40"); Df = trades(L_, ATRL, bd & (zl <= q10), "X2 hold40")
    print(f"\nFILTER: Z swing where {sel.variant} <= its 10% line ({q10:.2f})")
    res = []
    for e in ("DESIGN", "CONFIRM", "C1", "C2"):
        sb, sf, sr = stats(Tb, *ERAS[e]), stats(Tf, *ERAS[e]), stats(Tr, *ERAS[e])
        print(f"  {e:8s} all n {sb['n']} win {100 * sb['win']:.0f}% exp {100 * sb['exp']:+.1f}% | filtered n {sf['n'] if sf else 0} " + (f"win {100 * sf['win']:.0f}% exp {100 * sf['exp']:+.1f}%" if sf else "") +
              (f" | rest n {sr['n']} win {100 * sr['win']:.0f}% exp {100 * sr['exp']:+.1f}%" if sr else " | rest n<10"))
        if e in ("DESIGN", "CONFIRM"): res.append(bool(sf and sf["exp"] > sb["exp"] and sf["n"] >= .5 * sb["n"]))
    sb, sf = stats(Dd, *ERAS["DEEP"]), stats(Df, *ERAS["DEEP"])
    print(f"  DEEP price-only all n {sb['n']} exp {100 * sb['exp']:+.1f}% | filtered n {sf['n'] if sf else 0} exp {100 * sf['exp']:+.1f}%" if sf else "  DEEP filtered n<10")
    res.append(bool(sf and sf["exp"] > sb["exp"] and sf["n"] >= .5 * sb["n"])); print("ADOPT AS FILTER:", all(res))
pd.to_pickle({k: V[k] for k in V}, "vq_variants.pkl")
