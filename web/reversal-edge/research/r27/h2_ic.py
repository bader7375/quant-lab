from feats27 import *
import json
Py, Pl = yahoo(), library()
Fy = build(Py); Fl = build(Pl, yahoo_extras=False)
pd.to_pickle(Fy, "F27y.pkl")
# the existing ML feature names for reference (computed in ml26/features.py) are not recomputed here
for h in (20, 5):
    Ty = ic_table(Fy, Py, h, ("DESIGN", "CONFIRM", "C1", "C2")); Tl = ic_table(Fl, Pl, h, ("DEEP",))
    T = Ty.join(Tl, how="left"); T["pass"] = (T.DESIGN_t.abs() >= 2.5) & (np.sign(T.CONFIRM_ic) == np.sign(T.DESIGN_ic)) & (T.CONFIRM_t.abs() >= 2)
    T = T.sort_values("DESIGN_t"); T.to_csv(f"h2_ic_h{h}.csv")
    print(f"\n=== rank IC with {h}-day excess return (t = monthly-clustered) ===")
    print(T[["DEEP_ic", "DEEP_t", "DESIGN_ic", "DESIGN_t", "CONFIRM_ic", "CONFIRM_t", "C1_t", "C2_t", "pass"]].round(3).to_string())
