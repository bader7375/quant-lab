"""H2 calendar: equal-weight market open-to-open return by Hijri/Gregorian calendar condition, per era."""
from base import *
from hijri_converter import convert
Py, Pl = yahoo(), library()
def cal(idx):
    h = [convert.Gregorian(d.year, d.month, d.day).to_hijri() for d in idx]
    D = pd.DataFrame({"hm": [x.month for x in h], "hd": [x.day for x in h]}, index=idx)
    pos = np.arange(len(idx)); D["ramadan"] = D.hm == 9; D["ram_last10"] = (D.hm == 9) & (D.hd >= 20)
    # trading days before Eid al-Fitr / Eid al-Adha holiday: last 5 sessions before the first session after the holiday gap
    pre = np.zeros(len(idx), bool); post = np.zeros(len(idx), bool)
    for m, d0 in ((10, 1), (12, 10)):
        for y in sorted(set(x.year for x in h)):
            try: g = convert.Hijri(y, m, d0).to_gregorian(); g = pd.Timestamp(g.year, g.month, g.day)
            except Exception: continue
            k = np.searchsorted(idx.values, g.to_datetime64())
            if 5 <= k < len(idx) - 5: pre[k - 5:k] = True; post[k:k + 5] = True
    D["pre_eid"] = pre; D["post_eid"] = post; D["hajj_month"] = D.hm == 12; D["muharram"] = D.hm == 1
    D["summer"] = idx.month.isin([6, 7, 8]); D["dec_jan"] = idx.month.isin([12, 1])
    mo = pd.Series(idx.to_period("M"), index=idx); first = ~mo.duplicated(); last = ~mo.duplicated(keep="last")
    tom = first.copy(); 
    for s in (1, 2): tom |= first.shift(-s, fill_value=False)
    tom |= last; D["turn_of_month"] = tom.values
    D["first_day_week"] = pd.Series(idx.dayofweek, index=idx).diff().fillna(1).values < 0     # first session after a weekend
    D["last_day_week"] = np.r_[(np.diff(idx.dayofweek) < 0), False]
    D["q_report"] = idx.month.isin([1, 4, 7, 10]) & (idx.day <= 31)                             # reporting months
    return D
rows = []
for P, eras in ((Pl, ("DEEP",)), (Py, ("DESIGN", "CONFIRM", "C1", "C2"))):
    m = P["Roo"].where(P["elig"]).mean(1).shift(1)          # return earned on day t = open(t) -> open(t+1) for a position decided at close t-1
    D = cal(P["C"].index)
    for k in [c for c in D.columns if c not in ("hm", "hd")]:
        for e in eras:
            a, b = ERAS[e]; x = m.loc[a:b]; f = D[k].loc[a:b].astype(bool)
            i, o = x[f], x[~f]
            if len(i) < 20: continue
            t = (i.mean() - o.mean()) / np.sqrt(i.var() / len(i) + o.var() / len(o))
            rows.append(dict(cond=k, era=e, n=len(i), in_bp=1e4 * i.mean(), out_bp=1e4 * o.mean(), diff_bp=1e4 * (i.mean() - o.mean()), t=t))
R = pd.DataFrame(rows); R.to_csv("h2_cal.csv", index=False)
print(R.pivot(index="cond", columns="era", values="diff_bp").round(1).join(R.pivot(index="cond", columns="era", values="t").round(1), rsuffix="_t")[["DEEP", "DEEP_t", "DESIGN", "DESIGN_t", "CONFIRM", "CONFIRM_t", "C1", "C2"]].to_string())
