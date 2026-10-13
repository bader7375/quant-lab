"""Validate the masters tree in data/masters/ (run after build.py).

  /tmp/claude-0/venv/bin/python tools/masters_tree/validate.py [--procs 3]

1. Independent recount: a separate, deliberately simple scan of ALL KingBase games (python-chess replay of the first plies, no
   shared code with build.py) counts the next moves and results for named positions and 10 random kept positions; the shipped
   numbers must match exactly (moves cut by the thresholds must add up to "other").
2. JS/Python key equivalence on >= 10,000 positions from real games (Node + js/masters.js keyOf vs python-chess epd()),
   including positions after double pawn pushes with and without a legal en-passant capture.
3. Orientation: White's score at the start position. 4. Transposition: 1.d4 Nf6 2.c4 e6 == 1.c4 e6 2.d4 Nf6. 5. Sizes.
Prints PASS/FAIL per check and exits 1 on any failure.
"""
import argparse, glob, hashlib, io, json, os, random, re, subprocess, sys
from multiprocessing import Pool
import chess, chess.pgn

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
OUT = os.path.join(ROOT, "data", "masters"); SRC = "/tmp/claude-0/kingbase-src/Kingbase"
FAILS = []
def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond: FAILS.append(msg)

def fnv1a32(s):
    h = 0x811C9DC5
    for c in s.encode(): h ^= c; h = (h * 0x01000193) & 0xFFFFFFFF
    return h

IDX = json.load(open(os.path.join(OUT, "index.json")))
SHARDS = {}
def entry(key):
    s = fnv1a32(key) % IDX["shards"]
    if s not in SHARDS: SHARDS[s] = json.load(open(os.path.join(OUT, f"s{s:02d}.json")))
    return SHARDS[s].get(key)

def key_after(sans):
    b = chess.Board()
    for s in sans: b.push_san(s)
    return b.epd()

def scan(args):
    """Simple independent counter: python-chess's own PGN reader, first `plies` plies, only for the wanted keys."""
    path, wanted, plies = args
    res = {"1-0": 0, "1/2-1/2": 1, "0-1": 2}
    out = {k: {} for k in wanted}
    with open(path, encoding="latin-1") as f:
        while True:
            g = chess.pgn.read_game(f)
            if g is None: break
            r = res.get(g.headers.get("Result"))
            if r is None or "FEN" in g.headers or g.headers.get("SetUp") == "1": continue
            b = g.board()
            for k, mv in enumerate(g.mainline_moves()):
                if k >= plies: break
                key = b.epd()
                if key in out:
                    c = out[key].setdefault(b.san(mv), [0, 0, 0]); c[r] += 1
                b.push(mv)
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    named = {
        "start": [], "1.e4 e5": ["e4", "e5"], "Italian 1.e4 e5 2.Nf3 Nc6 3.Bc4": ["e4", "e5", "Nf3", "Nc6", "Bc4"],
        "QGD 1.d4 d5 2.c4 e6": ["d4", "d5", "c4", "e6"],
    }
    keys = {name: key_after(s) for name, s in named.items()}
    # 10 random kept positions (deterministic)
    allk = []
    for f in sorted(glob.glob(os.path.join(OUT, "s*.json"))): allk += list(json.load(open(f)).keys())
    rnd = random.Random(7); rand = rnd.sample(allk, 10)
    for i, k in enumerate(rand): keys[f"random{i}"] = k
    # the recount needs every ply up to the deepest wanted position
    plies = IDX["plies"]
    files = sorted(glob.glob(os.path.join(SRC, "KingBase2017-*.pgn")))
    wanted = set(keys.values())
    with Pool(a.procs) as pool: parts = pool.map(scan, [(f, wanted, plies) for f in files])
    tot = {k: {} for k in wanted}
    for p in parts:
        for k, mv in p.items():
            for s, c in mv.items():
                t = tot[k].setdefault(s, [0, 0, 0])
                for i in range(3): t[i] += c[i]
    print("== 1. independent recount")
    for name, k in keys.items():
        e = entry(k); rc = tot[k]; n_rc = sum(sum(c) for c in rc.values())
        if e is None: check(False, f"{name}: missing from the shipped tree"); continue
        total, moves, other = e
        same = all(rc.get(s, [0, 0, 0]) == [w, d, l] and n == w + d + l for s, n, w, d, l in moves)
        rest = n_rc - sum(m[1] for m in moves)
        check(total == n_rc and same and rest == other, f"{name}: total {total} vs recount {n_rc}; shipped moves match {same}; other {other} vs {rest}")
    print("== 2. JS/Python key equivalence")
    sample = []; eps_legal = eps_illegal = 0
    with open(files[0], encoding="latin-1") as f:
        while len(sample) < 12000:
            g = chess.pgn.read_game(f)
            if g is None: break
            b = g.board()
            for mv in g.mainline_moves():
                b.push(mv)
                if rnd.random() < 0.15 or b.ep_square is not None:
                    fen = b.fen(en_passant="fen")  # chess.js-style: ep square after every double push
                    sample.append([fen, b.epd()])
                    if b.ep_square is not None:
                        if b.has_legal_en_passant(): eps_legal += 1
                        else: eps_illegal += 1
    js = """const M=require(process.argv[1]+'/js/masters.js');let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{const a=JSON.parse(s);let bad=0,ex=[];for(const [fen,epd] of a){const k=M.keyOf(fen);if(k!==epd){bad++;if(ex.length<3)ex.push([fen,k,epd]);}}console.log(JSON.stringify({n:a.length,bad,ex}));});"""
    r = subprocess.run(["node", "-e", js, os.path.abspath(ROOT)], input=json.dumps(sample), capture_output=True, text=True)
    res = json.loads(r.stdout or '{"n":0,"bad":-1}')
    check(res["n"] >= 10000 and res["bad"] == 0 and eps_legal > 0 and eps_illegal > 0,
          f"keyOf on {res['n']} positions: {res['bad']} mismatches (ep legal {eps_legal}, ep present but illegal {eps_illegal}) {res.get('ex', '')}")
    print("== 3. orientation")
    e = entry(keys["start"]); w = sum(m[2] for m in e[1]); d = sum(m[3] for m in e[1]); l = sum(m[4] for m in e[1])
    sc = (w + d / 2) / (w + d + l); check(0.52 <= sc <= 0.58, f"White's score from the start position {sc:.3f} (W {w} D {d} L {l})")
    print("== 4. transposition")
    k1, k2 = key_after(["d4", "Nf6", "c4", "e6"]), key_after(["c4", "e6", "d4", "Nf6"])
    check(k1 == k2 and entry(k1) is not None, f"1.d4 Nf6 2.c4 e6 and 1.c4 e6 2.d4 Nf6 share a key present in the tree ({entry(k1)[0] if entry(k1) else None} games)")
    print("== 5. sizes")
    sizes = [os.path.getsize(f) for f in glob.glob(os.path.join(OUT, "*.json"))]
    check(max(sizes) <= 1_500_000 and sum(sizes) <= 6_500_000, f"{len(sizes)} files, total {sum(sizes):,} bytes, largest {max(sizes):,}")
    print(f"\n{'FAIL' if FAILS else 'PASS'} ({len(FAILS)} failed)")
    sys.exit(1 if FAILS else 0)

if __name__ == "__main__":
    main()
