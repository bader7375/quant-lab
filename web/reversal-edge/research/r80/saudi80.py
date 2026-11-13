"""Round 80 (PREREG.md, amendment 1): Rebound Edge on Saudi. Usage: RE_WORK=<work folder> python3 saudi80.py design | confirm
design  = cases whose trade ended by 2019-12-31. Tests marks 1 and 2 with M19 (no Saudi data in it), fits the Saudi adjustment, writes
          it into fable/rebound_model.json. Nothing after 2019-12-31 is read.
confirm = signals from 2020-01-01, opened once, everything frozen: marks 1, 2, 3 and the verdict."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, HERE)
import rebound as RB, eval80 as EV
MODE = sys.argv[1]; WORK = os.environ["RE_WORK"]; D = pd.read_parquet(os.path.join(WORK, f"r80_saudi_{MODE}.parquet")); D = D[np.isfinite(D.Z) & np.isfinite(D.MS)].reset_index(drop=True)
M19, ALL = RB.load("m19"); e = RB.edge(M19, D); net = D.net.values; mon = D.month.values; OUT = dict(mode=MODE, cases=int(len(D)), wins=float(D.win.mean()), net=float(net.mean()))
print(f"Saudi {MODE}: {len(D)} cases (liquid, stretch Z -1.5 or lower), {D.date.min().date()} to {D.date.max().date()}; wins {100 * D.win.mean():.1f}%, average net {100 * net.mean():+.2f}%; passing the live gates: {100 * D.gated.mean():.0f}%")
def marks(e, D, label):
    net = D.net.values; mon = D.month.values; sep = EV.separation(e, net, mon); bt = EV.beats(e, dict(stretch=(D.Z.values, -1), momentum=(D.MS.values, -1)), net, mon)
    m1 = sep[1] > 0; m2 = bt["stretch"]["lead_p5"] > 0 and bt["momentum"]["lead_p5"] > 0
    print(f"[{label}] mark 1 (it separates): top third {100 * sep[3]:+.2f}% vs bottom third {100 * sep[4]:+.2f}% = {100 * sep[0]:+.2f} points, range {100 * sep[1]:+.2f} to {100 * sep[2]:+.2f} -> {'PASS' if m1 else 'FAIL'}")
    print(f"[{label}] mark 2 (it beats what you have): rank correlation with the net result: edge {bt['odds']:.3f} ({bt['odds_range'][0]:.3f} to {bt['odds_range'][1]:.3f}) | stretch Z alone {bt['stretch']['corr']:.3f}, lead {bt['stretch']['lead']:+.3f} (5th pct {bt['stretch']['lead_p5']:+.3f}) | "
          f"market momentum alone {bt['momentum']['corr']:.3f}, lead {bt['momentum']['lead']:+.3f} (5th pct {bt['momentum']['lead_p5']:+.3f}) -> {'PASS' if m2 else 'FAIL'}")
    return dict(separation=sep, beats=bt, mark1=bool(m1), mark2=bool(m2))
OUT["m19"] = marks(e, D, "M19, no Saudi data")
def table(e, D, M, label):
    """by third and by band: stated edge, realized result, wins against the band's stated share, dips against the stated bad dip."""
    net = D.net.values; q1, q2 = np.quantile(e, [1 / 3, 2 / 3]); th = [(e <= q1), (e > q1) & (e < q2), (e >= q2)]; rows3 = [dict(stated=float(e[m].mean()), realized=float(net[m].mean()), wins=float(D.win.values[m].mean()), n=int(m.sum())) for m in th]
    print(f"[{label}] thirds of edge: " + " | ".join(f"stated {100 * r['stated']:+.1f}% -> realized {100 * r['realized']:+.1f}% (wins {100 * r['wins']:.0f}%, {r['n']})" for r in rows3))
    band = np.searchsorted(np.asarray(M["band_edges"]), e, side="right"); rowsb = []; u = D.unit.values
    for k in range(10):
        m = band == k
        if not m.sum(): continue
        b = M["bands"][k]; ok = m & np.isfinite(u) & (u > 0); worse = float((D.dip.values[ok] < b["dipz_bad"] * u[ok]).mean()) if ok.sum() else np.nan
        rowsb.append(dict(band=k, n=int(m.sum()), stated=float(e[m].mean()), realized=float(net[m].mean()), wins=float(D.win.values[m].mean()), wins_stated=b["win"], days=float(np.median(D.held.values[m])), days_stated=b["days"], dip_med=float(np.median(D.dip.values[m])), dip_med_stated=float(np.median(b["dipz_med"] * u[ok])) if ok.sum() else np.nan, worse_than_bad=worse))
    for r in rowsb: print(f"   band {r['band']}: {r['n']:5d} cases | edge {100 * r['stated']:+5.1f}% -> {100 * r['realized']:+5.1f}% | wins {100 * r['wins']:.0f}% (stated {100 * r['wins_stated']:.0f}%) | sessions {r['days']:.0f} ({r['days_stated']:.0f}) | typical dip {100 * r['dip_med']:+.1f}% (stated {100 * r['dip_med_stated']:+.1f}%) | deeper than the stated bad dip: {100 * r['worse_than_bad']:.0f}%")
    okk = np.isfinite(u) & (u > 0); bad = np.array([M["bands"][k]["dipz_bad"] for k in band]) * u; allw = float((D.dip.values[okk] < bad[okk]).mean()); print(f"   all bands: worst dip deeper than the stated bad dip in {100 * allw:.0f}% of cases (stated 10%)")
    return dict(thirds=rows3, bands=rowsb, worse_than_bad=allw)
def inside(e, D, label):
    """the swing's own candidates: first close at -2.5 or lower, storm or deep weather, passing the gates."""
    c = (D.cross25 > 0) & (D.wx >= 2) & (D.gated > 0); x = D[c]; ec = e[c.values]
    if len(x) < 20: print(f"[{label}] swing candidates: {len(x)} (too few)"); return dict(n=int(len(x)))
    hi = ec >= np.median(ec); r = dict(n=int(len(x)), top=float(x.net.values[hi].mean()), bottom=float(x.net.values[~hi].mean()), top_win=float(x.win.values[hi].mean()), bottom_win=float(x.win.values[~hi].mean()), corr=EV.rank_corr(ec, x.net.values))
    print(f"[{label}] inside the swing's own candidates ({r['n']}): higher-edge half {100 * r['top']:+.1f}% ({100 * r['top_win']:.0f}% wins) vs lower-edge half {100 * r['bottom']:+.1f}% ({100 * r['bottom_win']:.0f}%); rank correlation {r['corr']:+.3f}. No pass mark; not a filter.")
    return r
def weather(e, D, label):
    rows = []
    for w, nm in ((0, "calm"), (1, "clouds"), (2, "storm"), (3, "deep")):
        m = D.wx.values == w
        if m.sum(): rows.append(dict(weather=nm, n=int(m.sum()), stated=float(e[m].mean()), realized=float(D.net.values[m].mean()), wins=float(D.win.values[m].mean())))
    print(f"[{label}] by weather: " + " | ".join(f"{r['weather']} {r['n']}: stated {100 * r['stated']:+.1f}% -> {100 * r['realized']:+.1f}% ({100 * r['wins']:.0f}% wins)" for r in rows)); return rows
if MODE == "design":
    # ---- the Saudi adjustment, fitted here and only here
    lo, hi = np.quantile(net, [.01, .99]); y = np.clip(net, lo, hi); g = D.gated.values
    def adj(ix, with_c=True):
        A = np.column_stack([np.ones(len(ix)), e[ix]] + ([g[ix]] if with_c else [])); return np.linalg.lstsq(A, y[ix], rcond=None)[0]
    full = adj(np.arange(len(D))); bs = np.array([adj(ix) for ix in EV.month_draws(mon, 1000)]); c5, c95 = np.quantile(bs[:, 2], [.05, .95]); keep = bool(c5 > 0 or c95 < 0)
    co = full if keep else adj(np.arange(len(D)), with_c=False); S = dict(a=float(co[0]), b=float(co[1]), c=float(co[2]) if keep else 0.0, c_tried=float(full[2]), c_range=[float(c5), float(c95)], c_kept=keep, b_range=[float(np.quantile(bs[:, 1], .05)), float(np.quantile(bs[:, 1], .95))], fitted_on="Saudi cases whose trade ended by 2019-12-31", cases=int(len(D)))
    print(f"\nSaudi adjustment (2013-19 only): saudi edge = {100 * S['a']:+.2f}% + {S['b']:.2f} x edge" + (f" + {100 * S['c']:+.2f}% when the stock passes the gates" if keep else "") + f"   | gate term tried: {100 * full[2]:+.2f}% (range {100 * c5:+.2f} to {100 * c95:+.2f}) -> {'kept' if keep else 'not kept'}; slope range {S['b_range'][0]:.2f} to {S['b_range'][1]:.2f}")
    S["band_edges"], S["bands"] = RB.saudi_tables(D, RB.edge(M19, D, saudi=S, gated=g), M19); S["zones"] = [float(v) for v in np.quantile(RB.edge(M19, D, saudi=S, gated=g), [1 / 3, 2 / 3])]
    ALL["saudi"] = S; ALL["saudi_tested"] = S; json.dump(ALL, open(RB.MODEL_FILE, "w"), indent=1); OUT["saudi"] = {k: v for k, v in S.items() if k not in ("bands",)}
S = ALL["saudi_tested"]; ea = RB.edge(M19, D, saudi=S, gated=D.gated.values)
OUT["adjusted_marks"] = marks(ea, D, "terminal version: Saudi-adjusted edge" + (" (fitted on these cases: shown, not a test)" if MODE == "design" else " (frozen on 2013-19: a test)"))
OUT["table"] = table(ea, D, S, "Saudi-adjusted edge, Saudi tables" + (" (built from these cases)" if MODE == "design" else " (frozen on 2013-19)")); OUT["inside"] = inside(ea, D, "Saudi-adjusted"); OUT["weather"] = weather(ea, D, "Saudi-adjusted")
OUT["by_year"] = {int(y_): dict(n=int((D.date.dt.year == y_).sum()), corr=EV.rank_corr(e[(D.date.dt.year == y_).values], net[(D.date.dt.year == y_).values])) for y_ in sorted(D.date.dt.year.unique()) if (D.date.dt.year == y_).sum() >= 200}
print("rank correlation by year (200+ cases): " + "  ".join(f"{y_} {v['corr']:+.2f} ({v['n']})" for y_, v in OUT["by_year"].items()))
if MODE == "confirm":
    t = OUT["table"]; th = t["thirds"]; a_ok = th[0]["realized"] < th[1]["realized"] < th[2]["realized"]; b_rows = [r for r in t["bands"] if r["n"] >= 100]; b_ok = all(abs(r["wins"] - r["wins_stated"]) <= .10 for r in b_rows); c_ok = .05 <= t["worse_than_bad"] <= .20
    print(f"\nmark 3 (honest about its numbers): (a) thirds rise {100 * th[0]['realized']:+.1f}% < {100 * th[1]['realized']:+.1f}% < {100 * th[2]['realized']:+.1f}%: {'yes' if a_ok else 'NO'} | (b) wins within 10 points of the stated share in every band with 100+ cases: {'yes' if b_ok else 'NO'} "
          f"(largest gap {100 * max(abs(r['wins'] - r['wins_stated']) for r in b_rows):.0f} points) | (c) dips deeper than the stated bad dip: {100 * t['worse_than_bad']:.0f}% (5% to 20%): {'yes' if c_ok else 'NO'} -> {'PASS' if a_ok and b_ok and c_ok else 'FAIL'}")
    OUT["mark3"] = dict(a=bool(a_ok), b=bool(b_ok), c=bool(c_ok), passed=bool(a_ok and b_ok and c_ok)); m = OUT["m19"]
    late = D.date >= "2023-01-01"; OUT["m19_2023_26"] = marks(e[late.values], D[late].reset_index(drop=True), "2023-26 check, M19")
    des = json.load(open(os.path.join(HERE, "saudi80_design.json")))["m19"]; one = m["mark1"] and des["mark1"]; two = m["mark2"] and des["mark2"]
    OUT["verdict"] = "NOT VALID" if not one else ("USEFUL" if two and OUT["mark3"]["passed"] else "DESCRIPTIVE"); print(f"\nVERDICT, chart formula: {OUT['verdict']}  (mark 1: 2013-19 {'pass' if des['mark1'] else 'fail'}, 2020-26 {'pass' if m['mark1'] else 'fail'}; mark 2: 2013-19 {'pass' if des['mark2'] else 'fail'}, 2020-26 {'pass' if m['mark2'] else 'fail'}; mark 3: {'pass' if OUT['mark3']['passed'] else 'fail'})")
    am = OUT["adjusted_marks"]; OUT["verdict_terminal"] = "USEFUL IN THE TERMINAL (one test period)" if (am["mark1"] and am["mark2"] and OUT["mark3"]["passed"]) else OUT["verdict"]
    print(f"VERDICT, terminal version (Saudi-adjusted, knows the gates; tested on 2020-26 only): {OUT['verdict_terminal']}  (mark 1 {'pass' if am['mark1'] else 'fail'}, mark 2 {'pass' if am['mark2'] else 'fail'}, mark 3 {'pass' if OUT['mark3']['passed'] else 'fail'})")
json.dump(OUT, open(os.path.join(HERE, f"saudi80_{MODE}.json"), "w"), indent=1, default=float)
