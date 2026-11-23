"""Round 65 follow-up (exploratory, after the pre-registered result): which part survives walk-forward - the exit or the slot order?"""
exec(open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "r65.py")).read().split("# ---------------------------------------------------------------- Test 1")[0])
ERAS = {"2016-26": ("2016-01-01", "2026-12-31"), "2016-20": ("2016-01-01", "2020-12-31"), "2021-26": ("2021-01-01", "2026-12-31")}
def walk_sub(cfgs):
    parts = []; ch = {}
    for Y in range(2016, 2027):
        key = max(cfgs, key=lambda k: ratio(k, "2013-01-01", f"{Y - 1}-12-31")); ch[Y] = key; T = RUN[key][0]
        parts.append(T[(dates[T.i.values] >= pd.Timestamp(f"{Y}-01-01")) & (dates[T.i.values] <= pd.Timestamp(f"{Y}-12-31"))])
    Ts, cv = gsleeve(pd.concat(parts).reset_index(drop=True)); return ch, Ts, cv
def show(nm, Ts, cv):
    o = {e: stats(Ts, cv, a, b) for e, (a, b) in ERAS.items()}
    print(f"  {nm:46s} " + " | ".join(f"{e} {100 * s['ret']:+.1f}%/y DD {100 * s['dd']:.1f}% r {s['ratio']:.2f}" for e, s in o.items())); return o
show("live (ML rank, hold 40)", *RUN[("ML rank", "hold 40")][1:])
ch, Ts, cv = walk_sub([("ML rank", e) for e in EXITS]); show("walk-forward over the EXIT only (ML order)", Ts, cv); print("    " + "; ".join(f"{Y}: {k[1]}" for Y, k in ch.items()))
ch, Ts, cv = walk_sub([(o, "hold 40") for o in ORDERS]); show("walk-forward over the SLOT ORDER only (hold 40)", Ts, cv); print("    " + "; ".join(f"{Y}: {k[0]}" for Y, k in ch.items()))
for e in EXITS: show(f"fixed: ML rank + {e}", *RUN[("ML rank", e)][1:])
