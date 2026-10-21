"""Position pools for the "مواقف" drill, from real Lichess games with server analysis (the combined puzzle/game dataset).
usage: python -I tools/positions/build_pools.py <dataset.ndjson.bz2> <out_dir>
Each pool item: {fen, g (lichess game id), r (average rating), ply}; ch02-safety adds x, the move actually played (the mistake). A position is the one BEFORE the move at `ply`.
  ch01-opening : plies 8-16, both players 1000-1800, the position still balanced (|eval| <= 120 cp): play the next moves
  ch02-safety  : the position just before a move that dropped 250+ cp while a safe move existed (eval for the mover >= -120)
  ch02-punish  : the position just after that move, when the punisher stands 250+ cp better
  ch03-mates   : side to move has a forced mate in 1-4 (Lichess analysis), from ply 20 on
Evaluations are Lichess's (Stockfish on the server); the app re-checks every move live with Stockfish 17.1."""
import bz2, json, sys, random, os
import chess
src, out = sys.argv[1], sys.argv[2]
random.seed(7)
pools = {k: [] for k in ("ch01-opening", "ch02-safety", "ch02-punish", "ch03-mates")}
CAP = {"ch01-opening": 3000, "ch02-safety": 2500, "ch02-punish": 2500, "ch03-mates": 3000}
def ev(a):  # White's view in cp; mate as +-10000-ish
    if a is None: return None
    if 'mate' in a: return 10000 - 10 * abs(a['mate']) if a['mate'] > 0 else -10000 + 10 * abs(a['mate'])
    return a.get('eval')
seen = set(); n = 0
with bz2.open(src, 'rt') as f:
    for line in f:
        n += 1
        d = json.loads(line); g = d['game']
        try: wr = g['players']['white']['rating']; br = g['players']['black']['rating']
        except KeyError: continue
        an = g.get('analysis') or []
        if not an: continue
        r = (wr + br) // 2; moves = g['moves'].split(); b = chess.Board()
        for k, san in enumerate(moves[:120]):
            if k >= len(an): break
            fen = b.fen(); stm = 1 if b.turn else -1
            before = 30 if k == 0 else ev(an[k - 1]); after = ev(an[k])
            key = ' '.join(fen.split()[:4])
            if before is not None and after is not None and key not in seen:
                item = {"fen": fen, "g": g['id'], "r": r, "ply": k}
                if 8 <= k <= 16 and 1000 <= min(wr, br) and max(wr, br) <= 1800 and abs(before) <= 120 and random.random() < 0.25:
                    pools["ch01-opening"].append(item); seen.add(key)
                elif 10 <= k <= 60 and 900 <= r <= 2000 and stm * before >= -120 and abs(before) < 900 and stm * (before - after) >= 250:
                    mv = b.parse_san(san); b2 = b.copy(); b2.push(mv)
                    pools["ch02-safety"].append({**item, "x": san}); seen.add(key)
                    if -stm * after >= 250 and -stm * after < 2000 and not b2.is_game_over():
                        pools["ch02-punish"].append({"fen": b2.fen(), "g": g['id'], "r": r, "ply": k + 1}); seen.add(' '.join(b2.fen().split()[:4]))
                elif k >= 20 and 'mate' in an[k - 1] and stm * an[k - 1]['mate'] > 0 and stm * an[k - 1]['mate'] <= 4 and random.random() < 0.5:
                    item["m"] = abs(an[k - 1]['mate']); pools["ch03-mates"].append(item); seen.add(key)
            try: b.push_san(san)
            except ValueError: break
os.makedirs(out, exist_ok=True)
for k, items in pools.items():
    random.shuffle(items); items = items[:CAP[k]]
    if k == "ch03-mates": items.sort(key=lambda x: x["m"])
    json.dump({"id": k, "source": "Lichess games with server analysis (mcognetta combined puzzle/game DB, first 50k)", "n": len(items), "items": items}, open(os.path.join(out, k + ".json"), "w"), separators=(',', ':'))
    print(k, len(items), os.path.getsize(os.path.join(out, k + ".json")), "bytes", "| mates by N:" if k == "ch03-mates" else "", {m: sum(1 for x in items if x.get('m') == m) for m in (1, 2, 3, 4)} if k == "ch03-mates" else "")
print("games read", n)
