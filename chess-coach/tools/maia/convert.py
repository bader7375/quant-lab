#!/usr/bin/env python3
"""Convert Maia-1 lc0 protobuf weights (maia-<rating>.pb.gz) to flat little-endian tensors for maia.js.

  python convert.py --weights /path/to/maia_weights --out ../../engines/maia [--games dataset.ndjson.bz2]

Steps
  1. decode the protobuf (ref.decode_pb: own wire-format decoder, LINEAR16 de-quantisation
     value = u16 / 65535 * (max_val - min_val) + min_val, as maia net.py denorm_layer) and print the
     format fields and layer shapes;
  2. fold batch norm into the preceding (bias-free) convolutions:  s = gamma / sqrt(var + 1e-5),
     W' = W * s[out],  b' = beta - mean * s   (bn_stddivs holds the moving VARIANCE, see tfprocess
     save_leelaz_weights_v2; gammas are 1.0 where the TF layer had scale=False);
  3. float16 vs float32 decision on 1000 test positions (dev split of the Lichess dataset): float16 is used
     only if, for EVERY rating, the argmax legal move is identical on >= 99.5% of positions and the max
     |p16 - p32| over all legal moves is < 0.01; the folded float32 net is also checked against the
     unfolded protobuf net (folding validity);
  4. write maia-<rating>.bin (tensors concatenated, 16-byte aligned) + manifest.json.
"""
import argparse
import bz2
import hashlib
import json
import os
import random
import sys
import time

import numpy as np
import chess

sys.dont_write_bytecode = True   # keep tools/maia free of __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref  # noqa: E402

RATINGS = [1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
FORMAT_NAMES = {
    'weights_encoding': {0: 'UNKNOWN', 1: 'LINEAR16'},
    'input': {0: 'INPUT_UNKNOWN', 1: 'INPUT_CLASSICAL_112_PLANE', 2: 'INPUT_112_WITH_CASTLING_PLANE'},
    'output': {0: 'OUTPUT_UNKNOWN', 1: 'OUTPUT_CLASSICAL', 2: 'OUTPUT_WDL'},
    'network': {0: 'NETWORK_UNKNOWN', 1: 'NETWORK_CLASSICAL', 2: 'NETWORK_SE', 3: 'NETWORK_CLASSICAL_WITH_HEADFORMAT',
                4: 'NETWORK_SE_WITH_HEADFORMAT'},
    'policy': {0: 'POLICY_UNKNOWN', 1: 'POLICY_CLASSICAL', 2: 'POLICY_CONVOLUTION'},
    'value': {0: 'VALUE_UNKNOWN', 1: 'VALUE_CLASSICAL', 2: 'VALUE_WDL'},
    'moves_left': {0: 'MOVES_LEFT_NONE', 1: 'MOVES_LEFT_V1'},
}


def fold(L):
    w = L['w'].astype(np.float64)
    b = L.get('b', np.zeros(w.shape[0], np.float32)).astype(np.float64)
    if 'bn' in L:
        mean, var, gamma, beta = [a.astype(np.float64) for a in L['bn']]
        s = gamma / np.sqrt(var + ref.BN_EPS)
        w = w * s[:, None, None, None]
        b = (b - mean) * s + beta
    return w.astype(np.float32), b.astype(np.float32)


def folded_tensors(net):
    """Ordered list of (name, array) in the layout maia.js / ref.net_from_bin expect."""
    T = []
    w, b = fold(net.L['input']); T += [('input.w', w), ('input.b', b)]
    for i, blk in enumerate(net.blocks):
        for c in ('conv1', 'conv2'):
            w, b = fold(blk[c]); T += [('res%d.%s.w' % (i, c), w), ('res%d.%s.b' % (i, c), b)]
        T += [('res%d.se.w1' % i, blk['se_w1']), ('res%d.se.b1' % i, blk['se_b1']),
              ('res%d.se.w2' % i, blk['se_w2']), ('res%d.se.b2' % i, blk['se_b2'])]
    for k in ('policy1', 'policy', 'value'):
        w, b = fold(net.L[k]); T += [(k + '.w', w), (k + '.b', b)]
    for k in ('ip1_val_w', 'ip1_val_b', 'ip2_val_w', 'ip2_val_b'):
        T.append((k, net.L[k]))
    return [(n, np.ascontiguousarray(a, dtype=np.float32)) for n, a in T]


def net_from_tensors(T, nblocks):
    d = dict(T)
    layers = {k: {'w': d[k + '.w'], 'b': d[k + '.b']} for k in ('input', 'policy1', 'policy', 'value')}
    blocks = []
    for i in range(nblocks):
        p = 'res%d.' % i
        blocks.append({'conv1': {'w': d[p + 'conv1.w'], 'b': d[p + 'conv1.b']},
                       'conv2': {'w': d[p + 'conv2.w'], 'b': d[p + 'conv2.b']},
                       'se_w1': d[p + 'se.w1'], 'se_b1': d[p + 'se.b1'],
                       'se_w2': d[p + 'se.w2'], 'se_b2': d[p + 'se.b2']})
    for k in ('ip1_val_w', 'ip1_val_b', 'ip2_val_w', 'ip2_val_b'):
        layers[k] = d[k]
    return ref.Net(layers, blocks)


def test_positions(games_path, n=1000, seed=7):
    """n positions (start FEN + UCI history) from dev-split games (sha1(id) % 5 == 0), bullet excluded,
    plies >= 1, one to four positions per game."""
    rng = random.Random(seed)
    out = []
    opener = bz2.open if games_path.endswith('.bz2') else open
    with opener(games_path, 'rt') as f:
        for line in f:
            g = json.loads(line)
            g = g.get('game', g)
            gid = g['id']
            if int(hashlib.sha1(gid.encode()).hexdigest()[:8], 16) % 5 != 0 or g.get('speed') == 'bullet':
                continue
            b = chess.Board()
            ucis = []
            try:
                for san in g['moves'].split():
                    mv = b.parse_san(san)
                    ucis.append(mv.uci())
                    b.push(mv)
            except ValueError:
                continue
            if len(ucis) < 4:
                continue
            for k in rng.sample(range(1, len(ucis)), min(len(ucis) - 1, rng.randint(1, 4))):
                out.append((chess.STARTING_FEN, ucis[:k]))
                if len(out) >= n:
                    return out
    return out


def compare(netA, netB, enc):
    planes = np.stack([e[0] for e in enc])
    PA, VA = netA.forward(planes)
    PB, VB = netB.forward(planes)
    same, maxdp = 0, 0.0
    for (pl, board), pa, pb in zip(enc, PA, PB):
        a = ref.legal_policy(board, pa)
        b = dict(ref.legal_policy(board, pb))
        same += a[0][0] == max(b, key=b.get)
        maxdp = max(maxdp, max(abs(p - b[u]) for u, p in a))
    return {'argmax_same': same / len(enc), 'max_abs_dp': maxdp, 'max_abs_dwdl': float(np.abs(VA - VB).max())}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument('--weights', default='/tmp/claude-0/maia-chess/maia_weights')
    ap.add_argument('--out', default=os.path.normpath(os.path.join(here, '../../engines/maia')))
    ap.add_argument('--games', default='/tmp/claude-0/mcognetta_lichess-combined-puzzle-game-db/'
                                       'combined_puzzle_db_first_50k.ndjson.bz2')
    ap.add_argument('--npos', type=int, default=1000)
    ap.add_argument('--force-dtype', choices=['float16', 'float32'])
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    t0 = time.time()
    pos = test_positions(a.games, a.npos)
    enc = [ref.encode(fen, mv) for fen, mv in pos]
    print('dtype test positions: %d (black to move: %d)' % (len(enc), sum(1 for e in enc if e[1].turn == chess.BLACK)))

    results, folded = {}, {}
    fmt0 = None
    for r in RATINGS:
        pb_path = os.path.join(a.weights, 'maia-%d.pb.gz' % r)
        W, fmt = ref.decode_pb(pb_path)
        fmt_named = {k: FORMAT_NAMES[k].get(v, v) for k, v in fmt.items()}
        if fmt0 is None:
            fmt0 = fmt_named
            print('format fields:', json.dumps(fmt_named))
        assert fmt_named == fmt0, (r, fmt_named)
        net_pb = ref.net_from_pb(pb_path)
        T = folded_tensors(net_pb)
        if r == RATINGS[0]:
            print('layer shapes after folding (%d tensors, %d parameters):' % (len(T), sum(x.size for _, x in T)))
            for n, x in T:
                print('   %-14s %s' % (n, list(x.shape)))
        nb = len(net_pb.blocks)
        net32 = net_from_tensors(T, nb)
        net16 = net_from_tensors([(n, x.astype(np.float16).astype(np.float32)) for n, x in T], nb)
        fold_chk = compare(net_pb, net32, enc)
        f16_chk = compare(net32, net16, enc)
        results[r] = {'fold_vs_pb': fold_chk, 'fp16_vs_fp32': f16_chk}
        folded[r] = T
        print('maia-%d  folded-fp32 vs pb: argmax %.4f max|dp| %.2e max|dwdl| %.2e   fp16 vs fp32: argmax %.4f '
              'max|dp| %.2e max|dwdl| %.2e   (%.0fs)' % (
                  r, fold_chk['argmax_same'], fold_chk['max_abs_dp'], fold_chk['max_abs_dwdl'],
                  f16_chk['argmax_same'], f16_chk['max_abs_dp'], f16_chk['max_abs_dwdl'], time.time() - t0))

    fp16_ok = all(v['fp16_vs_fp32']['argmax_same'] >= 0.995 and v['fp16_vs_fp32']['max_abs_dp'] < 0.01
                  for v in results.values())
    dtype = a.force_dtype or ('float16' if fp16_ok else 'float32')
    print('float16 criterion (argmax >= 99.5%% and max|dp| < 0.01 for all nets): %s -> storing %s'
          % ('PASS' if fp16_ok else 'FAIL', dtype))
    npdt = np.dtype('<f2') if dtype == 'float16' else np.dtype('<f4')

    tensors, off = [], 0
    for n, x in folded[RATINGS[0]]:
        nbytes = x.size * npdt.itemsize
        tensors.append({'name': n, 'shape': list(x.shape), 'offset': off, 'nbytes': nbytes})
        off += (nbytes + 15) // 16 * 16
    total = off
    files = {}
    for r in RATINGS:
        buf = bytearray(total)
        for t, (n, x) in zip(tensors, folded[r]):
            assert t['name'] == n and t['shape'] == list(x.shape)
            buf[t['offset']:t['offset'] + t['nbytes']] = x.astype(npdt).tobytes()
        fn = 'maia-%d.bin' % r
        with open(os.path.join(a.out, fn), 'wb') as f:
            f.write(buf)
        files[str(r)] = {'file': fn, 'bytes': len(buf), 'sha256': hashlib.sha256(buf).hexdigest()}
        print('wrote %s  %d bytes' % (fn, len(buf)))

    arch_net = ref.net_from_pb(os.path.join(a.weights, 'maia-%d.pb.gz' % RATINGS[0]))
    C = arch_net.L['input']['w'].shape[0]
    manifest = {
        'name': 'Maia-1 (CSSLab) human move-prediction networks, lc0 format, converted for maia.js',
        'license': 'GPL-3.0 (weights by CSSLab, https://github.com/CSSLab/maia-chess)',
        'ratings': RATINGS,
        'files': files,
        'dtype': dtype,
        'endianness': 'little',
        'alignment': 16,
        'lc0_format': fmt0,
        'architecture': {
            'type': 'SE-ResNet (lc0 NETWORK_SE_WITH_HEADFORMAT)',
            'blocks': len(arch_net.blocks), 'filters': int(C),
            'se_hidden': int(arch_net.blocks[0]['se_w1'].shape[0]),
            'input': 'conv3x3 112->%d (+bias, BN folded) -> relu' % C,
            'residual_block': 'x -> conv3x3 -> relu -> conv3x3 -> SE(avgpool -> fc C->se_hidden -> relu -> fc '
                              'se_hidden->2C; out = sigmoid(g[0:C]) * y + g[C:2C]) -> +x -> relu',
            'policy_head': 'conv3x3 C->C (BN folded) -> relu -> conv3x3 C->80 (+bias) = logits[plane*64 + '
                           'fromSquare]; planes 0..72 used (lc0 POLICY_CONVOLUTION), 73..79 unused',
            'value_head': 'conv1x1 C->32 (BN folded) -> relu -> flatten (channel*64+square) -> fc 2048->128 -> '
                          'relu -> fc 128->3 -> softmax = [win, draw, loss] for the side to move',
            'layout': 'NCHW, square = rank*8 + file in the side-to-move frame; conv weights [out][in][ky][kx] '
                      '(ky along ranks, kx along files), TF same-padding cross-correlation; fc weights [out][in]',
            'bn_folding': 'W\' = W * gamma/sqrt(var+1e-5), b\' = beta - mean*gamma/sqrt(var+1e-5)',
        },
        'input_encoding': {
            'planes': 112,
            'history': 'slot i = 0..7 is the position i plies ago; 13 planes each: ours P,N,B,R,Q,K, theirs '
                       'P,N,B,R,Q,K, repetition (all ones if that position occurred earlier in the game). Every '
                       'slot is seen from the CURRENT side to move (ours = mover, board mirrored vertically '
                       '(rank r -> 7-r) when Black is to move).',
            'history_fill': 'lc0 fen_only: game from the standard start position -> missing slots are all '
                            'zero; game from another FEN -> missing slots are copies of the first position '
                            '(an en-passant double push is undone in the copies)',
            'aux': {'104': 'mover can castle queenside (O-O-O)', '105': 'mover can castle kingside (O-O)',
                    '106': 'opponent O-O-O', '107': 'opponent O-O', '108': 'all ones if Black to move',
                    '109': 'rule-50 half-move clock, raw value (weights were pre-divided by 99)',
                    '110': 'zeros (former move-count plane)', '111': 'all ones'},
            'repetition_key': 'piece placement + side to move + castling rights + raw en-passant square',
        },
        'policy': {
            'castling': 'king_to_rook',
            'castling_note': 'castling is encoded as king-to-rook (e1h1 / e1a1 in the mover frame); maia.js '
                             'reports it as e1g1/e1c1/e8g8/e8c8',
            'promotion_note': 'queen/rook/bishop promotions use planes 64 + dir*3 + {r:0,b:1,q:2}, dir NW=0 '
                              'N=1 NE=2; knight promotion is the bare queen-move plane (e.g. a7a8)',
            'planes': '0..55: queen-like moves, plane = dir*7 + (distance-1), dir N,NE,E,SE,S,SW,W,NW '
                      '(dx,dy)=(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1); 56..63: knight moves '
                      '(1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1),(-2,1),(-1,2); 64..72 promotions',
            'output': 'softmax over the legal moves only (illegal logits ignored)',
        },
        'tensors': tensors,
        'conversion_checks': {str(r): v for r, v in results.items()},
        'dtype_test': {'positions': len(enc), 'source': os.path.basename(a.games) + ' dev split (sha1(id)%5==0), '
                                                                                    'bullet excluded',
                       'criterion': 'argmax identical >= 99.5% and max |dp| < 0.01, every rating',
                       'float16_pass': fp16_ok},
    }
    with open(os.path.join(a.out, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=1)
    print('wrote manifest.json; total %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
