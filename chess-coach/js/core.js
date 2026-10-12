"use strict";
/* Core: helpers, storage, Stockfish, Claude, data, board, tap-only solver with the Socratic ladder. */

const START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
const DAY = 86400000;
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const mv = (s) => `<bdi class="mv">${esc(s)}</bdi>`;
const now = () => Date.now();
const pct = (x) => (x == null || isNaN(x) ? "–" : Math.round(x) + "%");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const pick = (a) => a[Math.floor(Math.random() * a.length)];
const shuffle = (a) => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const uid = () => now().toString(36) + Math.random().toString(36).slice(2, 7);
const fmtEval = (cp) => cp == null ? "–" : Math.abs(cp) >= 9000 ? (cp > 0 ? "#" : "-#") + Math.round((10000 - Math.abs(cp)) / 10) : (cp > 0 ? "+" : "") + (cp / 100).toFixed(1);
function wp(cp) { return 50 + 50 * (2 / (1 + Math.exp(-0.00368208 * cp)) - 1); }
const sideOf = (fen) => fen.split(" ")[1];
const sideAr = (c) => (c === "w" ? "الأبيض" : "الأسود");
function uciMove(game, uci) { return game.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci[4] || "q" }); }
function fenAfter(fen, uci) { const g = new Chess(fen); return uciMove(g, uci) ? g.fen() : null; }
function sanOf(fen, uci) { const g = new Chess(fen); const m = uciMove(g, uci); return m ? m.san : uci; }
function pvToSan(fen, pv, max = 8) { const g = new Chess(fen); const out = []; for (const u of (pv || []).slice(0, max)) { const m = uciMove(g, u); if (!m) break; out.push(m.san); } return out; }
function numberedLine(fen, sans) {
  const p = fen.split(" "); let n = +p[5] || 1; let white = p[1] === "w"; const out = [];
  sans.forEach((s, i) => { out.push(white ? n + ". " + s : i === 0 ? n + "... " + s : s); if (!white) n++; white = !white; });
  return out.join(" ");
}
function pieceList(fen) {
  const g = new Chess(fen); const W = [], B = []; const nm = { k: "K", q: "Q", r: "R", b: "B", n: "N", p: "" };
  for (const f of "abcdefgh") for (let r = 1; r <= 8; r++) { const p = g.get(f + r); if (p) (p.color === "w" ? W : B).push(nm[p.type] + f + r); }
  return `White: ${W.join(", ")} | Black: ${B.join(", ")}`;
}
function moveKind(fen, uci) {
  const g = new Chess(fen); const m = uciMove(g, uci); if (!m) return "quiet";
  if (g.in_checkmate()) return "mate"; if (m.san.includes("+")) return "check"; if (m.captured) return "capture";
  if (m.promotion) return "promotion";
  return "quiet";
}
const KIND_AR = { mate: "كش مات", check: "كش", capture: "أسر", promotion: "ترقية", quiet: "نقلة هادئة (بلا كش ولا أسر)" };

/* ---------- storage ---------- */
const Store = {
  db: null, kind: "memory", mem: {},
  async init() {
    try { this.db = window.claude ? await window.claude.use("db") : null; } catch { this.db = null; }
    this.kind = this.db ? "db" : this.lsOk() ? "local" : "memory";
  },
  lsOk() { try { localStorage.setItem("cc:t", "1"); localStorage.removeItem("cc:t"); return true; } catch { return false; } },
  async get(path) {
    if (this.kind === "db") { const s = await this.db.doc(path).get(); return s.exists ? JSON.parse(JSON.stringify(s.data())) : null; }
    if (this.kind === "local") { try { const v = localStorage.getItem("cc:" + path); return v ? JSON.parse(v) : null; } catch { return null; } }
    return this.mem[path] ? JSON.parse(JSON.stringify(this.mem[path])) : null;
  },
  queue: Promise.resolve(),
  set(path, data) { // writes are serialized so one document never has two writes in flight
    const body = JSON.parse(JSON.stringify(data));
    const job = async () => {
      if (this.kind === "db") { try { await this.db.doc(path).set(body); } catch (e) { if (e && e.code === "unavailable") { await sleep(500 + Math.random() * 700); await this.db.doc(path).set(body); } else console.error("db", e); } return; }
      if (this.kind === "local") { try { localStorage.setItem("cc:" + path, JSON.stringify(body)); } catch {} return; }
      this.mem[path] = body;
    };
    this.queue = this.queue.then(job, job); return this.queue;
  },
  async list(coll) {
    if (this.kind === "db") { const s = await this.db.collection(coll).limit(1000).get(); return s.docs.map((d) => JSON.parse(JSON.stringify(d.data()))); }
    const out = [];
    if (this.kind === "local") { try { for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); if (k.startsWith("cc:" + coll + "/")) out.push(JSON.parse(localStorage.getItem(k))); } } catch {} return out; }
    for (const [k, v] of Object.entries(this.mem)) if (k.startsWith(coll + "/")) out.push(v);
    return out;
  },
};

/* ---------- Stockfish 17.1 (single-threaded "lite" WASM, or pure asm.js when WebAssembly is unavailable) ---------- */
function parseInfo(l) {
  if (/ (lower|upper)bound/.test(l)) return null;
  const d = l.match(/\bdepth (\d+)/), mp = l.match(/\bmultipv (\d+)/), sc = l.match(/\bscore (cp|mate) (-?\d+)/), wd = l.match(/\bwdl (\d+) (\d+) (\d+)/), pv = l.match(/ pv (.+?)(?: bmc .*)?$/);
  if (!d || !sc || !pv) return null;
  return { depth: +d[1], multipv: mp ? +mp[1] : 1, cp: sc[1] === "cp" ? +sc[2] : null, mate: sc[1] === "mate" ? +sc[2] : null, wdl: wd ? [+wd[1], +wd[2], +wd[3]] : null, pv: pv[1].trim().split(/\s+/) };
}
const scoreCp = (s) => s.mate != null ? (s.mate > 0 ? 10000 - s.mate * 10 : -10000 - s.mate * 10) : s.cp;
const Engine = {
  w: null, onLine: null, chain: Promise.resolve(), ok: false, ready: null, kind: null, current: null,
  start() {
    this.ready = (async () => {
      const boot = (w, ms) => new Promise((res, rej) => {
        const t = setTimeout(() => { try { w.terminate(); } catch {} rej(new Error("timeout")); }, ms);
        w.onerror = (e) => { clearTimeout(t); try { w.terminate(); } catch {} rej(e); };
        w.onmessage = (e) => { if (String(e.data) === "uciok") { clearTimeout(t); res(w); } };
        w.postMessage("uci");
      });
      // The WASM build is faster; if the viewer blocks WebAssembly the worker errors or stays silent, and the asm.js build takes over.
      try { this.w = await boot(new Worker("engines/sf17-lite.js"), 20000); this.kind = "wasm"; }
      catch { this.w = await boot(new Worker("engines/sf17-asm.js"), 60000); this.kind = "asm"; }
      this.w.onmessage = (e) => { if (this.onLine) this.onLine(String(e.data)); };
      this.w.postMessage("setoption name UCI_ShowWDL value true");
      this.w.postMessage("setoption name Hash value 32");
      this.ok = true;
    })();
    return this.ready;
  },
  /* Result: {best, cp (White's view), wdl ([w,d,l] per mille, White's view), lines:[{pv, cpWhite, wdlWhite, depth}], terminal}.
     skill < 20 weakens the move choice. low: a background job that a foreground request may interrupt. signal: abort -> "stop". */
  analyse(fen, { movetime = 0, depth = 0, nodes = 0, multipv = 1, skill = 20, low = false, signal = null } = {}) {
    const job = () => new Promise((res) => {
      const g = new Chess(fen);
      if (g.game_over()) {
        const cpStm = g.in_checkmate() ? -10000 : 0; const white = sideOf(fen) === "w";
        const wdl = g.in_checkmate() ? (white ? [0, 0, 1000] : [1000, 0, 0]) : [0, 1000, 0];
        return res({ best: null, cp: white ? cpStm : -cpStm, wdl, lines: [], terminal: true });
      }
      if (signal && signal.aborted) return res({ best: null, cp: 0, wdl: null, lines: [], aborted: true });
      const lines = {}; const white = sideOf(fen) === "w";
      this.current = { low };
      const onAbort = () => this.w.postMessage("stop");
      if (signal) signal.addEventListener("abort", onAbort, { once: true });
      this.onLine = (l) => {
        if (l.startsWith("info")) { const p = parseInfo(l); if (p) lines[p.multipv] = p; }
        else if (l.startsWith("bestmove")) {
          this.onLine = null; this.current = null; if (signal) signal.removeEventListener("abort", onAbort);
          const flip = white ? 1 : -1;
          const ls = Object.values(lines).sort((a, b) => a.multipv - b.multipv).map((x) => ({ ...x, cpWhite: flip * scoreCp(x), wdlWhite: x.wdl ? (white ? x.wdl : [x.wdl[2], x.wdl[1], x.wdl[0]]) : null }));
          const best = l.split(" ")[1];
          res({ best: best && best !== "(none)" ? best : null, cp: ls[0] ? ls[0].cpWhite : 0, wdl: ls[0] ? ls[0].wdlWhite : null, lines: ls, aborted: !!(signal && signal.aborted) });
        }
      };
      this.w.postMessage("setoption name Skill Level value " + skill);
      this.w.postMessage("setoption name MultiPV value " + multipv);
      this.w.postMessage("position fen " + fen);
      let go = "go"; if (depth) go += " depth " + depth; if (movetime) go += " movetime " + movetime; if (nodes) go += " nodes " + nodes;
      this.w.postMessage(go);
    });
    if (!low && this.current && this.current.low && this.w) this.w.postMessage("stop"); // a foreground request cuts a background search short
    const prev = this.chain; const p = this.ready.then(() => prev).then(job, job); this.chain = p.catch(() => {}); return p;
  },
};
/* Win-probability loss of playing `uci` in `fen` for the side to move, with the engine's refutation. */
async function judgeMove(fen, uci, { expected = null, base = null, tol = 5 } = {}) {
  const after = fenAfter(fen, uci); const g = new Chess(after);
  const s = sideOf(fen) === "w" ? 1 : -1;
  if (expected && uci === expected) return { correct: true, loss: 0, after, refutation: [], reply: null };
  if (g.in_checkmate()) return { correct: true, loss: 0, after, refutation: [], reply: null };
  const b = base || await Engine.analyse(fen, { depth: 16, movetime: 1500 });
  const a = await Engine.analyse(after, { depth: 15, movetime: 1200 });
  const loss = Math.max(0, wp(s * b.cp) - wp(s * a.cp));
  return { correct: uci === b.best || loss <= (expected ? 3 : tol), loss: Math.round(loss), after, base: b, refutation: a.lines[0] ? pvToSan(after, a.lines[0].pv, 6) : [], reply: a.best };
}

/* ---------- Claude ---------- */
let SAMPLE = null;
const CLAUDE_ERR = {
  not_granted: "لم تسمح لهذه الصفحة باستخدام Claude، لذلك الشرح من Stockfish فقط.",
  sampling_disabled: "Claude غير متاح لهذا الحساب.",
  rate_limited: "طلبات كثيرة في وقت قصير. انتظر قليلًا.",
  session_expired: "انتهت الجلسة. سجّل الدخول من جديد.",
  invalid_json: "رد Claude لم يكن بالصيغة المتوقعة.",
  refused: "Claude رفض هذا الطلب.",
  upstream_error: "انقطع الاتصال بـ Claude.",
};
const claudeMsg = (e) => CLAUDE_ERR[e && e.code] || CLAUDE_ERR.upstream_error;
const LANG_RULES = `LANGUAGE: Write in clear, simple Modern Standard Arabic for a beginner. Keep chess notation (SAN like Nf3, Bxh7+), opening names and English motif names (fork, pin, opposition, IQP) in English inside the Arabic text. Be short and direct; no praise unless earned.
GROUNDING: Never invent chess variations. Only cite moves that appear in the ENGINE DATA or SOLUTION below, or in the student's own choices. If an idea needs a line that is not provided, describe it in words without concrete moves. Never contradict the engine evaluations.`;
async function askClaude(prompt, { json = false, tier = "default", onText, cache = false } = {}) {
  if (!SAMPLE) throw { code: "not_granted" };
  if (json) return SAMPLE.json(prompt, { modelTier: tier, cache });
  const r = await SAMPLE(prompt, { modelTier: tier, cache, onText }); return r.text;
}
function coachHtml(who, body) { return `<div class="coach"><span class="who">${esc(who)}</span><div class="prewrap">${body}</div></div>`; }
/* Fill `el` with a short Claude explanation of a solved/failed position, grounded in the given lines. */
async function explainInto(el, { fen, solutionSan, played, themes = [], context = "" }) {
  if (!el) return;
  if (!SAMPLE) { el.innerHTML = ""; return; }
  el.innerHTML = coachHtml("المدرّب", "يكتب...");
  const prompt = `You are a chess coach explaining one position to a beginner.
${LANG_RULES}
Write 2-4 short sentences: the key idea of the solution, why it works, and (if the student's move differs) why the student's move falls short. End with one sentence naming the pattern to remember.
POSITION FEN: ${fen} (${sideOf(fen) === "w" ? "White" : "Black"} to move)
PIECES: ${pieceList(fen)}
SOLUTION (verified by Stockfish): ${numberedLine(fen, solutionSan)}
${played ? "STUDENT PLAYED: " + played + "\n" : ""}${themes.length ? "MOTIFS: " + themes.join(", ") + "\n" : ""}${context}`;
  try { await askClaude(prompt, { tier: "quick", cache: { gcTime: 86400000 }, onText: (t) => { el.innerHTML = coachHtml("المدرّب · مقيّد بخطوط Stockfish", esc(t.text)); } }); }
  catch (e) { el.innerHTML = coachHtml("المدرّب", esc(claudeMsg(e))); }
}

/* ---------- data ---------- */
const DATA = { puzzles: [], playout: [], structures: [], opposition: [], masters: [] };
async function loadData() {
  const get = async (f) => { try { const r = await fetch("data/" + f); return r.ok ? await r.json() : []; } catch { return []; } };
  [DATA.puzzles, DATA.playout, DATA.structures, DATA.opposition, DATA.masters] = await Promise.all(["puzzles.json", "playout.json", "structures.json", "opposition.json", "masters.json"].map(get));
  DATA.byId = Object.fromEntries(DATA.puzzles.map((p) => [p.i, p]));
}
function skillOf(themes) {
  if (themes.some((t) => /Endgame$/.test(t)) || themes.includes("endgame")) return "endgame";
  if (themes.includes("defensiveMove")) return "defence";
  if (themes.includes("quietMove") || themes.includes("equality")) return "strategy";
  return "tactics";
}
/* A training item. kind "puzzle": has a forced solution. kind "pos": judged by the engine only. */
function puzzleItem(p) {
  const sol = p.s.split(" ");
  return { kind: "puzzle", id: p.i, fen: p.f, last: p.l, lastSan: p.ls, sol, rating: p.r, themes: p.t, skill: skillOf(p.t) };
}
function oppositionItem(o) { return { kind: "puzzle", id: o.i, fen: o.f, sol: [o.best], rating: 1100, themes: ["opposition", "pawnEndgame"], skill: "endgame", result: o.result }; }
function libItem(p) { return { kind: "pos", id: p.id, fen: p.fen, skill: p.skill, themes: [p.chunkKey || "lib"], note: p.note, chunkName: p.chunk, rating: 1200 }; }

/* ---------- board ---------- */
const ARROW_COLORS = { good: "var(--arrow-good)", bad: "var(--arrow-bad)", plan: "var(--arrow-plan)", alt: "var(--arrow-alt)" };
function Board(el, init) {
  const st = Object.assign({ fen: START_FEN, orient: "w", last: null, interactive: true, hidden: false, dots: true, coords: true, logicFen: null, marks: {}, arrows: [], onMove: null, onSquare: null }, init);
  let sel = null; const files = "abcdefgh";
  const logic = () => new Chess(st.logicFen || st.fen);
  const center = (sq) => { const f = files.indexOf(sq[0]), r = +sq[1] - 1; const col = st.orient === "w" ? f : 7 - f, row = st.orient === "w" ? 7 - r : r; return [col + 0.5, row + 0.5]; };
  function arrowSvg() {
    if (!st.arrows || !st.arrows.length) return "";
    return `<svg class="arrows" viewBox="0 0 8 8" aria-hidden="true">${st.arrows.map((a) => {
      const [x1, y1] = center(a.from), [x2, y2] = center(a.to); const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1, ux = dx / L, uy = dy / L;
      const hx = x2 - ux * 0.32, hy = y2 - uy * 0.32, sx = x1 + ux * 0.22, sy = y1 + uy * 0.22; const w = 0.2, px = -uy, py = ux; const c = ARROW_COLORS[a.color || "good"] || a.color;
      return `<g style="color:${c}"><line x1="${sx}" y1="${sy}" x2="${hx}" y2="${hy}" stroke="currentColor" stroke-width="0.16" stroke-linecap="round" opacity=".85"></line><polygon points="${x2},${y2} ${hx + px * w},${hy + py * w} ${hx - px * w},${hy - py * w}" fill="currentColor" opacity=".9"></polygon></g>`;
    }).join("")}</svg>`;
  }
  function draw() {
    const show = new Chess(st.fen); const lg = logic();
    const legal = sel && st.dots ? lg.moves({ square: sel, verbose: true }) : [];
    let html = "";
    for (let row = 0; row < 8; row++) for (let col = 0; col < 8; col++) {
      const f = st.orient === "w" ? col : 7 - col, r = st.orient === "w" ? 7 - row : row;
      const sq = files[f] + (r + 1); const p = st.hidden ? null : show.get(sq); const light = (f + r) % 2 === 1;
      const cls = ["sq", light ? "l" : "d"];
      if (st.last && (st.last.slice(0, 2) === sq || st.last.slice(2, 4) === sq)) cls.push("last");
      if (sel === sq) cls.push("sel");
      if (st.marks[sq]) cls.push(st.marks[sq]);
      const lm = legal.find((m) => m.to === sq); if (lm) cls.push("dot", lm.captured ? "cap" : "x");
      const co = st.coords ? (col === 0 ? `<span class="co r">${r + 1}</span>` : "") + (row === 7 ? `<span class="co f">${files[f]}</span>` : "") : "";
      html += `<button type="button" class="${cls.join(" ")}" data-sq="${sq}" aria-label="${sq}">${p ? `<img alt="" src="${PIECES[p.color + p.type]}">` : ""}${co}</button>`;
    }
    el.innerHTML = html + arrowSvg();
  }
  el.onclick = (e) => {
    const b = e.target.closest(".sq"); if (!b) return; const sq = b.dataset.sq;
    if (st.onSquare) { st.onSquare(sq); return; }
    if (!st.interactive) return;
    const lg = logic(); const p = lg.get(sq);
    if (sel) {
      const m = lg.moves({ square: sel, verbose: true }).find((x) => x.to === sq);
      if (m) {
        const g2 = logic(); const made = g2.move({ from: m.from, to: m.to, promotion: "q" }); sel = null; draw();
        st.onMove && st.onMove({ from: m.from, to: m.to, san: made.san, uci: m.from + m.to + (made.promotion || ""), fenAfter: g2.fen() });
        return;
      }
      if (!st.dots && !(p && p.color === lg.turn())) { el.classList.add("shake"); setTimeout(() => el.classList.remove("shake"), 300); }
    }
    sel = p && p.color === lg.turn() && sel !== sq ? sq : null; draw();
  };
  draw();
  return { update(o) { Object.assign(st, o); if (!Object.keys(o).every((k) => k === "arrows" || k === "marks")) sel = null; draw(); }, get state() { return st; } }; // drawing arrows keeps a half-made move
}

/* ---------- ratings & spaced repetition ---------- */
function eloUpdate(r, opp, score, n) { const k = n < 30 ? 40 : 20; const e = 1 / (1 + Math.pow(10, (opp - r) / 400)); return Math.round(r + k * (score - e)); }
function sm2(card, q) {
  card.ef = card.ef ?? 2.5; card.reps = card.reps ?? 0; card.interval = card.interval ?? 0; card.lapses = card.lapses ?? 0;
  if (q < 3) { card.reps = 0; card.interval = 1; card.lapses++; }
  else { card.reps++; card.interval = card.reps === 1 ? 1 : card.reps === 2 ? 3 : Math.round(card.interval * card.ef); }
  card.ef = Math.max(1.3, card.ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)));
  card.due = now() + card.interval * DAY; card.history = [...(card.history || []), { t: now(), q }].slice(-20);
  return card;
}
function qualityOf(r) { return r.solvedAt === 1 ? (r.confidence >= 4 ? 5 : 4) : r.solvedAt === 2 ? 3 : r.solvedAt === 3 ? 2 : 1; }

/* ---------- confidence picker ---------- */
function confRow(name = "conf") {
  return `<div class="f"><b>ثقتك في هذه النقلة</b><div class="conf" role="radiogroup">${[1, 2, 3, 4, 5].map((k) => `<label><input type="radio" name="${name}" value="${k}"><span>${k}</span></label>`).join("")}</div><span class="note">1 = تخمين، 5 = متأكد تمامًا</span></div>`;
}
function askConfidence(box, title = "قبل أن ترى النتيجة: ما ثقتك؟") {
  return new Promise((res) => {
    box.innerHTML = `<div class="confask"><b>${title}</b><div class="conf big">${[1, 2, 3, 4, 5].map((k) => `<button type="button" data-c="${k}">${k}</button>`).join("")}</div><span class="note">1 = تخمين، 5 = متأكد تمامًا</span></div>`;
    for (const b of $$("[data-c]", box)) b.onclick = () => res(+b.dataset.c);
  });
}

/* ---------- the tap-only solver with the Socratic ladder ----------
   Plays a puzzle on the board. First wrong move: find the opponent's refutation yourself.
   Second: a guiding question (Claude) plus the kind of move to look for. Third, or "show": the solution.
   opts: {labelHtml, timed: seconds, askConf: true, ladder: true, onDone(result)} */
function Solver(root, item, opts = {}) {
  const o = Object.assign({ askConf: true, ladder: true, timed: 0, labelHtml: "" }, opts);
  const stm = sideOf(item.fen); window.__item = item;
  const R = { itemId: item.id, kind: item.kind, skill: item.skill, rating: item.rating, themes: item.themes, fails: [], confidence: null, t0: now(), timed: !!o.timed };
  let fen = item.fen, step = 0, board, timer = null, finished = false, base = null, phase = "play";
  root.innerHTML = `
    <div class="train">
      <div class="boardwrap">
        <div class="boardcap"><span class="turn"><i class="${stm}"></i>الدور ${stm === "w" ? "للأبيض" : "للأسود"}</span>${item.lastSan ? `<span>آخر نقلة: ${mv(item.lastSan)}</span>` : ""}<span class="clock" hidden></span></div>
        <div class="board"></div>
        <div class="row stepper" hidden><button class="btn quiet" data-st="-1">◀</button><span class="note sttext"></span><button class="btn quiet" data-st="1">▶</button></div>
      </div>
      <div class="panel side">
        ${o.labelHtml}
        <p class="prompt">اختر النقلة الأفضل ${stm === "w" ? "للأبيض" : "للأسود"} بالنقر على القطعة ثم المربع.</p>
        <div class="ask"></div><div class="ladder"></div><div class="explain"></div><div class="done"></div>
      </div>
    </div>`;
  const ask = $(".ask", root), lad = $(".ladder", root), done = $(".done", root), prompt = $(".prompt", root);
  board = Board($(".board", root), { fen, orient: stm, last: item.last, onMove });
  if (item.kind === "pos") Engine.analyse(fen, { depth: 16, movetime: 1500 }).then((b) => { base = b; });
  if (o.timed) {
    const clk = $(".clock", root); clk.hidden = false; let left = o.timed;
    const tick = () => { clk.textContent = "⏱ " + left + "s"; clk.classList.toggle("low", left <= 10); if (left-- <= 0) { clearInterval(timer); timeout(); } };
    tick(); timer = setInterval(tick, 1000);
  }
  if (o.preFail) {
    const pm = o.preFail.move, pj = o.preFail.judged;
    R.fails.push({ move: pm.san, loss: pj.loss, step: 0 }); R.firstMove = pm.san; R.firstLoss = pj.loss; R.seconds = 0;
    setTimeout(() => rung(pm, pj), 0);
  }
  function timeout() { if (finished) return; R.timedOut = true; R.solvedAt = 0; reveal("انتهى الوقت."); }

  async function onMove(m) {
    if (finished || phase !== "play") return;
    phase = "busy";
    board.update({ fen: m.fenAfter, last: m.uci, interactive: false });
    if (step === 0 && o.askConf && R.confidence == null) { if (timer) clearInterval(timer); R.confidence = await askConfidence(ask); ask.innerHTML = ""; }
    if (step === 0 && R.firstMove == null) { R.firstMove = m.san; R.seconds = Math.round((now() - R.t0) / 1000); }
    prompt.innerHTML = `<span class="note">Stockfish يتحقق...</span>`;
    const expected = item.sol ? item.sol[step] : null;
    const j = await judgeMove(fen, m.uci, { expected, base: step === 0 && item.kind === "pos" ? base : null });
    if (j.correct) {
      const alt = expected && m.uci !== expected;
      fen = j.after;
      if (!item.sol || alt || step + 1 >= item.sol.length) return success();
      // opponent replies with the solution move, then the student continues
      const reply = item.sol[step + 1]; await sleep(450);
      const g = new Chess(fen); const rm = uciMove(g, reply); fen = g.fen(); step += 2;
      if (step >= item.sol.length) return success();
      board.update({ fen, last: reply, interactive: true });
      prompt.innerHTML = `صحيح. الخصم ردّ بـ ${mv(rm.san)}. أكمل.`;
      phase = "play"; return;
    }
    // wrong
    R.fails.push({ move: m.san, loss: j.loss, step });
    if (step === 0 && R.fails.length === 1) R.firstLoss = j.loss;
    if (o.timed) { R.solvedAt = 0; return reveal("النقلة خاطئة."); }
    if (!o.ladder || R.fails.length >= 3) { R.solvedAt = 0; return reveal(); }
    await rung(m, j);
  }

  async function rung(m, j) {
    const n = R.fails.length;
    if (n === 1) {
      // Rung 1: find the refutation yourself
      prompt.innerHTML = `<b>${mv(m.san)} لا تنجح.</b> قبل أن تحاول مرة أخرى: الرقعة تُظهر الموقف بعد نقلتك. <b>ما أقوى رد للخصم؟</b> انقره على الرقعة.`;
      board.update({ fen: j.after, last: m.uci, interactive: true, onMove: async (r) => {
        board.update({ interactive: false, onMove });
        const hit = r.uci === j.reply;
        const refSan = j.refutation[0] || (j.reply ? sanOf(j.after, j.reply) : "?");
        R.fails[0].foundRefutation = hit;
        lad.innerHTML = `<div class="callout ${hit ? "good" : ""}">${hit ? `صحيح، ${mv(refSan)} هو الرد. لهذا تفشل نقلتك.` : `الرد الأقوى هو ${mv(refSan)}${j.refutation.length > 1 ? ` (الخط: ${mv(j.refutation.slice(0, 4).join(" "))})` : ""}. هذا ما فاتك في فحص الخطأ.`}</div>`;
        await sleep(300); backToStart("جرّب نقلة أخرى من الموقف الأصلي.");
      } });
      phase = "ladder";
      return;
    }
    // Rung 2: the kind of move + a guiding question
    const target = item.sol ? item.sol[step] : (base || await Engine.analyse(fen, { depth: 16, movetime: 1500 })).best;
    const kind = moveKind(fen, target);
    lad.innerHTML = `<div class="callout">تلميح: النقلة الصحيحة هي <b>${KIND_AR[kind]}</b>. ابدأ بفحص كل ${kind === "quiet" ? "النقلات التي تخلق تهديدًا أو تمنع تهديد الخصم" : "الكشات والأسر"}.</div><div class="q"></div>`;
    backToStart("حاول مرة أخيرة.", true);
    if (SAMPLE) {
      const q = $(".q", lad); q.innerHTML = coachHtml("سؤال المدرّب", "يفكّر...");
      const solSan = item.sol ? pvToSan(fen, item.sol.slice(step), 6) : pvToSan(fen, [target], 1);
      const prompt2 = `You are a Socratic chess coach. The student (a beginner, ${sideOf(fen) === "w" ? "White" : "Black"} to move) failed twice. Ask ONE short guiding question in Arabic (max 30 words) that points their attention to the right idea WITHOUT naming the solution move, its piece+square, or its destination square.
${LANG_RULES}
Reply with only JSON: {"question_ar":"..."}
FEN: ${fen}
PIECES: ${pieceList(fen)}
SOLUTION (secret): ${numberedLine(fen, solSan)}
STUDENT'S WRONG MOVES: ${R.fails.map((f) => f.move).join(", ")}
MOTIFS: ${(item.themes || []).join(", ")}`;
      try { const r = await askClaude(prompt2, { json: true, tier: "quick" }); q.innerHTML = coachHtml("سؤال المدرّب", esc(r.question_ar || "")); }
      catch (e) { q.innerHTML = ""; }
    }
  }
  function backToStart(msg, showReveal = false) {
    board.update({ fen, last: item.last && step === 0 ? item.last : null, interactive: true, onMove });
    prompt.innerHTML = msg;
    if (showReveal || R.fails.length >= 2) done.innerHTML = `<button class="btn ghost" data-rev>أظهر الحل</button>`;
    const rv = $("[data-rev]", done); if (rv) rv.onclick = () => { R.revealedEarly = true; R.solvedAt = 0; reveal(); };
    phase = "play";
  }
  function success() {
    R.solvedAt = R.fails.length + 1; R.correct = R.fails.length === 0;
    finish(`<div class="callout good"><b>${R.correct ? "صحيح من المحاولة الأولى." : "وجدتها بعد " + R.fails.length + (R.fails.length === 1 ? " خطأ." : " أخطاء.")}</b></div>`);
    if (!R.correct) explainInto($(".explain", root), { fen: item.fen, solutionSan: solutionSan(), played: R.fails[0]?.move, themes: item.themes });
    else done.insertAdjacentHTML("afterbegin", SAMPLE ? `<button class="btn quiet" data-why>اشرح لي الفكرة</button>` : "");
    const w = $("[data-why]", done); if (w) w.onclick = () => { w.remove(); explainInto($(".explain", root), { fen: item.fen, solutionSan: solutionSan(), themes: item.themes }); };
  }
  function solutionSan() { return item.sol ? pvToSan(item.fen, item.sol, 12) : base ? pvToSan(item.fen, base.lines[0]?.pv || [base.best], 6) : []; }
  async function reveal(why = "") {
    if (finished) return; R.correct = false; if (R.solvedAt == null) R.solvedAt = 0;
    if (!item.sol && !base) base = await Engine.analyse(item.fen, { depth: 16, movetime: 1500 });
    const line = item.sol || (base.lines[0]?.pv || [base.best]).slice(0, 6);
    const sans = pvToSan(item.fen, line, 12);
    // step through the solution on the board
    const fens = [item.fen]; { const g = new Chess(item.fen); for (const u of line) { if (!uciMove(g, u)) break; fens.push(g.fen()); } }
    let k = 1; const stp = $(".stepper", root); stp.hidden = false;
    const show = () => { board.update({ fen: fens[k], last: line[k - 1], interactive: false }); $(".sttext", root).innerHTML = mv(numberedLine(item.fen, sans.slice(0, k))); };
    for (const b of $$("[data-st]", stp)) b.onclick = () => { k = Math.max(0, Math.min(fens.length - 1, k + +b.dataset.st)); show(); };
    show();
    finish(`<div class="callout bad"><b>${why} الحل:</b> ${mv(numberedLine(item.fen, sans))}</div>${item.note ? coachHtml("ملاحظة متحقق منها بـ Stockfish", esc(item.note)) : ""}`);
    explainInto($(".explain", root), { fen: item.fen, solutionSan: sans, played: R.fails[0]?.move || R.firstMove, themes: item.themes });
  }
  function finish(html) {
    finished = true; if (timer) clearInterval(timer);
    if (R.seconds == null) R.seconds = Math.round((now() - R.t0) / 1000);
    prompt.innerHTML = ""; ask.innerHTML = ""; board.update({ interactive: false });
    done.innerHTML = html + `<div class="row"><button class="btn" data-next>التالي</button></div>`;
    $("[data-next]", done).onclick = () => o.onDone && o.onDone(R);
  }
  return { result: R };
}
