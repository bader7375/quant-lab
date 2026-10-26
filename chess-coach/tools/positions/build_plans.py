"""Chapter 6 pool: middlegame positions (moves 11-25) from KingBase master games, with the move the master played.
tag_pools.mjs then keeps the positions where the master's move is a plan move (open file, worst piece, pawn break,
outpost) and Stockfish rates it within 40 cp of its best move.
usage: python -I tools/positions/build_plans.py <kingbase dir> data/positions/ch06-plans.json"""
import sys, os, json, random, glob
import chess, chess.pgn
src, out = sys.argv[1], sys.argv[2]; random.seed(6)
groups = ["C20-C59", "D30-D69", "C60-C99", "E20-E59", "B20-B49", "A40-A79"]
items = []
for gname in groups:
    files = sorted(glob.glob(os.path.join(src, f"KingBase2017-{gname}*.pgn")))
    n = 0
    with open(files[-1], encoding="latin-1") as f:  # the newest part of each group
        while n < 900:
            g = chess.pgn.read_game(f)
            if g is None: break
            h = g.headers
            try: we, be = int(h.get("WhiteElo", 0)), int(h.get("BlackElo", 0))
            except ValueError: continue
            if min(we, be) < 2300 or h.get("Result") not in ("1-0", "0-1", "1/2-1/2"): continue
            moves = list(g.mainline_moves())
            if len(moves) < 50: continue
            n += 1; b = chess.Board(); plies = set(random.sample(range(20, 50), 4))
            for k, mv in enumerate(moves[:50]):
                if k in plies:
                    items.append({"fen": b.fen(), "mv": mv.uci(), "san": b.san(mv), "ply": k, "r": (we + be) // 2,
                                  "w": h.get("White", "?"), "bl": h.get("Black", "?"), "y": h.get("Date", "????")[:4], "eco": h.get("ECO", "")})
                b.push(mv)
    print(gname, n)
random.shuffle(items)
json.dump({"id": "ch06-plans", "source": "KingBase 2017 master games (players 2300+), moves 11-25", "n": len(items), "items": items}, open(out, "w"), separators=(",", ":"), ensure_ascii=False)
print(len(items))
