from events import *
raw = {os.path.basename(f)[:-4].replace(".SR", ""): pd.read_csv(f, index_col=0, parse_dates=True) for f in glob.glob("../edge26/data/d/*.csv")}
# 1) is Yahoo's dividend date the ex-date? raw open on that day vs previous raw close should drop by about the dividend
chk = []
DIV = {}
for f in glob.glob("../edge26/data/div/*.csv"):
    s = os.path.basename(f)[:-4].replace(".SR", ""); d = pd.read_csv(f, parse_dates=["date"]); d = d[d.type == "div"]; DIV[s] = d
    if s not in raw: continue
    r = raw[s]
    for _, x in d.iterrows():
        i = r.index.searchsorted(x.date)
        if i < 2 or i >= len(r) - 2 or r.index[i] != x.date: continue
        pc = r.close.iloc[i - 1]; y = float(x.value) / pc
        if y < .01: continue
        chk.append({"y": y, "gap_on": r.open.iloc[i] / pc - 1, "gap_before": r.open.iloc[i - 1] / r.close.iloc[i - 2] - 1, "gap_after": r.open.iloc[i + 1] / r.close.iloc[i] - 1})
K = pd.DataFrame(chk); print(f"dividend yield >= 1% events: {len(K)} | mean yield {100*K.y.mean():.2f}% | raw open gap ON the Yahoo date {100*K.gap_on.mean():+.2f}% | day before {100*K.gap_before.mean():+.2f}% | day after {100*K.gap_after.mean():+.2f}%")
# 2) no look-ahead: anniversary of last year's ex-dates (only info known a year ahead)
ev = []
for s, d in DIV.items():
    if s not in C.columns or len(d) < 2: continue
    for x in d.date:
        a = x + pd.Timedelta(days=364)                           # expected ex-date next year
        if a < pd.Timestamp("2013-01-01") or a > dates[-25]: continue
        i = dates.searchsorted(a)
        if i < 25 or not el[s].iloc[i - 21]: continue
        paid = ((d.date > a - pd.Timedelta(days=45)) & (d.date < a + pd.Timedelta(days=45))).any()
        ev.append({"date": a, "s": s, "paid": paid, "w-20..-1": ex_ret(s, i - 20, i), "w-20..+5": ex_ret(s, i - 20, i + 5), "w-10..+5": ex_ret(s, i - 10, i + 5)})
E = pd.DataFrame(ev); print(f"anniversary events {len(E)}, a dividend really came within 45 days in {100*E.paid.mean():.0f}%")
report("anniversary (no look-ahead)", E.drop(columns=["paid"]))
