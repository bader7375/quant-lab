// ------------------------------------------------ v12: Saudi helpers (mirror of the engine's isSaudi) and the Hijri month (Umm al-Qura calendar)
const SAUDI_NAMES_UI=/^(TASI|TASI_\w+|ARAMCO|ALRAJHI|RAJHI|AL_RAJHI|SABIC|STC|SNB|ALINMA|MAADEN|ACWA|ELM|DRSK|MOUWASAT|SULAIMAN|NOMU|MT30)$/i;
const saudiSym=sym=>/^\d{4}(_SR|_SE|_SA)?$/i.test(sym)||/(_SR|\.SR|_SE|_SA)$/i.test(sym)||SAUDI_NAMES_UI.test(sym);
function hijriMonth(iso){try{const p=new Intl.DateTimeFormat("en-u-ca-islamic-umalqura",{month:"numeric",timeZone:"UTC"}).formatToParts(new Date(iso+"T12:00:00Z"));return +p.find(x=>x.type==="month").value}catch(e){return NaN}}
function saudiNote(sym,date){if(!saudiSym(sym))return "";const s=SY(sym);const i=s?s.d.indexOf(date):-1;const out=[];
 out.push(s&&s.trendMode?"Saudi stock: <b>trend-breakout signals</b> (close at the 55-day high above the 200-day average; exit on a close below the highest close since entry − 3 ATR). 2013–2026: +2.5% net per trade (42% winners, average win +15%, average loss −6.6%); with the ML top-30% and market filter +3.5% (average loss −4.6%).":"Saudi stock on the general rules (Settings → Saudi signals → trend breakout is recommended).");
 if(s&&i>=0&&s.z250&&isF(s.z250[i])){const z=s.z250[i];
  out.push(`Long-term Z (250 days): <b>${z.toFixed(2)}</b> — ${z<=-2.5?"deep below its yearly mean: watch for a turn back above −2.5 (the deep-value watch)":z>=2.5?"far above its yearly mean: stretched, but in the 2013–2026 test skipping stretched breakouts did not help":z<=-1?"below its yearly mean":z>=1?"above its yearly mean":"near its yearly mean"}.`);
  if(s.zwatch&&s.zwatch[i])out.push("<b>Deep-value watch fired today:</b> the long-term Z turned back up through −2.5. Such turns (ML rank ≥ 50%) averaged +5.0% net, 68% winners, about 39 days, exit when Z reaches −1 or after 60 days. They cluster in market sell-offs, so as an automatic portfolio they lost; use small size (≤ 5%) and judgment.")}
 return out.join(" ")}
// ------------------------------------------------ v10: Bollinger helper, tomorrow planner, Claude analyst
function bbAt(c,i,n=20,k=2){if(i<n-1)return null;let m=0;for(let j=i-n+1;j<=i;j++)m+=c[j];m/=n;let v=0;for(let j=i-n+1;j<=i;j++)v+=(c[j]-m)**2;const sd=Math.sqrt(v/(n-1));
 return sd>0?{mid:m,up:m+k*sd,lo:m-k*sd,pb:(c[i]-(m-k*sd))/(2*k*sd),bw:4*sd/m}:null}
function rsiState(c,i,n=2){let up=NaN,dn=NaN;for(let t=1;t<=i;t++){const d=c[t]-c[t-1],u=Math.max(d,0),w=Math.max(-d,0);up=isF(up)?up+(u-up)/n:u;dn=isF(dn)?dn+(w-dn)/n:w}return {up,dn}}
// the close tomorrow that would turn RSI(2) into a setup: below it for reversal (RSI2 < trig), above it for momentum (RSI2 > momTrig)
function triggerClose(s,i){const {up,dn}=rsiState(s.c,i),c=s.c[i];if(!isF(up)||!isF(dn))return {rev:NaN,mom:NaN};
 const T=ECFG.trig,M=ECFG.momTrig;return {rev:c-Math.max(0,up*(100-T)/T-dn),mom:c+Math.max(0,dn*M/(100-M)-up)}}
const PRIOR_EDGE={aplus:.025,2:.012,1:.006,0:.003,mom:.003,short:0};   // research per-trade averages (v6-v9 studies) used as the starting estimate
function ownEdge(s,i,grade){let n=0,sum=0,win=0;
 for(let j=s.first;j<i;j++){if(grade==="mom"){if(!s.msetup[j]||!isF(s.mret[j])||j+s.mhold[j]>=i)continue;n++;sum+=s.mret[j];win+=s.mret[j]>0;continue}
  if(!s.setup[j]||!isF(s.tret[j])||j+s.thold[j]>=i)continue;const g=s.aplus&&s.aplus[j]?"aplus":thirdOf(s.score[j]);if(grade==="aplus"?g!=="aplus":(g==="aplus"?2:g)!==grade)continue;n++;sum+=s.tret[j];win+=s.tret[j]>0}
 const avg=n?sum/n:NaN,K=30,est=(n*(n?avg:0)+K*PRIOR_EDGE[grade])/(n+K);return {n,avg,win:n?win/n:NaN,est}}
// ---------- v11 short side
const SHORT_EVIDENCE="Evidence: short rules broke even or lost on the development data (6 long histories, 87 stocks) and paid only in bear markets: 2007–2012 stocks +1.1% per short, the 2020 crash +3.8% (18 shorts, market filter on); China lost. Use shorts when the market itself is falling, keep the stop, half size.";
function ownShort(s,i){let n=0,sum=0,win=0;if(!s.stret)return {n:0,avg:NaN,win:NaN,est:0};for(let j=s.first;j<i;j++){if(!s.sgood[j]||!isF(s.stret[j])||j+s.sthold[j]>=i)continue;n++;sum+=s.stret[j];win+=s.stret[j]>0}
 const avg=n?sum/n:NaN,K=30;return {n,avg,win:n?win/n:NaN,est:(n*(n?avg:0)+K*PRIOR_EDGE.short)/(n+K)}}
function shortSay(s,c,plan){const e=ownShort(s,c),mk=s.mdown?" and the market is below its 200-day average":"",sz=ECFG.shortSize<1?"half":"full";
 return `RSI(2) is <b>${fmt(s.rsi2[c],0)}</b>: an overbought bounce inside a downtrend (close below its 200-day average ${fp(s.sma200[c])}${mk}). Short score <b>${fmt(s.sscore[c],1)}</b> (${THIRD_NAME[thirdOf(s.sscore[c])]}).`
  +` Plan: place a <b>limit sell short at ${fp(plan.entry)}</b> (close + ${ECFG.limitATR} ATR), good for tomorrow only; cover on ${EXIT_TEXT.prevlow} (now ${fp(plan.exitLevel)}) or after ${ECFG.maxHold} days; <b>stop ${fp(plan.stop)}</b> (3 ATR); ${sz} size.`
  +(e.n>=8?` On this stock, past short setups averaged <b class="${cl(e.avg)}">${spct(e.avg,2)}</b> (${e.n} shorts, ${pct(e.win,0)} won).`:"")
  +(s.mdown?"":` <span class="acc">No market file is set, so the market-downtrend filter is off: choose one (e.g. SPY or TASI) in Settings.</span>`)
  +(ECFG.shorts==="watch"?` <span class="note">(Shown only: Settings → short trades → trade them, to include shorts in the backtest and plan.)</span>`:"")
  +` <span class="acc">${SHORT_EVIDENCE}</span>`}
function planFor(sym){const s=SY(sym);if(!s)return null;const i=s.d.length-1;if(i<s.first)return {sym,s,i,kind:"warm",rank:9};
 const c=s.c[i],atr=s.atr[i],mom=s.mode[i]===-1,P=s.pulse,bb=bbAt(s.c,i),tc=triggerClose(s,i),warn=[],good=[];
 const st0=P?P.state[i]:0,isIndex=/^(TASI|SPY|QQQ|DIA|IWM|\^)/i.test(sym);
 if(mom&&!isIndex&&!saudiSym(sym))warn.push("momentum mode on what may be a single stock: momentum trades lost money on fresh US stocks; consider reversal only");
 if(!mom&&st0===1)warn.push("strong up-trend on a reverting stock: the next 10 days averaged −0.31% vs normal in tests (don't chase)");
 if(!mom&&st0===-1)good.push("strong down-momentum: capitulation, reversal setups did better here in tests");
 if(bb&&bb.pb<0)good.push("closed below the lower Bollinger Band (top-third setups below the band averaged +1.54% vs +0.93% after 2013)");
 {const newest=RES.syms.map(q=>{const z=SY(q);return z?z.d[z.d.length-1]:""}).sort().pop(),gap=(Date.parse(newest)-Date.parse(s.d[i]))/864e5;if(gap>4)warn.push(`data ends ${s.d[i]}, ${Math.round(gap)} days before your newest file: update this file before trading it`)}
 if(saudiSym(sym)&&s.z250&&isF(s.z250[i]))good.push(`long-term Z ${s.z250[i].toFixed(2)}`);
 if(false&&saudiSym(sym)&&i>0){const r1=s.c[i]/s.c[i-1]-1;if(r1>=.095)warn.push("closed at the +10% limit: next morning usually opens higher then fades; holders consider selling into the open, don't buy the open");
  if(r1<=-.095)warn.push("closed at the -10% limit: next morning usually opens 2-4% lower");
}
 let o={sym,s,i,c,atr,mom,bb,tc,warn,good,st0};
 const gate=saudiSym(sym)&&!isIndex&&(ECFG.mlf||"on")!=="off"?mlGate(sym):null;
 if(gate&&!gate.ok&&(s.sig[i]===1||s.sig[i]===2)){Object.assign(o,{kind:"weak",rank:4,action:`skip: ML filter (${gate.why})`,edge:null});
  warn.push(s.sig[i]===2?`${s.trendMode?"trend":"momentum"} signal filtered out: ${gate.why}. Trend breakouts that pass the ML top-30% and market filter averaged +3.5% net (average loss −4.6%) vs +2.5% unfiltered (average loss −6.6%); in a portfolio the filter cut the worst drawdown from −37% to −8%`:`reversal signal filtered out: Saudi dip-buys lost −0.67% net per trade in 2013–2026 (−0.36% even in the ML top 30%)`);return o}
 if(gate&&gate.ok&&s.sig[i]===2)good.push(`passes the ML filter: rank ${Math.round(100*gate.pct)}th percentile${gate.mkt?", market model positive":""} (filtered trend breakouts averaged +3.5% net per trade in 2013–2026, +2.0% in 2013–19 and +4.0% in 2020–26)`);
 if(s.sig[i]===1){const ap=!!(s.aplus&&s.aplus[i]),grade=ap?"aplus":thirdOf(s.score[i]),e=ownEdge(s,i,grade);
  Object.assign(o,{kind:"rev",rank:ap?0:1,action:(ap?"A+ ":"")+(ECFG.entry==="limit"?"limit buy":"buy at open"),entry:ECFG.entry==="limit"?c-ECFG.limitATR*atr:c,
   exitTxt:EXIT_SHORT[ECFG.exit]+(ECFG.exit==="prevhigh"?` (today's high ${fp(s.h[i])})`:""),maxHold:ECFG.maxHold,grade,edge:e,P:s.P[i]});
  if(e.n>=10&&e.avg<0)warn.push(`this stock's own past ${ap?"A+":THIRD_NAME[grade]} setups lost on average (${spct(e.avg,2)}, ${e.n} trades)`);
  if(e.n<10)warn.push(`few own past setups (${e.n}): the estimate leans on research averages`)}
 else if(s.sig[i]===2){const e=ownEdge(s,i,"mom"),tm=!!s.trendMode;Object.assign(o,{kind:"mom",rank:2,action:tm?"trend buy at open":"momentum buy at open",entry:c,exitTxt:tm?`trailing stop: close below highest close − 3 ATR (starts at ${fp(c-3*atr)})`:"close below the 5-day average",maxHold:tm?null:ECFG.momMaxHold,grade:"mom",edge:e,P:NaN});
  if(e.n>=8&&e.avg<0)warn.push(`past momentum trades here lost (${spct(e.avg,2)}, ${e.n} trades)`)}
 else if(s.sgood&&s.sgood[i]&&ECFG.shorts!=="off"&&!mom){const e=ownShort(s,i),entry=c+ECFG.limitATR*atr;
  Object.assign(o,{kind:ECFG.shorts==="trade"?"short":"shortwatch",rank:ECFG.shorts==="trade"?2.5:3.2,action:ECFG.shorts==="trade"?"limit sell short":"short setup (watch only)",entry,exitTxt:`cover below today's low ${fp(s.l[i])}, stop ${fp(entry+3*atr)}`,maxHold:ECFG.maxHold,grade:"short",edge:e,P:s.sP[i]});
  warn.push("short: research shows shorts only paid in bear markets; half size, keep the stop");if(!s.mdown)warn.push("no market file set: the market-downtrend filter is off")}
 else if(saudiSym(sym)&&!isIndex&&MLPF&&MLPF.rel10&&isF(MLPF.rel10[sym])&&MLPF.rel10[sym]<=-.07&&(MLPF.ranks||{})[sym]>=.5){const rv=MLPF.rel10[sym],on=MLPF.pm>0;
  Object.assign(o,{kind:on?"rev":"weak",rank:on?1.5:4,action:on?"industry-dip buy (half size)":"skip: industry dip, but market model negative",entry:on?c:null,exitTxt:on?"sell at the open 10 trading days later":null,maxHold:on?10:null,edge:null});
  good.push(`${(100*rv).toFixed(1)}% behind its industry over 10 days (as of ${MLPF.rel10_date}), ML rank ${Math.round(100*MLPF.ranks[sym])}%: such dips averaged +2.1% net in 10 days (2013–19 +2.0%, 2020–26 +2.2%) when the market model was positive`);
  warn.push("separate reversal sleeve: half size (5% of the account), at most 10 at once; it did not improve the Core Strategy when combined, so keep it small")}
 else if(s.zwatch&&s.zwatch[i]&&saudiSym(sym)){const pct=MLPF&&MLPF.ranks?MLPF.ranks[sym]:NaN;Object.assign(o,{kind:"zwatch",rank:2.8,action:"deep-value watch (small size)",entry:c,exitTxt:"sell when the 250-day Z reaches −1, or after 60 days",maxHold:60,edge:null});
  good.push(`long-term Z turned up through −2.5 (now ${s.z250[i].toFixed(2)}): such turns averaged +5.0% net, 68% winners, about 39 days`);
  if(!(pct>=.5))warn.push(isF(pct)?`ML rank ${Math.round(100*pct)}th percentile: below 50%, where these turns did worse (+3.5% vs +5.0%)`:"no ML rank for this stock");
  warn.push("not an automatic trade: in a portfolio these signals clustered in sell-offs and lost; keep it to 5% or less")}
 else if(s.setup[i]){Object.assign(o,{kind:"weak",rank:4,action:"skip: setup below your score filter",edge:null})}
 else if(s.trendMode){let hi=-Infinity;for(let k=Math.max(0,i-53);k<=i;k++)hi=Math.max(hi,s.c[k]);const s2=s.sma200&&s.sma200[i],trig=Math.max(hi,isF(s2)?s2:0),dist=atr>0?Math.abs(trig-c)/atr:NaN;
  Object.assign(o,{kind:"watch",rank:3,trig,dist,action:`watch: trend breakout if it closes at or above ${fp(trig)}${isF(s2)&&c<s2?" (also needs to be above the 200-day average)":""}`,edge:null})}
 else{const trig=mom?tc.mom:tc.rev,dist=isF(trig)&&atr>0?Math.abs(trig-c)/atr:NaN;
  Object.assign(o,{kind:"watch",rank:3,trig,dist,action:mom?`watch: momentum setup if it closes above ${fp(trig)}`:`watch: setup if it closes below ${fp(trig)}`,edge:null})}
 return o}
function tomorrowPlan(){if(!RES)return [];const rows=RES.syms.map(planFor).filter(Boolean);
 rows.sort((a,b)=>(a.rank-b.rank)||((b.edge?b.edge.est:-1)-(a.edge?a.edge.est:-1))||((a.dist??99)-(b.dist??99)));return rows}
function drawPlan(){const el=$("plan-t");if(!el)return;if(!RES){el.innerHTML='<tr><td class="empty">Upload stocks in the Data tab (or with the button above) and the plan appears here.</td></tr>';return}
 const rows=tomorrowPlan(),act=rows.filter(r=>r.kind==="rev"||r.kind==="mom"||r.kind==="short");
 $("plan-note").innerHTML=`<b>${act.length}</b> trade(s) to place for the next session across ${rows.length} symbol(s)${act.length?`; best estimated edge: <b>${esc(act[0].sym)}</b>`:""}. Estimated edge = this stock's own past average for the same grade, shrunk toward the research average (30-trade weight). Watch rows show the close that would create a setup.`;
 el.innerHTML="<tr>"+["#","symbol","last close","action","entry","exit","est. edge / trade","own record","chance of profit","pulse","notes"].map(h=>`<th>${h}</th>`).join("")+"</tr>"+rows.map((r,k)=>{
  if(r.kind==="warm")return `<tr data-s="${esc(r.sym)}"><td>${k+1}</td><td>${esc(r.sym)}</td><td colspan="9" class="note">warming up: needs more history</td></tr>`;
  const e=r.edge,cls=r.kind==="rev"?(r.grade==="aplus"?"vp long aplus-b":"vp long"):r.kind==="mom"?"vp long":r.kind==="short"||r.kind==="shortwatch"?"vp short":"note";
  return `<tr data-s="${esc(r.sym)}"><td>${k+1}</td><td><b>${esc(nameOf(r.sym))}</b></td><td>${fp(r.c)}</td><td><span class="${cls}" style="padding:1px 6px${r.kind==="mom"?";color:#c08cff":""}">${esc(r.action)}</span></td>
   <td>${r.entry!=null?fp(r.entry):"—"}</td><td style="text-align:left">${r.exitTxt?esc(r.exitTxt)+(r.maxHold?`, max ${r.maxHold} days`:""):"—"}</td>
   <td class="${e?cl(e.est):""}">${e?spct(e.est,2):r.kind==="watch"&&isF(r.dist)?`${r.dist.toFixed(1)} ATR away`:"—"}</td><td>${e&&e.n?`${spct(e.avg,2)} · ${e.n} tr · ${pct(e.win,0)} won`:"—"}</td>
   <td>${isF(r.P)?pct(r.P,0):"—"}</td><td>${r.s.pulse?PULSE_STATE[r.st0].toLowerCase():"—"}</td>
   <td style="text-align:left;max-width:420px">${r.good.map(x=>`<div class="up">▲ ${esc(x)}</div>`).join("")}${r.warn.map(x=>`<div class="down">▼ ${esc(x)}</div>`).join("")}</td></tr>`}).join("")}

// ---------- data handed to Claude
function rsum(a){return a.map(v=>isF(v)?+v.toFixed(4):null)}
function snapshotFor(sym,iIn){const s=SY(sym);if(!s)return null;const i=iIn==null?s.d.length-1:iIn,c=s.c,P=s.pulse,bb=bbAt(c,i),r=k=>i>=k?c[i]/c[i-k]-1:NaN;
 const pl=planFor(sym)||{},ev=P?pulseEvidence(s,i).filter(e=>e.cnt>=30).map(e=>({state:e.n,days:e.cnt,next10d_vs_normal:+(100*e.ex).toFixed(2)+"%"})):[];
 const stp=lastStep(s,i),tr=RES.bt.trades.filter(t=>t.symbol===sym),win=tr.filter(t=>t.pnl>0).length;
 const third=stp?stp.thirds.map((t,k)=>({third:THIRD_NAME[k],trades:t.n,avg:isF(t.avg)?+(100*t.avg).toFixed(2)+"%":null,won:isF(t.win)?Math.round(100*t.win)+"%":null})):[];
 return {symbol:sym,date:s.d[i],close:+c[i].toFixed(4),returns:{d1:+(100*r(1)).toFixed(2),d5:+(100*r(5)).toFixed(2),d20:+(100*r(20)).toFixed(2)},
  atr_pct:+(100*s.atr[i]/c[i]).toFixed(2),rsi2:+s.rsi2[i].toFixed(1),rsi14:+s.rsi14[i].toFixed(1),close_in_range_ibs:+s.ibs[i].toFixed(2),streak:s.streak[i],z20:+s.z20[i].toFixed(2),
  zone:s.zone[i]>=0?["<2.5%","2.5–10%","10–25%","25–75%","75–90%","90–97.5%",">97.5%"][s.zone[i]]:null,volume_vs_normal_sigma:isF(s.volz[i])?+s.volz[i].toFixed(2):null,
  bollinger:bb?{upper:+bb.up.toFixed(4),middle:+bb.mid.toFixed(4),lower:+bb.lo.toFixed(4),pct_b:+bb.pb.toFixed(2),bandwidth_pct:+(100*bb.bw).toFixed(1)}:null,
  character:{autocorr_500d:isF(s.ac[i])?+s.ac[i].toFixed(3):null,mode:s.mode[i]===-1?"momentum":"reversal",switch_above:ECFG.acThr},
  setup:{reversal_setup:!!s.setup[i],momentum_setup:!!s.msetup[i],system_signal:s.sig[i]===1?"reversal buy":s.sig[i]===2?"momentum buy":"none",edge_score:isF(s.score[i])?+s.score[i].toFixed(2):null,score_third:THIRD_NAME[thirdOf(s.score[i])]||null,chance_of_profit:isF(s.P[i])?Math.round(100*s.P[i])+"%":null,aplus:!!(s.aplus&&s.aplus[i])},
  plan:{action:pl.action||null,entry:isF(pl.entry)?+pl.entry.toFixed(4):null,exit:pl.exitTxt||null,max_hold_days:pl.maxHold||null,trigger_close_for_reversal_setup:isF(pl.tc&&pl.tc.rev)?+pl.tc.rev.toFixed(4):null,trigger_close_for_momentum_setup:isF(pl.tc&&pl.tc.mom)?+pl.tc.mom.toFixed(4):null,estimated_edge_per_trade:pl.edge?+(100*pl.edge.est).toFixed(2)+"%":null,warnings:pl.warn,positives:pl.good},
  market_notes:saudiSym(sym)?{market:"Saudi (Tadawul)",mode_used:ECFG.saudi==="mom"?"momentum (Saudi setting)":"same as other stocks",hijri_month:hijriMonth(s.d[i]),ramadan:hijriMonth(s.d[i])===9,daily_price_limit:"±10%"}:{market:"other"},
  short_side:s.sgood?{enabled:ECFG.shorts,short_setup_now:!!s.sgood[i],below_200d_avg:isF(s.sma200[i])?c[i]<s.sma200[i]:null,market_below_200d:s.mdown?!!s.mdown[i]:"no market file",short_score:isF(s.sscore[i])?+s.sscore[i].toFixed(2):null,short_chance_of_profit:isF(s.sP[i])?Math.round(100*s.sP[i])+"%":null,own_short_record:(()=>{const e=ownShort(s,i);return {shorts:e.n,avg:isF(e.avg)?+(100*e.avg).toFixed(2)+"%":null}})()}:{enabled:"off"},
  pulse:P?{value_sigma:+P.M[i].toFixed(2),horizons_5_10_20_60:P.mh.map(a=>isF(a[i])?+a[i].toFixed(2):null),agreeing:P.align[i],path_efficiency:isF(P.er[i])?+P.er[i].toFixed(2):null,rank_2y:isF(P.pct[i])?+P.pct[i].toFixed(2):null,accelerating:P.acc[i]>0,state:PULSE_STATE[P.state[i]],divergence_last_10_bars:recentDiv(P,i),evidence_on_this_stock:ev}:null,
  top_signs:topSigns(s,i,4).map(([k,v])=>chipName(k,v)),
  volatility:{yz5:+s.yz5[i].toFixed(1),yz20:+s.yz20[i].toFixed(1),yz60:+s.yz60[i].toFixed(1),garch_next_day:+s.garch[i].toFixed(1),vol_rank_2y:isF(s.vrank[i])?+s.vrank[i].toFixed(2):null},
  fear_vix:isF(s.vix[i])?{vix:+s.vix[i].toFixed(1),rank:+s.frank[i].toFixed(2)}:null,
  own_setup_record_by_score_third:third,momentum_record:(()=>{const m=momStats(s,i);return {trades:m.n,avg:isF(m.avg)?+(100*m.avg).toFixed(2)+"%":null}})(),
  system_backtest_on_this_symbol:{trades:tr.length,won:tr.length?Math.round(100*win/tr.length)+"%":null,last5:tr.slice(-5).map(t=>({in:t.entry_date,out:t.exit_date,ret:+(100*(t.exit_price/t.entry_price-1)).toFixed(2)+"%",why:t.exit_reason}))},
  last_15_bars:s.d.slice(Math.max(0,i-14),i+1).map((d,k)=>{const j=Math.max(0,i-14)+k;return [d,+s.o[j].toFixed(4),+s.h[j].toFixed(4),+s.l[j].toFixed(4),+c[j].toFixed(4)]})}}
const researchFacts=()=>`SYSTEM (Reversal Edge v10, daily bars, long only):
- Reversal setup: RSI(2) < ${ECFG.trig}. Trade only top-third Reversal Edge Score (9 signs, fixed research weights). Entry: limit order ${ECFG.limitATR} ATR under the signal close, valid next session only. Exit: first close above the previous day's high, or after ${ECFG.maxHold} days. No price stop (stops cut the edge in every test).
- A+ grade: top-third setup + close in the bottom 13% of the day's range + Momentum Pulse below -0.5. A+ trades earned about twice the other top-third trades per trade on all six long histories.
- Market character: 500-day lag-1 autocorrelation above ${ECFG.acThr} -> momentum mode (buy RSI(2) > ${ECFG.momTrig} at the open, exit on a close below the 5-day average).
EVIDENCE (out of sample; 93 development series + 432 never-seen stocks):
- The reversal edge is real vs random entries in every period on US stocks (+2.6% per trade 1990-2007, +0.7% 2008-12, +0.8% 2013-17, +0.5% 2018-21, +1.9% 2022-26) but has shrunk since 2008. No edge on China A-shares 2018-21.
- Reversal setups during a strong down-trend in the Pulse did BETTER (+1.70% vs +1.09% per trade): strong down-momentum is capitulation, not a reason to avoid buying the dip.
- Strong UP-trend on a stock that reverts: next 10 days were -0.31% vs normal (t -2.4, below average on 75% of 87 stocks): do not chase strength.
- Momentum-mode trades lost money on individual US stocks (-1.6% per trade on 47 fresh stocks); momentum mode helped index-like markets (TASI). "Reversal only" beat "auto" on all three fresh stock sets.
- Exhaustion, thrusts and divergences: no reliable edge (|t| < 1). Context only.
- A close below the lower Bollinger Band inside top-third setups: +1.54% vs +0.93% per trade (2013+), +2.13% vs +1.48% before 2013. Overlaps with depth of the drop; context, not a rule.
- 200-day average filter, VIX change, longer trends: no consistent effect. Exit at next open, 2-day limit orders, stops: rejected.
- Position size "others half" (A+ full size, others half) lowered drawdowns on every data set with the same or better Sharpe; "A+ double" raised return with deeper drawdowns.
- SHORTS (v11, optional): sell an overbought bounce (RSI(2) > 90, top-third short score) only below the 200-day average (and market below its 200-day average if a market file is set); limit 0.5 ATR above the close; cover on the first close below the previous day's low or after the max hold; 3-ATR stop; half size. Short rules broke even or lost on development data (87 stocks, 6 long histories) and paid only in bear markets (2007-12: +1.1% per short; 2020 crash: +3.8% on 18 shorts); China lost. Plain mirrored shorts blew up a test account through a squeeze. Index hedging lowered Sharpe everywhere. Recommend shorts only when the market itself is in a downtrend.
- SAUDI REVERSAL (v14): plain dip-buys lose on Saudi stocks (RSI(2)<10: -0.66% net per trade; also in uptrends, ML-top stocks, 3-day selloffs, 20-day lows, capitulation days). The one reversal that works in both periods is the INDUSTRY-RELATIVE DIP: the stock fell 7%+ more than its industry (code group median) over 10 days, ML rank >= 50%, market model positive, buy next open, hold 10 days: +2.1% net per trade (58% win; 2013-19 +2.0%, 2020-26 +2.2%); as a 10 x 5% sleeve Sharpe 1.06, max DD -15%. All 36 tested variants were positive in 2020-26. Adding it to the Core Strategy lowered the Core's Sharpe (1.55 -> 1.36), so it is an optional half-size sleeve.
- SAUDI SIGNALS (v14): trend breakout replaces RSI momentum for Saudi stocks: close at the 55-day high above the 200-day average, buy next open, exit on a close below (highest close since entry - 3 ATR). 2013-2026, 257 stocks: +2.54% net per trade (win 42%, avg win +15.3%, avg loss -6.6%; 2013-19 +1.7%, 2020-26 +3.3%); with ML top 30% + market model positive +3.50% (avg loss -4.6%). Old RSI momentum: +0.08%. LONG-TERM Z (250-day log-price z-score): buying Z <= -2.5 (ML >= 50%) and selling at Z >= -1 averaged +6.6% net per trade (69% win) but as a 10-slot portfolio it returned +1.4%/yr with -32% drawdown because signals cluster in sell-offs; confirmed turns (Z back above -2.5) +5.0% per trade, same portfolio problem. Skipping breakouts with Z > 2-3 did not help. So Z is context and a small-size watch, not an automatic trade. 60-day Z reversion lost money. Opening-auction and short-selling features were removed (intraday / no edge outside bear markets).
- SAUDI ML PORTFOLIO (v14, walk-forward 2013-2026, 270 stocks): LightGBM ranker on 46 stock features predicting 20-day relative return; rank IC positive in all 14 test years (avg ~+0.09). Monthly top-10 liquid stocks, invested only when a market-feature model forecasts a positive 20-day market return: +14.8%/yr, Sharpe 0.91, max DD -17% (market ~+4%/yr, -57%). Learned profile: low volatility, near 52-week high, positive 12-month momentum, above 200-day average, short pause in the last 5 days. Today's picks are in the page's ML panel (collection ml/latest).
- SAUDI 2026 EDGE STUDY (pre-registered, fresh data 2020-03-06..2026-10-05, 270 Yahoo stocks, 0.40% round-trip cost): (1) PASSED: opening-auction gap-down rule - buy stocks that open <= -3% below the previous close (and above -10.5%, top two-thirds by traded value, max 5 deepest gaps) and sell at the close: CAGR +55%, Sharpe 1.72, max drawdown -24%, every year positive (2004-2020 discovery: Sharpe 1.66). Gross per trade +0.6% (-3..-5% gaps), +1.3% (-5..-7%), +2.8% (beyond -7%). BUT the pre-registered fill check FAILED: buying at ~11:00 instead earned -0.05%; 5-minute bars show the rebound is gone by 10:05. Only orders filled in the opening auction capture it; capacity is small (first 5 minutes trade about SAR 1.2m in these stocks). Break-even cost about 1% round trip. Mirror: opens >= +3% fell -1.0% by the close (holders: sell in the auction). (2) FAILED on fresh data: the terminal's Saudi momentum mode (momentum beat reversal on only 54% of 251 stocks, Sharpe 0.04 vs 0.04, buy & hold 0.13), illiquidity premium, pre-holiday effect. (3) Rejected before testing (no edge with tradable timing): weekly/monthly/12-month momentum, low volatility, MAX, 52-week high, volume surge, industry momentum, salary days, IPO drift, overnight US/oil/EM moves (fully priced in the Saudi open), overnight holding after strong days (only limit-locked closes continue, and those cannot be bought).
- SAUDI MARKET (v13 study of 193 Tadawul stocks 2002-2020 plus Al Rajhi, Aramco and TASI to 2026): 89-94% of Saudi stocks trend day to day (median lag-1 autocorrelation +0.08 to +0.09, strongest in the most liquid). Momentum mode (buy after RSI(2) > 90 at the next open, sell on a close below the 5-day average) beat dip-buying on 75% of 191 stocks (mean Sharpe 0.31 vs -0.04; buy & hold 0.22) and in every sector; its entries beat random days by +0.42% (2002-07), +0.20% (2008-13), +0.17% (2014-20) per trade. Not adopted after testing: momentum only in a TASI uptrend, skipping >2x-volume signals, selling at the next open after a limit-up close, adding pullback-turn entries. Limit-up closes: next morning opens +2.6% to +3.4% higher, then fades -0.5% to -1.3% (do not buy that open; holders can sell into it). Limit-down closes: next morning opens 2.3-3.8% lower. Gap-down opens (< -2%) rebounded about +1% open-to-close (t 12-18, all liquidity groups, both periods; not verified with live fills). Last week's winners beat last week's losers by +0.30% the next week; longer-horizon cross-sectional momentum: none. TASI up > 1% today: average stock +0.28% tomorrow; big caps lead small caps. Day before a long holiday +0.51% (t 3.3, n 39). Ramadan: no reliable effect for the average stock. Daily price limit ±10%; retail short selling restricted.
- Costs matter: 87-stock Sharpe 1.23 at 5bp per side, 0.59 at 20bp.
- Realistic diversified portfolio Sharpe on fresh data: about 0.45-0.7.`;
const ANALYST_RULES=`You are the trading analyst built into the Reversal Edge terminal. You see only the data below (computed by the system from the user's own price files) plus the research summary. You cannot browse the web or see news.
Rules: base every claim on the numbers given or on tool results; quote the numbers. Prefer the evidence on THIS stock when it has enough trades (30+ days for states, 10+ trades for setups), otherwise lean on the research. Say clearly when the evidence is weak. Never invent prices, news or fundamentals. This is decision support, not financial advice; say so in one short line at the end.
Write plain text with short headings (lines starting with ##) and "- " bullets, no tables, under 350 words unless asked for more.`;

// ---------- tools Claude may call to do research on the user's data
function studyCondition(a){const sym=String(a.symbol||st.sym||""),s=SY(sym);if(!s)throw new Error("unknown symbol "+sym+"; loaded: "+RES.syms.join(", "));
 const H=Math.max(1,Math.min(20,Math.round(+a.horizon_days||10))),n=s.d.length,P=s.pulse,cond=a.conditions||{},names={trend_up:1,trend_down:-1,range:0,no_trend:0,exhaustion_up:2,exhaustion_down:-2};
 const ok=j=>{const c=cond;if(c.rsi2_below!=null&&!(s.rsi2[j]<+c.rsi2_below))return false;if(c.rsi2_above!=null&&!(s.rsi2[j]>+c.rsi2_above))return false;
  if(c.pulse_state!=null&&P&&P.state[j]!==names[String(c.pulse_state)])return false;if(c.pulse_below!=null&&!(P&&P.M[j]<+c.pulse_below))return false;if(c.pulse_above!=null&&!(P&&P.M[j]>+c.pulse_above))return false;
  if(c.ibs_below!=null&&!(s.ibs[j]<+c.ibs_below))return false;if(c.ibs_above!=null&&!(s.ibs[j]>+c.ibs_above))return false;
  if(c.z20_below!=null&&!(s.z20[j]<+c.z20_below))return false;if(c.z20_above!=null&&!(s.z20[j]>+c.z20_above))return false;
  if(c.below_lower_bollinger||c.above_upper_bollinger){const b=bbAt(s.c,j);if(!b)return false;if(c.below_lower_bollinger&&!(b.pb<0))return false;if(c.above_upper_bollinger&&!(b.pb>1))return false}
  if(c.one_day_drop_atr_below!=null&&!(s.ret1[j]<+c.one_day_drop_atr_below))return false;if(c.volume_sigma_above!=null&&!(s.volz[j]>+c.volume_sigma_above))return false;
  if(c.reversal_setup_only&&!s.setup[j])return false;if(c.aplus_only&&!(s.aplus&&s.aplus[j]))return false;if(c.score_third&&THIRD_NAME[thirdOf(s.score[j])]!==String(c.score_third))return false;
  if(c.mode&&(s.mode[j]===-1?"momentum":"reversal")!==String(c.mode))return false;if(c.from_date&&s.d[j]<String(c.from_date))return false;return true};
 let N=0,sum=0,w=0,bs=0,bn=0,ss=0;const dates=[],trades=[];
 for(let j=Math.max(1,s.first-260);j+H<n;j++){const f=Math.log(s.c[j+H]/s.c[j]);bs+=f;bn++;if(!ok(j))continue;N++;sum+=f;ss+=f*f;w+=f>0;dates.push(s.d[j]);if(s.setup[j]&&isF(s.tret[j]))trades.push(s.tret[j])}
 const avg=N?sum/N:NaN,base=bn?bs/bn:NaN,sd=N>1?Math.sqrt(ss/N-avg*avg):NaN,t=N>1&&sd>0?(avg-base)/sd*Math.sqrt(N/Math.max(1,H)):NaN;
 return {symbol:sym,horizon_days:H,matches:N,avg_forward_return:N?+(100*avg).toFixed(2)+"%":null,all_days_avg:+(100*base).toFixed(2)+"%",excess:N?+(100*(avg-base)).toFixed(2)+"%":null,
  t_stat_overlap_adjusted:isF(t)?+t.toFixed(2):null,win_rate:N?Math.round(100*w/N)+"%":null,system_trades_among_matches:{n:trades.length,avg:trades.length?+(100*trades.reduce((x,y)=>x+y,0)/trades.length).toFixed(2)+"%":null,won:trades.length?Math.round(100*trades.filter(x=>x>0).length/trades.length)+"%":null},
  last_matches:dates.slice(-6),note:"hindsight study over this symbol's own history; each match is a day whose next "+H+" days are known"}}
const TOOLS=[
 {name:"study_condition",description:"Research on the user's own price history: for one symbol, find every past day matching the conditions and return the average forward return over horizon_days vs all days (excess, overlap-adjusted t-stat, win rate) plus the system's reversal-trade results among those days. Use it to test ideas like 'does buying below the lower Bollinger Band work on this stock' before advising.",
  inputSchema:{type:"object",properties:{symbol:{type:"string"},horizon_days:{type:"integer",minimum:1,maximum:20},conditions:{type:"object",description:"Any of: rsi2_below, rsi2_above, pulse_state (trend_up|trend_down|no_trend|exhaustion_up|exhaustion_down), pulse_below, pulse_above, ibs_below, ibs_above, z20_below, z20_above, below_lower_bollinger (bool), above_upper_bollinger (bool), one_day_drop_atr_below, volume_sigma_above, reversal_setup_only (bool), aplus_only (bool), score_third (bottom third|middle third|top third), mode (reversal|momentum), from_date (YYYY-MM-DD)"}},required:["symbol","conditions"]},
  execute:a=>{aiStatus(`researching ${a.symbol||""}…`);return studyCondition(a)}},
 {name:"get_snapshot",description:"The full current snapshot (indicators, setup, pulse, Bollinger, plan, own record) of another loaded symbol, to compare.",inputSchema:{type:"object",properties:{symbol:{type:"string"}},required:["symbol"]},
  execute:a=>{const x=snapshotFor(String(a.symbol));if(!x)throw new Error("not loaded; loaded symbols: "+RES.syms.join(", "));delete x.last_15_bars;return x}},
 {name:"get_bars",description:"Recent daily bars [date, open, high, low, close, volume] for a loaded symbol (at most 60).",inputSchema:{type:"object",properties:{symbol:{type:"string"},n:{type:"integer",maximum:60}},required:["symbol"]},
  execute:a=>{const s=SY(String(a.symbol));if(!s)throw new Error("not loaded");const n=Math.max(1,Math.min(60,+a.n||30)),i=s.d.length;return s.d.slice(i-n).map((d,k)=>{const j=i-n+k;return [d,s.o[j],s.h[j],s.l[j],s.c[j],s.v[j]]})}}];

// ---------- UI
let SAMPLE=null,TOOLS_OK=false,aiCtl=null,aiTurns=[],aiCtxSym=null;
(async()=>{try{if(!window.claude||!claude.use)return;SAMPLE=await claude.use("sample");if(!SAMPLE)return;const lim=await SAMPLE.limits().catch(()=>null);TOOLS_OK=!!(lim&&lim.tools);
 document.querySelectorAll(".ai-only").forEach(e=>e.hidden=false);document.querySelectorAll(".ai-off").forEach(e=>e.hidden=true)}catch(e){}})();
function md(t){const lines=esc(t).split("\n");let h="",inUl=false;const inl=x=>x.replace(/\*\*(.+?)\*\*/g,"<b>$1</b>").replace(/`([^`]+)`/g,"<code>$1</code>");
 for(const ln of lines){const m=ln.match(/^\s*[-*]\s+(.*)/);if(m){if(!inUl){h+="<ul>";inUl=true}h+=`<li>${inl(m[1])}</li>`;continue}if(inUl){h+="</ul>";inUl=false}
  const hd=ln.match(/^#{1,4}\s+(.*)/);if(hd){h+=`<h4>${inl(hd[1])}</h4>`;continue}if(ln.trim())h+=`<p>${inl(ln)}</p>`}
 if(inUl)h+="</ul>";return h}
function aiStatus(t){const e=$("ai-status");if(e)e.textContent=t||""}
const AI_ERR={not_granted:"Claude access was not allowed for this page.",sampling_disabled:"Claude is not available for this account.",rate_limited:"Too many requests or your usage limit was reached. Try again later.",
 session_expired:"Please sign in to Claude again.",prompt_too_large:"Too much data for one request.",refused:"Claude declined this request.",empty_completion:"Claude returned nothing; try again.",upstream_error:"Connection problem; try again."};
async function askClaude(outId,input,{tools=false,onDone}={}){if(!SAMPLE)return;aiCtl&&aiCtl.abort();const ctl=aiCtl=new AbortController(),out=$(outId);
 out.innerHTML='<p class="note">Thinking… (Claude reads the system data and may run research on your files; this can take up to a minute)</p>';aiStatus("thinking…");$("ai-stop").hidden=false;$("plan-stop").hidden=false;
 const opts={signal:ctl.signal,modelTier:($("ai-tier")||{}).value||"complex",onText:({text})=>{out.innerHTML=md(text);aiStatus("writing…")}};if(tools&&TOOLS_OK)opts.tools=TOOLS;else opts.cache=false;
 try{const r=await SAMPLE(input,opts);out.innerHTML=md(r.text)+(r.truncated?'<p class="note">(cut short: ask for less)</p>':"");onDone&&onDone(r.text);aiStatus("")}
 catch(e){out.innerHTML=e.text?md(e.text):"";if(e.code!=="cancelled")out.insertAdjacentHTML("beforeend",`<p class="down">${esc(AI_ERR[e.code]||AI_ERR.upstream_error)}</p>`);aiStatus("");
  if(["not_granted","sampling_disabled","not_declared","capability_disabled","capability_removed"].includes(e.code))document.querySelectorAll(".ai-only button").forEach(b=>b.disabled=true)}
 finally{if(aiCtl===ctl){$("ai-stop").hidden=true;$("plan-stop").hidden=true}}}
function analyseStock(){const sym=st.sym,c=cur(),snap=snapshotFor(sym,c);if(!snap){aiStatus("run the system first");return}
 const ctx=`${ANALYST_RULES}\n\nRESEARCH SUMMARY:\n${researchFacts()}\n\nSYSTEM DATA FOR ${sym} AS OF ${snap.date}${REPLAY?" (replay: later bars hidden)":""}:\n${JSON.stringify(snap)}`;
 const task=`Tell me how best to trade ${sym} for the next session. Cover:\n## Verdict (one of: TAKE THE TRADE, WAIT, AVOID) and why\n## How to trade it (exact entry, exit, holding time, size suggestion: full or half)\n## What to avoid on this stock right now (e.g. fading strong momentum, chasing strength) and the evidence\n## What would change the view (trigger prices)\n${TOOLS_OK?"Before writing, use study_condition on this symbol to check one or two conditions that matter most today (for example the current pulse state, a close below the lower Bollinger Band, or the current RSI(2) level) and quote the results.":""}`;
 aiCtxSym=sym;aiTurns=[{role:"user",content:ctx+"\n\nTASK:\n"+task}];
 askClaude("ai-out",aiTurns,{tools:true,onDone:t=>{aiTurns.push({role:"assistant",content:t})}})}
function followUp(){const q=$("ai-q").value.trim();if(!q)return;if(!aiTurns.length||aiCtxSym!==st.sym){analyseStock();return}$("ai-q").value="";
 $("ai-hist").insertAdjacentHTML("beforeend",`<div class="ai-turn"><b>You:</b> ${esc(q)}</div><div class="ai-turn">${$("ai-out").innerHTML}</div>`);
 aiTurns.push({role:"user",content:q});if(aiTurns.length>9)aiTurns.splice(1,2);
 askClaude("ai-out",aiTurns,{tools:true,onDone:t=>aiTurns.push({role:"assistant",content:t})}).then(()=>{if(aiTurns[aiTurns.length-1].role==="user")aiTurns.pop()})}
function planBrief(){if(!RES){return}const rows=tomorrowPlan(),act=rows.filter(r=>r.kind==="rev"||r.kind==="mom"||r.kind==="short").slice(0,8),watch=rows.filter(r=>r.kind==="watch").slice(0,8);
 const table=rows.map(r=>({symbol:r.sym,action:r.action||r.kind,entry:isF(r.entry)?+r.entry.toFixed(4):null,exit:r.exitTxt||null,est_edge:r.edge?+(100*r.edge.est).toFixed(2)+"%":null,own_trades:r.edge?r.edge.n:null,own_avg:r.edge&&r.edge.n?+(100*r.edge.avg).toFixed(2)+"%":null,chance:isF(r.P)?Math.round(100*r.P)+"%":null,pulse:r.s.pulse?PULSE_STATE[r.st0]:null,distance_to_trigger_atr:isF(r.dist)?+r.dist.toFixed(2):null,warnings:r.warn,positives:r.good}));
 const snaps=act.concat(watch.slice(0,3)).map(r=>{const x=snapshotFor(r.sym);if(x){delete x.last_15_bars;delete x.system_backtest_on_this_symbol}return x});
 const input=`${ANALYST_RULES}\n\nRESEARCH SUMMARY:\n${researchFacts()}\n\nTOMORROW'S PLAN TABLE (all ${rows.length} loaded symbols, ranked by the system):\n${JSON.stringify(table)}\n\nDETAIL FOR THE TOP CANDIDATES:\n${JSON.stringify(snaps).slice(0,40000)}\n\nTASK:\nPick the best trades for the next session.\n## Best trades (ranked, max 3): for each, the order to place (type, price), exit, size (full or half) and the reason in one or two lines with numbers\n## Watch list: stocks that could set up tomorrow and the trigger close\n## Avoid: symbols to stay away from and why (strong up-momentum on reverting stocks, momentum mode on single stocks, weak own record)\n${TOOLS_OK?"Use study_condition to check the most important claim for your top pick before you write.":""}\nIf no trade is worth taking, say so.`;
 askClaude("plan-ai",input,{tools:true})}

$("ai-go").addEventListener("click",analyseStock);$("ai-stop").addEventListener("click",()=>aiCtl&&aiCtl.abort());$("plan-stop").addEventListener("click",()=>aiCtl&&aiCtl.abort());
$("ai-send").addEventListener("click",followUp);$("ai-q").addEventListener("keydown",e=>{if(e.key==="Enter")followUp()});
$("plan-go").addEventListener("click",planBrief);$("plan-upload").addEventListener("click",()=>$("file").click());
$("plan-t").addEventListener("click",e=>{const tr=e.target.closest("tr[data-s]");if(!tr)return;const sym=tr.dataset.s;focusDate(sym,DS[sym].d[DS[sym].d.length-1])});


