# Example runs

## Single instrument — TSLA

`REPORT.md` plus nine charts. The full adaptive stack: eleven engines, pattern
mining, regime clustering, meta-learner, RL sizing layer. Verdict: no edge.

## Multi-instrument — 40 S&P 500 names

Two runs of the **identical** pipeline and settings, differing only in how much
history they were given. Read them side by side; that is the point.

| file | period | trades | traded days | R/day | day-level t | verdict |
|---|---|---:|---:|---:|---:|---|
| `PANEL_REPORT_full_2013-2018.md` | 2013-02 → 2018-02 | 6,090 | 467 | +0.105 | **+2.35** | all four gates pass |
| `PANEL_REPORT_research_2013-2016.md` | 2013-02 → 2016-12 | 2,165 | 165 | −0.014 | **−0.15** | fails two gates |

The full-period run looks like a strategy: four folds with proper samples, three
of four positive, every fold beating its own baseline, positive in 2016, 2017
and 2018, and a 95% interval that excludes zero.

The research-period run is the same method on the earlier window and it is flat.

The extra data in the first run is 2017–2018 — the period that had been locked
away during development and was therefore examined *last*, after the threshold
logic was revised. That is what selection bias looks like from the inside, and
it is why the platform reports the trial count and the deflated t next to every
headline number.

`panel_scan.csv` is the ranked latest-bar output: every instrument scored, with
its stop, target and decision.
