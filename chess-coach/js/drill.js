"use strict";
/* Positions (stage C): endless positions on the chapter's theme, mostly from real games, played a few moves deep against
   Stockfish's best defence. Each move goes through an engine's routine: list your candidate moves (tap them on the board,
   nothing is played), choose one, then every candidate is scored by Stockfish 17.1 next to its own top moves. Everything
   shown is computed in the page (no Claude call). Mates are judged by the mate distance; other positions by the drop in your
   chances (the same scale as Play). Positions you get wrong come back later. */
const movesAr = (k) => arCount(k, "نقلة واحدة", "نقلتين", "نقلات", "نقلة");
const DRILL_POOLS = {}; // file -> items
async function drillPool(file) { if (!DRILL_POOLS[file]) DRILL_POOLS[file] = (await loadJSON("data/positions/" + file)).items; return DRILL_POOLS[file]; }
function drillState(n) { const s = chState(n); return s.drill || (s.drill = { pools: {}, mates: [], count: 0 }); }
function poolState(n, id) { const d = drillState(n); return d.pools[id] || (d.pools[id] = { done: 0, moves: 0, match: 0, candBest: 0, seen: [], retry: [] }); }

STAGE_RUNNERS.drill = (n) => {
  const c = chapter(n); const box = $("#stage-box"); const pools = content(c).drill.pools; const d = drillState(n);
  box.innerHTML = `<div class="panel"><h3>مواقف بلا نهاية</h3>
    <p>مواقف على موضوع الفصل${pools.some((p) => p.file) ? "، أغلبها من مباريات حقيقية للاعبين قبلك" : ""}. تلعب كل موقف عدة نقلات ضد أفضل دفاع من Stockfish، وكل نقلة تمر بروتين المحرك:</p>
    <ol class="facts"><li>النقلات القسرية أولًا: كشات، أسر، تهديدات (لك وللخصم).</li><li>مرشحاتك: العب حتى 3 نقلات على الرقعة، لا تُلعب، تُسجّل فقط.</li><li>اختر واحدة. بعدها يقيّم Stockfish كل مرشحاتك وأفضل نقلاته، فترى هل كانت الأفضل بين ما فكرت فيه.</li></ol>
    <p class="note">الموقف الذي تخطئ فيه يعود إليك لاحقًا. كل الشرح من Stockfish مباشرة في الصفحة، بلا استهلاك من Claude.</p>
    <div class="dpools">${pools.map((p) => { const ps = poolState(n, p.id); const acc = ps.moves ? Math.round(100 * ps.match / ps.moves) : null;
      return `<div class="stage"><div class="stage-h"><b>${esc(p.title)}</b><span class="state ${ps.done ? "on" : "part"}">${ps.done ? `${ps.done} موقف` : "جديد"}</span></div><p class="note">${esc(p.sub)}</p>
        ${ps.moves ? `<p class="note">نقلات بمستوى المحرك: <bdi class="mono">${acc}%</bdi> · أفضل نقلة كانت بين مرشحاتك: <bdi class="mono">${Math.round(100 * ps.candBest / ps.moves)}%</bdi>${ps.retry.length ? ` · تنتظرك ${ps.retry.length} للإعادة` : ""}</p>` : ""}
        <button class="btn" data-pool="${p.id}">ابدأ</button></div>`; }).join("")}</div>
    ${d.mates.length ? `<p class="note">محاولات الكش الأساسي: ${d.mates.length}، نجحت منها ${d.mates.filter((x) => x.ok).length}.</p>` : ""}</div>`;
  for (const b of $$("[data-pool]", box)) b.onclick = () => DrillSession($("#v-chapter"), n, pools.find((p) => p.id === b.dataset.pool));
  box.scrollIntoView?.({ block: "start" });
};

/* Random king + queen/rook against a lone king, the stronger side to move, not in check, not stalemate, and short enough
   for the chapter's limit (Stockfish's mate distance). */
async function randomBasicMate(kind) {
  const files = "abcdefgh"; const sq = () => files[Math.floor(Math.random() * 8)] + (1 + Math.floor(Math.random() * 8));
  const maxN = kind === "kqk" ? 8 : 15;
  for (let t = 0; t < 60; t++) {
    const col = Math.random() < 0.5 ? "w" : "b"; const opp = col === "w" ? "b" : "w";
    const g = new Chess(); g.clear();
    const a = sq(), q = sq(), k = sq(); if (new Set([a, q, k]).size < 3) continue;
    g.put({ type: "k", color: col }, a); g.put({ type: kind === "kqk" ? "q" : "r", color: col }, q); g.put({ type: "k", color: opp }, k);
    const fen = g.fen().replace(/ [wb] .*$/, ` ${col} - - 0 1`); const h = new Chess(fen); if (h.fen().split(" ")[0] !== fen.split(" ")[0]) continue;
    const other = new Chess(fen.replace(/ [wb] /, ` ${opp} `)); if (other.in_check()) continue; // the lone king may not stand in check with the strong side to move
    if (h.in_check() || h.game_over() || Math.abs(files.indexOf(a[0]) - files.indexOf(k[0])) <= 1 && Math.abs(+a[1] - +k[1]) <= 1) continue;
    const r = await Engine.analyse(fen, { depth: 18, movetime: 1500 });
    const m = r.lines[0] && r.lines[0].mate; if (m && m > 0 && m <= maxN && m >= 3) return { fen, kind, optimal: m };
  }
  return null;
}

function DrillSession(root, n, P) {
  const c = chapter(n); const set = J.state.settings; const ps = poolState(n, P.id); const mateGoal = P.goal === "mate";
  let tMove = 0; let item = null, game = null, me = "w", own = 0, cands = [], base = null, basePromise = null, recs = [], startFen = null, busy = false, optimal = null, token = 0;
  root.innerHTML = `
    <div class="whead"><button class="btn quiet" id="d-back">→ الفصل ${n}</button><div class="wtitle"><b>${esc(P.title)}</b><span class="note" id="d-prog"></span></div></div>
    <div class="watch">
      <div class="wboard"><div class="boardcap"><span class="turn" id="d-turn"></span><span class="note" id="d-status"></span></div>
        <div class="note" id="d-src"></div><div class="board" id="d-board"></div>
        <div class="cands" id="d-cands"></div>
        <label class="note bcheck"><input type="checkbox" id="d-fast" ${set.drillFast ? "checked" : ""}> سريع: العب النقلة مباشرة بلا مرشحات</label>
        <label class="note bcheck"><input type="checkbox" id="d-xp"> مساعدة: عندما ألمس قطعة، اشرح كل نقلاتها</label></div>
      <div class="wside"><div class="panel livecheck" id="d-plan"></div><div class="panel" id="d-x" hidden></div><div class="panel coachfeed"><div class="chat-h"><b>تحليل نقلاتك</b><span class="note">الأحدث في الأعلى</span></div><div id="d-feed" aria-live="polite"></div></div>
        <div class="panel" id="d-chat"></div></div>
    </div>`;
  const board = Board($("#d-board", root), { interactive: false }); const feed = $("#d-feed", root);
  const setStatus = (t) => { $("#d-status", root).textContent = t; };
  const card = (html, cls = "") => { const el = document.createElement("div"); el.className = "fcard " + cls; el.innerHTML = html; feed.prepend(el); while (feed.children.length > 30) feed.lastChild.remove(); return el; };
  $("#d-back", root).onclick = () => { token++; go("chapter", n); };
  $("#d-fast", root).onchange = (e) => { set.drillFast = e.target.checked; saveJourney(); };
  const alive = (t) => t === token && document.body.contains(root) && $("#d-board", root);
  const ctx = (fen) => Prob.ctx(fen, item && item.ply != null ? item.ply + 2 * own : 30);
  const esOf = (cpWhite, fen) => Prob.esFor(cpWhite, me, ctx(fen));
  const prog = () => { $("#d-prog", root).textContent = `الموقف ${ps.done + 1}${ps.moves ? ` · نقلات بمستوى المحرك ${Math.round(100 * ps.match / ps.moves)}%` : ""}`; };

  async function nextItem() {
    const t = ++token; feed.innerHTML = ""; recs = []; own = 0; cands = []; busy = true; drawCands();
    setStatus("أجهّز الموقف..."); board.update({ interactive: false, arrows: [], marks: {} });
    if (P.kind === "kqk" || P.kind === "krk") {
      const r = await randomBasicMate(P.kind); if (!alive(t)) return;
      if (!r) { setStatus("تعذّر توليد موقف. جرّب مرة أخرى."); return; }
      item = { fen: r.fen }; optimal = r.optimal;
      $("#d-src", root).textContent = `موقف عشوائي: ${P.kind === "kqk" ? "ملك ووزير" : "ملك ورخ"} ضد ملك. تقدير Stockfish: كش في ${movesAr(optimal)} تقريبًا، والحد ${P.kind === "kqk" ? 10 : 20}.`;
    } else {
      const items = await drillPool(P.file); if (!alive(t)) return;
      const due = ps.retry.filter((x) => x.due <= now());
      let idx;
      if (due.length && Math.random() < 0.4) { idx = due[0].i; ps.retry = ps.retry.filter((x) => x !== due[0]); }
      else { const seen = new Set(ps.seen); for (let k = 0; k < 50; k++) { idx = Math.floor(Math.random() * items.length); if (!seen.has(idx)) break; } }
      item = { ...items[idx], i: idx }; optimal = item.m || null;
      $("#d-src", root).textContent = `من مباراة حقيقية على Lichess (متوسط تقييم اللاعبين ${item.r})، النقلة ${Math.floor(item.ply / 2) + 1}.${P.srcNote ? " " + P.srcNote : ""}`;
    }
    startFen = item.fen; game = new Chess(item.fen); me = game.turn(); prog();
    card(`<p>${esc(P.task)}</p><p class="note">أنت ${me === "w" ? "بالأبيض" : "بالأسود"}. ${mateGoal ? "الهدف: كش مات بأقصر طريق، بلا stalemate." : `تلعب ${P.own} نقلات من هنا.`}</p>${methodHtml(P).replace("<details class=\"method\" open>", ps.done >= 3 ? "<details class=\"method\">" : "<details class=\"method\" open>")}`, "hint");
    myTurn(t);
  }
  function myTurn(t) {
    if (!alive(t)) return;
    const fen = game.fen(); base = null; cands = [];
    basePromise = Engine.analyse(fen, { depth: mateGoal ? 20 : 15, movetime: 1600, multipv: 3 }); basePromise.then((r) => { if (game.fen() === fen) base = r; }, () => {});
    busy = false; drawCands(); tMove = now();
    $("#d-turn", root).innerHTML = `<i class="${me}"></i>دورك`; $("#d-plan", root).innerHTML = planHtml(fen, item && item.ply != null ? item.ply + 2 * own : 40);
    board.update({ fen, orient: me, interactive: true, arrows: [], onMove: (m) => onCandidate(m, t) });
    setStatus(set.drillFast ? "العب نقلتك." : "سجّل مرشحاتك على الرقعة (حتى 3)، ثم اختر واحدة.");
  }
  function onCandidate(m, t) {
    if (busy) return;
    if (set.drillFast) { cands = [m]; return choose(m, t); }
    if (!cands.some((x) => x.uci === m.uci)) { if (cands.length >= 3) cands.shift(); cands.push(m); }
    board.update({ fen: game.fen(), interactive: true, arrows: cands.map((x) => ({ from: x.uci.slice(0, 2), to: x.uci.slice(2, 4), color: "alt" })) });
    drawCands(t);
  }
  function drawCands(t) {
    const el = $("#d-cands", root);
    if (!cands.length || set.drillFast) { el.innerHTML = ""; return; }
    el.innerHTML = `<span class="note">مرشحاتك:</span> ${cands.map((x, i) => `<span class="cand"><button class="chip-q on" data-play="${i}">العب ${esc(x.san)}</button><button class="chip-q" data-del="${i}" aria-label="احذف">✕</button></span>`).join(" ")}`;
    for (const b of $$("[data-play]", el)) b.onclick = () => choose(cands[+b.dataset.play], t);
    for (const b of $$("[data-del]", el)) b.onclick = () => { cands.splice(+b.dataset.del, 1); board.update({ arrows: cands.map((x) => ({ from: x.uci.slice(0, 2), to: x.uci.slice(2, 4), color: "alt" })) }); drawCands(t); };
  }
  async function choose(m, t) {
    if (busy) return; busy = true;
    const fen = game.fen(); const myCands = cands.slice(); drawCands(); $("#d-cands", root).innerHTML = "";
    board.update({ fen: m.fenAfter, last: m.uci, interactive: false, arrows: [] }); setStatus("Stockfish يقيّم نقلتك ومرشحاتك...");
    const cd = card(`<div class="fh"><bdi class="mv">${esc(moveLabel(fen, m.san))}</bdi><span class="note">يقيّم...</span></div>`, "mine");
    let b; try { b = base || await basePromise; } catch { b = null; }
    if (!alive(t)) return;
    if (!b || !b.lines.length) { setStatus("تعذّر تشغيل Stockfish."); return; }
    // every candidate gets its own score (searchmoves), so it is compared on the same footing as Stockfish's moves
    const score = {}; for (const l of b.lines) score[l.pv[0]] = l;
    for (const x of myCands) if (!score[x.uci]) { const r = await Engine.analyse(fen, { depth: mateGoal ? 16 : 13, movetime: 900, searchmoves: [x.uci] }); if (r.lines[0]) score[x.uci] = r.lines[0]; }
    if (!alive(t)) return;
    game.move(m.san); own++;
    const rec = rate(fen, m, b, score, myCands);
    rec.secs = Math.max(1, Math.round((now() - tMove) / 1000)); recs.push(rec); renderRec(cd, rec, fen, b, myCands, score);
    const over = finished(rec);
    if (over) return endItem(over, t);
    $("#d-turn", root).innerHTML = `<i class="${me === "w" ? "b" : "w"}"></i>دور الخصم`; setStatus("الخصم يرد (Stockfish، أفضل دفاع)...");
    const r = await Engine.analyse(game.fen(), { depth: mateGoal ? 18 : 14, movetime: 1000 });
    if (!alive(t)) return;
    if (!r.best) return endItem(finished(rec, true) || "end", t);
    const om = game.move({ from: r.best.slice(0, 2), to: r.best.slice(2, 4), promotion: r.best[4] || "q" });
    board.update({ fen: game.fen(), last: r.best, arrows: [] });
    card(`<div class="fh"><bdi class="mv">${esc(moveLabel(fen, m.san) + " " + om.san)}</bdi><span class="note">رد الخصم: أفضل دفاع عند Stockfish</span></div>`, "theirs");
    if (game.game_over()) return endItem(game.in_checkmate() ? "mated" : "draw", t);
    myTurn(t);
  }
  function rate(fen, m, b, score, myCands) {
    const best = b.lines[0]; const bestUci = best.pv[0]; const mine = score[m.uci];
    const rec = { san: m.san, uci: m.uci, fen, best: sanOf(fen, bestUci), bestUci, candBest: myCands.some((x) => x.uci === bestUci) || m.uci === bestUci, nc: myCands.length };
    const after = new Chess(m.fenAfter);
    if (mateGoal) {
      const nBest = best.mate && best.mate > 0 ? best.mate : null; const nMine = after.in_checkmate() ? 0 : mine && mine.mate && mine.mate > 0 ? mine.mate - 1 : null;
      rec.stalemate = after.in_stalemate() || after.in_draw();
      rec.nBest = nBest; rec.nMine = nMine;
      rec.ok = !rec.stalemate && nMine != null && nBest != null && nMine <= nBest - 1;
      rec.cls = rec.stalemate ? "blunder" : nMine == null ? "blunder" : rec.ok ? "excellent" : nMine - (nBest - 1) <= 2 ? "good" : "inaccuracy";
      rec.match = rec.ok;
    } else {
      const esB = esOf(best.cpWhite, fen), esA = mine ? esOf(mine.cpWhite, fen) : esB - 30;
      const cl = m.uci === bestUci ? { cls: "excellent", drop: 0 } : Prob.classify(esB, esA);
      Object.assign(rec, { esB: Math.round(esB), esA: Math.round(esA), cls: cl.cls, drop: cl.drop, match: cl.drop <= 2 });
    }
    ps.moves++; if (rec.match) ps.match++; if (rec.candBest) ps.candBest++;
    return rec;
  }
  function renderRec(cd, rec, fen, b, myCands, score) {
    const line = (l) => { const s = sanOf(fen, l.pv[0]); const v = mateGoal ? (l.mate && l.mate > 0 ? `كش في ${l.mate}` : "بلا كش قسري") : `${Math.round(esOf(l.cpWhite, fen))}%`; return `<bdi class="mv">${esc(s)}</bdi> <span class="note">${v}</span>`; };
    const candHtml = myCands.length > 1 || (myCands.length === 1 && myCands[0].uci !== rec.uci) ? `<p class="note">مرشحاتك: ${myCands.map((x) => (score[x.uci] ? line(score[x.uci]) : `<bdi class="mv">${esc(x.san)}</bdi>`) + (x.uci === rec.uci ? " (لعبتها)" : "")).join(" · ")}</p>` : "";
    const verdict = mateGoal
      ? (rec.stalemate ? "stalemate: الخصم لا يملك نقلة قانونية وملكه ليس في كش. تعادل، وضاع الفوز." : rec.nMine === 0 ? "كش مات." : rec.nMine == null ? "ضاع الكش القسري بهذه النقلة." : rec.ok ? `أقصر طريق: كش في ${rec.nMine} بعد رد الخصم.` : `ما زال الكش قائمًا لكنه أبعد: ${rec.nMine} بدل ${rec.nBest - 1}.`)
      : `فرصك <bdi class="mono">${rec.esB}%</bdi> ← <bdi class="mono">${rec.esA}%</bdi>.`;
    const why = rec.uci === rec.bestUci ? [] : bestMoveWhy(fen, rec.best, rec.bestUci, null);
    cd.innerHTML = `<div class="fh"><bdi class="mv">${esc(moveLabel(fen, rec.san))}</bdi><span class="cls ${rec.cls}">${CLASS_AR[rec.cls]}</span>${rec.uci === rec.bestUci ? `<span class="tag best">نقلة المحرك الأولى</span>` : ""}</div>
      <p>${verdict}</p>${candHtml}
      ${rec.uci !== rec.bestUci ? `<p>الأفضل: <bdi class="mv">${esc(rec.best)}</bdi>. ${rec.candBest ? "كانت بين مرشحاتك: الاختيار هو ما يحتاج تدريبًا." : rec.nc ? "لم تكن بين مرشحاتك: ابحث عن نقلات من هذا النوع في المرة القادمة." : ""}</p>${why.length ? `<ul class="facts">${why.map((x) => `<li>${fmtNote(x)}</li>`).join("")}</ul>` : ""}` : ""}
      <p class="note">أفضل نقلات Stockfish: ${b.lines.map(line).join(" · ")}</p>`;
  }
  function finished(rec, noReply = false) {
    if (game.in_checkmate()) return "mate";
    if (game.in_stalemate() || game.in_draw()) return "draw";
    if (mateGoal) {
      if (rec.nMine == null) return "lost";
      const limit = P.kind === "kqk" ? 10 : P.kind === "krk" ? 20 : (optimal || 4) + 3;
      if (own >= limit) return "limit";
      return null;
    }
    return own >= P.own || noReply ? "end" : null;
  }
  /* advice for this position: candidates, the big mistake, speed against your average for this pool */
  function drillAdvice() {
    const out = []; const avg = ps.secs || null; const mine = Math.round(recs.reduce((s, r) => s + (r.secs || 0), 0) / Math.max(1, recs.length));
    const withC = recs.filter((r) => r.nc > 0); const missB = withC.filter((r) => !r.candBest);
    if (set.drillFast) out.push("لعبت بلا مرشحات. الطريقة الأفضل: سجّل 2 أو 3 مرشحات قبل كل نقلة، وأولها دائمًا الكشات والأسر.");
    else if (missB.length) out.push(`أفضل نقلة لم تكن بين مرشحاتك في ${missB.length} من ${withC.length}. ابدأ مرشحاتك بالنقلات القسرية (كش، أسر، تهديد)، ثم نقلة تحسّن أسوأ قطعة.`);
    else if (withC.length) out.push("أفضل نقلة كانت دائمًا بين مرشحاتك: رؤيتك جيدة، ركّز الآن على الاختيار بينها (أيها يترك قطعًا بلا حماية؟).");
    const worst = recs.slice().sort((a, b) => (b.drop || 0) - (a.drop || 0))[0];
    if (worst && (mateGoal ? !worst.ok : (worst.drop || 0) >= 10)) out.push(`أكبر خطأ: [${worst.san}] (الأفضل [${worst.best}]). قبل نقلة كهذه طبّق الخطوة الأخيرة من «أفضل طريقة».`);
    out.push(avg ? (mine > avg * 1.3 ? `متوسطك هنا ${mine} ثانية للنقلة، أبطأ من معدلك (${avg}). ${P.fast || ""}` : mine < avg * 0.8 ? `متوسطك ${mine} ثانية للنقلة، أسرع من معدلك (${avg}).` : `متوسطك ${mine} ثانية للنقلة (معدلك ${avg}).`) : `متوسطك ${mine} ثانية للنقلة.`);
    ps.secs = avg ? Math.round(avg * 0.7 + mine * 0.3) : mine;
    return `<div class="advice"><b>نصيحة لتتحسن</b><ul class="facts">${out.map((x) => `<li>${fmtNote(x)}</li>`).join("")}</ul></div>`;
  }
  function endItem(why, t) {
    if (!alive(t)) return;
    busy = true; board.update({ interactive: false });
    const okMoves = recs.filter((r) => r.match).length; const bad = recs.some((r) => (mateGoal ? !r.ok && r.cls === "blunder" : r.drop >= 10));
    let ok = !bad && okMoves * 2 >= recs.length;
    let head;
    if (mateGoal) {
      ok = why === "mate";
      head = why === "mate" ? `كش مات في ${movesAr(own)}${optimal ? ` (تقدير Stockfish عند البداية: ${movesAr(optimal)})` : ""}.` : why === "draw" ? "انتهى الموقف بالتعادل (stalemate أو تكرار): ضاع الفوز." : why === "lost" ? "ضاع الكش القسري." : `وصلت إلى الحد (${own} نقلة) بلا كش مات.`;
      if (P.kind === "kqk" || P.kind === "krk") drillState(n).mates.push({ kind: P.kind, moves: own, optimal, ok, stalemate: why === "draw", t: now() });
    } else head = `${okMoves} من ${recs.length} نقلات بمستوى المحرك (الأفضل أو قريبة منها جدًا).${item.x ? ` في المباراة الحقيقية لُعب هنا ${item.x}، وخسر صاحبه مادة أو موقفًا.` : ""}`;
    ps.done++; drillState(n).count = (drillState(n).count || 0) + 1;
    if (item.i != null) { ps.seen.push(item.i); if (ps.seen.length > 600) ps.seen.splice(0, ps.seen.length - 600); if (!ok) ps.retry.push({ i: item.i, due: now() + 10 * 60000 }); }
    const candB = recs.filter((r) => r.candBest).length;
    saveJourney(); checkChapterComplete(n);
    const prog2 = ruleProgress(c);
    const cd = card(`<div class="fh"><b>${ok ? "أحسنت" : "انتهى الموقف"}</b></div><p>${esc(head)}</p>
      ${set.drillFast ? "" : `<p class="note">أفضل نقلة كانت بين مرشحاتك في ${candB} من ${recs.length}.</p>`}
      ${!ok && item.i != null ? `<p class="note">سيعود إليك هذا الموقف لاحقًا.</p>` : ""}
      ${drillAdvice()}
      ${c.rule.kind === "mates" ? `<p class="note">شرط الفصل: <bdi class="mono">${prog2.have}/${prog2.need}</bdi> ${esc(prog2.unit)}.</p>` : ""}
      <div class="row"><button class="btn" data-a="next">الموقف التالي</button><button class="btn quiet" data-a="again">أعد هذا الموقف</button></div>`, "end");
    $('[data-a="next"]', cd).onclick = () => nextItem();
    $('[data-a="again"]', cd).onclick = () => { const it = item, op = optimal; const t2 = ++token; feed.innerHTML = ""; recs = []; own = 0; item = it; optimal = op; game = new Chess(startFen); card(`<p>${esc(P.task)}</p>`, "hint"); myTurn(t2); };
    setStatus(ok ? "أحسنت. الموقف التالي جاهز." : "انتهى الموقف.");
  }
  $("#d-xp", root).onchange = (e) => { $("#d-x", root).hidden = !e.target.checked; if (!e.target.checked) board.update({ marks: {} }); else $("#d-x", root).innerHTML = `<p class="note">المس قطعة لك لترى نقلاتها مشروحة.</p>`; };
  board.update({ onSelect: (sq) => { if ($("#d-xp", root).checked && sq && game && game.turn() === me && !busy) explainPiece($("#d-x", root), board, game.fen(), sq, 40, () => document.body.contains(root)); } });
  window.DRILL_DEBUG = { fen: () => (game ? game.fen() : null) }; // read-only hook for the headless tests
  Chat($("#d-chat", root), { level: c.level, chips: ["ما النقلات القسرية هنا؟", "ما الخطة في هذا الموقف؟"], getContext: () => ({ fen: game ? game.fen() : START_FEN, ply: 30, start: startFen || START_FEN, moves: [], extra: `CONTEXT: A training position (${P.title}). Do not reveal the best move unless the student explicitly asks; teach how to find it.` }) });
  nextItem();
}
