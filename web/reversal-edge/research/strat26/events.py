from sim import *
P = load(); C, O, V = P["C"], P["O"], P["V"]; dates = C.index; el = P["elig"]
Of = O.ffill(); mkt = (P["Roo"].where(el)).mean(1)                       # EW open-to-open market
cum_m = np.log1p(mkt).cumsum()
def ex_ret(sym, i0, i1):           # buy open of day i0, sell open of day i1 (log, excess of EW market)
    a, b = Of[sym].iloc[i0], Of[sym].iloc[i1]
    if not (a > 0 and b > 0): return np.nan
    return np.log(b / a) - (cum_m.iloc[i1 - 1] - cum_m.iloc[i0 - 1])
def report(nm, ev):
    ev = pd.DataFrame(ev).dropna(); 
    if not len(ev): print(nm, "no events"); return
    for col in [c for c in ev.columns if c.startswith("w")]:
        a = ev[ev.date < "2020"][col]; b = ev[ev.date >= "2020"][col]
        t = lambda x: x.mean() / x.std() * np.sqrt(len(x))
        print(f"  {nm:30s} {col:10s} 2013-19 {100*a.mean():+.2f}% (t {t(a):+.1f}, n {len(a)}) | 2020-26 {100*b.mean():+.2f}% (t {t(b):+.1f}, n {len(b)})")
# --- dividends: ex-date from Yahoo events
ev = []
for f in glob.glob("../edge26/data/div/*.csv"):
    s = os.path.basename(f)[:-4].replace(".SR", "")
    if s not in C.columns: continue
    d = pd.read_csv(f, parse_dates=["date"]); d = d[d.type == "div"]
    for x in d.date:
        i = dates.searchsorted(x)
        if i < 40 or i + 21 >= len(dates) or x < pd.Timestamp("2013-01-01"): continue
        if not el[s].iloc[i - 21]: continue
        ev.append({"date": x, "s": s, "w-20..-1": ex_ret(s, i - 20, i), "w-10..-1": ex_ret(s, i - 10, i), "w-5..-1": ex_ret(s, i - 5, i), "w0..+20": ex_ret(s, i, i + 20)})
print("DIVIDEND EX-DATES (adjusted prices: the dividend itself is included; excess over equal-weight market)"); report("dividend", ev)
# --- news-like events: volume >= 3x 20-day average and close-to-close move (known at close t); trade from open t+1
cc = np.log(C).diff(); vr = V / V.rolling(20, min_periods=15).mean().shift(1); ev = {"up": [], "down": []}
idx = np.argwhere(((vr >= 3) & el & (cc.abs() >= .04)).values)
for i, j in idx:
    if i < 60 or i + 22 >= len(dates) or dates[i] < pd.Timestamp("2013-01-01"): continue
    s = C.columns[j]; side = "up" if cc.iloc[i, j] > 0 else "down"
    ev[side].append({"date": dates[i], "w1..5": ex_ret(s, i + 1, i + 6), "w1..20": ex_ret(s, i + 1, i + 21), "w1..60": ex_ret(s, i + 1, min(i + 61, len(dates) - 1))})
print("VOLUME-SHOCK EVENTS (>=3x volume, |move| >= 4%), bought next open, excess over market"); report("big-volume UP day", ev["up"]); report("big-volume DOWN day", ev["down"])
