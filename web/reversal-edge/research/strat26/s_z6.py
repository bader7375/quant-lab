from sim import *
import pickle, s_trend, s_ml
P = load(); ZP = pickle.load(open("Zs.pkl", "rb"))[("price", 250)].reindex(index=P["C"].index, columns=P["C"].columns)
core = lambda a, b: (lambda W: W.div(np.maximum(W.sum(1), 1), axis=0))(a.add(b, fill_value=0))
Wb = pd.read_pickle("W_best.pkl")
# 1) trend sleeve: skip breakouts with Z above a cap; optional take-profit when Z >= tp
orig_sig_fn = s_trend.trend
def trend_z(zcap=None, tp=None, **kw):
    C = s_trend.C; save = s_trend.SMA200
    if zcap is not None: s_trend.SMA200 = s_trend.SMA200.where(ZP <= zcap, np.inf)      # fails "close > SMA200" when Z too high -> no entry
    W = orig_sig_fn(**kw); s_trend.SMA200 = save
    if tp is not None:                                                               # exit the day after Z >= tp (hold off re-entry until next breakout)
        hit = (ZP >= tp) & (W > 0); W = W.mask(hit.cummax() & False, 0)              # placeholder (kept simple below)
    return W
for zc in (None, 2.0, 2.5, 3.0):
    W = trend_z(zcap=zc, ml=.7, mkt=True); r, i = run(P, W); show(f"TREND sleeve, skip if Z250 > {zc}", r, i)
    rc, ic = run(P, core(Wb["ml"], W)); show(f"   CORE with that trend sleeve", rc, ic)
# 2) ML sleeve: drop picks with Z above cap
pred_save = s_ml.pred.copy()
for zc in (2.0, 2.5):
    s_ml.pred = pred_save.where(ZP.reindex(pred_save.index) <= zc)
    W = s_ml.ml_weights(N=10, tranches=4, timing="bin"); r, i = run(P, W); show(f"ML sleeve, skip picks with Z250 > {zc}", r, i)
    rc, ic = run(P, core(W, Wb["trend"])); show(f"   CORE with that ML sleeve", rc, ic)
s_ml.pred = pred_save
