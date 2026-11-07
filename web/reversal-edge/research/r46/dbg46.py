src = open("meta46.py").read(); exec(src.split("E2 = {")[0])
Wt = pd.DataFrame(1 / X.shape[1], index=X.index, columns=X.columns)
raw = (Wt * X).sum(1); expo = (Wt * SC * INV).sum(1)
pv = raw.rolling(60, min_periods=40).std().shift(2) * np.sqrt(250)
k = (0.10 / pv).where(pv > 0, 1.0).fillna(1.0); k = np.minimum(k, (1 / expo).where(expo > 0, np.inf))
turn = ((Wt * SC).mul(k, axis=0).diff().abs() * INV).sum(1).fillna(0)
D = pd.DataFrame(dict(k=k, expo=expo, kexpo=k * expo, raw=raw, gain=k * raw, cost=0.002 * turn, cashpart=(1 - k * expo).clip(lower=0) * cash))
for a, b in (("2013", "2019"), ("2020", "2026")):
    d = D.loc[a:b]; print(a, b, "mean k", round(d.k.mean(), 2), "max k", round(d.k.max(), 1), "mean k*expo", round(d.kexpo.mean(), 2),
          "| per yr: gain", round(250 * d.gain.mean() * 100, 1), "cost", round(250 * d.cost.mean() * 100, 1), "cash", round(250 * d.cashpart.mean() * 100, 1))
print(SC.loc["2013":"2019"].describe().round(2).to_string())
print(INV.loc["2013":"2019"].mean().round(2).to_string())
