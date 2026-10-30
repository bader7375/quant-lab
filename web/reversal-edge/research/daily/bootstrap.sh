#!/bin/sh
# Rebuild the daily pipeline's work folder after the cloud machine was reset (it lives in a temporary scratchpad).
# Usage: sh bootstrap.sh <work folder>. About 20 minutes: Python packages, code from this repo copy, then a full run.sh,
# which downloads the whole Yahoo history (about 290 Saudi codes, 117 US symbols, 15 market series) and refits the models.
set -e
S=${1:?usage: sh bootstrap.sh <work folder>}; R=$(cd "$(dirname "$0")/.." && pwd)
python3 -c "import pandas, lightgbm, sklearn, pyarrow" 2>/dev/null || python3 -m pip install -q "pandas==2.3.3" lightgbm scikit-learn pyarrow
mkdir -p $S
for d in daily edge26 r27 r28 r30 r31 r33 r35 r36 ml26 tadawul; do cp -r $R/$d $S/; done; cp -r $R/strat26 $S/strat
mkdir -p $S/edge26/data/d $S/edge26/data/div $S/edge26/data/ext $S/edge26/data/idx $S/edge26/data/us100 $S/r33/fund $S/daily/out $S/r27/preds
# small files the pipeline needs that are not code: Tadawul listings after 2020 (Yahoo probe), their names,
# market momentum 2003-2012 from the 2001-2020 library (the library itself is not in the repo), the US large-cap list
cp $R/daily/restore/new_codes.json $S/edge26/data/new_codes.json; cp $R/daily/restore/extra_names.json $S/edge26/extra_names.json
cp $R/daily/restore/ms_hist_pre2013.json $S/r31/ms_hist.json; cp $R/daily/restore/us100_list.json $S/edge26/us100_list.json
rm -f $S/r27/py.pkl $S/r27/W_core.pkl $S/r27/F27y.pkl
FULL=1 sh $S/daily/run.sh
