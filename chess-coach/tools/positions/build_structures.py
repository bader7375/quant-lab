"""Chapter 7 pool, step 1: middlegame positions (moves 12-30) from KingBase master games in openings where the classic
structures arise (QGD, Nimzo/Queen's Indian, French, King's Indian, Sicilian, closed openings), with the master's move.
tag_structures.mjs then keeps the positions with a recognised structure and a sound master move.
usage: python -I tools/positions/build_structures.py <kingbase dir> /tmp/.../ch07-raw.json"""
import sys, os, json, random, glob
import chess.pgn
src, out = sys.argv[1], sys.argv[2]; random.seed(7)
groups = ["D30-D69", "E20-E59", "C00-C19", "E60-E99", "D00-D29", "B20-B49", "A40-A79"]
items = []
for gname in groups:
    files = sorted(glob.glob(os.path.join(src, f"KingBase2017-{gname}*.pgn"))); n = 0
    for fn in files[-2:]:
        with open(fn, encoding="latin-1") as f:
            while n < 1500:
                g = chess.pgn.read_game(f)
                if g is None: break
                h = g.headers
                try: we, be = int(h.get("WhiteElo", 0)), int(h.get("BlackElo", 0))
                except ValueError: continue
                if min(we, be) < 2300: continue
                moves = list(g.mainline_moves())
                if len(moves) < 44: continue
                n += 1; b = g.board()
                for k, mv in enumerate(moves[:60]):
                    if k >= 22 and k % 3 == 0:
                        items.append({"fen": b.fen(), "mv": mv.uci(), "san": b.san(mv), "ply": k, "r": (we + be) // 2,
                                      "w": h.get("White", "?"), "bl": h.get("Black", "?"), "y": h.get("Date", "????")[:4], "eco": h.get("ECO", "")})
                    b.push(mv)
    print(gname, n, len(items))
json.dump(items, open(out, "w"), separators=(",", ":"), ensure_ascii=False)
