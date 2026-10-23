"""Chapter 4 pool: positions from real Lichess games right after the opponent's mistake or blunder, when the side to move
now stands 250+ cp better than before that move (a tactic is usually there). Tagged later by tag_pools.mjs, and only
items whose best move carries a tactical motif are kept (see keep_motifs in tag_pools.mjs).
usage: python -I tools/positions/build_tactics.py <dataset.ndjson.bz2> data/positions/ch04-tactics.json"""
import bz2, json, sys, random
import chess
src, out = sys.argv[1], sys.argv[2]; random.seed(11)
def ev(a):
    if a is None: return None
    if 'mate' in a: return 10000 - 10 * abs(a['mate']) if a['mate'] > 0 else -10000 + 10 * abs(a['mate'])
    return a.get('eval')
items = []; seen = set()
with bz2.open(src, 'rt') as f:
    for line in f:
        g = json.loads(line)['game']
        try: r = (g['players']['white']['rating'] + g['players']['black']['rating']) // 2
        except KeyError: continue
        an = g.get('analysis') or []; moves = g['moves'].split(); b = chess.Board()
        for k, san in enumerate(moves[:100]):
            if k >= len(an): break
            try: b.push_san(san)
            except ValueError: break
            if k < 12 or k + 1 >= len(moves) or b.is_game_over(): continue
            j = (an[k].get('judgment') or {}).get('name')
            if j not in ('Mistake', 'Blunder'): continue
            stm = 1 if b.turn else -1; before = ev(an[k - 1]); after = ev(an[k])
            if before is None or after is None or abs(after) >= 2000: continue
            if stm * after - stm * before >= 250 and stm * after >= 200 and stm * before <= 150:
                key = ' '.join(b.fen().split()[:4])
                if key in seen: continue
                seen.add(key); items.append({"fen": b.fen(), "g": g['id'], "r": r, "ply": k + 1})
random.shuffle(items); items = items[:7000]
json.dump({"id": "ch04-tactics", "source": "Lichess games with server analysis (mcognetta combined puzzle/game DB, first 50k)", "n": len(items), "items": items}, open(out, 'w'), separators=(',', ':'))
print(len(items))
