"use strict";
/* Play: a full game against an engine with the coach beside you.
   Before your move: an optional hint (what to think about, never the move). After it: a rating, the reason and the
   better move. After the opponent's move: what it threatens. After a mistake: take it back or play on. The chat is
   open throughout. Every game is saved (db games/<id>) with the metrics the chapter's completion rule reads. */

/* The opponent: Maia-1 (js/human.js), a network trained to play the moves real players at a rating actually play. A move
   is sampled from its probabilities, so games vary and contain human mistakes. Below 1100 (no Maia network) the 1100 network
   is sampled at temperature 1.3, which fitted sub-1000 players best on held-out games (tools/maia/MAIA_REPORT.md). Moves
   under 1% are never played. If Maia is unavailable, Stockfish weakened by Skill Level stands in (rating mapping guessed). */
const OPP = {
  kind: "maia",
  label(r, kind = "maia") {
    if (kind === "stockfish-limited") return `خصم بمستوى ${r} تقريبًا (Stockfish بقوة محدودة)`;
    return `خصم يلعب كلاعبين بمستوى ${r} تقريبًا (Maia${r < 1100 ? "-1100 مع عشوائية أكبر" : r > 1900 ? "-1900" : ""})`;
  },
  temp(r) { return r < 1100 ? 1.3 : 1; },
  async move(G, fen, rating) {
    const h = await Human.predict(G.start, G.ucis, rating);
    if (h && h.policy && h.policy.length) {
      const T = this.temp(rating); let w = h.policy.map((m) => Math.pow(m.p, 1 / T)); const tot = w.reduce((x, y) => x + y, 0);
      w = w.map((x) => (x / tot >= 0.01 ? x : 0)); const sum = w.reduce((x, y) => x + y, 0);
      let r = Math.random() * sum, k = 0; while (k < w.length - 1 && r >= w[k]) { r -= w[k]; k++; }
      return { uci: h.policy[k].uci, source: "maia", p: h.policy[k].p };
    }
    return { uci: await this.fallback(fen, rating), source: "stockfish" };
  },
  LEVELS: [[800, 0, 1], [900, 0, 2], [1000, 1, 2], [1100, 2, 3], [1200, 3, 4], [1300, 5, 5], [1400, 7, 6], [1600, 10, 8], [1800, 13, 10], [2000, 16, 12]],
  async fallback(fen, rating) {
    const row = this.LEVELS.reduce((a, r) => (Math.abs(r[0] - rating) < Math.abs(a[0] - rating) ? r : a));
    const a = await Engine.analyse(fen, { depth: row[2], skill: row[1], movetime: 700 });
    return a.best;
  },
};
/* "Players at your level": Maia's probability of the move played and the most common moves, for the position before it. */
function humanSummary(h, playedUci) {
  if (!h || !h.policy || !h.policy.length) return null;
  const mine = h.policy.find((m) => m.uci === playedUci);
  return { rating: h.rating, p: mine ? mine.p : 0, top: h.policy.slice(0, 3).map((m) => ({ san: m.san, uci: m.uci, p: m.p })) };
}
const pctR = (x) => (x < 0.005 ? "<1%" : Math.round(100 * x) + "%");
const RESULT_AR = { win: "فوز", loss: "خسارة", draw: "تعادل", abandoned: "لم تكتمل" };
const fmtNote = (t) => esc(t).replace(/\[([^\]]+)\]/g, '<bdi class="mv">$1</bdi>'); // notes keep moves in [brackets]
const plainNote = (t) => String(t).replace(/\[([^\]]+)\]/g, "$1");
const unverifiedHtml = (bad) => (bad.length ? `<br><span class="note warnline">لم أتحقق من: ${bad.map((b) => `<bdi class="mv">${esc(b)}</bdi>`).join("، ")}</span>` : "");

STAGE_RUNNERS.play = (n) => {
  const c = chapter(n); const box = $("#stage-box"); const set = J.state.settings; const opening = (c.rule || {}).kind === "opening_checklist";
  const games = chapterGames(n).slice().reverse();
  const open = J.games.filter((g) => g.chapter === n && !g.finished && g.sans.length).sort((a, b) => b.t - a.t);
  box.innerHTML = `<div class="panel"><h3>العب مع المدرّب</h3>
    <p>${esc(c.play)}</p>
    <ul class="facts">
      <li>قبل نقلتك: زر «بماذا أفكر الآن؟» يعطيك أسئلة وأماكن تنظر إليها، ولا يكشف النقلة.</li>
      <li>بعد نقلتك: تقييمها (ممتازة، جيدة، غير دقيقة، خطأ، خطأ فادح)، والسبب، والنقلة الأفضل.</li>
      <li>بعد نقلة الخصم: ماذا يهدد. وبعد الخطأ أو الخطأ الفادح تستطيع التراجع، لكنه يبقى محسوبًا في بيانات الفصل.</li>
    </ul>
    ${open.length ? `<div class="callout">لديك مباراة لم تنتهِ بعد (${Math.ceil(open[0].sans.length / 2)} نقلة، ${open[0].color === "w" ? "بالأبيض" : "بالأسود"}).<div class="row"><button class="btn" id="p-resume">أكمل المباراة</button></div></div>` : ""}
    <div class="row"><b>تلعب بـ</b><div class="seg" role="radiogroup" aria-label="اللون">${[["w", "الأبيض"], ["b", "الأسود"], ["r", "عشوائي"]].map(([v, t], k) => `<label><input type="radio" name="p-color" value="${v}" ${k === 0 ? "checked" : ""}><span>${t}</span></label>`).join("")}</div></div>
    <p class="note">${esc(OPP.label(set.oppRating))}. يرتفع المستوى 100 بعد الفوز وينخفض 100 بعد الخسارة. التعليق: ${set.commentary === "every" ? "على كل نقلة" : "على النقلات المهمة فقط"} (يتغيّر من «التقدم»).</p>
    <div class="row"><button class="btn big" id="p-start">${open.length ? "ابدأ مباراة جديدة" : "ابدأ المباراة"}</button></div>
    ${games.length ? `<h4>مبارياتك في هذا الفصل</h4><div class="tbl"><table><thead><tr><th>التاريخ</th><th>اللون</th><th>النتيجة</th><th>نقلاتك</th><th>أخطاء وأخطاء فادحة</th>${opening ? "<th>قائمة الافتتاح</th>" : ""}<th>تُحسب للفصل</th><th></th></tr></thead><tbody>${games.map((g) => { const m = g.metrics || {}; return `<tr><td class="num">${new Date(g.t).toISOString().slice(0, 10)}</td><td>${g.color === "w" ? "أبيض" : "أسود"}</td><td>${RESULT_AR[g.result] || "–"}</td><td class="num">${m.moves ?? "–"}</td><td class="num">${(m.mistakes ?? 0) + (m.blunders ?? 0)}</td>${opening ? `<td class="num">${m.openingScore == null ? "–" : m.openingScore + "/5"}</td>` : ""}<td>${countsForChapter(g) ? "نعم" : "لا"}</td><td><button class="btn quiet" data-rev="${g.id}">راجع</button></td></tr>`; }).join("")}</tbody></table></div>` : ""}</div>`;
  $("#p-start", box).onclick = () => {
    for (const g of open) abandonGame(g, "بدأت مباراة جديدة قبل أن تنتهي هذه.");
    let col = ($('input[name="p-color"]:checked', box) || {}).value || "w"; if (col === "r") col = Math.random() < 0.5 ? "w" : "b";
    PlayGame($("#v-chapter"), { n, color: col, rating: set.oppRating });
  };
  const rs = $("#p-resume", box); if (rs) rs.onclick = () => PlayGame($("#v-chapter"), { n, resume: open[0] });
  for (const b of $$("[data-rev]", box)) b.onclick = () => openReview(n, J.games.find((g) => g.id === b.dataset.rev));
  box.scrollIntoView?.({ block: "start" });
};

let PLAY_TOKEN = 0;
function PlayGame(root, { n, color, rating, resume = null }) {
  const c = chapter(n); const set = J.state.settings; const opening = (c.rule || {}).kind === "opening_checklist";
  const G = resume || { id: "g" + uid(), chapter: n, t: now(), color, opp: { kind: OPP.kind, rating, fallbacks: 0 }, start: START_FEN, sans: [], ucis: [], recs: [], takebacks: 0, hints: 0, threats: 0, finished: false };
  if (!J.games.includes(G)) J.games.push(G);
  const me = G.color, opp = me === "w" ? "b" : "w", oppRating = G.opp.rating;
  const game = new Chess(G.start); let ownMoves = 0;
  for (const s of G.sans) { if (game.turn() === me) ownMoves++; game.move(s, { sloppy: true }); }
  const lastRec = G.recs.filter((r) => !r.takenBack).slice(-1)[0];
  let lastCp = lastRec && lastRec.cpAfter != null ? lastRec.cpAfter : 30;
  let lastUci = G.ucis[G.ucis.length - 1] || null, pre = null, preRes = null, busy = false, threat = null, claudeQuiet = 0;
  const streak = { w: 0, l: 0 }, offered = {}; const token = ++PLAY_TOKEN;
  root.innerHTML = `
    <div class="whead"><button class="btn quiet" id="p-back">→ الفصل ${n}</button>
      <div class="wtitle"><b>العب مع المدرّب · الفصل ${n}</b><span class="note">أنت ${me === "w" ? "بالأبيض" : "بالأسود"} · ${esc(OPP.label(oppRating, G.opp.kind))}</span></div></div>
    <div class="watch play">
      <div class="wboard">
        <div class="boardcap"><span class="turn" id="p-turn"></span><span class="note" id="p-status"></span></div>
        <div class="openname note" id="p-open"></div>
        <div class="board" id="p-board"></div>
        <div class="wctrl"><button class="ctl" id="p-hint">بماذا أفكر الآن؟</button><button class="ctl" id="p-end">أنهِ وراجع</button><button class="ctl" id="p-resign">استسلم</button></div>
        <div id="p-line"></div><div id="p-decide"></div><div id="p-offer"></div>
        <div id="p-odds"></div>
        ${opening ? `<div class="livecheck" id="p-check"></div>` : ""}
      </div>
      <div class="wside">
        <div class="panel coachfeed"><div class="chat-h"><b>المدرّب بجانبك</b><span class="note">الأحدث في الأعلى</span></div><div id="p-feed" aria-live="polite"></div></div>
        <div class="panel" id="p-chat"></div>
      </div>
      <div class="wbelow"><div class="moves wmoves" id="p-moves"></div></div>
    </div>`;
  const boardEl = $("#p-board", root), feed = $("#p-feed", root), decide = $("#p-decide", root), offerEl = $("#p-offer", root), lineEl = $("#p-line", root);
  const alive = () => token === PLAY_TOKEN && document.body.contains(boardEl);
  const board = Board(boardEl, { fen: game.fen(), orient: me, last: lastUci, interactive: false });
  $("#p-back", root).onclick = () => { save(); go("chapter", n); }; // the game stays open and can be resumed
  $("#p-resign", root).onclick = () => { if (!G.finished && G.sans.length) endGame("loss", "استسلمت."); };
  $("#p-end", root).onclick = () => { if (!G.finished) endGame("abandoned", "أنهيت المباراة قبل نهايتها."); };
  $("#p-hint", root).onclick = showHint;
  const setStatus = (t) => { $("#p-status", root).textContent = t; };
  let openShown = null;
  function showOpening() {
    const at = G.sans.slice(); Masters.openingAlong(G.start, at).then((o) => {
      if (!alive() || !o) return; const t = `${o.eco} · ${o.name}`; if (t === openShown) return; openShown = t;
      $("#p-open", root).innerHTML = `الافتتاح: <bdi dir="ltr">${esc(t)}</bdi>`; G.opening = { eco: o.eco, name: o.name, ply: o.ply }; save();
    }).catch(() => {});
  }
  function engineDown() { busy = false; board.update({ interactive: false }); setStatus("تعذّر تشغيل Stockfish في هذا المتصفح، فلا يمكن اللعب الآن. المباراة محفوظة وتستطيع إكمالها لاحقًا."); }
  function card(html, cls = "") { const d = document.createElement("div"); d.className = "fcard " + cls; d.innerHTML = html; feed.prepend(d); while (feed.children.length > 40) feed.lastChild.remove(); return d; }
  let saveT = null; function save() { clearTimeout(saveT); saveT = setTimeout(() => Store.set("games/" + G.id, G), 400); }
  const claudeOk = () => !!SAMPLE && now() > claudeQuiet;
  const claudeFail = (el, e) => { if (e && e.code === "rate_limited") claudeQuiet = now() + 60000; el.innerHTML = coachHtml("المدرّب", esc(claudeMsg(e))); };
  function odds(cp, wdl, prevCp, mover) { $("#p-odds", root).innerHTML = oddsBarHtml(cp, wdl, { prevCp, mover, fen: game.fen(), label: "فرص لاعبين بمستواك من هذا الموقف (تقدير)" }); }
  function refreshUi() {
    const stm = game.turn();
    $("#p-turn", root).innerHTML = G.finished ? "انتهت المباراة" : `<i class="${stm}"></i>${stm === me ? "دورك" : "دور الخصم"}`;
    const st = new Chess(G.start); let h = "";
    G.sans.forEach((s, k) => { const p = st.fen().split(" "); if (p[1] === "w" || k === 0) h += `<span class="mnum">${p[5]}${p[1] === "w" ? "." : "..."}</span>`; st.move(s, { sloppy: true }); h += `<span class="mvbtn ${k === G.sans.length - 1 ? "on" : ""}">${esc(s)}</span>`; });
    const mvEl = $("#p-moves", root); mvEl.innerHTML = h || `<span class="note">لم تبدأ النقلات بعد.</span>`; mvEl.scrollTop = mvEl.scrollHeight;
    liveChecklist();
  }
  function liveChecklist() {
    const el = $("#p-check", root); if (!el) return;
    const ck = Facts.openingChecklist(G.sans, me, G.start, { partial: true });
    const L = [["centre", "بيدق في المركز"], ["develop", `3 قطع خفيفة خارج البيت (${Math.min(ck.developed, 4)}/3)`], ["castle", "التبييت قبل النقلة 12"], ["queen", "الوزير لا يخرج مبكرًا"], ["repeat", "لا قطعة تتحرك مرتين بلا سبب"]];
    el.innerHTML = `<div class="fh"><b>قائمة الافتتاح</b><span class="note">نقلتك ${Math.min(ck.own, 12)} · تُحكم بعد النقلة 10</span></div><ul class="checklist live">${L.map(([k, t]) => `<li class="${ck.state[k]}">${esc(t)}</li>`).join("")}</ul>`;
  }

  /* ---- your turn ---- */
  function userTurn() {
    if (G.finished || !alive()) return;
    const fen = game.fen(); preRes = null;
    pre = Engine.analyse(fen, { depth: 16, movetime: 1500, multipv: 3, low: true });
    pre.then((r) => { if (game.fen() === fen) preRes = r; }, () => {});
    board.update({ fen, last: lastUci, interactive: true, onMove: onUserMove, arrows: threat ? [threatArrow(threat)] : [] });
    setStatus("دورك. خذ وقتك."); refreshUi();
  }
  const threatArrow = (t) => ({ from: t.pv[0].slice(0, 2), to: t.pv[0].slice(2, 4), color: "bad" });
  async function onUserMove(m) {
    if (busy || G.finished || game.turn() !== me) return;
    busy = true; decide.innerHTML = ""; offerEl.innerHTML = ""; lineEl.innerHTML = "";
    const fenBefore = game.fen(), ply = G.sans.length, basePromise = pre, threatBefore = threat; threat = null;
    const humanP = Human.predict(G.start, G.ucis.slice(), oppRating).catch(() => null);
    board.update({ interactive: false, fen: m.fenAfter, last: m.uci, arrows: [] });
    game.move(m.san); G.sans.push(m.san); G.ucis.push(m.uci); lastUci = m.uci; ownMoves++;
    refreshUi(); save(); setStatus("المدرّب يقيّم نقلتك...");
    const cd = card(`<div class="fh"><bdi class="mv">${esc(moveLabel(fenBefore, m.san))}</bdi><span class="note">نقلتك · المدرّب يقيّم...</span></div>`, "mine");
    let base, after;
    try {
      base = await basePromise;
      if (!base.lines.length) base = await Engine.analyse(fenBefore, { depth: 14, movetime: 1200, multipv: 3 }); // the background search was cut off before its first line
      after = await Engine.analyse(game.fen(), { depth: 15, movetime: 1300 });
    } catch { return engineDown(); }
    if (!alive()) return;
    const rec = rateOwn(m, fenBefore, ply, base, after, threatBefore);
    rec.human = humanSummary(await humanP, m.uci);
    rec.masters = await mastersSummary(fenBefore, m.san);
    if (rec.masters && !(await Masters.lookup(game.fen()).catch(() => null))) rec.mastersLeft = true;
    showOpening();
    if (G.finished) return renderOwnCard(cd, rec); // the game was ended while this move was being rated
    G.recs.push(rec); lastCp = after.cp; save();
    odds(after.cp, after.wdl, base.cp, me);
    renderOwnCard(cd, rec);
    if (claudeOk() && (set.commentary === "every" || rec.drop > 5)) explainMine($(".fx", cd), rec);
    if (rec.drop > 10 && !game.game_over()) return offerTakeback(rec, base, threatBefore); // mistakes and blunders stop the game; inaccuracies are commented on
    busy = false; afterMine(rec);
  }
  function rateOwn(m, fenBefore, ply, base, after, threatBefore) {
    const fenNow = game.fen();
    const inLines = base.lines.find((l) => l.pv[0] === m.uci); // same search as the best move: the fairest comparison
    const isBest = !!base.best && m.uci === base.best;
    const pc = Prob.ctx(fenBefore, ply); // one phase for both sides of the comparison, so a phase change is not counted as a drop
    const esB = Prob.esFor(base.cp, me, pc), esA = Prob.esFor(inLines ? inLines.cpWhite : after.cp, me, pc);
    const cl = isBest ? { cls: "excellent", drop: 0 } : Prob.classify(esB, esA);
    const refPv = after.lines[0] ? after.lines[0].pv : [];
    const rec = { ply, own: ownMoves, color: me, san: m.san, uci: m.uci, fenBefore, fen: fenNow, cpBefore: base.cp, cpAfter: after.cp,
      esBefore: Math.round(esB), esAfter: Math.round(esA), cls: cl.cls, drop: cl.drop, isBest,
      best: base.best ? sanOf(fenBefore, base.best) : null, bestUci: base.best, bestLine: base.lines[0] ? pvToSan(fenBefore, base.lines[0].pv, 6) : [],
      refut: pvToSan(fenNow, refPv, 6), alts: base.lines.map((l) => ({ san: pvToSan(fenBefore, l.pv, 1)[0], es: Math.round(Prob.esFor(l.cpWhite, me, pc)) })) };
    // did the opponent's last move hand you a chance?
    const prevOwn = G.recs.filter((r) => r.color === me && !r.takenBack && r.ply < ply).slice(-1)[0];
    if (prevOwn) { const gift = esB - prevOwn.esAfter; if (gift >= 10) { rec.gift = Math.round(gift); if (cl.drop >= 8) rec.missedChance = true; } }
    // grounded observations: every square and move below comes from the position or Stockfish's lines
    const fb = Facts.positionFacts(fenBefore, ply), fa = Facts.positionFacts(fenNow, ply + 1);
    const N = Facts.NAME_AR; const notes = []; const refTo = refPv[0] ? refPv[0].slice(2, 4) : null;
    const lost = refTo && fa[me].hanging.find((h) => h.sq === refTo);
    if (cl.drop >= 10 && lost && rec.refut[0] && rec.refut[0].includes("x")) {
      const already = fb[me].hanging.some((h) => h.sq === refTo) && m.uci.slice(2, 4) !== refTo;
      if (already) { rec.missed = refTo; notes.push(`${N[lost.type]} على ${refTo} كان مهدَّدًا قبل نقلتك وبقي كذلك: الخصم يستطيع [${rec.refut[0]}].`); }
      else { rec.hung = refTo; notes.push(`نقلتك تركت ${N[lost.type]} على ${refTo} بلا حماية كافية: الخصم يستطيع [${rec.refut[0]}].`); }
    }
    if (cl.drop >= 10 && threatBefore && refPv[0] === threatBefore.pv[0] && !rec.missed && !rec.hung) { rec.missed = threatBefore.san[0]; notes.push(`الخصم كان يهدد [${threatBefore.san.join(" ")}] ونقلتك لم تمنعه.`); }
    if (!isBest && cl.drop >= 5 && base.best) {
      const to = base.best.slice(2, 4); const prize = fb[opp].hanging.find((h) => h.sq === to);
      if (prize) notes.push(`كان يمكنك كسب ${N[prize.type]} الخصم على ${to} بـ [${rec.best}].`);
    }
    if (rec.missedChance) notes.push("نقلة الخصم السابقة كانت خطأ يمنحك فرصة، ونقلتك لم تستغلها.");
    if (!notes.length && cl.drop > 5 && rec.refut.length) notes.push(`بعد نقلتك، أقوى رد للخصم: [${numberedLine(fenNow, rec.refut.slice(0, 4))}].`);
    notes.push(...moveFacts(fenBefore, m.san, "me"));
    if (opening && rec.own <= 12) notes.push(...openingNotes(fenBefore, m.san, "me", { warningsOnly: cl.drop > 5, justified: cl.drop <= 2 }));
    rec.notes = notes; rec.habit = habitFor(rec);
    return rec;
  }
  function renderOwnCard(cd, rec) {
    const better = !rec.isBest && rec.drop > 2 && rec.best ? `<p>الأفضل كان <button class="mvref" data-line="best">${esc(rec.best)}</button>، وفرصك بعدها <bdi class="mono">${rec.esBefore}%</bdi>.</p>` : "";
    cd.innerHTML = `<div class="fh"><bdi class="mv">${esc(moveLabel(rec.fenBefore, rec.san))}</bdi><span class="cls ${rec.cls}">${CLASS_AR[rec.cls]}</span>${rec.isBest ? `<span class="tag best">نقلة المحرك الأولى</span>` : ""}<span class="note">فرصك <bdi class="mono">${rec.esBefore}%</bdi> ← <bdi class="mono">${rec.esAfter}%</bdi></span></div>
      ${rec.notes.length ? `<ul class="facts">${rec.notes.map((x) => `<li>${fmtNote(x)}</li>`).join("")}</ul>` : ""}${better}${humanLineHtml(rec)}${mastersLineHtml(rec)}
      ${rec.habit ? `<p class="habit">${esc(rec.habit)}</p>` : ""}
      ${rec.drop > 5 && rec.refut.length ? `<div class="row"><button class="chip-q" data-line="refut">ماذا يحدث بعد نقلتي؟</button></div>` : ""}<div class="fx"></div>`;
    const bb = $('[data-line="best"]', cd); if (bb) bb.onclick = () => showLine(rec.fenBefore, rec.bestLine, `الأفضل: ${numberedLine(rec.fenBefore, rec.bestLine.slice(0, 4))}`);
    const rb = $('[data-line="refut"]', cd); if (rb) rb.onclick = () => showLine(rec.fenBefore, [rec.san, ...rec.refut], `ما لعبته: ${numberedLine(rec.fenBefore, [rec.san, ...rec.refut].slice(0, 5))}`);
  }
  function offerTakeback(rec, base, threatBefore) {
    decide.innerHTML = `<div class="callout ${rec.drop > 10 ? "bad" : ""}"><b>${CLASS_AR[rec.cls]}: فرصك <bdi class="mono">${rec.esBefore}%</bdi> ← <bdi class="mono">${rec.esAfter}%</bdi>.</b> ${rec.notes[0] ? fmtNote(rec.notes[0]) : ""}
      <p class="note">تستطيع التراجع وتجربة نقلة أخرى (الخطأ يبقى محسوبًا في بيانات الفصل)، أو الاستمرار.</p>
      <div class="row"><button class="btn" id="p-take">تراجع وجرّب مرة أخرى</button><button class="btn quiet" id="p-go">استمر</button></div></div>`;
    setStatus("قرّر: تراجع أم استمر؟");
    $("#p-take", decide).onclick = () => {
      decide.innerHTML = ""; lineEl.innerHTML = ""; rec.takenBack = true; G.takebacks++;
      game.undo(); G.sans.pop(); G.ucis.pop(); ownMoves--; lastUci = G.ucis[G.ucis.length - 1] || null; lastCp = base.cp; threat = threatBefore;
      card(`<p class="note">تراجعت عن <bdi class="mv">${esc(rec.san)}</bdi>. فكّر مرة أخرى: ماذا يهدد الخصم؟ وما الذي تحققه نقلتك؟</p>`, "hint");
      pre = Promise.resolve(base); preRes = base; busy = false; save();
      board.update({ fen: game.fen(), last: lastUci, interactive: true, onMove: onUserMove, arrows: threat ? [threatArrow(threat)] : [] });
      odds(base.cp, base.wdl); refreshUi(); setStatus("جرّب نقلة أخرى.");
    };
    $("#p-go", decide).onclick = () => { decide.innerHTML = ""; busy = false; closeLine(); afterMine(rec); };
  }
  function afterMine(rec) {
    if (checkEnd()) return;
    const adv = me === "w" ? rec.cpAfter : -rec.cpAfter; // Stockfish: +10 pawns or a forced mate counts as decided
    streak.w = adv >= 1000 ? streak.w + 1 : 0; streak.l = adv <= -1000 ? streak.l + 1 : 0;
    if (streak.w >= 3 && !offered.w) { offered.w = true; offer("w"); }
    if (streak.l >= 3 && !offered.l) { offered.l = true; offer("l"); }
    opponentTurn();
  }
  function offer(kind) {
    offerEl.innerHTML = kind === "w"
      ? `<div class="callout good"><b>الموقف محسوم لصالحك</b> (Stockfish: تفوّق بعشرة بيادق أو أكثر، أو كش مات قسري، منذ 3 نقلات). تستطيع تسجيلها فوزًا الآن، أو الإكمال للتدرّب على إنهاء المباراة بالكش مات.<div class="row"><button class="btn" data-o="claim">سجّلها فوزًا</button><button class="btn quiet" data-o="no">أكمل</button></div></div>`
      : `<div class="callout bad"><b>الموقف خاسر بوضوح</b> (Stockfish: الخصم متفوق بعشرة بيادق أو أكثر، أو عنده كش مات قسري، منذ 3 نقلات). تستطيع الاستسلام والانتقال إلى المراجعة، أو المحاولة حتى النهاية.<div class="row"><button class="btn" data-o="claim">استسلم وراجع</button><button class="btn quiet" data-o="no">أكمل</button></div></div>`;
    $('[data-o="claim"]', offerEl).onclick = () => { offerEl.innerHTML = ""; endGame(kind === "w" ? "win" : "loss", kind === "w" ? "سجّلت الفوز: الموقف كان محسومًا (تفوّق بعشرة بيادق أو كش مات قسري لثلاث نقلات)." : "استسلمت في موقف خاسر."); };
    $('[data-o="no"]', offerEl).onclick = () => { offerEl.innerHTML = ""; };
  }
  function closeLine() { if (!lineEl.innerHTML) return; lineEl.innerHTML = ""; board.update({ fen: game.fen(), last: lastUci, interactive: game.turn() === me && !G.finished && !busy, onMove: onUserMove, arrows: threat && game.turn() === me ? [threatArrow(threat)] : [] }); }
  function showLine(fen, sans, title) {
    const fens = [fen], ucis = []; const g = new Chess(fen); for (const s of sans) { const mm = g.move(s, { sloppy: true }); if (!mm) break; fens.push(g.fen()); ucis.push(mm.from + mm.to); }
    let k = 1;
    lineEl.innerHTML = `<div class="branchbar"><div class="row" style="justify-content:space-between"><b>${esc(title)}</b><button class="btn quiet" id="l-back">عودة إلى المباراة</button></div><div class="row"><button class="ctl" id="l-prev" aria-label="السابقة">→</button><span class="note" id="l-txt"></span><button class="ctl" id="l-next" aria-label="التالية">←</button></div></div>`;
    const show = () => { board.update({ fen: fens[k], last: ucis[k - 1] || null, interactive: false, arrows: [] }); $("#l-txt", lineEl).innerHTML = k ? `<bdi class="mv">${esc(numberedLine(fen, sans.slice(0, k)))}</bdi>` : "الموقف قبل النقلة"; };
    $("#l-prev", lineEl).onclick = () => { k = Math.max(0, k - 1); show(); };
    $("#l-next", lineEl).onclick = () => { k = Math.min(ucis.length, k + 1); show(); };
    $("#l-back", lineEl).onclick = closeLine;
    show();
  }

  /* ---- the opponent's turn ---- */
  async function opponentTurn() {
    if (G.finished || !alive()) return;
    setStatus("الخصم يفكّر..."); refreshUi();
    const fen0 = game.fen(); let uci;
    try { const mv0 = await OPP.move(G, fen0, oppRating); uci = mv0.uci; if (mv0.source !== "maia") G.opp.fallbacks = (G.opp.fallbacks || 0) + 1; } catch { return engineDown(); }
    await sleep(300);
    if (!uci || G.finished || !alive() || game.fen() !== fen0) return;
    lineEl.innerHTML = "";
    const mv = uciMove(game, uci); G.sans.push(mv.san); G.ucis.push(uci); lastUci = uci; showOpening();
    const rec = { ply: G.sans.length - 1, color: opp, san: mv.san, uci, fenBefore: fen0, fen: game.fen(), cpBefore: lastCp };
    G.recs.push(rec); save();
    board.update({ fen: game.fen(), last: uci, interactive: false, arrows: [] });
    if (checkEnd()) return;
    const cd = card(`<div class="fh"><bdi class="mv">${esc(moveLabel(fen0, mv.san))}</bdi><span class="note">نقلة الخصم</span></div><ul class="facts"></ul><div class="fx"></div>`, "theirs");
    userTurn();
    commentOpp(cd, rec);
  }
  async function commentOpp(cd, rec) {
    const fenNow = rec.fen; const ul = $(".facts", cd); const add = (t) => ul.insertAdjacentHTML("beforeend", `<li>${fmtNote(t)}</li>`);
    for (const t of moveFacts(rec.fenBefore, rec.san, "opp")) add(t);
    mastersSummary(rec.fenBefore, rec.san).then((ms) => { if (ms) ul.insertAdjacentHTML("beforeend", `<li class="mastersli">${mastersText(ms, rec.san, "opp")}</li>`); });
    if (game.in_check()) add("عالج الكش أولًا: حرّك الملك، أو ضع قطعة في طريق الكش، أو أسر القطعة التي تعطيه.");
    if (opening && ownMoves < 12) for (const t of openingNotes(rec.fenBefore, rec.san, "opp")) add(t);
    let base; try { base = await pre; } catch { return; }
    rec.cpAfter = base.cp; const oc = Prob.ctx(rec.fenBefore, rec.ply); const oppDrop = Prob.esFor(rec.cpBefore, opp, oc) - Prob.esFor(base.cp, opp, oc); rec.drop = Math.max(0, Math.round(oppDrop)); save();
    if (!alive() || game.fen() !== fenNow) return; // you already moved
    odds(base.cp, base.wdl, rec.cpBefore, opp); lastCp = base.cp;
    if (oppDrop >= 10) add("هذه النقلة خطأ من الخصم: فرصك زادت. ابحث عن الفرصة قبل أي شيء آخر: كش، أسر، تهديد.");
    let th = null;
    if (!game.in_check()) { // what would the opponent play if it were their move again?
      const nf = nullFenOf(fenNow);
      const tn = await Engine.analyse(nf, { depth: 12, movetime: 600, low: true }).catch(() => ({ lines: [] }));
      if (tn.lines[0]) { const tc = Prob.ctx(fenNow); const gain = Prob.esFor(tn.cp, opp, tc) - Prob.esFor(base.cp, opp, tc); if (gain >= 8) th = { pv: tn.lines[0].pv.slice(0, 3), san: pvToSan(nf, tn.lines[0].pv, 3), gain: Math.round(gain) }; }
    }
    if (!alive() || game.fen() !== fenNow) return;
    if (th) {
      threat = th; G.threats = (G.threats || 0) + 1; rec.threat = th.san; save();
      add(`يهدد: [${th.san.join(" ")}]. عالج هذا التهديد قبل أي خطة أخرى.`);
      board.update({ arrows: [threatArrow(th)] });
    } else if (!game.in_check() && !Facts.positionFacts(fenNow, G.sans.length)[me].hanging.length) add("لا تهديد مباشرًا. فكّر في خطتك: أي قطعة لم تعمل بعد؟");
    if (claudeOk() && (set.commentary === "every" || th || oppDrop >= 10)) explainTheirs($(".fx", cd), rec, th);
  }

  /* ---- hint: what to think about, never the move ---- */
  function showHint() {
    if (G.finished || game.turn() !== me || busy) return;
    G.hints = (G.hints || 0) + 1; save();
    const fen = game.fen(); const f = Facts.positionFacts(fen, G.sans.length);
    const cd = card(`<div class="fh"><b>بماذا تفكر الآن؟</b><span class="note">تلميح لا يكشف النقلة</span></div><ul class="facts">${hintItems(f).map((x) => `<li>${fmtNote(x)}</li>`).join("")}</ul><p class="habit">قبل أن تلعب: ماذا يهدد الخصم؟ ما نقلاتي القسرية (كش، أسر، تهديد)؟ وبعد نقلتي، ما أقوى رد له؟</p><div class="fx"></div>`, "hint");
    if (claudeOk()) hintClaude($(".fx", cd), fen);
  }
  function hintItems(f) {
    const mine = f[me]; const out = [];
    out.push({ opening: "مرحلة الافتتاح: المركز، التطوير، أمان الملك.", middlegame: "وسط اللعب: ما خطتك؟ أي قطعة لم تعمل بعد؟ وماذا يريد الخصم؟", endgame: "النهاية: الملك قطعة مقاتلة الآن، والبيادق الحرة مهمة." }[f.phase]);
    if (f.inCheck) out.push("أنت في كش: حرّك الملك، أو ضع قطعة في الطريق، أو أسر القطعة التي تعطي الكش.");
    if (threat) out.push(`تذكّر تهديد الخصم: [${threat.san.join(" ")}].`);
    if (mine.hanging.length) out.push(`عدد قطعك التي يمكن أن تُكسب الآن: ${mine.hanging.length}. أيها؟`);
    if (f.goodCaptures.length) out.push("هناك أسر يكسب مادة. ابحث عنه.");
    if (f.checks.length) out.push(`عدد الكشات الممكنة لك: ${f.checks.length}. افحص كلًّا منها: هل يحقق شيئًا؟`);
    if (f.phase === "opening") {
      if (mine.dev.undeveloped.length) out.push(`قطع لم تتطور بعد: ${mine.dev.undeveloped.map((s) => Facts.NAME_AR["bg".includes(s[0]) ? "n" : "b"] + " على " + s).join("، ")}.`);
      if (!mine.dev.castled && mine.dev.kingCenter) out.push("ملكك ما زال في المركز. متى تبيّت؟");
      if (!mine.center.pawns) out.push("لا بيدق لك في المركز (d4، e4، d5، e5).");
    }
    if (mine.king && mine.king.attackers >= 3) out.push(`عدد قطع الخصم التي تهاجم المربعات حول ملكك: ${mine.king.attackers}.`);
    return out;
  }
  async function hintClaude(el, fen) {
    el.innerHTML = coachHtml("المدرّب", "يفكّر...");
    const prompt = `${COACH_RULES}\n${LEVEL_RULES[c.level] || ""}
TASK: The student asks what to think about BEFORE choosing a move. In Arabic, 2-3 short sentences: what matters most in this position and which questions to ask. Do NOT name any move and do not name a destination square; point to ideas and areas of the board only.
DATA:
${factSheet({ fen, ply: G.sans.length, start: G.start, moves: G.sans, threat: threat ? threat.san : null })}
CHAPTER FOCUS: ${c.title}: ${c.goal}`;
    const strip = (t) => t.replace(SAN_RE, "…"); // a hint never shows a move, whatever the model writes
    try {
      const t = await askClaude(prompt, { tier: "quick", onText: (x) => { el.innerHTML = coachHtml("المدرّب", esc(strip(x.text))); } });
      el.innerHTML = coachHtml("المدرّب", esc(strip(t)));
    } catch (e) { claudeFail(el, e); }
  }

  /* ---- Claude's explanations, grounded in the move's data ---- */
  async function explainMine(el, rec) {
    el.innerHTML = coachHtml("المدرّب", "يكتب...");
    const good = rec.drop <= 5;
    const prompt = `${COACH_RULES}\n${LEVEL_RULES[c.level] || ""}
TASK: The student (${me === "w" ? "White" : "Black"}) just played ${rec.san}, rated "${rec.cls}" (their chances ${rec.esBefore}% with the best move, ${rec.esAfter}% after this one). In Arabic, 2-4 short sentences: ${good ? "what the move achieves, using the facts" : `what the move allows, and why ${rec.best} is better`}. End with one reusable thinking habit (one sentence).
DATA:
POSITION BEFORE: ${rec.fenBefore}
PIECES: ${pieceList(rec.fenBefore)}
GAME SO FAR: ${numberedLine(G.start, G.sans.slice(0, rec.ply)) || "(start)"}
STOCKFISH BEST LINE BEFORE THE MOVE: ${numberedLine(rec.fenBefore, rec.bestLine) || "none"}
STOCKFISH BEST REPLY LINE AFTER ${rec.san}: ${numberedLine(rec.fen, rec.refut) || "none"}
OBSERVATIONS (verified): ${rec.notes.map(plainNote).join(" ") || "none"}
PLAYERS AT THE STUDENT'S LEVEL (Maia-1 model of ~${rec.human ? rec.human.rating : "?"}-rated players): ${rec.human ? `${Math.round(100 * rec.human.p)}% of them play ${rec.san}; most common here: ${rec.human.top.map((t) => `${t.san} ${Math.round(100 * t.p)}%`).join(", ")}` : "unavailable"}
FACTS AFTER THE MOVE (student's side): ${Facts.describe(Facts.positionFacts(rec.fen, rec.ply + 1), me).join(" ") || "none"}
CHAPTER FOCUS: ${c.title}: ${c.goal}`;
    const allowed = allowedFrom(rec.fenBefore, [rec.bestLine, [rec.san, ...rec.refut], G.sans]);
    try {
      const t = await askClaude(prompt, { tier: "quick", onText: (x) => { el.innerHTML = coachHtml("المدرّب", markSan(esc(x.text), null).html); } });
      const { html, bad } = markSan(esc(t), allowed); rec.coach = t; save();
      el.innerHTML = coachHtml("المدرّب", html + unverifiedHtml(bad));
    } catch (e) { claudeFail(el, e); }
  }
  async function explainTheirs(el, rec, th) {
    el.innerHTML = coachHtml("المدرّب", "يكتب...");
    const prompt = `${COACH_RULES}\n${LEVEL_RULES[c.level] || ""}
TASK: The opponent (${opp === "w" ? "White" : "Black"}) just played ${rec.san}. In Arabic, 1-3 short sentences: what this move does, threatens or prepares, and what the student should look at now. Do not tell the student which move to play.
DATA:
POSITION AFTER: ${rec.fen} (the student plays ${me === "w" ? "White" : "Black"} and is to move)
PIECES: ${pieceList(rec.fen)}
GAME SO FAR: ${numberedLine(G.start, G.sans.slice(0, rec.ply + 1))}
IF THE OPPONENT COULD MOVE AGAIN, STOCKFISH SAYS THEY WOULD PLAY: ${th ? numberedLine(nullFenOf(rec.fen), th.san) : "nothing dangerous"}
FACTS (student's side): ${Facts.describe(Facts.positionFacts(rec.fen, rec.ply + 1), me).join(" ") || "none"}
CHAPTER FOCUS: ${c.title}`;
    const allowed = allowedFrom(rec.fen, [th ? th.san : [], G.sans]);
    try {
      const t = await askClaude(prompt, { tier: "quick", onText: (x) => { el.innerHTML = coachHtml("المدرّب", markSan(esc(x.text), null).html); } });
      const { html, bad } = markSan(esc(t), allowed); rec.coach = t; save();
      el.innerHTML = coachHtml("المدرّب", html + unverifiedHtml(bad));
    } catch (e) { claudeFail(el, e); }
  }

  /* ---- the end ---- */
  function checkEnd() {
    if (!game.game_over()) return false;
    if (game.in_checkmate()) { const lost = game.turn() === me; endGame(lost ? "loss" : "win", lost ? "كش مات: خسرت." : "كش مات: فزت."); }
    else endGame("draw", game.in_stalemate() ? "تعادل: لا نقلة قانونية والملك ليس في كش (stalemate)." : game.in_threefold_repetition() ? "تعادل بتكرار الموقف ثلاث مرات." : game.insufficient_material() ? "تعادل: القطع الباقية لا تكفي للكش مات." : "تعادل بقاعدة الخمسين نقلة.");
    return true;
  }
  function endGame(result, msg) {
    if (G.finished) return;
    G.finished = true; G.result = result; G.reason = msg; busy = false; threat = null;
    board.update({ interactive: false, arrows: [] }); decide.innerHTML = ""; offerEl.innerHTML = ""; lineEl.innerHTML = "";
    const wasDone = !!chState(n).completedAt;
    finalizeGame(G); setStatus(msg); refreshUi();
    const prog = ruleProgress(c); const justDone = !wasDone && !!chState(n).completedAt;
    const cd = card(`<div class="fh"><b>انتهت المباراة: ${RESULT_AR[result]}</b></div><p>${esc(msg)}</p>
      ${countsForChapter(G) ? (prog.pending ? "" : `<p>شرط إكمال الفصل: <bdi class="mono">${prog.have}/${prog.need}</bdi> ${esc(prog.unit)}.</p>`) : `<p class="note">مباراة لم تكتمل وفيها أقل من 20 نقلة لك: لا تُحسب في شرط إكمال الفصل.</p>`}
      ${justDone ? `<div class="callout good"><b>اكتمل الفصل ${n}.</b> ${n < CUR.chapters.length ? `الفصل ${n + 1} مفتوح الآن.` : ""}</div>` : ""}
      <p class="note">مستوى الخصم في المباراة القادمة: ${J.state.settings.oppRating}.</p>
      <div class="row"><button class="btn" data-a="review">راجع المباراة</button><button class="btn quiet" data-a="again">مباراة جديدة</button></div>`, "end");
    $('[data-a="review"]', cd).onclick = () => openReview(n, G);
    $('[data-a="again"]', cd).onclick = () => { go("chapter", n); STAGE_RUNNERS.play(n); };
  }

  Chat($("#p-chat", root), {
    level: c.level,
    chips: ["ماذا يريد الخصم الآن؟", "ما خطتي في هذا الموقف؟", "لماذا قيّمتَ نقلتي الأخيرة هكذا؟", "ما أهم شيء في هذه المرحلة؟"],
    getContext: () => {
      const fen = game.fen(); const ctx = { fen, ply: G.sans.length, start: G.start, moves: G.sans.slice(), threat: threat ? threat.san : null };
      if (preRes && game.turn() === me) ctx.engineLines = preRes.lines.map((l) => ({ san: pvToSan(fen, l.pv, 8), cp: l.cpWhite }));
      const lastOwn = G.recs.filter((r) => r.color === me && r.cls).slice(-1)[0];
      ctx.knownLines = lastOwn ? [lastOwn.bestLine, [lastOwn.san, ...lastOwn.refut]] : [];
      ctx.extra = `CONTEXT: The student plays ${me === "w" ? "White" : "Black"} in a training game in progress. Do not reveal the best move in the current position unless the student explicitly asks for it; teach how to find it instead.${lastOwn ? ` The student's last move was ${lastOwn.san}, rated ${lastOwn.cls} (chances ${lastOwn.esBefore}% -> ${lastOwn.esAfter}%); the best move there was ${lastOwn.best}; Stockfish's reply line after it: ${lastOwn.refut.join(" ") || "none"}.` : ""}`;
      return ctx;
    },
  });

  /* ---- start or resume ---- */
  if (resume) card(`<p class="note">استأنفت المباراة من النقلة ${Math.floor(G.sans.length / 2) + 1}.</p>`, "hint");
  else card(`<p>بدأت المباراة. أنت ${me === "w" ? "بالأبيض، فابدأ أنت" : "بالأسود، والخصم يبدأ"}.${opening ? " راقب قائمة الافتتاح تحت الرقعة." : ""}</p>`, "hint");
  odds(lastCp, null);
  refreshUi();
  if (game.game_over()) checkEnd(); else if (game.turn() === me) userTurn(); else opponentTurn();
}

/* What a move does, from the position alone: captures, checks, a new threat, a piece taken out of danger. */
const YOUR_AR = { p: "بيدقك", n: "حصانك", b: "فيلك", r: "رخّك", q: "وزيرك", k: "ملكك" };
function moveFacts(fenBefore, san, who) {
  const g = new Chess(fenBefore); const mv = g.move(san, { sloppy: true }); if (!mv) return [];
  const side = mv.color, other = side === "w" ? "b" : "w"; const N = Facts.NAME_AR; const you = who === "me"; const out = [];
  if (mv.captured) out.push(you ? `أسرت ${N[mv.captured]} على ${mv.to}.` : `الخصم أسر ${YOUR_AR[mv.captured]} على ${mv.to}.`);
  if (mv.san.includes("#")) return [...out, you ? "كش مات." : "الخصم أعطى كش مات."];
  if (mv.san.includes("+")) out.push(you ? "كش: الخصم مجبر على الرد عليه قبل أي شيء." : "الخصم يعطي كش.");
  if (you) {
    const G0 = Facts.grid(new Chess(fenBefore)), G1 = Facts.grid(g);
    const was = new Set(Facts.hanging(G0, other).map((h) => h.sq));
    const hit = Facts.hanging(G1, other).find((h) => !was.has(h.sq));
    if (hit) out.push(`تهديد جديد: نقلتك تهاجم ${N[hit.type]} الخصم على ${hit.sq}، ولا يحميه ما يكفي.`);
    const after = new Set(Facts.hanging(G1, side).map((h) => h.sq));
    const saved = Facts.hanging(G0, side).find((h) => !after.has(h.sq === mv.from ? mv.to : h.sq));
    if (saved) out.push(`أخرجت ${N[saved.type]} على ${saved.sq} من الخطر.`);
  }
  return out;
}
/* Opening observations about one move (chapter 1), from the move itself and the position before it.
   warningsOnly: after a bad move, praise for development would point at the wrong thing.
   justified: the move breaks a principle but was one of the best moves here, so it is an exception, not a mistake. */
function openingNotes(fenBefore, san, who, { warningsOnly = false, justified = false } = {}) {
  const g = new Chess(fenBefore); const mv = g.move(san, { sloppy: true }); if (!mv) return [];
  const side = mv.color, other = side === "w" ? "b" : "w"; const G0 = Facts.grid(new Chess(fenBefore)); const dev = Facts.development(G0, side);
  const home = { w: { b1: "n", g1: "n", c1: "b", f1: "b" }, b: { b8: "n", g8: "n", c8: "b", f8: "b" } }[side]; const you = who === "me";
  const good = (t) => (warningsOnly ? [] : [t]);
  if (mv.flags.includes("k") || mv.flags.includes("q")) return good(you ? "بيّتّ ملكك: الملك أأمن، والرخ دخل اللعب." : "الخصم بيّت ملكه.");
  if (mv.captured) return [];
  if (home[mv.from] === mv.piece) return good(you ? "طوّرت قطعة جديدة من مكانها الأصلي." : "الخصم طوّر قطعة جديدة.");
  if (mv.piece === "q" && !mv.captured && dev.developed < 2) return [!you ? "الخصم أخرج وزيره قبل تطوير قطعه الخفيفة. هل تستطيع مهاجمته بقطعة تتطور في الوقت نفسه؟" : justified ? "أخرجت الوزير مبكرًا، وهنا كان لذلك سبب: النقلة من أفضل نقلات الموقف. القاعدة تبقى: لا يخرج الوزير قبل القطع الخفيفة إلا لسبب واضح (تهديد أو دفاع)." : "أخرجت الوزير قبل تطوير قطعك الخفيفة: الخصم قد يهاجمه ويكسب الوقت بتطوير قطعه."];
  if ((mv.piece === "n" || mv.piece === "b") && !mv.captured && !home[mv.from] && dev.undeveloped.length >= 2) {
    const threatened = Facts.see(G0, mv.from, other) > 0 || Facts.attackers(G0, mv.from, other).some((a) => Facts.VAL[a.type] < Facts.VAL[mv.piece]);
    if (!threatened) return [!you ? `الخصم حرّك قطعة متطورة مرة ثانية بلا سبب، وما زال في البيت ${dev.undeveloped.length} من قطعه الخفيفة: وقت ضائع لصالحك.` : justified ? "حرّكت قطعة متطورة مرة ثانية، وهنا كان لذلك سبب: النقلة من أفضل نقلات الموقف. القاعدة تبقى: في الافتتاح قطعة جديدة في كل نقلة إلا لسبب واضح." : `حرّكت قطعة متطورة مرة ثانية بلا سبب، وما زال في البيت ${dev.undeveloped.length} من قطعك الخفيفة.`];
  }
  if (you && mv.piece === "p" && ["d4", "e4", "d5", "e5"].includes(mv.to)) return good("بيدق في المركز: يسيطر على مربعات مهمة ويفتح الطريق لقطعك.");
  return [];
}
/* Masters (KingBase 2017): how often the move was played in this position and how it scored for the side that played it. */
async function mastersSummary(fenBefore, san) {
  if (typeof Masters === "undefined") return null;
  const t = await Masters.lookup(fenBefore).catch(() => null); if (!t) return null;
  const mine = t.moves.find((m) => m.san === san);
  return { total: t.total, share: mine ? mine.share : 0, scoreStm: mine ? mine.scoreStm : null, n: mine ? mine.n : 0, top: t.moves.slice(0, 3).map((m) => ({ san: m.san, share: m.share, scoreStm: m.scoreStm })) };
}
function mastersText(ms, san, who) {
  const top = ms.top[0];
  let t = `في مباريات الأساتذة (<bdi class="mono">${ms.total.toLocaleString("en")}</bdi> مباراة من هذا الموقف): `;
  if (ms.n) t += `${who === "opp" ? "هذه النقلة" : "نقلتك"} لُعبت في <bdi class="mono">${pctR(ms.share)}</bdi> منها، وسجّلت <bdi class="mono">${pctR(ms.scoreStm)}</bdi> لمن لعبها`;
  else t += `${who === "opp" ? "هذه النقلة" : "نقلتك"} نادرة جدًا عندهم`;
  if (top && top.san !== san) t += `؛ الأكثر: <bdi class="mv">${esc(top.san)}</bdi> (<bdi class="mono">${pctR(top.share)}</bdi>)`;
  return t + ".";
}
function mastersLineHtml(rec) {
  if (!rec.masters) return "";
  return `<p class="masterline">${mastersText(rec.masters, rec.san, "me")}${rec.mastersLeft ? " من هنا خرجت المباراة من المواقف المعروفة في قاعدة الأساتذة (أقل من 75 مباراة)." : ""}</p>`;
}
/* "Players at your level" line under a move card (Maia). A common move that Stockfish rates poorly is flagged as a common trap. */
function humanLineHtml(rec) {
  const H = rec.human; if (!H) return "";
  const top = H.top[0]; const alt = (rec.alts || []).find((a) => a.san === top.san);
  let t = `عند لاعبين بمستوى ~${H.rating}: <bdi class="mono">${pctR(H.p)}</bdi> يلعبون نقلتك`;
  if (top.uci === rec.uci) t += "، وهي الأكثر شيوعًا.";
  else {
    t += `، والأكثر شيوعًا <bdi class="mv">${esc(top.san)}</bdi> (<bdi class="mono">${pctR(top.p)}</bdi>)`;
    t += alt && rec.esBefore - alt.es > 5 ? "، وهي نقلة ضعيفة هنا: موقف يخطئ فيه كثيرون بمستواك." : ".";
  }
  if (rec.drop > 10 && H.p >= 0.15) t += " خطأ شائع عند هذا المستوى، فاحفظ الموقف جيدًا.";
  return `<p class="humanline">${t}</p>`;
}
function habitFor(r) {
  if (r.hung) return "عادة: بعد أن تختار نقلتك وقبل أن تلعبها، افحص كل قطعة: هل ما زالت محمية؟";
  if (r.missed) return "عادة: أول سؤال بعد كل نقلة للخصم: ماذا يهدد الآن؟";
  if (r.missedChance) return "عادة: بعد كل نقلة للخصم اسأل: هل ترك شيئًا بلا حماية؟ (كش، أسر، تهديد)";
  if (r.drop > 5) return "عادة: قبل أن تلعب، تخيّل أقوى رد للخصم على نقلتك.";
  return "";
}
/* Metrics over every attempt, including moves taken back: a takeback lets you learn, it does not erase the mistake. */
function computeMetrics(G) {
  const all = G.recs.filter((r) => r.color === G.color && r.cls); const fin = all.filter((r) => !r.takenBack);
  const cnt = (k) => all.filter((r) => r.cls === k).length;
  const ck = Facts.openingChecklist(G.sans, G.color, G.start);
  return {
    moves: fin.length, attempts: all.length, takebacks: G.takebacks || 0, hints: G.hints || 0, threats: G.threats || 0,
    excellent: cnt("excellent"), good: cnt("good"), inaccuracies: cnt("inaccuracy"), mistakes: cnt("mistake"), blunders: cnt("blunder"),
    okShare: all.length ? Math.round(100 * all.filter((r) => r.drop <= 5).length / all.length) : null, // every attempt counts
    avgDrop: fin.length ? +(fin.reduce((s, r) => s + r.drop, 0) / fin.length).toFixed(1) : null,
    openingScore: ck ? ck.score : null, openingItems: ck ? ck.items : null,
    openingBlunder: all.some((r) => r.own <= 10 && r.cls === "blunder"),
    hanging: all.filter((r) => r.hung).length, missedThreats: all.filter((r) => r.missed).length,
    gifts: fin.filter((r) => r.gift >= 10).length, punished: fin.filter((r) => r.gift >= 10 && r.drop <= 5).length,
  };
}
function finalizeGame(G) {
  G.metrics = computeMetrics(G); G.tEnd = now();
  const st = J.state.settings;
  if (G.result === "win") st.oppRating = Math.min(2000, st.oppRating + 100); else if (G.result === "loss") st.oppRating = Math.max(800, st.oppRating - 100);
  Prob.band = st.oppRating;
  makeWarmCards(G);
  Store.set("games/" + G.id, G); checkChapterComplete(G.chapter); saveJourney();
}
function abandonGame(G, why) { if (G.finished) return; G.finished = true; G.result = "abandoned"; G.reason = why; finalizeGame(G); }
function checkChapterComplete(n) {
  const c = chapter(n); const s = chState(n); if (s.completedAt) return;
  if (ruleProgress(c).met) { s.completedAt = now(); saveJourney(); }
}
