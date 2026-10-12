"use strict";
/* Practice (optional tab): the earlier exam-style modes, their bookkeeping, hubs and statistics. */

const S = { profile: null, attempts: [], cards: {}, view: "today" };
const PROFILE0 = () => ({ created: now(), ratings: { tactics: { r: 800, n: 0 }, timed: { r: 800, n: 0 } }, rhist: [], viz: { level: 1 }, chunks: {}, guess: {}, sessions: [] });
let saveTimer = null;
function saveProfile() { clearTimeout(saveTimer); saveTimer = setTimeout(() => Store.set("coach/profile", S.profile), 400); }
const SKILL_AR = { tactics: "تكتيك", endgame: "نهايات", defence: "دفاع", strategy: "استراتيجية", calculation: "حساب", visualization: "تصور", conversion: "تحويل الأفضلية" };
const MODE_AR = { think: "التفكير بالخطوات", calc: "الحساب", viz: "التصور", guess: "خمّن النقلة", playout: "لعب الموقف", pattern: "الأنماط", timed: "تحت الوقت", review: "مراجعة", solve: "حل" };
const dueCards = () => Object.values(S.cards).filter((c) => (c.due ?? 0) <= now());

/* ---------- results ---------- */
function slimItem(it) { const { kind, id, fen, last, lastSan, sol, rating, themes, skill, note, chunkName, s, op } = it; return { kind, id, fen, last, lastSan, sol, rating, themes, skill, note, chunkName, s, op }; }
async function record(R, ctx = {}) {
  const a = { id: "a" + uid(), t: now(), ...R, mode: ctx.mode === "review" ? "review" : R.mode || ctx.mode || "solve", review: !!ctx.card, session: ctx.session || null };
  delete a.fails; if (a.fails === undefined && R.fails) a.failMoves = R.fails.map((f) => f.move);
  S.attempts.push(a); Store.set("attempts/" + a.id, a);
  const P = S.profile;
  // puzzle rating (first-try result on a rated puzzle, outside reviews)
  if (R.kind === "puzzle" && R.rating && !ctx.card && ["think", "solve", "pattern", "timed", "calc"].includes(a.mode)) {
    const key = a.mode === "timed" ? "timed" : "tactics"; const cur = P.ratings[key];
    cur.r = eloUpdate(cur.r, R.rating, R.correct ? 1 : 0, cur.n); cur.n++;
    P.rhist.push({ t: now(), k: key, r: cur.r }); if (P.rhist.length > 600) P.rhist.shift();
  }
  if (a.mode === "viz" && R.newLevel) P.viz.level = R.newLevel;
  if (a.mode === "pattern" && R.chunk && !R.learning) { const c = P.chunks[R.chunk] || (P.chunks[R.chunk] = {}); c.tests = (c.tests || 0) + 1; c.rec = (c.rec || 0) + (R.recognized ? 1 : 0); c.sol = (c.sol || 0) + (R.correct ? 1 : 0); }
  // spaced repetition: every failure becomes a card; reviews update their card
  const q = a.mode === "calc" ? (R.correct ? 4 : R.firstCorrect ? 2 : 1) : a.mode === "playout" ? (R.correct ? 4 : 1) : qualityOf({ solvedAt: R.solvedAt ?? (R.correct ? 1 : 0), confidence: R.confidence });
  if (ctx.card) { const c = S.cards[ctx.card.id]; if (c) { sm2(c, q); Store.set("cards/" + c.id, c); } }
  else if (ctx.item && q < 4 && !["viz", "guess"].includes(a.mode)) {
    const id = "c-" + (ctx.mode === "playout" ? "po-" : ctx.mode === "calc" ? "calc-" : "") + ctx.item.id;
    if (!S.cards[id]) { const c = { id, type: ctx.mode === "playout" ? "playout" : ctx.mode === "calc" ? "calc" : ctx.item.kind === "struct" ? "struct" : "solve", item: ctx.mode === "playout" ? ctx.item : slimItem(ctx.item), skill: R.skill, created: now() }; sm2(c, q); c.due = now() + 10 * 60000; S.cards[id] = c; Store.set("cards/" + id, c); }
  }
  saveProfile();
  return a;
}

/* ---------- item makers ---------- */
function thinkItem(skill) {
  const r = RATING();
  if (skill === "endgame") { const pool = Math.random() < 0.3 ? [...DATA.opposition.map(oppositionItem), ...LIB.filter((p) => p.skill === "endgame").map(libItem)] : null; if (pool) return pick(pool); return pickPuzzles(1, r, { filter: (p) => p.t.some((t) => /Endgame$/.test(t)) })[0]; }
  if (skill === "defence") { if (Math.random() < 0.25) return libItem(pick(LIB.filter((p) => p.skill === "defence"))); return pickPuzzles(1, r, { filter: (p) => p.t.includes("defensiveMove") })[0]; }
  if (skill === "strategy") { if (Math.random() < 0.4) return libItem(pick(LIB.filter((p) => p.skill === "strategy"))); return pickPuzzles(1, r, { filter: (p) => p.t.includes("quietMove") || p.t.includes("equality") })[0]; }
  return pickPuzzles(1, r, { filter: (p) => !p.t.includes("oneMove") || Math.random() < 0.3 })[0];
}
function calcItem() { return pickPuzzles(1, RATING() - 100, { filter: (p) => p.s.split(" ").length >= 5 && (p.t.includes("long") || p.t.includes("veryLong") || p.t.includes("mateIn3")) })[0]; }
function weakSkills() {
  const rec = S.attempts.slice(-120); const acc = {};
  for (const k of ["tactics", "endgame", "defence", "strategy"]) { const xs = rec.filter((a) => a.skill === k && a.correct != null); acc[k] = xs.length >= 3 ? xs.filter((a) => a.correct).length / xs.length : 0.5 - Math.random() * 0.05; }
  return Object.keys(acc).sort((a, b) => acc[a] - acc[b]);
}
function nextChunkToLearn() { return CHUNKS.find((c) => !(S.profile.chunks[c.k]?.learned) && chunkItems(c.k).length >= 5); }
function learnedChunks() { return CHUNKS.filter((c) => S.profile.chunks[c.k]?.learned).map((c) => c.k); }
function patternTestItems(n) {
  const L = learnedChunks(); if (!L.length) return [];
  const used = new Set(); const out = []; const tested = new Set(S.attempts.filter((a) => a.mode === "pattern" && !a.learning).map((a) => a.itemId));
  for (let guard = 0; out.length < n && guard < n * 6; guard++) {
    const k = L[guard % L.length === 0 ? Math.floor(Math.random() * L.length) : (guard * 7) % L.length];
    const pool = k === "iqp" ? DATA.structures.filter((s) => s.s !== "carlsbad").map(structItem) : k === "carlsbad" ? DATA.structures.filter((s) => s.s === "carlsbad" || s.s === "none").map(structItem) : chunkItems(k);
    const fresh = pool.filter((x) => !used.has(x.id) && !tested.has(x.id));
    const cand = (fresh.length ? fresh : pool.filter((x) => !used.has(x.id))).sort((a, b) => Math.abs(a.rating - RATING()) - Math.abs(b.rating - RATING())).slice(0, 6);
    const it = pick(cand); if (it) { used.add(it.id); out.push(it); }
  }
  return shuffle(out);
}
function currentGuessGame() { return DATA.masters.find((G) => (S.profile.guess[G.id]?.ply || 0) < G.sans.length) || DATA.masters[0]; }

/* ---------- task runner: one task = one mode run with a callback ---------- */
function runTask(box, task, done) {
  const fin = (R) => { record(R, { mode: task.mode, item: task.item, card: task.card, session: task.session }); done(R); };
  switch (task.mode) {
    case "think": return ThinkMode(box, task.item, fin);
    case "calc": return CalcMode(box, task.item, fin);
    case "viz": return VizMode(box, task.level || S.profile.viz.level, fin);
    case "guess": return GuessMode(box, task.game, { moves: task.moves }, fin);
    case "playout": return PlayoutMode(box, task.item, { skill: task.skill }, (R) => { if (R.retry) { record(R, { mode: "playout", item: task.item }); return runTask(box, task, done); } fin(R); });
    case "learn": return learnChunk(box, task.chunk, (R) => { done(R); });
    case "pattern": return PatternTestItem(box, task.item, learnedChunks(), fin);
    case "struct": return StructQuestion(box, task.item, {}, fin);
    case "timed": return Solver(box, task.item, { timed: timeFor(task.item.rating), ladder: false, labelHtml: `<div class="callout">تحت الوقت: ${timeFor(task.item.rating)} ثانية.</div>`, onDone: (R) => fin({ ...R, mode: "timed" }) });
    case "review": {
      const c = task.card; const it = c.item;
      const tag = `<div class="callout">مراجعة: موقف أخطأت فيه سابقًا (${SKILL_AR[c.skill] || ""}).</div>`;
      if (c.type === "playout") return PlayoutMode(box, it, { skill: 20 }, (R) => fin({ ...R, mode: "playout" }));
      if (c.type === "calc") return CalcMode(box, it, (R) => fin({ ...R, mode: "calc" }));
      if (c.type === "struct") return StructQuestion(box, it, {}, (R) => fin({ ...R, mode: "review" }));
      return Solver(box, it, { labelHtml: tag, onDone: (R) => fin({ ...R, mode: "review" }) });
    }
    default: return Solver(box, task.item, { onDone: (R) => fin({ ...R, mode: "solve" }) });
  }
}
function learnChunk(box, k, done) {
  const C = CHUNK[k]; const items = chunkItems(k).sort((a, b) => a.rating - b.rating);
  const chosen = (items.length > 5 ? [items[0], ...shuffle(items.slice(1, Math.min(items.length, 25))).slice(0, 4)] : items).sort((a, b) => a.rating - b.rating);
  let i = 0; let right = 0;
  const step = () => {
    if (i >= chosen.length) {
      const st = S.profile.chunks[k] || (S.profile.chunks[k] = {}); st.learned = true; st.learnedAt = now(); saveProfile();
      box.innerHTML = `<div class="panel"><h2>${C.ar}</h2><div class="callout good">انتهى تعلّم النمط: ${right} من ${chosen.length} من المحاولة الأولى. سيظهر الآن في الاختبارات المختلطة دون عنوان.</div><div class="row"><button class="btn" id="lc-n">التالي</button></div></div>`;
      $("#lc-n", box).onclick = () => done({ mode: "learn", chunk: k }); return;
    }
    const it = chosen[i]; const label = `<div class="chunkhead"><b>${C.ar}</b> <span class="note">· ${i + 1} من ${chosen.length}</span><p class="note">${esc(C.def)}</p></div>`;
    const next = (R) => { record({ ...R, mode: "pattern", chunk: k, recognized: true, learning: true }, { mode: "pattern", item: it }); if (R.correct) right++; i++; step(); };
    if (it.kind === "struct") StructQuestion(box, it, { labeled: true }, next);
    else Solver(box, it, { labelHtml: label, onDone: next });
  };
  step();
}

/* ---------- the daily session (mode 9): interleaved, ~45 minutes ---------- */
function buildSession() {
  const sid = "s" + uid(); const T = []; const due = dueCards().sort((a, b) => a.due - b.due);
  const weak = weakSkills(); const add = (t) => T.push({ ...t, session: sid });
  const review = () => { const c = due.shift(); if (c) add({ mode: "review", card: c, est: 2 }); };
  add({ mode: "viz", est: 4 });
  review();
  add({ mode: "think", item: thinkItem(weak[0]), est: 5 });
  const nc = nextChunkToLearn();
  if (learnedChunks().length >= 2 && (Math.random() < 0.6 || !nc)) for (const it of patternTestItems(3)) add({ mode: "pattern", item: it, est: 1.5 });
  else if (nc) add({ mode: "learn", chunk: nc.k, est: 6 });
  review();
  add({ mode: "calc", item: calcItem(), est: 7 });
  add({ mode: "think", item: thinkItem(weak[1]), est: 5 });
  for (const it of pickPuzzles(4, RATING("timed"))) add({ mode: "timed", item: it, est: 0.8 });
  review();
  add({ mode: "guess", game: currentGuessGame(), moves: 4, est: 5 });
  const po = pickPlayout(); if (po) add({ mode: "playout", item: po, skill: 20, est: 6 });
  review();
  return { id: sid, tasks: T.filter((t) => t.mode !== "think" || t.item), est: Math.round(T.reduce((s, t) => s + t.est, 0)) };
}
function pickPlayout() {
  const tried = new Set(S.attempts.filter((a) => a.mode === "playout" && a.correct).map((a) => a.itemId));
  const basics = DATA.playout.filter((p) => p.basic); const order = ["KQK", "KRK", "KPK", "Lucena", "KBBK"];
  const nb = order.map((b) => basics.find((p) => p.basic === b)).find((p) => p && !tried.has(p.i));
  return nb || pick(DATA.playout.filter((p) => !p.basic && !tried.has(p.i))) || pick(DATA.playout);
}
function runSession(sess) {
  const el = $("#pv-today"); let i = 0; const t0 = now(); const results = [];
  const step = () => {
    if (i >= sess.tasks.length) return finishSession();
    const t = sess.tasks[i];
    el.innerHTML = `<div class="sessbar"><div class="row" style="justify-content:space-between"><b>جلسة اليوم · ${i + 1} من ${sess.tasks.length} · ${MODE_AR[t.mode] || (t.mode === "learn" ? "تعلّم نمط" : t.mode)}</b><button class="btn quiet" id="ss-stop">إنهاء الجلسة</button></div><div class="progress"><i style="width:${(100 * i / sess.tasks.length).toFixed(1)}%"></i></div></div><div id="ss-box"></div>`;
    $("#ss-stop", el).onclick = finishSession;
    runTask($("#ss-box", el), t, (R) => { results.push({ mode: t.mode, correct: R.correct }); i++; step(); window.scrollTo?.(0, 0); });
  };
  function finishSession() {
    const min = Math.round((now() - t0) / 60000); const scored = results.filter((r) => r.correct != null);
    S.profile.sessions.push({ t: t0, min, n: results.length, acc: scored.length ? Math.round(100 * scored.filter((r) => r.correct).length / scored.length) : null }); saveProfile();
    el.innerHTML = `<div class="panel"><h2>انتهت الجلسة</h2><p>${results.length} مهمة في ${min} دقيقة. صحيح: ${scored.filter((r) => r.correct).length} من ${scored.length}.</p><p class="note">كل ما أخطأت فيه أصبح بطاقة مراجعة وسيعود إليك حسب جدول التكرار المتباعد.</p><div class="row"><button class="btn" data-go="progress">انظر التقدم</button><button class="btn quiet" data-go="today">عودة</button></div></div>`;
    wireGo(el);
  }
  step();
}

/* ---------- loops for single-mode practice ---------- */
function runLoop(view, title, makeTask) {
  const el = $("#pv-" + view); let n = 0, right = 0;
  const step = () => {
    const t = makeTask(n);
    if (!t) {
      el.innerHTML = n ? `<div class="panel"><h2>${title}: انتهى</h2><p>صحيح ${right} من ${n}.</p><p class="note">ما أخطأت فيه أصبح بطاقة مراجعة.</p><div class="row"><button class="btn" data-go="${view}">عودة</button><button class="btn quiet" data-go="progress">التقدم</button></div></div>`
        : `<div class="panel"><p class="empty">${view === "train" && title === "مراجعة" ? "لا توجد مراجعات مستحقة الآن. ستعود الأخطاء حسب جدولها." : "لا توجد مواد متاحة الآن لهذا التدريب."}</p><div class="row"><button class="btn" data-go="${view}">عودة</button></div></div>`;
      wireGo(el); return;
    }
    el.innerHTML = `<div class="sessbar"><div class="row" style="justify-content:space-between"><b>${title} · ${n + 1}</b><span class="note">${n ? `صحيح ${right} من ${n}` : ""}</span><button class="btn quiet" id="lp-stop">إنهاء</button></div></div><div id="lp-box"></div>`;
    $("#lp-stop", el).onclick = () => pshow(view);
    runTask($("#lp-box", el), t, (R) => { n++; if (R.correct) right++; step(); window.scrollTo?.(0, 0); });
  };
  step();
}

/* ---------- views ---------- */
function pshow(view) {
  S.view = view;
  for (const b of $$("#pnav button")) { if (b.dataset.pview === view) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current"); }
  for (const [v] of PVIEWS) { const el = $("#pv-" + v); if (el) el.hidden = v !== view; }
  ({ today: renderToday, train: renderTrain, patterns: renderPatterns, progress: renderProgress })[view]();
  try { localStorage.setItem("cc:pview", view); } catch {}
}
function wireGo(el) { for (const b of $$("[data-go]", el)) b.onclick = (e) => { e.preventDefault(); pshow(b.dataset.go); }; }
const kpi = (v, l) => `<div class="kpi"><b>${esc(v)}</b><span>${esc(l)}</span></div>`;

function renderToday() {
  const el = $("#pv-today"); const P = S.profile; const due = dueCards().length; const A = S.attempts;
  const sess = P.sessions.length; const lastS = P.sessions[sess - 1];
  const weak = weakSkills();
  el.innerHTML = `
    <div class="hero panel"><div><h2>جلسة اليوم</h2>
      <p class="lead">حوالي 45 دقيقة، مختلطة: تصوّر، تفكير بالخطوات، أنماط، حساب، قرارات تحت الوقت، مباراة أستاذ، تحويل موقف رابح، ومراجعة أخطائك. لا كتابة: كل إجابة نقرة.</p>
      <div class="row"><button class="btn big" id="td-start">ابدأ الجلسة</button><span class="note">${due ? `${due} مراجعة مستحقة ستدخل الجلسة` : "لا مراجعات مستحقة الآن"}</span></div></div></div>
    <div class="kpis">${kpi(P.ratings.tactics.r, "تصنيف التكتيك في التدريب")}${kpi(P.ratings.timed.r, "تصنيف القرار تحت الوقت")}${kpi(A.length, "مهام أنجزتها")}${kpi(sess, "جلسات")}${kpi(due + " / " + Object.keys(S.cards).length, "مراجعات مستحقة / كل البطاقات")}</div>
    ${A.length >= 10 ? `<div class="panel"><h3>ما تركّز عليه الجلسة</h3><p>أضعف مهارتين حسب نتائجك الأخيرة: <b>${SKILL_AR[weak[0]]}</b> و<b>${SKILL_AR[weak[1]]}</b>. مواقف التفكير بالخطوات تُختار منهما.</p></div>` : `<div class="panel"><h3>البداية</h3><p class="lead">في الجلسات الأولى نقيس مستواك في كل مهارة. بعد حوالي 10 مهام تبدأ الجلسة بالتركيز على أضعف مهاراتك.</p></div>`}
    ${lastS ? `<p class="note">آخر جلسة: ${new Date(lastS.t).toISOString().slice(0, 10)}، ${lastS.n} مهام في ${lastS.min} دقيقة${lastS.acc != null ? `، دقة ${lastS.acc}%` : ""}.</p>` : ""}`;
  $("#td-start", el).onclick = () => runSession(buildSession());
}

function renderTrain() {
  const el = $("#pv-train"); const due = dueCards().length;
  const cards = [
    ["think", "التفكير بالخطوات", "التهديد، المرشحات، الاختيار، فحص الخطأ، التقييم. خطوة خطوة بالنقر، ثم نقد طريقة تفكيرك.", "1, 7, 10"],
    ["calc", "الحساب", "أدخل شجرة المرشحات بالنقر بدون أن تتحرك القطع، ثم قارنها بشجرة Stockfish.", "2"],
    ["viz", "التصور واللعب الأعمى", `المستوى الحالي ${S.profile.viz.level}: ${VIZ_LEVELS[S.profile.viz.level].ar}.`, "3"],
    ["guess", "خمّن نقلة الأستاذ", "مباريات كلاسيكية. توقّع النقلة وسببها، ثم قارن.", "4"],
    ["playout", "لعب الموقف حتى الفوز", "مواقف رابحة ضد Stockfish: هل تعرف كيف تحوّلها؟", "5"],
    ["timed", "قرارات تحت الوقت", "8 مواقف بساعة. نقارن دقتك بوقت وبدون وقت.", "12"],
    ["review", "مراجعة أخطائك", `${due} مستحقة الآن. التكرار المتباعد (SM-2).`, "11"],
  ];
  el.innerHTML = `<div class="panel"><h2>تدريب حر</h2><p class="lead">الجلسة اليومية تخلط كل هذا تلقائيًا. هنا تتدرب على وضع واحد عندما تريد.</p></div>
    <div class="modegrid">${cards.map(([k, t, d, n]) => `<button class="modecard" data-m="${k}"><span class="n mono">${n}</span><b>${t}</b><span class="note">${d}</span></button>`).join("")}</div><div id="tr-sub"></div>`;
  for (const b of $$("[data-m]", el)) b.onclick = () => startMode(b.dataset.m);
}
function startMode(m) {
  const sub = $("#tr-sub");
  if (m === "think") return runLoop("train", "التفكير بالخطوات", () => ({ mode: "think", item: thinkItem(pick(["tactics", "tactics", "endgame", "defence", "strategy"])) }));
  if (m === "calc") return runLoop("train", "الحساب", () => ({ mode: "calc", item: calcItem() }));
  if (m === "viz") return runLoop("train", "التصور", () => ({ mode: "viz" }));
  if (m === "timed") { let k = 0; const items = pickPuzzles(8, RATING("timed")); return runLoop("train", "تحت الوقت", () => items[k] ? { mode: "timed", item: items[k++] } : null); }
  if (m === "review") { return runLoop("train", "مراجعة", () => { const c = dueCards().sort((a, b) => a.due - b.due)[0]; return c ? { mode: "review", card: c } : null; }); }
  if (m === "guess") {
    sub.innerHTML = `<div class="panel"><h3>اختر مباراة</h3><div class="tbl"><table><thead><tr><th>المباراة</th><th>الفكرة</th><th>تلعب بـ</th><th>التقدم</th><th></th></tr></thead><tbody>${DATA.masters.map((G) => { const p = S.profile.guess[G.id]; return `<tr><td><b>${esc(G.white)} – ${esc(G.black)}</b><div class="note">${esc(G.event)}</div></td><td class="mono">${esc(G.concept)}</td><td>${G.side === "w" ? "الأبيض" : "الأسود"}</td><td class="num">${p ? Math.round(100 * Math.min(p.ply, G.sans.length) / G.sans.length) + "%" : "–"}</td><td><button class="btn quiet" data-g="${G.id}">العب</button></td></tr>`; }).join("")}</tbody></table></div></div>`;
    for (const b of $$("[data-g]", sub)) b.onclick = () => { const G = DATA.masters.find((x) => x.id === b.dataset.g); runLoopOnce("train", "خمّن النقلة", { mode: "guess", game: G }); };
    return;
  }
  if (m === "playout") {
    const tried = {}; for (const a of S.attempts.filter((a) => a.mode === "playout")) { const t = tried[a.itemId] || (tried[a.itemId] = { n: 0, w: 0 }); t.n++; if (a.correct) t.w++; }
    const rows = [...DATA.playout.filter((p) => p.basic), ...DATA.playout.filter((p) => !p.basic).slice(0, 18)];
    sub.innerHTML = `<div class="panel"><h3>اختر موقفًا</h3><label class="f">قوة الخصم (Stockfish Skill Level): <span id="po-sk">20</span><input type="range" id="po-skill" min="0" max="20" value="20"></label>
      <div class="tbl"><table><thead><tr><th>الموقف</th><th>التقييم</th><th>محاولات</th><th></th></tr></thead><tbody>${rows.map((p) => `<tr><td>${p.basic ? `<b>${PLAYOUT_AR[p.basic]}</b>` : `موقف رابح من مباراة (${p.phase === "endgame" ? "نهاية" : "وسط اللعب"})`}</td><td class="num">${fmtEval(p.cp)}</td><td class="num">${tried[p.i] ? tried[p.i].w + "/" + tried[p.i].n : "–"}</td><td><button class="btn quiet" data-p="${p.i}">العب</button></td></tr>`).join("")}</tbody></table></div></div>`;
    const sk = $("#po-skill", sub); sk.oninput = () => { $("#po-sk", sub).textContent = sk.value; };
    for (const b of $$("[data-p]", sub)) b.onclick = () => runLoopOnce("train", "لعب الموقف", { mode: "playout", item: DATA.playout.find((p) => p.i === b.dataset.p), skill: +sk.value });
  }
}
function runLoopOnce(view, title, task) { let used = false; runLoop(view, title, () => (used ? null : ((used = true), task))); }

function renderPatterns() {
  const el = $("#pv-patterns"); const P = S.profile; const L = learnedChunks();
  const groups = [...new Set(CHUNKS.map((c) => c.g))];
  el.innerHTML = `<div class="panel"><h2>الأنماط بأسمائها</h2><p class="lead">الأساتذة يرون المواقف كـ"قطع" مألوفة (de Groot، Chase & Simon). تعلّم كل نمط على 5 مواقف بعنوانه، ثم يظهر في اختبارات مختلطة بلا عنوان: تحدد النمط أولًا، ثم تحل.</p>
    <div class="row"><button class="btn" id="pt-test" ${L.length >= 2 ? "" : "disabled"}>اختبار مختلط (8 مواقف)</button><span class="note">${L.length >= 2 ? `من ${L.length} أنماط تعلّمتها` : "تعلّم نمطين على الأقل أولًا"}</span></div></div>
    ${groups.map((g) => `<div class="panel"><h3>${GROUP_AR[g]}</h3><div class="chunkgrid">${CHUNKS.filter((c) => c.g === g).map((c) => { const st = P.chunks[c.k] || {}; const n = chunkItems(c.k).length; const m = st.tests ? Math.round(100 * (st.rec + st.sol) / (2 * st.tests)) : null;
      return `<div class="chunk ${st.learned ? "learned" : ""}"><div class="row" style="justify-content:space-between"><b>${c.ar}</b>${st.learned ? `<span class="state on">${m == null ? "تعلّمته" : "إتقان " + m + "%"}</span>` : ""}</div><p class="note">${esc(c.def)}</p><div class="row"><button class="btn quiet" data-l="${c.k}" ${n >= 5 ? "" : "disabled"}>${st.learned ? "أعد التعلّم" : "تعلّم"} (${Math.min(5, n)} مواقف)</button><span class="note">${n} موقف متاح</span></div></div>`; }).join("")}</div></div>`).join("")}`;
  for (const b of $$("[data-l]", el)) b.onclick = () => { const k = b.dataset.l; el.innerHTML = `<div id="pt-box"></div>`; learnChunk($("#pt-box", el), k, () => pshow("patterns")); };
  const t = $("#pt-test", el); t.onclick = () => { const items = patternTestItems(8); let k = 0; runLoop("patterns", "اختبار الأنماط", () => (items[k] ? { mode: items[k].kind === "struct" ? "struct" : "pattern", item: items[k++] } : null)); };
}

/* ---------- dashboard ---------- */
function barChart(rows, unit = "") {
  if (!rows.length) return `<p class="empty">لا توجد بيانات بعد.</p>`;
  const W = 640, rowH = 28, labelW = 200, gutter = 84, H = rows.length * rowH + 10; const max = Math.max(...rows.map((r) => r.value), 1);
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px;min-width:400px;direction:ltr" role="img">${rows.map((r, i) => { const y = i * rowH + 4; const w = (W - labelW - gutter) * r.value / max;
    return `<text x="${W - 4}" y="${y + 16}" text-anchor="end" class="lbl">${esc(r.label)}</text><rect class="bar" x="${W - labelW - w}" y="${y + 4}" width="${Math.max(1, w)}" height="16" rx="3"></rect><text x="${W - labelW - w - 6}" y="${y + 16}" text-anchor="end">${r.value}${unit}${r.n != null ? " · n=" + r.n : ""}</text>`; }).join("")}</svg>`;
}
function lineChart(pts, { yMin, yMax, fmt = (v) => v, ref = null, w = 640, h = 200 } = {}) {
  if (pts.length < 2) return `<p class="empty">يظهر بعد نقطتين على الأقل.</p>`;
  const pad = { l: 46, r: 14, t: 12, b: 26 };
  const lo = yMin ?? Math.min(...pts.map((p) => p.y)), hi = yMax ?? Math.max(...pts.map((p) => p.y)); const span = hi - lo || 1;
  const X = (i) => pad.l + (w - pad.l - pad.r) * i / (pts.length - 1), Y = (v) => pad.t + (h - pad.t - pad.b) * (1 - (v - lo) / span);
  const d = pts.map((p, i) => `${i ? "L" : "M"}${X(i).toFixed(1)},${Y(p.y).toFixed(1)}`).join("");
  return `<svg viewBox="0 0 ${w} ${h}" width="100%" style="max-width:${w}px;min-width:400px;direction:ltr" role="img">
    ${[lo, lo + span / 2, hi].map((t) => `<line class="ax" x1="${pad.l}" x2="${w - pad.r}" y1="${Y(t)}" y2="${Y(t)}"></line><text x="${pad.l - 6}" y="${Y(t) + 4}" text-anchor="end">${fmt(Math.round(t))}</text>`).join("")}
    ${ref != null ? `<line class="ref" x1="${pad.l}" x2="${w - pad.r}" y1="${Y(ref)}" y2="${Y(ref)}"></line>` : ""}
    <path class="area" d="${d}L${X(pts.length - 1).toFixed(1)},${Y(lo)}L${X(0)},${Y(lo)}Z"></path><path class="ln" d="${d}"></path>
    <circle class="pt" cx="${X(pts.length - 1)}" cy="${Y(pts[pts.length - 1].y)}" r="4"></circle>
    <text x="${pad.l}" y="${h - 6}">${esc(pts[0].label || "")}</text><text x="${w - pad.r}" y="${h - 6}" text-anchor="end">${esc(pts[pts.length - 1].label || "")}</text></svg>`;
}
function calibrationChart(att) {
  const bins = [1, 2, 3, 4, 5].map((c) => { const xs = att.filter((a) => a.confidence === c); return { c, n: xs.length, acc: xs.length ? 100 * xs.filter((a) => a.correct).length / xs.length : null }; });
  const w = 420, h = 260, pad = { l: 44, r: 14, t: 12, b: 34 };
  const X = (c) => pad.l + (w - pad.l - pad.r) * (c - 1) / 4, Y = (v) => pad.t + (h - pad.t - pad.b) * (1 - v / 100);
  const exp = (c) => (c - 0.5) * 20; const pts = bins.filter((b) => b.acc != null);
  return `<svg viewBox="0 0 ${w} ${h}" width="100%" style="max-width:${w}px;direction:ltr" role="img">
    ${[0, 50, 100].map((t) => `<line class="ax" x1="${pad.l}" x2="${w - pad.r}" y1="${Y(t)}" y2="${Y(t)}"></line><text x="${pad.l - 6}" y="${Y(t) + 4}" text-anchor="end">${t}%</text>`).join("")}
    ${[1, 2, 3, 4, 5].map((c) => `<text x="${X(c)}" y="${h - 14}" text-anchor="middle">${c}</text>`).join("")}<text x="${(w + pad.l) / 2}" y="${h - 1}" text-anchor="middle">confidence</text>
    <path class="ref" d="M${X(1)},${Y(exp(1))}L${X(5)},${Y(exp(5))}"></path>
    ${pts.length > 1 ? `<path class="ln" d="${pts.map((b, i) => `${i ? "L" : "M"}${X(b.c)},${Y(b.acc)}`).join("")}"></path>` : ""}
    ${pts.map((b) => `<circle class="pt" cx="${X(b.c)}" cy="${Y(b.acc)}" r="${3 + Math.min(6, Math.sqrt(b.n) * 1.5)}"></circle><text x="${b.c === 5 ? X(b.c) - 8 : X(b.c) + 8}" y="${Y(b.acc) + (b.acc > 90 ? 18 : -8)}" text-anchor="${b.c === 5 ? "end" : "start"}">n=${b.n}</text>`).join("")}</svg>`;
}
const accOf = (xs) => (xs.length ? Math.round(100 * xs.filter((a) => a.correct).length / xs.length) : null);
function renderProgress() {
  const el = $("#pv-progress"); const A = S.attempts.slice().sort((a, b) => a.t - b.t); const P = S.profile;
  const withConf = A.filter((a) => a.confidence && a.correct != null && !a.learning);
  const calGap = withConf.length ? Math.round(withConf.reduce((s, a) => s + (a.confidence - 0.5) * 20, 0) / withConf.length - accOf(withConf)) : null;
  const bySkill = Object.keys(SKILL_AR).map((k) => { const xs = A.filter((a) => a.skill === k && a.correct != null && !a.review); return { label: SKILL_AR[k], value: accOf(xs) ?? 0, n: xs.length }; }).filter((r) => r.n);
  const byMode = Object.keys(MODE_AR).map((k) => { const xs = A.filter((a) => a.mode === k && a.correct != null); return { label: MODE_AR[k], value: accOf(xs) ?? 0, n: xs.length }; }).filter((r) => r.n);
  const think = A.filter((a) => a.mode === "think" && a.scores);
  const steps = Object.keys(CHECK_AR).map((k) => { const xs = think.filter((a) => a.scores[k] != null); return { label: CHECK_AR[k], value: xs.length ? Math.round(50 * xs.reduce((s, a) => s + a.scores[k], 0) / xs.length) : 0, n: xs.length }; }).filter((r) => r.n);
  const calc = A.filter((a) => a.mode === "calc" && a.depth != null);
  const calcTrend = calc.map((a, i) => { const w = calc.slice(Math.max(0, i - 4), i + 1); return { y: w.reduce((s, x) => s + x.depth, 0) / w.length, label: new Date(a.t).toISOString().slice(5, 10) }; });
  const timed = A.filter((a) => a.mode === "timed"); const untimed = A.filter((a) => a.kind === "puzzle" && ["solve", "think", "pattern"].includes(a.mode) && !a.learning);
  const gap = timed.length >= 4 && untimed.length >= 4 ? accOf(untimed) - accOf(timed) : null;
  const viz = A.filter((a) => a.mode === "viz");
  const rh = (k) => P.rhist.filter((x) => x.k === k).map((x) => ({ y: x.r, label: new Date(x.t).toISOString().slice(5, 10) }));
  const cards = Object.values(S.cards); const due = dueCards();
  const chunkRows = CHUNKS.filter((c) => P.chunks[c.k]?.learned).map((c) => { const st = P.chunks[c.k]; return `<tr><td>${c.ar}</td><td class="num">${st.tests || 0}</td><td class="num">${st.tests ? Math.round(100 * st.rec / st.tests) + "%" : "–"}</td><td class="num">${st.tests ? Math.round(100 * st.sol / st.tests) + "%" : "–"}</td></tr>`; }).join("");
  el.innerHTML = `
  <div class="kpis">${kpi(P.ratings.tactics.r, "تصنيف التكتيك")}${kpi(A.length, "مهام")}${kpi(calGap == null ? "–" : (calGap > 0 ? "+" : "") + calGap, "فجوة الثقة (موجب = ثقة زائدة)")}${kpi(calc.length ? (calc.reduce((s, a) => s + a.depth, 0) / calc.length).toFixed(1) : "–", "متوسط عمق الحساب الصحيح (نقلات)")}${kpi(gap == null ? "–" : (gap > 0 ? "-" : "+") + Math.abs(gap) + "%", "الفرق تحت الوقت")}${kpi(due.length + " / " + cards.length, "مراجعات مستحقة / الكل")}</div>
  <div class="panel"><h2>تصنيف التكتيك عبر الزمن</h2><p class="note">يتغير بعد كل لغز مصنَّف من قاعدة Lichess (نظام Elo بسيط). يبدأ من 800.</p><div class="chart">${lineChart(rh("tactics"))}</div></div>
  <div class="cols">
    <div class="panel"><h2>منحنى المعايرة</h2><p class="note">الخط المتقطع = معايرة مثالية. نقطة تحت الخط = ثقة زائدة عند هذا المستوى.</p><div class="chart">${withConf.length ? calibrationChart(withConf) : `<p class="empty">يظهر بعد أول إجابة.</p>`}</div>
      ${calGap != null && withConf.length >= 10 ? `<p>${calGap > 10 ? `<b>ثقة زائدة</b>: ثقتك أعلى من دقتك بـ ${calGap} نقطة.` : calGap < -10 ? `<b>ثقة ناقصة</b> بـ ${-calGap} نقطة.` : "معايرتك قريبة من الواقع."}</p>` : withConf.length ? `<p class="note">الحكم يحتاج 10 إجابات على الأقل (لديك ${withConf.length}).</p>` : ""}</div>
    <div class="panel"><h2>الدقة حسب المهارة</h2><p class="note">صحيح من المحاولة الأولى، بدون المراجعات.</p><div class="chart">${barChart(bySkill, "%")}</div></div>
  </div>
  <div class="cols">
    <div class="panel"><h2>جودة خطوات التفكير</h2><p class="note">من وضع التفكير بالخطوات (0 إلى 100%).</p><div class="chart">${barChart(steps, "%")}</div></div>
    <div class="panel"><h2>الدقة حسب الوضع</h2><div class="chart">${barChart(byMode, "%")}</div></div>
  </div>
  <div class="cols">
    <div class="panel"><h2>عمق الحساب</h2><p class="note">عدد النقلات الصحيحة في خطك الرئيسي، متوسط متحرك لآخر 5.</p><div class="chart">${lineChart(calcTrend, { yMin: 0 })}</div></div>
    <div class="panel"><h2>بوقت وبدون وقت</h2>${gap == null ? `<p class="empty">يحتاج 4 مواقف بوقت و4 بدون وقت على الأقل.</p>` : `<p>بدون وقت: <b>${accOf(untimed)}%</b> (n=${untimed.length}) · تحت الوقت: <b>${accOf(timed)}%</b> (n=${timed.length}).</p><p>${gap > 10 ? "دقتك تنهار تحت الوقت. القرار السريع يحتاج أنماطًا محفوظة: تدرّب على الأنماط أكثر." : "الفرق صغير."}</p>`}
      <h3>التصور</h3><p>المستوى الحالي: <b>${P.viz.level}</b> (${VIZ_LEVELS[P.viz.level].ar}). آخر الجولات: ${viz.slice(-6).map((a) => a.acc + "%").join("، ") || "–"}</p></div>
  </div>
  <div class="panel"><h2>إتقان الأنماط</h2>${chunkRows ? `<div class="tbl"><table><thead><tr><th>النمط</th><th>اختبارات</th><th>تعرّف صحيح</th><th>حل صحيح</th></tr></thead><tbody>${chunkRows}</tbody></table></div>` : `<p class="empty">لم تتعلم أنماطًا بعد.</p>`}</div>
  <div class="panel"><h2>جدول المراجعة</h2>${cards.length ? `<div class="tbl"><table><thead><tr><th>النوع</th><th>المهارة</th><th>تكرارات ناجحة</th><th>الفاصل</th><th>الموعد</th></tr></thead><tbody>${cards.sort((a, b) => a.due - b.due).slice(0, 25).map((c) => `<tr><td>${({ solve: "موقف", calc: "حساب", playout: "تحويل", struct: "بنية" })[c.type] || c.type}</td><td>${SKILL_AR[c.skill] || ""}</td><td class="num">${c.reps || 0}</td><td class="num">${c.interval || 0}d</td><td class="num">${c.due <= now() ? "الآن" : new Date(c.due).toISOString().slice(0, 10)}</td></tr>`).join("")}</tbody></table></div>` : `<p class="empty">لا بطاقات بعد. كل خطأ يصبح بطاقة.</p>`}</div>`;
}

/* ---------- entry points used by the app shell ---------- */
const PVIEWS = [["today", "جلسة مختلطة"], ["train", "تمارين"], ["patterns", "الأنماط"], ["progress", "إحصاءات التمرين"]];
async function practiceInit() {
  try {
    S.profile = Object.assign(PROFILE0(), (await Store.get("coach/profile")) || {});
    for (const k of ["tactics", "timed"]) S.profile.ratings[k] = S.profile.ratings[k] || { r: 800, n: 0 };
    S.attempts = await Store.list("attempts");
    for (const c of await Store.list("cards")) if (!c.kind || c.kind === "practice") S.cards[c.id] = c;
  } catch (e) { console.error(e); S.profile = S.profile || PROFILE0(); }
}
function renderPractice() {
  const root = $("#v-practice");
  root.innerHTML = `<div class="panel"><h2>التمرين</h2><p class="lead">أدوات اختيارية: ألغاز، حساب، تصوّر، أنماط، وقرارات تحت الوقت. الرحلة لا تحتاجها، لكنها مفيدة للتكرار.</p>
    <nav class="subnav" id="pnav">${PVIEWS.map(([k, t]) => `<button data-pview="${k}">${t}</button>`).join("")}</nav></div>
    ${PVIEWS.map(([k]) => `<section id="pv-${k}" hidden></section>`).join("")}`;
  for (const b of $$("#pnav button", root)) b.onclick = () => pshow(b.dataset.pview);
  if (!DATA.puzzles.length) { $("#pv-today").innerHTML = `<div class="panel"><p class="err">تعذّر تحميل ملفات التمرين (data/*.json).</p></div>`; }
  let first = "train"; try { first = localStorage.getItem("cc:pview") || "train"; } catch {}
  pshow(PVIEWS.some(([k]) => k === first) ? first : "train");
}
