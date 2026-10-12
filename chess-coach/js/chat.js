"use strict";
/* Coach chat: questions about the exact position on screen.
   Claude answers from a fact sheet and, where the viewer supports it, calls page tools first
   (engine lines, play a line, position facts). A post-check flags any move it names that is neither
   legal here nor present in the verified data. */

const LEVEL_RULES = {
  basic: "LEVEL: beginner chapter. Use only simple concepts: centre, development, king safety, threats, hanging pieces, attacking and defending, piece activity. Avoid advanced jargon unless the student asks for it.",
  plan: "LEVEL: intermediate. You may also use plans, pawn breaks, open files, weak pawns and pawn structures.",
  positional: "LEVEL: advanced. You may also use outposts, prophylaxis, good and bad bishops, weak squares, the principle of two weaknesses.",
};
const COACH_RULES = `You are the student's private chess coach: a grandmaster-level teacher whose job is to show HOW to think, not just which move is best.
${LANG_RULES}
STYLE: Explain with human concepts (threats, plans, piece activity, structure, king safety). Never quote engine numbers such as "+1.3" or centipawns; describe chances in words, the student sees them in a bar. Keep answers short (3-6 sentences) unless asked for more. When it fits, end with one reusable thinking habit.
MOVES: write moves in SAN (Nf3, Bxh7+, O-O). Only name moves that appear in the DATA or that you checked with a tool.`;

let CLAUDE_CAPS = null;
async function claudeCaps() { if (CLAUDE_CAPS) return CLAUDE_CAPS; try { CLAUDE_CAPS = SAMPLE ? await SAMPLE.limits() : {}; } catch { CLAUDE_CAPS = {}; } return CLAUDE_CAPS; }

/* SAN-looking tokens worth checking: piece moves, captures, castles, promotions, checks. Bare squares like e4 are ignored. */
const SAN_RE = /(?:O-O-O|O-O|[KQRBN][a-h]?[1-8]?x?[a-h][1-8]|[a-h]x[a-h][1-8](?:=[QRBN])?|[a-h][18]=[QRBN])[+#]?/g;
const normSan = (s) => s.replace(/[+#!?]/g, "");
function allowedFrom(fen, lines = []) {
  const A = new Set();
  try { for (const m of new Chess(fen).moves()) A.add(normSan(m)); } catch {}
  try { const p = fen.split(" "); p[1] = p[1] === "w" ? "b" : "w"; p[3] = "-"; for (const m of new Chess(p.join(" ")).moves()) A.add(normSan(m)); } catch {}
  for (const l of lines) for (const s of l) A.add(normSan(s));
  return A;
}
function markSan(textEsc, allowed) {
  const bad = [];
  const html = textEsc.replace(SAN_RE, (t) => { if (allowed && !allowed.has(normSan(t))) { bad.push(t); return `<bdi class="mv unv" title="لم يُتحقق منها">${t}</bdi>`; } return `<bdi class="mv">${t}</bdi>`; });
  return { html, bad };
}

/* The fact sheet: everything Claude may rely on, for one position. */
function factSheet(ctx) {
  const f = Facts.positionFacts(ctx.fen, ctx.ply); const stm = sideOf(ctx.fen);
  const fmtLine = (l) => `${l.san.join(" ")} (chances for ${stm === "w" ? "White" : "Black"} afterwards ≈ ${Math.round(Prob.esFor(l.cp, stm))}%)`;
  const lines = [];
  lines.push(`POSITION (FEN): ${ctx.fen}`);
  lines.push(`SIDE TO MOVE: ${stm === "w" ? "White" : "Black"}`);
  lines.push(`PIECES: ${pieceList(ctx.fen)}`);
  if (ctx.moves && ctx.moves.length) lines.push(`GAME SO FAR: ${numberedLine(ctx.start || START_FEN, ctx.moves)}`);
  if (ctx.engineLines && ctx.engineLines.length) lines.push(`ENGINE (Stockfish 17.1) BEST LINES FROM HERE:\n- ${ctx.engineLines.map(fmtLine).join("\n- ")}`);
  if (ctx.threat) lines.push(`IF IT WERE THE OPPONENT'S MOVE, THEY WOULD PLAY: ${ctx.threat.join(" ")}`);
  lines.push(`COMPUTED FACTS: phase=${f.phase}; material (White minus Black, pawns)=${f.material.diff}; White hanging=[${f.w.hanging.map((h) => h.type.toUpperCase() + h.sq).join(",")}]; Black hanging=[${f.b.hanging.map((h) => h.type.toUpperCase() + h.sq).join(",")}]; developed minor pieces W=${f.w.dev.developed}/4 B=${f.b.dev.developed}/4; castled W=${f.w.dev.castled} B=${f.b.dev.castled}; king attackers near W king=${f.w.king ? f.w.king.attackers : 0}, near B king=${f.b.king ? f.b.king.attackers : 0}; centre pawns W=${f.w.center.pawns} B=${f.b.center.pawns}; checks available to side to move=${f.checks.join(",") || "none"}.`);
  if (ctx.narration) lines.push(`COACH'S NARRATION SHOWN TO THE STUDENT:\n${ctx.narration}`);
  if (ctx.extra) lines.push(ctx.extra);
  return lines.join("\n");
}

/* Page tools Claude may call. Every move they return is added to the allowed set for the post-check. */
function chatTools(ctx, allowed) {
  const addLine = (fen, sans) => { for (const s of sans) allowed.add(normSan(s)); };
  return [
    { name: "engine_lines", description: "Stockfish 17.1 analysis of a position: the 3 best lines in SAN with the side to move's winning chances after each (percent). Defaults to the current position; pass `moves` (SAN, from the current position) to analyse the position after them.",
      inputSchema: { type: "object", properties: { moves: { type: "array", items: { type: "string" } } } },
      async execute(input) {
        const seq = Array.isArray(input.moves) ? input.moves.map(String) : [];
        const g = new Chess(ctx.fen); for (const s of seq) if (!g.move(s, { sloppy: true })) throw new Error("illegal move " + s);
        const fen = g.fen(); const a = await Engine.analyse(fen, { depth: 16, movetime: 1500, multipv: 3 }); const stm = sideOf(fen);
        const out = a.lines.map((l) => { const sans = pvToSan(fen, l.pv, 8); addLine(fen, sans); return { moves: sans, chances_for_side_to_move: Math.round(Prob.esFor(l.cpWhite, stm)) + "%" }; });
        return { side_to_move: stm === "w" ? "White" : "Black", lines: out };
      } },
    { name: "play_line", description: "Play a sequence of SAN moves from the current position. Returns whether it is legal, the resulting position's facts, the best reply line and the chances for both sides afterwards.",
      inputSchema: { type: "object", properties: { moves: { type: "array", items: { type: "string" } } }, required: ["moves"] },
      async execute(input) {
        const seq = (input.moves || []).map(String); const g = new Chess(ctx.fen);
        for (let i = 0; i < seq.length; i++) if (!g.move(seq[i], { sloppy: true })) return { legal: false, illegal_at: i, move: seq[i] };
        addLine(ctx.fen, seq);
        const fen = g.fen(); const a = await Engine.analyse(fen, { depth: 16, movetime: 1500 }); const reply = a.lines[0] ? pvToSan(fen, a.lines[0].pv, 6) : [];
        addLine(fen, reply);
        return { legal: true, white_chances: Math.round(Prob.esFor(a.cp, "w")) + "%", black_chances: Math.round(Prob.esFor(a.cp, "b")) + "%", best_reply_line: reply, facts: Facts.describe(Facts.positionFacts(fen), sideOf(fen)) };
      } },
    { name: "position_facts", description: "Computed facts (no engine) for the current position: hanging pieces, development, king safety, centre, pawn structure, available checks.",
      async execute() { const f = Facts.positionFacts(ctx.fen); return { white: Facts.describe(f, "w"), black: Facts.describe(f, "b"), phase: f.phase }; } },
  ];
}

function Chat(root, { getContext, level = "basic", chips = [], onOpen = null }) {
  const turns = []; // {role, content}
  root.innerHTML = `<div class="chat">
    <div class="chat-h"><b>اسأل المدرّب</b><span class="note">عن الموقف الظاهر على الرقعة الآن</span></div>
    <div class="chat-log" aria-live="polite"></div>
    <div class="chat-chips">${chips.map((c, i) => `<button type="button" class="chip-q" data-q="${i}">${esc(c)}</button>`).join("")}</div>
    <form class="chat-form"><input type="text" class="chat-in" dir="auto" placeholder="اكتب سؤالك..." aria-label="سؤالك"><button class="btn" type="submit">إرسال</button></form></div>`;
  const log = $(".chat-log", root), input = $(".chat-in", root);
  for (const b of $$("[data-q]", root)) b.onclick = () => ask(chips[+b.dataset.q]);
  $(".chat-form", root).onsubmit = (e) => { e.preventDefault(); const q = input.value.trim(); if (q) { input.value = ""; ask(q); } };
  input.onfocus = () => onOpen && onOpen();
  function bubble(cls, html) { const d = document.createElement("div"); d.className = "msg " + cls; d.innerHTML = html; log.appendChild(d); log.scrollTop = log.scrollHeight; return d; }
  async function ask(q) {
    onOpen && onOpen();
    bubble("me", esc(q));
    const ctx = getContext(); const out = bubble("coach", `<span class="note">يفكّر...</span>`);
    const allowed = allowedFrom(ctx.fen, [...(ctx.engineLines || []).map((l) => l.san), ...(ctx.knownLines || [])]);
    if (!SAMPLE) { out.innerHTML = `<span class="note">Claude غير متاح في هذا العرض. هذه حقائق الموقف:</span><ul>${Facts.describe(Facts.positionFacts(ctx.fen), sideOf(ctx.fen)).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`; return; }
    const sheet = factSheet(ctx);
    const msgs = [{ role: "user", content: COACH_RULES + "\n" + (LEVEL_RULES[level] || "") }, ...turns.slice(-6), { role: "user", content: `DATA:\n${sheet}\n\nSTUDENT'S QUESTION: ${q}` }];
    const caps = await claudeCaps(); const useTools = !!caps.tools;
    try {
      const opts = { onText: ({ text }) => { out.innerHTML = markSan(esc(text), null).html; log.scrollTop = log.scrollHeight; } };
      if (useTools) opts.tools = chatTools(ctx, allowed); else opts.cache = false;
      const r = await SAMPLE(msgs, opts);
      const { html, bad } = markSan(esc(r.text), allowed);
      out.innerHTML = html + (bad.length ? `<p class="note warnline">تنبيه: لم أستطع التحقق من ${bad.map((b) => `<bdi class="mv">${esc(b)}</bdi>`).join("، ")} في بيانات المحرك لهذا الموقف، فلا تعتمد عليها.</p>` : "");
      turns.push({ role: "user", content: `(Position ${ctx.fen}) ${q}` }, { role: "assistant", content: r.text });
    } catch (e) { out.innerHTML = `<span class="err">${esc(claudeMsg(e))}</span>`; }
  }
  return { ask };
}
