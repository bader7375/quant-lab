"""Masters opening tree from KingBase 2017 (master games, players rated about 2000+), shipped as static JSON shards.

  /tmp/claude-0/venv/bin/python tools/masters_tree/build.py [--plies 24] [--min-games 50] [--procs 3]

Input:  /tmp/claude-0/kingbase-src/Kingbase/KingBase2017-*.pgn   (github.com/rozim/ChessData, sparse checkout)
        /tmp/claude-0/chess-openings/[a-e].tsv                    (github.com/lichess-org/chess-openings, CC0)
Output: data/masters/index.json, data/masters/sNN.json, data/masters/openings.json

Position key: python-chess board.epd() = the FEN's first four fields, with the en-passant square only when an en-passant
capture is legal (so transpositions merge). js/masters.js computes the same key with chess.js.
Shard of a key = fnv1a32(key) % S. Shard content: { key: [total, [[san, n, w, d, l], ...], other] }, w/d/l = White wins /
draws / Black wins.

Pass 1 replays the first P plies of every game once and records (hash of the position before the ply, move id, result,
game id, ply). Everything after that is numpy: position totals, the threshold, per-move counts.
"""
import argparse, glob, hashlib, json, os, re, sys, time
from multiprocessing import Pool
import numpy as np
import chess

SRC = "/tmp/claude-0/kingbase-src/Kingbase"
OPEN = "/tmp/claude-0/chess-openings"
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "data", "masters")
RES = {"1-0": 0, "1/2-1/2": 1, "0-1": 2}

TAG = re.compile(r'^\[(\w+)\s+"(.*)"\]\s*$')
TOKEN_STRIP = re.compile(r"\{[^}]*\}|;[^\n]*|\$\d+")
MOVENUM = re.compile(r"^\d+\.(\.\.)?$|^\d+\.\.\.$")


def h64(key):
    return int.from_bytes(hashlib.blake2b(key.encode(), digest_size=8).digest(), "little", signed=True)


def strip_variations(text):
    out, depth = [], 0
    for ch in text:
        if ch == "(": depth += 1
        elif ch == ")": depth = max(0, depth - 1)
        elif depth == 0: out.append(ch)
    return "".join(out)


def games(path):
    """Yield (tags, movetext) for each game in a PGN file."""
    tags, moves, in_moves = {}, [], False
    with open(path, encoding="latin-1") as f:
        for line in f:
            line = line.rstrip("\n")
            m = TAG.match(line)
            if m:
                if in_moves:
                    yield tags, " ".join(moves); tags, moves, in_moves = {}, [], False
                tags[m.group(1)] = m.group(2)
            elif line.strip():
                in_moves = True; moves.append(line)
            elif in_moves:
                yield tags, " ".join(moves); tags, moves, in_moves = {}, [], False
    if in_moves: yield tags, " ".join(moves)


def sans_of(movetext, plies):
    text = strip_variations(TOKEN_STRIP.sub(" ", movetext))
    out = []
    for tok in text.split():
        if MOVENUM.match(tok) or tok in RES or tok == "*": continue
        tok = re.sub(r"^\d+\.+", "", tok)
        if not tok: continue
        out.append(tok)
        if len(out) >= plies: break
    return out


def work(args):
    path, plies, fileno = args
    H, M, R, G, P = [], [], [], [], []
    vocab = {}
    stats = {"games": 0, "used": 0, "no_result": 0, "setup": 0, "illegal": 0, "years": {}}
    for gi, (tags, mt) in enumerate(games(path)):
        stats["games"] += 1
        r = RES.get(tags.get("Result"))
        if r is None: stats["no_result"] += 1; continue
        if tags.get("SetUp") == "1" or "FEN" in tags or (tags.get("Variant", "Standard") or "Standard").lower() not in ("standard", ""):
            stats["setup"] += 1; continue
        b = chess.Board(); ok = True
        gid = fileno * 10_000_000 + gi
        for k, san in enumerate(sans_of(mt, plies)):
            key = b.epd()
            try:
                mv = b.parse_san(san)
            except Exception:
                ok = False; break
            s = b.san(mv)  # canonical SAN (the PGN may write Nbd2 where Nd2 suffices, or omit +)
            H.append(h64(key)); M.append(vocab.setdefault(s, len(vocab))); R.append(r); G.append(gid); P.append(k)
            b.push(mv)
        if not ok: stats["illegal"] += 1
        stats["used"] += 1
        y = (tags.get("Date") or "????")[:4]
        stats["years"][y] = stats["years"].get(y, 0) + 1
    return (np.array(H, np.int64), np.array(M, np.int32), np.array(R, np.int8), np.array(G, np.int64), np.array(P, np.int8),
            list(vocab), stats, path)


def fnv1a32(s):
    h = 0x811C9DC5
    for c in s.encode():
        h ^= c; h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def replay_key(path, gid, ply, plies):
    gi = gid % 10_000_000
    for i, (tags, mt) in enumerate(games(path)):
        if i == gi:
            b = chess.Board()
            for san in sans_of(mt, plies)[:ply]: b.push_san(san)
            return b.epd()
    raise KeyError(gid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plies", type=int, default=24)
    ap.add_argument("--min-games", type=int, default=50)
    ap.add_argument("--max-moves", type=int, default=12)
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--shard-bytes", type=int, default=1_400_000)
    ap.add_argument("--dry", action="store_true", help="print the size trade-off table only")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(SRC, "KingBase2017-*.pgn")))
    print(f"{len(files)} PGN files"); t0 = time.time()
    cache = f"/tmp/claude-0/masters_pass1_p{a.plies}.npz"
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True); H, M, R, G, P = z["H"], z["M"], z["R"], z["G"], z["P"]; vocab = list(z["vocab"]); stats = z["stats"].item(); paths = list(z["paths"])
        print("pass 1 from cache", cache)
    else:
        with Pool(a.procs) as pool:
            parts = pool.map(work, [(f, a.plies, i) for i, f in enumerate(files)])
        # unify move vocabularies
        vocab, vid = [], {}
        Hs, Ms, Rs, Gs, Ps = [], [], [], [], []
        stats = {"games": 0, "used": 0, "no_result": 0, "setup": 0, "illegal": 0, "years": {}}
        paths = []
        for H, M, R, G, P, voc, st, path in parts:
            remap = np.array([vid.setdefault(s, len(vid)) for s in voc] or [0], np.int32)
            Hs.append(H); Ms.append(remap[M] if len(M) else M); Rs.append(R); Gs.append(G); Ps.append(P); paths.append(path)
            for k in ("games", "used", "no_result", "setup", "illegal"): stats[k] += st[k]
            for y, n in st["years"].items(): stats["years"][y] = stats["years"].get(y, 0) + n
        vocab = sorted(vid, key=vid.get)
        H, M, R, G, P = (np.concatenate(x) for x in (Hs, Ms, Rs, Gs, Ps))
        np.savez(cache, H=H, M=M, R=R, G=G, P=P, vocab=np.array(vocab, dtype=object), stats=np.array(stats, dtype=object), paths=np.array(paths, dtype=object))
    print(f"pass 1: {stats} records {len(H):,} in {time.time() - t0:.0f}s")

    # position totals
    uh, inv, cnt = np.unique(H, return_inverse=True, return_counts=True)
    print(f"distinct positions: {len(uh):,}")
    table = []
    for T in (20, 30, 50, 75, 100, 200):
        for Pmax in (16, 20, 24):
            sel = cnt[inv] >= T
            sel &= P < Pmax
            npos = len(np.unique(H[sel]))
            table.append((Pmax, T, npos))
    print("trade-off (plies, min games -> positions kept):")
    for row in table: print("  P=%2d T=%3d -> %7d" % row)
    if a.dry: return

    keep_pos = cnt >= a.min_games
    rec = keep_pos[inv]
    Hk, Mk, Rk = H[rec], M[rec], R[rec]
    # per (position, move) counts by result
    pm = np.stack([Hk, Mk.astype(np.int64)], 1)
    upm, pinv = np.unique(pm, axis=0, return_inverse=True)
    pinv = pinv.ravel()
    wdl = np.zeros((len(upm), 3), np.int64)
    np.add.at(wdl, (pinv, Rk.astype(np.int64)), 1)
    # first occurrence of each kept position -> its key (replay one game)
    order = np.argsort(H, kind="stable")
    first = {}
    sel_idx = np.nonzero(rec)[0]
    hk_first = {}
    for i in sel_idx:
        h = int(H[i])
        if h not in hk_first: hk_first[h] = i
    path_of = {i: p for i, p in enumerate(paths)}
    by_file = {}
    for h, i in hk_first.items():
        gid = int(G[i]); by_file.setdefault(gid // 10_000_000, []).append((gid, int(P[i]), h))
    keys = {}
    for fno, lst in by_file.items():
        want = {gid % 10_000_000: [] for gid, _, _ in lst}
        for gid, ply, h in lst: want[gid % 10_000_000].append((ply, h))
        for gi, (tags, mt) in enumerate(games(path_of[fno])):
            if gi not in want: continue
            sans = sans_of(mt, a.plies); b = chess.Board(); need = sorted(want[gi]); k = 0
            for ply in range(len(sans) + 1):
                while k < len(need) and need[k][0] == ply:
                    keys[need[k][1]] = b.epd(); k += 1
                if ply < len(sans): b.push_san(sans[ply])
    assert all(h64(k) == h for h, k in keys.items()), "hash/key mismatch"
    # assemble positions
    pos = {}
    for (h, mid), (w, d, l) in zip(upm.tolist(), wdl.tolist()):
        pos.setdefault(h, []).append([vocab[mid], w + d + l, w, d, l])
    shards_out = {}
    nmoves = 0
    for h, mv in pos.items():
        tot = sum(m[1] for m in mv)
        mv.sort(key=lambda m: -m[1])
        thr = max(2, 0.005 * tot)
        kept = [m for m in mv if m[1] >= thr][: a.max_moves]
        other = tot - sum(m[1] for m in kept)
        nmoves += len(kept)
        shards_out[keys[h]] = [tot, kept, other]
    # shard count from size
    raw = len(json.dumps(shards_out, separators=(",", ":")))
    S = max(1, -(-raw // a.shard_bytes))
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, "s*.json")): os.remove(f)
    shards = [dict() for _ in range(S)]
    for k, v in shards_out.items(): shards[fnv1a32(k) % S][k] = v
    sizes = []
    for i, sh in enumerate(shards):
        p = os.path.join(OUT, f"s{i:02d}.json")
        with open(p, "w") as f: json.dump(sh, f, separators=(",", ":"))
        sizes.append(os.path.getsize(p))
    years = sorted(y for y in stats["years"] if y.isdigit())
    index = {
        "version": 1, "source": "KingBase 2017 (kingbase-chess.net, mirrored in github.com/rozim/ChessData), master games, players about 2000+",
        "licence": "KingBase is distributed free for personal and non-commercial use; this tree keeps only aggregate move counts",
        "games": stats["used"], "skipped": {k: stats[k] for k in ("no_result", "setup", "illegal")},
        "dateRange": [years[0], years[-1]] if years else None, "plies": a.plies, "minGames": a.min_games, "maxMoves": a.max_moves,
        "positions": len(shards_out), "moves": nmoves, "shards": S, "hash": "fnv1a32", "shardBytes": sizes,
        "keyRule": "FEN fields 1-4 (board, side, castling, en passant); en-passant square only if an en-passant capture is legal",
        "entry": "key -> [total, [[san, n, whiteWins, draws, blackWins], ...], other]",
    }
    with open(os.path.join(OUT, "index.json"), "w") as f: json.dump(index, f, indent=1)
    print(f"positions {len(shards_out):,}, moves {nmoves:,}, shards {S}, bytes {sum(sizes):,} (max {max(sizes):,})")
    build_openings()
    print(f"done in {time.time() - t0:.0f}s")


def build_openings():
    names = {}
    for fn in sorted(glob.glob(os.path.join(OPEN, "[a-e].tsv"))):
        with open(fn) as f:
            next(f)
            for line in f:
                eco, name, pgn = line.rstrip("\n").split("\t")
                b = chess.Board()
                for tok in pgn.split():
                    if MOVENUM.match(tok) or re.match(r"^\d+\.", tok) and not re.sub(r"^\d+\.+", "", tok): continue
                    tok = re.sub(r"^\d+\.+", "", tok)
                    if tok: b.push_san(tok)
                k = b.epd()
                # several lines may reach one position; keep the shortest (most general) name
                if k not in names or len(name) < len(names[k][1]): names[k] = [eco, name]
    with open(os.path.join(OUT, "openings.json"), "w") as f: json.dump(names, f, separators=(",", ":"), ensure_ascii=False)
    print(f"openings: {len(names)} positions, {os.path.getsize(os.path.join(OUT, 'openings.json')):,} bytes")


if __name__ == "__main__":
    main()
