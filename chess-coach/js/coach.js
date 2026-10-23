"use strict";
/* Training tools, all computed in the page (Stockfish + position facts, no Claude call):
   - techniques to master per chapter (data/curriculum/techniques.json), each with its own endless drill and a mastery score;
   - the move explorer: tap a piece and see every move it can make, scored by Stockfish, with the reason and an advice;
   - "all moves explained": Stockfish's top moves in a position, each with what it does and what it risks;
   - the plan box: what to do now, from the position (development, king, loose pieces, worst piece, targets, endgame). */
let TECH = null;
async function techCatalog() { if (!TECH) TECH = await loadJSON("data/curriculum/techniques.json"); return TECH; }
function techState(id) { const t = (J.state.tech = J.state.tech || {}); return t[id] || (t[id] = { n: 0, last: [] }); }
const techMastery = (s) => { const l = s.last.slice(-10); return { ok: l.filter(Boolean).length, of: l.length, mastered: s.n >= 10 && l.length >= 10 && l.filter(Boolean).length >= 8 }; };

/* ---------- the plan box ---------- */
function planFor(fen, ply, { noThreats = false } = {}) {
  const g = new Chess(fen); const me = g.turn(), opp = me === "w" ? "b" : "w"; const f = Facts.positionFacts(fen, ply ?? 30); const N = Facts.NAME_AR;
  const G = Facts.grid(g); const mine = f[me], his = f[opp]; const out = [];
  if (f.inCheck) out.push("أنت في كش: عالجه أولًا (حرّك الملك، أو سد الخط، أو خذ القطعة المهاجِمة).");
  if (mine.hanging.length && !noThreats) out.push(`أولًا الأمان: ${mine.hanging.slice(0, 2).map((h) => `${N[h.type]} على ${h.sq}`).join(" و")} ${mine.hanging.length > 1 ? "معرّضان" : "معرّض"} للكسب. أنقذ، أو احمِ، أو خذ المهاجم.`);
  if (his.hanging.length && !noThreats) out.push(`فرصة: ${N[his.hanging[0].type]} الخصم على ${his.hanging[0].sq} لا يحميه ما يكفي. هل تستطيع أخذه بأمان؟`);
  if (f.checks.length) out.push(`عندك ${arCount(f.checks.length, "كش واحد", "كشّان", "كشات", "كشًا")}: افحصها أولًا (هل يكسب أحدها شيئًا؟).`);
  const pieces = Object.values(G).filter((p) => p.color === opp).length;
  const myMat = Object.values(G).filter((p) => p.color === me && p.type !== "k").map((p) => p.type).sort().join("");
  if (pieces === 1 && (myMat === "q" || myMat.includes("q"))) out.push("الخطة: ضع الوزير على بعد قفزة حصان من الملك المعادي، اتبعه لتصغير الصندوق، ثم أحضر ملكك. احذر الـ stalemate.");
  else if (pieces === 1 && myMat.includes("r")) out.push("الخطة: الرخ يقطع الملك المعادي ويبقى بعيدًا عنه، ملكك يقترب حتى المعارضة، ثم كش الرخ على الحافة.");
  else if (f.phase === "opening") {
    if (mine.dev.undeveloped.length) out.push(`طوّر: ${mine.dev.undeveloped.map((s) => `${N["bg".includes(s[0]) ? "n" : "b"]} ${s}`).join("، ")} ما زالت في البيت. الحصانان غالبًا قبل الفيلين.`);
    if (!mine.center.pawns) out.push("لا بيدق لك في المركز: d4 أو e4 (d5 أو e5) إن كان آمنًا.");
    if (!mine.dev.castled && mine.dev.kingCenter) out.push("ملكك في الوسط: بيّت قريبًا.");
  } else if (f.phase === "middlegame") {
    // the piece with the fewest moves is the one to improve
    let worst = null; for (const [sq, p] of Object.entries(G)) { if (p.color !== me || "kp".includes(p.type)) continue; const n = g.moves({ square: sq }).length; if (!worst || n < worst.n) worst = { sq, p, n }; }
    if (worst && worst.n <= 3) out.push(`حسّن أسوأ قطعة: ${N[worst.p.type]} على ${worst.sq} ${worst.n ? `له ${arCount(worst.n, "نقلة واحدة", "نقلتان", "نقلات", "نقلة")} فقط` : "لا يتحرك"}. أين تعمل أفضل؟`);
    if (his.king && (his.king.attackers >= 2 || his.king.openFiles.length)) out.push(`ملك الخصم على ${his.king.sq}${his.king.openFiles.length ? ` وأمامه عمود مفتوح (${his.king.openFiles.join("، ")})` : ""}: وجّه قطعك نحوه.`);
    if (mine.king && mine.king.attackers >= 2) out.push(`انتبه لملكك: ${mine.king.attackers} قطع للخصم تهاجم المربعات حوله.`);
    if (his.pawns.isolated.length) out.push(`هدف: بيدق الخصم المعزول على ${his.pawns.isolated[0]}. هاجمه بقطعك.`);
    if (!out.length || out.length < 2) out.push("لا شيء عاجل: حسّن قطعة، أو ضع رخًا على عمود مفتوح، أو هاجم نقطة ضعف.");
  } else {
    out.push("النهاية: الملك قطعة مقاتلة. أحضره نحو المركز أو نحو البيادق.");
    if (mine.pawns.passed.length) out.push(`بيدقك الحر على ${mine.pawns.passed[0]}: ادفعه ورافقه بالملك أو الرخ.`);
    if (his.pawns.passed.length) out.push(`بيدق الخصم الحر على ${his.pawns.passed[0]}: أوقفه قبل أي شيء.`);
  }
  return out.slice(0, 4);
}
const planHtml = (fen, ply, opt) => `<div class="fh"><b>خطتك الآن</b><span class="note">من الموقف</span></div><ul class="facts">${planFor(fen, ply, opt).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`;

/* ---------- explaining moves ---------- */
const TAG_AR = {
  knight: "تقنية: الحصان إلى مربعه الطبيعي، يسيطر على المركز.", bishop: "تقنية: الفيل إلى قطر مفتوح.", centre: "تقنية: بيدق في المركز.", castle: "تقنية: التبييت يؤمّن الملك ويُدخل الرخ.",
  save: "تقنية: تنقذ قطعة كانت مهدَّدة.", cover: "تقنية: تحمي قطعة مهدَّدة دون أن تحرّكها.", take: "تقنية: تأخذ قطعة لا يحميها ما يكفي.", check: "كش: الخصم مجبر على الرد.",
  backrank: "تقنية: كش على الصف الأخير.", qknight: "تقنية: الوزير على بعد قفزة حصان من الملك.", rcut: "تقنية: الرخ يقطع الملك.",
};
/* What a move risks: your pieces it leaves loose, the opponent's strongest reply, stalemate. */
function moveRisks(fen, san, reply) {
  const g = new Chess(fen); const me = g.turn(); const m = g.move(san, { sloppy: true }); if (!m) return [];
  const N = Facts.NAME_AR; const out = [];
  if (g.in_stalemate()) return ["stalemate: الخصم بلا نقلة وملكه ليس في كش. تعادل."];
  const before = new Set(Facts.hanging(Facts.grid(new Chess(fen)), me).map((h) => h.sq));
  for (const h of Facts.hanging(Facts.grid(g), me)) {
    if (h.sq === m.to) out.push(`${N[h.type]} يذهب إلى مربع يكسبه الخصم.`);
    else if (!before.has(h.sq)) out.push(`تترك ${N[h.type]} على ${h.sq} بلا حماية كافية${m.from && Facts.attackers(Facts.grid(new Chess(fen)), h.sq, me).some((a) => a.sq === m.from) ? " (القطعة التي تحركت كانت تحميه)" : ""}.`);
  }
  // the chapter rules this move breaks ("don't" advice), only for moves Stockfish also dislikes
  const opening = Facts.phaseOf(Facts.grid(g), 10) === "opening";
  if (m.piece === "n" && "ah".includes(m.to[0])) out.push("الحصان على الحافة يسيطر على نصف مربعاته فقط.");
  if (opening && m.piece === "q" && Facts.development(Facts.grid(g), me).developed < 3) out.push("الوزير يخرج قبل التطوير: قطع الخصم ستطارده وتكسب وقتًا.");
  if (opening && m.piece === "k" && !m.flags.includes("k") && !m.flags.includes("q")) out.push("الملك يتحرك بلا تبييت: يفقد حق التبييت ويبقى في الوسط.");
  if (opening && m.piece === "p" && m.from === "f" + (me === "w" ? "2" : "7")) out.push("بيدق f يتحرك: القطر نحو ملكك ينفتح (e1-h4 أو e8-h5).");
  if (m.piece === "p" && "ah".includes(m.from[0]) && opening) out.push("نقلة بيدق طرف في الافتتاح: لا تطوّر شيئًا.");
  if (reply && reply.length) out.push(`أقوى رد للخصم: [${reply.slice(0, 3).join(" ")}].`);
  return out;
}
/* One move, explained: {san, cls, es, good[], risks[], advice}. line: Stockfish's line starting with this move. */
function explainMove(fen, uci, line, esBest, es, mateInfo) {
  const san = sanOf(fen, uci); const cl = Prob.classify(esBest, es); const tags = Tech.tagsOf(fen, uci);
  const good = bestMoveWhy(fen, san, uci, null).concat(tags.filter((t) => TAG_AR[t] && !["check"].includes(t)).map((t) => TAG_AR[t]));
  const reply = pvToSan(fen, line || [], 4).slice(1);
  const risks = cl.drop > 5 ? moveRisks(fen, san, reply) : (tags.includes("stalemate") ? ["stalemate: تعادل."] : []);
  const cls = mateInfo || cl.cls;
  const advice = cls === "excellent" ? "نقلة ممتازة: العبها بثقة." : cls === "good" ? "جيدة: قريبة من الأفضل." : cls === "inaccuracy" ? "مقبولة، لكن هناك أفضل منها." : cls === "mistake" ? "تجنّبها: تخسر جزءًا مهمًا من فرصك." : "لا تلعبها: تخسر كثيرًا.";
  return { san, uci, cls, es: Math.round(es), drop: cl.drop, good: [...new Set(good)], risks, advice };
}
function explainedHtml(fen, x, mine) {
  return `<li class="xmove"><div class="fh"><bdi class="mv">${esc(moveLabel(fen, x.san))}</bdi><span class="cls ${x.cls}">${CLASS_AR[x.cls]}</span>${mine ? `<span class="tag">نقلتك</span>` : ""}<span class="note">فرصك <bdi class="mono">${x.es}%</bdi></span></div>
    ${x.good.length ? `<p class="note">ما تفعله: ${x.good.map(fmtNote).join(" ")}</p>` : ""}${x.risks.length ? `<p class="note warnline">ما تخاطر به: ${x.risks.map(fmtNote).join(" ")}</p>` : ""}<p class="habit">${esc(x.advice)}</p></li>`;
}
/* Stockfish's top moves in a position (multipv), each explained, plus the student's move if it is not among them. */
async function explainTopMoves(el, fen, ply, { k = 6, mineUci = null } = {}) {
  el.innerHTML = `<p class="note">Stockfish يحلل كل النقلات المهمة...</p>`;
  const me = new Chess(fen).turn(); const pc = Prob.ctx(fen, ply ?? 30);
  const r = await Engine.analyse(fen, { depth: 13, movetime: 2500, multipv: k });
  if (!r.lines.length) { el.innerHTML = `<p class="note">لا نقلات.</p>`; return; }
  const es = (l) => Prob.esFor(l.cpWhite, me, pc); const esBest = es(r.lines[0]);
  const lines = r.lines.slice();
  if (mineUci && !lines.some((l) => l.pv[0] === mineUci)) { const a = await Engine.analyse(fen, { depth: 12, movetime: 800, searchmoves: [mineUci] }); if (a.lines[0]) lines.push(a.lines[0]); }
  const n = new Chess(fen).moves().length;
  el.innerHTML = `<p class="note">لديك ${arCount(n, "نقلة قانونية واحدة", "نقلتان قانونيتان", "نقلات قانونية", "نقلة قانونية")}. هذه أهمها عند Stockfish، مرتبة من الأفضل:</p>
    <ol class="xmoves">${lines.map((l) => explainedHtml(fen, explainMove(fen, l.pv[0], l.pv, esBest, es(l)), l.pv[0] === mineUci)).join("")}</ol>`;
}
/* Every move of one piece, each explained; the target squares are coloured on the board. */
async function explainPiece(el, board, fen, sq, ply, token) {
  const g = new Chess(fen); const p = g.get(sq); if (!p || p.color !== g.turn()) return;
  const moves = g.moves({ square: sq, verbose: true }); const N = Facts.NAME_AR; const me = g.turn(); const pc = Prob.ctx(fen, ply ?? 30);
  // what this piece sees right now: the opponent's pieces it attacks and your pieces it protects
  const G = Facts.grid(g); const hits = [], guards = [];
  for (const [s, q] of Object.entries(G)) { if (s === sq) continue; if (Facts.attackers(G, s, me).some((a) => a.sq === sq)) (q.color === me ? guards : hits).push(s); }
  const marks = {}; for (const s of hits) marks[s] = "threat"; for (const s of guards) marks[s] = "focus";
  board.update({ marks });
  el.innerHTML = `<div class="fh"><b>${N[p.type]} على ${sq}</b><span class="note">${arCount(moves.length, "نقلة واحدة", "نقلتان", "نقلات", "نقلة")}</span></div>
    <p class="note">يهاجم الآن: ${hits.length ? hits.map((s) => `${N[G[s].type]} ${s}`).join("، ") : "لا شيء"} · يحمي: ${guards.length ? guards.map((s) => `${N[G[s].type]} ${s}`).join("، ") : "لا شيء"} (المربعات الحمراء والمؤطرة على الرقعة).</p>
    ${moves.length ? `<ol class="xmoves"><li class="note">Stockfish يقيّم كل نقلة...</li></ol>` : `<p>هذه القطعة لا تتحرك الآن.</p>`}`;
  if (!moves.length) return;
  const base = await Engine.analyse(fen, { depth: 12, movetime: 1200 }); if (token && !token()) return;
  const es = (l) => Prob.esFor(l.cpWhite, me, pc); const esBest = base.lines[0] ? es(base.lines[0]) : 50;
  const out = [];
  for (const m of moves) {
    const uci = m.from + m.to + (m.promotion || "");
    const a = await Engine.analyse(fen, { depth: 10, movetime: 300, searchmoves: [uci] }); if (token && !token()) return;
    const l = a.lines[0]; if (!l) continue;
    out.push(explainMove(fen, uci, l.pv, Math.max(esBest, es(l)), es(l)));
  }
  out.sort((x, y) => y.es - x.es);
  const col = { excellent: "mgood", good: "mgood", inaccuracy: "mok", mistake: "mbad", blunder: "mbad" };
  for (const x of out) marks[x.uci.slice(2, 4)] = col[x.cls];
  board.update({ marks });
  $(".xmoves", el).outerHTML = `<ol class="xmoves">${out.map((x) => explainedHtml(fen, x)).join("")}</ol><p class="note">على الرقعة: الأخضر جيد، الأصفر مقبول، الأحمر سيئ.</p>`;
}

/* ---------- the chapter's techniques ---------- */
async function techniquesPanel(el, n) {
  const C = await techCatalog().catch(() => null); const list = C && C.chapters[n];
  if (!list || !list.length) { el.innerHTML = ""; return; }
  el.innerHTML = `<div class="panel"><h3>تقنيات هذا المستوى: أتقنها</h3><p class="note">لكل تقنية: القاعدة، ولماذا، وما لا تفعله، وكيف تراها على الرقعة، ثم مواقف بلا نهاية تتدرّب فيها عليها. تُعتبر متقنة بعد 8 صحيحة من آخر 10.</p>
    <div class="techs">${list.map((t) => { const m = techMastery(techState(t.id));
      return `<div class="tech ${m.mastered ? "done" : ""}"><div class="fh"><b>${esc(t.title)}</b><span class="state ${m.mastered ? "on" : "part"}">${m.mastered ? "متقنة" : m.of ? `${m.ok}/${m.of}` : "جديدة"}</span></div>
        <p>${esc(t.rule)}</p><div class="progress"><i style="width:${m.of ? Math.round(100 * m.ok / 10) : 0}%"></i></div>
        <button class="btn" data-tech="${t.id}">تدرّب</button></div>`; }).join("")}</div></div>`;
  for (const b of $$("[data-tech]", el)) b.onclick = () => TechniqueSession($("#v-chapter"), n, list.find((t) => t.id === b.dataset.tech));
}

/* ---------- advice to get better (method, speed, what you personally missed) ---------- */
const methodHtml = (T) => (T.best ? `<details class="method" open><summary><b>أفضل طريقة</b> (خطوة بخطوة)</summary><ol>${T.best.map((x) => `<li>${esc(x)}</li>`).join("")}</ol></details><p class="fastway"><b>أسرع طريقة:</b> ${esc(T.fast)}</p>` : "");
const avgTime = (ts) => { const t = ts.times || []; return t.length ? Math.round(t.reduce((a, b) => a + b, 0) / t.length) : null; };
function adviceHtml(tips, took, avg, ok, T) {
  const speed = avg == null ? `استغرقت ${took} ثانية. هذا رقمك الأول، وسأقارن به المرات القادمة.`
    : took <= avg * 0.8 ? `استغرقت ${took} ثانية، أسرع من معدلك (${avg}).${ok ? " ممتاز: الدقة مع السرعة." : " لكن السرعة بلا دقة لا تفيد: اتبع الخطوات بالترتيب."}`
    : took >= avg * 1.3 ? `استغرقت ${took} ثانية، أبطأ من معدلك (${avg}). لتسرع: ${T.fast || "اتبع الخطوات بالترتيب نفسه كل مرة حتى تصبح عادة."}`
    : `استغرقت ${took} ثانية، قريب من معدلك (${avg}).`;
  return `<div class="advice"><b>نصيحة لتتحسن</b><ul class="facts">${tips.map((x) => `<li>${fmtNote(x)}</li>`).join("")}<li>${esc(speed)}</li></ul></div>`;
}
function moveAdvice(T, { ok, used, bestUsed, bestSan, risks }) {
  const out = [];
  if (ok && used) out.push(`طبّقت التقنية. ثبّتها: قبل كل نقلة في مباراتك اسأل السؤال الأول من «أفضل طريقة»: ${T.best ? T.best[0] : T.rule}`);
  else if (ok) out.push(`نقلتك جيدة بقدر الأفضل، لكنها ليست التقنية. في التدريب اختر التقنية: ${T.rule}${bestUsed ? ` (هنا: [${bestSan}]).` : ""}`);
  else {
    if (bestUsed) out.push(`الحل كان التقنية نفسها: [${bestSan}]. ارجع إلى الخطوة الأولى في «أفضل طريقة» وطبّقها حرفيًا في الموقف التالي.`);
    if (risks.some((r) => /بلا حماية|يكسبه/.test(r))) out.push("خطؤك ترك قطعة بلا حماية. قبل أن تلعب: انظر إلى المربع الذي تذهب إليه، ثم إلى القطع التي كانت قطعتك تحميها.");
    if (T.best && T.best.length > 1) out.push(`الخطوة التي غالبًا تفوت: «${T.best[T.best.length - 1]}»`);
  }
  return out;
}
/* Vision: why you missed what you missed, and why the extra squares were wrong. */
function visionAdvice(kind, fen, miss, extra) {
  const g = new Chess(fen); const me = g.turn(), opp = me === "w" ? "b" : "w"; const G = Facts.grid(g); const N = Facts.NAME_AR; const out = [];
  const nm = (s) => (G[s] ? `${N[G[s].type]} ${s}` : s);
  const how = (t) => ({ p: "البيدق يحمي ويهاجم قطريًا للأمام فقط", n: "قفزة الحصان (شكل L) تفوت العين أكثر من غيرها", b: "الفيل على قطر", r: "الرخ على صف أو عمود", q: "الوزير على خط مستقيم أو قطر", k: "الملك يحمي المربعات الثمانية حوله" }[t]);
  if (kind === "queen") {
    const q = Object.keys(G).find((s) => G[s].type === "q" && G[s].color === me);
    const diag = miss.filter((s) => s[0] !== q[0] && s[1] !== q[1]), straight = miss.filter((s) => s[0] === q[0] || s[1] === q[1]);
    if (diag.length) out.push(`فاتك ما على الأقطار (${diag.map(nm).join("، ")}). الأقطار هي ما تفوّته العين أكثر: ابدأ بها في المرة القادمة.`);
    if (straight.length) out.push(`فاتك ما على العمود أو الصف (${straight.map(nm).join("، ")}). مرّر عينك على الخط كاملًا حتى أول قطعة.`);
    for (const s of extra.slice(0, 2)) out.push(G[s] && G[s].color === opp ? `${nm(s)} ليس على خط مفتوح من الوزير: قطعة أخرى تسد الطريق. توقف دائمًا عند أول قطعة.` : `${nm(s)} ليس قطعة للخصم.`);
  }
  if (kind === "loose") {
    for (const s of miss.slice(0, 3)) out.push(`${nm(s)} لا يحميه شيء${(me === "w" ? +s[1] >= 4 : +s[1] <= 5) ? "، وهو متقدم: القطع المتقدمة غالبًا وحيدة" : ""}${G[s].type === "n" ? "، والحصان نادرًا ما يحميه أحد" : ""}.`);
    for (const s of extra.slice(0, 3)) { const d = Facts.attackers(G, s, me)[0]; if (d) out.push(`${nm(s)} محمي: يحميه ${N[d.type]} على ${d.sq} (${how(d.type)}).`); }
  }
  if (kind === "attacked") {
    for (const s of miss.slice(0, 3)) { const a = Facts.attackers(G, s, opp)[0]; if (a) out.push(`${nm(s)} يهاجمه ${N[a.type]} الخصم على ${a.sq}: ${how(a.type)}.`); }
    const byKnight = miss.filter((s) => Facts.attackers(G, s, opp).some((a) => a.type === "n")).length;
    if (byKnight) out.push("أغلب ما فاتك هجوم بالحصان: ابدأ بحصاني الخصم قبل أي قطعة أخرى.");
    for (const s of extra.slice(0, 2)) out.push(`${nm(s)} ليس مهاجَمًا الآن: تأكد أن خط الهجوم ليس مسدودًا بقطعة.`);
  }
  if (kind === "kingbox") {
    const wg = new Chess(fen.replace(" w ", " b ")); const GB = Facts.grid(wg);
    for (const s of miss.slice(0, 3)) out.push(G[s] ? `الملك يستطيع أخذ ${nm(s)} لأنه بلا حماية: القطعة بجانب الملك تحتاج حارسًا.` : `${s} حر: لا قطعة لك تهاجمه. افحص كل مربع من الثمانية بالترتيب.`);
    for (const s of extra.slice(0, 3)) { const a = Facts.attackers(GB, s, "w")[0]; out.push(a ? `${s} ليس متاحًا: يهاجمه ${N[a.type]} على ${a.sq} (${how(a.type)}).` : `${s} ليس متاحًا للملك.`); }
  }
  if (!miss.length && !extra.length) out.push("رأيت كل شيء. الخطوة التالية: افعلها أسرع في الموقف القادم، ثم افعلها في مبارياتك قبل كل نقلة.");
  return out;
}

function TechniqueSession(root, n, T) {
  const ts = techState(T.id); let token = 0, fen = null, item = null, board, solved = false, picks = new Set(), truth = null;
  root.innerHTML = `
    <div class="whead"><button class="btn quiet" id="t-back">→ الفصل ${n}</button><div class="wtitle"><b>${esc(T.title)}</b><span class="note" id="t-prog"></span></div></div>
    <div class="panel tlesson"><p><b>القاعدة:</b> ${esc(T.rule)}</p><p><b>لماذا:</b> ${esc(T.why)}</p><p><b>لا تفعل:</b> ${esc(T.dont)}</p><p><b>كيف تراها:</b> ${esc(T.see)}</p>${methodHtml(T)}</div>
    <div class="watch">
      <div class="wboard"><div class="boardcap"><span class="turn" id="t-turn"></span><span class="note" id="t-status"></span></div><div class="note" id="t-src"></div>
        <div class="board" id="t-board"></div><div class="row" id="t-ctl"></div></div>
      <div class="wside"><div class="panel" id="t-card" aria-live="polite"></div><div class="panel livecheck" id="t-plan"></div><div class="panel" id="t-x"></div></div>
    </div>`;
  board = Board($("#t-board", root), { interactive: false });
  const alive = (t) => t === token && document.body.contains(root) && $("#t-board", root);
  const setStatus = (t) => { $("#t-status", root).textContent = t; };
  $("#t-back", root).onclick = () => { token++; go("chapter", n); };
  const prog = () => { const m = techMastery(ts); $("#t-prog", root).textContent = `${m.mastered ? "متقنة · " : ""}صحيحة ${m.ok} من آخر ${m.of || 0} · المجموع ${ts.n}`; };
  let t0 = 0; const secs = () => Math.max(1, Math.round((now() - t0) / 1000));
  const record = (ok, s) => { ts.n++; ts.last.push(ok ? 1 : 0); if (ts.last.length > 20) ts.last.shift(); ts.times = (ts.times || []).concat(s).slice(-10); saveJourney(); prog(); };

  async function next() {
    const t = ++token; solved = false; picks = new Set(); truth = null; $("#t-x", root).innerHTML = ""; $("#t-ctl", root).innerHTML = "";
    setStatus("أجهّز الموقف..."); board.update({ interactive: false, arrows: [], marks: {}, onSquare: null, onSelect: null });
    if (T.kind === "pool") {
      let items = []; for (const id of T.pools) items = items.concat((await drillPool(id + ".json")).filter((x) => x.t && x.t.includes(T.tag)));
      if (!alive(t)) return; if (!items.length) { setStatus("لا مواقف لهذه التقنية بعد."); return; }
      item = items[Math.floor(Math.random() * items.length)]; fen = item.fen;
      $("#t-src", root).textContent = `من مباراة حقيقية على Lichess (متوسط التقييم ${item.r})، النقلة ${Math.floor(item.ply / 2) + 1}.`;
    } else if (T.kind === "basic") {
      const r = await randomBasicMate(T.basic); if (!alive(t)) return; if (!r) { setStatus("تعذّر توليد موقف."); return; }
      item = r; fen = r.fen; $("#t-src", root).textContent = `موقف عشوائي: ${T.basic === "kqk" ? "ملك ووزير" : "ملك ورخ"} ضد ملك.`;
    } else { fen = await visionPosition(T.vision); if (!alive(t)) return; item = { fen }; $("#t-src", root).textContent = T.vision === "kingbox" ? "موقف عشوائي في النهاية." : "موقف من مباراة حقيقية."; }
    const me = new Chess(fen).turn();
    $("#t-turn", root).innerHTML = `<i class="${me}"></i>${me === "w" ? "الأبيض" : "الأسود"}`;
    $("#t-plan", root).innerHTML = planHtml(fen, item.ply);
    $("#t-card", root).innerHTML = `<p><b>${esc(T.prompt)}</b></p><p class="note">أنت ${me === "w" ? "بالأبيض" : "بالأسود"}.</p>`;
    if (T.kind === "vision") return visionTask(t, me);
    board.update({ fen, orient: me, last: null, interactive: true, onMove: (m) => answer(m, t) });
    setStatus("فكّر، ثم العب نقلتك."); t0 = now();
    const help = document.createElement("button"); help.className = "btn quiet"; help.textContent = "اشرح لي النقلات المتاحة (يُحسب مساعدة)";
    help.onclick = () => { help.remove(); explainTopMoves($("#t-x", root), fen, item.ply, { k: 6 }); ts.help = (ts.help || 0) + 1; }; $("#t-ctl", root).append(help);
  }
  async function answer(m, t) {
    if (solved) return; solved = true; board.update({ interactive: false, fen: m.fenAfter, last: m.uci });
    $("#t-ctl", root).innerHTML = ""; setStatus("Stockfish يقيّم...");
    const me = new Chess(fen).turn(); const pc = Prob.ctx(fen, item.ply ?? 30);
    const b = await Engine.analyse(fen, { depth: T.kind === "basic" ? 18 : 14, movetime: 1500, multipv: 3 }); if (!alive(t)) return;
    const mineL = b.lines.find((l) => l.pv[0] === m.uci) || (await Engine.analyse(fen, { depth: 13, movetime: 900, searchmoves: [m.uci] })).lines[0];
    if (!alive(t)) return;
    const best = b.lines[0]; const tags = Tech.tagsOf(fen, m.uci); const used = tags.includes(T.tag);
    let ok, verdict;
    if (best.mate && best.mate > 0) { // mates: judged by mate distance
      const mm = new Chess(m.fenAfter).in_checkmate() ? 1 : mineL && mineL.mate > 0 ? mineL.mate : null;
      ok = mm != null && !tags.includes("stalemate") && mm <= best.mate + (T.kind === "basic" ? 2 : 0) && (T.kind !== "basic" || used || mm <= best.mate);
      verdict = tags.includes("stalemate") ? "stalemate: تعادل وضاع الفوز." : mm == null ? "ضاع الكش القسري." : mm === 1 && new Chess(m.fenAfter).in_checkmate() ? "كش مات." : `كش في ${mm} (أسرع طريق: ${best.mate}).`;
    } else {
      const esB = Prob.esFor(best.cpWhite, me, pc), esA = mineL ? Prob.esFor(mineL.cpWhite, me, pc) : esB - 30; const cl = m.uci === best.pv[0] ? { cls: "excellent", drop: 0 } : Prob.classify(esB, esA);
      ok = (used && cl.drop <= 5) || cl.drop <= 1; // the technique within tolerance, or a move as good as the best
      verdict = `${CLASS_AR[cl.cls]}: فرصك ${Math.round(esB)}% مع الأفضل، و${Math.round(esA)}% بعد نقلتك.`;
    }
    const took = secs(); const avg = avgTime(ts); record(ok, took);
    const bestSan = sanOf(fen, best.pv[0]);
    const tips = moveAdvice(T, { ok, used, bestUsed: Tech.tagsOf(fen, best.pv[0]).includes(T.tag), bestSan, risks: !ok && mineL ? moveRisks(fen, m.san, []) : [] });
    const why = bestMoveWhy(fen, bestSan, best.pv[0], null).concat(Tech.tagsOf(fen, best.pv[0]).filter((x) => TAG_AR[x] && x !== "check").map((x) => TAG_AR[x]));
    $("#t-card", root).innerHTML = `<div class="callout ${ok ? "good" : "bad"}"><b>${ok ? "صحيح" : "ليس بعد"}: <bdi class="mv">${esc(moveLabel(fen, m.san))}</bdi></b> ${esc(verdict)}
      <p class="note">${used ? "استخدمت التقنية." : `لم تستخدم التقنية: ${esc(T.rule)}`}</p></div>
      ${m.uci !== best.pv[0] ? `<p>أفضل نقلة: <bdi class="mv">${esc(bestSan)}</bdi>.</p>${why.length ? `<ul class="facts">${[...new Set(why)].map((x) => `<li>${fmtNote(x)}</li>`).join("")}</ul>` : ""}` : ""}
      ${!ok && mineL ? `<p class="note warnline">${moveRisks(fen, m.san, pvToSan(fen, mineL.pv, 4).slice(1)).map(fmtNote).join(" ")}</p>` : ""}
      ${adviceHtml(tips, took, avg, ok, T)}
      <p class="note">اضغط أي قطعة لك على الرقعة لترى كل نقلاتها مع شرح كل واحدة.</p>
      <div class="row"><button class="btn" data-a="next">الموقف التالي</button><button class="btn quiet" data-a="all">اشرح كل النقلات المتاحة</button></div>`;
    $('[data-a="next"]', root).onclick = () => next();
    $('[data-a="all"]', root).onclick = (e) => { e.target.remove(); explainTopMoves($("#t-x", root), fen, item.ply, { k: 6, mineUci: m.uci }); };
    // explorer: the original position, tap a piece to see all its moves explained
    board.update({ fen, last: null, interactive: true, arrows: [{ from: best.pv[0].slice(0, 2), to: best.pv[0].slice(2, 4), color: "good" }, ...(m.uci !== best.pv[0] ? [{ from: m.uci.slice(0, 2), to: m.uci.slice(2, 4), color: ok ? "alt" : "bad" }] : [])],
      onMove: () => board.update({ fen }), onSelect: (sq) => { if (sq) explainPiece($("#t-x", root), board, fen, sq, item.ply, () => alive(t)); } });
    setStatus(ok ? "أحسنت." : "راجع الشرح، ثم الموقف التالي.");
  }

  /* vision: tap squares, checked against the position */
  async function visionPosition(kind) {
    if (kind === "kingbox") {
      for (let i = 0; i < 200; i++) {
        const g = new Chess(); g.clear(); const files = "abcdefgh"; const sq = () => files[Math.floor(Math.random() * 8)] + (1 + Math.floor(Math.random() * 8));
        const a = sq(), q = sq(), k = sq(); if (new Set([a, q, k]).size < 3) continue;
        if (Math.abs(a.charCodeAt(0) - k.charCodeAt(0)) <= 1 && Math.abs(+a[1] - +k[1]) <= 1) continue;
        g.put({ type: "k", color: "w" }, a); g.put({ type: Math.random() < 0.5 ? "q" : "r", color: "w" }, q); g.put({ type: "k", color: "b" }, k);
        const f = g.fen().replace(/ [wb] .*$/, " w - - 0 1"); const h = new Chess(f); if (h.fen().split(" ")[0] !== f.split(" ")[0]) continue;
        const asBlack = new Chess(f.replace(" w ", " b ")); if (asBlack.in_check() || asBlack.game_over() || new Chess(f).in_check()) continue;
        const n = asBlack.moves().length; if (n < 1 || n > 5) continue; return f;
      }
    }
    const items = await drillPool(kind === "queen" ? "ch01-opening.json" : "ch02-safety.json");
    for (let i = 0; i < 200; i++) { const it = items[Math.floor(Math.random() * items.length)]; const g = new Chess(it.fen); const me = g.turn(); const G = Facts.grid(g);
      if (kind === "queen" && !Object.values(G).some((p) => p.type === "q" && p.color === me)) continue;
      if (i < 150 && !visionTruth(kind, it.fen).size) continue; // mostly positions with something to find
      item = it; return it.fen; }
    return items[0].fen;
  }
  function visionTruth(kind, f) {
    const g = new Chess(f); const me = g.turn(), opp = me === "w" ? "b" : "w"; const G = Facts.grid(g); const set = new Set();
    if (kind === "queen") { const q = Object.keys(G).find((s) => G[s].type === "q" && G[s].color === me); for (const [s, p] of Object.entries(G)) if (p.color === opp && Facts.attackers(G, s, me).some((a) => a.sq === q)) set.add(s); }
    if (kind === "loose") for (const [s, p] of Object.entries(G)) { if (p.color === me && !"kp".includes(p.type) && !Facts.attackers(G, s, me).length) set.add(s); }
    if (kind === "attacked") for (const [s, p] of Object.entries(G)) { if (p.color === me && p.type !== "k" && Facts.attackers(G, s, opp).length) set.add(s); }
    if (kind === "kingbox") { const bk = new Chess(f.replace(" w ", " b ")); for (const m of bk.moves({ verbose: true })) set.add(m.to); }
    return set;
  }
  function visionTask(t, me) {
    truth = visionTruth(T.vision, fen); const orient = me;
    const draw = () => board.update({ marks: Object.fromEntries([...picks].map((s) => [s, "focus"])) });
    board.update({ fen, orient, last: null, interactive: false, marks: {}, onSquare: (s) => { if (solved) return; picks.has(s) ? picks.delete(s) : picks.add(s); draw(); } });
    setStatus(T.vision === "kingbox" ? "الملك الأسود: أين يستطيع الذهاب؟" : "اضغط المربعات، ثم «تحقّق»."); t0 = now();
    const btn = document.createElement("button"); btn.className = "btn"; btn.textContent = picks.size ? "تحقّق" : "تحقّق (أو لا شيء)";
    btn.onclick = () => {
      if (solved) return; solved = true; btn.remove();
      const miss = [...truth].filter((s) => !picks.has(s)), extra = [...picks].filter((s) => !truth.has(s)); const ok = !miss.length && !extra.length; const took = secs(); const avg = avgTime(ts); record(ok, took);
      const marks = {}; for (const s of truth) marks[s] = "mgood"; for (const s of extra) marks[s] = "mbad"; board.update({ marks, onSquare: null });
      const G = Facts.grid(new Chess(fen)); const nm = (s) => (G[s] ? `${Facts.NAME_AR[G[s].type]} ${s}` : s);
      $("#t-card", root).innerHTML = `<div class="callout ${ok ? "good" : "bad"}"><b>${ok ? "صحيح تمامًا" : "ليس تمامًا"}</b>
        <p>الصحيح: ${truth.size ? [...truth].map(nm).join("، ") : "لا شيء"}.</p>${miss.length ? `<p>فاتك: ${miss.map(nm).join("، ")}.</p>` : ""}${extra.length ? `<p>زيادة: ${extra.map(nm).join("، ")}.</p>` : ""}</div>
        ${adviceHtml(visionAdvice(T.vision, fen, miss, extra), took, avg, ok, T)}<div class="row"><button class="btn" data-a="next">الموقف التالي</button></div>`;
      $('[data-a="next"]', root).onclick = () => next();
      setStatus(ok ? "أحسنت." : "انظر إلى المربعات الخضراء.");
    };
    $("#t-ctl", root).append(btn);
  }
  prog(); next();
}
