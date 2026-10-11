"use strict";
/* Training modes. Every answer is a tap: on the board, or on a choice. Nothing is typed. */

/* ---------- curated positions (Stockfish 10, depth 20-22; tools/verify.mjs) ---------- */
const LIB = [
  { id: "opposition-1", fen: "8/8/4k3/8/8/4K3/4P3/8 w - - 0 1", skill: "endgame", chunk: "King in front of the pawn", chunkKey: "opposition",
    note: "تقدّم بالملك أمام البيدق أولًا. Stockfish يؤكد أن Ke4 وKd4 وKf4 كلها تفوز، أما e4 أولًا فتعادل (0.00) لأن الملك الأسود يأخذ المعارضة." },
  { id: "scholar-defence", fen: "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3", skill: "defence", chunk: "Mate threat on f7",
    note: "الأبيض يهدد Qxf7# لأن الوزير والفيل يهاجمان f7 معًا. أفضل الدفاعات حسب Stockfish: Qe7 وg6، وg6 يطرد الوزير أيضًا." },
  { id: "fried-liver-defence", fen: "r1bqkb1r/pppp1ppp/2n2n2/4p1N1/2B1P3/8/PPPP1PPP/RNBQK2R b KQkq - 5 4", skill: "defence", chunk: "Attack on f7",
    note: "الحصان في g5 والفيل في c4 يهاجمان f7. الدفاع الصحيح d5 يقطع قطر الفيل. Nxe4 وQe7 يخسران بعد Bxf7+ (حوالي -2)." },
  { id: "lucena", fen: "1K6/1P1k4/8/8/8/8/r7/2R5 w - - 0 1", skill: "endgame", chunk: "Lucena position",
    note: "موقف Lucena، فوز للأبيض: أبعد الملك الأسود بكش (Rd1+)، ثم أخرج ملكك واستخدم رخك جسرًا يحجب الكشات. Stockfish يقبل أيضًا Rc7+." },
  { id: "philidor", fen: "3k4/8/r7/3PK3/8/8/8/7R b - - 0 1", skill: "endgame", chunk: "Philidor defence",
    note: "تعادل بطريقة Philidor: الرخ يبقى على الصف السادس ليمنع الملك الأبيض من التقدم، وإذا تقدّم البيدق إلى d6 ينزل الرخ إلى الصف الأول ويكش من الخلف." },
  { id: "iqp-plan", fen: "r1bq1rk1/pp2bppp/2n1pn2/8/2BP4/2N2N2/PP3PPP/R1BQ1RK1 w - - 0 9", skill: "strategy", chunk: "Isolated queen pawn (IQP)",
    note: "بيدق وزير معزول على d4. الخطة: نشاط القطع، الهجوم على الملك، والتحضير للدفعة d5. Stockfish يفضل Re1 ثم a3 وBe3، نقلات هادئة متقاربة." },
  { id: "carlsbad-plan", fen: "r1bq1rk1/pp1nbppp/2p2n2/3p2B1/3P4/2NBPN2/PPQ2PPP/R3K2R w KQ - 0 9", skill: "strategy", chunk: "Carlsbad structure",
    note: "بنية Carlsbad. Stockfish يفضل h3 وBh4 وBf4 ثم التبييت. الخطط المعروفة: هجوم الأقلية b4-b5، أو التبييت الطويل والهجوم على الملك." },
  { id: "italian-plan", fen: "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4", skill: "strategy", chunk: "Italian Game centre plan",
    note: "Stockfish يفضل c3 للتحضير للدفعة d4 وبناء مركز، ثم O-O وd3 كخطة أهدأ." },
  { id: "fork-trick", fen: "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 0 5", skill: "tactics", chunk: "Fork trick",
    note: "الأصح Nxe4، وبعد d5 يستعيد الأسود القطعة بشوكة البيدق والموقف متساوٍ تقريبًا. Qe2 أو O-O يعطيان الأسود أفضلية (حوالي -0.6)." },
  { id: "kp-defence", fen: "8/8/8/3k4/8/8/3PK3/8 b - - 0 1", skill: "endgame", chunk: "Opposition (defence)", chunkKey: "opposition",
    note: "الأسود يدافع: Ke4 يقف أمام الملك الأبيض مباشرة ويأخذ المعارضة، فيضمن التعادل." },
];

/* ---------- pattern catalogue ---------- */
const CHUNKS = [
  { k: "hangingPiece", g: "basics", ar: "قطعة معلّقة", def: "قطعة غير محمية، أو محمية بأقل مما يهاجمها. أول سؤال في كل موقف: هل هناك شيء مجاني؟" },
  { k: "mateIn1", g: "basics", ar: "كش مات في نقلة", def: "افحص كل كش متاح: هل للملك مربع هروب؟ هل يمكن أسر القطعة المهاجمة أو الحجب بينها وبين الملك؟" },
  { k: "fork", g: "basics", ar: "الشوكة (fork)", def: "قطعة واحدة تهاجم هدفين معًا فلا يستطيع الخصم إنقاذ الاثنين. الحصان أشهر من يفعلها." },
  { k: "pin", g: "basics", ar: "التثبيت (pin)", def: "قطعة لا تستطيع التحرك لأن خلفها قطعة أثمن أو الملك. هاجم القطعة المثبّتة مرة أخرى." },
  { k: "skewer", g: "basics", ar: "السيخ (skewer)", def: "عكس التثبيت: القطعة الأثمن في الأمام تُهاجَم، وعندما تتحرك تُؤخذ القطعة التي خلفها." },
  { k: "backRankMate", g: "basics", ar: "كش الصف الأخير", def: "الملك محبوس خلف بيادقه في صفه الأخير، فرخ أو وزير يصل إلى ذلك الصف يعطي كش مات." },
  { k: "discoveredAttack", g: "basics", ar: "الهجوم المكشوف", def: "تتحرك قطعة فتكشف خطًا لقطعة خلفها، فيقع هجومان في نقلة واحدة." },
  { k: "doubleCheck", g: "basics", ar: "الكش المزدوج", def: "قطعتان تكشان معًا. لا يمكن صده إلا بتحريك الملك." },
  { k: "mateIn2", g: "basics", ar: "كش مات في نقلتين", def: "نقلة أولى قسرية، غالبًا كش أو تضحية، تُجبر الخصم، ثم الكش المات." },
  { k: "attackingF2F7", g: "tactics", ar: "الهجوم على f7 / f2", def: "أضعف مربع في الافتتاح لأن الملك وحده يحميه." },
  { k: "trappedPiece", g: "tactics", ar: "قطعة محاصرة", def: "قطعة ليس لها مربع آمن. هاجمها لتكسبها." },
  { k: "deflection", g: "tactics", ar: "الإبعاد (deflection)", def: "أجبر قطعة مدافعة على ترك مهمتها: حماية مربع أو قطعة." },
  { k: "attraction", g: "tactics", ar: "الجذب (attraction)", def: "أجبر قطعة، غالبًا الملك، على الانتقال إلى مربع سيئ، عادة بتضحية." },
  { k: "capturingDefender", g: "tactics", ar: "إزالة المدافع", def: "خذ القطعة التي تحمي الهدف، فيبقى الهدف بلا حماية." },
  { k: "intermezzo", g: "tactics", ar: "النقلة الوسيطة (intermezzo)", def: "بدل الرد المتوقع، العب أولًا نقلة قسرية (كش أو تهديد أكبر) ثم عد." },
  { k: "xRayAttack", g: "tactics", ar: "هجوم الأشعة (x-ray)", def: "قطعة تهاجم أو تحمي عبر قطعة أخرى على نفس الخط." },
  { k: "clearance", g: "tactics", ar: "التفريغ (clearance)", def: "حرّك قطعتك من مربع أو خط لتستفيد منه قطعة أخرى." },
  { k: "interference", g: "tactics", ar: "القطع (interference)", def: "ضع قطعة بين قطعة الخصم والمربع الذي تحميه." },
  { k: "promotion", g: "tactics", ar: "الترقية", def: "بيدق متقدم يصل إلى الصف الأخير، أحيانًا بعد تضحية تُبعد المدافع." },
  { k: "smotheredMate", g: "mates", ar: "الكش المخنوق", def: "حصان يكش ملكًا محاطًا بقطعه فلا يستطيع الهروب." },
  { k: "hookMate", g: "mates", ar: "كش الخطّاف (hook mate)", def: "رخ يكش بجانب الملك، يحميه حصان، والحصان يحميه بيدق." },
  { k: "anastasiaMate", g: "mates", ar: "كش أناستازيا", def: "حصان يغلق مربعات الهروب، ورخ أو وزير يكش على العمود الطرفي." },
  { k: "greekGift", g: "mates", ar: "الهدية اليونانية (Greek gift)", def: "تضحية الفيل على h7 (أو h2) مع كش، ثم الحصان والوزير يهاجمان الملك المكشوف." },
  { k: "defensiveMove", g: "defence", ar: "النقلة الدفاعية", def: "الأفضل هنا ليس الهجوم بل إيقاف تهديد الخصم بدقة." },
  { k: "quietMove", g: "defence", ar: "النقلة الهادئة", def: "نقلة بلا كش ولا أسر، لكنها تخلق تهديدًا لا يمكن صده." },
  { k: "zugzwang", g: "endgame", ar: "الإجبار على النقلة (zugzwang)", def: "لو استطاع الخصم أن يمرر دوره لكان بخير، لكن كل نقلة لديه تضعف موقفه." },
  { k: "opposition", g: "endgame", ar: "المعارضة (opposition)", def: "ملكان متقابلان بينهما مربع واحد. الطرف الذي ليس دوره يملك المعارضة، وهي مفتاح نهايات الملك والبيدق." },
  { k: "pawnEndgame", g: "endgame", ar: "نهايات البيادق", def: "الملك قطعة هجومية في النهاية. احسب السباقات بدقة: كل نقلة تهم." },
  { k: "rookEndgame", g: "endgame", ar: "نهايات الرخ", def: "الرخ النشيط أهم من بيدق. ضع الرخ خلف البيدق المتقدم." },
  { k: "queenEndgame", g: "endgame", ar: "نهايات الوزير", def: "الكشات المتتالية والشوكات بالوزير هي أهم الأسلحة." },
  { k: "bishopEndgame", g: "endgame", ar: "نهايات الفيل", def: "لون مربعات الفيل يحدد أي البيادق يستطيع حمايتها أو مهاجمتها." },
  { k: "knightEndgame", g: "endgame", ar: "نهايات الحصان", def: "الحصان بطيء: احسب عدد نقلاته للوصول، وهو يكره البيادق الطرفية البعيدة." },
  { k: "iqp", g: "structure", ar: "البيدق المعزول (IQP)", def: "بيدق على d4 (أو d5) بلا بيادق صديقة على العمودين c وe. صاحبه يحصل على نشاط ومساحة ويهاجم، ويحضّر الدفعة d5. خصمه يحاصر المربع أمامه ويتبادل القطع ليصل إلى نهاية يضعف فيها البيدق." },
  { k: "carlsbad", g: "structure", ar: "بنية Carlsbad وهجوم الأقلية", def: "بنية تنتج عن التبادل في QGD: للأبيض d4 وe3 بلا بيدق c، وللأسود c6 وd5 بلا بيدق e. الخطة الكلاسيكية للأبيض: هجوم الأقلية b4-b5 لإضعاف c6." },
];
const CHUNK = Object.fromEntries(CHUNKS.map((c) => [c.k, c]));
const GROUP_AR = { basics: "الأساسيات", tactics: "تكتيك متقدم", mates: "أنماط الكش", defence: "الدفاع والنقلات الهادئة", endgame: "النهايات", structure: "بنى البيادق والخطط" };
const STRUCT_AR = { "iqp-w": "بيدق معزول للأبيض على d4", "iqp-b": "بيدق معزول للأسود على d5", carlsbad: "بنية Carlsbad", none: "لا شيء من هذه البنى" };
const STRUCT_PLANS = {
  "iqp-w": { q: "ما الخطة النموذجية للأبيض (صاحب البيدق المعزول)؟", right: "نشاط القطع، الهجوم على الملك، والتحضير للدفعة d5", wrong: ["هجوم الأقلية b4-b5", "تبادل كل القطع بسرعة والذهاب إلى النهاية", "إغلاق المركز واللعب على الجناح الوزيري ببطء"] },
  "iqp-b": { q: "ما الخطة النموذجية للأسود (صاحب البيدق المعزول)؟", right: "نشاط القطع، الهجوم، والتحضير للدفعة d4", wrong: ["هجوم الأقلية b5-b4", "تبادل كل القطع بسرعة والذهاب إلى النهاية", "انتظار سلبي خلف البيادق"] },
  carlsbad: { q: "ما الخطة الكلاسيكية للأبيض في هذه البنية؟", right: "هجوم الأقلية b4-b5 لخلق ضعف في c6", wrong: ["الدفعة e4 فورًا بلا تحضير", "دفع g4-g5 دون تبييت ولا خطة", "تبادل الوزيرين ثم الانتظار"] },
};
function chunkItems(k) {
  if (k === "opposition") return [...DATA.opposition.map(oppositionItem), ...LIB.filter((p) => p.chunkKey === "opposition").map(libItem)];
  if (k === "iqp") return DATA.structures.filter((s) => s.s === "iqp-w" || s.s === "iqp-b").map(structItem);
  if (k === "carlsbad") return DATA.structures.filter((s) => s.s === "carlsbad").map(structItem);
  return DATA.puzzles.filter((p) => p.t.includes(k)).map(puzzleItem);
}
function structItem(s, i) { return { kind: "struct", id: "st-" + s.s + "-" + hashStr(s.f), fen: s.f, s: s.s, op: s.op, skill: "strategy", rating: 1200, themes: [s.s === "carlsbad" ? "carlsbad" : s.s === "none" ? "none" : "iqp"] }; }
function hashStr(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0).toString(36); }

/* pick puzzles near a rating, preferring unseen ones */
function pickPuzzles(n, target, { filter = () => true, exclude = new Set() } = {}) {
  const seen = new Set(S.attempts.map((a) => a.itemId));
  const xs = DATA.puzzles.filter((p) => filter(p) && !exclude.has(p.i));
  const score = (p) => Math.abs(p.r - target) + (seen.has(p.i) ? 400 : 0) + Math.random() * 120;
  return xs.map((p) => [score(p), p]).sort((a, b) => a[0] - b[0]).slice(0, n).map((x) => puzzleItem(x[1]));
}
const RATING = (k = "tactics") => S.profile.ratings?.[k]?.r ?? 800;

/* ========== 1. Thought-process training (tap only) ========== */
function nullMoveFen(fen) { const p = fen.split(" "); p[1] = p[1] === "w" ? "b" : "w"; p[3] = "-"; return p.join(" "); }
const EVAL_CATS = [["الأبيض يربح", 300], ["الأبيض أفضل", 100], ["متساوٍ تقريبًا", -100], ["الأسود أفضل", -300], ["الأسود يربح", -Infinity]];
const evalCat = (cpWhite) => EVAL_CATS.findIndex(([, lo]) => cpWhite >= lo);

function ThinkMode(root, item, done) {
  window.__item = item;
  const stm = sideOf(item.fen); const s = stm === "w" ? 1 : -1;
  const T = { step: 1, cands: [], chosen: null, reply: undefined, threat: null, evalIdx: null, conf: null, t0: now(), changed: false };
  root.innerHTML = `
  <div class="train">
    <div class="boardwrap">
      <div class="boardcap"><span class="turn"><i class="${stm}"></i>الدور ${stm === "w" ? "للأبيض" : "للأسود"}</span>${item.lastSan ? `<span>آخر نقلة للخصم: ${mv(item.lastSan)}</span>` : ""}</div>
      <div class="board"></div>
      <div class="chips" id="th-chips"></div>
    </div>
    <div class="panel side"><div class="steps" id="th-steps"></div><div id="th-body"></div><div id="th-out"></div></div>
  </div>`;
  const body = $("#th-body", root), out = $("#th-out", root);
  const board = Board($(".board", root), { fen: item.fen, orient: stm, last: item.last, interactive: false });
  const prep = (async () => {
    const base = await Engine.analyse(item.fen, { depth: 16, movetime: 2000, multipv: 3 });
    const inCheck = new Chess(item.fen).in_check();
    let threat = null, nullOpts = [];
    if (!inCheck) {
      const nf = nullMoveFen(item.fen); const ng = new Chess(nf);
      if (ng.validate_fen(nf).valid) {
        const tn = await Engine.analyse(nf, { depth: 14, movetime: 900 });
        const size = wp(s * base.cp) - wp(s * tn.cp);
        if (size >= 8 && tn.best) threat = { uci: tn.best, san: sanOf(nf, tn.best), size: Math.round(size) };
        nullOpts = ng.moves({ verbose: true });
      }
    }
    return { base, threat, inCheck, nullOpts };
  })();
  const STEPS = ["التهديد", "المرشحات", "الاختيار", "فحص الخطأ", "التقييم"];
  function drawSteps() { $("#th-steps", root).innerHTML = STEPS.map((t, i) => `<span class="${i + 1 === T.step ? "on" : i + 1 < T.step ? "done" : ""}">${i + 1}. ${t}</span>`).join(""); }
  function chips(onTap) {
    const el = $("#th-chips", root);
    el.innerHTML = T.cands.map((c, i) => `<button type="button" class="chip-mv ${T.chosen && T.chosen.uci === c.uci ? "on" : ""}" data-i="${i}">${mv(c.san)}${T.step === 2 ? " ✕" : ""}</button>`).join("");
    for (const b of $$("[data-i]", el)) b.onclick = () => onTap && onTap(+b.dataset.i);
  }
  async function step1() {
    T.step = 1; drawSteps();
    body.innerHTML = `<h3>ماذا تغيّر؟ ماذا يهدد الخصم؟</h3><p class="note">انظر إلى آخر نقلة للخصم. لو كان الدور له الآن، ماذا كان سيلعب؟</p><div id="th-opts"><span class="note">Stockfish يجهّز الموقف...</span></div>`;
    const P = await prep;
    if (P.inCheck) { T.threat = { skipped: true }; body.innerHTML = `<div class="callout">أنت في كش. كل نقلة يجب أن تعالج الكش، فابدأ مباشرة بالمرشحات.</div>`; await sleep(900); return step2(); }
    const opts = [];
    if (P.threat) opts.push({ label: `يهدد ${P.threat.san}`, right: true, uci: P.threat.uci });
    const forcing = shuffle(P.nullOpts.filter((m) => (m.captured || m.san.includes("+")) && (!P.threat || m.from + m.to !== P.threat.uci.slice(0, 4))));
    const quiet = shuffle(P.nullOpts.filter((m) => !(m.captured || m.san.includes("+"))));
    for (const m of [...forcing, ...quiet]) { if (opts.length >= 3) break; opts.push({ label: `يهدد ${m.san}`, right: false, uci: m.from + m.to }); }
    opts.push({ label: "لا يوجد تهديد مباشر", right: !P.threat, none: true });
    const shown = shuffle(opts.slice(0, -1)).concat(opts.slice(-1));
    $("#th-opts", body).innerHTML = `<div class="choices">${shown.map((o, i) => `<button type="button" class="choice" data-o="${i}">${o.none ? o.label : `يهدد ${mv(o.label.replace("يهدد ", ""))}`}</button>`).join("")}</div>`;
    for (const b of $$("[data-o]", body)) b.onclick = () => { const o = shown[+b.dataset.o]; T.threat = { right: o.right, picked: o.none ? "none" : o.label, real: P.threat ? P.threat.san : null }; step2(); };
  }
  function step2() {
    T.step = 2; drawSteps();
    const legalN = new Chess(item.fen).moves().length; const need = Math.min(2, legalN);
    body.innerHTML = `<h3>النقلات المرشحة</h3><p class="note">انقر على الرقعة كل نقلة تستحق التفكير، من 2 إلى 4. ابدأ بالكشات والأسر والتهديدات. الرقعة لا تتحرك.</p><div class="row"><button class="btn" id="th-n2" disabled>انتهيت من المرشحات</button></div>`;
    const btn = $("#th-n2", body);
    const refresh = () => { chips((i) => { T.cands.splice(i, 1); refresh(); }); btn.disabled = T.cands.length < need; };
    board.update({ interactive: true, onMove: (m) => { if (!T.cands.some((c) => c.uci === m.uci) && T.cands.length < 4) T.cands.push(m); board.update({ fen: item.fen, last: item.last }); refresh(); } });
    refresh(); btn.onclick = step3;
  }
  function step3() {
    T.step = 3; drawSteps(); board.update({ interactive: false, fen: item.fen, last: item.last, marks: {} });
    body.innerHTML = `<h3>اختر نقلتك</h3><p class="note">من بين مرشحاتك. إن اقتنعت أن نقلة أخرى أفضل، أضفها.</p><div class="row"><button class="btn quiet" id="th-add">أضف مرشحًا آخر</button></div>`;
    chips((i) => { T.chosen = T.cands[i]; step4(); });
    $("#th-add", body).onclick = step2;
  }
  function step4() {
    T.step = 4; drawSteps(); chips(null);
    const after = T.chosen.fenAfter;
    body.innerHTML = `<h3>فحص الخطأ</h3><p class="note">الرقعة الآن بعد نقلتك ${mv(T.chosen.san)}. <b>ما أقوى رد للخصم؟</b> كل كشاته وأسره وتهديداته. انقر الرد على الرقعة.</p><div class="row"><button class="btn quiet" id="th-none">ليس للخصم رد خطير</button></div>`;
    board.update({ fen: after, orient: stm, last: T.chosen.uci, interactive: true, onMove: (r) => { T.reply = r; checkAgain(); } });
    $("#th-none", body).onclick = () => { T.reply = null; checkAgain(); };
  }
  function checkAgain() {
    board.update({ interactive: false });
    body.innerHTML = `<h3>فحص الخطأ</h3><p>${T.reply ? `ترى أن الخصم سيرد ${mv(T.reply.san)}.` : "ترى أن الخصم ليس لديه رد خطير."} هل ما زلت تريد ${mv(T.chosen.san)}؟</p>
      <div class="row"><button class="btn" id="th-keep">نعم، أبقيها</button><button class="btn quiet" id="th-change">لا، سأغيّر نقلتي</button></div>`;
    $("#th-keep", body).onclick = step5;
    $("#th-change", body).onclick = () => { T.changed = true; T.chosen = null; board.update({ fen: item.fen, last: item.last }); step3(); };
  }
  function step5() {
    T.step = 5; drawSteps(); board.update({ fen: item.fen, last: item.last, marks: { [T.chosen.uci.slice(0, 2)]: "pick", [T.chosen.uci.slice(2, 4)]: "pick" } });
    body.innerHTML = `<h3>التقييم</h3><p class="note">بعد أفضل لعب من الطرفين، من الأفضل في هذا الموقف؟</p>
      <div class="choices" id="th-ev">${EVAL_CATS.map(([t], i) => `<button type="button" class="choice" data-e="${i}">${t}</button>`).join("")}</div><div id="th-cf"></div>`;
    for (const b of $$("[data-e]", body)) b.onclick = async () => {
      T.evalIdx = +b.dataset.e; for (const x of $$("[data-e]", body)) x.classList.toggle("on", x === b);
      T.conf = await askConfidence($("#th-cf", body), "ما ثقتك في نقلتك؟"); submit();
    };
  }
  async function submit() {
    body.innerHTML = `<p class="note">Stockfish يقيّم تفكيرك...</p>`; $("#th-chips", root).innerHTML = "";
    const P = await prep; const base = P.base;
    const j = await judgeMove(item.fen, T.chosen.uci, { expected: item.sol ? item.sol[0] : null, base });
    const bestWp = wp(s * base.cp);
    const good = new Set(base.lines.filter((l) => bestWp - wp(s * l.cpWhite) <= 5).map((l) => l.pv[0])); if (item.sol) good.add(item.sol[0]);
    const sc = {};
    sc.threats = T.threat.skipped ? null : T.threat.right ? 2 : 0;
    sc.candidates = T.cands.some((c) => good.has(c.uci)) ? 2 : T.cands.some((c) => moveKind(item.fen, c.uci) !== "quiet") ? 1 : 0;
    sc.blunder_check = T.reply === null ? (j.correct ? 2 : 0) : (T.reply && j.reply && T.reply.uci === j.reply ? 2 : 0);
    const ec = evalCat(base.cp); sc.evaluation = T.evalIdx === ec ? 2 : Math.abs(T.evalIdx - ec) === 1 ? 1 : 0;
    const vals = Object.values(sc).filter((v) => v != null);
    const R = { mode: "think", itemId: item.id, kind: item.kind, skill: item.skill, rating: item.rating, themes: item.themes, confidence: T.conf, firstMove: T.chosen.san,
      correct: j.correct, firstLoss: j.loss, scores: sc, process: Math.round(100 * vals.reduce((a, b) => a + b, 0) / (2 * vals.length)), changedAfterCheck: T.changed,
      seconds: Math.round((now() - T.t0) / 1000), cands: T.cands.map((c) => c.san), threatPick: T.threat.picked || null, realThreat: T.threat.real || null, evalPick: T.evalIdx, engineEval: base.cp };
    const scoreHtml = `<div class="scores">${Object.entries(CHECK_AR).map(([k, t]) => `<div><span>${t}</span><b>${sc[k] == null ? "–" : sc[k] + "/2"}</b></div>`).join("")}</div>`;
    const facts = [
      T.threat.skipped ? "" : T.threat.right ? `التهديد: أصبت.` : `التهديد: ${T.threat.real ? `الخصم كان يهدد ${mv(T.threat.real)}` : "لم يكن هناك تهديد مباشر"}، وأنت اخترت "${esc(T.threat.picked === "none" ? "لا يوجد تهديد" : T.threat.picked)}".`,
      sc.candidates === 2 ? "المرشحات: كانت بينها نقلة جيدة." : `المرشحات: لم تكن بينها النقلة الأفضل.`,
      `فحص الخطأ: ${j.reply ? `أقوى رد للخصم بعد نقلتك كان ${mv(sanOf(j.after, j.reply))}` : "لا رد"}${T.reply ? `، وأنت توقعت ${mv(T.reply.san)}` : "، وأنت قلت لا يوجد رد خطير"}.`,
      `التقييم: Stockfish يقول ${EVAL_CATS[ec][0]} (${fmtEval(base.cp)})، وأنت قلت ${EVAL_CATS[T.evalIdx][0]}.`,
    ].filter(Boolean).map((x) => `<li>${x}</li>`).join("");
    const summary = `<h3>${j.correct ? "نقلتك جيدة" : "نقلتك لا تنجح"} ${mv(T.chosen.san)}</h3>${scoreHtml}<ul class="facts">${facts}</ul>`;
    body.innerHTML = summary;
    const finish = async (solverR, target = out) => {
      if (solverR) { R.solvedAt = solverR.solvedAt; R.revealed = solverR.solvedAt === 0; } else R.solvedAt = 1;
      const lines = base.lines.map((l) => `<div><span class="ev">${fmtEval(l.cpWhite)}</span>${mv(numberedLine(item.fen, pvToSan(item.fen, l.pv, 7)))}</div>`).join("");
      target.innerHTML = `<div class="lines"><span class="note">أفضل خطوط Stockfish (التقييم من جهة الأبيض):</span>${lines}</div>${item.note ? coachHtml("ملاحظة متحقق منها بـ Stockfish", esc(item.note)) : ""}<div id="th-cr"></div><div class="row"><button class="btn" id="th-next">التالي</button></div>`;
      if (target === out) board.update({ fen: item.fen, last: item.last, interactive: false });
      $("#th-next", target).onclick = () => done(R);
      critique($("#th-cr", target), item, T, R, base, j);
    };
    if (j.correct) return finish(null);
    // wrong: the Socratic ladder takes over, starting at rung 1 (find the refutation yourself)
    root.innerHTML = `<div class="panel">${summary}</div><div id="th-solve"></div><div id="th-fin" class="panel" hidden></div>`;
    Solver($("#th-solve", root), item, { askConf: false, ladder: true, preFail: { move: T.chosen, judged: j },
      onDone: (sr) => { $("#th-solve", root).innerHTML = ""; const fin = $("#th-fin", root); fin.hidden = false; finish(sr, fin); } });
  }
  step1();
}
const CHECK_AR = { threats: "تهديدات الخصم", candidates: "المرشحات", blunder_check: "فحص الخطأ", evaluation: "التقييم" };
async function critique(el, item, T, R, base, j) {
  if (!SAMPLE) { el.innerHTML = ""; return; }
  el.innerHTML = coachHtml("نقد طريقة التفكير", "يكتب...");
  const prompt = `You are a demanding chess coach in the tradition of Heisman, Aagaard and Dvoretsky. A beginner answered a structured thinking checklist by tapping (no writing). Critique their PROCESS in Arabic, 3-5 sentences: which step failed and what to do differently, then the key idea of the position from the engine lines, then ONE habit for next time. Plain text, no headings.
${LANG_RULES}
FEN: ${item.fen} (${sideOf(item.fen) === "w" ? "White" : "Black"} to move)${item.lastSan ? ", opponent's last move " + item.lastSan : ""}
PIECES: ${pieceList(item.fen)}
ENGINE DATA (Stockfish 10, multipv 3):
${base.lines.map((l, k) => `${k + 1}. ${fmtEval(l.cpWhite)} (White's view): ${numberedLine(item.fen, pvToSan(item.fen, l.pv, 7))}`).join("\n")}
${item.sol ? "PUZZLE SOLUTION: " + numberedLine(item.fen, pvToSan(item.fen, item.sol, 10)) + "\n" : ""}STUDENT'S TAPS:
- threat question: picked "${T.threat.skipped ? "skipped (in check)" : T.threat.picked}", real threat: ${T.threat.real || "none"}
- candidates: ${T.cands.map((c) => c.san).join(", ")}
- chosen move: ${T.chosen.san} -> ${j.correct ? "good" : "loses " + j.loss + " win-probability points; engine refutation: " + j.refutation.join(" ")}
- blunder check (opponent's best reply they expected): ${T.reply ? T.reply.san : "none"}; engine's best reply: ${j.reply ? sanOf(j.after, j.reply) : "n/a"}
- changed move after blunder check: ${T.changed ? "yes" : "no"}
- evaluation picked: ${EVAL_CATS[T.evalIdx][0]}; engine: ${fmtEval(base.cp)}
- confidence: ${T.conf}/5
- solved after Socratic hints: ${R.solvedAt === 0 ? "no (solution shown)" : R.solvedAt > 1 ? "yes, attempt " + R.solvedAt : "first try"}`;
  try { await askClaude(prompt, { onText: (t) => { el.innerHTML = coachHtml("نقد طريقة التفكير · Claude مقيّد بخطوط Stockfish", esc(t.text)); } }); }
  catch (e) { el.innerHTML = coachHtml("نقد طريقة التفكير", esc(claudeMsg(e))); }
}

/* ========== 2. Calculation (Kotov / Aagaard) ========== */
function CalcMode(root, item, done) {
  window.__item = item;
  const stm = sideOf(item.fen); const s = stm === "w" ? 1 : -1;
  const C = { lines: [], cur: null, peeks: 0, t0: now() };
  root.innerHTML = `
  <div class="train">
    <div class="boardwrap">
      <div class="boardcap"><span class="turn"><i class="${stm}"></i>الدور ${stm === "w" ? "للأبيض" : "للأسود"}</span>${item.lastSan ? `<span>آخر نقلة: ${mv(item.lastSan)}</span>` : ""}</div>
      <div class="board"></div>
      <p class="note">القطع لا تتحرك. انقر النقلات كما تراها في ذهنك: نقلتك، ثم رد الخصم، وهكذا.</p>
    </div>
    <div class="panel side"><h3>احسب بدون تحريك القطع</h3>
      <p class="note">اكتب بالنقر كل نقلة مرشحة كخط كامل حتى موقف هادئ (لا كشات ولا أسر معلّق). حتى 3 خطوط.</p>
      <div id="cl-lines"></div><div id="cl-ctl"></div><div id="cl-out"></div></div>
  </div>`;
  const board = Board($(".board", root), { fen: item.fen, orient: stm, last: item.last, interactive: false, dots: false });
  const linesEl = $("#cl-lines", root), ctl = $("#cl-ctl", root), out = $("#cl-out", root);
  const rootEval = Engine.analyse(item.fen, { depth: 16, movetime: 2000, multipv: 3 });
  const lineFen = (line) => { const g = new Chess(item.fen); for (const m of line) uciMove(g, m.uci); return g.fen(); };
  function render() {
    linesEl.innerHTML = C.lines.map((l, i) => `<div class="calc-line"><span class="n">${i + 1}</span>${mv(numberedLine(item.fen, l.map((m) => m.san)))}</div>`).join("") +
      (C.cur ? `<div class="calc-line cur"><span class="n">${C.lines.length + 1}</span>${C.cur.length ? mv(numberedLine(item.fen, C.cur.map((m) => m.san))) : `<span class="note">انقر النقلة الأولى...</span>`}</div>` : "");
    if (C.cur) {
      const turn = sideOf(lineFen(C.cur));
      ctl.innerHTML = `<p class="note">الآن دور ${turn === stm ? "نقلتك" : "رد الخصم"} في هذا الخط.</p><div class="row">
        <button class="btn quiet" id="cl-undo" ${C.cur.length ? "" : "disabled"}>تراجع</button>
        <button class="btn" id="cl-end" ${C.cur.length ? "" : "disabled"}>أنهِ الخط هنا (موقف هادئ)</button>
        <button class="btn ghost" id="cl-peek" ${C.cur.length ? "" : "disabled"}>اختلس نظرة (تُحسب)</button></div>`;
      $("#cl-undo", ctl).onclick = () => { C.cur.pop(); sync(); };
      $("#cl-end", ctl).onclick = () => { C.lines.push(C.cur); C.cur = null; sync(); };
      $("#cl-peek", ctl).onclick = () => { C.peeks++; board.update({ fen: lineFen(C.cur) }); setTimeout(() => board.update({ fen: item.fen, logicFen: lineFen(C.cur) }), 2500); };
    } else {
      ctl.innerHTML = `<div class="row">${C.lines.length < 3 ? `<button class="btn ${C.lines.length ? "quiet" : ""}" id="cl-new">${C.lines.length ? "أضف مرشحًا آخر" : "ابدأ الخط الأول"}</button>` : ""}${C.lines.length ? `<button class="btn" id="cl-fin">انتهيت من الحساب</button>` : ""}</div>`;
      const nw = $("#cl-new", ctl); if (nw) nw.onclick = () => { C.cur = []; sync(); };
      const fn = $("#cl-fin", ctl); if (fn) fn.onclick = chooseMain;
    }
  }
  function sync() {
    const lf = C.cur ? lineFen(C.cur) : item.fen;
    board.update({ fen: item.fen, logicFen: lf, interactive: !!C.cur && C.cur.length < 12, onMove: (m) => {
      if (C.cur.length === 0 && C.lines.some((l) => l[0].uci === m.uci)) { ctl.insertAdjacentHTML("afterbegin", `<p class="err">هذا المرشح موجود في خط سابق.</p>`); return; }
      C.cur.push({ uci: m.uci, san: m.san }); sync(); } });
    render();
  }
  function chooseMain() {
    board.update({ interactive: false });
    ctl.innerHTML = `<h3>أي خط تلعب؟</h3><div class="choices">${C.lines.map((l, i) => `<button type="button" class="choice" data-l="${i}">${mv(l[0].san)}</button>`).join("")}</div>`;
    for (const b of $$("[data-l]", ctl)) b.onclick = () => { C.main = +b.dataset.l; evalStep(); };
  }
  function evalStep() {
    ctl.innerHTML = `<h3>في نهاية خطك الرئيسي، من الأفضل؟</h3><div class="choices">${EVAL_CATS.map(([t], i) => `<button type="button" class="choice" data-e="${i}">${t}</button>`).join("")}</div><div id="cl-cf"></div>`;
    for (const b of $$("[data-e]", ctl)) b.onclick = async () => { C.evalIdx = +b.dataset.e; for (const x of $$("[data-e]", ctl)) x.classList.toggle("on", x === b); C.conf = await askConfidence($("#cl-cf", ctl), "ما ثقتك في حسابك؟"); grade(); };
  }
  async function grade() {
    ctl.innerHTML = `<p class="note">Stockfish يراجع شجرتك، خطوة خطوة...</p><div class="progress"><i id="cl-bar"></i></div>`;
    const base = await rootEval; const bestWp = wp(s * base.cp);
    const good = base.lines.filter((l) => bestWp - wp(s * l.cpWhite) <= 8).map((l) => l.pv[0]); if (item.sol && !good.includes(item.sol[0])) good.unshift(item.sol[0]);
    const firsts = C.lines.map((l) => l[0].uci);
    const missed = good.filter((u) => !firsts.includes(u)).map((u) => sanOf(item.fen, u));
    const main = C.lines[C.main]; let pos = item.fen, depthOk = 0, broke = null;
    for (let k = 0; k < main.length; k++) {
      const bar = $("#cl-bar", ctl); if (bar) bar.style.width = (100 * k / main.length) + "%";
      const m = main[k]; const mine = sideOf(pos) === stm;
      if (mine) {
        const expected = item.sol && main.slice(0, k).every((x, i) => x.uci === item.sol[i]) ? item.sol[k] : null;
        const j = await judgeMove(pos, m.uci, { expected, tol: 8 });
        if (!j.correct) { broke = { ply: k, type: "own", move: m.san, loss: j.loss, refutation: j.refutation }; break; }
      } else {
        const e = await Engine.analyse(pos, { depth: 14, movetime: 900 });
        if (m.uci !== e.best) {
          const a = await Engine.analyse(fenAfter(pos, m.uci), { depth: 13, movetime: 800 });
          const oppLoss = wp(-s * e.cp) - wp(-s * a.cp);
          if (oppLoss > 10) { broke = { ply: k, type: "assumed", move: m.san, better: sanOf(pos, e.best), line: pvToSan(pos, e.lines[0]?.pv || [e.best], 5) }; break; }
        }
      }
      pos = fenAfter(pos, m.uci); depthOk = k + 1;
    }
    let endIdx = null, endCp = null;
    if (!broke) { const e = await Engine.analyse(pos, { depth: 15, movetime: 1500 }); endCp = e.cp; endIdx = evalCat(e.cp); }
    const firstOk = !(broke && broke.ply === 0);
    const R = { mode: "calc", itemId: item.id, kind: item.kind, skill: "calculation", rating: item.rating, themes: item.themes, confidence: C.conf, correct: firstOk && !broke,
      firstCorrect: firstOk, depth: depthOk, length: main.length, lines: C.lines.length, missed: missed.length, peeks: C.peeks, seconds: Math.round((now() - C.t0) / 1000),
      evalRight: endIdx != null ? endIdx === C.evalIdx : null, firstMove: main[0].san, solvedAt: firstOk && !broke ? 1 : 0 };
    const solSan = item.sol ? pvToSan(item.fen, item.sol, 12) : [];
    const engineLines = base.lines.map((l) => `<div><span class="ev">${fmtEval(l.cpWhite)}</span>${mv(numberedLine(item.fen, pvToSan(item.fen, l.pv, 8)))}</div>`).join("");
    ctl.innerHTML = "";
    out.innerHTML = `
      <div class="kpis small">${kpi(depthOk + " / " + main.length, "نقلات صحيحة في خطك الرئيسي")}${kpi(missed.length, "مرشحات جيدة فاتتك")}${kpi(C.peeks, "نظرات مختلسة")}</div>
      ${broke ? `<div class="callout bad">${broke.type === "own" ? `حسابك انكسر عند نقلتك ${mv(broke.move)}: تخسر ${broke.loss}% من احتمال الفوز. الرد: ${mv(broke.refutation.slice(0, 4).join(" "))}.` : `حسابك انكسر عند رد الخصم: افترضت ${mv(broke.move)}، لكن الخصم يملك ${mv(broke.better)} (${mv(broke.line.join(" "))}).`}</div>`
        : `<div class="callout good">خطك الرئيسي صحيح حتى النهاية.${endIdx != null ? ` تقييمك للنهاية: ${EVAL_CATS[C.evalIdx][0]}، وStockfish: ${EVAL_CATS[endIdx][0]} (${fmtEval(endCp)}).` : ""}</div>`}
      ${missed.length ? `<p>مرشحات جيدة لم تحسبها: ${missed.map(mv).join("، ")}</p>` : ""}
      <div class="lines"><span class="note">شجرة Stockfish:</span>${engineLines}${solSan.length ? `<div><span class="ev">حل</span>${mv(numberedLine(item.fen, solSan))}</div>` : ""}</div>
      <div id="cl-cr"></div><div class="row"><button class="btn" id="cl-next">التالي</button></div>`;
    $("#cl-next", out).onclick = () => done(R);
    const cr = $("#cl-cr", out);
    if (SAMPLE) {
      cr.innerHTML = coachHtml("المدرّب", "يكتب...");
      const prompt = `You are a calculation coach (Kotov, Aagaard). Compare the student's calculation tree with the engine's. In Arabic, 3-4 sentences: which candidates they missed and why they matter, exactly where their main line broke (or confirm it held), and one concrete calculation habit (e.g. check all forcing replies, continue to a quiet position).
${LANG_RULES}
FEN: ${item.fen} (${stm === "w" ? "White" : "Black"} to move)
PIECES: ${pieceList(item.fen)}
ENGINE TREE: ${base.lines.map((l) => fmtEval(l.cpWhite) + ": " + numberedLine(item.fen, pvToSan(item.fen, l.pv, 8))).join(" | ")}
${solSan.length ? "VERIFIED SOLUTION: " + numberedLine(item.fen, solSan) + "\n" : ""}STUDENT TREE: ${C.lines.map((l, i) => (i === C.main ? "[main] " : "") + numberedLine(item.fen, l.map((m) => m.san))).join(" | ")}
RESULT: ${broke ? (broke.type === "own" ? `main line broke at the student's move ${broke.move} (loses ${broke.loss} points; refutation ${broke.refutation.join(" ")})` : `main line broke where the student assumed ${broke.move}; the opponent has ${broke.better} (${broke.line.join(" ")})`) : "main line correct to the end"}; good candidates missed: ${missed.join(", ") || "none"}; peeks: ${C.peeks}; confidence ${C.conf}/5.`;
      try { await askClaude(prompt, { onText: (t) => { cr.innerHTML = coachHtml("المدرّب · مقيّد بشجرة Stockfish", esc(t.text)); } }); }
      catch (e) { cr.innerHTML = coachHtml("المدرّب", esc(claudeMsg(e))); }
    }
  }
  sync();
}

/* ========== 3. Visualization and blindfold ========== */
const VIZ_LEVELS = [
  null,
  { n: 10, ar: "لون المربع", kind: "color" },
  { n: 10, ar: "أين المربع؟ (من جهة الأبيض)", kind: "find", orient: "w" },
  { n: 10, ar: "أين المربع؟ (من جهة الأسود)", kind: "find", orient: "b" },
  { n: 8, ar: "مسار الحصان", kind: "knight" },
  { n: 6, ar: "خط ذهني: نقلتان", kind: "line", plies: 2 },
  { n: 6, ar: "خط ذهني: 4 نقلات", kind: "line", plies: 4 },
  { n: 6, ar: "خط ذهني: 6 نقلات", kind: "line", plies: 6 },
  { n: 5, ar: "خط ذهني: 8 نقلات", kind: "line", plies: 8 },
  { n: 1, ar: "مباراة عمياء: ملك ووزير ضد ملك", kind: "blindKQ" },
  { n: 1, ar: "مباراة عمياء: 10 نقلات من البداية", kind: "blindOpening" },
];
const PIECE_AR = { k: "الملك", q: "الوزير", r: "الرخ", b: "الفيل", n: "الحصان", p: "البيدق" };
function knightDist(a, b) {
  const F = "abcdefgh"; const st = [F.indexOf(a[0]), +a[1] - 1], en = [F.indexOf(b[0]), +b[1] - 1];
  const seen = new Set([st.join()]); let fr = [st], d = 0;
  while (fr.length) { if (fr.some((p) => p[0] === en[0] && p[1] === en[1])) return d; d++; const nx = [];
    for (const [x, y] of fr) for (const [dx, dy] of [[1, 2], [2, 1], [-1, 2], [-2, 1], [1, -2], [2, -1], [-1, -2], [-2, -1]]) { const p = [x + dx, y + dy]; if (p[0] < 0 || p[0] > 7 || p[1] < 0 || p[1] > 7 || seen.has(p.join())) continue; seen.add(p.join()); nx.push(p); }
    fr = nx; }
  return d;
}
const randSq = () => "abcdefgh"[Math.floor(Math.random() * 8)] + (1 + Math.floor(Math.random() * 8));
function VizMode(root, level, done) {
  const L = VIZ_LEVELS[level]; let i = 0, right = 0; const t0 = now(); const log = [];
  if (L.kind === "blindKQ" || L.kind === "blindOpening") return Blindfold(root, L, level, done);
  root.innerHTML = `<div class="panel"><div class="row" style="justify-content:space-between"><h3>التصور · المستوى ${level}: ${L.ar}</h3><span class="note" id="vz-c"></span></div><div id="vz"></div></div>`;
  const box = $("#vz", root);
  const next = () => { if (i >= L.n) return finish(); $("#vz-c", root).textContent = `${i + 1} / ${L.n} · صحيح ${right}`; ({ color, find, knight, line })[L.kind](); };
  const answer = (ok, msg) => { log.push(ok); if (ok) right++; i++; box.insertAdjacentHTML("beforeend", `<div class="callout ${ok ? "good" : "bad"}">${msg}</div>`); setTimeout(next, ok ? 500 : 1500); };
  function color() {
    const sq = randSq(); const light = ("abcdefgh".indexOf(sq[0]) + +sq[1]) % 2 === 0; // a1: 0+1 odd -> dark
    box.innerHTML = `<p class="big-q">ما لون المربع ${mv(sq)}؟</p><div class="choices two"><button class="choice" data-a="l">فاتح</button><button class="choice" data-a="d">داكن</button></div>`;
    for (const b of $$("[data-a]", box)) b.onclick = () => answer((b.dataset.a === "l") === light, `${mv(sq)} ${light ? "فاتح" : "داكن"}.`);
  }
  function find() {
    const sq = randSq();
    box.innerHTML = `<p class="big-q">انقر على المربع ${mv(sq)}</p><div class="board small"></div>`;
    Board($(".board", box), { fen: "8/8/8/8/8/8/8/8 w - - 0 1", orient: L.orient, coords: false, onSquare: (t) => answer(t === sq, t === sq ? "صحيح." : `نقرت ${mv(t)}، والمطلوب ${mv(sq)}.`) });
  }
  function knight() {
    let a = randSq(), b = randSq(); while (a === b) b = randSq(); const d = knightDist(a, b);
    box.innerHTML = `<p class="big-q">كم نقلة يحتاج الحصان ليذهب من ${mv(a)} إلى ${mv(b)}؟</p><p class="note">احسبها في ذهنك. الرقعة فارغة.</p><div class="choices">${[1, 2, 3, 4, 5, 6].map((k) => `<button class="choice" data-a="${k}">${k}</button>`).join("")}</div>`;
    for (const x of $$("[data-a]", box)) x.onclick = () => answer(+x.dataset.a === d, `الجواب ${d}.`);
  }
  function line() {
    const G = pick(DATA.masters); const startPly = Math.min(G.sans.length - L.plies - 1, 6 + Math.floor(Math.random() * 20));
    const g = new Chess(); for (let k = 0; k < startPly; k++) g.move(G.sans[k]); const fen0 = g.fen();
    const seq = G.sans.slice(startPly, startPly + L.plies); const moved = [];
    for (const s of seq) { const m = g.move(s); moved.push(m); }
    box.innerHTML = `<p class="note">احفظ الموقف، ثم تخيّل هذه النقلات دون أن تتحرك القطع:</p><div class="board small"></div><p class="big-q">${mv(numberedLine(fen0, seq))}</p><div class="row"><button class="btn" id="vz-go">تخيّلتها، اسألني</button></div>`;
    Board($(".board", box), { fen: fen0, orient: sideOf(fen0), interactive: false });
    $("#vz-go", box).onclick = () => {
      const m = pick(moved);
      const askWhere = Math.random() < 0.6;
      if (askWhere) {
        box.innerHTML = `<p class="big-q">أين ${PIECE_AR[m.piece]} ${m.color === "w" ? "الأبيض" : "الأسود"} الذي كان على ${mv(m.from)}؟ انقر مربعه.</p><div class="board small"></div>`;
        const finalSq = (() => { let sq = m.to; for (const x of moved.slice(moved.indexOf(m) + 1)) if (x.from === sq) sq = x.to; return sq; })();
        const captured = moved.slice(moved.indexOf(m) + 1).some((x) => x.to === finalSq && x.color !== m.color);
        Board($(".board", box), { fen: "8/8/8/8/8/8/8/8 w - - 0 1", orient: sideOf(fen0), onSquare: (t) => answer(!captured && t === finalSq, captured ? `أُخذ هذا ${PIECE_AR[m.piece]} في الخط.` : `كان على ${mv(finalSq)}.`) });
      } else {
        const sq = m.to; const p = g.get(sq); const truth = p ? p.type + p.color : "empty";
        const opts = shuffle([...new Set([truth, "empty", "nw", "bb", "qw", "rb", "pw", "nb"])]).slice(0, 4); if (!opts.includes(truth)) opts[0] = truth;
        const lab = (o) => o === "empty" ? "فارغ" : `${PIECE_AR[o[0]]} ${o[1] === "w" ? "أبيض" : "أسود"}`;
        box.innerHTML = `<p class="big-q">بعد الخط، ماذا يوجد على ${mv(sq)}؟</p><div class="choices">${shuffle(opts).map((o) => `<button class="choice" data-a="${o}">${lab(o)}</button>`).join("")}</div>`;
        for (const x of $$("[data-a]", box)) x.onclick = () => answer(x.dataset.a === truth, `الجواب: ${lab(truth)}.`);
      }
    };
  }
  function finish() {
    const acc = Math.round(100 * right / L.n);
    const up = acc >= 80 && level < VIZ_LEVELS.length - 1, down = acc < 50 && level > 1;
    box.innerHTML = `<div class="callout ${acc >= 80 ? "good" : acc < 50 ? "bad" : ""}">${right} من ${L.n} (${acc}%). ${up ? "تنتقل إلى المستوى التالي." : down ? "نعود مستوى واحدًا للتثبيت." : "نكرر هذا المستوى حتى 80%."}</div><div class="row"><button class="btn" id="vz-next">التالي</button></div>`;
    $("#vz-next", box).onclick = () => done({ mode: "viz", itemId: "viz-" + level, skill: "visualization", level, n: L.n, right, acc, correct: acc >= 80, newLevel: up ? level + 1 : down ? level - 1 : level, seconds: Math.round((now() - t0) / 1000) });
  }
  next();
}
function Blindfold(root, L, level, done) {
  const KQ = L.kind === "blindKQ";
  const fen0 = KQ ? pick(["8/8/8/4k3/8/8/8/3QK3 w - - 0 1", "8/8/3k4/8/8/8/8/4KQ2 w - - 0 1", "4k3/8/8/8/8/8/8/Q3K3 w - - 0 1"]) : START_FEN;
  const g = new Chess(fen0); const sans = []; let illegal = 0, peeks = 0; const t0 = now(); const maxMoves = KQ ? 30 : 10;
  root.innerHTML = `<div class="panel"><h3>التصور · المستوى ${level}: ${L.ar}</h3>
    <p class="note">${KQ ? "الموقف: " + esc(pieceList(fen0)) + ". أعطِ كش مات بدون رؤية القطع." : "العب 10 نقلات من البداية ضد Stockfish ضعيف، بدون رؤية القطع."} انقر مربع القطعة ثم مربع الوصول.</p>
    <div class="train"><div class="boardwrap"><div class="board"></div><div class="row"><button class="btn ghost" id="bf-peek">اختلس نظرة (تُحسب)</button></div></div>
    <div class="panel side"><div id="bf-moves" class="moves"></div><div id="bf-msg"></div></div></div></div>`;
  const board = Board($(".board", root), { fen: fen0, hidden: true, dots: false, orient: "w", onMove: play });
  const showMoves = () => { $("#bf-moves", root).innerHTML = sans.length ? mv(numberedLine(fen0, sans)) : `<span class="note">لم تُلعب نقلات بعد.</span>`; };
  $("#bf-peek", root).onclick = () => { peeks++; board.update({ hidden: false }); setTimeout(() => board.update({ hidden: true }), 2000); };
  async function play(m) {
    g.move(m.san); sans.push(m.san); showMoves(); board.update({ fen: g.fen(), interactive: false });
    if (g.game_over() || sans.length >= maxMoves * 2) return end();
    const e = await Engine.analyse(g.fen(), { movetime: 300, depth: 8, skill: KQ ? 20 : 2 });
    const r = g.move({ from: e.best.slice(0, 2), to: e.best.slice(2, 4), promotion: "q" }); sans.push(r.san); showMoves();
    board.update({ fen: g.fen(), interactive: true, last: e.best });
    $("#bf-msg", root).innerHTML = `<p>رد Stockfish: ${mv(r.san)}</p>`;
    if (g.game_over() || (!KQ && sans.length >= maxMoves * 2)) end();
  }
  function end() {
    board.update({ hidden: false, interactive: false });
    const ok = KQ ? g.in_checkmate() : true; const acc = ok ? Math.max(0, 100 - peeks * 20) : 0;
    $("#bf-msg", root).innerHTML = `<div class="callout ${ok && peeks === 0 ? "good" : "bad"}">${KQ ? (g.in_checkmate() ? `كش مات في ${Math.ceil(sans.length / 2)} نقلة.` : g.in_stalemate() ? "تعادل بالـ stalemate! انتبه لمربعات الملك." : "لم يكتمل الكش المات.") : "أكملت 10 نقلات."} نظرات: ${peeks}.</div><div class="row"><button class="btn" id="bf-next">التالي</button></div>`;
    $("#bf-next", root).onclick = () => done({ mode: "viz", itemId: "viz-" + level, skill: "visualization", level, n: 1, right: acc >= 80 ? 1 : 0, acc, correct: acc >= 80, newLevel: acc >= 80 && level < VIZ_LEVELS.length - 1 ? level + 1 : level, seconds: Math.round((now() - t0) / 1000) });
  }
  showMoves();
}

/* ========== 4. Guess the move ========== */
const REASONS = ["تطوير قطعة", "السيطرة على المركز", "أمان الملك", "هجوم", "صدّ تهديد", "تبادل أو تبسيط", "تحسين أسوأ قطعة", "فتح خط أو عمود", "كسب مادة"];
function GuessMode(root, G, opts, done) {
  const prog = S.profile.guess[G.id] || { ply: 0, pts: 0, max: 0 }; let ply = prog.ply >= G.sans.length ? 0 : prog.ply;
  const limit = opts.moves || 999; let asked = 0; const t0 = now(); const seg = { pts: 0, max: 0, n: 0 };
  root.innerHTML = `<div class="train"><div class="boardwrap"><div class="boardcap"><span><b>${esc(G.white)}</b> – <b>${esc(G.black)}</b></span><span class="note">${esc(G.event)}</span></div><div class="board"></div><div id="gm-moves" class="moves"></div></div>
    <div class="panel side"><p class="note">${esc(G.intro)}</p><p>أنت تلعب بـ${G.side === "w" ? "الأبيض" : "الأسود"}. في كل نقلة لك: توقّع نقلة الأستاذ ولماذا.</p><div id="gm-q"></div><div id="gm-a"></div></div></div>`;
  const g = new Chess(); for (let k = 0; k < ply; k++) g.move(G.sans[k]);
  const board = Board($(".board", root), { fen: g.fen(), orient: G.side, interactive: false, last: ply ? G.ucis[ply - 1] : null });
  const qEl = $("#gm-q", root), aEl = $("#gm-a", root);
  const showMoves = () => { $("#gm-moves", root).innerHTML = mv(numberedLine(START_FEN, G.sans.slice(0, ply))) || ""; };
  async function advance() {
    showMoves();
    if (ply >= G.sans.length) return finish(true);
    if (sideOf(g.fen()) !== G.side) { await sleep(500); const m = g.move(G.sans[ply]); ply++; board.update({ fen: g.fen(), last: m.from + m.to }); return advance(); }
    if (asked >= limit) return finish(false);
    qEl.innerHTML = `<h3>نقلتك ${Math.floor(ply / 2) + 1}${G.side === "w" ? "." : "..."}</h3><p>انقر النقلة التي تتوقع أن الأستاذ لعبها.</p>`; aEl.innerHTML = "";
    board.update({ interactive: true, onMove: (m) => { board.update({ interactive: false, fen: m.fenAfter, last: m.uci }); reasonStep(m); } });
  }
  function reasonStep(m) {
    qEl.innerHTML = `<p>توقعت ${mv(m.san)}. لماذا؟ اختر السبب الرئيسي:</p><div class="choices">${REASONS.map((r, i) => `<button class="choice" data-r="${i}">${r}</button>`).join("")}</div>`;
    for (const b of $$("[data-r]", qEl)) b.onclick = () => reveal(m, REASONS[+b.dataset.r]);
  }
  async function reveal(m, reason) {
    const fen = g.fen(); const master = G.ucis[ply], masterSan = G.sans[ply]; asked++;
    let pts = 0, note = "";
    if (m.uci === master) { pts = 2; note = "نفس نقلة الأستاذ."; }
    else {
      qEl.innerHTML = `<p class="note">Stockfish يقارن...</p>`;
      const s = G.side === "w" ? 1 : -1;
      const [a, b] = [await Engine.analyse(m.fenAfter, { depth: 14, movetime: 900 }), await Engine.analyse(fenAfter(fen, master), { depth: 14, movetime: 900 })];
      const diff = wp(s * b.cp) - wp(s * a.cp);
      if (diff <= 4) { pts = 1; note = `ليست نقلة الأستاذ، لكن Stockfish يراها بنفس القوة تقريبًا (${fmtEval(a.cp)} مقابل ${fmtEval(b.cp)}).`; }
      else note = `Stockfish: نقلتك ${fmtEval(a.cp)}، ونقلة الأستاذ ${fmtEval(b.cp)} (من جهة الأبيض).`;
      m.evalCp = a.cp; m.masterCp = b.cp;
    }
    seg.pts += pts; seg.max += 2; seg.n++; prog.pts += pts; prog.max += 2;
    const mm = g.move(masterSan); ply++; board.update({ fen: g.fen(), last: master });
    qEl.innerHTML = `<div class="callout ${pts === 2 ? "good" : pts ? "" : "bad"}">الأستاذ لعب ${mv(masterSan)}. ${note} (+${pts})</div><div id="gm-ex"></div><div class="row"><button class="btn" id="gm-n">التالي</button>${pts === 2 && SAMPLE ? `<button class="btn quiet" id="gm-why">لماذا هذه النقلة؟</button>` : ""}</div>`;
    const ex = $("#gm-ex", qEl);
    const explain = () => explainMaster(ex, G, fen, masterSan, m.san, reason);
    if (pts < 2) explain(); const w = $("#gm-why", qEl); if (w) w.onclick = () => { w.remove(); explain(); };
    $("#gm-n", qEl).onclick = () => { prog.ply = ply; S.profile.guess[G.id] = prog; saveProfile(); advance(); };
  }
  function finish(gameOver) {
    prog.ply = gameOver ? G.sans.length : ply; S.profile.guess[G.id] = prog; saveProfile();
    const p = seg.max ? Math.round(100 * seg.pts / seg.max) : 0;
    qEl.innerHTML = `<div class="callout">${gameOver ? "انتهت المباراة." : "انتهى هذا الجزء."} نقاطك: ${seg.pts} من ${seg.max} (${p}%).</div><div id="gm-sum"></div><div class="row"><button class="btn" id="gm-end">التالي</button></div>`;
    if (gameOver && SAMPLE) {
      const el = $("#gm-sum", qEl); el.innerHTML = coachHtml("خطة الأستاذ", "يكتب...");
      askClaude(`In Arabic, 4-5 sentences for a beginner: summarize the plan and the main lesson of this famous game. Use only the moves given; do not invent variations.\n${LANG_RULES}\nGAME: ${G.white} vs ${G.black}, ${G.event}\nMOVES: ${numberedLine(START_FEN, G.sans)}\nTHEME: ${G.concept}`,
        { tier: "quick", cache: { gcTime: 86400000 }, onText: (t) => { el.innerHTML = coachHtml("خطة الأستاذ", esc(t.text)); } }).catch((e) => { el.innerHTML = ""; });
    }
    $("#gm-end", qEl).onclick = () => done({ mode: "guess", itemId: G.id, skill: "strategy", pts: seg.pts, max: seg.max, n: seg.n, correct: seg.max ? seg.pts / seg.max >= 0.5 : false, acc: p, seconds: Math.round((now() - t0) / 1000) });
  }
  advance();
}
async function explainMaster(el, G, fen, masterSan, guessSan, reason) {
  if (!SAMPLE) return;
  el.innerHTML = coachHtml("لماذا لعبها الأستاذ؟", "يكتب...");
  const e = await Engine.analyse(fen, { depth: 14, movetime: 1000, multipv: 2 });
  const prompt = `Explain in Arabic, in 2-3 short sentences for a beginner, why the master played ${masterSan} here and what plan it serves. If the student's guess differs, say in one sentence what it misses. Comment on the student's stated reason.
${LANG_RULES}
GAME: ${G.white} vs ${G.black}, ${G.event}. Theme: ${G.concept}.
FEN BEFORE THE MOVE: ${fen}
PIECES: ${pieceList(fen)}
MASTER'S MOVE: ${masterSan}
STUDENT'S GUESS: ${guessSan}; student's reason: ${reason}
ENGINE DATA: ${e.lines.map((l) => fmtEval(l.cpWhite) + ": " + numberedLine(fen, pvToSan(fen, l.pv, 6))).join(" | ")}`;
  try { await askClaude(prompt, { tier: "quick", cache: { gcTime: 86400000 }, onText: (t) => { el.innerHTML = coachHtml("لماذا لعبها الأستاذ؟ · مقيّد بـ Stockfish", esc(t.text)); } }); }
  catch (err) { el.innerHTML = ""; }
}

/* ========== 5. Play out the position ========== */
const PLAYOUT_AR = { KQK: "ملك ووزير ضد ملك", KRK: "ملك ورخ ضد ملك", KPK: "ملك وبيدق ضد ملك", Lucena: "موقف Lucena", KBBK: "ملك وفيلان ضد ملك" };
function PlayoutMode(root, pos, opts, done) {
  const side = pos.side; const s = side === "w" ? 1 : -1; const skill = opts.skill ?? 20;
  const g = new Chess(pos.f); const hist = [{ fen: pos.f, cp: pos.cp * s }]; const t0 = now(); let over = false;
  root.innerHTML = `<div class="train"><div class="boardwrap"><div class="boardcap"><span class="turn"><i class="${side}"></i>أنت ${side === "w" ? "الأبيض" : "الأسود"}</span><span class="note" id="po-ev"></span></div><div class="board"></div><div id="po-moves" class="moves"></div></div>
    <div class="panel side"><h3>${pos.basic ? PLAYOUT_AR[pos.basic] : "حوّل الأفضلية إلى فوز"}</h3>
    <p class="note">${pos.basic ? "موقف رابح نظريًا. المطلوب: كش مات." : `موقف من مباراة حقيقية، Stockfish يقيّمه بـ ${fmtEval(pos.cp)} لصالحك. المطلوب: كش مات، دون أن تفقد الأفضلية.`} الخصم Stockfish بمستوى ${skill} من 20.</p>
    <div id="po-msg"></div></div></div>`;
  const board = Board($(".board", root), { fen: g.fen(), orient: side, onMove: play, interactive: sideOf(pos.f) === side });
  const sans = [];
  const showMoves = () => { $("#po-moves", root).innerHTML = mv(numberedLine(pos.f, sans)); };
  if (sideOf(pos.f) !== side) engineMove();
  async function play(m) {
    if (over) return; g.move(m.san); sans.push(m.san); showMoves(); board.update({ fen: g.fen(), last: m.uci, interactive: false });
    if (g.game_over()) return end();
    await engineMove();
  }
  async function engineMove() {
    $("#po-msg", root).innerHTML = `<p class="note">الخصم يفكّر...</p>`;
    const e = await Engine.analyse(g.fen(), { movetime: 600, depth: 14, skill });
    const userCp = s * e.cp; hist.push({ fen: g.fen(), cp: userCp, san: sans[sans.length - 1] });
    $("#po-ev", root).textContent = "تقييم: " + fmtEval(e.cp);
    if (userCp < 150 && Math.abs(userCp) < 9000) { $("#po-msg", root).innerHTML = ""; return end("lost"); }
    const r = g.move({ from: e.best.slice(0, 2), to: e.best.slice(2, 4), promotion: e.best[4] || "q" }); sans.push(r.san); showMoves();
    board.update({ fen: g.fen(), last: e.best, interactive: !g.game_over() });
    $("#po-msg", root).innerHTML = "";
    if (g.game_over()) return end();
    if (sans.length > 160) end("limit");
  }
  async function end(why) {
    over = true; board.update({ interactive: false });
    const win = g.in_checkmate() && sideOf(g.fen()) !== side;
    const msg = win ? `كش مات في ${Math.ceil(sans.length / 2)} نقلة. حوّلت الموقف.` : why === "lost" ? "فقدت الأفضلية: التقييم نزل تحت +1.5. هذا هو الدرس." : g.in_stalemate() ? "Stalemate! تعادل. انتبه دائمًا: هل للملك مربع؟" : g.in_draw() ? "تعادل (تكرار أو 50 نقلة أو مادة غير كافية)." : "تجاوزت حد النقلات.";
    $("#po-msg", root).innerHTML = `<div class="callout ${win ? "good" : "bad"}">${msg}</div><div id="po-ex"></div><div class="row"><button class="btn" id="po-next">التالي</button><button class="btn quiet" id="po-again">أعد المحاولة</button></div>`;
    const R = { mode: "playout", itemId: pos.i, skill: pos.phase === "endgame" ? "endgame" : "conversion", correct: win, moves: Math.ceil(sans.length / 2), result: win ? "win" : why || "draw", strength: skill, seconds: Math.round((now() - t0) / 1000) };
    $("#po-next", root).onclick = () => done(R);
    $("#po-again", root).onclick = () => { done({ ...R, retry: true }); };
    // the three biggest drops in the user's evaluation
    const drops = []; for (let k = 1; k < hist.length; k++) drops.push({ k, d: hist[k - 1].cp - hist[k].cp, san: hist[k].san, fen: hist[k - 1].fen });
    const worst = drops.filter((d) => d.d > 80).sort((a, b) => b.d - a.d).slice(0, 3);
    if (SAMPLE && (worst.length || !win)) {
      const ex = $("#po-ex", root); ex.innerHTML = coachHtml("المدرّب", "يكتب...");
      const facts = [];
      for (const w of worst) { const b = await Engine.analyse(w.fen, { depth: 14, movetime: 800 }); facts.push(`before ${w.san}: engine preferred ${pvToSan(w.fen, b.lines[0]?.pv || [b.best], 4).join(" ")} (${fmtEval(b.cp)}); after ${w.san} the evaluation dropped by ${Math.round(w.d)} cp`); }
      askClaude(`A beginner tried to convert a winning position against Stockfish. In Arabic, 3-4 sentences: was the conversion technique right, and what was the main lesson (e.g. restrict the king, avoid stalemate, push passed pawns with king support, trade pieces when ahead). Use only the facts given.\n${LANG_RULES}\nSTART FEN: ${pos.f}\nRESULT: ${R.result}, ${R.moves} moves\nMOVES: ${numberedLine(pos.f, sans)}\nBIGGEST MISTAKES: ${facts.join(" | ") || "none"}`,
        { tier: "quick", onText: (t) => { ex.innerHTML = coachHtml("المدرّب · مقيّد بـ Stockfish", esc(t.text)); } }).catch(() => { ex.innerHTML = ""; });
    }
  }
}

/* ========== 8. Patterns: learn a chunk, then mixed tests ========== */
function StructQuestion(root, item, { labeled = false } = {}, done) {
  const t0 = now(); const R = { mode: "pattern", itemId: item.id, skill: "strategy", themes: item.themes, kind: "struct", chunk: item.s === "carlsbad" ? "carlsbad" : item.s === "none" ? null : "iqp" };
  root.innerHTML = `<div class="train"><div class="boardwrap"><div class="board"></div><p class="note">${esc(item.op || "")}</p></div><div class="panel side"><div id="sq-a"></div><div id="sq-b"></div></div></div>`;
  const board = Board($(".board", root), { fen: item.fen, orient: "w", interactive: false });
  const A = $("#sq-a", root);
  const ask2 = () => {
    if (item.s === "none") return end();
    const P = STRUCT_PLANS[item.s]; const ch = shuffle([P.right, ...P.wrong]);
    $("#sq-b", root).innerHTML = `<h3>${P.q}</h3><div class="choices col">${ch.map((c, i) => `<button class="choice" data-p="${i}">${c}</button>`).join("")}</div>`;
    for (const b of $$("[data-p]", root)) b.onclick = () => { R.planRight = ch[+b.dataset.p] === P.right; $("#sq-b", root).innerHTML = `<div class="callout ${R.planRight ? "good" : "bad"}">${R.planRight ? "صحيح." : "الخطة النموذجية: " + P.right}</div>`; end(); };
  };
  if (labeled) { R.recognized = true; A.innerHTML = `<div class="callout">${STRUCT_AR[item.s]}. لاحظ البيادق: ${item.s === "carlsbad" ? "الأبيض بلا بيدق c، والأسود بلا بيدق e." : "البيدق على العمود d بلا جيران على c وe."}</div>`; ask2(); }
  else {
    const keys = ["iqp-w", "iqp-b", "carlsbad", "none"];
    A.innerHTML = `<h3>ما بنية البيادق هنا؟</h3><div class="choices col">${keys.map((k) => `<button class="choice" data-k="${k}">${STRUCT_AR[k]}</button>`).join("")}</div>`;
    for (const b of $$("[data-k]", A)) b.onclick = () => { R.recognized = b.dataset.k === item.s; A.innerHTML = `<div class="callout ${R.recognized ? "good" : "bad"}">${R.recognized ? "صحيح: " : "الجواب: "}${STRUCT_AR[item.s]}</div>`; ask2(); };
  }
  function end() {
    R.correct = !!R.recognized && (item.s === "none" || !!R.planRight); R.solvedAt = R.correct ? 1 : 0; R.seconds = Math.round((now() - t0) / 1000);
    $("#sq-b", root).insertAdjacentHTML("beforeend", `<div class="row"><button class="btn" id="sq-n">التالي</button></div>`);
    $("#sq-n", root).onclick = () => done(R);
  }
}
function PatternTestItem(root, item, learned, done) {
  if (item.kind === "struct") return StructQuestion(root, item, {}, done);
  const own = item.themes.filter((t) => CHUNK[t] && learned.includes(t));
  const truth = own[0] || item.themes.find((t) => CHUNK[t]);
  const others = shuffle(learned.filter((k) => !item.themes.includes(k) && CHUNK[k].g !== "structure")).slice(0, 3);
  const opts = shuffle([truth, ...others]);
  root.innerHTML = `<div class="train"><div class="boardwrap"><div class="board"></div></div><div class="panel side"><h3>أولًا: ما النمط في هذا الموقف؟</h3><p class="note">لا تحل بعد. حدّد نوع الموقف.</p><div class="choices col">${opts.map((k) => `<button class="choice" data-k="${k}">${CHUNK[k].ar}</button>`).join("")}</div></div></div>`;
  Board($(".board", root), { fen: item.fen, orient: sideOf(item.fen), last: item.last, interactive: false });
  for (const b of $$("[data-k]", root)) b.onclick = () => {
    const recognized = item.themes.includes(b.dataset.k) || b.dataset.k === truth;
    const label = `<div class="callout ${recognized ? "good" : "bad"}">${recognized ? "صحيح: " : "النمط: "}${CHUNK[truth].ar}. الآن حلّه.</div>`;
    Solver(root, item, { labelHtml: label, onDone: (r) => done({ ...r, mode: "pattern", recognized, chunk: truth }) });
  };
}

/* ========== 12. Timed decisions ========== */
const timeFor = (r) => (r < 1000 ? 30 : r < 1300 ? 45 : 60);
