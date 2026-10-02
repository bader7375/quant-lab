"""Final feature set + strategy-consistent label, walk-forward check, and the research prior exported for the browser engine.
Feature definitions here are mirrored exactly in engine.js (buildRev)."""
import json
import warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from feats import load_universe, features, load, RD

warnings.filterwarnings("ignore")
data, vix = load_universe()

FEATS = ["oversold_rsi2", "down_streak", "drop1_atr", "drop5_atr", "stretch_z20", "own_rank", "near_low20",
         "rel_volume", "range_expansion", "lower_wick", "weak_close", "gap_size", "trend200", "vol_rank", "vol_term",
         "fear_rank", "fear_change", "stretch_x_fear", "stretch_x_volume"]


def oriented(F, s):
    O = pd.DataFrame(index=F.index)
    O["oversold_rsi2"] = s * (50 - F.rsi2) / 50
    O["down_streak"] = (-s * F.streak).clip(-10, 10)
    O["drop1_atr"] = -s * F.ret1_atr
    O["drop5_atr"] = -s * F.ret5_atr
    O["stretch_z20"] = -s * F.z20
    O["own_rank"] = (1 - F.z20_pct) if s > 0 else F.z20_pct
    O["near_low20"] = -(F.dist_low20 if s > 0 else F.dist_high20)
    O["rel_volume"] = F.vol_z
    O["range_expansion"] = F.range_exp
    O["lower_wick"] = F.lower_wick if s > 0 else F.upper_wick
    O["weak_close"] = s * (0.5 - F.ibs) * 2
    O["gap_size"] = F.gap_atr.abs()
    O["trend200"] = s * F.trend200
    O["vol_rank"] = F.vol_pct
    O["vol_term"] = F.vol_term
    O["fear_rank"] = F.vix_pct
    O["fear_change"] = F.vix_chg5
    O["stretch_x_fear"] = O.stretch_z20.clip(lower=0) * (F.vix_pct - .5)
    O["stretch_x_volume"] = O.stretch_z20.clip(lower=0) * F.vol_z
    return O


def label(df, F, s, maxhold=10, stop_atr=3.0, cost=0.001):
    """Enter next open; exit at first close beyond the 5-day average (in the trade's favour), a 3-ATR stop, or after maxhold bars."""
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    sma5 = df.close.rolling(5).mean().to_numpy()
    atr = (F.atr_pct * df.close).to_numpy()
    n = len(df)
    y = np.full(n, np.nan); ret = np.full(n, np.nan); hold = np.full(n, np.nan)
    for t in range(n - 2):
        if not np.isfinite(atr[t]):
            continue
        e = o[t + 1]; st = e - s * stop_atr * atr[t]; x = None
        for j in range(t + 1, min(n, t + 1 + maxhold)):
            if (s > 0 and l[j] <= st) or (s < 0 and h[j] >= st):
                x = (min(o[j], st) if s > 0 else max(o[j], st)) if j > t + 1 else st; break
            if (s > 0 and c[j] > sma5[j]) or (s < 0 and c[j] < sma5[j]) or j == t + maxhold:
                x = c[j]; break
        if x is None:
            continue
        r = s * np.log(x / e) - cost
        ret[t] = r; y[t] = float(r > 0); hold[t] = j - t
    return y, ret, hold


def candidates(F, s):
    return ((F.rsi2 < 15) | (F.streak <= -2) | (F.z20 <= -1) | (F.ret1_atr <= -1)) if s > 0 else ((F.rsi2 > 85) | (F.streak >= 2) | (F.z20 >= 1) | (F.ret1_atr >= 1))


def panel(s):
    rows = []
    for k, d in data.items():
        F = features(d, None, vix)
        O = oriented(F, s)
        O["y"], O["ret"], O["hold"] = label(d, F, s)
        O["cand"] = candidates(F, s)
        O["sym"] = k
        rows.append(O.iloc[260:])
    return pd.concat(rows)


def scale_fit(X):
    med = X.median(); iqr = (X.quantile(.75) - X.quantile(.25)).replace(0, 1)
    return med, iqr


if __name__ == "__main__":
    prior = {}
    for s, nm in ((1, "long"), (-1, "short")):
        Pn = panel(s)
        E = Pn[Pn.cand].dropna(subset=["y"])
        print(f"\n== {nm}: {len(E)} candidate events, base win rate {E.y.mean():.3f}, avg trade {1e4*E.ret.mean():.1f} bp, avg hold {E.hold.mean():.1f} bars")
        # walk-forward by year
        aucs, tops, alls, bots = [], [], [], []
        for yv in (2015, 2016, 2017):
            tr = E[E.index < pd.Timestamp(f"{yv}-01-01") - pd.Timedelta(days=15)]; te = E[E.index.year == yv]
            med, iqr = scale_fit(tr[FEATS]); Z = lambda d: ((d[FEATS] - med) / iqr).clip(-5, 5).fillna(0)
            m = LogisticRegression(C=.05, max_iter=500).fit(Z(tr), tr.y)
            p = m.predict_proba(Z(te))[:, 1]
            q80, q20 = np.quantile(p, .8), np.quantile(p, .2)
            aucs.append(roc_auc_score(te.y, p)); tops.append(te.ret[p >= q80].mean()); bots.append(te.ret[p <= q20].mean()); alls.append(te.ret.mean())
            print(f"  {yv}: AUC {aucs[-1]:.3f} · avg trade all {1e4*alls[-1]:.0f} bp · top20% {1e4*tops[-1]:.0f} bp · bottom20% {1e4*bots[-1]:.0f} bp")
        # prior: fit on everything
        med, iqr = scale_fit(E[FEATS]); Z = ((E[FEATS] - med) / iqr).clip(-5, 5).fillna(0)
        m = LogisticRegression(C=.05, max_iter=1000).fit(Z, E.y)
        prior[nm] = {"features": FEATS, "coef": dict(zip(FEATS, np.round(m.coef_[0], 4))), "intercept": round(float(m.intercept_[0]), 4),
                     "base_rate": round(float(E.y.mean()), 4), "n": int(len(E))}
        print("  prior weights:", {k: round(v, 3) for k, v in sorted(prior[nm]["coef"].items(), key=lambda kv: -abs(kv[1]))})
        # univariate evidence per sign (for display): avg trade & hit when sign present
    json.dump(prior, open("prior.json", "w"), indent=1, default=float)
    # TSLA out-of-sample check with the prior only (no TSLA training)
    T = load(RD / "TSLA_long.csv"); F = features(T, None, vix); O = oriented(F, 1); O["y"], O["ret"], O["hold"] = label(T, F, 1); O["cand"] = candidates(F, 1)
    E = O[O.cand & (O.index > "2011-06-01")].dropna(subset=["y"])
    Pn = panel(1); Ep = Pn[Pn.cand].dropna(subset=["y"]); med, iqr = scale_fit(Ep[FEATS])
    Z = ((E[FEATS] - med) / iqr).clip(-5, 5).fillna(0)
    c = np.array([prior["long"]["coef"][f] for f in FEATS]); p = 1 / (1 + np.exp(-(Z.to_numpy() @ c + prior["long"]["intercept"])))
    E = E.assign(p=p)
    for yr0, yr1 in (("2011", "2017"), ("2018", "2026")):
        S = E[(E.index >= yr0) & (E.index <= yr1 + "-12-31")]
        q = S.p.quantile(.7)
        print(f"TSLA {yr0}-{yr1}: AUC {roc_auc_score(S.y, S.p):.3f} · candidates {len(S)} avg {1e4*S.ret.mean():.0f} bp win {S.y.mean():.2f} · top30% {1e4*S.ret[S.p>=q].mean():.0f} bp win {S.y[S.p>=q].mean():.2f} · rest {1e4*S.ret[S.p<q].mean():.0f} bp")
    json.dump({"med": med.round(5).to_dict(), "iqr": iqr.round(5).to_dict()}, open("prior_scale.json", "w"), indent=1)
