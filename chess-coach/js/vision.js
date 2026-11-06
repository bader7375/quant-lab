"use strict";
/* Board vision (تدريب العين): short tap-only drills on positions from real games that train what you see at a glance:
   what each piece reaches, what you protect, what you attack, what attacks you, loose pieces, who defends a piece, the
   attacker/defender count, what the opponent's last move changed, and a "flash" version from memory. Each drill has a
   level (fewer pieces first), a method, a shortcut, and advice from what you missed; a daily mixed set of 10. Plus the
   in-game "vision lens" overlay. Attacks are counted as lines of sight (a pinned piece still counts); no engine, no Claude. */
const VG_DRILLS = [
  { id: "piece", title: "مدى القطعة", ask: (x) => `اضغط كل مربع يصل إليه ${x.name} المؤطَّر (حتى أول قطعة في كل خط، ويشمل مربعها).`,
    best: ["سمِّ القطعة واتجاهاتها: الرخ 4 خطوط، الفيل 4 أقطار، الوزير 8، الحصان 8 قفزات.", "امشِ على كل خط مربعًا مربعًا حتى أول قطعة، ثم توقف.", "للحصان: كل قفزة تغيّر لون المربع."], fast: "لا تعدّ المربعات الفارغة واحدًا واحدًا: انظر إلى نهاية كل خط (أول قطعة أو حافة الرقعة) واضغط ما بينهما دفعة واحدة." },
  { id: "defend", title: "ماذا أحمي؟", ask: () => "اضغط كل قطعة لك (غير الملك) تحميها قطعة أخرى لك، ثم «تحقّق».",
    best: ["ابدأ بالبيادق: كل بيدق يحمي مربعين قطريين أمامه.", "ثم الحصانان: قفزاتهما نحو قطعك.", "ثم الخطوط الطويلة: الرخان والفيلان والوزير، حتى أول قطعة.", "والملك يحمي ما حوله."], fast: "اسأل عن كل قطعة «من يراها من لوني؟» بدل أن تتتبع كل قطعة: إن وجدت حارسًا واحدًا انتقل إلى التالية." },
  { id: "attack", title: "ماذا أهاجم؟", ask: () => "اضغط كل قطعة للخصم (غير الملك) تهاجمها إحدى قطعك، ثم «تحقّق».",
    best: ["ابدأ بقطعك الطويلة: الوزير ثم الرخان ثم الفيلان، كل خط حتى أول قطعة.", "ثم الحصانان: 8 قفزات لكل واحد.", "ثم بيادقك: مربعان قطريان أمام كل بيدق."], fast: "انظر إلى قطع الخصم المتقدمة في نصفك أولًا: هي غالبًا داخل مدى قطعك." },
  { id: "threat", title: "ماذا يهاجمني؟", ask: () => "اضغط كل قطعة لك (غير الملك) تهاجمها إحدى قطع الخصم (أو لا شيء)، ثم «تحقّق».",
    best: ["ابدأ بحصاني الخصم: أكثر ما يفوت العين.", "ثم خطوط وزيره ورخيه وفيليه نحو قطعك.", "ثم بيادقه: مربعان قطريان أمام كل بيدق."], fast: "انظر إلى قطع الخصم التي تحركت مؤخرًا والخطوط التي فتحتها: هناك معظم الهجمات الجديدة." },
  { id: "loose", title: "القطع غير المحمية", ask: () => "اضغط كل قطعة لك (غير البيادق والملك) لا تحميها أي قطعة لك (أو لا شيء)، ثم «تحقّق».",
    best: ["ابدأ بالقطع المتقدمة خارج صفيك الأولين.", "ثم الحصانين: نادرًا ما يحميهما شيء.", "لكل قطعة: هل يراها بيدق أو حصان أو قطعة على خطها من لونك؟"], fast: "«القطع غير المحمية تسقط»: القطعة البعيدة عن ملكك وبيادقك هي المرشحة الأولى." },
  { id: "defenders", title: "من يحمي هذه القطعة؟", ask: (x) => `اضغط كل قطعة لك تحمي ${x.name} المؤطَّر (أو لا شيء).`,
    best: ["انظر من القطعة نفسها إلى الخارج: الأقطار الأربعة، ثم الأعمدة والصفوف، ثم مربعات قفزة الحصان، ثم البيادق خلفها قطريًا.", "على كل خط: أول قطعة من لونك تراها هي حارس إذا كانت تتحرك في ذلك الاتجاه."], fast: "ابدأ بالبيادق خلف القطعة قطريًا وبالحصانين: هما الحارسان الأكثر نسيانًا والأسهل رؤية." },
  { id: "count", title: "عُدّ المهاجمين والمدافعين", ask: (x) => `${x.name} المؤطَّر: كم قطعة تهاجمه، وكم قطعة تحميه؟`,
    best: ["عُدّ المهاجمين (من لون الخصم) بالترتيب: بيادق، حصانان، أقطار، أعمدة وصفوف، الملك.", "ثم المدافعين (من لون القطعة) بالترتيب نفسه.", "القاعدة: إذا كان المهاجمون أكثر، أو أرخص من القطعة، فهي في خطر."], fast: "استعمل الترتيب نفسه في كل مرة: البيادق، الحصانان، الخطوط، الملك. الترتيب الثابت يجعل العدّ سريعًا ولا يفوّت شيئًا." },
  { id: "changed", title: "ماذا تغيّر بنقلة الخصم؟", ask: (x) => `الخصم لعب ${x.san}. اضغط كل قطعة لك أصبحت مهاجَمة بسبب هذه النقلة (والملك إذا صار في كش)، أو لا شيء.`,
    best: ["انظر إلى القطعة التي تحركت: ماذا تهاجم من مربعها الجديد؟", "انظر إلى المربع الذي غادرته: هل فتح خطًا لقطعة خلفه (هجوم مكشوف)؟", "هل صار ملكك في كش؟"], fast: "سؤالان فقط بعد كل نقلة للخصم: ماذا تهاجم القطعة؟ وماذا كشفت خلفها؟" },
  { id: "flash", title: "ومضة: من الذاكرة", unlock: 2, ask: (x) => `انظر إلى الموقف ${x.secs} ثوانٍ. ستختفي القطع، ثم اضغط مربعات قطع الخصم التي تهاجمها.`,
    best: ["في الثواني الأولى: حدد قطعك الطويلة وخطوطها.", "ثم قطع الخصم على تلك الخطوط.", "رتّب ما رأيته بجملة قصيرة: «فيلي يرى حصانه، رخي يرى بيدقه»."], fast: "لا تحفظ الرقعة كلها: احفظ الأهداف فقط (قطع الخصم التي على خطوطك)." },
];
const VG_POOLS = ["ch03-mates.json", "ch04-tactics.json", "ch06-plans.json", "ch02-safety.json"];
const VG_MAXP = { 1: 16, 2: 24, 3: 32 }; // pieces on the board by level
const VG_TIME = { 1: 25, 2: 20, 3: 15 }; // average seconds needed to move up
function vgState() { const v = (J.state.vision = J.state.vision || { drills: {}, sessions: [] }); return v; }
function vgDrillState(id) { const v = vgState(); return v.drills[id] || (v.drills[id] = { n: 0, last: [], times: [], level: 1 }); }
const vgAcc = (s) => { const l = s.last.slice(-10); return l.length ? Math.round(100 * l.filter(Boolean).length / l.length) : null; };
const vgAvg = (s) => (s.times.length ? Math.round(s.times.reduce((a, b) => a + b, 0) / s.times.length) : null);
const VG_NAME = (G, s) => `${Facts.NAME_AR[G[s].type]} على ${s}`;
function vgHow(G, from, to) { // how the piece on `from` reaches `to`, in words
  const p = G[from]; const N = Facts.NAME_AR;
  if (p.type === "n") return `${N.n} ${from} بقفزة`;
  if (p.type === "p") return `${N.p} ${from} قطريًا للأمام`;
  if (p.type === "k") return `${N.k} ${from} من جانبه`;
  const line = from[0] === to[0] ? "على العمود" : from[1] === to[1] ? "على الصف" : "على القطر";
  return `${N[p.type]} ${from} ${line}`;
}

/* ---------- questions ---------- */
async function vgPosition(level, need) { // a real-game position with at most VG_MAXP[level] pieces, passing `need`
  for (let tries = 0; tries < 400; tries++) {
    const file = VG_POOLS[Math.floor(Math.random() * VG_POOLS.length)]; const items = await drillPool(file);
    const it = items[Math.floor(Math.random() * items.length)]; const g = new Chess(it.fen); if (g.in_check() || g.game_over()) continue;
    const G = Facts.grid(g); const np = Object.keys(G).length;
    if (np > VG_MAXP[level] && tries < 300) continue;
    const q = need(it, g, G); if (q) return { it, g, G, ...q };
  }
  return null;
}
function vgMakeQuestion(id, level) {
  const withPawns = level >= 3;
  const mine = (G, me, s, pawns = withPawns) => G[s].color === me && G[s].type !== "k" && (pawns || G[s].type !== "p");
  return vgPosition(level, (it, g, G) => {
    const me = g.turn(), opp = me === "w" ? "b" : "w"; const att = (s, c) => Facts.attackers(G, s, c);
    if (id === "piece") {
      const cands = Object.keys(G).filter((s) => G[s].color === me && "nbrq".includes(G[s].type)); if (!cands.length) return null;
      const sq = cands[Math.floor(Math.random() * cands.length)]; const truth = new Set();
      for (const f of "abcdefgh") for (let r = 1; r <= 8; r++) { const t = f + r; if (t !== sq && att(t, me).some((a) => a.sq === sq)) truth.add(t); }
      return { me, sel: sq, name: VG_NAME(G, sq), truth };
    }
    if (id === "defend") { const truth = new Set(Object.keys(G).filter((s) => mine(G, me, s) && att(s, me).length)); return { me, truth }; }
    if (id === "attack" || id === "flash") { const truth = new Set(Object.keys(G).filter((s) => G[s].color === opp && G[s].type !== "k" && (withPawns || id === "flash" || G[s].type !== "p") && att(s, me).length)); return truth.size ? { me, truth, secs: { 1: 8, 2: 6, 3: 4 }[level] } : null; }
    if (id === "threat") { const truth = new Set(Object.keys(G).filter((s) => mine(G, me, s) && att(s, opp).length)); return { me, truth }; }
    if (id === "loose") { const truth = new Set(Object.keys(G).filter((s) => mine(G, me, s, false) && !att(s, me).length)); return { me, truth }; }
    if (id === "defenders") {
      const cands = Object.keys(G).filter((s) => mine(G, me, s, false)); if (!cands.length) return null;
      const sq = cands[Math.floor(Math.random() * cands.length)]; return { me, sel: sq, name: VG_NAME(G, sq), truth: new Set(att(sq, me).map((a) => a.sq)) };
    }
    if (id === "count") {
      const cands = Object.keys(G).filter((s) => G[s].type !== "k" && G[s].type !== "p" && att(s, G[s].color === "w" ? "b" : "w").length); if (!cands.length) return null;
      const sq = cands[Math.floor(Math.random() * cands.length)]; const c = G[sq].color, o = c === "w" ? "b" : "w";
      return { me, sel: sq, name: `${Facts.NAME_AR[G[sq].type]} ${c === me ? "لك" : "الخصم"} على ${sq}`, counts: { a: att(sq, o).length, d: att(sq, c).length } };
    }
    if (id === "changed") {
      if (!it.mv) return null; // master positions carry the move that was played
      const h = new Chess(it.fen); const m = h.move({ from: it.mv.slice(0, 2), to: it.mv.slice(2, 4), promotion: it.mv[4] || "q" }); if (!m) return null;
      const G1 = Facts.grid(h); const victim = h.turn(), mover = m.color;
      const before = new Set(Object.keys(G).filter((s) => G[s].color === victim && Facts.attackers(G, s, mover).length));
      const truth = new Set(Object.keys(G1).filter((s) => G1[s].color === victim && (G1[s].type !== "p" || withPawns) && (G1[s].type !== "k" || h.in_check()) && Facts.attackers(G1, s, mover).length && !before.has(s)));
      if (!truth.size && Math.random() < 0.7) return null; // mostly moves that did change something
      return { me: victim, fen2: h.fen(), last: m.from + m.to, san: m.san, truth, G1 };
    }
    return null;
  }).then((q) => q && { ...q, id, level });
}

/* ---------- the gym ---------- */
function visionPanelHtml() {
  const v = vgState(); const today = new Date().toISOString().slice(0, 10); const done = v.sessions.some((s) => s.day === today);
  return `<div class="panel warm"><div class="row" style="justify-content:space-between"><div><span class="eyebrow">تدريب العين</span>
    <h3>رؤية الرقعة: ماذا أحمي؟ ماذا أهاجم؟</h3><p class="note">${done ? "أنهيت تمرين اليوم. تستطيع الإعادة أو اختيار تمرين محدد." : "10 أسئلة سريعة على مواقف حقيقية، 5 دقائق تقريبًا. كل يوم."}</p></div>
    <button class="btn" id="vg-go">تدريب العين</button></div></div>`;
}
function VisionGym(root) {
  const v = vgState();
  const card = (d) => { const s = vgDrillState(d.id); const acc = vgAcc(s); const locked = d.unlock && Math.max(...VG_DRILLS.map((x) => vgDrillState(x.id).level)) < d.unlock;
    return `<div class="tech ${acc != null && acc >= 80 ? "done" : ""}"><div class="fh"><b>${esc(d.title)}</b><span class="state ${locked ? "next" : "part"}">${locked ? "يُفتح في المستوى 2" : `المستوى ${s.level}`}</span></div>
      <p class="note">${s.n ? `دقة آخر 10: ${acc}% · متوسط الوقت ${vgAvg(s)} ث · المجموع ${s.n}` : "جديد"}</p><button class="btn quiet" data-vd="${d.id}" ${locked ? "disabled" : ""}>تدرّب</button></div>`; };
  root.innerHTML = `<div class="whead"><button class="btn quiet" id="vg-back">→ الرحلة</button><div class="wtitle"><b>تدريب العين: رؤية الرقعة</b><span class="note">كل الأسئلة على مواقف من مباريات حقيقية، بالضغط فقط</span></div></div>
    <div class="panel"><h3>كيف تدرّب عينك</h3><ol class="facts">
      <li><b>ترتيب ثابت للنظر:</b> بعد كل نقلة للخصم انظر دائمًا بالترتيب نفسه: الكشات، ثم الأسر، ثم التهديدات. الترتيب الثابت يصبح عادة سريعة.</li>
      <li><b>خطوط لا مربعات:</b> انظر إلى القطعة الطويلة كخطوط تنتهي عند أول قطعة. لا تعدّ المربعات الفارغة.</li>
      <li><b>الحصان أولًا:</b> قفزات الحصان أكثر ما يفوت العين. وتذكّر: كل قفزة تغيّر لون المربع.</li>
      <li><b>القطع غير المحمية تسقط:</b> اعرف في كل لحظة أي قطعة لك بلا حارس.</li>
      <li><b>ماذا تغيّر؟</b> القطعة التي تحركت، والخط الذي فتحته خلفها: هناك معظم الهجمات الجديدة.</li>
      <li><b>من الأسهل إلى الأصعب:</b> تبدأ بمواقف قليلة القطع (المستوى 1)، وتنتقل إلى المستوى التالي عندما تصيب 9 من 10 بسرعة كافية (المستوى 1: 25 ثانية، المستوى 2: 20).</li>
      <li><b>في مبارياتك:</b> «عدسة الرؤية» تلوّن ما تحميه وما تهاجمه وما يهددك. استعملها للتعلّم، ثم أطفئها: الهدف أن تراها عينك بلا عدسة.</li>
    </ol><div class="row"><button class="btn big" id="vg-daily">تمرين اليوم: 10 أسئلة</button></div></div>
    <div class="techs">${VG_DRILLS.map(card).join("")}</div>
    ${v.sessions.length ? `<div class="panel"><h3>جلساتك الأخيرة</h3><div class="tbl"><table><thead><tr><th>اليوم</th><th>صحيحة</th><th>متوسط الوقت</th></tr></thead><tbody>${v.sessions.slice(-7).reverse().map((s) => `<tr><td class="num">${s.day}</td><td class="num">${s.ok}/${s.n}</td><td class="num">${s.avg} ث</td></tr>`).join("")}</tbody></table></div></div>` : ""}`;
  $("#vg-back", root).onclick = () => go("journey");
  $("#vg-daily", root).onclick = () => vgRun(root, null);
  for (const b of $$("[data-vd]", root)) b.onclick = () => vgRun(root, b.dataset.vd);
}

/* A run: one drill (endless), or the daily mix of 10 (weakest drills first). */
function vgRun(root, only) {
  let k = 0, ok = 0, times = [], token = 0; const total = only ? Infinity : 10;
  const unlocked = VG_DRILLS.filter((d) => !d.unlock || Math.max(...VG_DRILLS.map((x) => vgDrillState(x.id).level)) >= d.unlock);
  const pick = () => { if (only) return VG_DRILLS.find((d) => d.id === only);
    const w = unlocked.map((d) => { const a = vgAcc(vgDrillState(d.id)); return { d, w: a == null ? 2 : 1 + (100 - a) / 25 }; });
    let x = Math.random() * w.reduce((s, e) => s + e.w, 0); for (const e of w) { x -= e.w; if (x <= 0) return e.d; } return w[0].d; };
  root.innerHTML = `<div class="whead"><button class="btn quiet" id="vg-stop">→ تدريب العين</button><div class="wtitle"><b id="vg-title"></b><span class="note" id="vg-prog"></span></div></div>
    <div class="watch"><div class="wboard"><div class="boardcap"><span class="turn" id="vg-turn"></span><span class="note mono" id="vg-clock"></span></div><div class="board" id="vg-board"></div><div class="row" id="vg-ctl"></div></div>
      <div class="wside"><div class="panel" id="vg-card" aria-live="polite"></div><div class="panel" id="vg-method"></div></div></div>`;
  const board = Board($("#vg-board", root), { interactive: false }); let clockT = null;
  $("#vg-stop", root).onclick = () => { token++; clearInterval(clockT); VisionGym(root); };
  const finish = () => {
    clearInterval(clockT);
    if (!only) { const s = { day: new Date().toISOString().slice(0, 10), t: now(), n: k, ok, avg: times.length ? Math.round(times.reduce((a, b) => a + b, 0) / times.length) : 0 }; vgState().sessions.push(s); vgState().sessions = vgState().sessions.slice(-60); saveJourney(); }
    $("#vg-card", root).innerHTML = `<h3>انتهى التمرين</h3><p>${ok} من ${k} صحيحة. متوسط الوقت ${times.length ? Math.round(times.reduce((a, b) => a + b, 0) / times.length) : 0} ثانية.</p><div class="row"><button class="btn" id="vg-again">مرة أخرى</button><button class="btn quiet" id="vg-home">تدريب العين</button></div>`;
    $("#vg-again", root).onclick = () => vgRun(root, only); $("#vg-home", root).onclick = () => VisionGym(root);
  };
  async function next() {
    if (k >= total) return finish();
    const t = ++token; const d = pick(); const st = vgDrillState(d.id);
    $("#vg-title", root).textContent = d.title; $("#vg-prog", root).textContent = only ? `المستوى ${st.level} · السؤال ${k + 1}` : `السؤال ${k + 1} من ${total} · المستوى ${st.level}`;
    $("#vg-card", root).innerHTML = `<p class="note">أجهّز الموقف...</p>`; $("#vg-ctl", root).innerHTML = "";
    $("#vg-method", root).innerHTML = methodHtml(d).replace(`<details class="method" open>`, st.n >= 5 ? `<details class="method">` : `<details class="method" open>`);
    const q = await vgMakeQuestion(d.id, st.level); if (t !== token || !document.body.contains(root)) return;
    if (!q) { $("#vg-card", root).innerHTML = `<p class="note">تعذّر إيجاد موقف. التالي.</p>`; k++; return next(); }
    ask(q, d, st, t);
  }
  function ask(q, d, st, t) {
    window.VG_DEBUG = q; // read-only hook for the headless tests
    const fen = q.fen2 || q.g.fen(); const picks = new Set(); const marks0 = q.sel ? { [q.sel]: "vsel" } : {};
    const draw = () => board.update({ marks: { ...marks0, ...Object.fromEntries([...picks].map((s) => [s, "focus"])) } });
    $("#vg-turn", root).innerHTML = `<i class="${q.me}"></i>أنت ${q.me === "w" ? "الأبيض" : "الأسود"}`;
    $("#vg-card", root).innerHTML = `<p><b>${esc(d.ask(q))}</b></p>`;
    board.update({ fen, orient: q.me, last: q.last || null, interactive: false, arrows: [], hidden: false, marks: marks0, onSquare: null });
    let t0 = now(); clearInterval(clockT); const tick = () => { $("#vg-clock", root).textContent = `${Math.round((now() - t0) / 1000)} ث`; }; clockT = setInterval(tick, 500); tick();
    const done = (correct, html) => {
      clearInterval(clockT); const secs = Math.max(1, Math.round((now() - t0) / 1000));
      st.n++; st.last.push(correct ? 1 : 0); if (st.last.length > 20) st.last.shift(); st.times = st.times.concat(secs).slice(-10);
      const l10 = st.last.slice(-10), l5 = st.last.slice(-5); let lv = "";
      if (st.level < 3 && l10.length >= 10 && l10.filter(Boolean).length >= 9 && vgAvg(st) <= VG_TIME[st.level]) { st.level++; st.last = []; st.times = []; lv = `<div class="callout good"><b>انتقلت إلى المستوى ${st.level}:</b> مواقف بقطع أكثر${st.level === 3 ? "، والبيادق تُحسب أيضًا" : ""}.</div>`; }
      else if (st.level > 1 && l5.length >= 5 && l5.filter(Boolean).length <= 1) { st.level--; st.last = []; st.times = []; lv = `<div class="callout">رجعت إلى المستوى ${st.level} لتثبّت العادة أولًا.</div>`; }
      saveJourney(); k++; if (correct) ok++; times.push(secs);
      const avg = vgAvg(st);
      $("#vg-card", root).innerHTML = `${html}<p class="note">الوقت: ${secs} ثانية${avg ? ` (متوسطك ${avg})` : ""}.${secs > (VG_TIME[st.level] || 15) ? ` لتسرع: ${esc(d.fast)}` : ""}</p>${lv}<div class="row"><button class="btn" id="vg-next">${k >= total ? "النتيجة" : "التالي"}</button></div>`;
      $("#vg-next", root).onclick = () => next();
    };
    if (q.id === "count") { // two rows of number chips
      let a = null, dd = null;
      $("#vg-ctl", root).innerHTML = `<div class="countq"><span class="note">المهاجمون:</span>${[0, 1, 2, 3, 4, 5].map((x) => `<button class="chip-q" data-ca="${x}">${x}</button>`).join("")}</div>
        <div class="countq"><span class="note">المدافعون:</span>${[0, 1, 2, 3, 4, 5].map((x) => `<button class="chip-q" data-cd="${x}">${x}</button>`).join("")}</div><button class="btn" id="vg-check" disabled>تحقّق</button>`;
      const upd = () => { for (const b of $$("[data-ca]", root)) b.classList.toggle("on", +b.dataset.ca === a); for (const b of $$("[data-cd]", root)) b.classList.toggle("on", +b.dataset.cd === dd); $("#vg-check", root).disabled = a == null || dd == null; };
      for (const b of $$("[data-ca]", root)) b.onclick = () => { a = +b.dataset.ca; upd(); };
      for (const b of $$("[data-cd]", root)) b.onclick = () => { dd = +b.dataset.cd; upd(); };
      $("#vg-check", root).onclick = () => {
        const G = q.G; const c = G[q.sel].color, o = c === "w" ? "b" : "w"; const A = Facts.attackers(G, q.sel, o), D = Facts.attackers(G, q.sel, c);
        const marks = { [q.sel]: "vsel" }; for (const x of A) marks[x.sq] = "mbad"; for (const x of D) marks[x.sq] = "mgood"; board.update({ marks });
        const right = a === q.counts.a && dd === q.counts.d; $("#vg-ctl", root).innerHTML = "";
        const list = (xs) => (xs.length ? xs.map((x) => vgHow(G, x.sq, q.sel)).join("، ") : "لا شيء");
        done(right, `<div class="callout ${right ? "good" : "bad"}"><b>${right ? "صحيح" : "ليس تمامًا"}</b><p>المهاجمون (${q.counts.a}، بالأحمر): ${esc(list(A))}.</p><p>المدافعون (${q.counts.d}، بالأخضر): ${esc(list(D))}.</p>
          ${q.counts.a > q.counts.d || A.some((x) => Facts.VAL[x.type] < Facts.VAL[G[q.sel].type]) ? `<p class="note">القطعة في خطر: ${q.counts.a > q.counts.d ? "المهاجمون أكثر" : "يهاجمها ما هو أرخص منها"}.</p>` : `<p class="note">القطعة محمية بما يكفي الآن.</p>`}</div>`);
      };
      return;
    }
    const startTap = () => {
      board.update({ hidden: false, onSquare: (s) => { if (s === q.sel) return; picks.has(s) ? picks.delete(s) : picks.add(s); draw(); } });
      if (q.id === "flash") board.update({ hidden: true });
      $("#vg-ctl", root).innerHTML = `<button class="btn" id="vg-check">تحقّق</button>`;
      $("#vg-check", root).onclick = () => {
        board.update({ onSquare: null, hidden: false });
        const truth = q.truth; const miss = [...truth].filter((s) => !picks.has(s)), extra = [...picks].filter((s) => !truth.has(s)); const right = !miss.length && !extra.length;
        const marks = { ...marks0 }; for (const s of truth) marks[s] = picks.has(s) ? "mgood" : "mok"; for (const s of extra) marks[s] = "mbad"; board.update({ marks });
        $("#vg-ctl", root).innerHTML = "";
        done(right, `<div class="callout ${right ? "good" : "bad"}"><b>${right ? "صحيح تمامًا" : "ليس تمامًا"}</b> <span class="note">الأخضر أصبت، الأصفر فاتك، الأحمر زيادة.</span>
          ${vgAdvice(q, miss, extra).map((x) => `<p class="note">${esc(x)}</p>`).join("")}</div>`);
      };
    };
    if (q.id === "flash") { // look, then the pieces disappear
      $("#vg-card", root).insertAdjacentHTML("beforeend", `<p class="note" id="vg-cd"></p>`); let left = q.secs;
      const cd = setInterval(() => { left--; const el = $("#vg-cd", root); if (el) el.textContent = left > 0 ? `تختفي القطع بعد ${left}...` : ""; if (left <= 0) { clearInterval(cd); if (t === token) { t0 = now(); startTap(); $("#vg-card", root).insertAdjacentHTML("beforeend", `<p class="note">اختفت القطع: اضغط المربعات من الذاكرة.</p>`); } } }, 1000);
      return;
    }
    startTap();
  }
  next();
}
/* Why you missed what you missed, square by square. */
function vgAdvice(q, miss, extra) {
  const G = q.G1 || q.G; const out = []; const me = q.me, opp = me === "w" ? "b" : "w"; const N = Facts.NAME_AR;
  const nm = (s) => (G[s] ? `${N[G[s].type]} ${s}` : s);
  for (const s of miss.slice(0, 3)) {
    if (q.id === "piece") out.push(`فاتك ${s}: ${vgHow(G, q.sel, s)} يصل إليه${G[s] ? `، ويتوقف عند ${nm(s)}` : ""}.`);
    else if (q.id === "defend" || q.id === "defenders") { const d = q.id === "defenders" ? G[s] && { sq: s } : Facts.attackers(G, s, me)[0]; if (d) out.push(q.id === "defenders" ? `فاتك ${nm(s)}: يحمي ${q.sel} (${vgHow(G, s, q.sel)}).` : `${nm(s)} محمية: يحميها ${vgHow(G, d.sq, s)}.`); }
    else if (q.id === "attack" || q.id === "flash") { const a = Facts.attackers(G, s, me)[0]; if (a) out.push(`فاتك ${nm(s)}: يهاجمه ${vgHow(G, a.sq, s)}.`); }
    else if (q.id === "threat" || q.id === "changed") { const a = Facts.attackers(G, s, opp)[0]; if (a) out.push(`فاتك ${nm(s)}: يهاجمه ${vgHow(G, a.sq, s)}${q.id === "changed" && q.last && a.sq !== q.last.slice(2, 4) ? " (هجوم مكشوف: الخط انفتح بعد أن تحركت قطعة الخصم)" : ""}.`); }
    else if (q.id === "loose") out.push(`فاتك ${nm(s)}: لا قطعة لك تراها.`);
  }
  for (const s of extra.slice(0, 3)) {
    if (q.id === "piece") out.push(`${s} خارج مدى القطعة: ${G[s] ? "" : "الخط مسدود قبله أو ليس في اتجاهاتها."}`);
    else if (q.id === "loose") { const d = Facts.attackers(G, s, me)[0]; out.push(d ? `${nm(s)} محمية: يحميها ${vgHow(G, d.sq, s)}.` : `${nm(s)} ليست مما يُسأل عنه.`); }
    else out.push(`${nm(s)} ليس من الجواب: ${G[s] ? "لا خط مفتوح إليه، أو قطعة تسد الطريق." : "مربع فارغ."}`);
  }
  if (!miss.length && !extra.length) out.push("رأيت كل شيء. الآن أسرع قليلًا، ثم افعل الشيء نفسه في مبارياتك قبل كل نقلة.");
  return out;
}

/* ---------- the in-game vision lens ---------- */
function lensMarks(fen, me, { threats = true } = {}) {
  const G = Facts.grid(new Chess(fen)); const opp = me === "w" ? "b" : "w"; const marks = {};
  for (const [s, p] of Object.entries(G)) {
    if (p.type === "k") continue;
    if (p.color === me) {
      const A = Facts.attackers(G, s, opp), D = Facts.attackers(G, s, me);
      if (threats && A.length && Facts.see(G, s, opp) > 0) marks[s] = "vthreat";
      else if (threats && A.length) marks[s] = "vwarn";
      else if (!D.length && p.type !== "p") marks[s] = "vloose";
      else if (D.length) marks[s] = "vdef";
    } else if (Facts.attackers(G, s, me).length) marks[s] = Facts.see(G, s, me) > 0 ? "vwin" : "vatt";
  }
  return marks;
}
const LENS_LEGEND = (threats) => `<div class="lenslegend note">${threats ? `<span><i class="vthreat"></i>مهدَّدة وقد تُكسب</span><span><i class="vwarn"></i>مهاجَمة لكن محمية</span>` : ""}<span><i class="vloose"></i>بلا حماية</span><span><i class="vdef"></i>محمية</span><span><i class="vatt"></i>تهاجمها</span><span><i class="vwin"></i>تستطيع كسبها</span></div>`;
