# Round 27 - Saudi deep dive (stretch Z, Saudi features, advanced ML, data correction)
Read `PREREG.md` (plan and pass/fail rules written first), `selection_rule.txt` (ML choice rule, written before evaluation) and `RESULTS.md`.
Scripts expect the scratch layout used during the research: `../edge26` (Yahoo data in `data/d`, `data/ext`, `data/div`; fixed `panel.py`),
`../ml26`, `../strat` (= `strat26` here), `../eng/tad` (2001-2020 Tadawul library) and `../tadawul/meta.json`. Price data is not committed.
Order: base/zfam/feats27 (shared) -> z_map, z_trig, z_scale (H1) -> h2_* (H2) -> ds27, wf27 NAME, eval27 design|confirm, mkt27, gate_test (H3)
-> core_tune, core_final, z_robust_clean, trend_trades (H4) -> record27, final27 (daily export to the artifact db: ml/latest) and strat26/sector_export.py (ml/sectors).
`patch_v15*.py` are the edits that turned the v14 page into v15; `t28_browser_test.py` is the browser check (page stretch Z equals the Python value).
