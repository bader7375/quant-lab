#!/usr/bin/env python3
"""Independent numpy reference for the Maia-1 (lc0 SE-ResNet) networks.

* decode_pb()   : reads an lc0 .pb.gz directly (own protobuf wire decoder, LINEAR16 de-quantisation),
                  keeps batch norm UNFOLDED (applied explicitly at inference).
* load_bin()    : reads the converted engines/maia/maia-<r>.bin + manifest.json (BN already folded).
* Net.forward() : batched numpy forward pass -> (80x64 policy-conv logits, WDL probabilities).
* encode()      : lc0 INPUT_CLASSICAL_112_PLANE encoder built with python-chess from a start FEN and a
                  UCI move history (8 history boards x 13 planes + 8 auxiliary planes).
* legal_policy(): softmax over the legal moves only, moves mapped through lc0's 1858-entry policy index
                  (generated here with the same geometry as lc0_az_policy_map.make_map).

CLI (used by validate.mjs):
  python ref.py eval --bin maia-1100.bin --manifest manifest.json --cases cases.json --out out.json
     cases.json: [{"startFen": "...", "moves": ["e2e4", ...]}, ...]
     out.json  : [{"policy": [[uci, p], ...] sorted desc, "wdl": [w, d, l]}, ...]
  python ref.py eval --pb maia-1100.pb.gz ...   (same, straight from the protobuf, BN unfolded)

This file is part of the chess-coach Maia port. The Maia weights are GPL-3.0 (CSSLab, github.com/CSSLab/maia-chess).
"""
import gzip
import json
import struct
import sys

import numpy as np
import chess

BN_EPS = 1e-5  # tfprocess.batch_norm_v2 epsilon; lc0 uses the same constant when inverting bn_stddivs
STARTPOS_KEY = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -'

# --------------------------------------------------------------------------------------------
# protobuf decoding (wire format; field numbers from lczero-common/proto/net.proto)
# --------------------------------------------------------------------------------------------

def _varint(b, i):
    r = 0
    s = 0
    while True:
        c = b[i]
        i += 1
        r |= (c & 0x7F) << s
        s += 7
        if c < 0x80:
            return r, i


def _fields(b):
    i = 0
    out = []
    while i < len(b):
        key, i = _varint(b, i)
        fn, wt = key >> 3, key & 7
        if wt == 0:
            v, i = _varint(b, i)
        elif wt == 1:
            v = bytes(b[i:i + 8]); i += 8
        elif wt == 5:
            v = bytes(b[i:i + 4]); i += 4
        elif wt == 2:
            n, i = _varint(b, i)
            v = bytes(b[i:i + n]); i += n
        else:
            raise ValueError('unsupported wire type %d' % wt)
        out.append((fn, v))
    return out


def _layer(buf):
    """Weights.Layer: LINEAR16 -> float32, exactly as maia net.py denorm_layer."""
    d = dict(_fields(buf))
    mn = struct.unpack('<f', d[1])[0] if 1 in d else 0.0
    mx = struct.unpack('<f', d[2])[0] if 2 in d else 0.0
    q = np.frombuffer(d.get(3, b''), dtype='<u2').astype(np.float32)
    return q / np.float32(0xFFFF) * np.float32(mx - mn) + np.float32(mn)


def _convblock(buf):
    names = {1: 'weights', 2: 'biases', 3: 'bn_means', 4: 'bn_stddivs', 5: 'bn_gammas', 6: 'bn_betas'}
    return {names[fn]: _layer(v) for fn, v in _fields(buf)}


def decode_pb(path):
    raw = gzip.open(path, 'rb').read()
    top = dict()
    for fn, v in _fields(raw):
        top.setdefault(fn, []).append(v)
    fmt = {}
    for fn, v in _fields(top[4][0]):
        if fn == 1:
            fmt['weights_encoding'] = v
        elif fn == 2:
            nf = dict(_fields(v))
            fmt.update(input=nf.get(1, 0), output=nf.get(2, 0), network=nf.get(3, 0),
                       policy=nf.get(4, 0), value=nf.get(5, 0), moves_left=nf.get(6, 0))
    W = {'input': None, 'residual': []}
    for fn, v in _fields(top[10][0]):
        if fn == 1:
            W['input'] = _convblock(v)
        elif fn == 2:
            blk = {}
            for f2, v2 in _fields(v):
                if f2 in (1, 2):
                    blk['conv%d' % f2] = _convblock(v2)
                elif f2 == 3:
                    se = {1: 'w1', 2: 'b1', 3: 'w2', 4: 'b2'}
                    blk['se'] = {se[f3]: _layer(v3) for f3, v3 in _fields(v2)}
            W['residual'].append(blk)
        elif fn in (3, 6, 11, 12):
            W[{3: 'policy', 6: 'value', 11: 'policy1', 12: 'moves_left'}[fn]] = _convblock(v)
        else:
            nm = {4: 'ip_pol_w', 5: 'ip_pol_b', 7: 'ip1_val_w', 8: 'ip1_val_b', 9: 'ip2_val_w', 10: 'ip2_val_b',
                  13: 'ip1_mov_w', 14: 'ip1_mov_b', 15: 'ip2_mov_w', 16: 'ip2_mov_b'}[fn]
            W[nm] = _layer(v)
    return W, fmt


def net_from_pb(path):
    """Net with UNFOLDED batch norm, straight from the protobuf."""
    W, fmt = decode_pb(path)
    assert fmt['input'] == 1 and fmt['network'] == 4 and fmt['policy'] == 2 and fmt['value'] == 2, fmt
    C = W['input']['bn_means'].shape[0]

    def conv(cb, k, cin):
        w = cb['weights']
        cout = w.size // (cin * k * k)
        L = {'w': w.reshape(cout, cin, k, k)}
        if 'biases' in cb:
            L['b'] = cb['biases']
        if 'bn_means' in cb:
            L['bn'] = (cb['bn_means'], cb['bn_stddivs'], cb.get('bn_gammas', np.ones(cout, np.float32)),
                       cb['bn_betas'])
        return L

    layers = {'input': conv(W['input'], 3, 112)}
    blocks = []
    for blk in W['residual']:
        se = blk['se']
        h = se['b1'].shape[0]
        blocks.append({'conv1': conv(blk['conv1'], 3, C), 'conv2': conv(blk['conv2'], 3, C),
                       'se_w1': se['w1'].reshape(h, C), 'se_b1': se['b1'],
                       'se_w2': se['w2'].reshape(2 * C, h), 'se_b2': se['b2']})
    layers['policy1'] = conv(W['policy1'], 3, C)
    layers['policy'] = conv(W['policy'], 3, C)
    vc = W['value']['bn_means'].shape[0]
    layers['value'] = conv(W['value'], 1, C)
    nh = W['ip1_val_b'].shape[0]
    layers['ip1_val_w'] = W['ip1_val_w'].reshape(nh, vc * 64)
    layers['ip1_val_b'] = W['ip1_val_b']
    layers['ip2_val_w'] = W['ip2_val_w'].reshape(-1, nh)
    layers['ip2_val_b'] = W['ip2_val_b']
    return Net(layers, blocks)


def net_from_bin(bin_path, manifest_path):
    """Net from the converted file (BN folded into conv weights/biases by convert.py)."""
    man = json.load(open(manifest_path))
    buf = open(bin_path, 'rb').read()
    dt = {'float16': '<f2', 'float32': '<f4'}[man['dtype']]
    T = {}
    for t in man['tensors']:
        a = np.frombuffer(buf, dtype=dt, count=int(np.prod(t['shape'])), offset=t['offset'])
        T[t['name']] = a.astype(np.float32).reshape(t['shape'])
    layers = {k: {'w': T[k + '.w'], 'b': T[k + '.b']} for k in ('input', 'policy1', 'policy', 'value')}
    blocks = []
    for i in range(man['architecture']['blocks']):
        p = 'res%d.' % i
        blocks.append({'conv1': {'w': T[p + 'conv1.w'], 'b': T[p + 'conv1.b']},
                       'conv2': {'w': T[p + 'conv2.w'], 'b': T[p + 'conv2.b']},
                       'se_w1': T[p + 'se.w1'], 'se_b1': T[p + 'se.b1'],
                       'se_w2': T[p + 'se.w2'], 'se_b2': T[p + 'se.b2']})
    for k in ('ip1_val_w', 'ip1_val_b', 'ip2_val_w', 'ip2_val_b'):
        layers[k] = T[k]
    return Net(layers, blocks)


# --------------------------------------------------------------------------------------------
# forward pass (NCHW, square index = rank*8 + file, board seen from the side to move)
# --------------------------------------------------------------------------------------------

def _conv(x, L):
    """x: [N, C, 8, 8] float32; same padding cross-correlation (TF conv2d semantics), then bias / BN."""
    w = L['w']
    N, C = x.shape[:2]
    O, _, k, _ = w.shape
    if k == 1:
        y = np.einsum('oc,ncp->nop', w.reshape(O, C), x.reshape(N, C, 64), optimize=True)
    else:
        xp = np.zeros((N, C, 10, 10), np.float32)
        xp[:, :, 1:9, 1:9] = x
        cols = np.empty((N, C, 3, 3, 8, 8), np.float32)
        for ky in range(3):
            for kx in range(3):
                cols[:, :, ky, kx] = xp[:, :, ky:ky + 8, kx:kx + 8]
        y = np.einsum('ok,nkp->nop', w.reshape(O, C * 9), cols.reshape(N, C * 9, 64), optimize=True)
    y = y.reshape(N, O, 8, 8)
    if 'b' in L:
        y = y + L['b'][None, :, None, None]
    if 'bn' in L:
        mean, var, gamma, beta = L['bn']
        y = (y - mean[None, :, None, None]) / np.sqrt(var[None, :, None, None] + BN_EPS) \
            * gamma[None, :, None, None] + beta[None, :, None, None]
    return y.astype(np.float32)


def _relu(x):
    return np.maximum(x, 0)


class Net:
    def __init__(self, layers, blocks):
        self.L = layers
        self.blocks = blocks

    def forward(self, planes, batch=256):
        """planes: [N, 112, 64] -> (policy conv logits [N, 80*64], wdl probs [N, 3])"""
        outs_p, outs_v = [], []
        for s in range(0, planes.shape[0], batch):
            x = planes[s:s + batch].reshape(-1, 112, 8, 8).astype(np.float32)
            p, v = self._fwd(x)
            outs_p.append(p)
            outs_v.append(v)
        return np.concatenate(outs_p), np.concatenate(outs_v)

    def _fwd(self, x):
        L = self.L
        x = _relu(_conv(x, L['input']))
        for b in self.blocks:
            y = _relu(_conv(x, b['conv1']))
            y = _conv(y, b['conv2'])
            pooled = y.mean(axis=(2, 3))                               # [N, C]
            s = _relu(pooled @ b['se_w1'].T + b['se_b1'])
            e = s @ b['se_w2'].T + b['se_b2']                         # [N, 2C]
            C = y.shape[1]
            g = 1.0 / (1.0 + np.exp(-e[:, :C]))
            y = g[:, :, None, None] * y + e[:, C:, None, None]
            x = _relu(x + y)
        p = _relu(_conv(x, L['policy1']))
        p = _conv(p, L['policy'])                                     # [N, 80, 8, 8]
        v = _relu(_conv(x, L['value']))                               # [N, 32, 8, 8]
        v = _relu(v.reshape(v.shape[0], -1) @ L['ip1_val_w'].T + L['ip1_val_b'])
        v = v @ L['ip2_val_w'].T + L['ip2_val_b']
        v = np.exp(v - v.max(axis=1, keepdims=True))
        v /= v.sum(axis=1, keepdims=True)
        return p.reshape(p.shape[0], -1).astype(np.float32), v.astype(np.float32)


# --------------------------------------------------------------------------------------------
# lc0 policy map (re-implementation of lc0_az_policy_map.make_map)
# --------------------------------------------------------------------------------------------

def make_policy_map():
    """Returns (names[1858] in lc0 policy_index order, flat_index[1858] into the 80x64 conv output)."""
    files, ranks = 'abcdefgh', '12345678'
    qdirs = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]       # N NE E SE S SW W NW
    kdirs = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]
    flat = []  # flat conv index -> move name or None
    for dx, dy in qdirs:
        for st in range(1, 8):
            for r in range(8):
                for f in range(8):
                    f2, r2 = f + dx * st, r + dy * st
                    flat.append(files[f] + ranks[r] + files[f2] + ranks[r2] if 0 <= f2 < 8 and 0 <= r2 < 8 else None)
    for dx, dy in kdirs:
        for r in range(8):
            for f in range(8):
                f2, r2 = f + dx, r + dy
                flat.append(files[f] + ranks[r] + files[f2] + ranks[r2] if 0 <= f2 < 8 and 0 <= r2 < 8 else None)
    for dx in (-1, 0, 1):                                   # NW, N, NE
        for promo in 'rbq':
            for r in range(8):
                for f in range(8):
                    f2 = f + dx
                    flat.append(files[f] + '7' + files[f2] + '8' + promo if r == 6 and 0 <= f2 < 8 else None)
    assert len(flat) == 73 * 64      # 56 queen-move + 8 knight + 9 promotion planes; conv planes 73..79 unused
    flat += [None] * (7 * 64)
    # lc0 policy_index order: grouped by from-square (a1..h8), then sorted by to-square (a1..h8) for normal
    # moves; the 66 promotions (q, r, b) come last. Reconstructed and checked against maia policy_index.py.
    normal = sorted([m for m in flat if m and len(m) == 4], key=lambda m: (_sq(m[:2]), _sq(m[2:4])))
    promos = sorted([m for m in flat if m and len(m) == 5], key=lambda m: (_sq(m[:2]), _sq(m[2:4]), 'qrb'.index(m[4])))
    names = normal + promos
    pos = {m: i for i, m in enumerate(flat) if m}
    return names, np.array([pos[m] for m in names], dtype=np.int64)


def _sq(s):
    return 'abcdefgh'.index(s[0]) + 8 * (int(s[1]) - 1)


POLICY_NAMES, POLICY_FLAT = make_policy_map()
POLICY_IDX = {m: i for i, m in enumerate(POLICY_NAMES)}


def move_to_lc0(board, move, castling='king_to_rook'):
    """python-chess move (side to move = board.turn) -> lc0 policy name in the side-to-move frame."""
    fr, to = move.from_square, move.to_square
    if board.is_castling(move) and castling == 'king_to_rook':
        to = chess.square(7 if chess.square_file(to) > chess.square_file(fr) else 0, chess.square_rank(fr))
    if board.turn == chess.BLACK:
        fr, to = chess.square_mirror(fr), chess.square_mirror(to)
    name = chess.square_name(fr) + chess.square_name(to)
    if move.promotion and move.promotion != chess.KNIGHT:
        name += chess.piece_symbol(move.promotion)
    return name


# --------------------------------------------------------------------------------------------
# 112-plane encoder
# --------------------------------------------------------------------------------------------

def _rep_key(b):
    # lc0 ChessBoard equality: pieces, side to move, castling rights and the raw en-passant flag
    # (python-chess keeps ep_square for every double push, like lc0 and chess.js 0.10.3).
    return (b.board_fen(), b.turn, b.castling_rights, b.ep_square)


def _piece_planes(board, us, flip):
    """12 planes (ours P N B R Q K, theirs P N B R Q K) of `board` from the perspective of colour `us`."""
    out = np.zeros((12, 64), np.float32)
    for sq, pc in board.piece_map().items():
        s = chess.square_mirror(sq) if flip else sq
        k = pc.piece_type - 1 + (0 if pc.color == us else 6)
        out[k, s] = 1.0
    return out


def encode(start_fen, moves, history_fill='fen_only'):
    """Returns (planes [112, 64] float32, board at the end).

    lc0 EncodePositionForNN semantics (INPUT_CLASSICAL_112_PLANE):
      * slot i (0..7) holds the position i plies ago, always seen from the CURRENT side to move
        (ours/theirs and vertical flip fixed by the current mover).
      * history shorter than 8: lc0's default history fill is 'fen_only': if the game started from the
        standard start position the missing slots stay all-zero; otherwise they are filled with copies of the
        first position (with an en-passant double push undone in the copies, as lc0 does).
      * plane 13*i+12: all ones if that position occurred before (repetition count >= 1).
      * aux 104..111: our O-O-O, our O-O, their O-O-O, their O-O, side to move (ones if black),
        rule-50 half-move clock (raw, NOT divided by 99: the stored input weights were pre-divided),
        zeros (old move-count plane), all ones.
    """
    board = chess.Board(start_fen)
    boards = [board.copy(stack=False)]
    for u in moves:
        mv = chess.Move.from_uci(u)
        if mv not in board.legal_moves:
            raise ValueError('illegal move %s in %s' % (u, board.fen()))
        board.push(mv)
        boards.append(board.copy(stack=False))
    keys = [_rep_key(b) for b in boards]
    reps = [1 if keys[i] in keys[:i] else 0 for i in range(len(keys))]

    us = board.turn
    flip = us == chess.BLACK
    planes = np.zeros((112, 64), np.float32)
    n = len(boards)
    first_is_start = keys[0] == _rep_key(chess.Board())
    for i in range(8):
        h = n - 1 - i
        base = 13 * i
        if h >= 0:
            planes[base:base + 12] = _piece_planes(boards[h], us, flip)
            if reps[h]:
                planes[base + 12] = 1.0
        else:
            if history_fill == 'no' or (history_fill == 'fen_only' and first_is_start):
                break
            b0 = boards[0].copy(stack=False)
            if b0.ep_square is not None:      # undo the double push that created the ep square
                mover = not b0.turn
                f = chess.square_file(b0.ep_square)
                now = chess.square(f, 3 if mover == chess.WHITE else 4)
                before = chess.square(f, 1 if mover == chess.WHITE else 6)
                pc = b0.remove_piece_at(now)
                if pc is not None:
                    b0.set_piece_at(before, pc)
            planes[base:base + 12] = _piece_planes(b0, us, flip)
    them = not us
    planes[104] = float(board.has_queenside_castling_rights(us))
    planes[105] = float(board.has_kingside_castling_rights(us))
    planes[106] = float(board.has_queenside_castling_rights(them))
    planes[107] = float(board.has_kingside_castling_rights(them))
    planes[108] = 1.0 if us == chess.BLACK else 0.0
    planes[109] = float(board.halfmove_clock)
    planes[110] = 0.0
    planes[111] = 1.0
    return planes, board


def legal_policy(board, logits80, castling='king_to_rook', temperature=1.0):
    """Softmax over legal moves. Returns list of (uci, p) sorted by p desc (UCI in normal orientation,
    castling as e1g1 etc., promotions with q/r/b/n suffix)."""
    moves = list(board.legal_moves)
    if not moves:
        return []
    idx = [POLICY_FLAT[POLICY_IDX[move_to_lc0(board, m, castling)]] for m in moves]
    z = logits80[idx].astype(np.float64) / temperature
    z = np.exp(z - z.max())
    z /= z.sum()
    order = np.argsort(-z, kind='stable')
    return [(moves[i].uci(), float(z[i])) for i in order]


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------

def main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['eval'])
    ap.add_argument('--pb')
    ap.add_argument('--bin')
    ap.add_argument('--manifest')
    ap.add_argument('--cases', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--castling', default=None)
    a = ap.parse_args(argv)
    if a.pb:
        net = net_from_pb(a.pb)
        castling = a.castling or 'king_to_rook'
    else:
        net = net_from_bin(a.bin, a.manifest)
        castling = a.castling or json.load(open(a.manifest))['policy']['castling']
    cases = json.load(open(a.cases))
    enc = [encode(c['startFen'], c['moves']) for c in cases]
    planes = np.stack([e[0] for e in enc]) if enc else np.zeros((0, 112, 64), np.float32)
    P, V = net.forward(planes)
    out = []
    for (pl, board), p, v in zip(enc, P, V):
        out.append({'policy': legal_policy(board, p, castling), 'wdl': [float(x) for x in v]})
    json.dump(out, open(a.out, 'w'))


if __name__ == '__main__':
    main(sys.argv[1:])
