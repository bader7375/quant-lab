"""Round 31 indicators (all known at the close of day t): VWAP stretch Z and momentum-gate candidates. Works on the Yahoo and library panels."""
import os, sys
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../r27"))
from base import *

def zc_of(P):
    lc = np.log(P["C"]); r = lc.diff().clip(-.25, .25); sd = r.rolling(60, min_periods=40).std()
    z = [r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]
    return (z[0] + z[1] + z[2]) / 3

def vwap_z(P, parts=False):
    """vz = mean over k = 10, 20, 60 of ln(C / k-day VWAP) / (pre-window daily sd x sqrt((k-1)(2k-1)/(6k)))."""
    C, Hh, L, V = P["C"], P["H"], P["L"], P["V"]
    TP = (Hh + L + C) / 3; Vz = V.where(TP.notna() & (V > 0), 0).fillna(0); TPz = TP.fillna(0)
    r = np.log(C).diff().clip(-.25, .25); sd = r.rolling(60, min_periods=40).std(); out = {}
    for k in (10, 20, 60):
        num = (TPz * Vz).rolling(k, min_periods=int(.8 * k)).sum(); den = Vz.rolling(k, min_periods=int(.8 * k)).sum()
        vw = (num / den).where(den > 0); scale = np.sqrt((k - 1) * (2 * k - 1) / (6 * k))
        out[k] = np.log(C / vw) / (sd.shift(k) * scale)
    vz = (out[10] + out[20] + out[60]) / 3
    return (vz, out) if parts else vz

def adx(P, n=14):
    C, Hh, L = P["C"], P["H"], P["L"]; up = Hh.diff(); dn = -L.diff()
    pdm = up.where((up > dn) & (up > 0), 0.0); mdm = dn.where((dn > up) & (dn > 0), 0.0)
    tr = pd.concat([Hh - L, (Hh - C.shift()).abs(), (L - C.shift()).abs()]).groupby(level=0).max().reindex(C.index)
    w = lambda x: x.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    atr = w(tr); pdi = 100 * w(pdm) / atr; mdi = 100 * w(mdm) / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi); return w(dx)

def gauges(P):
    C = P["C"]; lc = np.log(C); r = lc.diff().clip(-.25, .25); el = P["elig"]; G = {}
    r5 = r.rolling(5, min_periods=5).sum()
    G["G1_vr5"] = (r5.rolling(250, min_periods=200).var() / (5 * r.rolling(250, min_periods=200).var())).shift(20)
    G["G2_ac1"] = r.rolling(250, min_periods=200).corr(r.shift(1)).shift(20)
    G["G3_er60"] = ((lc.shift(10) - lc.shift(70)).abs() / r.abs().rolling(60, min_periods=50).sum().shift(10))
    m121 = lc.shift(21) - lc.shift(252); G["G4_mom121"] = m121.where(el).rank(axis=1, pct=True)
    G["G5_adx14"] = adx(P)
    mr = r.where(el).mean(1); msd = mr.rolling(60, min_periods=40).std()
    mz = mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))
    G["G6_mkt60"] = pd.DataFrame(np.repeat(mz.values[:, None], C.shape[1], 1), index=C.index, columns=C.columns)
    return G
