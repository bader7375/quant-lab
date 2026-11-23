"""Round 46, engine 2 (PREREG.md): a 1D convolutional network reads the last 60 sessions of each Saudi stock (open/high/low/close vs today's
close in volatility units, volume vs its window mean, the market's path) and ranks stocks by their next 20 sessions. Yearly walk-forward
retraining, 3-seed ensemble; compared with the current ML ranker (M0) as the Core ML sleeve and as the Z-swing filter."""
import os, sys, json, time, math, numpy as np, pandas as pd, torch, torch.nn as nn, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0])
os.chdir(R27); from core import ml_weights, run, PRED; from sim import stats; os.chdir(HERE)
torch.set_num_threads(3); W = 60
# ---------------------------------------------------------------- inputs
Cf = C.ffill(); lC = np.log(Cf.values)
def lfill(X): return np.log(X.where(X > 0).fillna(Cf).values)
lO, lH, lL = lfill(P["O"]), lfill(P["H"]), lfill(P["L"])
lV = np.log1p(P["V"].fillna(0).values)
r = np.log(Cf).diff().clip(-.25, .25); sd = r.rolling(60, min_periods=40).std().values
mr = r.where(pd.DataFrame(EL, index=dates, columns=cols)).mean(1).fillna(0); mcum = mr.cumsum().values; msd = mr.rolling(60, min_periods=40).std().values
Of = P["Of"].values; T_, N_ = Of.shape
fwd = np.full((T_, N_), np.nan); fwd[:T_ - 21] = Of[21:] / Of[1:T_ - 20] - 1; fwd = np.where(EL & np.isfinite(fwd), fwd, np.nan)
yrank = pd.DataFrame(fwd).rank(axis=1, pct=True).values - .5
def day_batch(i):
    """(x, j) for the liquid stocks of day i with a full window."""
    js = np.where(EL[i] & np.isfinite(sd[i]) & (sd[i] > 0) & np.isfinite(lC[i]))[0]
    if i < W or len(js) == 0 or not np.isfinite(msd[i]) or msd[i] <= 0: return None, js[:0]
    sl = slice(i - W + 1, i + 1); base = lC[i, js]; s = sd[i, js] * math.sqrt(W)
    ch = [(X[sl][:, js] - base) / s for X in (lO, lH, lL, lC)]
    v = lV[sl][:, js]; ch.append(np.clip(v - v.mean(0), -3, 3))
    ch.append(np.repeat(((mcum[sl] - mcum[i]) / (msd[i] * math.sqrt(W)))[:, None], len(js), 1))
    x = np.stack(ch, 0).transpose(2, 0, 1).astype(np.float32)               # (stocks, 6, 60)
    ok = np.isfinite(x).all(axis=(1, 2)); return np.clip(x[ok], -10, 10), js[ok]
class Net(nn.Module):
    def __init__(s):
        super().__init__()
        s.f = nn.Sequential(nn.Conv1d(6, 32, 5, padding=2), nn.BatchNorm1d(32), nn.LeakyReLU(), nn.MaxPool1d(2),
                            nn.Conv1d(32, 64, 5, padding=2), nn.BatchNorm1d(64), nn.LeakyReLU(), nn.MaxPool1d(2),
                            nn.Conv1d(64, 64, 3, padding=1), nn.BatchNorm1d(64), nn.LeakyReLU(), nn.AdaptiveAvgPool1d(1), nn.Flatten(), nn.Dropout(.3), nn.Linear(64, 1))
    def forward(s, x): return s.f(x).squeeze(-1)
def collect(days, with_y=True):
    X, Y, I, J = [], [], [], []
    for i in days:
        x, js = day_batch(i)
        if x is None or len(js) == 0: continue
        if with_y:
            y = yrank[i, js]; ok = np.isfinite(y); x, js, y = x[ok], js[ok], y[ok]; Y.append(y.astype(np.float32))
        X.append(x); I.append(np.full(len(js), i)); J.append(js)
    if not X: return None
    return np.concatenate(X), (np.concatenate(Y) if with_y else None), np.concatenate(I), np.concatenate(J)
start = int(np.searchsorted(dates, np.datetime64("2011-01-01"))); preds = []; t0 = time.time(); LOG = []
for Y in range(2013, 2027):
    a = int(np.searchsorted(dates, np.datetime64(f"{Y}-01-01"))); b = int(np.searchsorted(dates, np.datetime64(f"{Y + 1}-01-01")))
    if a >= T_: break
    cut = a - 22; tr = collect(range(start, cut, 2))
    Xtr, Ytr = torch.from_numpy(tr[0]), torch.from_numpy(tr[1]); te = collect(range(a, min(b, T_)), with_y=False)
    if te is None: continue
    Xte = torch.from_numpy(te[0]); out = np.zeros(len(Xte))
    for seed in range(3):
        torch.manual_seed(seed); net = Net(); opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4); n = len(Xtr)
        for ep in range(3):
            net.train(); perm = torch.randperm(n)
            for k in range(0, n, 512):
                idx = perm[k:k + 512]; opt.zero_grad(); loss = ((net(Xtr[idx]) - Ytr[idx]) ** 2).mean(); loss.backward(); opt.step()
        net.eval()
        with torch.no_grad(): out += np.concatenate([net(Xte[k:k + 4096]).numpy() for k in range(0, len(Xte), 4096)]) / 3
    p = pd.DataFrame({"date": dates[te[2]], "sym": cols[te[3]], "pred": out}); preds.append(p)
    f = fwd[te[2], te[3]]; d = p.assign(f=f).dropna(subset=["f"])
    ic = d.groupby("date").apply(lambda g: g.pred.corr(g.f, method="spearman") if len(g) >= 20 else np.nan).mean()
    LOG.append((Y, len(Xtr), float(ic))); print(f"{Y}: trained on {len(Xtr)} samples, predicted {len(Xte)}; IC {ic:+.4f}; {time.time() - t0:.0f}s", flush=True)
PR = pd.concat(preds); PR.to_parquet(os.path.join(R27, "preds/CNN46.parquet"))
CNN = PR.pivot(index="date", columns="sym", values="pred").reindex(index=dates, columns=cols)
# ---------------------------------------------------------------- evaluation
ic_y = pd.Series({y: ic for y, _, ic in LOG}); E2 = {"DESIGN 2013-19": ("2013", "2019-12-31"), "CONFIRM 2020-26": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
m0 = PRED.reindex(index=dates, columns=cols)
def mic(pred):
    out = {}
    for y in range(2013, 2027):
        a, b = np.searchsorted(dates, np.datetime64(f"{y}-01-01")), np.searchsorted(dates, np.datetime64(f"{y + 1}-01-01")); vals = []
        for i in range(a, min(b, T_ - 21), 5):
            pv = pred.values[i]; ok = np.isfinite(pv) & np.isfinite(fwd[i])
            if ok.sum() >= 20: vals.append(pd.Series(pv[ok]).corr(pd.Series(fwd[i][ok]), method="spearman"))
        out[y] = float(np.nanmean(vals)) if vals else np.nan
    return pd.Series(out)
avg = (CNN.rank(axis=1, pct=True) + m0.rank(axis=1, pct=True)) / 2
ICS = {"CNN": mic(CNN), "M0 (current ML)": mic(m0), "average of both": mic(avg)}
print("\nIC by year (every 5th day):"); print(pd.DataFrame(ICS).round(3).to_string())
RES = {}
for nm, pr in (("M0 (current ML)", m0), ("CNN", CNN), ("average of both", avg)):
    rr, inv = run(P, ml_weights(pred=pr)); RES[nm] = {e: stats(rr, a, b) for e, (a, b) in E2.items()}
    print(f"Core ML sleeve with {nm:16s}: " + " | ".join(f"{e[:7]} CAGR {100 * v['cagr']:+5.1f}% Sh {v['sharpe']:.2f} DD {100 * v['maxdd']:4.0f}%" for e, v in RES[nm].items()), flush=True)
# Z swing filtered by CNN rank instead of M0 rank
sys.path.insert(0, os.path.join(SP, "r41")); from sim41 import trades, sleeve, era, fmt
M = dict(Of=Of.astype(float), O=P["O"].values.astype(float), L=P["L"].values.astype(float), Cf=Cf.values.astype(float), Z=zc.values.astype(float))
cnn_pct = CNN.rank(axis=1, pct=True); ZR = {}
for nm, pc in (("Z swing, M0 rank >= 0.5 (live)", PCT), ("Z swing, CNN rank >= 0.5", cnn_pct)):
    T = trades((BASE & (pc >= .5)).values & EL, M); T = T[dates[T.i.values] >= pd.Timestamp("2013")].reset_index(drop=True)
    T, cv = sleeve(T, np.nan_to_num(pc.values, nan=-1.0), np.full(len(T), .05), M, T_); ZR[nm] = {e: era(T, cv, dates, a, b) for e, (a, b) in E2.items()}
    print(f"{nm:32s} " + " || ".join(f"{e[:7]} {fmt(v)}" for e, v in ZR[nm].items()))
m0s, cs, av = RES["M0 (current ML)"], RES["CNN"], RES["average of both"]
icok = all(ICS["CNN"].loc[a_:b_].mean() > 0 for a_, b_ in ((2013, 2019), (2020, 2026)))
ok_c = icok and all(cs[e]["sharpe"] > m0s[e]["sharpe"] for e in ("DESIGN 2013-19", "CONFIRM 2020-26"))
ok_a = icok and all(av[e]["sharpe"] > m0s[e]["sharpe"] for e in ("DESIGN 2013-19", "CONFIRM 2020-26"))
print(f"\nDECISION CNN replaces M0: {ok_c} | average of CNN and M0 replaces M0: {ok_a} (CNN mean IC > 0 in both eras: {icok})")
json.dump({"ic": {k: v.to_dict() for k, v in ICS.items()}, "core_ml": RES, "zswing": ZR, "cnn_adopt": bool(ok_c), "avg_adopt": bool(ok_a)}, open(os.path.join(HERE, "cnn46_results.json"), "w"), indent=1, default=float)
