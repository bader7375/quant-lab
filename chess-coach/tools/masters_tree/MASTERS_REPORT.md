# Masters opening tree

Built by `tools/masters_tree/build.py` (log `/tmp/claude-0/masters_build.log`), checked by `tools/masters_tree/validate.py` (PASS, 0 failed).

- Source: KingBase 2017 (kingbase-chess.net, mirrored in github.com/rozim/ChessData), 55 PGN files, 1,796,954 games,
  1990–2017, master games with players rated about 2000+. 145 games without a result were skipped; no illegal moves or
  non-standard starts. KingBase is free for personal and non-commercial use; only aggregate move counts are shipped.
- Opening names: lichess-org/chess-openings (CC0), 3,865 positions (`openings.json`, 464 KB).
- Positions: first 24 plies, key = FEN fields 1–4 with the en-passant square only when the capture is legal. 7,729,018 distinct
  positions; trade-off (plies, min games → positions): 24/50 → 56,856 (8.1 MB, over budget), **24/75 → 39,021 (shipped)**, 24/100 →
  29,799, 20/75 → 34,503. Moves kept: n ≥ max(2, 0.5% of the position), at most 12 per position, the rest in "other".
- Files: `index.json` + 5 shards (`fnv1a32(key) % 5`), 1.14–1.17 MB each; total with names 6.24 MB.
- Validation (`validate.py`): an independent recount with python-chess's own PGN reader over all games matches the shipped counts
  exactly for the start position (1,796,817), 1.e4 e5 (164,975), the Italian after 3.Bc4 (21,769), the QGD after 2...e6
  (43,020) and 10 random positions, including "other". JS `keyOf` equals python-chess `epd()` on 12,017 positions (75 with a legal
  en-passant capture, 3,650 with an ep square but no legal capture). White's score from the start: 0.545. Transpositions merge
  (1.d4 Nf6 2.c4 e6 = 1.c4 e6 2.d4 Nf6: 100,258 games).
- Repertoire coverage (positions with 75+ games): the Italian, 1...e5 lines and the QGD stay in the tree well past move 8.
