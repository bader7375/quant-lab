# Maia-1 in JavaScript

`engines/maia/` runs the nine Maia-1 networks (CSSLab, github.com/CSSLab/maia-chess, **GPL-3.0**; this port is GPL-3.0 too) in a
browser Web Worker: the app's human-like opponent and its "players at your level" lines.

## Files
- `tools/maia/convert.py`: lc0 protobuf (`maia-<r>.pb.gz`, uint16 linearly quantized layers) → `engines/maia/maia-<r>.bin`
  (batch norm folded into the convolutions, float16) + `manifest.json` (layers, shapes, offsets, encoding notes).
  Each file 1,731,152 bytes; all nine 14.9 MiB.
- `tools/maia/ref.py`: independent numpy forward pass + lc0 input encoder (python-chess).
- `engines/maia/maia.js`: dependency-free inference (Winograd 3×3 convolutions), legal-move softmax, SAN via chess.js.
- `engines/maia/worker.js`: `{type:"init", rating}` → `ready`; `{type:"eval", id, startFen, moves}` → `{policy, value, ms}`.
- `tools/maia/validate.mjs`: everything below (full run: `--per-band 1000 --special 1000`, 1,775 s; log
  `/tmp/claude-0/maia-work/full2.log`).

## Architecture and encoding (decoded from the weights, not assumed)
SE-ResNet, 6 blocks × 64 filters, convolutional policy head (80×8×8, mapped through lc0's 1858-move table), WDL value head.
Input: lc0 `INPUT_CLASSICAL_112_PLANE` — 8 history positions × 13 planes from the side to move's view (board flipped for Black),
then castling (ours O-O-O, O-O, theirs), black-to-move, rule-50, a zero and a ones plane. Missing history at the start of a game
is zeros (lc0's default for games from the standard position: 56.7–66.7% top-1 on plies 0–9 vs 41.7–58.3% when filling with copies).
Castling is king-to-rook (e1h1) in the policy; promotions to q/r/b use the underpromotion planes, the knight promotion is the
plain move.

## Validation
**JS vs numpy reference** (377 positions: Black to move, castling, promotions, en passant, short history, repetitions, terminal):
top-1 identical 377/377 for every net; max |Δp| ≤ 2.8e-6. Against the original fp32 weights with unfolded batch norm: top-1
identical in 3,391 of 3,393 net-positions; max |Δp| ≤ 3.1e-3 (float16 storage).

**Move-matching** (held-out Lichess games, bullet excluded, plies ≥ 10; matched net = the player's rating clamped to 1100–1900):
**53.0% [51.8–54.2]** top-1 over 7,088 positions (Maia-1 paper: about 50–53%). Per band (matched net): 1500s 54.9%, 1600s 54.1%,
1700s 51.2%, 1800s 54.6%, 1900s 53.4%. The diagonal is weak in this data: higher-rated nets do as well or better in every band.
Moves Lichess judged fine: 60.8%; inaccuracies 35.6%; the blunders that created the puzzles 43.3%.
- Castling (n=1000): 74–78% top-1 with king-to-rook; 0% with the king-two-squares encoding → encoding confirmed.
- Promotions (n=3039): =Q 88.2% (0.1% with queen/knight planes swapped → confirmed); =N 0/58 and =R 0/19 (Maia gives
  underpromotions little probability; the swapped control is confounded by the queen plane's mass, so knight underpromotion
  encoding is consistent with lc0 but not independently confirmed).
- **Not validated at the app's level:** the dataset has 0 players rated 1000–1499 (the puzzle generator skips them) and 88
  positions under 1000 (best net ~35%). Maia-1100 for the 1100 student is used on the paper's evidence, not this data's.

**Value head**: Brier skill over a constant is small (2.8% under 1000; larger bands in the log) — it is not used for the odds.

**Temperature** (fitted on a dev split, reported on test): players under 1000 are best matched by maia-1100 at T = 1.3
(log-likelihood −1.824 vs −1.856 at T = 1). The app samples the opponent's move from Maia's probabilities, T = 1 for 1100–1900,
T = 1.3 below 1100, never a move under 1%.

**Speed** (Node, one thread, machine shared): 9.2 ms per move during play (p95 14.8), 13.8 ms cold; load 51 ms.
