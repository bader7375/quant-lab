"use strict";
/* خطوطي: the repertoire learned as whole lines, kept in memory with spaced repetition, and each line ended with its plan.
   Data: data/curriculum/ch08/lines.json (tools/repertoire/build_lines.mjs): every line of the repertoire tree, how often
   you meet it, what masters play next (checked with Stockfish) and Stockfish at its end.
   - Learn: the line move by move. Every move of yours gets its ideas, computed from the position (develops, castles,
     prepares d4 because c3 will defend d4, prevents Bg4, steps away before d5 can hit it, the first step of Nbd2-f1-g3...)
     and a short label to remember it by.
   - Recall: you play your moves from memory, the opponent's replies come by themselves. A wrong move shows the line's
     move and its idea, and you play it before going on.
   - Levels: 1 = your first 5 moves, 2 = the whole line, 3 = the line plus what masters play next. A line goes up after
     two recalls without a mistake on different days; reviews follow SM-2.
   - The plan at the end: where to attack (Tech.compass, the reasons shown), what masters played from there and on which
     wing, and Stockfish's line, with the three compared honestly. From level 2 you answer «where do you play?» first.
   No Claude calls. */
let LINES = null;
async function loadLines() { if (!LINES) LINES = (await loadJSON("data/curriculum/ch08/lines.json")).lines; return LINES; }
const LV_OWN = { 1: 5, 2: 8, 3: 12 };
const LV_AR = { 1: "البداية: أول 5 نقلات لك", 2: "الخط كاملًا", 3: "الخط وخطة الأساتذة بعده" };
const LINE_GROUP_AR = { w: "بالأبيض", e5: "بالأسود ضد 1.e4", qgd: "بالأسود ضد 1.d4", "b-other": "بالأسود ضد 1.c4 و1.Nf3" };
const lineSide = (L) => (L.g === "w" ? "w" : "b");
function lineState(id, create = false) { const s = (J.state.lines = J.state.lines || {}); if (!s[id] && create) s[id] = { lv: 1, learned: now(), perfect: 0 }; return s[id] || null; }
/* The moves to recall at a level: up to that many of your moves, ending with yours. */
function lineMoves(L, lv) {
  const me = lineSide(L); const all = lv >= 3 ? [...L.mv, ...L.cont] : L.mv; const g = new Chess(); const out = []; let own = 0;
  for (const s of all) { const mine = g.turn() === me; if (mine && own >= LV_OWN[lv]) break; if (!g.move(s, { sloppy: true })) break; out.push(s); if (mine) own++; }
  while (out.length && (out.length % 2 === 1) !== (me === "w")) out.pop(); // end on your move
  return out;
}
const lineMaxLv = (L) => (lineMoves(L, 3).length > lineMoves(L, 2).length ? 3 : lineMoves(L, 2).length > lineMoves(L, 1).length ? 2 : 1);
const lineShort = (L, n = 6) => numberedLine(START_FEN, L.mv.slice(0, n)) + (L.mv.length > n ? " …" : "");
function linesQueue({ newMax = 2, dueMax = 8 } = {}) {
  if (!LINES) return { due: [], fresh: [] };
  const S = J.state.lines || {};
  const due = LINES.filter((L) => S[L.id] && (S[L.id].due ?? 0) <= now()).sort((a, b) => S[a.id].due - S[b.id].due).slice(0, dueMax);
  const fresh = LINES.filter((L) => !S[L.id]).slice(0, newMax);
  return { due, fresh };
}

/* ---------- the ideas of a move, from the position ---------- */
const sqAttacksOfPawn = (sq, c) => { const f = sq.charCodeAt(0), r = +sq[1] + (c === "w" ? 1 : -1); return [-1, 1].map((d) => String.fromCharCode(f + d) + r).filter((s) => /^[a-h][1-8]$/.test(s)); };
const asTurn = (fen, c) => { const p = fen.split(" "); p[1] = c; p[3] = "-"; return p.join(" "); };
function moveIdeas(fen, san, later = []) {
  const g = new Chess(fen); const me = g.turn(), opp = me === "w" ? "b" : "w"; const m = g.move(san, { sloppy: true }); if (!m) return { ideas: [], label: "" };
  const G0 = Facts.grid(new Chess(fen)), G1 = Facts.grid(g); const N = Facts.NAME_AR; const out = [], lab = [];
  const push = (t, l) => { if (out.length < 4) out.push(t); if (l && lab.length < 2 && !lab.includes(l)) lab.push(l); };
  const back = me === "w" ? "1" : "8";
  if (m.san.includes("#")) push("كش مات.", "كش مات");
  if (m.captured) push(`تأسر ${N[m.captured]} على ${m.to}.`, "أسر");
  if (m.san.includes("+") && !m.san.includes("#")) push("كش: الخصم مجبر على الرد أولًا.", "كش");
  if (m.flags.includes("k") || m.flags.includes("q")) push("تبييت: الملك إلى الأمان، والرخ يدخل اللعب.", "تبييت");
  else if ("nb".includes(m.piece) && m.from[1] === back) push(`تطوير: ${N[m.piece]} يخرج من بيته إلى ${m.to}.`, "تطوير");
  if (m.piece === "p" && ["d4", "e4", "d5", "e5"].includes(m.to)) push(`بيدق في المركز على ${m.to}: يسيطر على مربعات مهمة ويفتح الطريق لقطعك.`, "المركز");
  // a new threat: an enemy unit attacked and not defended enough
  const was = new Set(Facts.hanging(G0, opp).map((h) => h.sq));
  const hit = Facts.hanging(G1, opp).find((h) => !was.has(h.sq)); if (hit) push(`تهديد: تهاجم ${N[hit.type]} الخصم على ${hit.sq}، ولا يحميه ما يكفي.`, `تهديد ${hit.sq}`);
  // pressure: enemy units newly attacked by the moved piece (a point only the king defends first)
  const newly = Object.keys(G1).filter((s) => G1[s].color === opp && G1[s].type !== "k" && Facts.attackers(G1, s, me).some((a) => a.sq === m.to) && Facts.attackers(G1, s, me).length > Facts.attackers(G0, s, me).length && s !== (hit && hit.sq));
  const kingOnly = newly.find((s) => { const D = Facts.attackers(G1, s, opp); return D.length === 1 && D[0].type === "k"; });
  if (kingOnly) push(`تصوّب على ${kingOnly}: لا يحميه إلا الملك، وهو أضعف نقطة عند الخصم.`, `ضغط على ${kingOnly}`);
  else if (newly.length && m.piece !== "p") push(`تضغط على ${N[G1[newly[0]].type]} الخصم على ${newly[0]}.`, `ضغط على ${newly[0]}`);
  // defends: a unit of yours under attack gets a new defender
  const guard = Object.keys(G1).find((s) => s !== m.to && G1[s].color === me && G1[s].type !== "k" && Facts.attackers(G1, s, opp).length && Facts.attackers(G1, s, me).some((a) => a.sq === m.to) && !Facts.attackers(G0, s, me).some((a) => a.sq === m.from));
  if (guard) push(`تحمي ${N[G1[guard].type]} على ${guard}.`, `حماية ${guard}`);
  // saves: the piece stood where it could be won
  if (Facts.hanging(G0, me).some((h) => h.sq === m.from) && !Facts.hanging(G1, me).some((h) => h.sq === m.to)) push(`تُبعد ${N[m.piece]} عن الخطر.`, "إنقاذ");
  // steps away in advance: an enemy pawn could have attacked the piece next move
  if (m.piece !== "p" && m.piece !== "k" && !m.captured) {
    const og = new Chess(asTurn(fen, opp)); const chasers = og.moves({ verbose: true }).filter((x) => x.piece === "p" && sqAttacksOfPawn(x.to, opp).includes(m.from)).map((x) => x.san);
    const og2 = new Chess(asTurn(g.fen(), opp)); const still = og2.moves({ verbose: true }).some((x) => x.piece === "p" && sqAttacksOfPawn(x.to, opp).includes(m.to));
    if (chasers.length && !still) push(`تبتعد مسبقًا: كان الخصم يستطيع مطاردة ${N[m.piece]} بـ[${chasers.slice(0, 2).join("] أو [")}] ويكسب وقتًا.`, "ابتعاد مسبق");
  }
  if (m.piece === "p") {
    // prevents: squares this pawn now covers where enemy pieces could have gone
    const cover = sqAttacksOfPawn(m.to, me); const og = new Chess(asTurn(fen, opp));
    const pawnCovered0 = (s) => Facts.attackers(G0, s, me).some((a) => a.type === "p");
    const stopped = og.moves({ verbose: true }).filter((x) => x.piece !== "p" && x.piece !== "k" && cover.includes(x.to) && !pawnCovered0(x.to)).map((x) => x.san);
    if (stopped.length) push(`تمنع [${[...new Set(stopped)].slice(0, 2).join("] و[")}]: البيدق على ${m.to} يراقب ${[...new Set(stopped.map((s) => s.replace(/[+#]/g, "").slice(-2)))].join(" و")}.`, `تمنع ${stopped[0].replace(/[+#]/g, "")}`);
    // prepares a pawn push of yours that this pawn will support
    const mg = new Chess(asTurn(g.fen(), me));
    const laterSans = new Set(later.map((x) => x.san.replace(/[+#]/g, "")));
    const prep = mg.moves({ verbose: true }).find((x) => x.piece === "p" && x.from !== m.to && cover.includes(x.to) && ((me === "w" ? ["d4", "e4"] : ["d5", "e5"]).includes(x.to) || laterSans.has(x.san.replace(/[+#]/g, ""))));
    if (prep) push(`تحضّر [${prep.san}]: البيدق على ${m.to} سيحمي ${prep.to}.`, `تحضير ${prep.to}`);
    // luft
    const k = Object.keys(G1).find((s) => G1[s].type === "k" && G1[s].color === me);
    if (k && k[1] === back && "gh".includes(k[0]) && ["h3", "h6"].includes(m.to)) push("تصنع مخرجًا للملك: لا كش على الصف الأخير لاحقًا.", "مخرج للملك");
  }
  // vacates a square for a later move of yours, or the first step of a manoeuvre
  const vi = later.findIndex((x) => x.to === m.from && x.from !== m.to);
  const vac = vi >= 0 && later.slice(0, vi + 1).every((x) => !x.fen || !new Chess(x.fen).get(m.from)) ? later[vi] : null;
  if (vac) push(/^O-O/.test(vac.san) ? "تُخلي الطريق للتبييت." : `تُخلي ${m.from} من أجل [${vac.san}] لاحقًا.`, /^O-O/.test(vac.san) ? "طريق التبييت" : `تُخلي ${m.from}`);
  const route = []; let at = m.to; for (const x of later) if (x.from === at) { if (x.cap) break; route.push(x.to); at = x.to; } // a capture ends a manoeuvre
  if (route.length && m.piece !== "p") push(`مناورة: ${N[m.piece]} في طريقه ${[m.to, ...route].join(" ← ")}.`, `مناورة إلى ${route[route.length - 1]}`);
  if (!out.length && m.piece === "r" && m.from[0] !== m.to[0]) {
    const own = Object.keys(G1).some((x) => x[0] === m.to[0] && G1[x].type === "p" && G1[x].color === me);
    const tgt = Object.keys(G1).filter((x) => x[0] === m.to[0] && G1[x].type === "p" && G1[x].color === opp);
    if (!own) push(tgt.length ? `الرخ إلى العمود ${m.to[0]} نصف المفتوح: يضغط على البيدق ${tgt[0]}.` : `الرخ إلى العمود ${m.to[0]} المفتوح.`, `رخ إلى العمود ${m.to[0]}`);
    else push(`الرخ إلى العمود ${m.to[0]}: يقف خلف البيدق ويدعم تقدّمه أو فتح العمود لاحقًا.`, `رخ إلى ${m.to}`);
  }
  if (!out.length && m.piece === "n") {
    const ng = new Chess(asTurn(g.fen(), me)); const fwd = (x) => (me === "w" ? +x[1] > +m.to[1] : +x[1] < +m.to[1]);
    const cen = (x) => Math.abs(x.charCodeAt(0) - 100.5) + Math.abs(+x[1] - 4.5); // closer to the centre first; not back where it came from
    const nx = [...new Set(ng.moves({ verbose: true }).filter((x) => x.from === m.to && !x.captured && fwd(x.to) && x.to !== m.from).map((x) => x.to))].sort((a, b) => cen(a) - cen(b));
    if (nx.length) push(`من ${m.to} يصل الحصان لاحقًا إلى ${nx.slice(0, 3).join(" أو ")}.`, `الحصان نحو ${nx[0]}`);
  }
  if (!out.length) { const t = Tech.tagsOf(fen, m.from + m.to + (m.promotion || "")); const k2 = ["openfile", "outpost", "break", "worst"].find((x) => t.includes(x)); if (k2 && typeof PLAN_AR !== "undefined") push(PLAN_AR[k2] + ".", PLAN_AR[k2]); }
  if (!out.length) push("تحسين هادئ: الأساتذة وStockfish يرونها النقلة المناسبة هنا.", "تحسين");
  return { ideas: out, label: lab.join(" + ") };
}
function oppIdeas(fen, san) {
  const g = new Chess(fen); const opp = g.turn(), me = opp === "w" ? "b" : "w"; const m = g.move(san, { sloppy: true }); if (!m) return [];
  const G1 = Facts.grid(g); const N = Facts.NAME_AR; const out = [];
  if (m.captured) out.push(`يأسر ${YOUR_AR[m.captured] || N[m.captured]} على ${m.to}.`);
  if (m.san.includes("+")) out.push("كش: عالجه أولًا.");
  if (m.flags.includes("k") || m.flags.includes("q")) out.push("يبيّت.");
  const att = Object.keys(G1).filter((s) => G1[s].color === me && G1[s].type !== "k" && Facts.attackers(G1, s, opp).some((a) => a.sq === m.to));
  if (att.length) out.push(`يهاجم ${att.slice(0, 2).map((s) => `${N[G1[s].type]} ${s}`).join(" و")}.`);
  if (m.piece === "p" && ["d4", "e4", "d5", "e5"].includes(m.to) && !m.captured) out.push("بيدق في المركز.");
  if (!out.length && "nb".includes(m.piece)) out.push(`يطوّر ${N[m.piece]}.`);
  return out;
}
/* The ideas of every move of a line (your later moves are passed so manoeuvres and vacated squares are seen). */
function lineNotes(L, moves) {
  const me = lineSide(L); const g = new Chess(); const steps = [];
  for (const s of moves) { const fen = g.fen(); const m = g.move(s, { sloppy: true }); if (!m) break; steps.push({ fen, san: m.san, from: m.from, to: m.to, mine: m.color === me, cap: !!m.captured }); }
  return steps.map((st, i) => {
    if (!st.mine) return { ...st, ideas: oppIdeas(st.fen, st.san) };
    const later = steps.slice(i + 1).filter((x) => x.mine); const r = moveIdeas(st.fen, st.san, later);
    return { ...st, ideas: r.ideas, label: r.label };
  });
}

/* ---------- the plan at the end of what you recalled ---------- */
async function linePlan(L, upto) {
  const me = lineSide(L); const g = new Chess(); for (const s of upto) g.move(s, { sloppy: true }); const fen = g.fen();
  const next = [...L.mv, ...L.cont].slice(upto.length, upto.length + 12);
  const C = Tech.compass(fen, me); const mw = Tech.wingOfMoves(fen, next, me);
  let pv = null, cp = null;
  if (upto.length === L.mv.length) { pv = L.end.pv; cp = L.end.cp; }
  else { try { const a = await Engine.analyse(fen, { depth: 14, movetime: 1500 }); pv = pvToSan(fen, a.lines[0].pv, 8); cp = a.cp; } catch {} }
  const ew = pv ? Tech.wingOfMoves(fen, pv, me) : null; const st = Tech.structure(fen);
  return { fen, me, next, C, mw, ew, pv, cp, st };
}
function linePlanHtml(L, P) {
  const myNext = []; { const g = new Chess(P.fen); for (const s of P.next) { const mine = g.turn() === P.me; const fen = g.fen(); g.move(s, { sloppy: true }); if (mine) myNext.push({ san: s, label: moveIdeas(fen, s).label }); } }
  const agree = [P.C && P.C.wing, P.mw && P.mw.wing, P.ew && P.ew.wing].filter(Boolean);
  const same = agree.length >= 2 && agree.every((w) => w === agree[0]);
  const evalTxt = P.cp == null ? "" : (() => { const v = (P.me === "w" ? 1 : -1) * P.cp; return Math.abs(v) < 40 ? "متعادل تقريبًا" : v > 0 ? `أفضل لك قليلًا (${(v / 100).toFixed(1)})` : `أفضل للخصم قليلًا (${(-v / 100).toFixed(1)})`; })();
  return `<div class="lplan"><h3>الخطة من هنا</h3>
    ${P.st && typeof STRUCTS !== "undefined" ? `<p><b>البنية:</b> ${esc(STRUCTS[P.st.id].name)}.</p>` : ""}
    ${P.C ? `<p><b>أين أهاجم؟ ${esc(P.C.name)}.</b></p><ul class="facts">${P.C.reasons.slice(0, 3).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>${P.C.levers.length ? `<p class="note">دفعات بيدق في هذه الجهة: ${P.C.levers.map(mv).join("، ")}.</p>` : ""}` : ""}
    ${P.next.length ? `<p><b>ماذا لعب الأساتذة بعد هذا الموقف:</b> <bdi class="mv">${esc(numberedLine(P.fen, P.next.slice(0, 10)))}</bdi></p>
      ${myNext.length ? `<p class="note">نقلاتك فيها: ${myNext.slice(0, 5).map((x) => `${mv(x.san)} (${esc(x.label)})`).join("، ")}${P.mw ? `. أغلبها في ${esc(P.mw.name)}` : ""}.</p>` : ""}` : `<p class="note">لا مباريات أساتذة كافية بعد هذا الموقف (أقل من 50).</p>`}
    ${P.pv ? `<p><b>Stockfish:</b> ${esc(evalTxt)}. خطه: <bdi class="mv">${esc(numberedLine(P.fen, P.pv.slice(0, 6)))}</bdi>${P.ew ? ` (نقلاتك فيه نحو ${esc(P.ew.name)})` : ""}.</p>` : ""}
    <p class="note">${same ? `البوصلة والأساتذة وStockfish متفقون: ${esc(Tech.WING_AR[agree[0]])}.` : agree.length >= 2 ? `ليسوا متفقين تمامًا (البوصلة: ${esc(P.C ? P.C.name : "–")}، الأساتذة: ${esc(P.mw ? P.mw.name : "–")}، Stockfish: ${esc(P.ew ? P.ew.name : "–")}). البوصلة قاعدة عامة؛ ما لعبه الأساتذة هنا هو الأدق لهذا الموقف.` : ""}</p></div>`;
}
const MEMORY_TIPS = `<details class="method"><summary><b>كيف تحفظ مثل الآلة، وتفهم مثل الإنسان</b></summary><ol class="facts">
  <li><b>قطع لا نقلات:</b> لا تحفظ «e4، Nf3، Bc4». احفظ ثلاث أفكار: المركز، تطوير مع ضغط على e5، الفيل نحو f7. الوسم الصغير بجانب كل نقلة هو القطعة.</li>
  <li><b>قل الفكرة قبل النقلة:</b> في الاستذكار، قل لنفسك الفكرة («أحضّر d4») ثم العب. الفكرة تبقى في الذاكرة أطول من الرمز.</li>
  <li><b>التكرار في وقته:</b> الخط يعود بعد يوم، ثم 3 أيام، ثم أسبوع وأكثر. الخطأ يعيده غدًا. خمس دقائق يوميًا أقوى من ساعة في الأسبوع.</li>
  <li><b>الخطة أهم من آخر نقلة:</b> إذا خرج الخصم عن الخط تبقى الخطة: أين أهاجم، وأي دفعة بيدق، وأين تذهب القطع.</li>
  <li><b>الترقية:</b> كل خط يبدأ بأول 5 نقلات، ثم الخط كاملًا، ثم ما يلعبه الأساتذة بعده. ينتقل بعد استذكارين بلا خطأ في يومين مختلفين.</li></ol></details>`;

/* ---------- learn and recall one line ---------- */
function LineTrainer(root, L, { mode = "learn", onDone = null, onBack = null, title = null } = {}) {
  const st = lineState(L.id, true); const lv = st.lv; const moves = lineMoves(L, lv); const me = lineSide(L);
  const notes = lineNotes(L, moves); let token = 0; window.LN_DEBUG = { L }; /* tests read the line on screen */ const alive = (t) => t === token && document.body.contains(root) && $("#ln-board", root);
  root.innerHTML = `<div class="whead"><button class="btn quiet" id="ln-back">${onBack ? "→ رجوع" : "→ خطوطي"}</button><div class="wtitle"><b>${esc(L.name || "خط")}</b><span class="note">${esc(LINE_GROUP_AR[L.g])} · المستوى ${lv}: ${esc(LV_AR[lv])}${title ? ` · ${esc(title)}` : ""}</span></div></div>
    <div class="watch"><div class="wboard"><div class="boardcap"><span class="turn" id="ln-turn"></span><span class="note" id="ln-status"></span></div><div class="board" id="ln-board"></div><div class="row" id="ln-ctl"></div><div class="moves wmoves" id="ln-moves"></div></div>
      <div class="wside"><div class="panel" id="ln-card" aria-live="polite"></div><div class="panel" id="ln-plan" hidden></div>${MEMORY_TIPS}</div></div>`;
  const board = Board($("#ln-board", root), { orient: me, interactive: false });
  $("#ln-back", root).onclick = () => { token++; onBack ? onBack() : LinesHome(root); };
  const setStatus = (t) => { $("#ln-status", root).textContent = t; };
  const fenAt = (k) => { const g = new Chess(); for (const s of moves.slice(0, k)) g.move(s, { sloppy: true }); return g.fen(); };
  const movesHtml = (k, reveal) => { const g = new Chess(); let h = ""; moves.forEach((s, i) => { const p = g.fen().split(" "); if (p[1] === "w" || i === 0) h += `<span class="mnum">${p[5]}${p[1] === "w" ? "." : "..."}</span>`; g.move(s, { sloppy: true }); const n = notes[i]; const shown = reveal || i < k; h += `<span class="mvbtn ${i === k - 1 ? "on" : ""} ${n.mine ? "mine" : ""}">${shown ? esc(s) : "؟"}${shown && n.mine && n.label ? `<small class="mlab">${esc(n.label)}</small>` : ""}</span>`; }); return h; };
  const turnTxt = (fen) => { const t = fen.split(" ")[1]; $("#ln-turn", root).innerHTML = `<i class="${t}"></i>${t === me ? "دورك" : "دور الخصم"}`; };
  const noteCard = (i) => { const n = notes[i]; const sh = L.sh[i] ?? (L.csh[i - L.mv.length] ?? null);
    return `<p><b>${n.mine ? "نقلتك" : "الخصم"}: <bdi class="mv">${esc(moveLabel(n.fen, n.san))}</bdi></b>${n.mine && n.label ? ` <span class="tag best">${esc(n.label)}</span>` : ""}</p>
      ${n.ideas.length ? `<ul class="facts">${n.ideas.map((x) => `<li>${fmtNote(x)}</li>`).join("")}</ul>` : ""}
      ${sh ? `<p class="note">${n.mine ? "لعبها الأساتذة هنا" : "هذا الرد"} في ${Math.round(100 * sh)}% من مباريات الأساتذة${i >= L.mv.length ? " (من خطة الأساتذة بعد الخط)" : ""}.</p>` : ""}`; };

  async function showPlan(quiz) {
    const box = $("#ln-plan", root); box.hidden = false; box.innerHTML = `<p class="note">أحسب الخطة...</p>`;
    const t = token; const P = await linePlan(L, moves); if (!alive(t)) return;
    const reveal = () => { box.innerHTML = linePlanHtml(L, P) + `<div class="row"><button class="btn" id="ln-fin">${onDone ? "التالي" : "إلى خطوطي"}</button></div>`;
      board.update({ fen: P.fen, last: null, arrows: P.C ? P.C.levers.map((s) => { const m = new Chess(asTurn(P.fen, me)).move(s, { sloppy: true }); return m ? { from: m.from, to: m.to, color: "plan" } : null; }).filter(Boolean) : [] });
      $("#ln-fin", root).onclick = () => (onDone ? onDone(result) : LinesHome(root)); };
    const truth = (P.mw && P.mw.wing) || (P.C && P.C.wing);
    if (!quiz || !truth) return reveal();
    box.innerHTML = `<h3>قبل أن أريك الخطة: أين تلعب من هنا؟</h3><div class="row">${["q", "c", "k"].map((w) => `<button class="chip-q" data-w="${w}">${esc(Tech.WING_AR[w])}</button>`).join("")}</div><div id="ln-q"></div>`;
    for (const b of $$("[data-w]", box)) b.onclick = () => { const ok = b.dataset.w === truth; result.planOk = ok; st.planQ = (st.planQ || []).concat(ok ? 1 : 0).slice(-10); saveJourney();
      for (const x of $$("[data-w]", box)) x.disabled = true; b.classList.add(ok ? "on" : "bad");
      $("#ln-q", box).innerHTML = `<div class="callout ${ok ? "good" : "bad"}">${ok ? "صحيح" : `الأساتذة لعبوا في ${esc(Tech.WING_AR[truth])}`}.</div><div class="row"><button class="btn" id="ln-rev">أرني الخطة</button></div>`;
      $("#ln-rev", box).onclick = reveal; };
  }
  const result = { id: L.id, errors: 0, upgraded: false, lv, mode };

  function learn() {
    let k = 0; setStatus("تعلّم الخط: فكرة كل نقلة.");
    const show = () => { const fen = fenAt(k); const n = notes[k - 1];
      board.update({ fen, last: n ? n.from + n.to : null, arrows: n ? [{ from: n.from, to: n.to, color: n.mine ? "good" : "alt" }] : [] }); turnTxt(fen);
      $("#ln-moves", root).innerHTML = movesHtml(k, false);
      $("#ln-card", root).innerHTML = k ? noteCard(k - 1) : `<p><b>${esc(L.name)}</b></p><p class="note">${moves.length} نقلة (${moves.filter((_, i) => notes[i].mine).length} لك). اضغط «التالية» لترى كل نقلة وفكرتها، ثم العب الخط من ذاكرتك.</p>`;
      $("#ln-ctl", root).innerHTML = `<button class="ctl" id="ln-prev" ${k ? "" : "disabled"}>→ السابقة</button><button class="ctl" id="ln-next" ${k < moves.length ? "" : "disabled"}>التالية ←</button>${k === moves.length ? `<button class="btn" id="ln-go">العبه من ذاكرتك</button>` : ""}`;
      $("#ln-prev", root).onclick = () => { k--; show(); }; $("#ln-next", root).onclick = () => { k++; show(); };
      const go2 = $("#ln-go", root); if (go2) go2.onclick = () => recall(); };
    show();
  }
  function recall() {
    const t = ++token; let k = 0; const t0 = now(); result.errors = 0; result.mode = "recall"; $("#ln-plan", root).hidden = true;
    $("#ln-ctl", root).innerHTML = ""; $("#ln-card", root).innerHTML = `<p><b>العب نقلاتك من ذاكرتك.</b> ردود الخصم تأتي وحدها. قل الفكرة لنفسك قبل كل نقلة.</p>`;
    const step = () => {
      if (!alive(t)) return;
      const fen = fenAt(k); turnTxt(fen); $("#ln-moves", root).innerHTML = movesHtml(k, false);
      if (k >= moves.length) return finish();
      const n = notes[k];
      if (!n.mine) { board.update({ fen, interactive: false }); setTimeout(() => { if (!alive(t)) return; k++; board.update({ fen: fenAt(k), last: n.from + n.to, arrows: [] }); step(); }, k ? 450 : 250); return; }
      setStatus(`نقلتك ${notes.slice(0, k + 1).filter((x) => x.mine).length} من ${notes.filter((x) => x.mine).length}`);
      let missed = false;
      board.update({ fen, interactive: true, arrows: [], onMove: async (m) => {
        const norm = (s) => s.replace(/[+#]/g, "");
        if (norm(m.san) === norm(n.san)) {
          board.update({ interactive: false, fen: m.fenAfter, last: m.uci });
          if (!missed) $("#ln-card", root).innerHTML = `<p class="callout good">✓ <bdi class="mv">${esc(m.san)}</bdi>${n.label ? ` · ${esc(n.label)}` : ""}</p>`;
          k++; return step();
        }
        if (missed) { board.update({ fen }); return; } // play the line's move to go on
        missed = true; result.errors++; (st.errs = st.errs || []).push(k); st.errs = st.errs.slice(-20);
        board.update({ fen, arrows: [{ from: n.from, to: n.to, color: "good" }] });
        $("#ln-card", root).innerHTML = `<div class="callout bad"><b>ليست نقلة خطك: <bdi class="mv">${esc(m.san)}</bdi></b><p>نقلة خطك: <bdi class="mv">${esc(moveLabel(fen, n.san))}</bdi>${n.label ? ` (${esc(n.label)})` : ""}</p></div>
          <ul class="facts">${n.ideas.map((x) => `<li>${fmtNote(x)}</li>`).join("")}</ul><p class="note" id="ln-sf">Stockfish يقارن...</p><p class="note">العبها الآن على الرقعة لتكمل.</p>`;
        try { const a = await Engine.analyse(fen, { depth: 12, movetime: 800, multipv: 1 }); const u = n.from + n.to;
          const ev = async (x) => (x === a.best ? a.lines[0].cpWhite : (await Engine.analyse(fen, { depth: 12, movetime: 600, searchmoves: [x] })).lines[0].cpWhite);
          const mine = await ev(m.uci), line = await ev(u); if (!alive(t)) return; const d = (me === "w" ? 1 : -1) * (line - mine);
          const el = $("#ln-sf", root); if (el) el.textContent = d <= 30 ? "نقلتك ليست خطأ عند Stockfish، لكنها ليست خطك: الخط الثابت يعني أنك تعرف الخطة بعده." : `نقلتك أضعف من نقلة الخط عند Stockfish (بفارق ${(d / 100).toFixed(1)} بيدق تقريبًا).`;
        } catch { const el = $("#ln-sf", root); if (el) el.textContent = ""; }
      } });
    };
    const finish = () => {
      board.update({ interactive: false }); const secs = Math.round((now() - t0) / 1000); const own = notes.filter((x) => x.mine).length;
      const q = result.errors === 0 ? (secs / own <= 6 ? 5 : 4) : result.errors === 1 ? 2 : 1; sm2(st, q); st.last = now();
      const day = new Date().toISOString().slice(0, 10);
      if (!result.errors) { if (st.pDay !== day) { st.perfect = (st.perfect || 0) + 1; st.pDay = day; } } else st.perfect = 0;
      if (st.perfect >= 2 && st.lv < lineMaxLv(L)) { st.lv++; st.perfect = 0; result.upgraded = true; st.due = now() + DAY; }
      saveJourney(); $("#ln-moves", root).innerHTML = movesHtml(moves.length, true);
      $("#ln-card", root).innerHTML = `<div class="callout ${result.errors ? "bad" : "good"}"><b>${result.errors ? `${arCount(result.errors, "خطأ واحد", "خطآن", "أخطاء", "خطأ")}` : "بلا خطأ"}</b> · ${secs} ثانية.
        <p>${result.upgraded ? `ترقية: الخط الآن في المستوى ${st.lv} (${esc(LV_AR[st.lv])}).` : result.errors ? "يعود غدًا. الأماكن التي أخطأت فيها محفوظة." : st.lv < lineMaxLv(L) ? `استذكار بلا خطأ (${st.perfect} من 2 في يومين مختلفين للترقية).` : "الخط في أعلى مستوى."} المراجعة القادمة بعد ${Math.max(1, Math.round((st.due - now()) / DAY))} يوم.</p></div>
        ${result.errors ? `<div class="row"><button class="btn quiet" id="ln-again">أعده الآن</button></div>` : ""}`;
      const ag = $("#ln-again", root); if (ag) ag.onclick = () => { ag.remove(); result.retried = true; recall(); };
      showPlan(lv >= 2);
    };
    step();
  }
  if (mode === "learn") learn(); else recall();
  return result;
}

/* ---------- a session: due reviews, then new lines ---------- */
async function LinesSession(root, { newMax = 2, dueMax = 8, onDone = null, onBack = null } = {}) {
  await loadLines(); const { due, fresh } = linesQueue({ newMax, dueMax }); const list = [...due.map((L) => ["recall", L]), ...fresh.map((L) => ["learn", L])];
  const res = []; let k = 0;
  const next = () => {
    if (k >= list.length) { const sum = { n: res.length, perfect: res.filter((r) => !r.errors).length, upgraded: res.filter((r) => r.upgraded).length, fresh: fresh.length }; return onDone ? onDone(sum) : LinesHome(root); }
    const [mode, L] = list[k++];
    LineTrainer(root, L, { mode, title: `${k} من ${list.length}${mode === "learn" ? " · جديد" : " · مراجعة"}`, onBack: onBack || (() => LinesHome(root)), onDone: (r) => { res.push(r); next(); } });
  };
  if (!list.length) { root.innerHTML = `<div class="panel"><h3>خطوطي</h3><p>لا مراجعة مستحقة ولا خط جديد اليوم.</p><div class="row"><button class="btn" id="ln-b">رجوع</button></div></div>`; $("#ln-b", root).onclick = onBack || (() => LinesHome(root)); return; }
  next();
}

/* ---------- the library page ---------- */
async function LinesHome(root) {
  root.innerHTML = `<p class="note">أحمّل الخطوط...</p>`; await loadLines(); const S = J.state.lines || {};
  const { due } = linesQueue({ dueMax: 999 }); const learned = LINES.filter((L) => S[L.id]);
  const cover = (g) => { const all = LINES.filter((L) => L.g === g); const tot = all.reduce((s, L) => s + L.w, 0); const kn = all.filter((L) => S[L.id]).reduce((s, L) => s + L.w, 0); return tot ? Math.round(100 * kn / tot) : 0; };
  const fams = {}; for (const L of LINES) { const k = L.g + "|" + (L.fam || "?"); (fams[k] = fams[k] || { g: L.g, fam: L.fam || "?", lines: [], w: 0 }).lines.push(L); fams[k].w += L.w; }
  const famList = Object.values(fams).sort((a, b) => b.w - a.w);
  root.innerHTML = `<div class="whead"><button class="btn quiet" id="lh-back">→ الرحلة</button><div class="wtitle"><b>خطوطي: افتتاحي وخطتي</b><span class="note">${LINES.length} خطًّا من ذخيرتك · تعلّمت ${learned.length} · مستحق للمراجعة ${due.length}</span></div></div>
    <div class="panel"><p>كل خط: النقلات وفكرة كل نقلة، ثم تلعبه من ذاكرتك، ثم خطته: أين تهاجم وماذا يلعب الأساتذة بعده. الخطوط مرتبة حسب احتمال أن تقابلها.</p>
      <p class="note">ما تغطيه خطوطك من مبارياتك المتوقعة: بالأبيض ${cover("w")}% · ضد 1.e4 ${cover("e5")}% · ضد 1.d4 ${cover("qgd")}%.</p>
      <div class="row"><button class="btn big" id="lh-go">ابدأ: ${due.length ? `${Math.min(due.length, 8)} مراجعة` : "لا مراجعة"} + ${Math.min(2, LINES.length - learned.length)} جديد</button></div>${MEMORY_TIPS}</div>
    ${famList.slice(0, 40).map((F) => `<details class="panel lfam"><summary><b>${esc(F.fam)}</b> <span class="note">${esc(LINE_GROUP_AR[F.g])} · ${F.lines.length} خط · تعلّمت ${F.lines.filter((L) => S[L.id]).length}</span></summary>
      <div class="tbl"><table><tbody>${F.lines.map((L) => { const s = S[L.id]; return `<tr><td><bdi class="mv">${esc(lineShort(L, 8))}</bdi><div class="note">${esc(L.name)}</div></td><td class="num">${s ? `م${s.lv}` : "–"}</td><td class="num">${s ? (s.due <= now() ? "الآن" : new Date(s.due).toISOString().slice(5, 10)) : ""}</td><td><button class="btn quiet" data-l="${L.id}" data-m="${s ? "recall" : "learn"}">${s ? "استذكر" : "تعلّم"}</button>${s ? `<button class="btn quiet" data-l="${L.id}" data-m="learn">راجع الأفكار</button>` : ""}</td></tr>`; }).join("")}</tbody></table></div></details>`).join("")}`;
  $("#lh-back", root).onclick = () => go("journey");
  $("#lh-go", root).onclick = () => LinesSession(root);
  for (const b of $$("[data-l]", root)) b.onclick = () => LineTrainer(root, LINES.find((L) => L.id === b.dataset.l), { mode: b.dataset.m });
}
