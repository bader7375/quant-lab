import os, sys; HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "r48")); sys.path.insert(0, HERE)
from zswing import *; from sim49 import trades49
for nm, a, b in (("hold 40", dict(), dict()), ("Z exit", dict(exitm=1, zt=0.0, cap=60), dict(zexit=True, cap=60))):
    A = trades(S_LIVE, M, **a); B = trades49(S_LIVE, M, **b)
    print(nm, len(A), len(B), round(A.net.mean(), 6), round(B.net.mean(), 6), (A[["i", "j", "ex"]].values == B[["i", "j", "ex"]].values).all() if len(A) == len(B) else "len differs")
