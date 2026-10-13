"use strict";
/* Watch: a narrated demo game. Play / pause / step / speed, the odds bar, per-move narration,
   questions in the chat, and "what if" branches that return to the game. */

async function loadJSON(p) { const r = await fetch(p); if (!r.ok) throw new Error(p); return r.json(); }
const nullFenOf = (fen) => { const p = fen.split(" "); p[1] = p[1] === "w" ? "b" : "w"; p[3] = "-"; return p.join(" "); };
const moveLabel = (fenBefore, san) => { const p = fenBefore.split(" "); return `${p[5]}${p[1] === "w" ? "." : "..."} ${san}`; };

STAGE_RUNNERS.watch = (n) => {
  const c = chapter(n); const list = content(c).watch || []; const s = chState(n); const seen = new Set(s.watch.seen || []);
  const box = $("#stage-box");
  box.innerHTML = `<div class="panel"><h3>شاهد: مباريات مشروحة نقلة نقلة</h3>
    <p class="note">أشرح كل نقلة: ماذا تفعل، بماذا فكّر اللاعب، النقلات التي رفضها ولماذا، والخطة. أوقف متى شئت، واسأل، أو جرّب «ماذا لو؟».</p>
    <div class="demos">${list.map((d, k) => `<button class="demo" data-d="${k}"><b>${esc(d.title)}</b><span class="note">${esc(d.sub || "")}</span><span class="state ${seen.has(d.id) ? "on" : "part"}">${seen.has(d.id) ? "شاهدتها" : "لم تشاهدها"}</span></button>`).join("")}</div></div>`;
  for (const b of $$("[data-d]", box)) b.onclick = () => openWatch(n, list[+b.dataset.d]);
  box.scrollIntoView?.({ block: "start" });
};
async function openWatch(n, item) {
  const root = $("#v-chapter"); root.innerHTML = `<div class="panel"><p class="note">جارٍ تحميل المباراة...</p></div>`;
  try { const D = await loadJSON("data/curriculum/" + item.file); WatchPlayer(root, D, { n }); }
  catch (e) { console.error(e); root.innerHTML = `<div class="panel"><p class="err">تعذّر تحميل المباراة.</p><button class="btn" id="w-err-back">عودة</button></div>`; $("#w-err-back").onclick = () => go("chapter", n); }
}

function WatchPlayer(root, D, { n }) {
  const c = chapter(n); const P = D.plies; const last = P.length - 1; const side = D.narrated;
  const who = D.kind === "classic" ? (side === "w" ? D.white : D.black).split(" ").slice(-1)[0] : "المدرّب";
  let i = -1, playing = false, timer = null, speed = 1, branch = null, whatIfK = null;
  root.innerHTML = `
    <div class="whead"><button class="btn quiet" id="w-back">→ الفصل ${n}</button>
      <div class="wtitle"><b>${esc(D.title)}</b><span class="note" dir="ltr">${esc(D.white)} – ${esc(D.black)} · ${esc(D.event)}</span></div></div>
    <div class="watch">
      <div class="wboard">
        <div class="boardcap"><span class="turn" id="w-turn"></span><span class="note" id="w-prog"></span></div>
        <div class="board" id="w-board"></div>
        <div id="w-branch" hidden></div>
        <div class="wctrl" role="toolbar" aria-label="التحكم في المباراة">
          <button class="ctl" id="w-first">البداية</button>
          <button class="ctl" id="w-prev" aria-label="النقلة السابقة">→ السابقة</button>
          <button class="ctl main" id="w-play">تشغيل</button>
          <button class="ctl" id="w-next" aria-label="النقلة التالية">التالية ←</button>
          <button class="ctl" id="w-last">النهاية</button>
          <label class="speed">السرعة <select id="w-speed"><option value="0.6">بطيئة</option><option value="1" selected>عادية</option><option value="1.6">سريعة</option><option value="2.5">سريعة جدًا</option></select></label>
        </div>
        <div class="row"><button class="btn ghost" id="w-whatif">ماذا لو لُعبت نقلة أخرى هنا؟</button></div>
        <div id="w-odds"></div>
        <div class="moves wmoves" id="w-moves"></div>
      </div>
      <div class="wside">
        <div class="panel ncard" id="w-narr" aria-live="polite"></div>
        <div class="panel" id="w-chat"></div>
      </div>
    </div>`;
  const board = Board($("#w-board", root), { fen: D.start, orient: side, interactive: false });
  const narrEl = $("#w-narr", root), branchEl = $("#w-branch", root);
  $("#w-back", root).onclick = () => { stop(); go("chapter", n); };
  $("#w-first", root).onclick = () => { pause(); show(-1); };
  $("#w-prev", root).onclick = () => { pause(); if (branch) return stepBranch(-1); show(i - 1); };
  $("#w-next", root).onclick = () => { pause(); if (branch) return stepBranch(1); show(i + 1); };
  $("#w-last", root).onclick = () => { pause(); show(last); };
  $("#w-play", root).onclick = () => (playing ? pause() : play());
  $("#w-speed", root).onchange = (e) => { speed = +e.target.value; };
  $("#w-whatif", root).onclick = startWhatIf;
  const keys = (e) => {
    if (!document.body.contains(root) || $("#v-chapter").hidden || /INPUT|SELECT|TEXTAREA/.test(document.activeElement?.tagName || "")) return;
    if (e.key === "ArrowLeft") { e.preventDefault(); pause(); branch ? stepBranch(1) : show(i + 1); }
    else if (e.key === "ArrowRight") { e.preventDefault(); pause(); branch ? stepBranch(-1) : show(i - 1); }
    else if (e.key === " ") { e.preventDefault(); playing ? pause() : play(); }
  };
  if (window.__watchKeys) document.removeEventListener("keydown", window.__watchKeys);
  window.__watchKeys = keys; document.addEventListener("keydown", keys);

  /* ---- grounding of [SAN] groups, mirroring tools/build_demo.mjs ---- */
  const norm = (s) => s.replace(/[+#!?]/g, "");
  function roots(k) {
    if (k < 0) return [];
    const R = []; const p = P[k], q = P[k + 1];
    for (const l of p.lines) R.push({ start: p.fenBefore, sans: l.san });
    if (q) for (const l of q.lines) R.push({ start: q.fenBefore, sans: l.san });
    if (p.threat) R.push({ start: nullFenOf(p.fenBefore), sans: p.threat.san });
    if (q && q.threat) R.push({ start: nullFenOf(q.fenBefore), sans: q.threat.san });
    for (let j = k; j <= Math.min(last, k + 6); j++) R.push({ start: P[j].fenBefore, sans: P.slice(j).map((x) => x.san) });
    for (const e of p.extra || []) R.push({ start: p.fenBefore, sans: e.san });
    if (p.after && p.after.line) R.push({ start: p.fen, sans: p.after.line });
    return R;
  }
  const refs = []; // chips registry for the current card
  function rich(k, text, chain0) {
    if (!text) return "";
    const R = roots(k); let chain = chain0 ? [norm(chain0)] : []; let chainRoot = null; let out = ""; let pos = 0;
    if (chain0) chainRoot = R.find((r) => norm(r.sans[0] || "") === chain[0]) || null;
    for (const m of text.matchAll(/\[([^\]]+)\]/g)) {
      out += esc(text.slice(pos, m.index)); pos = m.index + m[0].length;
      const T = m[1].trim().split(/\s+/); const Tn = T.map(norm);
      const pre = (a, r) => a.length <= r.sans.length && a.every((t, x) => t === norm(r.sans[x]));
      let found = null;
      const cont = [...chain, ...Tn];
      if (chain.length) { const r = R.find((r) => pre(cont, r)); if (r) found = { start: r.start, seq: r.sans.slice(0, cont.length), show: T }; }
      if (!found) { const r = R.find((r) => pre(Tn, r)); if (r) found = { start: r.start, seq: r.sans.slice(0, Tn.length), show: T }; }
      if (found) { chain = found.seq.map(norm); refs.push(found); out += `<button type="button" class="mvref" data-ref="${refs.length - 1}">${esc(T.join(" "))}</button>`; }
      else out += `<bdi class="mv">${esc(T.join(" "))}</bdi>`;
    }
    return out + esc(text.slice(pos));
  }
  const plain = (t) => (t || "").replace(/\[([^\]]+)\]/g, "$1");

  /* ---- display ---- */
  function esAt(k) { // mover's chances before (best play) and after the move
    const p = P[k]; const c = Prob.ctx(p.fenBefore); return { before: Prob.esFor(p.lines[0].cp, p.color, c), after: Prob.esFor(p.after.cp, p.color, c) };
  }
  function show(k) {
    i = Math.max(-1, Math.min(last, k)); branch = null; whatIfK = null; branchEl.hidden = true;
    const fen = i < 0 ? D.start : P[i].fen;
    board.update({ fen, last: i < 0 ? null : P[i].uci, interactive: false, onMove: null, arrows: i < 0 ? [] : [{ from: P[i].uci.slice(0, 2), to: P[i].uci.slice(2, 4), color: P[i].color === side ? "good" : "alt" }] });
    const stm = sideOf(fen);
    $("#w-turn", root).innerHTML = `<i class="${stm}"></i>الدور ${stm === "w" ? "للأبيض" : "للأسود"}`;
    $("#w-prog", root).textContent = i < 0 ? `${P.length} نقلة` : `النقلة ${i + 1} من ${P.length}`;
    const cp = i < 0 ? P[0].lines[0].cp : P[i].after.cp, wdl = i < 0 ? P[0].lines[0].wdl : P[i].after.wdl;
    $("#w-odds", root).innerHTML = oddsBarHtml(cp, wdl, i < 0 ? { fen: D.start } : { prevCp: P[i].lines[0].cp, mover: P[i].color, fen: P[i].fen });
    narrEl.innerHTML = cardHtml(i); wireRefs(narrEl); levelLines(i);
    const mv = $("#w-moves", root); mv.innerHTML = movesHtml();
    for (const b of $$("[data-k]", mv)) b.onclick = () => { pause(); show(+b.dataset.k); };
    const on = $(".mvbtn.on", mv); if (on && on.scrollIntoView) on.scrollIntoView({ block: "nearest", inline: "nearest" });
    if (i === last) markSeen();
  }
  function movesHtml() {
    let h = "";
    P.forEach((p, k) => { const fb = p.fenBefore.split(" "); if (p.color === "w" || k === 0) h += `<span class="mnum">${fb[5]}${p.color === "w" ? "." : "..."}</span>`; h += `<button class="mvbtn ${k === i ? "on" : ""}" data-k="${k}">${esc(p.san)}</button>`; });
    return h;
  }
  function cardHtml(k) {
    refs.length = 0;
    if (k < 0) return `<h3>${esc(D.title)}</h3><p>${esc(D.intro)}</p><p class="note">اضغط «تشغيل» أو «التالية». أوقف متى شئت واسأل في المحادثة، أو جرّب «ماذا لو؟». النقلات المكتوبة بين الأسطر قابلة للنقر: تعرض الخط على الرقعة.</p>`;
    const p = P[k], nn = p.n || {}; const es = esAt(k); const cl = Prob.classify(es.before, es.after);
    let h = `<div class="nhead"><bdi class="mv big">${esc(moveLabel(p.fenBefore, p.san))}</bdi><span class="cls ${cl.cls}">${CLASS_AR[cl.cls]}</span><span class="who note">${p.color === side ? esc(who) : "الخصم"}</span></div>`;
    if (p.color === side) {
      h += sec("ماذا تفعل النقلة", rich(k, nn.does));
      h += sec(`بماذا فكّر ${esc(who)}`, rich(k, nn.think));
      if (nn.cands && nn.cands.length) {
        h += `<section class="cands"><h4>نقلات أخرى فكّر فيها، ولماذا رفضها</h4>${nn.cands.map((cd) => {
          const ces = cd.cp != null ? Math.round(Prob.esFor(cd.cp, p.color, Prob.ctx(p.fenBefore))) : null;
          return `<div class="cand"><div class="cand-h">${rich(k, "[" + cd.san + "]")}${ces != null ? `<span class="note">فرصه بعدها <bdi class="mono">${ces}%</bdi>، مقابل <bdi class="mono">${Math.round(es.after)}%</bdi> للنقلة المختارة</span>` : ""}</div><p>${rich(k, cd.why, cd.san)}</p></div>`; }).join("")}</section>`;
      }
      h += sec(`الخطة${nn.planChange ? ` <span class="tag plan">تغيّرت الخطة</span>` : ""}`, rich(k, nn.plan));
      if (nn.habit) h += `<div class="habit"><b>عادة تفكير:</b> ${rich(k, nn.habit)}</div>`;
      const q = P[k - 1];
      if (q && q.color !== side && q.n && q.n.intent) h += `<section class="opp"><h4>ماذا أراد الخصم بنقلته ${esc(moveLabel(q.fenBefore, q.san))}</h4><p>${rich(k - 1, q.n.intent)}</p></section>`;
    } else {
      h += sec("ماذا يريد الخصم بهذه النقلة", rich(k, nn.intent));
      if (nn.note) h += sec("تقييم النقلة", rich(k, nn.note));
    }
    if (k === last && D.outro) h += `<section class="outro"><h4>خلاصة المباراة</h4><p>${esc(D.outro)}</p></section>`;
    return h;
  }
  /* Under each move: what players at the student's level would have played here (Maia), and the masters' statistics. */
  async function levelLines(k) {
    if (k < 0) return; const p = P[k];
    const box = document.createElement("section"); box.className = "lvl"; narrEl.appendChild(box);
    const [h, ms] = await Promise.all([
      typeof Human !== "undefined" ? Human.predict(D.start, P.slice(0, k).map((x) => x.uci), Prob.band || 1100).catch(() => null) : null,
      mastersSummary(p.fenBefore, p.san)]);
    if (i !== k || !box.isConnected) return;
    const hs = humanSummary(h, p.uci); let html = "";
    if (hs) {
      const top = hs.top[0];
      html += `<p class="humanline">لو كان لاعب بمستوى ~${hs.rating} مكان ${p.color === side ? esc(who) : "الخصم"}: <bdi class="mono">${pctR(hs.p)}</bdi> منهم يلعبون <bdi class="mv">${esc(p.san)}</bdi>${top.uci === p.uci ? "، وهي اختيارهم الأول." : `، واختيارهم الأول <bdi class="mv">${esc(top.san)}</bdi> (<bdi class="mono">${pctR(top.p)}</bdi>).`}</p>`;
    }
    if (ms) html += `<p class="masterline">${mastersText(ms, p.san, "opp").replace("هذه النقلة", "النقلة")}</p>`;
    box.innerHTML = html ? `<h4>عند لاعبين بمستواك وعند الأساتذة</h4>${html}` : "";
  }
  const sec = (title, body) => (body ? `<section><h4>${title}</h4><p>${body}</p></section>` : "");
  function wireRefs(el) { for (const b of $$("[data-ref]", el)) b.onclick = () => { pause(); const r = refs[+b.dataset.ref]; openBranch({ start: r.start, sans: r.seq, title: `الخط: ${r.seq.join(" ")}` }); }; }

  /* ---- auto-play ---- */
  function readMs(k) {
    const p = P[k]; const txt = k < 0 ? D.intro : Object.values(p.n || {}).filter((v) => typeof v === "string").join(" ") + " " + ((p.n && p.n.cands) || []).map((x) => x.why).join(" ");
    return Math.min(24000, Math.max(2600, 1500 + txt.split(/\s+/).length * 280)) / speed;
  }
  function tick() { if (!playing) return; if (i >= last) return pause(); show(i + 1); timer = setTimeout(tick, readMs(i)); }
  function play() { if (branch) closeBranch(); if (i >= last) show(-1); playing = true; $("#w-play", root).textContent = "إيقاف"; timer = setTimeout(tick, i < 0 ? 500 : 900); }
  function pause() { playing = false; clearTimeout(timer); const b = $("#w-play", root); if (b) b.textContent = "تشغيل"; }
  function stop() { pause(); document.removeEventListener("keydown", keys); }

  /* ---- branches: [SAN] previews and "what if" ---- */
  function openBranch({ start, sans, title, whatIf = null }) {
    pause();
    const fens = [start], ucis = []; const g = new Chess(start);
    for (const s of sans) { const m = g.move(s, { sloppy: true }); if (!m) break; fens.push(g.fen()); ucis.push(m.from + m.to); }
    branch = { start, sans: sans.slice(0, ucis.length), fens, ucis, k: Math.min(1, ucis.length), title, whatIf };
    branchEl.hidden = false;
    branchEl.innerHTML = `<div class="branchbar"><div class="row" style="justify-content:space-between"><b>${esc(title)}</b><button class="btn quiet" id="b-back">عودة إلى المباراة</button></div>
      <div class="row"><button class="ctl" id="b-prev">→</button><span id="b-line" class="moves"></span><button class="ctl" id="b-next">←</button></div><div id="b-explain"></div></div>`;
    $("#b-back", branchEl).onclick = closeBranch; $("#b-prev", branchEl).onclick = () => stepBranch(-1); $("#b-next", branchEl).onclick = () => stepBranch(1);
    showBranch();
    branchEl.scrollIntoView?.({ block: "nearest" });
  }
  function showBranch() {
    const b = branch; board.update({ fen: b.fens[b.k], last: b.k ? b.ucis[b.k - 1] : null, arrows: b.k < b.ucis.length ? [{ from: b.ucis[b.k].slice(0, 2), to: b.ucis[b.k].slice(2, 4), color: "plan" }] : [], interactive: false, onMove: null });
    const fb = b.start.split(" "); let num = +fb[5], white = fb[1] === "w"; let h = "";
    b.sans.forEach((s, x) => { if (white || x === 0) h += `<span class="mnum">${num}${white ? "." : "..."}</span>`; h += `<span class="mvbtn ${x === b.k - 1 ? "on" : ""}">${esc(s)}</span>`; if (!white) num++; white = !white; });
    $("#b-line", branchEl).innerHTML = h;
  }
  function stepBranch(d) { if (!branch) return; branch.k = Math.max(0, Math.min(branch.ucis.length, branch.k + d)); showBranch(); }
  function closeBranch() { const k = i; branch = null; show(k); }

  function startWhatIf() {
    pause(); const k = Math.max(0, i); const p = P[k]; whatIfK = k; branch = null;
    board.update({ fen: p.fenBefore, last: k > 0 ? P[k - 1].uci : null, arrows: [], interactive: true, onMove: (m) => runWhatIf(k, m) });
    branchEl.hidden = false;
    branchEl.innerHTML = `<div class="branchbar"><div class="row" style="justify-content:space-between"><b>ماذا لو؟ اختر على الرقعة نقلة بدل ${esc(moveLabel(p.fenBefore, p.san))}</b><button class="btn quiet" id="b-cancel">إلغاء</button></div><p class="note">الدور ${p.color === "w" ? "للأبيض" : "للأسود"}. سيكمل Stockfish الخط، وأشرح ما يحدث، ثم تعود إلى المباراة.</p></div>`;
    $("#b-cancel", branchEl).onclick = () => show(k);
  }
  async function runWhatIf(k, m) {
    const p = P[k]; board.update({ interactive: false, onMove: null });
    const label = `ماذا لو ${moveLabel(p.fenBefore, m.san)} بدل ${p.san}؟`;
    branchEl.innerHTML = `<div class="branchbar"><b>${esc(label)}</b><p class="note">Stockfish يحلّل...</p></div>`;
    const a = await Engine.analyse(m.fenAfter, { depth: 18, movetime: 1800 });
    const reply = a.lines[0] ? pvToSan(m.fenAfter, a.lines[0].pv, 7) : [];
    const wc = Prob.ctx(p.fenBefore); const esX = Math.round(Prob.esFor(a.cp, p.color, wc)), esPlayed = Math.round(Prob.esFor(p.after.cp, p.color, wc));
    openBranch({ start: p.fenBefore, sans: [m.san, ...reply], title: label, whatIf: true });
    const same = m.uci === p.uci; const sideAr2 = p.color === "w" ? "الأبيض" : "الأسود";
    const ex = $("#b-explain", branchEl);
    ex.innerHTML = `<p>${same ? "هذه هي نقلة المباراة نفسها." : `بعد <bdi class="mv">${esc(m.san)}</bdi> أفضل رد حسب Stockfish: <bdi class="mv">${esc(reply[0] || "–")}</bdi>. فرص ${sideAr2} تصبح حوالي <bdi class="mono">${esX}%</bdi>، مقابل <bdi class="mono">${esPlayed}%</bdi> بعد نقلة المباراة <bdi class="mv">${esc(p.san)}</bdi>.`}</p><div id="b-claude"></div>`;
    if (!same && SAMPLE) explainWhatIf($("#b-claude", ex), k, m, reply, esX, esPlayed, a);
  }
  async function explainWhatIf(el, k, m, reply, esX, esPlayed, a) {
    const p = P[k]; el.innerHTML = coachHtml("المدرّب", "يكتب...");
    const factsX = Facts.describe(Facts.positionFacts(m.fenAfter), p.color), factsP = Facts.describe(Facts.positionFacts(p.fen), p.color);
    const prompt = `${COACH_RULES}\n${LEVEL_RULES[c.level] || ""}
TASK: The student paused a narrated game and asked "what if ${m.san} instead of ${p.san}?". In Arabic, 3-5 sentences: what ${m.san} does, what the opponent's best reply shows, and why the game move was better or worse. Finish with one reusable thinking habit.
DATA:
POSITION BEFORE THE MOVE: ${p.fenBefore} (${p.color === "w" ? "White" : "Black"} to move)
PIECES: ${pieceList(p.fenBefore)}
STUDENT'S MOVE: ${m.san}; Stockfish best continuation after it: ${reply.join(" ")}; ${p.color === "w" ? "White" : "Black"}'s chances afterwards ≈ ${esX}%
GAME MOVE: ${p.san}; chances afterwards ≈ ${esPlayed}%; best line after the game move: ${(p.after.line || []).join(" ")}
ENGINE TOP LINES BEFORE THE MOVE: ${p.lines.map((l) => l.san.slice(0, 6).join(" ")).join(" | ")}
FACTS AFTER ${m.san}: ${factsX.join(" ")}
FACTS AFTER ${p.san}: ${factsP.join(" ")}`;
    const allowed = allowedFrom(p.fenBefore, [[m.san, ...reply], [p.san, ...(p.after.line || [])], ...p.lines.map((l) => l.san)]);
    try {
      const t = await askClaude(prompt, { tier: "quick", cache: { gcTime: 86400000 }, onText: (x) => { el.innerHTML = coachHtml("المدرّب · مقيّد بخطوط Stockfish", markSan(esc(x.text), null).html); } });
      const { html, bad } = markSan(esc(t), allowed);
      el.innerHTML = coachHtml("المدرّب · مقيّد بخطوط Stockfish", html + (bad.length ? `<br><span class="note warnline">لم أتحقق من: ${bad.map(esc).join("، ")}</span>` : ""));
    } catch (e) { el.innerHTML = coachHtml("المدرّب", esc(claudeMsg(e))); }
  }

  function markSeen() {
    const s = chState(n); s.watch.seen = s.watch.seen || [];
    if (!s.watch.seen.includes(D.id)) { s.watch.seen.push(D.id); s.watch.done = true; s.watch.t = now(); saveJourney(); narrEl.insertAdjacentHTML("beforeend", `<div class="callout good">اكتملت مرحلة «شاهد» لهذا الفصل. التالي: «العب».</div>`); }
  }

  Chat($("#w-chat", root), {
    level: c.level,
    chips: ["لماذا هذه النقلة؟", "ما أخطر تهديد في هذا الموقف؟", "ما خطة كل طرف الآن؟", "ما العادة التي أتعلمها من هذه اللحظة؟"],
    onOpen: pause,
    getContext: () => {
      if (branch) {
        const fen = branch.fens[branch.k];
        return { fen, ply: i + 1, start: branch.start, moves: branch.sans.slice(0, branch.k), knownLines: [branch.sans], narration: `The student is looking at a side line: ${branch.title} ${branch.sans.join(" ")}` };
      }
      const k = i; const fen = k < 0 ? D.start : P[k].fen; const nxt = P[k + 1];
      const nn = k >= 0 ? P[k].n || {} : {};
      const narration = k < 0 ? plain(D.intro) : [nn.does, nn.think, nn.plan, nn.intent, nn.note].filter(Boolean).map(plain).join("\n");
      return { fen, ply: k + 1, start: D.start, moves: P.slice(0, k + 1).map((p) => p.san), engineLines: nxt ? nxt.lines : [], threat: nxt && nxt.threat ? nxt.threat.san : null, knownLines: [P.slice(k + 1).map((p) => p.san)], narration };
    },
  });
  show(-1);
}
