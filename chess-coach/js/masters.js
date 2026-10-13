"use strict";
/* Masters: what strong players played in a position, and how it scored (KingBase 2017, aggregate counts only), plus
   opening names (lichess-org/chess-openings, CC0). Static files in data/masters/, built by tools/masters_tree/build.py.
   Shards are fetched on first use and cached; any missing file makes the lookup return null.
   Browser: global Masters (needs chess.js). Node (tests): require("./js/masters.js") reads the files from disk. */
(function (root) {
  const isNode = typeof module !== "undefined" && module.exports && typeof window === "undefined";
  const ChessLib = root.Chess || (isNode ? require("../chess.js").Chess : null);
  const BASE = "data/masters/";
  let fsRead = null;
  if (isNode) { const fs = require("fs"), path = require("path"); const dir = path.join(__dirname, "..", BASE); fsRead = (f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")); }
  const cache = {};
  function load(file) {
    if (!cache[file]) cache[file] = (async () => {
      try { if (fsRead) return fsRead(file); const r = await fetch(BASE + file); return r.ok ? await r.json() : null; } catch { return null; }
    })();
    return cache[file];
  }
  function fnv1a32(s) { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } return h >>> 0; }
  /* Same key as python-chess board.epd(): FEN fields 1-4, en-passant square only if an en-passant capture is legal. */
  function keyOf(fen) {
    const p = fen.split(" ");
    let ep = "-";
    if (p[3] && p[3] !== "-") { const g = new ChessLib(fen); if (g.moves({ verbose: true }).some((m) => m.flags.includes("e"))) ep = p[3]; }
    return `${p[0]} ${p[1]} ${p[2] || "-"} ${ep}`;
  }
  async function lookup(fen) {
    const idx = await load("index.json"); if (!idx) return null;
    const key = keyOf(fen); const sh = await load(`s${String(fnv1a32(key) % idx.shards).padStart(2, "0")}.json`);
    const e = sh && sh[key]; if (!e) return null;
    const white = fen.split(" ")[1] === "w";
    return {
      total: e[0], other: e[2],
      moves: e[1].map(([san, n, w, d, l]) => { const score = (w + d / 2) / n; return { san, n, w, d, l, share: n / e[0], score, scoreStm: white ? score : 1 - score }; }),
    };
  }
  async function opening(fen) { const o = await load("openings.json"); const e = o && o[keyOf(fen)]; return e ? { eco: e[0], name: e[1] } : null; }
  /* The deepest named opening along a game (start position + SAN moves). */
  async function openingAlong(startFen, sans) {
    const o = await load("openings.json"); if (!o) return null;
    const g = new ChessLib(startFen); let best = null;
    for (let i = 0; i <= sans.length; i++) {
      const e = o[keyOf(g.fen())]; if (e) best = { eco: e[0], name: e[1], ply: i };
      if (i < sans.length && !g.move(sans[i], { sloppy: true })) break;
    }
    return best;
  }
  const api = { lookup, opening, openingAlong, keyOf, fnv1a32 };
  root.Masters = api;
  if (isNode) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
