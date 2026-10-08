"""Tadawul-style industry groups (library sector + code ranges), equal-weight leave-one-out sector indices, beta/correlation."""
import json, numpy as np, pandas as pd
META = json.load(open("../tadawul/meta.json")); NEW = json.load(open("../edge26/data/new_codes.json"))
BANKS = {1010, 1020, 1030, 1050, 1060, 1080, 1120, 1140, 1150, 1180}
def industry(code):
    c = int(code); sec = META.get(code, {}).get("sector")
    if c in BANKS: return "Banks"
    if 8000 <= c < 8400: return "Insurance"
    if c in (1111, 1182, 1183) or 4080 <= c <= 4084 or c in (4130, 4280, 2120): return "Diversified Financials"
    if 3000 <= c < 3100: return "Cement"
    if 4330 <= c <= 4350: return "REITs"
    if 7010 <= c <= 7040: return "Telecom"
    if 7200 <= c < 7300: return "Software & IT"
    if c in (2222, 2030, 2380, 2381, 2382, 2223, 4030, 4200) : return "Energy"
    if c in (5110, 2080, 2081, 2082, 2083, 2084): return "Utilities"
    if sec == "Health Care" or (code not in META and 4013 <= c <= 4021): return "Health Care"
    if sec == "Health Care": return "Health Care"
    if sec == "Materials" or 1200 <= c < 1400 or c in (2001, 2010, 2020, 2060, 2170, 2210, 2250, 2290, 2310, 2330, 2350): return "Petrochem & Materials"
    if sec == "Consumer Staples" or 6000 <= c <= 6100 or 2280 <= c <= 2288 or c in (2050, 2270, 2100, 4001, 4061, 4160, 4161, 4162, 4163, 4164): return "Food & Staples"
    if sec == "Real Estate" or 4300 <= c < 4330 or c in (4020, 4090, 4100, 4150, 4220, 4230, 4250): return "Real Estate"
    if sec == "Industrials" or c in (4031, 4040, 4260, 4261, 4262, 4263, 4264, 4265, 4110, 4140, 4141, 4142, 4143, 4144, 4145, 4146, 4147, 4148, 1212, 1213, 1214, 2040, 2110, 2160, 2320, 2360, 2370): return "Industrials & Transport"
    if sec == "Communication Services": return "Media"
    return "Consumer & Retail"
def build(P):
    C = P["C"]; cols = C.columns; G = pd.Series({s: industry(s) for s in cols})
    r = np.log(C).diff().clip(-.25, .25); w = (P["VAL"].rolling(60, min_periods=20).median().shift(1) >= 1e6) & r.notna()
    rw = r.where(w)
    S = {}; LOO = pd.DataFrame(index=C.index, columns=cols, dtype=float)
    for g, members in G.groupby(G).groups.items():
        m = list(members); sm = rw[m].sum(1, min_count=1); cnt = rw[m].notna().sum(1)
        S[g] = (sm / cnt).where(cnt >= 3)
        for s in m:                                            # leave-one-out: sector return without the stock itself
            own = rw[s].fillna(0); c2 = cnt - rw[s].notna().astype(int)
            LOO[s] = ((sm - own) / c2).where(c2 >= 3)
    SI = pd.DataFrame(S)
    return G, r, SI, LOO
if __name__ == "__main__":
    from sim import load
    P = load(); G, r, SI, LOO = build(P)
    print(G.value_counts().to_string())
    cum = np.exp(SI.loc["2013":].fillna(0).cumsum()); print("\nsector index total return 2013-2026:", (cum.iloc[-1] - 1).round(2).to_dict())
    beta = (r.rolling(120, min_periods=80).cov(LOO) / LOO.rolling(120, min_periods=80).var()); corr = r.rolling(120, min_periods=80).corr(LOO)
    last = P["C"].index[-1]; B = pd.DataFrame({"g": G, "beta": beta.loc[last], "corr": corr.loc[last]}).dropna()
    print("\nmedian beta / correlation to own sector (last 120 days):"); print(B.groupby("g")[["beta", "corr"]].median().round(2).to_string())
    pd.to_pickle({"G": G, "SI": SI, "LOO": LOO, "beta": beta, "corr": corr}, "sectors.pkl")
