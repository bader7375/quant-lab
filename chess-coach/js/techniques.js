"use strict";
/* Technique tags: what kind of move a move is (develop a knight, castle, save an attacked piece, take a loose piece, back-rank
   check, queen a knight's jump from the lone king...). Used to pick training positions where the best move IS the technique
   (tools/positions/tag_pools.mjs runs this over the pools with Stockfish's best move), and to tell the student whether
   their own move used the technique. Engine-free; works in the browser and in Node. */
(function (root) {
  const isNode = typeof module !== "undefined" && module.exports;
  const ChessLib = root.Chess || (isNode ? require("../chess.js").Chess : null);
  const Facts = root.Facts || (isNode ? require("./facts.js") : null);
  const HOME = { n: ["b1", "g1", "b8", "g8"], b: ["c1", "f1", "c8", "f8"] };
  const GOOD_N = ["c3", "f3", "d2", "e2", "c6", "f6", "d7", "e7"];
  const CENTRE = ["d4", "e4", "d5", "e5"];
  const kd = (a, b) => [Math.abs(a.charCodeAt(0) - b.charCodeAt(0)), Math.abs(+a[1] - +b[1])];
  const knightJump = (a, b) => { const [x, y] = kd(a, b); return (x === 1 && y === 2) || (x === 2 && y === 1); };

  /* All tags of `uci` played in `fen`. */
  function tagsOf(fen, uci) {
    const g = new ChessLib(fen); const me = g.turn(); const opp = me === "w" ? "b" : "w";
    const m = g.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci[4] || "q" }); if (!m) return [];
    const G0 = Facts.grid(new ChessLib(fen)), G1 = Facts.grid(g); const t = [];
    if (m.piece === "n" && HOME.n.includes(m.from) && GOOD_N.includes(m.to)) t.push("knight");
    if (m.piece === "b" && HOME.b.includes(m.from)) t.push("bishop");
    if (m.piece === "p" && CENTRE.includes(m.to)) t.push("centre");
    if (m.flags.includes("k") || m.flags.includes("q")) t.push("castle");
    const h0 = Facts.hanging(G0, me), h1 = Facts.hanging(G1, me);
    const worst0 = h0[0] ? h0[0].gain : 0, worst1 = h1[0] ? h1[0].gain : 0;
    if (worst0 >= 2 && worst1 < worst0) {
      if (m.from === h0[0].sq || (m.captured && Facts.attackers(G0, h0[0].sq, opp).some((a) => a.sq === m.to))) t.push("save");
      else if (!m.captured) t.push("cover");
    }
    if (m.captured) { const s = Facts.see(G0, m.to, me); if (s >= 2) t.push("take"); }
    if (/[+#]/.test(m.san)) t.push("check");
    if (m.san.includes("#")) t.push("mate");
    const back = opp === "w" ? "1" : "8"; const ek = Object.keys(G1).find((s) => G1[s].type === "k" && G1[s].color === opp);
    if (/[+#]/.test(m.san) && "rq".includes(m.piece) && m.to[1] === back && ek && ek[1] === back) t.push("backrank");
    // basic mates: queen a knight's jump from the lone king; rook cutting the king off on a rank or file
    const lone = Object.values(G1).filter((p) => p.color === opp).length === 1;
    if (lone && m.piece === "q" && ek && knightJump(m.to, ek) && !g.in_stalemate()) t.push("qknight");
    if (lone && m.piece === "r" && ek && !/[+#]/.test(m.san)) { const [x, y] = kd(m.to, ek); if ((x === 1 || y === 1) && Math.max(x, y) >= 2) t.push("rcut"); }
    if (g.in_stalemate()) t.push("stalemate");
    t.push(...motifs(G0, G1, m, me, opp));
    t.push(...plans(fen, g, G0, G1, m, me, opp));
    return t;
  }

  /* Middlegame plan moves: a rook to an open or half-open file, improving the worst piece, a pawn break, an outpost. */
  const pawnsOn = (G, file, color) => Object.entries(G).filter(([s, p]) => s[0] === file && p.type === "p" && p.color === color).length;
  function mobility(fen, sq) { // moves of the piece on sq as if it were its side's turn
    const p = fen.split(" "); const g = new ChessLib(fen); const c = g.get(sq); if (!c) return 0;
    p[1] = c.color; p[3] = "-"; const h = new ChessLib(p.join(" ")); return h.moves({ square: sq }).length;
  }
  function plans(fen, g, G0, G1, m, me, opp) {
    const t = [];
    if (m.piece === "r" && m.from[0] !== m.to[0] && !pawnsOn(G1, m.to[0], me) && pawnsOn(G0, m.from[0], me)) t.push("openfile");
    if ("nbrq".includes(m.piece) && !m.captured) {
      let worst = null; for (const [s, p] of Object.entries(G0)) { if (p.color !== me || !"nbr".includes(p.type)) continue; const k = mobility(fen, s); if (!worst || k < worst.k) worst = { s, k }; }
      if (worst && worst.s === m.from && worst.k <= 3 && mobility(g.fen(), m.to) >= worst.k + 3) t.push("worst");
    }
    if (m.piece === "p") {
      const dir = me === "w" ? 1 : -1; const f = m.to.charCodeAt(0);
      const hits = [-1, 1].map((d) => String.fromCharCode(f + d) + (+m.to[1] + dir)).filter((s) => G1[s] && G1[s].type === "p" && G1[s].color === opp);
      if (hits.length || (m.captured === "p")) t.push("break");
    }
    if ((m.piece === "n" || m.piece === "b") && (me === "w" ? +m.to[1] >= 5 : +m.to[1] <= 4)) {
      const dir = me === "w" ? -1 : 1; const f = m.to.charCodeAt(0);
      const guarded = [-1, 1].some((d) => { const s = String.fromCharCode(f + d) + (+m.to[1] + dir); return G1[s] && G1[s].type === "p" && G1[s].color === me; });
      const ahead = (r) => (me === "w" ? r > +m.to[1] : r < +m.to[1]);
      const chased = Object.entries(G1).some(([s, p]) => p.type === "p" && p.color === opp && Math.abs(s.charCodeAt(0) - f) === 1 && ahead(+s[1]));
      if (guarded && !chased) t.push("outpost");
    }
    return t;
  }

  /* Tactical motifs of a move: fork, pin, skewer, discovered attack, removing the defender. Static (no engine): the
     tag says what the move sets up; whether it works is Stockfish's best move choosing it. */
  const V = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 100 };
  const F = "abcdefgh"; const at = (f, r) => (f >= 0 && f < 8 && r >= 0 && r < 8 ? F[f] + (r + 1) : null);
  const xy = (sq) => [F.indexOf(sq[0]), +sq[1] - 1];
  const RAYS = { b: [[1, 1], [1, -1], [-1, 1], [-1, -1]], r: [[1, 0], [-1, 0], [0, 1], [0, -1]] }; RAYS.q = RAYS.b.concat(RAYS.r);
  function lineTargets(G, sq) { // along each ray of the slider on sq: the first and second pieces met
    const p = G[sq]; const out = []; if (!RAYS[p.type]) return out;
    for (const [dx, dy] of RAYS[p.type]) {
      let [f, r] = xy(sq); const hit = [];
      for (;;) { f += dx; r += dy; const s = at(f, r); if (!s) break; if (G[s]) { hit.push(s); if (hit.length === 2) break; } }
      out.push(hit);
    }
    return out;
  }
  function between(a, b, c) { // is c strictly between a and b on a straight line or diagonal
    const [ax, ay] = xy(a), [bx, by] = xy(b), [cx, cy] = xy(c); const dx = Math.sign(bx - ax), dy = Math.sign(by - ay);
    if (!(ax === bx || ay === by || Math.abs(bx - ax) === Math.abs(by - ay))) return false;
    let x = ax + dx, y = ay + dy; while (x !== bx || y !== by) { if (x === cx && y === cy) return true; x += dx; y += dy; } return false;
  }
  function motifs(G0, G1, m, me, opp) {
    const t = []; const mover = G1[m.to];
    // fork: the moved piece attacks two targets (the king, a more valuable piece, or a piece it can win)
    const targets = Object.keys(G1).filter((s) => G1[s].color === opp && Facts.attackers(G1, s, me).some((a) => a.sq === m.to)
      && (G1[s].type === "k" || V[G1[s].type] > V[mover.type] || Facts.see(G1, s, me) > 0));
    if (targets.length >= 2) { t.push("fork"); if (mover.type === "n") t.push("knightfork"); }
    // pin and skewer: the moved slider sees two enemy pieces on one line
    for (const [a, b] of lineTargets(G1, m.to)) {
      if (!a || !b || G1[a].color !== opp || G1[b].color !== opp) continue;
      if (G1[a].type === "p") continue; // a pawn in front is not worth a pin
      if ((G1[b].type === "k" || G1[b].type === "q" || V[G1[b].type] > V[G1[a].type]) && G1[a].type !== "k" && G1[b].type !== "p") t.push("pin");
      else if ((G1[a].type === "k" || G1[a].type === "q") && G1[b].type !== "p" && V[G1[a].type] > V[G1[b].type] && (G1[a].type === "k" || Facts.see(G1, b, me) > 0 || !Facts.attackers(G1, b, opp).length)) t.push("skewer");
    }
    // exploiting a pin: the moved piece attacks a piece that cannot move because your slider pins it to its king
    for (const x of targets.length ? targets : Object.keys(G1).filter((q) => G1[q].color === opp && Facts.attackers(G1, q, me).some((a) => a.sq === m.to))) {
      if (G1[x].type === "k") continue;
      if (Object.entries(G1).some(([s, p]) => p.color === me && s !== m.to && RAYS[p.type] && lineTargets(G1, s).some(([a, b]) => a === x && b && G1[b].type === "k" && G1[b].color === opp))) { t.push("pin"); break; }
    }
    // discovered attack: another of your sliders now reaches the king or a piece it can win, through the square just left
    for (const [s, p] of Object.entries(G1)) {
      if (p.color !== me || s === m.to || !RAYS[p.type]) continue;
      for (const [a] of lineTargets(G1, s)) if (a && G1[a].color === opp && between(s, a, m.from) && (G1[a].type === "k" || Facts.see(G1, a, me) > 0 || V[G1[a].type] > V[p.type])) { t.push("discovered"); break; }
    }
    // removing the defender: you capture a piece that was the only defender of another piece you attack
    if (m.captured) for (const [s, p] of Object.entries(G0)) {
      if (p.color !== opp || s === m.to || p.type === "k") continue;
      const defs = Facts.attackers(G0, s, opp); if (defs.length === 1 && defs[0].sq === m.to && Facts.attackers(G0, s, me).length) { t.push("removal"); break; }
    }
    return [...new Set(t)];
  }
  const T = { tagsOf, knightJump };
  if (isNode) module.exports = T; else root.Tech = T;
})(typeof self !== "undefined" ? self : this);
