"""Round 79, idea 8 abroad: crosses into the buy zone on a limit-down close against the other crosses, in markets with a 10% daily
limit (China, Qatar; Taiwan from 2015-06). Price-only, storm and deep weather. An event table, nothing judged.
Usage: RE_WORK=<work folder> python3 limit79.py <world data folder>"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, os.path.join(HERE, "../r72")); sys.path.insert(0, HERE)
import wpanel, swing as SW, swingbook as SBk; from engine import Book; from feat79 import feats
ROOT = sys.argv[1]; OUT = {}
for mk, since in (("china", "2001-01-01"), ("qatar", "2001-01-01"), ("taiwan", "2015-06-01")):
    P = wpanel.panel(os.path.join(ROOT, mk)); B = Book(C=P["C"], O=P["O"], elig=P["elig"], week=wpanel.WEEK.get(mk, "W-FRI")); F = feats(B); d = B.dates
    inz, age = SBk.zone_age(B, -2.5); wx = SBk.prep(B)["wx"]; ok = inz & (age == 0) & B.EL & np.isin(wx, (2, 3))[:, None] & (d >= since)[:, None]
    I, J = np.where(ok); X = SW.run_exits(B, I, J, target=0.0, cap=40); done = X["ex"] >= 0; net = X["ret"] - .004; f5 = SW.fwd(B.Of, 5)[I, J]; isld = F["ld"][I, J]; mon = (d[I].year * 12 + d[I].month).values
    row = {}
    for nm, m in (("limit-down close", isld & done), ("other crosses", ~isld & done)):
        a, (lo, hi) = SW.month_ranges(net[m], mon[m]); a5, (lo5, hi5) = SW.month_ranges(f5[m], mon[m])
        row[nm] = dict(n=int(m.sum()), swing=a, swing_range=[lo, hi], first5=a5, first5_range=[lo5, hi5], win=float((net[m] > 0).mean()) if m.sum() else np.nan, held=float(X["held"][m].mean()) if m.sum() else np.nan)
        print(f"{mk:8s} {nm:17s} n={int(m.sum()):5d} | swing trade (sold at stretch 0 or 40 sessions, net) {100 * a:+5.1f}% ({100 * lo:+.1f} to {100 * hi:+.1f}) | first 5 sessions {100 * a5:+5.1f}% ({100 * lo5:+.1f} to {100 * hi5:+.1f}) | winners {100 * row[nm]['win']:.0f}% | held {row[nm]['held']:.0f}")
    OUT[mk] = row
json.dump(OUT, open(os.path.join(HERE, "limit79.json"), "w"), indent=1, default=float)
