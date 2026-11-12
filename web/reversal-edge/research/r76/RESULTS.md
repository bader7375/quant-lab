# Round 76 results: the anatomy of a buy-zone cross (plan in PREREG.md; a description, nothing judged)
Scripts and outputs: r76 (.out, _results.json), map76 (.out, .json). Other markets: 24 markets, 186,197 crosses, 2001-26.
Saudi: 2013-19 only, 10,105 crosses (every window ends by 2019-12-31). Returns are net of 0.4% costs; ranges resample months.

## 1. Enter on the cross down, not on the cross back up
5 sessions after the event, other markets, line -2.0:
| weather | cross DOWN into the zone | cross back UP out of it |
|---|---|---|
| calm | +0.27% | -0.32% |
| clouds | +0.37% | -0.01% |
| storm | +0.51% | -0.20% |
| deep | +1.81% | +0.43% |
The same at every line. Waiting for the turn costs the first days of the bounce (as rounds 42 and 63 found for candles).

## 2. Weather decides, and in Saudi it decides almost everything
After a cross down at -2.0, sold when the stretch Z is back at -1 (40 sessions at most):
| weather | other markets | Saudi 2013-19, all liquid | Saudi 2013-19 with the ML and market-model gates |
|---|---|---|---|
| calm | +0.8% (+0.5 to +1.0), 11 sessions | +0.5% (-0.5 to +1.4) | +1.7% (-0.3 to +3.8), 42 cases |
| clouds | +1.4% (+0.9 to +1.8) | -3.0% (-7.8 to +1.4) | +2.3% (-4.2 to +4.3), 41 cases |
| storm | +2.0% (+1.6 to +2.5) | +0.1% (-4.1 to +3.3) | +3.9% (+1.6 to +5.4) |
| deep | +5.7% (+5.1 to +6.3) | +3.4% (+0.9 to +5.4) | +4.4% (+2.3 to +6.1) |
- Above the average liquid stock over the same sessions the Saudi cross adds about nothing, except at very deep stretch (below
  -2.5 to -3). The gain is being in the market at that moment; the stock adds a little at the extremes.
- Calm and cloudy weather: a small, short bounce abroad; no reliable one in Saudi, and held longer it turns into losses there
  (clouds, sold at stretch Z 0: -7.5% a trade).

## 3. Selling when the stretch is gone: less per trade, more per day
Line -2.5, deep weather:
| sell at | other markets: result, sessions, per session | Saudi 2013-19 with gates |
|---|---|---|
| stretch Z -1 | +6.8%, 12, 55 bp | +8.6%, 12, 74 bp |
| stretch Z 0 | +9.2%, 24, 39 bp | +12.5%, 23, 54 bp |
| stretch Z +1 or 40 sessions | +10.2%, 37, 28 bp | +18.7%, 37, 51 bp |
Nearly every trade (97-100%) sees its stretch back at -1 within 40 sessions, often because time passes, not because the price
recovered. The pain on the way: the middle trade closes 4-6% under its entry at some point, one in ten 17-25% under.

## 4. The edge map (map76): the average next 5 sessions of a liquid stock by its stretch and the weather that day
- Other markets, deep weather: +4.1% below -3.5, +2.6% at -3 to -2.5, +2.3% at -2.5 to -2, +1.3% at -1.5 to -1, +0.4% at -0.5 to 0,
  +0.1% above 0. The edge of staying fades at about stretch Z 0. In a storm it fades near -0.5; in clouds near -1; in calm weather
  it is flat at +0.2% to +0.5% whatever the stretch.
- Saudi 2013-19 with gates: +4.5% to +5.0% below -3.5, +2.3% at -3 to -2.5, +0.7% to +1.2% at -2.5 to -2, about nothing above -1.5 in
  deep weather.
This map feeds the scanner's edge score (Saudi numbers pulled toward the other markets' where Saudi cases are few).
