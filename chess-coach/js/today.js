"use strict";
/* جلسة اليوم: one guided daily session built from the student's own data, replacing the open chapter map as the way to
   learn (the chapters stay as a library). Five steps:
   1. eye warm-up (5 vision questions, the weakest drill first);
   2. the skill of the day: the first skill of the ladder not yet mastered, 10 positions; mastered at 8/10 with no help.
      A mastered skill comes back for a 5-question review after 7 and 21 days; failing it (under 4/5) un-masters it;
   3. your own mistakes (positions from your games, spaced repetition);
   4. one full game: no best-move hint (a teaching hint in three steps instead), no restart (resign is allowed), colours
      alternate;
   5. the review of that game.
   Progress is shown from hint-free moves only. No Claude calls. */
const SKILL_LEVELS = [
  { n: 1, name: "الأمان: لا تخسر قطعة", why: "62% من أخطائك في مبارياتك تهديد فاتك أو قطعة تركتها بلا حماية." },
  { n: 2, name: "الفرص: خذ ما يُعطى لك", why: "عندما يخطئ الخصم، اعرف كيف تعاقبه." },
  { n: 3, name: "الافتتاح بلا أخطاء", why: "أغلب أخطائك تقع في أول 20 نقلة." },
  { n: 4, name: "إنهاء المباراة", why: "حوّل التفوق إلى فوز." },
  { n: 5, name: "الخطة في وسط اللعب", why: "ماذا تفعل عندما لا يوجد تكتيك." },
  { n: 6, name: "بنى البيادق", why: "البنية تختار الخطة." },
];
const SKILLS = [
  { id: "s-changed", lv: 1, kind: "vision", ref: "changed", ch: 2, title: "ماذا تغيّر بنقلة الخصم؟" },
  { id: "s-save", lv: 1, kind: "tech", ref: "t2-save", ch: 2, title: "قطعتك مهاجَمة: أنقذها أو خذ المهاجم" },
  { id: "s-threat", lv: 1, kind: "vision", ref: "threat", ch: 2, title: "ماذا يهاجمني الآن؟" },
  { id: "s-cover", lv: 1, kind: "tech", ref: "t2-cover", ch: 2, title: "احمِ قطعتك دون أن تحرّكها" },
  { id: "s-loose", lv: 1, kind: "vision", ref: "loose", ch: 2, title: "قطعي غير المحمية" },
  { id: "s-safe", lv: 1, kind: "tech", ref: "t2-safe", ch: 2, title: "النقلة الآمنة حيث أخطأ لاعب حقيقي" },
  { id: "s-take", lv: 2, kind: "tech", ref: "t2-take", ch: 2, title: "خذ ما تُرك بلا حماية" },
  { id: "s-attack", lv: 2, kind: "vision", ref: "attack", ch: 2, title: "ماذا أهاجم؟" },
  { id: "s-check", lv: 2, kind: "tech", ref: "t2-check", ch: 2, title: "الكشات أولًا" },
  { id: "s-fork", lv: 2, kind: "tech", ref: "t4-fork", ch: 4, title: "الشوكة" },
  { id: "s-pin", lv: 2, kind: "tech", ref: "t4-pin", ch: 4, title: "التثبيت" },
  { id: "s-disc", lv: 2, kind: "tech", ref: "t4-discovered", ch: 4, title: "الهجوم المكشوف" },
  { id: "s-removal", lv: 2, kind: "tech", ref: "t4-removal", ch: 4, title: "أزل المدافع" },
  { id: "s-skewer", lv: 2, kind: "tech", ref: "t4-skewer", ch: 4, title: "السيخ" },
  { id: "s-knight", lv: 3, kind: "tech", ref: "t1-knight", ch: 1, title: "تطوير الحصانين" },
  { id: "s-castle", lv: 3, kind: "tech", ref: "t1-castle", ch: 1, title: "التبييت في وقته" },
  { id: "s-rep-w", lv: 3, kind: "tech", ref: "t8-white", ch: 8, title: "ذخيرتي بالأبيض" },
  { id: "s-rep-e5", lv: 3, kind: "tech", ref: "t8-e5", ch: 8, title: "ذخيرتي بالأسود ضد 1.e4" },
  { id: "s-rep-qgd", lv: 3, kind: "tech", ref: "t8-qgd", ch: 8, title: "ذخيرتي بالأسود ضد 1.d4" },
  { id: "s-mate1", lv: 4, kind: "tech", ref: "t3-mates", ch: 3, title: "كش مات في نقلة" },
  { id: "s-backrank", lv: 4, kind: "tech", ref: "t3-backrank", ch: 3, title: "كش الصف الأخير" },
  { id: "s-kqk", lv: 4, kind: "tech", ref: "t3-qknight", ch: 3, title: "وزير ضد ملك" },
  { id: "s-krk", lv: 4, kind: "tech", ref: "t3-rcut", ch: 3, title: "رخ ضد ملك" },
  { id: "s-worst", lv: 5, kind: "tech", ref: "t6-worst", ch: 6, title: "حسّن أسوأ قطعة" },
  { id: "s-openfile", lv: 5, kind: "tech", ref: "t6-openfile", ch: 6, title: "الرخ إلى العمود المفتوح" },
  { id: "s-break", lv: 5, kind: "tech", ref: "t6-break", ch: 6, title: "دفعة البيدق" },
  { id: "s-outpost", lv: 5, kind: "tech", ref: "t6-outpost", ch: 6, title: "المربع القوي" },
  { id: "s-iqp", lv: 6, kind: "tech", ref: "t7-iqp-vs", ch: 7, title: "ضد البيدق المعزول" },
  { id: "s-iqp-own", lv: 6, kind: "tech", ref: "t7-iqp-own", ch: 7, title: "بيدقي المعزول" },
  { id: "s-carlsbad", lv: 6, kind: "tech", ref: "t7-carlsbad", ch: 7, title: "Carlsbad" },
  { id: "s-chain", lv: 6, kind: "tech", ref: "t7-chain", ch: 7, title: "سلاسل البيادق" },
];
const SET_N = 10, REVIEW_N = 5, REVIEW_DAYS = [7, 21];
const dayKey = () => new Date().toISOString().slice(0, 10);
function skillState(id) { const s = (J.state.skills = J.state.skills || {}); return s[id] || (s[id] = { sets: [], mastered: null, reviews: 0 }); }
function todayState() {
  const t = J.state.today; if (t && t.day === dayKey()) return t;
  J.state.streak = J.state.streak || { last: null, days: 0 };
  return (J.state.today = { day: dayKey(), done: {}, gameId: null });
}
const currentSkill = () => SKILLS.find((s) => !skillState(s.id).mastered) || SKILLS[SKILLS.length - 1];
function dueReview() { // a mastered skill whose review is due (7 then 21 days after mastering)
  for (const s of SKILLS) { const st = skillState(s.id); if (!st.mastered) continue; const d = REVIEW_DAYS[st.reviews]; if (d != null && now() - st.mastered >= d * 864e5) return s; }
  return null;
}
async function skillTech(s) { const C = await techCatalog(); for (const list of Object.values(C.chapters)) { const T = list.find((t) => t.id === s.ref); if (T) return T; } return null; }

/* The honest picture: your moves played without any help (no hint step, no move explorer, no lens), in every game
   including the ones left unfinished, the last 100 against the 100 before. Games from before per-move hints were
   recorded count only if the whole game had at most one hint. */
const LEVEL_WINDOW = 100;
function realLevel() {
  const all = J.games.filter((g) => g.finished && g.recs && g.recs.length);
  const freeRecs = (g) => { const own = g.recs.filter((r) => r.color === g.color && r.cls && !r.takenBack); const legacy = !own.some((r) => "hint" in r); return legacy ? ((g.metrics || {}).hints || 0) <= 1 ? own : [] : own.filter((r) => !r.hint); };
  const free = all.flatMap(freeRecs);
  const sum = (rec) => { const n = rec.length; return n >= 30 ? { n, bl: +(100 * rec.filter((r) => r.cls === "blunder").length / n).toFixed(1), safety: +(100 * rec.filter((r) => r.hung || r.missed).length / n).toFixed(1), drop: +(rec.reduce((a, r) => a + r.drop, 0) / n).toFixed(1) } : null; };
  const done = all.filter((g) => g.result !== "abandoned").length;
  return { last: sum(free.slice(-LEVEL_WINDOW)), prev: sum(free.slice(-2 * LEVEL_WINDOW, -LEVEL_WINDOW)), free: free.length, games: done, abandoned: all.length - done, total: all.length };
}

/* Once, when the daily session replaces the old flow: games left open by the old flow are closed (all but the most
   recent, which you finish), and the opponent stays at 1900-2000 as you chose. */
function dailyMigrate() {
  if (J.state.dailySince) return;
  const open = J.games.filter((g) => !g.finished && g.sans && g.sans.length).sort((a, b) => b.t - a.t);
  for (const g of open.slice(1)) abandonGame(g, "مباراة قديمة لم تكتمل من قبل قاعدة «كل مباراة تُلعب حتى نهايتها».");
  J.state.settings.oppRating = Math.max(OPP_FLOOR, J.state.settings.oppRating || OPP_FLOOR); Prob.band = J.state.settings.oppRating;
  J.state.dailySince = now(); saveJourney();
}
function renderDaily(el) {
  dailyMigrate();
  const t = todayState(); const sk = dueReview() || currentSkill(); const review = !!dueReview(); const ss = skillState(sk.id);
  const lv = SKILL_LEVELS.find((x) => x.n === sk.lv); const mastered = SKILLS.filter((s) => skillState(s.id).mastered).length;
  const gOpen = J.games.find((g) => !g.finished && g.sans && g.sans.length);
  const tg = t.gameId && J.games.find((g) => g.id === t.gameId); const hasGame = J.games.some((g) => g.finished && g.result !== "abandoned");
  const steps = [
    { k: "warm", t: "إحماء العين", d: "5 أسئلة رؤية سريعة، الأضعف أولًا.", min: 3 },
    t.done.skill && t.skillDone ? (() => { const x = t.skillDone; const s0 = SKILLS.find((s) => s.id === x.id) || sk;
      return { k: "skill", t: `${x.review ? "مراجعة" : "مهارة اليوم"}: ${s0.title}`, d: `اليوم: ${x.ok} من ${x.n} بلا مساعدة${x.mastered ? (x.review ? "، وما زالت ثابتة." : "، وأتقنتها.") : "."} ${s0.id !== sk.id ? `التالية في السلّم: ${sk.title}.` : "تعود في الجلسة القادمة بمواقف جديدة."}`, min: 10 }; })()
    : { k: "skill", t: review ? `مراجعة: ${sk.title}` : `مهارة اليوم: ${sk.title}`, d: review ?`${REVIEW_N} مواقف. أتقنتها قبل ${Math.round((now() - ss.mastered) / 864e5)} يومًا: هل ما زالت ثابتة؟` : `${SET_N} مواقف. تُتقن عند 8 من 10 بلا مساعدة.${ss.sets.length ? ` آخر محاولة: ${ss.sets[ss.sets.length - 1].ok}/${ss.sets[ss.sets.length - 1].n}.` : ""}`, min: 10 },
    { k: "mistakes", t: "أخطاؤك أنت", d: "مواقف من مبارياتك أخطأت فيها: جد النقلة الأفضل.", min: 5 },
    { k: "game", t: gOpen && (!tg || tg.id === gOpen.id) ? "أكمل مباراتك" : "مباراة كاملة", d: "بلا تلميح يكشف النقلة، وبلا إعادة. تستطيع الاستسلام. اللون يتناوب.", min: 15 },
    { k: "review", t: "راجع المباراة", d: "اللحظات الحاسمة ودرس واحد.", min: 5 },
  ];
  const nextK = steps.find((s) => !t.done[s.k]);
  const R = realLevel(); const fmt = (x) => (x ? `${x.bl} خطأ فادح و${x.safety} خطأ أمان لكل 100 نقلة (متوسط الخسارة ${x.drop})` : "لا بيانات كافية بعد");
  el.innerHTML = `<div class="panel today">
    <div class="row" style="justify-content:space-between"><div><span class="eyebrow">جلسة اليوم · نحو 40 دقيقة</span><h2>${esc(lv.name)}</h2><p class="note">${esc(lv.why)} المهارات المتقنة: ${mastered} من ${SKILLS.length}.${J.state.streak && J.state.streak.days ? ` أيام متتالية: ${J.state.streak.days}.` : ""}</p></div></div>
    <ol class="tsteps today-steps">${steps.map((s, i) => `<li class="${t.done[s.k] ? "done" : nextK === s ? "on" : ""}"><span class="tnum ${t.done[s.k] ? "me" : "op"}">${t.done[s.k] ? "✓" : i + 1}</span> <b>${esc(s.t)}</b> <span class="note">~${s.min} د</span><div class="note">${esc(s.d)}</div>
      ${s.k === "review" && !hasGame ? "" : `<button class="btn ${nextK === s || (s.k === "game" && gOpen) ? "" : "quiet"}" data-step="${s.k}">${s.k === "game" && gOpen ? "أكمل المباراة" : t.done[s.k] ? "مرة أخرى" : nextK === s ? "ابدأ" : "ابدأ هذه الخطوة"}</button>`}</li>`).join("")}</ol>
    ${!nextK ? `<div class="callout good"><b>أنهيت جلسة اليوم.</b> عد غدًا: التكرار اليومي القصير أنفع من جلسة طويلة مرة في الأسبوع.</div>` : ""}
    <details class="method"><summary><b>مستواك الحقيقي</b> (من النقلات بلا مساعدة فقط)</summary>
      <p>آخر ${LEVEL_WINDOW} نقلة لك بلا مساعدة: ${esc(fmt(R.last))}.</p><p>الـ${LEVEL_WINDOW} التي قبلها: ${esc(fmt(R.prev))}.</p>
      <p class="note">نقلة «بلا مساعدة»: بلا أي خطوة تلميح، وبلا شرح نقلات القطعة، وبلا عدسة الرؤية. عندك ${R.free} نقلة كهذه. مباريات أنهيتها: ${R.games} من ${R.total}${R.abandoned ? ` (تركت ${R.abandoned} قبل نهايتها في النظام القديم، ونقلاتها محسوبة هنا)` : ""}. الخطأ الفادح وخطأ الأمان هما ما يجب أن ينخفض.</p></details>
    <details class="method"><summary><b>سلّم المهارات</b></summary>${SKILL_LEVELS.map((L) => `<p><b>${L.n}. ${esc(L.name)}</b>: ${SKILLS.filter((s) => s.lv === L.n).map((s) => `${skillState(s.id).mastered ? "✓" : s === sk ? "◀" : "·"} ${esc(s.title)}`).join("، ")}</p>`).join("")}</details>
  </div>`;
  for (const b of $$("[data-step]", el)) b.onclick = () => runStep(b.dataset.step, sk, review);
}
function markStep(k) {
  const t = todayState(); t.done[k] = true;
  if (Object.keys(t.done).length === 1) { const s = J.state.streak || (J.state.streak = { last: null, days: 0 }); const y = new Date(Date.now() - 864e5).toISOString().slice(0, 10); if (s.last !== t.day) { s.days = s.last === y ? s.days + 1 : 1; s.last = t.day; } }
  saveJourney();
}
const backToday = () => go("journey");
async function runStep(k, sk, review) {
  const root = $("#v-journey"); const t = todayState();
  if (k === "warm") {
    const last = J.games.filter((g) => g.finished).slice(-1)[0]; const m = (last && last.metrics) || {};
    const prefer = (m.hanging || 0) + (m.missedThreats || 0) >= 2 ? "changed" : null; // the last game's safety errors steer the warm-up
    return vgRun(root, null, { count: 5, prefer, onBack: backToday, onDone: (r) => { markStep("warm"); stepSummary(root, "إحماء العين", `${r.ok} من ${r.n} صحيحة، متوسط ${r.avg} ثانية.${prefer ? " بدأنا بـ«ماذا تغيّر؟» لأن مباراتك الأخيرة فيها أخطاء أمان." : ""}`); } });
  }
  if (k === "skill") {
    const n = review ? REVIEW_N : SET_N; const st = skillState(sk.id);
    const done = (r) => {
      st.sets.push({ t: now(), n: r.n, ok: r.ok, helped: !!r.helped, review });
      if (review) { if (r.ok >= 4) st.reviews++; else { st.mastered = null; st.reviews = 0; } }
      else if (r.ok >= 8) { st.mastered = now(); st.reviews = 0; }
      t.skillDone = { id: sk.id, ok: r.ok, n: r.n, review, mastered: !!st.mastered }; markStep("skill"); saveJourney();
      const res = review ? (st.mastered ? `${r.ok} من ${r.n}: المهارة ما زالت ثابتة.` : `${r.ok} من ${r.n}: المهارة تحتاج تدريبًا من جديد، وستعود مهارةَ اليوم.`) : st.mastered ? `${r.ok} من ${r.n} بلا مساعدة: أتقنت المهارة. المرة القادمة المهارة التالية في السلّم.` : `${r.ok} من ${r.n} صحيحة بلا مساعدة${r.helped ? ` (و${r.helped} بمساعدة لا تُحسب)` : ""}. الإتقان عند 8 من 10: المهارة نفسها تعود في الجلسة القادمة بمواقف جديدة.`;
      stepSummary(root, sk.title, res);
    };
    if (sk.kind === "vision") return vgRun(root, sk.ref, { count: n, onBack: backToday, onDone: done });
    const T = await skillTech(sk); if (!T) return backToday();
    return (T.kind === "rep" ? RepSession : TechniqueSession)(root, sk.ch, T, { count: n, onBack: backToday, onDone: done });
  }
  if (k === "mistakes") {
    const has = WARM.cards.length;
    if (!has) { markStep("mistakes"); return stepSummary(root, "أخطاؤك أنت", "لا مواقف من مبارياتك بعد. ستظهر بعد مبارياتك القادمة."); }
    return startWarmup({ max: 5, any: true, onBack: backToday, onDone: (r) => { markStep("mistakes"); stepSummary(root, "أخطاؤك أنت", `${r.ok} من ${r.n} صحيحة من المحاولة الأولى. المواقف التي أخطأت فيها تعود أقرب، والصحيحة تبتعد.`); } });
  }
  if (k === "game") {
    const open = J.games.filter((g) => !g.finished && g.sans && g.sans.length).sort((a, b) => b.t - a.t)[0];
    go("chapter", open ? open.chapter : sk.ch); const v = $("#v-chapter");
    if (open) { t.gameId = open.id; saveJourney(); return PlayGame(v, { n: open.chapter, resume: open, onBack: backToday }); }
    const lastCol = (J.games.filter((g) => g.finished).slice(-1)[0] || {}).color; const color = lastCol === "w" ? "b" : "w"; // colours alternate
    const G = PlayGame(v, { n: sk.ch, color, rating: J.state.settings.oppRating, onBack: backToday });
    if (G) { G.today = t.day; t.gameId = G.id; saveJourney(); }
    return;
  }
  if (k === "review") {
    const G = t.gameId && J.games.find((g) => g.id === t.gameId && g.finished) || J.games.filter((g) => g.finished && g.result !== "abandoned").slice(-1)[0];
    if (!G) { markStep("review"); return backToday(); } go("chapter", G.chapter); markStep("review"); return openReview(G.chapter, G, { onBack: backToday });
  }
}
function stepSummary(root, title, text) {
  root.innerHTML = `<div class="panel"><h3>${esc(title)}</h3><p>${esc(text)}</p><div class="row"><button class="btn" id="td-back">إلى جلسة اليوم</button></div></div>`;
  $("#td-back", root).onclick = backToday; root.scrollIntoView?.({ block: "start" });
}
/* Called when a game ends or a review opens, so the Today steps follow the real state (a game finished from the library
   counts as today's game too). */
function todaySync(G, reviewed = false) {
  const t = todayState(); if (!G || !G.finished || G.result === "abandoned") return;
  if (!t.gameId || t.gameId === G.id || !t.done.game) t.gameId = G.id;
  if (t.gameId === G.id) { if (!t.done.game) markStep("game"); if (reviewed && !t.done.review) markStep("review"); }
}
