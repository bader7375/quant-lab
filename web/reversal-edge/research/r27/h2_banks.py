"""Banks 5-day relative reversal: weekly, buy the banks that lagged the bank median most over the last 5 days."""
from core import *
Pl = library(); 
def bank_sig(P, k=2, look=5, every=5, start="2004-01-01"):
    G = P["G"]; banks = [s for s in P["C"].columns if G[s] == "Banks"]; r = np.log(P["C"][banks]).diff()
    rel = r.rolling(look).sum(); rel = rel.sub(rel.median(1), axis=0).where(P["elig"][banks])
    S = pd.DataFrame(False, index=P["C"].index, columns=P["C"].columns); dts = P["C"].index; i0 = np.searchsorted(dts, np.datetime64(start))
    for i in range(i0, len(dts), every):
        x = rel.iloc[i].dropna()
        if len(x) >= 6: S.loc[dts[i], x.nsmallest(k).index] = True
    return S
for k in (1, 2, 3):
    for h in (5, 10):
        T = pd.concat([events(Pl, bank_sig(Pl, k, 5, h), h, block=False), events(P, bank_sig(P, k, 5, h, "2013-01-01"), h, block=False)])
        res = summ(T, f"banks worst {k} by 5d relative, hold {h}"); log_trial("banks", f"k{k}h{h}", res)
# reference: all banks, same schedule
for h in (5, 10):
    def allb(P, start):
        G = P["G"]; S = pd.DataFrame(False, index=P["C"].index, columns=P["C"].columns); b = [s for s in S.columns if G[s] == "Banks"]; dts = S.index
        for i in range(np.searchsorted(dts, np.datetime64(start)), len(dts), h): S.loc[dts[i], b] = True
        return S
    summ(pd.concat([events(Pl, allb(Pl, "2004-01-01"), h, block=False), events(P, allb(P, "2013-01-01"), h, block=False)]), f"ALL banks same schedule, hold {h}")
