# v22 scanner: Saudi and US stretch-Z scans for the next session
No new research. The daily export (final27.py -> ml/latest) now carries `zscan`: Saudi fresh daily/weekly stretch-Z touches first
(buyable ones by ML rank, then skipped ones), then the most stretched liquid stocks; each row has close, day change, stretch Z, weekly Z,
ML rank and the loss flag. us_signal.py adds `us_scan`: the same for the 115 US large caps (US lines -1.67 daily / -1.13 weekly) with RSI(2),
the 200-day average and the US sell-off window (market momentum <= -1.18). The Scanner tab shows both tables with each row's next-session status.
