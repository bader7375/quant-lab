// Master games for guess-the-move. Each game is replayed with chess.js; any illegal move aborts the build,
// so a misremembered score cannot reach the app.
import { createRequire } from 'module'; import fs from 'fs'; import path from 'path';
const require = createRequire(import.meta.url);
const root = path.join(path.dirname(new URL(import.meta.url).pathname), '..');
const { Chess } = require(path.join(root, 'chess.js'));
const GAMES = [
  { id: 'opera-1858', white: 'Paul Morphy', black: 'Duke Karl / Count Isouard', event: 'Paris (Opera) 1858', side: 'w', concept: 'development',
    intro: 'Morphy يطوّر قطعه بسرعة ويفتح الخطوط ضد ملك لم يبيّت بعد. الدرس الأساسي: في الافتتاح، كل نقلة تطوّر قطعة أو تفتح خطًا، والتقدم في التطوير يتحوّل إلى هجوم.',
    moves: 'e4 e5 Nf3 d6 d4 Bg4 dxe5 Bxf3 Qxf3 dxe5 Bc4 Nf6 Qb3 Qe7 Nc3 c6 Bg5 b5 Nxb5 cxb5 Bxb5+ Nbd7 O-O-O Rd8 Rxd7 Rxd7 Rd1 Qe6 Bxd7+ Nxd7 Qb8+ Nxb8 Rd8#' },
  { id: 'reti-tartakower-1910', white: 'Richard Réti', black: 'Savielly Tartakower', event: 'Vienna 1910', side: 'w', concept: 'king safety',
    intro: 'الأسود يأخذ بيدقًا بالوزير ويترك ملكه في المركز. Réti يبيّت طويلًا ويضحّي بالوزير ليصطاد الملك. الدرس: الملك في المركز مع خطوط مفتوحة هدف قاتل.',
    moves: 'e4 c6 d4 d5 Nc3 dxe4 Nxe4 Nf6 Qd3 e5 dxe5 Qa5+ Bd2 Qxe5 O-O-O Nxe4 Qd8+ Kxd8 Bg5+ Kc7 Bd8#' },
  { id: 'evergreen-1852', white: 'Adolf Anderssen', black: 'Jean Dufresne', event: 'Berlin 1852 (Evergreen)', side: 'w', concept: 'attack',
    intro: 'Evans Gambit: الأبيض يضحّي ببيدق مقابل التطوير والمركز، ثم يفتح الأعمدة نحو الملك الأسود. الدرس: التطوير والأعمدة المفتوحة أهم من بيدق إضافي.',
    moves: 'e4 e5 Nf3 Nc6 Bc4 Bc5 b4 Bxb4 c3 Ba5 d4 exd4 O-O d3 Qb3 Qf6 e5 Qg6 Re1 Nge7 Ba3 b5 Qxb5 Rb8 Qa4 Bb6 Nbd2 Bb7 Ne4 Qf5 Bxd3 Qh5 Nf6+ gxf6 exf6 Rg8 Rad1 Qxf3 Rxe7+ Nxe7 Qxd7+ Kxd7 Bf5+ Ke8 Bd7+ Kf8 Bxe7#' },
  { id: 'immortal-1851', white: 'Adolf Anderssen', black: 'Lionel Kieseritzky', event: 'London 1851 (Immortal)', side: 'w', concept: 'activity over material',
    intro: 'Anderssen يعطي رخّين ووزيرًا، لكن قطعه الخفيفة المتبقية نشيطة وقطع الأسود غير متطورة. الدرس: القيمة الحقيقية للقطعة هي نشاطها، لا رقمها.',
    moves: 'e4 e5 f4 exf4 Bc4 Qh4+ Kf1 b5 Bxb5 Nf6 Nf3 Qh6 d3 Nh5 Nh4 Qg5 Nf5 c6 g4 Nf6 Rg1 cxb5 h4 Qg6 h5 Qg5 Qf3 Ng8 Bxf4 Qf6 Nc3 Bc5 Nd5 Qxb2 Bd6 Bxg1 e5 Qxa1+ Ke2 Na6 Nxg7+ Kd8 Qf6+ Nxf6 Be7#' },
  { id: 'century-1956', white: 'Donald Byrne', black: 'Robert James Fischer', event: 'New York 1956 (Game of the Century)', side: 'b', concept: 'king in the centre',
    intro: 'Fischer (13 سنة) يستغل تأخر الأبيض في التبييت. التضحية الشهيرة بالوزير (Be6!!) تعطيه هجومًا ومادة تفوق ما خسر. تلعب بالأسود.',
    moves: 'Nf3 Nf6 c4 g6 Nc3 Bg7 d4 O-O Bf4 d5 Qb3 dxc4 Qxc4 c6 e4 Nbd7 Rd1 Nb6 Qc5 Bg4 Bg5 Na4 Qa3 Nxc3 bxc3 Nxe4 Bxe7 Qb6 Bc4 Nxc3 Bc5 Rfe8+ Kf1 Be6 Bxb6 Bxc4+ Kg1 Ne2+ Kf1 Nxd4+ Kg1 Ne2+ Kf1 Nc3+ Kg1 axb6 Qb4 Ra4 Qxb6 Nxd1 h3 Rxa2 Kh2 Nxf2 Re1 Rxe1 Qd8+ Bf8 Nxe1 Bd5 Nf3 Ne4 Qb8 b5 h4 h5 Ne5 Kg7 Kg1 Bc5+ Kf1 Ng3+ Ke1 Bb4+ Kd1 Bb3+ Kc1 Ne2+ Kb1 Nc3+ Kc1 Rc2#' },
  { id: 'fischer-spassky-g6-1972', white: 'Robert James Fischer', black: 'Boris Spassky', event: 'World Championship 1972, game 6', side: 'w', concept: 'hanging pawns',
    intro: 'مباراة استراتيجية: الأسود يحصل على بيادق معلّقة في المركز (c5 وd5). Fischer يضغط عليها ثم يدفع f4-f5 ويفتح الطريق نحو الملك. الدرس: الخطة تأتي من بنية البيادق.',
    moves: 'c4 e6 Nf3 d5 d4 Nf6 Nc3 Be7 Bg5 O-O e3 h6 Bh4 b6 cxd5 Nxd5 Bxe7 Qxe7 Nxd5 exd5 Rc1 Be6 Qa4 c5 Qa3 Rc8 Bb5 a6 dxc5 bxc5 O-O Ra7 Be2 Nd7 Nd4 Qf8 Nxe6 fxe6 e4 d4 f4 Qe7 e5 Rb8 Bc4 Kh8 Qh3 Nf8 b3 a5 f5 exf5 Rxf5 Nh7 Rcf1 Qd8 Qg3 Re7 h4 Rbb7 e6 Rbc7 Qe5 Qe8 a4 Qd8 R1f2 Qe8 R2f3 Qd8 Bd3 Qe8 Qe4 Nf6 Rxf6 gxf6 Rxf6 Kg8 Bc4 Kh8 Qf4' },
  { id: 'legal-1750', white: 'Kermur de Legal', black: 'Saint Brie', event: 'Paris 1750 (Legal\'s mate)', side: 'w', concept: 'pins that are not real',
    intro: 'الأسود يظن أن الحصان على f3 مثبّت. لكن الوزير ليس قطعة يجب حمايتها بأي ثمن إذا كان هناك كش مات. الدرس: افحص دائمًا إن كان التثبيت حقيقيًا.',
    moves: 'e4 e5 Nf3 d6 Bc4 Bg4 Nc3 g6 Nxe5 Bxd1 Bxf7+ Ke7 Nd5#' },
];
const out = [];
for (const G of GAMES) {
  const g = new Chess(); const sans = G.moves.split(' '); const ucis = [];
  for (const [k, s] of sans.entries()) { const m = g.move(s); if (!m) { console.error('ILLEGAL', G.id, 'ply', k + 1, s, g.fen()); process.exit(1); } ucis.push(m.from + m.to + (m.promotion || '')); }
  out.push({ ...G, sans, ucis, final: g.fen(), mate: g.in_checkmate() });
  console.log('ok', G.id, sans.length, 'plies', g.in_checkmate() ? 'mate' : '');
}
fs.writeFileSync(path.join(root, 'data/masters.json'), JSON.stringify(out));
