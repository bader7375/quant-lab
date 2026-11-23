# v33 checks (Industry Z panel)
- iz_py.py: research values of industry Z (round 72 definition) and test 'bars' documents built from the Yahoo files.
- iz_node.js: runs the page's own Industry Z code (extracted from index.html) on 'bars' documents and compares with the research.
  Result 2026-11-13: same definition (adjusted traded value) correlation 1.000, max difference 0.00 on most industries;
  round 72's raw-value definition: correlation 0.996-1.000, the same zone (<= -1.0 / -1.0..-0.5 / > -0.5) on 96-100% of days 2019-26.
- iz_find.js / iz_last.js: found and explained the two data issues (suspended stocks' flat zero-volume rows; 91 stored stocks
  not refreshed by the 15:48 data task since 2026-10-22).
- vt33*.js: Playwright tests through the real UI with a mock database (all stored bars, ml/latest, ml/sectors): panel, legend,
  plan text at a Z touch (data cut at 2026-11-03), US stock (no panel), panel switch off/on, phone width (no horizontal scroll).
