"""Refresh the daily prices of the US 200 (round 84 list) from Yahoo. Yahoo only; nothing is estimated.
A bar for a New York session that has not closed yet (before 16:30 New York time) is left out, so every stored bar is a finished day.
Usage: RE_WORK=<work folder> python3 fetch_us.py      -> <work>/edge26/data/us200/<SYM>.csv (and us200_list.json beside it, if missing)"""
import os, sys, json, glob, shutil, datetime as dt
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "research", "edge26"))
import yf
WORK = os.environ["RE_WORK"]; DATA = os.path.join(WORK, "edge26", "data"); OUT = os.path.join(DATA, "us200"); os.makedirs(OUT, exist_ok=True)
LISTF = os.path.join(DATA, "us200_list.json")
if not os.path.exists(LISTF): shutil.copy(os.path.join(HERE, "..", "research", "r84", "us200_list.json"), LISTF)
L = json.load(open(LISTF)); ny = dt.datetime.now(ZoneInfo("America/New_York")); today = ny.strftime("%Y-%m-%d"); open_now = (ny.hour, ny.minute) < (16, 30)
bad, last = [], {}
for s in L["list"]:
    try: m = yf.daily(s, OUT)
    except Exception as e: bad.append(f"{s}: {str(e)[:80]}"); continue
    if not m: bad.append(f"{s}: no data"); continue
    p = os.path.join(OUT, s + ".csv"); rows = open(p).read().rstrip().split("\n")
    if open_now and rows[-1].split(",")[0] == today: rows = rows[:-1]; open(p, "w").write("\n".join(rows) + "\n")     # today's bar is not finished
    rows = [r for r in rows if r.split(",")[4] not in ("", "None")]; last[s] = rows[-1].split(",")[0]
newest = max(last.values()) if last else None; behind = sorted(s for s, d in last.items() if d < newest)
print(f"US 200 prices: {len(last)} of {len(L['list'])} stocks, newest close {newest}" + (f"; behind (Yahoo has no bar for the newest close): {', '.join(f'{s} {last[s]}' for s in behind)}" if behind else "") + (f"; failed: {'; '.join(bad)}" if bad else ""))
