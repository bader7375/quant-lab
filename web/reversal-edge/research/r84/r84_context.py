"""Round 84, context for the results (description only): how often the 200 were in a sell-off, and how much money the swing had at work.
Usage: RE_WORK=<work folder> python3 r84_context.py"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, os.path.join(HERE, "../r72"))
import wpanel, swingbook as SBk; from engine import Book
P = wpanel.panel(os.path.join(os.environ["RE_WORK"], "edge26/data/us200")); B = Book(C=P["C"], O=P["O"], elig=P["elig"], week="W-FRI"); d = B.dates; T = B.T
wx = SBk.prep(B)["wx"]; CORE = {2: (-2.5, 0.0, 40, 1.0), 3: (-2.5, 0.0, 40, 2.0)}; eq, TR = SBk.simulate(B, wplan=CORE, start="2001-01-01", cash=False)
inv = np.zeros(T)
for r in TR.itertuples(): inv[int(r.d1):int(r.ex)] += r.w
out = {}
for e, (a, b) in {"2001-09": ("2001-01-01", "2009-12-31"), "2010-19": ("2010-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31")}.items():
    m = (d >= a) & (d <= b); w = wx[m]; out[e] = dict(storm=float((w == 2).mean()), deep=float((w == 3).mean()), invested=float(inv[m].mean()), most=float(inv[m].max()))
    print(f"{e}: sell-off weather on {100 * out[e]['storm']:.0f}% of days, deep on {100 * out[e]['deep']:.0f}%; money at work on average {100 * out[e]['invested']:.1f}%, at most {100 * out[e]['most']:.1f}%")
dead = set(json.load(open(os.path.join(HERE, "us200_list.json")))["list"]) - set(B.cols)
print(f"not in the tested panel (under 3 years of prices after cleaning): {len(dead)}: {' '.join(sorted(dead))}")
print(f"stocks whose early history the cleaning cut (a one-day move above 60%, kept only the part after it): {P['cut']}")
json.dump(dict(context=out, short=sorted(dead), cut=int(P["cut"])), open(os.path.join(HERE, "r84_context.json"), "w"), indent=1)
