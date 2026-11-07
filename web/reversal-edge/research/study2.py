"""Study 2: walk-forward pooled reversal-probability models. Separate long (after drops) and short (after rises) models."""
import warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
import lightgbm as lgb

warnings.filterwarnings("ignore")
P = pd.read_pickle("/tmp/claude-0/panel.pkl")
T = pd.read_pickle("/tmp/claude-0/tsla.pkl")
T = T[T.index > "2011-06-01"]
COST = 0.0010  # 10 bp round trip


def oriented(df, side):
    """Features oriented so that positive = more stretched against the trade (the reversal side)."""
    s = side  # +1 long after drop, -1 short after rise
    O = pd.DataFrame(index=df.index)
    O["stretch_z20"] = -s * df.z20
    O["stretch_z10"] = -s * df.z10
    O["stretch_z50"] = -s * df.z50
    O["own_pct"] = (1 - df.z20_pct) if s > 0 else df.z20_pct
    O["rsi2"] = (50 - df.rsi2) * s / 50
    O["rsi14"] = (50 - df.rsi14) * s / 50
    O["streak"] = -s * df.streak
    O["ret5_atr"] = -s * df.ret5_atr
    O["ret1_atr"] = -s * df.ret1_atr
    O["dist_ext20"] = -(df.dist_low20 if s > 0 else df.dist_high20)
    O["ibs_weak"] = (0.5 - df.ibs) * s * 2          # close near the extreme of the move
    O["vol_z"] = df.vol_z
    O["range_exp"] = df.range_exp
    O["wick_rev"] = df.lower_wick if s > 0 else df.upper_wick
    O["gap_abs"] = df.gap_atr.abs()
    O["gap_with"] = -s * df.gap_atr                    # gap in the direction of the move
    O["trend200"] = s * df.trend200                    # with-trend for the trade
    O["slope50"] = s * df.slope50
    O["acf1"] = df.acf1_60
    O["vol_pct"] = df.vol_pct
    O["vol_term"] = df.vol_term
    O["vov"] = df.vov
    O["vix_pct"] = df.vix_pct
    O["vix_chg5"] = df.vix_chg5
    if "mkt_ret5" in df:
        O["mkt_move"] = -s * df.mkt_ret5 / df.yz20 * np.sqrt(252 / 5)
        O["resid5"] = -s * df.resid5
    O["stretch_x_volz"] = O.stretch_z20.clip(0) * df.vol_z
    O["stretch_x_vix"] = O.stretch_z20.clip(0) * (df.vix_pct - .5)
    O["stretch_x_volpct"] = O.stretch_z20.clip(0) * (df.vol_pct - .5)
    O["y_ret5"] = s * df.fwd5
    O["y_ret3"] = s * df.fwd3
    O["y_ret1"] = s * df.fwd1
    O["sym"] = df.sym
    return O


SETS = {
    "A stretch only": ["stretch_z20", "stretch_z10", "stretch_z50", "own_pct", "rsi2", "rsi14", "streak", "ret5_atr", "ret1_atr", "dist_ext20", "ibs_weak"],
}
SETS["B + reversal signs"] = SETS["A stretch only"] + ["vol_z", "range_exp", "wick_rev", "gap_abs", "gap_with", "stretch_x_volz"]
SETS["C + regime & volatility"] = SETS["B + reversal signs"] + ["trend200", "slope50", "acf1", "vol_pct", "vol_term", "vov", "stretch_x_volpct"]
SETS["D + fear (VIX) & market"] = SETS["C + regime & volatility"] + ["vix_pct", "vix_chg5", "stretch_x_vix"]
MKT = ["mkt_move", "resid5"]


def events(O):
    return O[(O.stretch_z20 >= 1) | (O.rsi2 >= 0.8) | (O.streak >= 3)].dropna(subset=["y_ret5"])


def fit_predict(tr, te, cols, kind):
    Xtr, Xte = tr[cols], te[cols]
    med, iqr = Xtr.median(), (Xtr.quantile(.75) - Xtr.quantile(.25)).replace(0, 1)
    Ztr = ((Xtr - med) / iqr).clip(-5, 5).fillna(0)
    Zte = ((Xte - med) / iqr).clip(-5, 5).fillna(0)
    y = (tr.y_ret5 > 0).astype(int)
    if kind == "logit":
        m = LogisticRegression(C=0.05, max_iter=500).fit(Ztr, y)
        return m.predict_proba(Zte)[:, 1], dict(zip(cols, m.coef_[0]))
    m = lgb.LGBMClassifier(n_estimators=200, learning_rate=.03, num_leaves=15, min_child_samples=200, subsample=.8, subsample_freq=1, colsample_bytree=.8, verbose=-1).fit(Ztr, y)
    return m.predict_proba(Zte)[:, 1], None


def evaluate(name, p, te):
    q = pd.Series(p, index=te.index)
    top = te[q >= q.quantile(.8)]
    bot = te[q <= q.quantile(.2)]
    return {"model": name, "n": len(te), "auc": roc_auc_score(te.y_ret5 > 0, p),
            "all5bp": 1e4 * te.y_ret5.mean(), "top20_5bp": 1e4 * top.y_ret5.mean(), "bot20_5bp": 1e4 * bot.y_ret5.mean(),
            "top20_hit": (top.y_ret5 > 0).mean(), "top_net_bp": 1e4 * (top.y_ret5.mean() - COST)}


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    for side, nm in ((1, "LONG after drops"), (-1, "SHORT after rises")):
        O = events(oriented(P, side))
        years = sorted(set(O.index.year))[1:]
        rows, coefs = [], {}
        for setname, cols in list(SETS.items()) + [("E D + market", SETS["D + fear (VIX) & market"] + MKT)]:
            for kind in ("logit", "lgbm"):
                ps, tes = [], []
                for yv in years:
                    tr = O[O.index < pd.Timestamp(f"{yv}-01-01") - pd.Timedelta(days=15)]
                    te = O[O.index.year == yv]
                    if len(tr) < 2000 or not len(te):
                        continue
                    p, cf = fit_predict(tr, te, cols, kind)
                    ps.append(p); tes.append(te)
                    if cf is not None and setname.startswith("E"):
                        coefs[yv] = cf
                te = pd.concat(tes)
                rows.append(evaluate(f"{setname} · {kind}", np.concatenate(ps), te))
        print(f"\n===== 87 STOCKS · {nm} · walk-forward by year (test {years[1] if len(years)>1 else ''}..) =====")
        print(pd.DataFrame(rows).set_index("model").round(3).to_string())
        print("logit coefficients (set E) by retrain year:")
        print(pd.DataFrame(coefs).round(3).to_string())
        # transfer test: train on all 87 stocks (2013-2017), test on TSLA 2018-2026 (unseen stock, unseen years)
        Ot = events(oriented(T, side))
        te = Ot[Ot.index >= "2018-01-01"]
        out = []
        for setname, cols in SETS.items():
            for kind in ("logit", "lgbm"):
                p, _ = fit_predict(O, te, cols, kind)
                out.append(evaluate(f"{setname} · {kind}", p, te))
        print(f"--- transfer to TSLA 2018-2026 ({nm}) ---")
        print(pd.DataFrame(out).set_index("model").round(3).to_string())
