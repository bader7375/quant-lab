from s_z import *
import pickle
Zs = pickle.load(open("Zs.pkl", "rb"))
ZP, ZR = Zs[("price", 250)], Zs[("relative", 250)]
for kw in (dict(entry=-2.5, exit_z=-1.0, maxhold=60), dict(entry=-2.5, exit_z=-1.0, maxhold=60, ml=.5), dict(entry=-2.5, exit_z=-0.5, maxhold=60), dict(entry=-3.0, exit_z=-1.0, maxhold=60)):
    rep("price-250 " + " ".join(f"{k}={v}" for k, v in kw.items()), ztrades(ZP, **kw))
for kw in (dict(entry=-2.0, exit_z=0.0, maxhold=90, ml=.5), dict(entry=-2.0, exit_z=-0.5, maxhold=60, ml=.5)):
    rep("relative-250 " + " ".join(f"{k}={v}" for k, v in kw.items()), ztrades(ZR, **kw))
# random-entry benchmark with the same holding time distribution (60 days)
rng = np.random.default_rng(0); el = P["elig"]; Of = P["O"].ffill(); out = []
idx = np.argwhere(el.loc["2013":].values); base = np.searchsorted(dates, np.datetime64("2013-01-01"))
for i, j in idx[rng.choice(len(idx), 4000, replace=False)]:
    i += base
    if i + 58 < len(dates): a, b = Of.iloc[i + 1, j], Of.iloc[i + 58, j]; out.append((dates[i], cols[j], b / a - 1 - .004, 57))
rep("RANDOM entries, 57-day hold (benchmark)", pd.DataFrame(out, columns=["date", "sym", "r", "days"]))
