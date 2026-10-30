"use strict";
/* Journey: the chapter map, chapter pages, stage cards, and the journey state (db doc journey/state). */

const CUR = { parts: [], chapters: [] };
const J = { state: null, games: [] };
const STAGES = [
  { k: "learn", ar: "تعلّم", letter: "A", what: "درس قصير على رقعة تفاعلية، وفي آخره قائمة «بماذا أفكر»." },
  { k: "watch", ar: "شاهد", letter: "B", what: "ألعب مباراة كاملة وأشرح كل نقلة. توقف متى شئت، واسأل، وجرّب «ماذا لو؟»." },
  { k: "drill", ar: "مواقف", letter: "C", what: "مواقف بلا نهاية على موضوع الفصل، أغلبها من مباريات حقيقية. تلعبها كالمحرك: مرشحات، ثم اختيار، ثم مقارنة بـ Stockfish." },
  { k: "play", ar: "العب", letter: "D", what: "تلعب مباراة كاملة وأنا بجانبك أعلّق على كل نقلة." },
  { k: "review", ar: "راجع", letter: "E", what: "بعد المباراة: اللحظات الحاسمة، ما أحسنت فيه، ما تعمل عليه، ودرس واحد." },
];
const pad2 = (n) => String(n).padStart(2, "0");
const J0 = () => ({ v: 1, created: now(), ch: {}, settings: { commentary: "every", odds: "human", oppRating: 1100 } });
function chState(n) { const ch = J.state.ch; return ch[n] || (ch[n] = { learn: {}, watch: { seen: [] }, play: {}, review: {}, completedAt: null }); }
let jSaveT = null;
function saveJourney() { clearTimeout(jSaveT); jSaveT = setTimeout(() => Store.set("journey/state", J.state), 300); }

async function loadCurriculum() {
  const r = await fetch("data/curriculum/chapters.json"); const d = await r.json();
  CUR.parts = d.parts; CUR.chapters = d.chapters;
}
async function journeyInit() {
  try { J.state = Object.assign(J0(), (await Store.get("journey/state")) || {}); } catch { J.state = J0(); }
  J.state.settings = Object.assign(J0().settings, J.state.settings || {});
  Prob.band = J.state.settings.oppRating; // the opponent's level follows results, so it is also the student's estimated level
  try { J.games = (await Store.list("games")).sort((a, b) => a.t - b.t); } catch { J.games = []; }
}
const chapter = (n) => CUR.chapters.find((c) => c.n === n);
function chapterStatus(n) {
  const s = J.state.ch[n]; if (s && s.completedAt) return "done";
  if (s && s.unlocked) return "open"; // opened early by the student's choice
  if (n === 1 || (J.state.ch[n - 1] && J.state.ch[n - 1].completedAt)) return "open";
  return "locked";
}
function currentChapterN() { for (const c of CUR.chapters) if (chapterStatus(c.n) === "open") return c.n; return CUR.chapters.length; }
const content = (c) => c.content || {};
function stageReady(c, k) {
  const ct = content(c);
  if (k === "learn") return !!ct.learn;
  if (k === "watch") return !!(ct.watch && ct.watch.length);
  if (k === "drill") return !!(ct.drill && ct.drill.pools.length);
  if (k === "play") return !!ct.play;
  if (k === "review") return !!ct.play;
  return false;
}
function stageDone(n, k) {
  const s = chState(n);
  if (k === "learn") return !!s.learn.done;
  if (k === "watch") return !!s.watch.done;
  if (k === "drill") return ((s.drill && s.drill.count) || 0) >= 10;
  if (k === "play") return chapterGames(n).length > 0;
  if (k === "review") return !!s.review.count;
  return false;
}
const chapterGames = (n) => J.games.filter((g) => g.chapter === n && g.finished);
/* A game counts toward a chapter's completion rule if it reached a result, or was stopped after 20 or more of your moves. */
const countsForChapter = (g) => g.finished && (g.result !== "abandoned" || ((g.metrics && g.metrics.moves) || 0) >= 20);
const countedGames = (n) => chapterGames(n).filter(countsForChapter);
function nextStage(n) { const c = chapter(n); for (const st of STAGES) if (!stageDone(n, st.k)) return st; return STAGES[2]; }

const safetyOk = (m) => !!m && (m.hanging ?? 9) <= 1 && (m.missedThreats ?? 9) <= 1;
const safetyJudged = (m) => !!m && (m.moves >= 15 || !safetyOk(m));
function safetyVerdictText(m, g) {
  if (!m) return "";
  const t = `قطع تركتها معلّقة: ${m.hanging}، تهديدات فاتتك: ${m.missedThreats} (المسموح 1 لكل منهما).`;
  if (g && !countsForChapter(g)) return safetyOk(m) ? `${t} المباراة لم تكتمل، فلا تُحسب لصالحك.` : `${t} المباراة لم تكتمل، لكن تجاوز الحد فيها يقطع السلسلة.`;
  if (!safetyJudged(m)) return `${t} المباراة أقصر من 15 نقلة لك، فلا تُحسب في السلسلة ولا تقطعها.`;
  return safetyOk(m) ? `${t} مباراة مؤهلة لشرط الفصل.` : `${t} ليست مؤهلة: السلسلة تبدأ من جديد.`;
}
/* Completion rules: evaluated only from coached-game data. Each returns {met, have, need, text}. */
function ruleProgress(c) {
  const r = c.rule || {}; const games = countedGames(c.n);
  if (r.kind === "opening_checklist") {
    // a game that ended before your 10th move cannot be judged on the checklist: it neither counts nor takes a slot
    const judged = games.filter((g) => g.metrics && g.metrics.openingScore != null);
    const last = judged.slice(-r.window); const ok = last.filter((g) => g.metrics.openingScore >= 4 && !g.metrics.openingBlunder).length;
    return { met: last.length >= r.window && ok >= r.need, have: ok, need: r.need, unit: "مباريات مؤهلة من آخر " + r.window };
  }
  if (r.kind === "mates") { // 2 basic mates of each kind from random positions, within the move limit, no stalemate
    const ms = (chState(c.n).drill || { mates: [] }).mates || [];
    const q = Math.min(2, ms.filter((x) => x.kind === "kqk" && x.ok && x.moves <= 10).length), rk = Math.min(2, ms.filter((x) => x.kind === "krk" && x.ok && x.moves <= 20).length);
    return { met: q + rk >= 4, have: q + rk, need: 4, unit: `كش ناجح (وزير ${q}/2، رخ ${rk}/2)` };
  }
  if (r.kind === "structure_quality") { // 30+ of your moves in recognised structures across the chapter's games, average drop 3 or less
    const ms = games.map((g) => g.metrics || {}).filter((m) => m.stN); const n = ms.reduce((a, m) => a + m.stN, 0);
    const avg = n ? ms.reduce((a, m) => a + m.stN * m.stDrop, 0) / n : null;
    return { met: n >= r.need && avg <= 3, have: Math.min(n, r.need), need: r.need, unit: `نقلة في بنى معروفة${avg != null ? ` · متوسط خسارتك ${avg.toFixed(1)} (الحد 3)` : ""}` };
  }
  if (r.kind === "middlegame_quality") { // moves 11-30: average drop at most 3 points in each of the last 3 judged games, and safe
    const judged = games.filter((g) => g.metrics && g.metrics.mgN >= 10); const last = judged.slice(-r.window);
    const ok = last.filter((g) => g.metrics.mgDrop <= 3 && safetyOk(g.metrics)).length;
    return { met: last.length >= r.window && ok >= r.need, have: ok, need: r.need, unit: `مباريات مؤهلة من آخر ${r.window} (متوسط الخسارة في النقلات 11 إلى 30 ≤ 3 نقاط${last.length ? `؛ آخرها ${last[last.length - 1].metrics.mgDrop}` : ""})` };
  }
  if (r.kind === "tactics") { // tactical chances = opponent errors that gave you 10+ points; used = you kept them
    const ms = games.map((g) => g.metrics || {}); const chances = ms.reduce((a, m) => a + (m.gifts || 0), 0), used = ms.reduce((a, m) => a + (m.punished || 0), 0);
    const last = games[games.length - 1]; const safe = !!last && safetyOk(last.metrics);
    const need = Math.max(3, Math.ceil(0.6 * Math.max(r.need, chances)));
    return { met: chances >= r.need && used >= 0.6 * chances && safe, have: Math.min(used, need), need, unit: `فرصة استغليتها من ${chances}${chances < r.need ? ` (يلزم ${r.need} فرص على الأقل)` : ""}${last && !safe ? " · آخر مباراة تجاوزت حد الأمان" : ""}` };
  }
  if (r.kind === "safety") {
    // judged after 15 of your moves; a shorter game counts only when it already broke a limit (it can fail, never pass).
    // An unfinished game you ended early never counts for you, but one that broke a limit still breaks the streak.
    const judged = chapterGames(c.n).filter((g) => g.finished && safetyJudged(g.metrics) && (countsForChapter(g) || !safetyOk(g.metrics)));
    let streak = 0; for (let i = judged.length - 1; i >= 0; i--) { if (safetyOk(judged[i].metrics)) streak++; else break; }
    return { met: streak >= r.need, have: Math.min(streak, r.need), need: r.need, unit: "مباريات متتالية" };
  }
  const n = games.length;
  return { met: false, have: 0, need: r.need || r.window || 3, unit: "", pending: true, games: n };
}

/* ---------- the map ---------- */
const ICON = {
  lock: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10V8a5 5 0 0 1 10 0v2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><rect x="5" y="10" width="14" height="10" rx="2" fill="currentColor"/></svg>`,
  check: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  drill: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M4 12h16M12 4v16" stroke="currentColor" stroke-width="1.4"/><rect x="4" y="4" width="8" height="8" fill="currentColor" opacity=".35"/><rect x="12" y="12" width="8" height="8" fill="currentColor" opacity=".35"/></svg>`,
  learn: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5C6.5 4.5 9.5 4.6 12 6c2.5-1.4 5.5-1.5 8-.5V19c-2.5-1-5.5-.9-8 .5-2.5-1.4-5.5-1.5-8-.5z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M12 6v13.5" stroke="currentColor" stroke-width="1.8"/></svg>`,
  watch: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="12" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M10.5 8.5v5l4-2.5z" fill="currentColor"/><path d="M8 20h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`,
  play: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 20h7M10 20l.8-4.5M14.2 15.5L15 20M8.5 15.5h7c0-2-1.5-3-1.5-5 1.2-.6 2-1.8 2-3.2A3.7 3.7 0 0 0 12 3.6a3.7 3.7 0 0 0-4 3.7c0 1.4.8 2.6 2 3.2 0 2-1.5 3-1.5 5z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>`,
  review: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19h16M7 15l3-4 3 2 4-6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><circle cx="17" cy="7" r="1.6" fill="currentColor"/></svg>`,
};
function renderJourney() {
  const el = $("#v-journey"); const cur = currentChapterN(); const c = chapter(cur); const ns = nextStage(cur);
  const done = CUR.chapters.filter((x) => chapterStatus(x.n) === "done").length;
  el.innerHTML = `
    <div class="where panel">
      <div class="where-main"><span class="eyebrow">أنت هنا</span><h2>الفصل ${cur}: ${esc(c.title)}</h2><p class="lead">${esc(c.goal)}</p></div>
      <div class="where-next"><span class="note">الخطوة التالية</span><b>${ns.letter}. ${ns.ar}</b><button class="btn" data-open="${cur}">افتح الفصل</button></div>
      <div class="where-stat"><span class="mono">${done}/${CUR.chapters.length}</span><span class="note">فصول مكتملة</span></div>
    </div>
    ${typeof warmPanelHtml === "function" ? warmPanelHtml() : ""}
    <div class="map" id="map"></div>`;
  for (const b of $$("[data-open]", el)) b.onclick = () => go("chapter", +b.dataset.open);
  const wg = $("#warm-go", el); if (wg) wg.onclick = startWarmup;
  layoutMap($("#map", el), cur);
}
function layoutMap(box, cur) {
  const W = box.clientWidth || 360; const narrow = W < 520;
  const rowH = narrow ? 118 : 112, partH = 70, top = 16, R = 26;
  const items = []; let y = top; let lastPart = 0;
  for (const c of CUR.chapters) {
    if (c.part !== lastPart) { items.push({ part: CUR.parts.find((p) => p.n === c.part), y }); y += partH; lastPart = c.part; }
    const i = c.n - 1; const x = (i % 2 === 0 ? 0.75 : 0.25) * W;
    items.push({ c, x, y: y + 36 }); y += rowH;
  }
  const H = y + 10; box.style.height = H + "px";
  const nodes = items.filter((it) => it.c);
  const seg = (a, b) => `C${a.x},${(a.y + b.y) / 2} ${b.x},${(a.y + b.y) / 2} ${b.x},${b.y}`;
  const curIdx = nodes.findIndex((n) => n.c.n === cur);
  let dDone = `M${nodes[0].x},${nodes[0].y}`, dTodo = "";
  nodes.forEach((n, i) => { if (!i) return; if (i <= curIdx) dDone += seg(nodes[i - 1], n); else { if (!dTodo) dTodo = `M${nodes[i - 1].x},${nodes[i - 1].y}`; dTodo += seg(nodes[i - 1], n); } });
  let html = `<svg class="path" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" aria-hidden="true"><path class="todo" d="${dTodo}"/><path class="done" d="${dDone}"/></svg>`;
  for (const it of items) {
    if (it.part) { html += `<div class="part" style="top:${it.y}px"><span>${esc(it.part.title)}</span><small>${esc(it.part.en)} · ${esc(it.part.range)}</small></div>`; continue; }
    const c = it.c; const st = chapterStatus(c.n); const isCur = c.n === cur;
    const pips = STAGES.map((s) => `<i class="${stageDone(c.n, s.k) ? "on" : ""}" title="${s.ar}"></i>`).join("");
    const right = it.x > W / 2; const lw = Math.min(narrow ? W * 0.5 : W * 0.42, 300);
    const lx = right ? it.x - R - 14 - lw : it.x + R + 14;
    const stTxt = st === "done" ? `مكتمل ${new Date(J.state.ch[c.n].completedAt).toISOString().slice(0, 10)}` : isCur ? "الفصل الحالي" : st === "open" ? "مفتوح" : `مقفل حتى يكتمل الفصل ${c.n - 1}`;
    html += `<button class="node ${st}${isCur ? " cur" : ""}" style="left:${it.x - R}px;top:${it.y - R}px" data-ch="${c.n}" aria-label="الفصل ${c.n}: ${esc(c.title)}، ${stTxt}">${st === "done" ? ICON.check : st === "locked" ? ICON.lock : `<span>${c.n}</span>`}</button>
      <button class="nlabel ${right ? "r" : "l"} ${st}${isCur ? " cur" : ""}" style="left:${lx}px;top:${it.y - 30}px;width:${lw}px" data-ch="${c.n}">
        <span class="nnum">الفصل ${c.n}${isCur ? ` · <em>أنت هنا</em>` : ""}</span><span class="ntitle">${esc(c.title)}</span><span class="pips" aria-hidden="true">${pips}</span><span class="nst">${stTxt}</span></button>`;
  }
  box.innerHTML = html;
  for (const b of $$("[data-ch]", box)) b.onclick = () => go("chapter", +b.dataset.ch);
  if (!box._ro && window.ResizeObserver) { let lastW = W; box._ro = new ResizeObserver(() => { if (Math.abs(box.clientWidth - lastW) > 8) { lastW = box.clientWidth; layoutMap(box, currentChapterN()); } }); box._ro.observe(box); }
}

/* ---------- a chapter page ---------- */
function renderChapter(n) {
  const el = $("#v-chapter"); const c = chapter(n); if (!c) return go("journey");
  const st = chapterStatus(n); const prog = ruleProgress(c); const s = chState(n);
  const stageCards = STAGES.map((S1, i) => {
    const ready = stageReady(c, S1.k); const doneS = stageDone(n, S1.k); const locked = st === "locked";
    const note = locked ? "مقفل" : !ready ? "قيد الإعداد" : doneS ? "تم" : "متاح";
    const detail = S1.k === "watch" ? c.watch : S1.k === "play" ? c.play : S1.what;
    return `<div class="stage ${doneS ? "done" : ""} ${!ready || locked ? "off" : ""}">
      <div class="stage-h"><span class="sicon">${ICON[S1.k]}</span><span class="sletter mono">${S1.letter}</span><b>${S1.ar}</b><span class="state ${doneS ? "on" : ready && !locked ? "part" : "next"}">${note}</span></div>
      <p class="note">${esc(detail)}</p>
      <button class="btn ${doneS ? "quiet" : ""}" data-stage="${S1.k}" ${ready && !locked ? "" : "disabled"}>${doneS ? "افتح مرة أخرى" : "ابدأ"}</button></div>`;
  }).join("");
  const pct = prog.need ? Math.round(100 * prog.have / prog.need) : 0;
  el.innerHTML = `
    <div class="row"><button class="btn quiet" id="ch-back">→ الخريطة</button></div>
    <div class="panel chead">
      <div><span class="eyebrow">الفصل ${n} · ${esc(CUR.parts.find((p) => p.n === c.part).title)}</span><h2>${esc(c.title)}</h2><p class="note" dir="ltr" style="text-align:right">${esc(c.en)}</p></div>
      <p class="lead">${esc(c.goal)}</p>
      ${st === "locked" ? `<div class="callout">هذا الفصل يُفتح عندما يكتمل الفصل ${n - 1}. يمكنك قراءة ما فيه الآن، أو فتحه الآن باختيارك (الفصل ${n - 1} يبقى غير مكتمل في بياناتك).<div class="row"><button class="btn" id="ch-unlock">افتح هذا الفصل الآن</button></div></div>` : ""}
    </div>
    <div class="cols">
      <div class="panel"><h3>ما الذي ستتعلمه</h3><ul class="topics">${c.topics.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>${n > 1 ? `<p class="note">المتطلب السابق: الفصل ${n - 1} (${esc(chapter(n - 1).title)}).</p>` : `<p class="note">لا يحتاج متطلبًا سابقًا.</p>`}</div>
      <div class="panel"><h3>متى يكتمل الفصل؟</h3><p>${esc(c.rule.text)}</p>
        ${prog.pending ? `<p class="note">يُحسب من مبارياتك المعلَّق عليها في هذا الفصل عندما تصبح جاهزة.</p>` : `<div class="progress"><i style="width:${pct}%"></i></div><p class="note"><span class="mono">${prog.have} / ${prog.need}</span> ${esc(prog.unit)}</p>`}
        <p class="note">${c.rule.kind === "mates" ? "الحكم من نتائجك في المواقف العشوائية (مرحلة المواقف)، لا من اختبار." : "الحكم من بيانات مبارياتك، لا من اختبار."}</p>
        ${s.completedAt ? `<div class="callout good">اكتمل في ${new Date(s.completedAt).toISOString().slice(0, 10)}.</div>` : ""}</div>
    </div>
    <div class="stages">${stageCards}</div>
    <div id="ch-tech"></div>
    ${s.learn && s.learn.checklist ? `<div class="panel"><h3>بماذا أفكر (من الدرس)</h3><ul class="checklist">${s.learn.checklist.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>` : ""}
    <div id="stage-box"></div>`;
  $("#ch-back", el).onclick = () => go("journey");
  if (typeof techniquesPanel === "function") techniquesPanel($("#ch-tech", el), n);
  const ul = $("#ch-unlock", el); if (ul) ul.onclick = () => { chState(n).unlocked = now(); saveJourney(); renderChapter(n); };
  for (const b of $$("[data-stage]", el)) b.onclick = () => openStage(n, b.dataset.stage);
}
function openStage(n, k) {
  const runner = STAGE_RUNNERS[k];
  if (runner) return runner(n);
  const box = $("#stage-box"); box.innerHTML = `<div class="panel"><p class="note">هذه المرحلة قيد الإعداد.</p></div>`;
}
const STAGE_RUNNERS = {}; // filled by watch.js, play.js, learn.js, review.js

/* ---------- journey progress ---------- */
function renderJourneyProgress() {
  const el = $("#v-progress"); const games = J.games.filter((g) => g.finished); const set = J.state.settings;
  const rows = CUR.chapters.map((c) => { const st = chapterStatus(c.n); const p = ruleProgress(c); return `<tr><td class="num">${c.n}</td><td>${esc(c.title)}</td><td>${st === "done" ? "مكتمل" : st === "open" ? "مفتوح" : "مقفل"}</td><td>${STAGES.map((s) => (stageDone(c.n, s.k) ? s.letter : "·")).join(" ")}</td><td class="num">${chapterGames(c.n).length}</td><td class="num">${p.pending ? "–" : p.have + "/" + p.need}</td></tr>`; }).join("");
  el.innerHTML = `
    <div class="kpis">${kpi(CUR.chapters.filter((c) => chapterStatus(c.n) === "done").length + "/" + CUR.chapters.length, "فصول مكتملة")}${kpi(games.length, "مباريات مع المدرّب")}${kpi(currentChapterN(), "الفصل الحالي")}</div>
    <div class="panel"><h2>الفصول</h2><div class="tbl"><table><thead><tr><th>#</th><th>الفصل</th><th>الحالة</th><th>المراحل</th><th>مباريات</th><th>شرط الإكمال</th></tr></thead><tbody>${rows}</tbody></table></div></div>
    <div class="panel"><h2>الإعدادات</h2>
      <label class="f">التعليق أثناء لعبك<select id="set-comm"><option value="every">على كل نقلة</option><option value="important">على النقلات المهمة فقط</option></select></label>
      <label class="f">الشريط الرئيسي للفرص<select id="set-odds"><option value="human">فرصك عند لاعبين بمستواك (تقدير)</option><option value="engine">تقدير المحرك مع لعب مثالي</option></select></label>
      <p class="note">مستوى الخصم يبدأ عند 1100 تقريبًا ويتعدّل بعد كل مباراة حسب نتائجك.</p></div>`;
  const sc = $("#set-comm", el), so = $("#set-odds", el); sc.value = set.commentary; so.value = set.odds;
  sc.onchange = () => { set.commentary = sc.value; saveJourney(); }; so.onchange = () => { set.odds = so.value; saveJourney(); };
}
