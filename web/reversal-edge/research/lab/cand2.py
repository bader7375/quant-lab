import sys; sys.path.insert(0, ".")
from cand1 import *
for n, c in [("C2a + C3 (frozen candidate v9)", {"adapt": False, "exit": "rsi70"}), ("C2b + C3", {"n0": 1000, "exit": "rsi70"}),
             ("info: C2a + C3 + C1 exit open", {"adapt": False, "exit": "rsi70", "exitAt": "open"})]:
    judge(n, c)
# incremental check: does C3 add on top of C2a?
L, P6, P87 = evalcfg({"adapt": False}); a = single_summary(L); print("C2a alone for reference:", f"L6 des {a['design'][0]:.2f} tst {a['test'][0]:.2f} | 6-port {port_summary(P6)['all'][0]:.2f} | 87 {port_summary(P87)['all'][0]:.2f}")
