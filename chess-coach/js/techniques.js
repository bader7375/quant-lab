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
    return t;
  }
  const T = { tagsOf, knightJump };
  if (isNode) module.exports = T; else root.Tech = T;
})(typeof self !== "undefined" ? self : this);
