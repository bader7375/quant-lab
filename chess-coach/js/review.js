"use strict";
/* Review: after a coached game. 3-5 key moments chosen from the game's data, what went well, what to work on,
   one lesson. Every mistake becomes a warm-up card (db cards/<id>, kind "warm") when the game ends. */

/* Arabic counted nouns: 1, 2, 3-10, 11+. */
const arCount = (n, one, two, few, many) => (n === 1 ? one : n === 2 ? two : n >= 3 && n <= 10 ? `${n} ${few}` : `${n} ${many}`);
const timesAr = (n) => arCount(n, "مرة واحدة", "مرتين", "مرات", "مرة");
const gameTitle = (g) => `${new Date(g.t).toISOString().slice(0, 10)} · ${g.color === "w" ? "بالأبيض" : "بالأسود"} · ${RESULT_AR[g.result] || "–"}`;
const OPENING_ITEMS = {
  centre: "بيدق في المركز في أول 10 نقلات",
  develop: "3 قطع خفيفة على الأقل خرجت قبل النقلة 10",
  castle: "التبييت قبل النقلة 12",
  queen: "الوزير لم يخرج مبكرًا",
  repeat: "لا قطعة تحركت مرتين في أول 8 نقلات بلا سبب",
};
const OPENING_LESSON = {
  castle: "بيّت قبل النقلة 12: الملك في المركز هدف سهل، والرخ في الزاوية لا يعمل.",
  develop: "في أول 10 نقلات: أخرج قطعك الخفيفة قبل أي هجوم، قطعة جديدة في كل نقلة تقريبًا.",
  centre: "ابدأ بالمركز: بيدق إلى e4 أو d4 (وبالأسود e5 أو d5) في أول نقلتين.",
  queen: "لا تخرج الوزير في أول 4 نقلات: كل هجوم عليه يمنح الخصم نقلة تطوير مجانية.",
  repeat: "لا تحرك القطعة نفسها مرتين في الافتتاح إلا لسبب: أسر، أو هروب من تهديد.",
};

STAGE_RUNNERS.review = (n) => {
  const box = $("#stage-box"); const games = chapterGames(n).slice().reverse(); const s = chState(n); const seen = new Set(s.review.games || []);
  if (!games.length) {
    box.innerHTML = `<div class="panel"><h3>راجع</h3><p class="note">لا مباريات بعد في هذا الفصل. العب مباراة مع المدرّب أولًا، ثم ارجع هنا.</p><div class="row"><button class="btn" id="r-play">العب الآن</button></div></div>`;
    $("#r-play", box).onclick = () => STAGE_RUNNERS.play(n); return;
  }
  box.innerHTML = `<div class="panel"><h3>راجع مبارياتك</h3><p class="note">لكل مباراة: اللحظات الحاسمة، ما أحسنت فيه، ما تعمل عليه، ودرس واحد. كل ذلك محسوب من بيانات المباراة.</p>
    <div class="demos">${games.map((g) => { const m = g.metrics || {}; return `<button class="demo" data-g="${g.id}"><b>${esc(gameTitle(g))}</b><span class="note">${m.moves ?? "–"} نقلة لك · أخطاء فادحة ${m.blunders ?? 0} · أخطاء ${m.mistakes ?? 0} · غير دقيقة ${m.inaccuracies ?? 0}</span><span class="state ${seen.has(g.id) ? "on" : "part"}">${seen.has(g.id) ? "راجعتها" : "لم تراجعها"}</span></button>`; }).join("")}</div></div>`;
  for (const b of $$("[data-g]", box)) b.onclick = () => openReview(n, J.games.find((g) => g.id === b.dataset.g));
  box.scrollIntoView?.({ block: "start" });
};

/* How much better the best move was than the second best; 0 for a recapture, which is obvious rather than found. */
function onlyMoveGap(G, r) {
  const prev = G.ucis[r.ply - 1]; if (r.san.includes("x") && prev && prev.slice(2, 4) === r.uci.slice(2, 4)) return 0;
  return r.alts && r.alts.length > 1 ? r.alts[0].es - r.alts[1].es : 0;
}
/* The key moments: the largest drops in your chances, a missed chance, and the moments you found the only good move. */
function keyMoments(G) {
  const own = G.recs.filter((r) => r.color === G.color && r.cls); const pick = [];
  const add = (r, kind) => { if (r && !pick.some((p) => p.r === r) && pick.length < 5) pick.push({ r, kind }); };
  own.filter((r) => r.hung || r.missed).sort((a, b) => b.drop - a.drop).slice(0, 3).forEach((r) => add(r, "error")); // a piece left hanging or a missed threat is always a key moment
  own.filter((r) => r.drop >= 10).sort((a, b) => b.drop - a.drop).slice(0, 3).forEach((r) => add(r, r.missedChance ? "chance" : "error"));
  own.filter((r) => r.missedChance).sort((a, b) => b.gift - a.gift).slice(0, 1).forEach((r) => add(r, "chance"));
  const shine = (r) => Math.max(onlyMoveGap(G, r), r.gift || 0);
  own.filter((r) => !r.takenBack && r.drop <= 2 && shine(r) >= 10).sort((a, b) => shine(b) - shine(a)).slice(0, 2).forEach((r) => add(r, "good"));
  if (pick.length < 3) own.filter((r) => r.drop >= 5).sort((a, b) => b.drop - a.drop).forEach((r) => { if (pick.length < 3) add(r, r.drop >= 10 ? "error" : "slip"); });
  return pick.sort((a, b) => a.r.ply - b.r.ply || (a.r.takenBack ? -1 : 1));
}

/* What went well, what to work on, one lesson: from the metrics only. */
function reviewSummary(G, c, m) {
  const own = G.recs.filter((r) => r.color === G.color && r.cls); const fin = own.filter((r) => !r.takenBack);
  const opening = (c.rule || {}).kind === "opening_checklist"; const well = [], work = [];
  if (opening && m.openingItems) {
    const ok = Object.keys(OPENING_ITEMS).filter((k) => m.openingItems[k]), bad = Object.keys(OPENING_ITEMS).filter((k) => !m.openingItems[k]);
    if (ok.length) well.push(`قائمة الافتتاح: حققت ${ok.length} من 5 (${ok.map((k) => OPENING_ITEMS[k]).join("، ")}).`);
    if (bad.length) work.push(`قائمة الافتتاح: لم يتحقق ${bad.map((k) => OPENING_ITEMS[k]).join("، ")}.`);
  } else if (opening) work.push("المباراة انتهت قبل نقلتك العاشرة، فلم تُحكم قائمة الافتتاح.");
  if (fin.length >= 8 && m.okShare >= 70) well.push(`${m.okShare}% من نقلاتك ممتازة أو جيدة (تُحسب النقلات التي تراجعت عنها).`);
  if (fin.length >= 10 && !m.hanging) well.push("لم تترك قطعة بلا حماية في المباراة كلها.");
  if (m.threats && !m.missedThreats) well.push(`عالجت كل تهديدات الخصم (${m.threats}).`);
  const onlyFound = fin.filter((r) => r.drop <= 2 && onlyMoveGap(G, r) >= 10).length;
  if (onlyFound) well.push(`وجدت النقلة الجيدة الوحيدة ${timesAr(onlyFound)}.`);
  if (m.gifts) (m.punished * 2 >= m.gifts ? well : work).push(`أخطأ الخصم خطأ واضحًا ${timesAr(m.gifts)}، واستغليت ${m.punished}.`);
  if (m.hanging) work.push(`تركت قطعة بلا حماية كافية ${timesAr(m.hanging)}.`);
  if (m.missedThreats) work.push(`فاتك تهديد للخصم ${timesAr(m.missedThreats)}.`);
  const back = own.filter((r) => r.takenBack && r.drop > 10).length;
  if (m.blunders + m.mistakes) work.push(`أخطاء فادحة: ${m.blunders}، أخطاء: ${m.mistakes}${back ? ` (منها ${back} تراجعت عنها، وتبقى محسوبة)` : ""}.`);
  const worst = own.slice().sort((a, b) => b.drop - a.drop)[0];
  if (worst && worst.drop >= 10) work.push(`أكبر خسارة في الفرص: ${moveLabel(worst.fenBefore, worst.san)} (من ${worst.esBefore}% إلى ${worst.esAfter}%).`);
  if (!well.length) well.push("لا شيء بارز في البيانات هذه المرة.");
  if (!work.length) work.push("لا أخطاء واضحة في البيانات.");
  let lesson;
  const failed = m.openingItems ? ["castle", "develop", "centre", "queen", "repeat"].filter((k) => !m.openingItems[k]) : [];
  if (m.hanging || m.missedThreats) lesson = "قبل كل نقلة اسأل سؤالين: ماذا يهدد الخصم الآن؟ وبعد نقلتي، هل تبقى كل قطعة محمية؟";
  else if (opening && failed.length > 1) lesson = OPENING_LESSON[failed[0]];
  else if (m.gifts > m.punished) lesson = "بعد كل نقلة للخصم اسأل: هل ترك قطعة بلا حماية؟ هل فتح طريقًا إلى ملكه؟ الأخطاء لا تُستغل إلا إذا بحثت عنها.";
  else if (m.blunders + m.mistakes) lesson = "قبل أن تلعب، تخيّل أقوى رد للخصم على نقلتك، ولا تلعبها إن لم تعرف جوابه.";
  else if (opening && failed.length) lesson = OPENING_LESSON[failed[0]];
  else lesson = "الروتين نفسه في كل نقلة: تهديد الخصم أولًا، ثم نقلاتك القسرية، ثم خطتك.";
  return { well, work, lesson };
}

function openReview(n, G) {
  if (!G) return;
  const c = chapter(n); const root = $("#v-chapter"); const m = G.metrics || computeMetrics(G);
  const s = chState(n); s.review.games = [...new Set([...(s.review.games || []), G.id])]; s.review.count = s.review.games.length; saveJourney();
  const moments = keyMoments(G); const sum = reviewSummary(G, c, m); const opening = (c.rule || {}).kind === "opening_checklist"; const prog = ruleProgress(c);
  const safety = (c.rule || {}).kind === "safety";
  root.innerHTML = `
    <div class="whead"><button class="btn quiet" id="r-back">→ الفصل ${n}</button>
      <div class="wtitle"><b>مراجعة المباراة · ${esc(gameTitle(G))}</b><span class="note">${esc(G.reason || "")} · ${esc(OPP.label(G.opp.rating, G.opp.kind))}</span>${theoryNote(G)}</div></div>
    <div class="kpis small rk">${kpi(m.moves, "نقلاتك")}${kpi(m.okShare == null ? "–" : m.okShare + "%", "ممتازة أو جيدة")}${kpi(m.inaccuracies, "غير دقيقة")}${kpi(m.mistakes, "أخطاء")}${kpi(m.blunders, "أخطاء فادحة")}${kpi(m.takebacks, "تراجعات")}${kpi(m.hints, "تلميحات")}</div>
    <div class="panel"><h3>فرصك خلال المباراة</h3>${esChart(G, moments)}<p class="note">تقدير فرصك (من 100) بعد كل نقلة عند لاعبين بمستواك. الدوائر المرقّمة هي اللحظات الحاسمة أدناه، والدائرة المفرغة نقلة تراجعت عنها (خارج المنحنى).</p></div>
    ${opening ? `<div class="panel"><h3>قائمة الافتتاح في هذه المباراة</h3>${m.openingItems ? `<ul class="checklist live">${Object.keys(OPENING_ITEMS).map((k) => `<li class="${m.openingItems[k] ? "ok" : "fail"}">${esc(OPENING_ITEMS[k])}</li>`).join("")}</ul><p><bdi class="mono">${m.openingScore}/5</bdi>${m.openingBlunder ? " · وفيها خطأ فادح في أول 10 نقلات" : ""}. ${m.openingScore >= 4 && !m.openingBlunder ? "مباراة مؤهلة لشرط الفصل." : "ليست مؤهلة لشرط الفصل: يلزم 4 من 5 بدون خطأ فادح في أول 10 نقلات."}</p>` : `<p class="note">المباراة أقصر من 10 نقلات لك، فلم تُحكم القائمة.</p>`}
      ${prog.pending ? "" : `<p class="note">شرط إكمال الفصل الآن: <bdi class="mono">${prog.have}/${prog.need}</bdi> ${esc(prog.unit)}.</p>`}</div>` : ""}
    ${safety ? safetyPanelHtml(G, m, prog) : ""}
    <h3 class="sect">اللحظات الحاسمة</h3>
    ${moments.length ? `<div class="moments">${moments.map((mo, i) => momentHtml(mo, i, G)).join("")}</div>` : `<p class="empty">لا لحظات حاسمة في البيانات: لم تتغير فرصك كثيرًا بأي نقلة.</p>`}
    ${moments.length && moments.length < 3 ? `<p class="note">${moments.length === 1 ? "لحظة واحدة فقط تستحق" : "لحظتان فقط تستحقان"} التوقف في هذه المباراة.</p>` : ""}
    <div class="wl">
      <div class="panel"><h3>ما أحسنت فيه</h3><ul class="facts">${sum.well.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
      <div class="panel"><h3>ما تعمل عليه</h3><ul class="facts">${sum.work.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
    </div>
    <div class="panel"><h3>درس واحد</h3><p class="lesson">${esc(sum.lesson)}</p><div id="r-claude"></div></div>
    ${G.warmCards ? `<div class="panel"><h3>للإحماء</h3><p>حفظتُ ${arCount(G.warmCards, "موقفًا واحدًا", "موقفين", "مواقف", "موقفًا")} من أخطائك في هذه المباراة. ${G.warmCards === 1 ? "سيعود" : "ستعود"} إليك كتمرين إحماء قصير في جلسة لاحقة: تجد النقلة الأفضل بنفسك.</p></div>` : ""}
    <div class="row"><button class="btn" id="r-again">مباراة جديدة</button><button class="btn quiet" id="r-ch">عودة إلى الفصل</button></div>`;
  $("#r-back", root).onclick = () => go("chapter", n); $("#r-ch", root).onclick = () => go("chapter", n);
  $("#r-again", root).onclick = () => { go("chapter", n); STAGE_RUNNERS.play(n); };
  moments.forEach((mo, i) => {
    const el = $(`[data-m="${i}"]`, root); const r = mo.r;
    const arrows = [{ from: r.uci.slice(0, 2), to: r.uci.slice(2, 4), color: mo.kind === "good" ? "good" : "bad" }];
    if (r.bestUci && r.bestUci !== r.uci && mo.kind !== "good") arrows.push({ from: r.bestUci.slice(0, 2), to: r.bestUci.slice(2, 4), color: "good" });
    const lines = [{ title: `ما لعبته: ${r.san}`, sans: [r.san, ...(r.refut || [])] }];
    if (r.best && r.best !== r.san) lines.push({ title: `الأفضل: ${r.best}`, sans: r.bestLine });
    MiniLine($(".mline", el), { fen: r.fenBefore, orient: G.color, lines, arrows });
    const ex = $("[data-explain]", el); if (ex) ex.onclick = () => { ex.parentElement.remove(); explainMoment($(".fx", el), G, c, mo); };
  });
  reviewClaude($("#r-claude", root), G, c, m, moments);
  root.scrollIntoView?.({ block: "start" });
}

/* Chapter 2: every piece you left hanging and every threat you missed (attempts you took back included), against the
   chapter's limit of one each. */
function safetyPanelHtml(G, m, prog) {
  const own = G.recs.filter((r) => r.color === G.color && r.cls); const bad = own.filter((r) => r.hung || r.missed);
  const st = (k) => (k === 0 ? "ok" : k === 1 ? "warn" : "fail");
  return `<div class="panel"><h3>الأمان في هذه المباراة</h3>
    <ul class="checklist live"><li class="${st(m.hanging)}">قطع تركتها معلّقة: ${m.hanging} (المسموح 1)</li><li class="${st(m.missedThreats)}">تهديدات فاتتك: ${m.missedThreats} (المسموح 1)</li></ul>
    ${bad.length ? `<ul class="facts">${bad.map((r) => `<li><bdi class="mv">${esc(moveLabel(r.fenBefore, r.san))}</bdi> ${r.hung ? "(قطعة معلّقة)" : "(تهديد فائت)"}: ${fmtNote(r.notes[0] || "")}${r.takenBack ? ` <span class="note">تراجعت عنها، وتبقى محسوبة.</span>` : ""}</li>`).join("")}</ul>` : `<p>لم تترك قطعة معلّقة ولم يفتك تهديد في ${arCount(m.attempts, "نقلة واحدة", "نقلتين", "نقلات", "نقلة")}.</p>`}
    <p class="note">التهديدات التي رصدها المدرّب بعد نقلات الخصم: ${m.threats}. تلميحات طلبتها: ${m.hints}. نقلات غيّرتها بعد أسئلة الفحص: ${m.rechecks || 0}.</p>
    <p>${esc(safetyVerdictText(m, G))}</p>
    <p class="note">شرط إكمال الفصل الآن: <bdi class="mono">${prog.have}/${prog.need}</bdi> ${esc(prog.unit)}.</p></div>`;
}

/* The opening's name and how long the game stayed in positions the masters database knows (75+ games). */
function theoryNote(G) {
  const inTree = G.recs.filter((r) => r.masters && !r.takenBack); const last = inTree[inTree.length - 1];
  const parts = [];
  if (G.opening) parts.push(`الافتتاح: <bdi dir="ltr">${esc(G.opening.eco + " · " + G.opening.name)}</bdi>`);
  if (last) parts.push(`بقيت ضمن مواقف الأساتذة المعروفة حتى نقلتك <bdi class="mono">${esc(moveLabel(last.fenBefore, last.san))}</bdi>`);
  return parts.length ? `<span class="note">${parts.join(" · ")}</span>` : "";
}
function momentHtml(mo, i, G) {
  const r = mo.r; const T = { error: "خطأ", chance: "فرصة ضائعة", good: "لحظة جيدة", slip: "أقل من الأفضل" }[mo.kind]; const why = [];
  if (mo.kind === "good") {
    if (r.gift >= 10) why.push("الخصم أخطأ في النقلة السابقة، ووجدت ردًّا يستغل ذلك.");
    if (onlyMoveGap(G, r) >= 10) why.push(`كانت تقريبًا النقلة الجيدة الوحيدة: ثاني أفضل نقلة [${r.alts[1].san}] تعطيك ${r.alts[1].es}% فقط.`);
  } else if (mo.kind === "slip") why.push(`فرق صغير: ${r.drop} نقاط من فرصك. ليس خطأً، لكنه المكان الأوضح للتحسين في هذه المباراة.`, ...(r.notes || []));
  else why.push(...(r.notes || []));
  const allowed = allowedFrom(r.fenBefore, [r.bestLine || [], [r.san, ...(r.refut || [])], G.sans]);
  return `<div class="panel moment ${mo.kind}" data-m="${i}">
    <div class="fh"><span class="mbadge">${i + 1}</span><b>${T}</b><bdi class="mv">${esc(moveLabel(r.fenBefore, r.san))}</bdi><span class="cls ${r.cls}">${CLASS_AR[r.cls]}</span>${r.takenBack ? `<span class="tag">تراجعت عنها</span>` : ""}<span class="note">فرصك <bdi class="mono">${r.esBefore}%</bdi> ← <bdi class="mono">${r.esAfter}%</bdi></span></div>
    <div class="mgrid"><div class="mline"></div><div class="mtext">
      ${why.length ? `<ul class="facts">${why.map((x) => `<li>${fmtNote(x)}</li>`).join("")}</ul>` : ""}
      ${mo.kind !== "good" && r.best && r.best !== r.san ? `<p>الأفضل كان <bdi class="mv">${esc(r.best)}</bdi>. خط Stockfish: <bdi class="mv">${esc(numberedLine(r.fenBefore, (r.bestLine || []).slice(0, 6)))}</bdi>.</p>` : ""}
      ${mo.kind !== "good" ? humanLineHtml(r) : ""}${mastersLineHtml(r)}
      ${r.coach ? coachHtml("ما قاله المدرّب أثناء المباراة", markSan(esc(r.coach), allowed).html) : ""}
      ${SAMPLE ? `<div class="row"><button class="btn quiet" data-explain="${i}">اشرح لي هذه اللحظة</button></div>` : ""}<div class="fx"></div>
    </div></div></div>`;
}

/* A small board with buttons for each line and step controls. */
function MiniLine(el, { fen, orient, lines, arrows = [] }) {
  el.innerHTML = `<div class="board small"></div><div class="mlbtns">${lines.map((l, i) => `<button type="button" class="chip-q" data-l="${i}">${esc(l.title)}</button>`).join("")}</div>
    <div class="row stepper"><button type="button" class="ctl" data-s="-1" aria-label="السابقة">→</button><span class="note mltxt"></span><button type="button" class="ctl" data-s="1" aria-label="التالية">←</button></div>`;
  const b = Board($(".board", el), { fen, orient, interactive: false, arrows }); const txt = $(".mltxt", el);
  let k = 0, fens = [fen], ucis = [], sans = [];
  function pick(i) {
    fens = [fen]; ucis = []; sans = []; const g = new Chess(fen);
    for (const s of lines[i].sans) { const m = g.move(s, { sloppy: true }); if (!m) break; fens.push(g.fen()); ucis.push(m.from + m.to); sans.push(m.san); }
    k = sans.length ? 1 : 0; for (const x of $$("[data-l]", el)) x.classList.toggle("on", +x.dataset.l === i); show();
  }
  function show() { b.update({ fen: fens[k], last: k ? ucis[k - 1] : null, arrows: k === 0 ? arrows : [] }); txt.innerHTML = k ? `<bdi class="mv">${esc(numberedLine(fen, sans.slice(0, k)))}</bdi>` : "الموقف قبل النقلة"; }
  for (const x of $$("[data-l]", el)) x.onclick = () => pick(+x.dataset.l);
  for (const x of $$("[data-s]", el)) x.onclick = () => { k = Math.max(0, Math.min(fens.length - 1, k + +x.dataset.s)); show(); };
  show();
}

/* Your chances after every move of yours (moves taken back are left out of the curve). */
function esChart(G, moments) {
  const own = G.recs.filter((r) => r.color === G.color && r.cls && !r.takenBack);
  if (own.length < 2) return `<p class="empty">المباراة أقصر من أن يُرسم لها منحنى.</p>`;
  const pts = []; for (const r of own) { pts.push([r.ply, r.esBefore]); pts.push([r.ply + 1, r.esAfter]); }
  const avail = (($("#v-chapter") || {}).clientWidth || 680) - 40; // drawn at about its real size, so the labels stay readable on a phone
  const maxX = Math.max(...pts.map((p) => p[0]), 2); const W = Math.round(Math.max(300, Math.min(640, avail))), H = W < 480 ? 170 : 190, L = 34, R = 12, T = 12, B = 26;
  const x = (p) => L + (W - L - R) * p / maxX, y = (v) => T + (H - T - B) * (1 - v / 100);
  const d = pts.map((p, i) => `${i ? "L" : "M"}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join(" ");
  const area = `${d} L${x(pts[pts.length - 1][0]).toFixed(1)},${y(0)} L${x(pts[0][0]).toFixed(1)},${y(0)} Z`;
  const moveTicks = []; const step = maxX > 60 || W < 480 ? 20 : 10; for (let p = 0; p <= maxX; p += step) moveTicks.push(p);
  const marks = moments.map((mo, i) => { const r = mo.r; const cx = x(r.ply + 1), cy = y(r.esAfter); return `<g><circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="9" class="mk ${mo.kind}${r.takenBack ? " back" : ""}"></circle><text x="${cx.toFixed(1)}" y="${(cy + 0.5).toFixed(1)}" class="mkt${r.takenBack ? " back" : ""}">${i + 1}</text></g>`; }).join("");
  return `<div class="chart" dir="ltr"><svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="منحنى فرصك خلال المباراة">
    ${[0, 50, 100].map((v) => `<line class="${v === 50 ? "ref" : "ax"}" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"></line><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${v}</text>`).join("")}
    ${moveTicks.map((p) => `<text x="${x(p).toFixed(1)}" y="${H - 6}" text-anchor="middle">${Math.floor(p / 2) + 1}</text>`).join("")}
    <path class="area" d="${area}"></path><path class="ln" d="${d}"></path>${marks}</svg></div>`;
}

/* Claude: a short review in words, from the same data. Cached on the game. */
async function reviewClaude(el, G, c, m, moments) {
  if (!el || !SAMPLE) return;
  const allowed = allowedFrom(G.start, [G.sans, ...moments.flatMap((mo) => [mo.r.bestLine || [], [mo.r.san, ...(mo.r.refut || [])]])]);
  const render = (t) => { const a = markSan(esc(t.review), allowed), b = markSan(esc(t.lesson), allowed); el.innerHTML = coachHtml("خلاصة المدرّب (Claude، من بيانات المباراة)", a.html + (t.lesson ? `<br><b>${b.html}</b>` : "") + unverifiedHtml([...a.bad, ...b.bad])); };
  if (G.reviewText) return render(G.reviewText);
  el.innerHTML = coachHtml("خلاصة المدرّب", "يكتب...");
  const lines = moments.map((mo, i) => { const r = mo.r; return `${i + 1}. ${moveLabel(r.fenBefore, r.san)} [${mo.kind}${r.takenBack ? ", taken back" : ""}] rated ${r.cls}, chances ${r.esBefore}% -> ${r.esAfter}%${r.best && r.best !== r.san ? `; better was ${r.best}, Stockfish line: ${numberedLine(r.fenBefore, r.bestLine || [])}` : ""}; Stockfish's reply line after the move played: ${numberedLine(r.fen, r.refut || []) || "none"}; observations: ${(r.notes || []).map(plainNote).join(" ") || "none"}`; }).join("\n");
  const prompt = `${COACH_RULES}\n${LEVEL_RULES[c.level] || ""}
TASK: Write a short post-game review for the student in Arabic (3-5 sentences): what decided this game, what to keep doing, what to change. Then a one-sentence lesson that is a reusable thinking habit. Base everything on the DATA; do not praise beyond what the numbers show. Reply with only JSON: {"review_ar": "...", "lesson_ar": "..."}
DATA:
STUDENT PLAYED: ${G.color === "w" ? "White" : "Black"}; RESULT: ${G.result} (${G.reason || ""})
GAME: ${numberedLine(G.start, G.sans)}
METRICS: own moves=${m.moves}; excellent or good=${m.okShare}%; inaccuracies=${m.inaccuracies}; mistakes=${m.mistakes}; blunders=${m.blunders}; pieces left hanging=${m.hanging}; opponent threats missed=${m.missedThreats}; takebacks=${m.takebacks}${m.openingItems ? `; opening checklist=${JSON.stringify(m.openingItems)}` : ""}
KEY MOMENTS:
${lines || "none"}
CHAPTER: ${c.title}: ${c.goal}`;
  try {
    const r = await askClaude(prompt, { json: true, tier: "default" });
    G.reviewText = { review: String(r.review_ar || ""), lesson: String(r.lesson_ar || "") }; Store.set("games/" + G.id, G);
    render(G.reviewText);
  } catch (e) { el.innerHTML = coachHtml("خلاصة المدرّب", esc(claudeMsg(e))); }
}
async function explainMoment(el, G, c, mo) {
  const r = mo.r; el.innerHTML = coachHtml("المدرّب", "يكتب...");
  const prompt = `${COACH_RULES}\n${LEVEL_RULES[c.level] || ""}
TASK: Explain this moment of the student's game in Arabic, 3-5 short sentences: what the position demanded, what the student's move did, and ${mo.kind === "good" ? "why it was the right decision" : "why the better move works"}. End with one reusable thinking habit.
DATA:
POSITION BEFORE THE MOVE: ${r.fenBefore} (student = ${G.color === "w" ? "White" : "Black"}, to move)
PIECES: ${pieceList(r.fenBefore)}
GAME UP TO HERE: ${numberedLine(G.start, G.sans.slice(0, r.ply)) || "(start)"}
MOVE PLAYED: ${r.san}${r.takenBack ? " (later taken back)" : ""}, rated ${r.cls}; chances ${r.esBefore}% with the best move, ${r.esAfter}% after the move played
STOCKFISH BEST LINE: ${numberedLine(r.fenBefore, r.bestLine || []) || "none"}
STOCKFISH REPLY LINE AFTER THE MOVE PLAYED: ${numberedLine(r.fen, r.refut || []) || "none"}
OTHER CANDIDATES (chances afterwards): ${(r.alts || []).map((a) => `${a.san} ${a.es}%`).join(", ") || "none"}
OBSERVATIONS (verified): ${(r.notes || []).map(plainNote).join(" ") || "none"}
FACTS BEFORE THE MOVE (student's side): ${Facts.describe(Facts.positionFacts(r.fenBefore, r.ply), G.color).join(" ") || "none"}`;
  const allowed = allowedFrom(r.fenBefore, [r.bestLine || [], [r.san, ...(r.refut || [])], (r.alts || []).map((a) => a.san), G.sans]);
  try {
    const t = await askClaude(prompt, { tier: "quick", onText: (x) => { el.innerHTML = coachHtml("المدرّب", markSan(esc(x.text), null).html); } });
    const { html, bad } = markSan(esc(t), allowed); el.innerHTML = coachHtml("المدرّب", html + unverifiedHtml(bad));
  } catch (e) { el.innerHTML = coachHtml("المدرّب", esc(claudeMsg(e))); }
}

/* Mistakes (a drop of 10 or more, taken back or not) become warm-up cards, due from the next day. */
function makeWarmCards(G) {
  if (G.cardsMade) return; G.cardsMade = true;
  const seen = new Set(); let k = 0;
  for (const r of G.recs) {
    if (r.color !== G.color || !r.cls || r.drop < 10 || !r.bestUci || seen.has(r.fenBefore)) continue;
    seen.add(r.fenBefore);
    const id = `warm-${G.id}-${r.ply}-${k++}`;
    const card = { id, kind: "warm", chapter: G.chapter, gameId: G.id, ply: r.ply, fen: r.fenBefore, played: r.san, playedUci: r.uci, best: r.best, bestUci: r.bestUci, bestLine: r.bestLine, refut: r.refut, drop: r.drop, cls: r.cls, hung: r.hung || null, missed: r.missed || null, created: now(), due: now() + 20 * 3600000, reps: 0, ef: 2.5, interval: 0, lapses: 0 };
    Store.set("cards/" + id, card); if (typeof WARM !== "undefined") WARM.cards.push(card);
  }
  G.warmCards = k;
}
