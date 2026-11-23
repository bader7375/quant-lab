"""Writes research/daily/rebound_edge.json, the small table the live daily list needs for its Rebound Edge and Hold Edge columns, from
the round 83 model files (fable/rebound40_model.json, fable/holdedge40_model.json): both describe the live plan's own sale, a fixed
40-session hold. The list shows each reading's group average (what past Saudi trades with a like reading did), not the formula's value.
Run again after the model files change: python3 fable/make_daily_model.py"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__)); R = json.load(open(os.path.join(HERE, "rebound40_model.json")))["saudi"]; H = json.load(open(os.path.join(HERE, "holdedge40_model.json")))["saudi"]
r4 = lambda x: round(float(x), 5)
reb = dict(raw={k: (r4(v) if not isinstance(v, dict) else {a: [r4(b) for b in c] for a, c in v.items()}) for k, v in R["raw"].items()}, band_edges=[r4(x) for x in R["band_edges"]], zones=[r4(x) for x in R["zones"]],
           bands=[dict(gain=r4(b["gain"]), win=r4(b["win"]), dz=r4(b["dipz_med"]), dzb=r4(b["dipz_bad"]), n=int(b["n"])) for b in R["bands"]], cases=int(R["cases"]), fitted_on=R["fitted_on"])
hold = dict(raw={k: (r4(v) if not isinstance(v, dict) else {a: [r4(b) for b in c] for a, c in v.items()}) for k, v in H["raw"].items()}, band_edges=[r4(x) for x in H["band_edges"]], zones=[r4(x) for x in H["zones"]],
            bands=[dict(rest=r4(b["rest"]), up=r4(b["up"]), togo=round(float(b["togo"]), 1), fz=r4(b["furz_med"]), fzb=r4(b["furz_bad"]), n=int(b["n"])) for b in H["bands"]], cases=int(H["cases"]), fitted_on=H["fitted_on"])
out = dict(about="Rebound Edge and Hold Edge for the daily list (research rounds 80, 82, 83), for the plan's own sale: a fixed 40-session hold. Saudi weights and Saudi group tables; made by fable/make_daily_model.py.",
           line=-1.5, rebound=reb, hold=hold,
           # the round 80 layout, kept so that an older rebound_edge.py reading this file still works (formula value, 40-session hold)
           raw=reb["raw"], zones=reb["zones"], band_edges=reb["band_edges"], bands=[dict(win=b["win"], days=40.0, dz=b["dz"], dzb=b["dzb"]) for b in reb["bands"]])
json.dump(out, open(os.path.join(HERE, "../research/daily/rebound_edge.json"), "w"), indent=1); print("wrote research/daily/rebound_edge.json")
