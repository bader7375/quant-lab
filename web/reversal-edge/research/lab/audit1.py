import sys; sys.path.insert(0, ".")
from grid import *
B = {}
def show(name, cfg):
    L = run1("dev_long", "single", cfg); P6 = run1("dev_long", "portfolio", cfg); P87 = run1("dev87", "portfolio", cfg); P87b = run1("dev87", "portfolio", dict(cfg, maxPos=10))
    print(f"{name:34s} L6 single: {fmt_single(single_summary(L))}\n{'':34s} L6 portf : {fmt_port(port_summary(P6))}\n{'':34s} 87 (4 pos): {fmt_port(port_summary(P87))}\n{'':34s} 87 (10 pos): {fmt_port(port_summary(P87b))}", flush=True)
show("BASELINE v8", {})
