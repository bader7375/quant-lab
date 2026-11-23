"""Round 46, engine 3 (PREREG.md): an online-learning portfolio manager. Each strategy in the library is a daily return stream at full
size, scaled to 10% annual volatility with its trailing 60-day volatility; weights follow multiplicative weights (Hedge) on yesterday's
returns with 5% fixed-share mixing toward equal weights; eta chosen on DESIGN. Compared with static Core v2 + Z swing and the
equal-weight library."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0])
os.chdir(R27); from core import sleeve as zsleeve, combine, core as core_w, run, ml_weights; from sim import stats; os.chdir(HERE)
ELd = pd.DataFrame(EL, index=dates, columns=cols); ZSIG = BASE & (PCT >= .5) & ELd
CW = core_w(); V2 = combine(CW["ml"] * .5, CW["trend"])
Mw = ELd.astype(float).div(ELd.sum(1).replace(0, np.nan), axis=0).fillna(0); rm, _ = run(P, Mw, side=0, cash=False); idx = (1 + rm).cumprod()
faber = (idx > idx.rolling(200, min_periods=150).mean()).astype(float)
zexit = (zc >= 0)                                                            # sell when stretch Z is back at 0 (exit_sig of the core sleeve)
LIB = {"Core ML sleeve": CW["ml"], "trend breakouts": CW["trend"], "Z swing hold 40 (5 x 20%)": zsleeve(ZSIG, h=40, N=5, w=.20),
       "Z swing sell at Z=0 (5 x 20%)": zsleeve(ZSIG, h=60, N=5, w=.20, exit_sig=zexit), "market timing (Faber)": Mw.mul(faber, axis=0)}
cf = os.path.join(R27, "preds/CNN46.parquet")
if os.path.exists(cf):
    pr = pd.read_parquet(cf).pivot(index="date", columns="sym", values="pred").reindex(index=dates, columns=cols); LIB["CNN top-10 sleeve"] = ml_weights(pred=pr)
RUN = {k: run(P, W, cash=False) for k, W in LIB.items()}
RS = pd.DataFrame({k: v[0] for k, v in RUN.items()}).loc["2012-06":]; INV = pd.DataFrame({k: v[1] for k, v in RUN.items()}).loc["2012-06":]
cash = P["cash"].reindex(RS.index).fillna(0)
vol = RS.rolling(60, min_periods=40).std().shift(2) * np.sqrt(250); SC = (0.10 / vol).clip(upper=2.0).fillna(0)   # vol-target each stream, at most 2x
RS["cash"], INV["cash"], SC["cash"] = cash, 0.0, 1.0                          # cash is a library member (PREREG), never scaled
X = RS * SC                                                                   # vol-scaled daily returns (stock part; idle money of a stream earns 0 here)
SIDE = 0.002
def portfolio(Wt):
    """Wt: weights per day (rows sum to 1) on the vol-scaled streams. Portfolio scaled to 10% volatility with its trailing 60-day volatility,
    at most 100% in stocks; money not in stocks earns cash. Moving money between streams pays 0.20% per side on the change in stock exposure."""
    raw = (Wt * X).sum(1); expo = (Wt * SC * INV).sum(1)                     # return and stock exposure per unit of the mix
    pv = raw.rolling(60, min_periods=40).std().shift(2) * np.sqrt(250)
    k = (0.10 / pv).where(pv > 0, 1.0).fillna(1.0); k = np.minimum(k, (1 / expo).where(expo > 0, np.inf))
    turn = ((Wt * SC).mul(k, axis=0).diff().abs() * INV).sum(1).fillna(0)   # resizing held positions (a stream's own trades are costed in run)
    return k * raw + (1 - k * expo).clip(lower=0) * cash - SIDE * turn
def hedge(eta, alpha=.05):
    K = X.shape[1]; w = np.full(K, 1 / K); out = np.zeros_like(X.values); xv = X.fillna(0).values
    for t in range(len(X)):
        out[t] = w
        w = w * np.exp(eta * xv[t]); w = w / w.sum(); w = (1 - alpha) * w + alpha / K
    return pd.DataFrame(out, index=X.index, columns=X.columns).shift(1).fillna(1 / K)   # one extra day of delay: weights use returns known by the previous open
E2 = {"DESIGN 2013-19": ("2013", "2019-12-31"), "CONFIRM 2020-26": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
def st(r): return {e: stats(r, a, b) for e, (a, b) in E2.items()}
def fmt(s): return " | ".join(f"{e[:7]} CAGR {100 * v['cagr']:+5.1f}% Sh {v['sharpe']:.2f} DD {100 * v['maxdd']:4.0f}%" for e, v in s.items())
R = {}
for k in LIB: R[f"[library] {k}"] = st(RS[k] + 0)
ZS = zsleeve(ZSIG, h=40, N=5, w=.05); room = (1 - ZS.sum(1)).clip(0, 1)
static = ZS.add(V2.mul(room / V2.sum(1).clip(lower=1), axis=0), fill_value=0); R["static Core v2 + Z swing (5 x 5%)"] = st(run(P, static)[0].loc["2012-06":])
R["Core v2 alone"] = st(run(P, V2)[0].loc["2012-06":])
EQ = pd.DataFrame(1 / X.shape[1], index=X.index, columns=X.columns); R["equal-weight library (vol-scaled)"] = st(portfolio(EQ))
best_eta, best_sh = None, -9
for eta in (2, 5, 10, 20):
    Wt = hedge(eta); s = st(portfolio(Wt)); R[f"AI manager (Hedge, eta {eta})"] = s
    if s["DESIGN 2013-19"]["sharpe"] > best_sh: best_eta, best_sh = eta, s["DESIGN 2013-19"]["sharpe"]
for k, s in R.items(): print(f"{k:42s} {fmt(s)}")
pick = R[f"AI manager (Hedge, eta {best_eta})"]; base1, base2 = R["static Core v2 + Z swing (5 x 5%)"], R["equal-weight library (vol-scaled)"]
ok = all(pick[e]["sharpe"] > base1[e]["sharpe"] and pick[e]["sharpe"] > base2[e]["sharpe"] for e in ("DESIGN 2013-19", "CONFIRM 2020-26"))
Wb = hedge(best_eta); avgw = Wb.groupby(Wb.index.year).mean().round(2)
print(f"\nDESIGN pick eta = {best_eta}; DECISION AI manager adopted: {ok}")
print("Average weight by year (eta pick):"); print(avgw.loc[2013:].to_string())
json.dump({"res": R, "eta": best_eta, "adopted": bool(ok), "weights_by_year": avgw.to_dict()}, open(os.path.join(HERE, "meta46_results.json"), "w"), indent=1, default=float)
