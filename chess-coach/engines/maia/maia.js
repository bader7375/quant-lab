/*
 * maia.js - dependency-free inference for the Maia-1 human move-prediction networks
 * (lc0 SE-ResNet, 6 blocks x 64 filters, convolutional policy head, WDL value head).
 *
 * Weights: Maia-1 by CSSLab (https://github.com/CSSLab/maia-chess), GPL-3.0. This port is GPL-3.0 too.
 * Converted by tools/maia/convert.py (batch norm folded, float16 storage); format in manifest.json.
 *
 * Browser / Web Worker: load chess.js 0.10.3 first (global Chess), then this file -> globalThis.MaiaNet.
 * Node:                 const MaiaNet = require('./maia.js')   (requires ../../chess.js itself).
 *
 *   const net = MaiaNet.load(arrayBuffer, manifest);
 *   const r = net.evaluate(startFen, ['e2e4', 'e7e5', ...]);
 *   // r.policy = [{uci, san, p}, ...] legal moves only, softmax over legal moves, sorted by p desc
 *   // r.value  = {w, d, l, es}  (side to move's view; es = w + d/2 = expected score)
 *   // r.ms     = wall time of this call
 *   MaiaNet.evaluateMany([net1100, net1500, net1900], startFen, moves) -> one result per net (the history
 *   replay / encoding / move generation is shared, the forward pass runs once per net).
 *
 * Encoding (verified against the numpy reference and by move-matching accuracy, see MAIA_REPORT.md):
 *   lc0 INPUT_CLASSICAL_112_PLANE, 8 history slots x 13 planes seen from the side to move (vertical flip
 *   for Black), missing history = zeros when the game started from the standard position (lc0 fen_only),
 *   aux planes: our O-O-O, our O-O, their O-O-O, their O-O, black-to-move, raw rule-50 count, 0, 1.
 *   Policy: 80x8x8 conv output, logit = out[plane*64 + fromSquare]; castling is king-to-rook (e1h1),
 *   knight promotion is the plain queen-move plane, q/r/b promotions use planes 64..72.
 */
(function (root, factory) {
  var api = factory(root);
  if (typeof module === 'object' && module && module.exports) module.exports = api;
  if (root) root.MaiaNet = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : this), function (root) {
  'use strict';

  var ChessCtor = null;
  function getChess() {
    if (ChessCtor) return ChessCtor;
    if (root && typeof root.Chess === 'function') ChessCtor = root.Chess;
    else if (typeof require === 'function') ChessCtor = require('../../chess.js').Chess;
    if (!ChessCtor) throw new Error('maia.js: chess.js (global Chess) is not loaded');
    return ChessCtor;
  }

  var STARTPOS = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  var STARTKEY = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -';
  var now = (typeof performance !== 'undefined' && performance.now) ? function () { return performance.now(); }
    : function () { return Date.now(); };

  // ------------------------------------------------------------------ weights
  var F16 = null;
  function f16table() {
    if (F16) return F16;
    F16 = new Float32Array(65536);
    for (var h = 0; h < 65536; h++) {
      var e = (h >> 10) & 31, m = h & 1023, v;
      if (e === 0) v = m * 5.960464477539063e-8;            // 2^-24
      else if (e === 31) v = m ? NaN : Infinity;
      else v = (1 + m / 1024) * Math.pow(2, e - 15);
      F16[h] = (h & 0x8000) ? -v : v;
    }
    return F16;
  }

  function readTensors(buf, manifest) {
    var u8 = buf instanceof ArrayBuffer ? new Uint8Array(buf) : new Uint8Array(buf.buffer, buf.byteOffset, buf.byteLength);
    var fp16 = manifest.dtype === 'float16';
    var tab = fp16 ? f16table() : null;
    var littleHost = new Uint8Array(new Uint16Array([1]).buffer)[0] === 1;
    var out = {};
    manifest.tensors.forEach(function (t) {
      var n = 1;
      t.shape.forEach(function (d) { n *= d; });
      var a = new Float32Array(n);
      var bytes = u8.slice(t.offset, t.offset + n * (fp16 ? 2 : 4));      // aligned private copy
      if (bytes.length !== n * (fp16 ? 2 : 4)) throw new Error('maia.js: weight file too short for ' + t.name);
      if (littleHost) {
        if (fp16) { var h = new Uint16Array(bytes.buffer); for (var i = 0; i < n; i++) a[i] = tab[h[i]]; }
        else a.set(new Float32Array(bytes.buffer));
      } else {
        var dv = new DataView(bytes.buffer);
        for (var j = 0; j < n; j++) a[j] = fp16 ? tab[dv.getUint16(2 * j, true)] : dv.getFloat32(4 * j, true);
      }
      out[t.name] = { data: a, shape: t.shape };
    });
    return out;
  }

  // Winograd F(4x4, 3x3): U = G g G^T for every (out, in) pair, stored as U[xi][o][c] (xi = 0..35).
  var G = [[1 / 4, 0, 0], [-1 / 6, -1 / 6, -1 / 6], [-1 / 6, 1 / 6, -1 / 6], [1 / 24, 1 / 12, 1 / 6],
    [1 / 24, -1 / 12, 1 / 6], [0, 0, 1]];
  function winoWeights(w, O, C) {
    var U = new Float32Array(36 * O * C), t = new Float64Array(18);
    for (var o = 0; o < O; o++) {
      for (var c = 0; c < C; c++) {
        var b = (o * C + c) * 9;
        for (var i = 0; i < 6; i++) {           // t = G g  (6x3)
          for (var k = 0; k < 3; k++) t[i * 3 + k] = G[i][0] * w[b + k] + G[i][1] * w[b + 3 + k] + G[i][2] * w[b + 6 + k];
        }
        for (i = 0; i < 6; i++) {               // (G g) G^T  (6x6)
          for (var j = 0; j < 6; j++) {
            U[((i * 6 + j) * O + o) * C + c] = t[i * 3] * G[j][0] + t[i * 3 + 1] * G[j][1] + t[i * 3 + 2] * G[j][2];
          }
        }
      }
    }
    return U;
  }

  // ------------------------------------------------------------------ kernels
  // Activations: [C][64], square = rank*8 + file. Padded: [C][100] (10x10, zero border).
  function pad(x, C, P) {
    for (var c = 0; c < C; c++) {
      var s = c * 64, d = c * 100 + 11;
      for (var r = 0; r < 8; r++, s += 8, d += 10) {
        P[d] = x[s]; P[d + 1] = x[s + 1]; P[d + 2] = x[s + 2]; P[d + 3] = x[s + 3];
        P[d + 4] = x[s + 4]; P[d + 5] = x[s + 5]; P[d + 6] = x[s + 6]; P[d + 7] = x[s + 7];
      }
    }
  }

  // V[xi][c][t] = (B^T d B)[xi] for the 4 tiles t of each channel.
  function winoIn(P, C, V, T) {
    var S = C * 4;
    for (var c = 0; c < C; c++) {
      for (var t = 0; t < 4; t++) {
        var base = c * 100 + (t >> 1) * 40 + (t & 1) * 4;
        for (var j = 0; j < 6; j++) {
          var b = base + j;
          var x0 = P[b], x1 = P[b + 10], x2 = P[b + 20], x3 = P[b + 30], x4 = P[b + 40], x5 = P[b + 50];
          T[j] = 4 * x0 - 5 * x2 + x4;
          T[6 + j] = -4 * x1 - 4 * x2 + x3 + x4;
          T[12 + j] = 4 * x1 - 4 * x2 - x3 + x4;
          T[18 + j] = -2 * x1 - x2 + 2 * x3 + x4;
          T[24 + j] = 2 * x1 - x2 - 2 * x3 + x4;
          T[30 + j] = 4 * x1 - 5 * x3 + x5;
        }
        var o = c * 4 + t;
        for (var i = 0; i < 6; i++) {
          var r = i * 6;
          var y0 = T[r], y1 = T[r + 1], y2 = T[r + 2], y3 = T[r + 3], y4 = T[r + 4], y5 = T[r + 5];
          var q = r * S + o;
          V[q] = 4 * y0 - 5 * y2 + y4;
          V[q + S] = -4 * y1 - 4 * y2 + y3 + y4;
          V[q + 2 * S] = 4 * y1 - 4 * y2 - y3 + y4;
          V[q + 3 * S] = -2 * y1 - y2 + 2 * y3 + y4;
          V[q + 4 * S] = 2 * y1 - y2 - 2 * y3 + y4;
          V[q + 5 * S] = 4 * y1 - 5 * y3 + y5;
        }
      }
    }
  }

  // M[xi][o][t] = sum_c U[xi][o][c] * V[xi][c][t]   (36 small GEMMs, 4 outputs x 4 tiles per inner loop)
  function winoGemm(U, V, M, O, C) {
    for (var xi = 0; xi < 36; xi++) {
      var vb = xi * C * 4, mb = xi * O * 4;
      for (var o = 0; o < O; o += 4) {
        var u0 = (xi * O + o) * C, u1 = u0 + C, u2 = u1 + C, u3 = u2 + C;
        var a00 = 0, a01 = 0, a02 = 0, a03 = 0, a10 = 0, a11 = 0, a12 = 0, a13 = 0;
        var a20 = 0, a21 = 0, a22 = 0, a23 = 0, a30 = 0, a31 = 0, a32 = 0, a33 = 0;
        for (var c = 0, v = vb; c < C; c++, v += 4) {
          var v0 = V[v], v1 = V[v + 1], v2 = V[v + 2], v3 = V[v + 3];
          var w0 = U[u0 + c], w1 = U[u1 + c], w2 = U[u2 + c], w3 = U[u3 + c];
          a00 += w0 * v0; a01 += w0 * v1; a02 += w0 * v2; a03 += w0 * v3;
          a10 += w1 * v0; a11 += w1 * v1; a12 += w1 * v2; a13 += w1 * v3;
          a20 += w2 * v0; a21 += w2 * v1; a22 += w2 * v2; a23 += w2 * v3;
          a30 += w3 * v0; a31 += w3 * v1; a32 += w3 * v2; a33 += w3 * v3;
        }
        var m = mb + o * 4;
        M[m] = a00; M[m + 1] = a01; M[m + 2] = a02; M[m + 3] = a03;
        M[m + 4] = a10; M[m + 5] = a11; M[m + 6] = a12; M[m + 7] = a13;
        M[m + 8] = a20; M[m + 9] = a21; M[m + 10] = a22; M[m + 11] = a23;
        M[m + 12] = a30; M[m + 13] = a31; M[m + 14] = a32; M[m + 15] = a33;
      }
    }
  }

  // Y = A^T M A per (o, tile) -> out[o][64] + bias
  function winoOut(M, O, bias, out, T) {
    var S = O * 4;
    for (var o = 0; o < O; o++) {
      var bo = bias[o];
      for (var t = 0; t < 4; t++) {
        var base = o * 4 + t;
        for (var j = 0; j < 6; j++) {          // A^T applied over xi rows: T[i][j], i = 0..3
          var q = base + j * S;
          var m0 = M[q], m1 = M[q + 6 * S], m2 = M[q + 12 * S], m3 = M[q + 18 * S], m4 = M[q + 24 * S], m5 = M[q + 30 * S];
          T[j] = m0 + m1 + m2 + m3 + m4;
          T[6 + j] = m1 - m2 + 2 * m3 - 2 * m4;
          T[12 + j] = m1 + m2 + 4 * m3 + 4 * m4;
          T[18 + j] = m1 - m2 + 8 * m3 - 8 * m4 + m5;
        }
        var ob = o * 64 + (t >> 1) * 32 + (t & 1) * 4;
        for (var i = 0; i < 4; i++) {
          var r = i * 6;
          var n0 = T[r], n1 = T[r + 1], n2 = T[r + 2], n3 = T[r + 3], n4 = T[r + 4], n5 = T[r + 5];
          var d = ob + i * 8;
          out[d] = n0 + n1 + n2 + n3 + n4 + bo;
          out[d + 1] = n1 - n2 + 2 * n3 - 2 * n4 + bo;
          out[d + 2] = n1 + n2 + 4 * n3 + 4 * n4 + bo;
          out[d + 3] = n1 - n2 + 8 * n3 - 8 * n4 + n5 + bo;
        }
      }
    }
  }

  function relu(x, n) { for (var i = 0; i < n; i++) if (x[i] < 0) x[i] = 0; }

  // ------------------------------------------------------------------ network
  function Net(T, manifest) {
    var arch = manifest.architecture;
    this.manifest = manifest;
    this.blocks = arch.blocks;
    var C = this.C = arch.filters;
    this.seH = arch.se_hidden;
    var w = function (n) { if (!T[n]) throw new Error('maia.js: missing tensor ' + n); return T[n].data; };
    this.inU = winoWeights(w('input.w'), C, 112); this.inB = w('input.b');
    this.res = [];
    for (var i = 0; i < this.blocks; i++) {
      var p = 'res' + i + '.';
      this.res.push({
        u1: winoWeights(w(p + 'conv1.w'), C, C), b1: w(p + 'conv1.b'),
        u2: winoWeights(w(p + 'conv2.w'), C, C), b2: w(p + 'conv2.b'),
        sw1: w(p + 'se.w1'), sb1: w(p + 'se.b1'), sw2: w(p + 'se.w2'), sb2: w(p + 'se.b2')
      });
    }
    this.p1U = winoWeights(w('policy1.w'), C, C); this.p1B = w('policy1.b');
    this.pW = w('policy.w'); this.pB = w('policy.b'); this.pPlanes = T['policy.w'].shape[0];
    this.vW = w('value.w'); this.vB = w('value.b'); this.vC = T['value.w'].shape[0];
    this.f1W = w('ip1_val_w'); this.f1B = w('ip1_val_b'); this.fH = T['ip1_val_w'].shape[0];
    this.f2W = w('ip2_val_w'); this.f2B = w('ip2_val_b');
    // scratch buffers (allocated once)
    var CM = Math.max(C, 112);
    this.X = new Float32Array(112 * 64);
    this.P = new Float32Array(CM * 100);
    this.V = new Float32Array(36 * CM * 4);
    this.M = new Float32Array(36 * Math.max(C, 80) * 4);
    this.T = new Float32Array(36);
    this.a = new Float32Array(C * 64);
    this.y = new Float32Array(C * 64);
    this.pol = new Float32Array(C * 64);
    this.polPad = new Float32Array(C * 100);
    this.vh = new Float32Array(this.vC * 64);
    this.cache = null;
  }

  Net.prototype.conv3 = function (x, Cin, U, bias, Cout, out) {
    pad(x, Cin, this.P);
    winoIn(this.P, Cin, this.V, this.T);
    winoGemm(U, this.V, this.M, Cout, Cin);
    winoOut(this.M, Cout, bias, out, this.T);
  };

  // planes: Float32Array(112*64). Returns WDL [w,d,l]; leaves padded policy1 activations in this.polPad.
  Net.prototype.forward = function (planes) {
    var C = this.C, a = this.a, y = this.y, n = C * 64, i, c, k;
    this.conv3(planes, 112, this.inU, this.inB, C, a);
    relu(a, n);
    var pooled = new Float64Array(C), hid = new Float64Array(this.seH), H = this.seH;
    for (var bI = 0; bI < this.blocks; bI++) {
      var R = this.res[bI];
      this.conv3(a, C, R.u1, R.b1, C, y);
      relu(y, n);
      this.conv3(y, C, R.u2, R.b2, C, y);
      for (c = 0; c < C; c++) {
        var s = 0;
        for (k = c * 64; k < c * 64 + 64; k++) s += y[k];
        pooled[c] = s / 64;
      }
      for (i = 0; i < H; i++) {
        var h = R.sb1[i];
        for (c = 0; c < C; c++) h += R.sw1[i * C + c] * pooled[c];
        hid[i] = h > 0 ? h : 0;
      }
      for (c = 0; c < C; c++) {
        var g = R.sb2[c], be = R.sb2[C + c];
        for (i = 0; i < H; i++) { g += R.sw2[c * H + i] * hid[i]; be += R.sw2[(C + c) * H + i] * hid[i]; }
        g = 1 / (1 + Math.exp(-g));
        for (k = c * 64; k < c * 64 + 64; k++) {
          var v = a[k] + g * y[k] + be;
          a[k] = v > 0 ? v : 0;
        }
      }
    }
    // policy trunk (the final 80-plane conv is evaluated lazily, only at legal moves' from-squares)
    this.conv3(a, C, this.p1U, this.p1B, C, this.pol);
    relu(this.pol, n);
    pad(this.pol, C, this.polPad);
    // value head
    var vC = this.vC, vh = this.vh;
    for (var o = 0; o < vC; o++) {
      var bo = this.vB[o];
      for (k = 0; k < 64; k++) vh[o * 64 + k] = bo;
      for (c = 0; c < C; c++) {
        var wv = this.vW[o * C + c], ab = c * 64, ob = o * 64;
        for (k = 0; k < 64; k++) vh[ob + k] += wv * a[ab + k];
      }
    }
    relu(vh, vC * 64);
    var fH = this.fH, fin = vC * 64, hidden = new Float64Array(fH);
    for (i = 0; i < fH; i++) {
      var acc = this.f1B[i], wb = i * fin;
      for (k = 0; k < fin; k++) acc += this.f1W[wb + k] * vh[k];
      hidden[i] = acc > 0 ? acc : 0;
    }
    var z = [0, 0, 0];
    for (i = 0; i < 3; i++) {
      var zz = this.f2B[i];
      for (k = 0; k < fH; k++) zz += this.f2W[i * fH + k] * hidden[k];
      z[i] = zz;
    }
    var mx = Math.max(z[0], z[1], z[2]);
    var e0 = Math.exp(z[0] - mx), e1 = Math.exp(z[1] - mx), e2 = Math.exp(z[2] - mx), es = e0 + e1 + e2;
    return [e0 / es, e1 / es, e2 / es];
  };

  // logit of policy plane `plane` at square `sq` (side-to-move frame) from the padded policy1 activations
  Net.prototype.policyLogit = function (plane, sq) {
    var C = this.C, P = this.polPad, W = this.pW, acc = this.pB[plane];
    var base = (sq >> 3) * 10 + (sq & 7);
    for (var c = 0; c < C; c++) {
      var p = c * 100 + base, wb = (plane * C + c) * 9;
      acc += W[wb] * P[p] + W[wb + 1] * P[p + 1] + W[wb + 2] * P[p + 2] +
        W[wb + 3] * P[p + 10] + W[wb + 4] * P[p + 11] + W[wb + 5] * P[p + 12] +
        W[wb + 6] * P[p + 20] + W[wb + 7] * P[p + 21] + W[wb + 8] * P[p + 22];
    }
    return acc;
  };

  // ------------------------------------------------------------------ chess encoding
  var PIECE = { P: 0, N: 1, B: 2, R: 3, Q: 4, K: 5, p: 6, n: 7, b: 8, r: 9, q: 10, k: 11 };
  function sqIdx(s) { return (s.charCodeAt(0) - 97) + 8 * (s.charCodeAt(1) - 49); }
  function sqName(i) { return String.fromCharCode(97 + (i & 7)) + String.fromCharCode(49 + (i >> 3)); }

  function parseFen(fen) {
    var f = fen.split(/\s+/), board = new Int8Array(64).fill(-1), r = 7, c = 0, rows = f[0];
    for (var i = 0; i < rows.length; i++) {
      var ch = rows[i];
      if (ch === '/') { r--; c = 0; } else if (ch >= '1' && ch <= '8') c += +ch;
      else { board[r * 8 + c] = PIECE[ch]; c++; }
    }
    return { board: board, turn: f[1] === 'b' ? 1 : 0, castling: f[2] || '-', ep: f[3] || '-',
      half: parseInt(f[4] || '0', 10) || 0, key: f.slice(0, 4).join(' ') };
  }

  // Position-history state with prefix reuse between calls (fast for growing games and what-if branches).
  function History(startFen) {
    var Ch = getChess();
    this.startFen = startFen;
    this.game = new Ch();
    var v = this.game.validate_fen(startFen);
    if (!v.valid || !this.game.load(startFen)) throw new Error('maia.js: invalid FEN ' + startFen + ' (' + v.error + ')');
    this.moves = [];
    this.pos = [parseFen(this.game.fen())];
  }
  History.prototype.push = function (uci) {
    var from = uci.slice(0, 2), to = uci.slice(2, 4), promo = uci.length > 4 ? uci[4].toLowerCase() : undefined;
    var g = this.game, mv = g.move({ from: from, to: to, promotion: promo });
    if (!mv) {
      // king-to-rook castling notation (e1h1 / e1a1) -> e1g1 / e1c1
      var pc = g.get(from), tp = g.get(to);
      if (pc && pc.type === 'k' && tp && tp.type === 'r' && tp.color === pc.color && from[1] === to[1]) {
        mv = g.move({ from: from, to: (to[0] > from[0] ? 'g' : 'c') + from[1] });
      } else if (!promo && pc && pc.type === 'p' && (to[1] === '8' || to[1] === '1')) {
        mv = g.move({ from: from, to: to, promotion: 'q' });
      }
    }
    if (!mv) throw new Error('maia.js: illegal move ' + uci + ' in ' + g.fen());
    this.moves.push(uci);
    this.pos.push(parseFen(g.fen()));
  };
  History.prototype.pop = function () { this.game.undo(); this.moves.pop(); this.pos.pop(); };

  Net.prototype.history = function (startFen, moves) {
    var h = this.cache;
    if (!h || h.startFen !== startFen) h = this.cache = new History(startFen);
    var k = 0, n = Math.min(h.moves.length, moves.length);
    while (k < n && h.moves[k] === moves[k]) k++;
    while (h.moves.length > k) h.pop();
    try {
      for (var i = k; i < moves.length; i++) h.push(moves[i]);
    } catch (e) { this.cache = null; throw e; }
    return h;
  };

  // Fill this.X with the 112 input planes for the last position of history h.
  Net.prototype.encode = function (h, historyFill) {
    var X = this.X, pos = h.pos, n = pos.length, cur = pos[n - 1], us = cur.turn, flip = us ? 56 : 0, i, s;
    X.fill(0);
    var keys = {}, rep = new Uint8Array(n);
    for (i = 0; i < n; i++) { if (keys[pos[i].key]) rep[i] = 1; keys[pos[i].key] = 1; }
    var fill = historyFill || 'fen_only';
    var startIsStd = pos[0].key === STARTKEY;
    for (var slot = 0; slot < 8; slot++) {
      var hi = n - 1 - slot, base = 13 * slot * 64, b;
      if (hi >= 0) {
        b = pos[hi].board;
        if (rep[hi]) for (s = 0; s < 64; s++) X[base + 768 + s] = 1;
      } else {
        if (fill === 'no' || (fill === 'fen_only' && startIsStd)) break;
        b = pos[0].board;
        if (pos[0].ep !== '-') {            // undo the double push that created the en-passant square
          b = b.slice();
          var f = pos[0].ep.charCodeAt(0) - 97, white = pos[0].turn === 1;   // mover of the double push
          var nowSq = (white ? 3 : 4) * 8 + f, befSq = (white ? 1 : 6) * 8 + f;
          if (b[nowSq] >= 0) { b[befSq] = b[nowSq]; b[nowSq] = -1; }
        }
      }
      for (s = 0; s < 64; s++) {
        var pc = b[s];
        if (pc < 0) continue;
        var color = pc >= 6 ? 1 : 0, plane = (color === us ? 0 : 6) + (pc % 6);
        X[base + plane * 64 + (s ^ flip)] = 1;
      }
    }
    var cs = cur.castling, ours = us ? ['q', 'k'] : ['Q', 'K'], theirs = us ? ['Q', 'K'] : ['q', 'k'];
    var aux = [cs.indexOf(ours[0]) >= 0, cs.indexOf(ours[1]) >= 0, cs.indexOf(theirs[0]) >= 0,
      cs.indexOf(theirs[1]) >= 0, us === 1, cur.half, 0, 1];
    for (i = 0; i < 8; i++) {
      var val = +aux[i];
      if (val) X.fill(val, (104 + i) * 64, (105 + i) * 64);
    }
    return X;
  };

  // policy plane for a chess.js verbose move, in the side-to-move frame
  var QDIR = { '0,1': 0, '1,1': 1, '1,0': 2, '1,-1': 3, '0,-1': 4, '-1,-1': 5, '-1,0': 6, '-1,1': 7 };
  var KDIR = { '1,2': 0, '2,1': 1, '2,-1': 2, '1,-2': 3, '-1,-2': 4, '-2,-1': 5, '-2,1': 6, '-1,2': 7 };
  function movePlane(m, black) {
    var fr = sqIdx(m.from), to = sqIdx(m.to);
    if (m.flags.indexOf('k') >= 0) to = (fr & 56) | 7;          // castling: king -> rook square
    else if (m.flags.indexOf('q') >= 0) to = fr & 56;
    if (black) { fr ^= 56; to ^= 56; }
    var dx = (to & 7) - (fr & 7), dy = (to >> 3) - (fr >> 3), plane;
    if (m.promotion && m.promotion !== 'n') {
      plane = 64 + (dx + 1) * 3 + (m.promotion === 'r' ? 0 : m.promotion === 'b' ? 1 : 2);
    } else if (KDIR[dx + ',' + dy] !== undefined && m.piece === 'n') {
      plane = 56 + KDIR[dx + ',' + dy];
    } else {
      var dist = Math.max(Math.abs(dx), Math.abs(dy));
      plane = QDIR[Math.sign(dx) + ',' + Math.sign(dy)] * 7 + dist - 1;
    }
    return { plane: plane, sq: fr };
  }

  /**
   * evaluate(startFen, movesUci, opts?) -> {policy:[{uci,san,p}], value:{w,d,l,es}, ms, terminal?}
   * opts.temperature (default 1): softmax temperature over legal-move logits.
   * opts.historyFill: 'fen_only' (lc0 default, used for validation) | 'always' | 'no'.
   */
  Net.prototype.evaluate = function (startFen, moves, opts) {
    return evaluateMany([this], startFen, moves, opts)[0];
  };

  // Shared path: history replay, encoding and legal-move generation once, one forward pass per net.
  function evaluateMany(nets, startFen, moves, opts) {
    var t0 = now();
    opts = opts || {};
    var lead = nets[0];
    var h = lead.history(startFen || STARTPOS, moves || []);
    var g = h.game, cur = h.pos[h.pos.length - 1];
    var legal = g.moves({ verbose: true });
    var out = [];
    if (!legal.length) {
      var mate = g.in_check();
      for (var q = 0; q < nets.length; q++) {
        out.push({ policy: [], value: mate ? { w: 0, d: 0, l: 1, es: 0 } : { w: 0, d: 1, l: 0, es: 0.5 },
          terminal: mate ? 'checkmate' : 'stalemate', ms: now() - t0 });
      }
      return out;
    }
    var X = lead.encode(h, opts.historyFill);
    var black = cur.turn === 1, planes = legal.map(function (m) { return movePlane(m, black); });
    var T = opts.temperature || 1, shared = now() - t0;
    for (var k = 0; k < nets.length; k++) {
      var t1 = now(), net = nets[k];
      var wdl = net.forward(X);
      var logits = new Float64Array(legal.length), mx = -Infinity, i;
      for (i = 0; i < legal.length; i++) {
        logits[i] = net.policyLogit(planes[i].plane, planes[i].sq) / T;
        if (logits[i] > mx) mx = logits[i];
      }
      var sum = 0;
      for (i = 0; i < legal.length; i++) { logits[i] = Math.exp(logits[i] - mx); sum += logits[i]; }
      var pol = legal.map(function (m, j) {
        return { uci: m.from + m.to + (m.promotion || ''), san: m.san, p: logits[j] / sum };
      });
      pol.sort(function (x, y) { return y.p - x.p; });
      out.push({ policy: pol, value: { w: wdl[0], d: wdl[1], l: wdl[2], es: wdl[0] + 0.5 * wdl[1] },
        ms: shared + (now() - t1) });
    }
    return out;
  }

  /** Raw forward on caller-supplied planes (Float32Array 112*64) - used by validation. */
  Net.prototype.forwardPlanes = function (planes) { return this.forward(planes); };

  function load(arrayBuffer, manifest) {
    if (!manifest || !manifest.tensors) throw new Error('maia.js: manifest.json required');
    return new Net(readTensors(arrayBuffer, manifest), manifest);
  }

  /** Sample a move from a policy list with temperature T (p^(1/T) renormalised); rng() in [0,1). */
  function sample(policy, T, rng) {
    if (!policy || !policy.length) return null;
    rng = rng || Math.random;
    T = T || 1;
    var w = policy.map(function (m) { return Math.pow(m.p, 1 / T); }), s = 0, i;
    for (i = 0; i < w.length; i++) s += w[i];
    var r = rng() * s;
    for (i = 0; i < w.length; i++) { r -= w[i]; if (r <= 0) return policy[i]; }
    return policy[policy.length - 1];
  }

  return { load: load, evaluateMany: evaluateMany, sample: sample, STARTPOS: STARTPOS, version: '1.0.0',
    _internal: { parseFen: parseFen, movePlane: movePlane, sqName: sqName } };
});
