from s_z import *
import pickle
Zs = pickle.load(open("Zs.pkl", "rb"))
for key in (("price", 250), ("relative", 250)):
    Z = Zs[key]
    for kw in (dict(entry=-2.5), dict(entry=-2.5, ml=.5), dict(entry=-2.5, ml=.3), dict(entry=-2.5, mkt=True), dict(entry=-2.5, stop_z=-4.0), dict(entry=-2.5, exit_z=-1.0),
               dict(entry=-2.5, exit_z=0.5), dict(entry=-2.5, maxhold=60), dict(entry=-2.5, maxhold=180), dict(entry=-2.0, ml=.5), dict(entry=-3.0)):
        kw.setdefault("maxhold", 125); rep(f"{key[0]}-{key[1]} " + " ".join(f"{k}={v}" for k, v in kw.items()), ztrades(Z, **kw))
