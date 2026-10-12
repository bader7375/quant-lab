"use strict";
/* Position facts: computed without an engine, so every explanation can be grounded in them.
   Works in the browser (global Chess) and in Node (require). */
(function (root) {
  const ChessLib = typeof Chess !== "undefined" ? Chess : require("../chess.js").Chess;
  const FILES = "abcdefgh";
  const VAL = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };
  const SEEVAL = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 100 };
  const NAME_AR = { p: "البيدق", n: "الحصان", b: "الفيل", r: "الرخ", q: "الوزير", k: "الملك" };
  const other = (c) => (c === "w" ? "b" : "w");
  const sqOf = (f, r) => FILES[f] + (r + 1);
  const fr = (sq) => [FILES.indexOf(sq[0]), +sq[1] - 1];

  function grid(g) { const b = g.board(); const G = {}; for (let r = 0; r < 8; r++) for (let f = 0; f < 8; f++) { const p = b[7 - r][f]; if (p) G[sqOf(f, r)] = p; } return G; }

  /* Pieces of `color` attacking `sq` (pseudo-attacks: pins ignored, no x-rays). */
  function attackers(G, sq, color) {
    const [f, r] = fr(sq); const out = [];
    const at = (ff, rr) => (ff >= 0 && ff < 8 && rr >= 0 && rr < 8 ? G[sqOf(ff, rr)] : undefined);
    const dr = color === "w" ? -1 : 1;
    for (const df of [-1, 1]) { const p = at(f + df, r + dr); if (p && p.color === color && p.type === "p") out.push({ sq: sqOf(f + df, r + dr), type: "p" }); }
    for (const [a, b] of [[1, 2], [2, 1], [-1, 2], [-2, 1], [1, -2], [2, -1], [-1, -2], [-2, -1]]) { const p = at(f + a, r + b); if (p && p.color === color && p.type === "n") out.push({ sq: sqOf(f + a, r + b), type: "n" }); }
    for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) { if (!a && !b) continue; const p = at(f + a, r + b); if (p && p.color === color && p.type === "k") out.push({ sq: sqOf(f + a, r + b), type: "k" }); }
    for (const [a, b, kinds] of [[1, 0, "rq"], [-1, 0, "rq"], [0, 1, "rq"], [0, -1, "rq"], [1, 1, "bq"], [1, -1, "bq"], [-1, 1, "bq"], [-1, -1, "bq"]]) {
      let ff = f + a, rr = r + b;
      while (ff >= 0 && ff < 8 && rr >= 0 && rr < 8) { const p = G[sqOf(ff, rr)]; if (p) { if (p.color === color && kinds.includes(p.type)) out.push({ sq: sqOf(ff, rr), type: p.type }); break; } ff += a; rr += b; }
    }
    return out;
  }

  /* Static exchange evaluation: material `by` wins by starting a capture sequence on `sq` (0 if it cannot capture). */
  function see(G, sq, by) {
    const target = G[sq]; if (!target || target.color === by) return 0;
    const att = { w: attackers(G, sq, "w").map((x) => SEEVAL[x.type]).sort((a, b) => a - b), b: attackers(G, sq, "b").map((x) => SEEVAL[x.type]).sort((a, b) => a - b) };
    if (!att[by].length) return 0;
    const gain = [SEEVAL[target.type]]; let d = 0; let onSq = att[by].shift(); let s = other(by);
    while (att[s].length) {
      d++; gain[d] = onSq - gain[d - 1];
      if (Math.max(-gain[d - 1], gain[d]) < 0) break;
      onSq = att[s].shift(); s = other(s);
    }
    while (d > 0) { gain[d - 1] = -Math.max(-gain[d - 1], gain[d]); d--; }
    return gain[0];
  }

  /* Pieces of `color` that the opponent could win right now (SEE > 0 for the opponent). */
  function hanging(G, color) {
    const out = [];
    for (const [sq, p] of Object.entries(G)) {
      if (p.color !== color || p.type === "k") continue;
      const s = see(G, sq, other(color));
      if (s > 0) out.push({ sq, type: p.type, gain: s, defended: attackers(G, sq, color).length > 0 });
    }
    return out.sort((a, b) => b.gain - a.gain);
  }

  const HOME = { w: { b1: "n", g1: "n", c1: "b", f1: "b" }, b: { b8: "n", g8: "n", c8: "b", f8: "b" } };
  function development(G, color) {
    const undeveloped = Object.entries(HOME[color]).filter(([sq, t]) => G[sq] && G[sq].color === color && G[sq].type === t).map(([sq]) => sq);
    const ksq = Object.keys(G).find((s) => G[s].type === "k" && G[s].color === color);
    const back = color === "w" ? "1" : "8";
    const castled = !!ksq && ksq[1] === back && "bcgh".includes(ksq[0]);
    const kingCenter = !!ksq && "def".includes(ksq[0]);
    const qHome = color === "w" ? "d1" : "d8";
    const queenOut = !(G[qHome] && G[qHome].type === "q" && G[qHome].color === color) && Object.values(G).some((p) => p.type === "q" && p.color === color);
    return { undeveloped, developed: 4 - undeveloped.length, castled, kingCenter, queenOut, king: ksq };
  }

  function kingSafety(G, color) {
    const ksq = Object.keys(G).find((s) => G[s].type === "k" && G[s].color === color); if (!ksq) return null;
    const [kf, kr] = fr(ksq); const dir = color === "w" ? 1 : -1;
    let shield = 0; const openFiles = [];
    for (let f = Math.max(0, kf - 1); f <= Math.min(7, kf + 1); f++) {
      for (const dr of [1, 2]) { const p = G[sqOf(f, kr + dir * dr)] ; if (kr + dir * dr >= 0 && kr + dir * dr < 8 && p && p.type === "p" && p.color === color) { shield++; break; } }
      let own = false; for (let r = 0; r < 8; r++) { const p = G[sqOf(f, r)]; if (p && p.type === "p" && p.color === color) own = true; }
      if (!own) openFiles.push(FILES[f]);
    }
    const near = new Set();
    for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) { const f = kf + a, r = kr + b; if (f < 0 || f > 7 || r < 0 || r > 7) continue; for (const x of attackers(G, sqOf(f, r), other(color))) if (x.type !== "k") near.add(x.sq); }
    return { sq: ksq, shield, openFiles, attackers: near.size };
  }

  const CENTER = ["d4", "e4", "d5", "e5"];
  function center(G, color) {
    let pawns = 0, control = 0, pieces = 0;
    for (const sq of CENTER) { const p = G[sq]; if (p && p.color === color) { if (p.type === "p") pawns++; else pieces++; } control += attackers(G, sq, color).length; }
    return { pawns, pieces, control };
  }

  function pawnStructure(G, color) {
    const files = Array.from({ length: 8 }, () => []); const enemy = Array.from({ length: 8 }, () => []);
    for (const [sq, p] of Object.entries(G)) if (p.type === "p") { const [f, r] = fr(sq); (p.color === color ? files : enemy)[f].push(r); }
    const doubled = [], isolated = [], passed = [];
    files.forEach((rs, f) => {
      if (!rs.length) return;
      if (rs.length > 1) doubled.push(FILES[f]);
      const adj = (files[f - 1] || []).length + (files[f + 1] || []).length; if (!adj) isolated.push(...rs.map((r) => sqOf(f, r)));
      for (const r of rs) {
        const ahead = (er) => (color === "w" ? er > r : er < r);
        if (![f - 1, f, f + 1].some((ff) => ff >= 0 && ff < 8 && enemy[ff].some(ahead))) passed.push(sqOf(f, r));
      }
    });
    return { doubled, isolated, passed, islands: files.reduce((n, rs, f) => n + (rs.length && !(files[f - 1] || []).length ? 1 : 0), 0) };
  }

  function material(G) { const m = { w: 0, b: 0 }; for (const p of Object.values(G)) m[p.color] += VAL[p.type]; return { ...m, diff: m.w - m.b }; }
  function phaseOf(G, ply) {
    const npm = Object.values(G).reduce((s, p) => s + (p.type !== "p" && p.type !== "k" ? VAL[p.type] : 0), 0);
    const queens = Object.values(G).filter((p) => p.type === "q").length;
    if (npm <= 26 || (queens === 0 && npm <= 32)) return "endgame";
    const dev = development(G, "w").developed + development(G, "b").developed;
    if ((ply ?? 99) < 16 || ((ply ?? 99) < 26 && dev < 7)) return "opening";
    return "middlegame";
  }

  function positionFacts(fen, ply) {
    const g = new ChessLib(fen); const G = grid(g); const turn = g.turn();
    const checks = g.moves({ verbose: true }).filter((m) => /[+#]/.test(m.san)).map((m) => m.san);
    const captures = g.moves({ verbose: true }).filter((m) => m.captured).map((m) => ({ san: m.san, see: see(G, m.to, turn) }));
    const f = { turn, inCheck: g.in_check(), material: material(G), phase: phaseOf(G, ply), checks, goodCaptures: captures.filter((c) => c.see > 0).map((c) => c.san) };
    for (const c of ["w", "b"]) f[c] = { hanging: hanging(G, c), dev: development(G, c), king: kingSafety(G, c), center: center(G, c), pawns: pawnStructure(G, c) };
    return f;
  }

  /* Chapter 1 opening checklist for one side, from the game's SAN moves. null if the game is too short to judge. */
  function openingChecklist(sans, color, startFen) {
    const g = new ChessLib(startFen || undefined); const own = [];
    for (const san of sans) {
      const before = grid(g); const mover = g.turn();
      const m = g.move(san, { sloppy: true }); if (!m) break;
      if (mover === color) own.push({ m, before, n: own.length + 1 });
      if (own.length >= 12) break;
    }
    if (own.length < 10) return null;
    const first = (k) => own.slice(0, k);
    const centre = first(10).some(({ m }) => m.piece === "p" && ["d4", "e4", "d5", "e5"].includes(m.to));
    const left = new Set(); for (const { m } of first(10)) if (HOME[color][m.from] === m.piece) left.add(m.from);
    const develop = left.size >= 3;
    const castle = first(12).some(({ m }) => m.flags.includes("k") || m.flags.includes("q"));
    const qMoves = first(8).filter(({ m }) => m.piece === "q" && !m.captured);
    const queen = qMoves.length <= 1 && !first(4).some(({ m }) => m.piece === "q" && !m.captured);
    let repeat = true; const movedFrom = {};
    for (const { m, before } of first(8)) {
      if (m.piece !== "n" && m.piece !== "b") continue;
      if (movedFrom[m.from]) {
        const threatened = see(before, m.from, other(color)) > 0 || attackers(before, m.from, other(color)).some((a) => VAL[a.type] < VAL[m.piece]);
        if (!m.captured && !threatened) repeat = false;
      }
      movedFrom[m.to] = true;
    }
    const items = { centre, develop, castle, queen, repeat };
    return { items, score: Object.values(items).filter(Boolean).length };
  }

  /* Short Arabic statements for hints and as grounding for Claude. `side` = the player we talk to. */
  function describe(f, side) {
    const me = f[side], opp = f[other(side)]; const out = [];
    for (const h of me.hanging.slice(0, 2)) out.push(`${NAME_AR[h.type]} على ${h.sq} يمكن أن يُكسب${h.defended ? " رغم أنه محمي" : " لأنه غير محمي"}.`);
    for (const h of opp.hanging.slice(0, 2)) out.push(`${NAME_AR[h.type]} الخصم على ${h.sq} معرّض للكسب.`);
    if (f.phase === "opening") {
      if (me.dev.undeveloped.length >= 2) out.push(`قطع لم تتطور بعد: ${me.dev.undeveloped.map((s) => NAME_AR["bg".includes(s[0]) ? "n" : "b"] + " على " + s).join("، ")}.`);
      if (!me.dev.castled && me.dev.kingCenter) out.push("ملكك ما زال في المركز.");
      if (me.center.pawns === 0) out.push("لا بيدق لك في المركز (d4، e4، d5، e5).");
    }
    if (me.king && me.king.attackers >= 3) out.push(`حول ملكك ${me.king.attackers} قطع للخصم تهاجم مربعاته.`);
    if (f.checks.length && f.turn === side) out.push(`لديك كشات ممكنة: ${f.checks.slice(0, 3).join("، ")}.`);
    return out;
  }

  const Facts = { grid, attackers, see, hanging, development, kingSafety, center, pawnStructure, material, phaseOf, positionFacts, openingChecklist, describe, NAME_AR, VAL };
  root.Facts = Facts;
  if (typeof module !== "undefined" && module.exports) module.exports = Facts;
})(typeof window !== "undefined" ? window : globalThis);
