/* In-memory stand-in for the claude.ai runtime: db, user, sample, downloads, permissions. Test use only. */
(() => {
  const SEED = window.__SEED__ || null;
  const store = new Map(); const subs = []; const UID = 'u_test';
  const cloneJ = o => o === undefined ? undefined : JSON.parse(JSON.stringify(o));
  const snapDoc = (path) => { const d = store.get(path); const id = path.split('/').pop(); return Object.freeze({id, exists: d !== undefined, data: () => cloneJ(d), metadata: {fromCache: false, hasPendingWrites: false}}); };
  const colDocs = cp => { const out = []; for (const [p] of store) { const i = p.lastIndexOf('/'); if (p.slice(0, i) === cp) out.push(p); } return out; };
  function run(q) {
    let ps = colDocs(q.path);
    if (q.order) { const [f, dir] = q.order; ps.sort((a, b) => { const x = store.get(a)[f], y = store.get(b)[f]; if (x === y) return 0; if (x === undefined) return 1; if (y === undefined) return -1; return (x < y ? -1 : 1) * (dir === 'desc' ? -1 : 1); }); }
    if (q.lim) ps = ps.slice(0, q.lim);
    const docs = ps.map(snapDoc); return {docs, size: docs.length, empty: !docs.length, docChanges: () => [], metadata: {fromCache: false, hasPendingWrites: false}};
  }
  let pending = false;
  function notify() { if (pending) return; pending = true; setTimeout(() => { pending = false; subs.forEach(s => s.kind === 'col' ? s.cb(run(s.q)) : s.cb(snapDoc(s.path))); }, 0); }
  const checkPath = (p, even) => { const n = p.split('/').length; if ((n % 2 === 0) !== even) throw new TypeError('bad path parity ' + p); };
  function query(path, order = null, lim = null) {
    checkPath(path, false); const q = {path, order, lim};
    return {path, where() { return this; }, orderBy: (f, d = 'asc') => query(path, [f, d], lim), limit: n => query(path, order, n), get: async () => run(q),
      onSnapshot(cb) { const s = {kind: 'col', q, cb}; subs.push(s); setTimeout(() => cb(run(q)), 0); return () => { const i = subs.indexOf(s); if (i >= 0) subs.splice(i, 1); }; },
      doc: id => docRef(path + '/' + (id || Math.random().toString(36).slice(2)))};
  }
  function docRef(path) {
    checkPath(path, true);
    return {id: path.split('/').pop(), path, get: async () => snapDoc(path),
      set: async d => { if (!d || typeof d !== 'object' || Array.isArray(d)) throw {code: 'invalid_argument', message: 'body'}; const s = JSON.stringify(d); if (s.length > 262144) throw {code: 'invalid_argument', message: 'too big'}; await new Promise(r => setTimeout(r, 3)); store.set(path, JSON.parse(s)); window.__writes = (window.__writes || 0) + 1; notify(); },
      update: async d => { const cur = store.get(path); if (!cur) throw {code: 'invalid_argument'}; store.set(path, {...cur, ...cloneJ(d)}); notify(); },
      delete: async () => { store.delete(path); notify(); },
      onSnapshot(cb) { const s = {kind: 'doc', path, cb}; subs.push(s); setTimeout(() => cb(snapDoc(path)), 0); return () => {}; },
      collection: p => query(path + '/' + p)};
  }
  const base = 'data/users/' + UID;
  if (SEED) { store.set(base + '/profile', cloneJ(SEED.profile)); store.set(base + '/settings', cloneJ(SEED.settings)); for (const [c, docs] of Object.entries(SEED.collections)) docs.forEach(d => store.set(base + '/os/' + c + '/' + d.id, cloneJ(d))); }
  window.__store = store;
  const db = {doc: docRef, collection: p => query(p)};
  const user = {id: async () => UID, isOwner: async () => true, canEdit: async () => true, can: async () => true, profiles: async () => ({})};
  window.__prompts = [];
  const sample = async (input, opts = {}) => {
    const text = typeof input === 'string' ? input : input.map(t => t.content).join('\n');
    if (typeof input !== 'string') { if (input[0].role !== 'user' || input[input.length - 1].role !== 'user') throw {code: 'invalid_request', message: 'turns'}; }
    if (new Blob([text]).size > 262144) throw {code: 'prompt_too_large', message: 'big'};
    window.__prompts.push({len: text.length, head: text.slice(0, 80), tier: opts.modelTier, model: opts.model, effort: opts.effort});
    const out = fake(text);
    await new Promise(r => setTimeout(r, 120));
    if (opts.signal && opts.signal.aborted) throw {code: 'cancelled'};
    if (opts.onText) opts.onText({text: out, delta: out});
    return {text: out, truncated: false, modelTierApplied: opts.modelTier || 'default', modelApplied: opts.model};
  };
  sample.limits = async () => ({maxPromptBytes: 262144, tools: {maxCount: 8}});
  function fake(p) {
    const J = o => JSON.stringify(o);
    if (p.includes("Write today's morning briefing")) return 'Here is the briefing.\n```json\n' + J({
      theme: {title: 'Turn guidelines into protocol checks', why: 'You have an unread 2026 anemia guideline in your library and no wheel scores yet. One focused comparison beats more reading.'},
      big_picture: {improving: ['Nothing measured yet — no check-ins or scores'], stagnating: [], neglected: ['Wheel not scored', 'No check-ins recorded'], attention: 'Score the wheel so tomorrow can compare.'},
      sections: [
        {key: 'career', dimension: 'career', title: 'KDIGO 2026 anemia: three numbers', format: 'Guideline update', minutes: 6, body: 'The 2026 guideline sets **iron start** at ferritin ≤500 and TSAT ≤30%.\n\n- ESA first line\n- Hb < 11.5 on ESA', task: '1. Open your unit protocol.\n2. Compare the three numbers.', evidence: 'established', source_ids: ['lib-kdigo-anemia-2026', 'bogus-id'], card_ids: ['c-s-ph02', 'nope']},
        {key: 'growth', dimension: 'growth', title: 'A 60-second voice memo', format: 'Voice drill', minutes: 3, body: 'Record one minute.', task: 'Count fillers.', evidence: 'emerging', source_ids: [], card_ids: []},
        {key: 'finance', dimension: 'finance', title: 'Expectancy after costs', format: 'Probability problem', minutes: 4, body: 'Win rate alone says nothing.', task: 'Solve the card.', evidence: 'model-knowledge', source_ids: [], card_ids: ['c-s-qu02']},
      ],
      final: {one_thing: 'Compare the anemia protocol with KDIGO 2026.', smallest_action: 'Open the protocol file now.', measure: 'A list of differences exists by 2 pm.'},
      challenge: 'You asked for a life OS but have recorded no baseline yet.', data_gaps: ['Wheel scores', 'Sleep data']}) + '\n```';
    if (p.includes('stage 2 (REFLECT)')) return J({progress: [{dimension: 'career', text: 'Started learning cards', evidence: '2 answers'}], obstacles: [], new_interests: ['HDF'], priority_shifts: ['Career up'], patterns: [{observation: 'Reads but does not apply sources', evidence: '3 read, 0 applied', hypothesis: 'Application step is undefined', experiment: 'Apply one source per week', dimension: 'career', confidence: 'low'}], balance: {neglected: ['fun'], overinvested: [], note: 'Fun has no data.'}, classification: [{dimension: 'career', status: 'priority', why: 'stated'}], simplify: null, unresolved_questions: ['Which Tadawul data source?'], research_questions: [{topic: 'pharm', question: 'Any 2026 changes to IV iron dosing in hemodialysis?', why: 'protocol'}]});
    if (p.includes('stages 5–7')) return J({new_knowledge: [{source_id: 'lib-kdigo-anemia-2026', what_is_new: 'Iron start thresholds', changes_understanding: 'Higher ferritin allowed', relevance: 'daily', action: 'compare protocol', uncertainty: 'full text unread'}], model_changes: [{type: 'goal', dimension: 'career', text: 'Audit the anemia protocol against KDIGO 2026 this month', horizon: 'monthly', measure: 'differences listed', why: 'new guideline'}, {type: 'memory', dimension: 'career', text: 'Prefers protocol comparisons over reading summaries', kind: 'hypothesis', category: 'learning', evidence: 'one briefing', why: 'test'}], new_cards: [{track: 'pharm', type: 'case', concept: 'IV iron hold rules', prompt: 'When should IV iron be held under KDIGO 2026 in HD?', answer: 'Ferritin >700 or TSAT ≥40%.', explanation: 'Illustration.', source_id: 'lib-kdigo-anemia-2026', importance: 2, level: 2, related: ['Iron and ESA thresholds (KDIGO 2026)']}], experiments: [{title: 'Apply one library source each week', dimension: 'career', problem: 'reading without applying', hypothesis: 'a weekly slot raises application', intervention: 'Friday 20 min', measure: 'sources applied', unit: 'count', duration_days: 28, success: '3 of 4 weeks', confounders: 'workload'}], verdicts: [{kind: 'enough-apply', text: 'You know enough about KDIGO 2026 iron thresholds. Apply them to your protocol.'}, {kind: 'not-today', text: 'HDF is interesting but not today.'}], next_actions: [{title: 'Protocol comparison', dimension: 'career', minutes: 20, kind: 'act', why: 'new guideline'}], why_it_matters: 'The guideline changes numbers you use weekly.'});
    if (p.includes("Grade a learner's answer")) return J({score: 72, verdict: 'partly', right: ['Loading dose range'], gaps: ['Pre-dialysis level target'], misconception: null, feedback: 'Good start.', criteria: p.includes('RUBRIC') ? [{name: 'States concern', score: 2, note: 'clear'}, {name: 'Recommendation', score: 1, note: 'vague'}] : [], better_version: p.includes('RUBRIC') ? 'Dr X, …' : null, transfer_question: 'How would residual urine output change your plan?', suggested_rating: 'good', reference_concern: null});
    if (p.includes('Assess one life dimension')) return J({summary: 'Thin evidence so far.', excellence_gap: 'Unknown until scored.', evidence: ['No check-ins'], status_suggestion: 'priority', why_status: 'You named it first.', next_experiment: {title: 'Ten minutes of cases daily', hypothesis: 'Accuracy rises', intervention: '10 min', measure: 'weekly accuracy', duration_days: 14}, watch_out: 'Reading instead of answering.'});
    if (p.includes("Synthesise this person's")) return J({summary: 'A quiet week.', activity_vs_achievement: 'Mostly activity.', keep: ['check-ins'], change: ['earlier start'], drop: ['late reading'], lesson: 'Small beats big.', next_focus: 'Protocol comparison.', question: 'What would make next week easy?'});
    if (p.includes('active-recall items')) return J([{type: 'case', concept: 'Cefepime neurotoxicity', prompt: 'A HD patient on cefepime becomes confused. What do you suspect?', answer: 'Cefepime neurotoxicity.', explanation: 'Accumulation.', source: null, importance: 2, level: 2, related: ['Drugs that accumulate in ESKD'], rubric: null}, {type: 'concept', concept: 'Dup', prompt: 'Which drug properties make a medicine likely to be removed by hemodialysis? Give one example of how this changes dose timing.', answer: 'x', explanation: 'y', importance: 1, level: 1, related: []}]);
    if (p.includes('Connection test')) return '{"ok": true}';
    if (p.includes('Extract durable personal memory')) return J([{category: 'interests', kind: 'fact', text: 'Is interested in Arabic calligraphy as a hobby.', dimension: 'fun', confidence: 'medium', evidence: 'I want to learn calligraphy', source_title: 'Hobbies', source_date: '2026-09-01', duplicate_of: null, conflicts_with: null}, {category: 'goals', kind: 'fact', text: 'Wants to build AI-powered pharmacy tools and automate repetitive work in the unit.', dimension: 'career', confidence: 'high', evidence: 'x', source_title: 'Work', source_date: null, duplicate_of: null, conflicts_with: null}]);
    if (p.includes("LIFE OS's coach")) return 'You have **no wheel scores** yet.\n\n- Score the wheel\n- Then choose three priorities.';
    return '{}';
  }
  const downloads = {save: async ({filename, data}) => { window.__download = {filename, size: data.length}; return {status: 'saved'}; }};
  const perm = {state: async () => 'prompt', request: async () => ({}), manage: async () => {}};
  const caps = {db, user, sample, downloads, permissions: perm};
  window.claude = {use: async n => { await new Promise(r => setTimeout(r, 15)); return caps[n] ?? null; }};
})();
