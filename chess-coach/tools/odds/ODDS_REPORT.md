# Human-level odds model ("your chances at your level")

`data/models/odds.json`, fitted by `tools/odds/fit_odds.py` (log of the shipped run: `/tmp/claude-0/odds/fit_run2.log`, reproduced in
`odds.json` → `meta`). Format check: `node tools/odds/check_prob.mjs` → PASS (442 checks; `js/prob.js` reproduces the Python
predictions to 1e-16, with and without phases).

## What it predicts
P(White wins / draw / Black wins) for players of a rating band, from the Stockfish 17.1 evaluation of the position (centipawns,
White's view) and the game phase. Ordered logit: `z = a·cp/100`, `P(Black) = σ(t1 − z)`, `P(White) = 1 − σ(t2 − z)`, cp clipped to ±800.
The app's move classes are drops in expected score (W + D/2) under this model.

## Data
- `combined_puzzle_db_first_50k.ndjson.bz2`: 51,200 Lichess games with server analysis (one eval per ply). 51,194 eligible.
- Filters: rated standard, |White − Black| ≤ 150, **rapid or classical** (30,568 games: 24,469 train / 6,099 test; split by md5 of the
  game id, test untouched until the end; blitz kept only for comparison).
- Alignment verified: `analysis[k-1]` is the eval after ply k (Spearman 0.984 against Stockfish 17.1 on 1,848 positions; one ply
  earlier/later 0.81/0.82). Sign is White's view (checkmates: White mated → −, Black mated → +, 16,448 cases, no exceptions).
- **Selection bias, and how it is handled.** Every game produced a Lichess puzzle: the generator picks games where one side
  blundered (eval jump from ≤ +300 to ≥ +200 for the other side). Positions *before* that blunder are biased by construction (the
  side that was better went on to blunder: their score falls as their eval rises). The model is therefore fitted and tested only on
  positions **after** the puzzle blunder, whose future is not used by the selection (631,296 train positions; ≤ 16 per game in CV).
- **The generator skips every game with a player rated ≤ 1500.** Fitted games have mean ratings 1501–2650 (bulk 1600–2300).
  Bands 800–1400 — including the default 1100 — are **extrapolated** from the linear-in-rating trend of the parameters
  (`meta.bands_extrapolated`). The app labels the odds bar "مستقرأ" for those bands.

## Evaluation scale
Lichess server evals come from an older Stockfish. 1,584 positions were re-evaluated with Stockfish 17.1 (depth 14,
`tools/odds/sf_rescore.mjs`): Huber fit `sf17 = 3.7 + 0.610 · lichess` (95% CI of the slope 0.599–0.622, R² 0.921, robust residual
SD 44 cp). The slope drifts by year (0.80 in 2016 → 0.54 in 2022: newer server engines report larger numbers). A power-law
mapping was not better (log-loss difference CI includes 0), so the linear one is used: every Lichess eval is converted to SF17
units before fitting, and the shipped parameters are in Stockfish 17.1 centipawns. An outcome-based check of the scale
(multiplier 1.03, CI 0.95–1.12) found no correction needed.

## Model selection (5-fold CV by game, train only)
- clip: 800 cp (600 equivalent; 400, 1000+ clearly worse).
- Rating dependence: `a`, the mid-cut and the draw width are linear in rating (log scale for `a` and the width), so bands are
  smooth and extrapolation is explicit. Pooled (no band) and per-band free parameters were not better on CV.
- **Phases** (`js/facts.js` phaseOf): relative log-loss reduction 2.7% (CI 2.4–3.0%) on CV and 3.4% (CI 2.8–4.1%) on test →
  included, as the pre-set rule required both.

## Held-out results (6,099 test games, game-clustered bootstrap 95% CIs)
| model | log loss | Brier |
|---|---|---|
| fitted, with phases (shipped) | **0.500** [0.484, 0.516] | **0.274** [0.265, 0.283] |
| fitted, no phases | 0.518 [0.501, 0.536] | 0.279 [0.268, 0.288] |
| pooled ordered logit (no bands) | 0.519 [0.502, 0.536] | 0.279 [0.269, 0.288] |
| provisional (Lichess curve + 6% draws) | 0.584 [0.559, 0.610] | 0.283 [0.273, 0.293] |

Provisional − fitted: +0.066 log loss [0.055, 0.077] (12.7% relative). By rating group (no-phase model vs provisional):
1450–1699 0.544 vs 0.622; 1700–1899 0.511 vs 0.571; 1900–2099 0.505 vs 0.569; 2100+ 0.532 vs 0.604.
Calibration by predicted-score decile is close to the diagonal (e.g. decile 4: predicted 0.225, observed 0.191; decile 7: 0.778 vs
0.809; full table in `meta.held_out.calibration_deciles`).

## What changes in the app (band 1100, extrapolated)
Expected score for White: −300 cp 30%, −100 cp 44%, 0 cp 51%, +100 cp 58%, +300 cp 71%, +500 cp 81% (95% CIs ≈ ±3 points).
The curve is flatter than the provisional one (+500 cp was 86%), so move classes are slightly milder: a +0.3 → −0.8 drop is
an inaccuracy (was a mistake); +1.5 → −1.5 and +5 → +1 stay blunders. Thresholds (2/5/10/20 points) are unchanged.
**Mates:** Stockfish's mate-in-n now counts as ±800 cp (≈ 90–95% at band 1100) instead of certainty — in the data the side with
a mate score wins less often than that; only checkmate on the board is certain.

## Limitations
- Sub-1500 bands are extrapolations; the curve's shape there is an assumption (the parameters' linear trend in rating).
- Positions after a blunder only: the model has never seen calm, balanced positions from equal games as such; held-out
  "before the blunder" positions are worse for every model by construction (selection), so they cannot be used to check this.
- Online rapid/classical games, not untimed games against a computer.
- Draw rates are low (5.5% of games), as is typical for online play at these ratings.
