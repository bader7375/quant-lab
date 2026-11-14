from core import *
Q = pd.read_parquet("pm27.parquet").reindex(dates)
for k in ("pm_old", "pm_new", "pm_newonly"):
    g = Q[k] > 0
    Wm = ml_weights(gate=g); Wt = trend(gate=g); show(f"CORE gated by {k} (invested days {100*g.loc['2013':].mean():.0f}%)", *run(P, combine(Wm, Wt)))
