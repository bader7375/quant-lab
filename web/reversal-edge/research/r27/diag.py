from core import *
oldp = pd.read_parquet("../ml26/pred_q20stockonly.parquet"); oldp["pct"] = oldp.groupby("date").pred.rank(pct=True)
OP = oldp.pivot(index="date", columns="sym", values="pred").reindex(index=dates, columns=cols); OPC = oldp.pivot(index="date", columns="sym", values="pct").reindex(index=dates, columns=cols)
opm = pd.read_parquet("../ml26/pm.parquet").pm.reindex(dates); Q = pd.read_parquet("pm27.parquet").reindex(dates)
print("gate agreement old pm vs pm27 pm_old (2013+):", round(float(((opm > 0) == (Q.pm_old > 0)).loc["2013":].mean()), 3), "| invested share old/new:", round(float((opm > 0).loc["2013":].mean()), 2), round(float((Q.pm_old > 0).loc["2013":].mean()), 2))
pp = pd.read_parquet("preds/M0.parquet").merge(oldp[["date", "sym", "pred"]], on=["date", "sym"], suffixes=("", "_old"))
print("M0 new vs old pred rank corr (pooled daily):", round(float(pp.groupby("date").apply(lambda g: g.pred.corr(g.pred_old, method="spearman")).mean()), 3))
for nm, pr, pc, g in (("old preds + old pm", OP, OPC, opm > 0), ("new preds + old pm", PRED, PCT, opm > 0), ("old preds + new pm", OP, OPC, Q.pm_old > 0), ("new preds + new pm", PRED, PCT, Q.pm_old > 0)):
    Wm = ml_weights(pred=pr, gate=g); Wt = trend(pct=pc, gate=g)
    show(f"ML   {nm}", *run(P, Wm)); show(f"TRND {nm}", *run(P, Wt)); show(f"CORE {nm}", *run(P, combine(Wm, Wt)))
