// Generate candidate demo games: the coach (Stockfish 17.1, preferring development and castling in the opening when they
// are within 15 cp of the best move) against Maia-1100 (moves sampled from its probabilities). Prints short decisive games
// in which Maia broke opening principles, for the narrated Watch demos.
//   node tools/gen_demo.mjs [games=40] [seed=1]
import fs from 'fs';
import { createRequire } from 'module';
import { Pool } from './sfpool.mjs';
const require = createRequire(import.meta.url);
const { Chess } = require('../chess.js');
const MaiaNet = require('../engines/maia/maia.js');
const Facts = require('../js/facts.js');
const N = +(process.argv[2] || 40); let seed = +(process.argv[3] || 1);
const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
const man = JSON.parse(fs.readFileSync('engines/maia/manifest.json', 'utf8'));
const buf = fs.readFileSync('engines/maia/' + man.files['1100'].file);
const net = MaiaNet.load(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength), man);
const pool = new Pool(2);
const HOME = { b1: 'n', g1: 'n', c1: 'b', f1: 'b' };
const out = [];
for (let gi = 0; gi < N; gi++) {
  const g = new Chess(); const ucis = []; let result = null;
  while (!g.game_over() && ucis.length < 70) {
    let uci;
    if (g.turn() === 'w') {
      const a = await pool.analyse(g.fen(), { depth: 14, multipv: 4 });
      if (Math.abs(a.lines[0].cpWhite) > 600 && ucis.length > 20) { result = a.lines[0].cpWhite > 0 ? 'white decisive' : 'black decisive'; break; }
      uci = a.best;
      if (ucis.length < 20) for (const l of a.lines) {
        const u = l.pv[0]; if (a.lines[0].cpWhite - l.cpWhite > 15) continue;
        const m = new Chess(g.fen()).move({ from: u.slice(0, 2), to: u.slice(2, 4), promotion: 'q' });
        if (m && (HOME[m.from] === m.piece || m.flags.includes('k'))) { uci = u; break; }
      }
    } else {
      const r = net.evaluate('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', ucis);
      let x = rnd(); let pick = r.policy[0];
      for (const m of r.policy) { if (m.p < 0.01) continue; x -= m.p; if (x <= 0) { pick = m; break; } }
      uci = pick.uci;
    }
    const m = g.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci[4] || 'q' }); ucis.push(m.from + m.to + (m.promotion || ''));
  }
  if (g.in_checkmate()) result = g.turn() === 'b' ? 'white mates' : 'black mates';
  const sans = g.history();
  const ck = Facts.openingChecklist(sans, 'b'), cw = Facts.openingChecklist(sans, 'w');
  out.push({ gi, plies: sans.length, result, black: ck && ck.items, blackScore: ck && ck.score, whiteScore: cw && cw.score, moves: sans.join(' ') });
  console.log(`${gi} plies ${sans.length} ${result} blackChecklist ${ck ? ck.score : '-'} ${JSON.stringify(ck && ck.items)} | ${sans.slice(0, 24).join(' ')}`);
}
fs.writeFileSync('/tmp/claude-0/demo_candidates.json', JSON.stringify(out, null, 1));
pool.close();
