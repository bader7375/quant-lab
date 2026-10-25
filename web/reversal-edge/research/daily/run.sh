#!/bin/sh
# Daily Saudi top-3: refresh Yahoo prices, rebuild features, refit the ML ranker and market model, then write the list (out/<date>.md).
# About 6-10 minutes. Progress and errors go to run.log; the list is printed at the end.
S=$(cd "$(dirname "$0")/.." && pwd); LOG=$S/daily/run.log; : > $LOG
step() { echo "== $1 $(date -u +%H:%M:%S)" >> $LOG; }
# US index ETFs for the US section (round 35)
(cd $S/edge26 && python3 -c "
from yf import daily
for s in ['SPY', 'QQQ']: print(s, daily(s, 'data/idx'))
" >> $LOG 2>&1; python3 $S/daily/strip_partial.py >> $LOG 2>&1)
if [ "$(TZ=Asia/Riyadh date +%u)" = "5" ]; then   # Friday: Tadawul is closed, only the US section
  echo "**Friday: the Saudi market is closed; Thursday's Saudi list stands.**"; (cd $S/daily && python3 us_signal.py 2>> $LOG) || echo "FAILED at us_signal"; exit 0
fi
step fetch; cd $S/edge26 || exit 1
CODES=$(ls data/d/*.SR.csv | xargs -n1 basename | sed 's/.SR.csv//' | paste -sd,)
python3 fetch_all.py "$CODES" > daily_fetch.log 2>&1
python3 -c "
from yf import daily
for s in ['BZ=F','CL=F','^GSPC','KSA','^VIX','^IRX','^TNX','DX-Y.NYB','GC=F','EEM','HYG','USO','FLSA','^IXIC','EWJ']: print(s, daily(s, 'data/ext'))
" >> daily_fetch.log 2>&1
python3 $S/daily/strip_partial.py >> $LOG 2>&1
echo "fetch errors: $(grep -c '^ERR' daily_fetch.log); last dates: $(grep -o "'last': '[0-9-]*'" daily_fetch.log | sort | uniq -c | sort -rn | head -3 | tr '\n' ' ')" >> $LOG
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
step us; python3 us_signal.py 2>> $LOG || echo "FAILED at us_signal"
step done
