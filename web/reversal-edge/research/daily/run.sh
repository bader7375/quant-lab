#!/bin/sh
# Daily Saudi top-3: refresh Yahoo prices, rebuild features, refit the ML ranker and market model, then write the list (out/<date>.md).
# About 6-10 minutes. Progress and errors go to run.log; the list is printed at the end.
S=$(cd "$(dirname "$0")/.." && pwd); LOG=$S/daily/run.log; : > $LOG
step() { echo "== $1 $(date -u +%H:%M:%S)" >> $LOG; }
# US index ETFs for the US section (round 35)
(cd $S/edge26 && python3 -c "
from yf import daily
for s in ['SPY', 'QQQ']: print(s, daily(s, 'data/idx'))
import glob, os, time
import json
nm = {}
syms = set(os.path.basename(f)[:-4] for f in glob.glob('data/us100/*.csv')) | {'SPY', 'QQQ'}
if os.path.exists('us100_list.json'): syms |= set(json.load(open('us100_list.json')))   # the 115 large caps (the list is in the repo)
for s in sorted(syms):
    try: x = daily(s, 'data/us100'); nm[s] = (x or {}).get('name', ''); time.sleep(0.15)
    except Exception as e: print('ERR', s, e)
json.dump(nm, open('data/us100_names.json', 'w'))
" >> $LOG 2>&1; python3 us30.py >> $LOG 2>&1; python3 $S/daily/strip_partial.py >> $LOG 2>&1)   # us30: most-traded 30 (round 44)
if [ "$(TZ=Asia/Riyadh date +%u)" = "5" ] && [ "${FULL:-0}" != "1" ]; then   # Friday: Tadawul is closed, only the US section (FULL=1 forces the Saudi part)
  echo "**Friday: the Saudi market is closed; Thursday's Saudi list stands.**"; (cd $S/daily && python3 us_signal.py 2>> $LOG) || echo "FAILED at us_signal"; (cd $S/daily && python3 us30_signal.py 2>> $LOG) || echo "FAILED at us30"; exit 0
fi
step fetch; cd $S/edge26 || exit 1
CODES=$(python3 -c "
import json, glob, os   # stored files plus the full Tadawul list (2001-2020 library, Aramco, later listings), so an empty folder fills itself
c = set(os.path.basename(f)[:-7] for f in glob.glob('data/d/*.SR.csv')) | set(json.load(open('../tadawul/meta.json'))) | {'2222'}
if os.path.exists('data/new_codes.json'): c |= set(json.load(open('data/new_codes.json')))
print(','.join(sorted(c)))")
python3 fetch_all.py "$CODES" > daily_fetch.log 2>&1
python3 -c "
from yf import daily
for s in ['BZ=F','CL=F','^GSPC','KSA','^VIX','^IRX','^TNX','DX-Y.NYB','GC=F','EEM','HYG','USO','FLSA','^IXIC','EWJ']: print(s, daily(s, 'data/ext'))
" >> daily_fetch.log 2>&1
python3 $S/daily/strip_partial.py >> $LOG 2>&1
echo "fetch errors: $(grep -c '^ERR' daily_fetch.log); last dates: $(grep -o "'last': '[0-9-]*'" daily_fetch.log | sort | uniq -c | sort -rn | head -3 | tr '\n' ' ')" >> $LOG
# After-close mode: the evening run (after 15:45 Riyadh) computes tomorrow's list from today's close; the morning run then reuses it.
LASTD=$(for f in data/d/*.SR.csv; do tail -1 "$f" | cut -d, -f1; done | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')
NLAST=$(for f in data/d/*.SR.csv; do tail -1 "$f" | cut -d, -f1; done | grep -c "^$LASTD$")
TODAY=$(TZ=Asia/Riyadh date +%F); HR=$(TZ=Asia/Riyadh date +%H); DOW=$(TZ=Asia/Riyadh date +%u)
if [ "$HR" -ge 15 ] && [ "$DOW" != "5" ] && [ "$DOW" != "6" ] && [ "$LASTD" != "$TODAY" ]; then
  echo "NOT UPDATED: Yahoo has not published today's ($TODAY) Saudi close yet, or Tadawul was closed today; the newest bar is $LASTD. The scanner keeps the previous close; the 06:42 run will try again."; step notyet; exit 3
fi
EXPD=$(python3 -c "import json; print(json.load(open('$S/r27/today27.json'))['date'])" 2>/dev/null)
PD=""; PN=0; [ -f $S/daily/last_full.txt ] && read PD PN < $S/daily/last_full.txt
if [ "${FULL:-0}" != "1" ] && [ "$LASTD" = "$EXPD" ] && [ "$PD" = "$LASTD" ] && [ "$NLAST" -le "${PN:-0}" ] && [ -f "$S/daily/out/$LASTD.md" ]; then
  step reuse   # no new Saudi close since the last full run: same list and export (no refit), fresh US part only
  cat $S/daily/out/$LASTD.md; echo; echo "_(Saudi list computed after the $(date -d $LASTD '+%a %d %b') close; no new Saudi close since.)_"
  cd $S/daily && { python3 us_signal.py 2>> $LOG || echo "FAILED at us_signal"; python3 us30_signal.py 2>> $LOG || echo "FAILED at us30"; }; step done; exit 0
fi
step features; cd $S/r27 || exit 1; rm -f py.pkl W_core.pkl F27y.pkl
python3 -c "
from feats27 import *
P = yahoo(); F = build(P); pd.to_pickle(F, 'F27y.pkl'); print('panel to', P['C'].index[-1].date(), 'stocks on last day', int(P['C'].iloc[-1].notna().sum()))
" >> $LOG 2>&1 || { echo "FAILED at features"; tail -5 $LOG; exit 1; }
step dataset; python3 ds27.py >> $LOG 2>&1 || { echo "FAILED at ds27"; tail -5 $LOG; exit 1; }
step ranker; python3 wf27.py M0 > wf_daily.log 2>&1 || { echo "FAILED at wf27"; tail -5 wf_daily.log; exit 1; }
step market; python3 mkt27.py >> $LOG 2>&1 || { echo "FAILED at mkt27"; tail -5 $LOG; exit 1; }
step accounts; find $S/r33/fund -name "*.json" -mtime +30 -delete 2>/dev/null; (cd $S/r33 && python3 fetch_fund.py >> $LOG 2>&1)   # Yahoo annual accounts, refreshed monthly
cd $S/r27
step export; PICK=M0 python3 final27.py >> $LOG 2>&1 || { echo "FAILED at final27"; tail -5 $LOG; exit 1; }
cp today27.json ../ml26/today.json
step list; cd $S/daily && python3 top3.py 2>> $LOG || { echo "FAILED at top3"; tail -5 $LOG; exit 1; }
echo "$LASTD $NLAST" > $S/daily/last_full.txt
step us; python3 us_signal.py 2>> $LOG || echo "FAILED at us_signal"
python3 us30_signal.py 2>> $LOG || echo "FAILED at us30"
step done
