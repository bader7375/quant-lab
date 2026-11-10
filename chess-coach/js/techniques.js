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
  /* The pawn structure of a position (chapter 7), from the pawns only:
     iqp: an isolated d-pawn (no c- or e-pawn of its colour); side = its owner.
     hanging: c- and d-pawns side by side on the 4th/5th rank with no b- or e-pawns; side = their owner.
     carlsbad: d4+e3 without a c-pawn against c6+d5 without an e-pawn (or the colours reversed); side = the minority attacker.
     chain: e5+d4 against e6+d5 (French) or d5+e4 against d6+e5 (King's Indian); side = White.
     open: at most one pawn left on the d- and e-files together. */
  function structure(fen) {
    const G = Facts.grid(new ChessLib(fen)); const P = { w: {}, b: {} };
    for (const [s, p] of Object.entries(G)) if (p.type === "p") (P[p.color][s[0]] = P[p.color][s[0]] || []).push(+s[1]);
    const has = (c, f, r) => (P[c][f] || []).includes(r); const any = (c, f) => (P[c][f] || []).length > 0;
    for (const c of ["w", "b"]) if ((P[c].d || []).length === 1 && !any(c, "c") && !any(c, "e")) return { id: "iqp", side: c, sq: "d" + P[c].d[0] };
    for (const c of ["w", "b"]) { const r = c === "w" ? [4] : [5]; if (r.some((x) => has(c, "c", x) && has(c, "d", x)) && !any(c, "b") && !any(c, "e")) return { id: "hanging", side: c }; }
    if (has("w", "d", 4) && has("w", "e", 3) && !any("w", "c") && has("b", "c", 6) && has("b", "d", 5) && !any("b", "e")) return { id: "carlsbad", side: "w" };
    if (has("b", "d", 5) && has("b", "e", 6) && !any("b", "c") && has("w", "c", 3) && has("w", "d", 4) && !any("w", "e")) return { id: "carlsbad", side: "b" };
    if ((has("w", "e", 5) && has("w", "d", 4) && has("b", "e", 6) && has("b", "d", 5)) || (has("w", "d", 5) && has("w", "e", 4) && has("b", "d", 6) && has("b", "e", 5))) return { id: "chain", side: "w" };
    const centre = ["d", "e"].reduce((n, f) => n + (P.w[f] || []).length + (P.b[f] || []).length, 0);
    if (centre <= 1) return { id: "open", side: null };
    return null;
  }
  /* Does a move follow the classic plan of the structure for the side that plays it? Returns the plan key or null. */
  function structPlan(fen, uci, st) {
    st = st || structure(fen); if (!st) return null;
    const g = new ChessLib(fen); const me = g.turn(); const m = g.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci[4] || "q" }); if (!m) return null;
    const G0 = Facts.grid(new ChessLib(fen)), G1 = Facts.grid(g); const tags = tagsOf(fen, uci); const opp = me === "w" ? "b" : "w";
    const ek = Object.keys(G1).find((s) => G1[s].type === "k" && G1[s].color === opp);
    const nearKing = ek && Math.abs(m.to.charCodeAt(0) - ek.charCodeAt(0)) <= 2 && (me === "w" ? +m.to[1] >= 5 : +m.to[1] <= 4);
    if (st.id === "iqp") {
      const front = st.sq[0] + (+st.sq[1] + (st.side === "w" ? 1 : -1));
      if (me === st.side) { if (m.piece === "p" && m.from === st.sq) return "iqp-push"; if ((m.piece === "n" && ["e5", "c5", "e4", "c4"].includes(m.to)) || (nearKing && m.piece !== "p")) return "iqp-attack"; return null; }
      if (m.to === front && "nbq".includes(m.piece)) return "iqp-blockade";
      if (m.captured && m.captured !== "p" && Facts.VAL[m.captured] === Facts.VAL[m.piece]) return "iqp-trade";
      if (Facts.attackers(G1, st.sq, me).length > Facts.attackers(G0, st.sq, me).length) return "iqp-pressure";
      return null;
    }
    if (st.id === "hanging") {
      if (me === st.side) return m.piece === "p" && "cd".includes(m.from[0]) ? "hang-push" : null;
      const tgt = Object.keys(G1).filter((s) => "cd".includes(s[0]) && G1[s].type === "p" && G1[s].color === opp);
      return tgt.some((s) => Facts.attackers(G1, s, me).length > Facts.attackers(G0, s, me).length) ? "hang-pressure" : null;
    }
    if (st.id === "carlsbad") {
      if (me === st.side) { if (m.piece === "p" && "ab".includes(m.from[0])) return "minority"; if (m.piece === "r" && "bc".includes(m.to[0]) && m.from[0] !== m.to[0]) return "minority"; return null; }
      if (nearKing || (m.piece === "n" && ["e4", "e5"].includes(m.to)) || (m.piece === "p" && "fg".includes(m.from[0]))) return "carlsbad-kingside";
      return null;
    }
    if (st.id === "chain") return tags.includes("break") ? "chain-break" : null;
    if (st.id === "open") return tags.some((x) => ["openfile", "outpost", "worst"].includes(x)) ? "open-activity" : null;
    return null;
  }
  /* «أين أهاجم؟»: which part of the board to play on (q = queenside a-c, c = centre d-e, k = kingside f-h), from the
     position alone, with the reasons that decided it. The rules are the classic ones: go where the enemy king is (with
     pawns only when the kings are on opposite wings), where your space is, where your pawn chain points, along half-open
     files, at weak pawns, and where your pieces already aim. Each reason has a weight; the wing with the most wins.
     A heuristic, so the trainer shows it next to what masters and Stockfish actually play (wingOfMoves). */
  const WING_OF = (f) => ("abc".includes(f) ? "q" : "de".includes(f) ? "c" : "k");
  const WING_AR = { q: "جناح الوزير", c: "المركز", k: "جناح الملك" };
  function compass(fen, side) {
    const g = new ChessLib(fen); const me = side || g.turn(), opp = me === "w" ? "b" : "w"; const G = Facts.grid(g);
    const S = { q: 0, c: 0, k: 0 }; const R = []; const add = (w, n, t) => { S[w] += n; R.push({ w, n, t }); };
    const rel = (s, c) => (c === "w" ? +s[1] : 9 - +s[1]); // rank counted from that side's back rank
    const pawnsOf = (c) => Object.keys(G).filter((s) => G[s].type === "p" && G[s].color === c);
    const kingOf = (c) => Object.keys(G).find((s) => G[s].type === "k" && G[s].color === c);
    const ek = kingOf(opp), mk = kingOf(me); if (!ek || !mk) return null;
    const ew = WING_OF(ek[0]), mw = WING_OF(mk[0]); const opposite = ew !== "c" && mw !== "c" && ew !== mw;
    // 1. the enemy king
    if (ew === "c") { // a king in the centre is a target only if the centre can be opened (a d/e file without your pawn) or it can no longer castle
      const rights = (fen.split(" ")[2] || "").split("").filter((x) => (opp === "w" ? /[KQ]/ : /[kq]/).test(x)).length;
      const lever = ["d", "e"].some((f) => !pawnsOf(me).some((s) => s[0] === f));
      if (!rights || lever) add("c", 3, `ملك الخصم ما زال في الوسط (${ek})${rights ? "" : " ولا يستطيع التبييت"}: افتح المركز قبل أن يبيّت`);
      else add("c", 1, `ملك الخصم في الوسط (${ek})، لكنه سيبيّت غالبًا: أكمل تطويرك أولًا`);
    }
    else if (opposite) add(ew, 4, `ملك الخصم على ${ek} وملكك في الجهة الأخرى: ادفع بيادقك نحو ملكه، فهذا لا يكشف ملكك`);
    else add(ew, 1.5, `ملك الخصم على ${ek}، وملكك في الجهة نفسها: هاجمه بالقطع لا بالبيادق`);
    // 2. space and 3. the direction of a blocked pawn chain
    const mine = pawnsOf(me), his = pawnsOf(opp); const at = (f, r) => f + r;
    const ahead = (s, c) => s[0] + (+s[1] + (c === "w" ? 1 : -1));
    // the chain: the most advanced blocked pawn of yours with a pawn diagonally behind it; a base that is itself blocked
    // is preferred (e4-d5 in the King's Indian, not the c4 pawn that only supports d5)
    let chain = null; const blockedP = (s, c) => { const a = G[ahead(s, c)]; return !!a && a.type === "p" && a.color !== c; };
    for (const s of mine) if (rel(s, me) >= 5) add(WING_OF(s[0]), 1, `بيدقك على ${s} يعطيك مساحة في ${WING_AR[WING_OF(s[0])]}`);
    for (const s of mine.slice().sort((a, b) => rel(b, me) - rel(a, me))) {
      if (!blockedP(s, me) || rel(s, me) < 4) continue;
      const back = +s[1] + (me === "w" ? -1 : 1);
      const bases = [-1, 1].map((df) => at(String.fromCharCode(s.charCodeAt(0) + df), back)).filter((b) => G[b] && G[b].type === "p" && G[b].color === me);
      if (bases.length) { chain = { head: s, base: bases.find((b) => blockedP(b, me)) || bases[0] }; break; }
    }
    if (chain) { const w = chain.head[0] > chain.base[0] ? "k" : "q"; add(w, 2.5, `سلسلة بيادقك ${chain.base}-${chain.head} تشير إلى ${WING_AR[w]}: هاجم في الجهة التي تشير إليها`); }
    // 4. half-open files: no pawn of yours, an enemy pawn to press
    for (const f of "abcdefgh") {
      const my = mine.some((s) => s[0] === f), hp = his.filter((s) => s[0] === f);
      if (!my && hp.length) { const front = hp.sort((a, b) => rel(b, opp) - rel(a, opp))[0]; add(WING_OF(f), 1, `العمود ${f} نصف مفتوح لك: رخ عليه يضغط على البيدق ${front}`); }
    }
    // 5. weak enemy pawns
    const ps = Facts.pawnStructure(G, opp);
    for (const s of ps.isolated) add(WING_OF(s[0]), 1, `بيدق الخصم على ${s} معزول: هدف لقطعك`);
    // the structure's classic plan (chapter 7)
    const st = structure(fen);
    if (st && st.id === "carlsbad") { if (st.side === me) add("q", 2, "بنية Carlsbad: هجوم الأقلية، b4 ثم b5 لتصنع بيدقًا ضعيفًا في c6"); else add("k", 2, "بنية Carlsbad: خصمك يلعب على جناح الوزير، فالعب أنت على جناح الملك والمركز"); }
    if (st && st.id === "iqp") { if (st.side === me) add("k", 1.5, "بيدقك المعزول يعطي قطعك مربعات نشطة: الهجوم على الملك قبل أن تُبادَل القطع"); else add("c", 2, `حاصر البيدق المعزول على ${st.sq} من المربع الذي أمامه واضغط عليه`); }
    if (st && st.id === "hanging") add("c", 2, st.side === me ? "بيدقاك المعلّقان: ادفع أحدهما في الوقت المناسب" : "بيدقا الخصم المعلّقان: اضغط عليهما ليدفع أحدهما فيضعف");
    // 6. hooks: enemy pawns already advanced in front of a castled king
    if (opposite) for (const s of his) if ("fgh".includes(s[0]) === (ew === "k") && "abc".includes(s[0]) === (ew === "q") && rel(s, opp) === 3 && Math.abs(s.charCodeAt(0) - ek.charCodeAt(0)) <= 1)
      add(ew, 1, `بيدق الخصم ${s} تقدّم أمام ملكه: خطاف تفتح عليه دفعة بيدق خطًّا نحو الملك`);
    // 7. where your pieces already aim (squares attacked in the enemy half)
    const aim = { q: 0, c: 0, k: 0 };
    for (const f of "abcdefgh") for (let r = 1; r <= 8; r++) { const s = f + r; if (rel(s, me) < 5) continue; aim[WING_OF(f)] += Facts.attackers(G, s, me).filter((a) => a.type !== "p" && a.type !== "k").length; }
    const ord = Object.entries(aim).sort((a, b) => b[1] - a[1]);
    if (ord[0][1] >= 4 && ord[0][1] >= 1.4 * ord[1][1]) add(ord[0][0], 1, `قطعك تستهدف ${WING_AR[ord[0][0]]} أكثر من غيره (${ord[0][1]} هجومًا على مربعات في نصف الخصم)`);
    const wing = Object.keys(S).sort((a, b) => S[b] - S[a] || (b === ew) - (a === ew) || (b === "c") - (a === "c"))[0];
    // levers: your pawn moves on that wing that attack an enemy pawn (a break) or, with opposite kings, storm toward his king
    const gm = new ChessLib(g.turn() === me ? fen : (() => { const p = fen.split(" "); p[1] = me; p[3] = "-"; return p.join(" "); })());
    const levers = [];
    for (const m of gm.moves({ verbose: true })) {
      if (m.piece !== "p" || WING_OF(m.from[0]) !== wing || m.captured) continue;
      const t = tagsOf(gm.fen(), m.from + m.to + (m.promotion || ""));
      const storm = opposite && wing === ew && Math.abs(m.to.charCodeAt(0) - ek.charCodeAt(0)) <= 2;
      if (t.includes("break") || storm) levers.push({ san: m.san, k: (t.includes("break") ? 0 : 10) + Math.abs(m.to.charCodeAt(0) - ek.charCodeAt(0)) - (m.flags.includes("b") ? 0.5 : 0) });
    }
    levers.sort((a, b) => a.k - b.k);
    return { me, wing, name: WING_AR[wing], scores: S, reasons: R.filter((x) => x.w === wing).sort((a, b) => b.n - a.n).map((x) => x.t), other: R.filter((x) => x.w !== wing && x.n >= 2).map((x) => x.t), levers: levers.slice(0, 3).map((x) => x.san), opposite };
  }
  /* The wing a sequence of moves plays on: the destination squares of `side`'s moves (castling ignored). */
  function wingOfMoves(fen, sans, side) {
    const g = new ChessLib(fen); const c = { q: 0, c: 0, k: 0 }; const me = side || g.turn();
    for (const s of sans) { const mover = g.turn(); const m = g.move(s, { sloppy: true }); if (!m) break; if (mover === me && !m.flags.includes("k") && !m.flags.includes("q")) c[WING_OF(m.to[0])]++; }
    const w = Object.keys(c).sort((a, b) => c[b] - c[a])[0];
    return c[w] ? { wing: w, name: WING_AR[w], counts: c } : null;
  }
  const T = { tagsOf, knightJump, structure, structPlan, compass, wingOfMoves, WING_AR, WING_OF };
  if (isNode) module.exports = T; else root.Tech = T;
})(typeof self !== "undefined" ? self : this);
