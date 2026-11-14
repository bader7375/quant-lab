"""Writes research/daily/rebound_edge.json (the small table the live daily list needs for its Rebound Edge column) from
fable/rebound_model.json. Run again after the model file changes: python3 fable/make_daily_model.py"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__)); X = json.load(open(os.path.join(HERE, "rebound_model.json"))); S = X["saudi"]
out = dict(about="Rebound Edge for the daily list (research round 80). Saudi weights and Saudi companion tables; made by fable/make_daily_model.py.", line=X["line"], raw=S["raw"], zones=S["zones"],
           band_edges=S["band_edges"], bands=[dict(win=round(b["win"], 4), days=round(b["days"], 1), dz=round(b["dipz_med"], 4), dzb=round(b["dipz_bad"], 4)) for b in S["bands"]])
json.dump(out, open(os.path.join(HERE, "../research/daily/rebound_edge.json"), "w"), indent=1); print("wrote research/daily/rebound_edge.json")
