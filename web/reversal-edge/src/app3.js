// ------------------------------------------------ paper trading simulator
// Placed on bar p: fills at the open of p+1 (or the close of p). Stops/targets fill at their price,
// or at the open when price gaps through; if one bar hits both, the stop counts first.
// Optional system exit: the first close back above (long) / below (short) the 5-day average.
function levelsAt(o,k){let stop=o.stop,target=o.target;for(const m of o.mods||[]){const mi=idxIn(o.sym,m.date);if(mi>=0&&mi<k){if(m.stop!==undefined)stop=m.stop;if(m.target!==undefined)target=m.target}}return {stop,target}}
function setLevel(o,key,price,persist=true){const d=DS[o.sym],c=REPLAY&&REPLAY.sym===o.sym?REPLAY.idx:d.d.length-1,date=d.d[c];o.mods=o.mods||[];let m=o.mods.find(x=>x.date===date);if(!m){m={date};o.mods.push(m)}m[key]=price;if(persist)saveOrders()}
const sma5Cache={};
function sma5Of(sym){const d=DS[sym];if(!d)return [];const key=sym+d.d.length;if(sma5Cache[sym]&&sma5Cache[sym].key===key)return sma5Cache[sym].a;const a=d.c.map((_,i)=>i<4?NaN:(d.c[i]+d.c[i-1]+d.c[i-2]+d.c[i-3]+d.c[i-4])/5);sma5Cache[sym]={key,a};return a}
function simulate(o,upto){
 const d=DS[o.sym];if(!d)return {o,status:"hidden"};const p=idxIn(o.sym,o.date);if(p<0||p>upto)return {o,status:"hidden"};
 if(o.cancelled)return {o,status:"cancelled"};const cost=o.cost!=null?o.cost:ACCT().cost;let ei,ep;
 if(o.fill==="close"){ei=p;ep=d.c[p]}else{if(p+1>upto)return {o,status:"pending"};ei=p+1;ep=d.o[p+1]}
 const sg=o.side,q=o.qty,risk0=isF(o.stop)?Math.abs(ep-o.stop)*q:NaN,ci=o.closeDate?idxIn(o.sym,o.closeDate):-1,cf=o.closeFill||o.fill,s5=o.sysExit?sma5Of(o.sym):null;let xi=-1,xp=NaN,why="";
 for(let k=p+1;k<=upto;k++){const {stop,target}=levelsAt(o,k),op=d.o[k],hi=d.h[k],lo=d.l[k];
  if(isF(stop)&&(sg>0?lo<=stop:hi>=stop)){xi=k;xp=(sg>0?op<=stop:op>=stop)?op:stop;why="Stop";break}
  if(isF(target)&&(sg>0?hi>=target:lo<=target)){xi=k;xp=(sg>0?op>=target:op<=target)?op:target;why="Target";break}
  if(s5&&k>=ei&&(sg>0?d.c[k]>s5[k]:d.c[k]<s5[k])){xi=k;xp=d.c[k];why="5d avg";break}
  if(o.time>0&&k-ei>=o.time){xi=k;xp=d.c[k];why="Time";break}
  if(ci>=ei){if(cf==="close"&&k===ci){xi=k;xp=d.c[k];why="Manual";break}if(cf!=="close"&&k===ci+1){xi=k;xp=op;why="Manual";break}}}
 if(xi<0&&ci===ei&&ci===p&&cf==="close"){xi=ei;xp=ep;why="Manual"}
 const fees=(Math.abs(ep*q)+(xi>=0?Math.abs(xp*q):0))*cost;
 if(xi>=0){const pnl=sg*(xp-ep)*q-fees;return {o,status:"closed",entryIdx:ei,entryPx:ep,exitIdx:xi,exitPx:xp,reason:why,pnl,R:risk0>0?pnl/risk0:NaN,bars:xi-ei}}
 const mark=d.c[upto],upnl=sg*(mark-ep)*q-fees;return {o,status:"open",entryIdx:ei,entryPx:ep,mark,upnl,R:risk0>0?upnl/risk0:NaN,bars:upto-ei,closing:ci>=0}}
function uptoFor(o){const d=DS[o.sym];if(!d)return -1;if(o.mode==="replay"){if(REPLAY&&REPLAY.sid===o.sid)return REPLAY.idx;return o.closeDate?Math.min(d.d.length-1,idxIn(o.sym,o.closeDate)+1):d.d.length-1}return d.d.length-1}
function simAll(){const m=mode();return ORDERS.filter(o=>m==="replay"?o.mode==="replay"&&o.sid===REPLAY.sid:o.mode==="live").map(o=>simulate(o,uptoFor(o)))}
function account(){const A=ACCT();let real=0,unreal=0,open=0,expo=0;for(const r of simAll()){if(r.status==="closed")real+=r.pnl;if(r.status==="open"){unreal+=r.upnl;open++;expo+=Math.abs(r.mark*r.o.qty)}}return {start:A.start,real,unreal,eq:A.start+real+unreal,open,expo}}

// ------------------------------------------------ order ticket
let side=1,autoQty=true;const draft={show:false};
const refPrice=()=>{const d=D();return d?d.c[cur()]:NaN};
const readTicket=()=>({stop:parseFloat($("t-stop").value),target:parseFloat($("t-target").value),risk:parseFloat($("t-risk").value)/100,qty:parseInt($("t-qty").value,10),time:parseInt($("t-time").value,10)||0});
function setSide(s){side=s;$("t-buy").classList.toggle("on",s>0);$("t-sell").classList.toggle("on",s<0);$("t-place").className="place "+(s>0?"b":"s");const t=readTicket(),e=refPrice();if(isF(t.stop)&&(s>0?t.stop>=e:t.stop<=e))defaultLevels();else ticketChanged(false)}
function sysPlan(c){const d=D();if(!d||!ARR)return null;const s=S(),sd=s?s.side:1,e=d.c[c],atr=isF(ARR.atr[c])?ARR.atr[c]:e*.02,k=ECFG.stopATR||3;
 const exitLine=ARR.sma5Arr[c],mean=ARR.meanArr[c];
 const stop=e-sd*k*atr,target=isF(exitLine)&&sd*(exitLine-e)>.25*atr?exitLine:isF(mean)&&sd*(mean-e)>.25*atr?mean:e+sd*atr;
 return {lg:sd>0,e,stop,target,exitLine,mean,atr,rr:Math.abs(target-e)/Math.abs(e-stop)}}
function defaultLevels(){const d=D();if(!d||!ARR)return;const p=sysPlan(cur());if(!p)return;const c=cur(),e=d.c[c],atr=p.atr,dg=pdig(e);
 const stop=side>0?Math.min(p.stop,e-.5*atr):Math.max(e+(e-p.stop),e+.5*atr),tg=side*(p.target-e)>0?p.target:e+side*1.5*atr;
 $("t-stop").value=(side===(p.lg?1:-1)?p.stop:stop).toFixed(dg);$("t-target").value=tg.toFixed(dg);ticketChanged(false)}
function sizing(){const t=readTicket(),e=refPrice(),A=ACCT(),acc=account(),per=isF(t.stop)?Math.abs(e-t.stop):NaN;let qty=t.qty;
 if(autoQty){qty=per>0?Math.floor(acc.eq*t.risk/per):0;const cap=Math.floor(acc.eq*A.lev/e);if(qty>cap)qty=cap;qty=Math.max(0,qty)}return {t,e,per,qty,acc,A}}
function ticketChanged(user=true){if(user)draft.show=true;
 if(!D()){$("t-sum").textContent="Load a price file to trade.";$("t-place").disabled=true;return}
 const {t,e,per,qty,acc,A}=sizing();if(autoQty)$("t-qty").value=qty||"";$("t-entry").value=fp(e);$("t-fill").textContent=A.fill==="open"?"≈ next open":"this close";
 const errs=[],warn=[];
 if(!isF(t.stop))errs.push("Set a stop so the size can be worked out.");else if(side>0?t.stop>=e:t.stop<=e)errs.push(side>0?"A long stop must be below the entry.":"A short stop must be above the entry.");
 if(isF(t.target)&&(side>0?t.target<=e:t.target>=e))errs.push(side>0?"A long target must be above the entry.":"A short target must be below the entry.");
 if(!(qty>0))errs.push("Size is zero. Raise the risk % or move the stop.");
 if(REPLAY&&REPLAY.sym!==st.sym)errs.push("Replay is running on another symbol.");
 const risk=per*qty,reward=isF(t.target)?Math.abs(t.target-e)*qty:NaN,notional=e*qty;
 $("t-sum").innerHTML=`risk <b>${money(risk)}</b> (${pct(risk/acc.eq,2)}) · reward <b>${money(reward)}</b><br>R:R <b>${isF(reward)&&risk>0?(reward/risk).toFixed(2):"—"}</b> · size <b>${money(notional)}</b> (${pct(notional/acc.eq,0)} of equity)`;
 if(autoQty&&qty>0&&per>0&&Math.floor(acc.eq*t.risk/per)>qty)warn.push(`Size capped at ${A.lev}× equity.`);
 if($("t-sys").checked&&isF(reward)&&risk>0&&reward/risk<1)warn.push("System-style trade: a near target and a wide stop. The edge comes from winning about 70% of the time, so the reward-to-risk looks small by design.");
 if(!REPLAY&&A.fill==="open")warn.push("Live: fills at the open of the next bar you upload.");
 $("t-msg").innerHTML=errs.map(x=>`<div class="er">${esc(x)}</div>`).join("")+warn.map(x=>`<div class="wn">${esc(x)}</div>`).join("");
 const pl=$("t-place");pl.disabled=errs.length>0;pl.textContent=`${side>0?"Buy":"Sell short"} ${qty>0?qty.toLocaleString():""} ${st.sym||""}`;
 $("t-acct").innerHTML=`${REPLAY?"replay":"live"} account: <b style="color:var(--ink)">${money(acc.eq)}</b> · open P&amp;L <span class="${cl(acc.unreal)}">${smoney(acc.unreal)}</span> · ${acc.open} open`;
 if(user)annotate()}
$("t-buy").addEventListener("click",()=>setSide(1));$("t-sell").addEventListener("click",()=>setSide(-1));
["t-stop","t-target","t-risk","t-time"].forEach(id=>$(id).addEventListener("input",()=>{if(id==="t-risk")saveAcct();ticketChanged(true)}));
$("t-qty").addEventListener("input",()=>{autoQty=false;$("t-auto").classList.remove("on");ticketChanged(true)});
$("t-auto").addEventListener("click",()=>{autoQty=!autoQty;$("t-auto").classList.toggle("on",autoQty);ticketChanged(true)});
$("t-place").addEventListener("click",()=>{const {t,qty,A}=sizing(),d=D(),c=cur();if(!(qty>0))return;const s=S();
 ORDERS.push({id:Date.now().toString(36)+Math.random().toString(36).slice(2,6),sym:st.sym,side,qty,stop:t.stop,target:isF(t.target)?t.target:NaN,time:t.time,sysExit:$("t-sys").checked,date:d.d[c],fill:A.fill,cost:A.cost,mode:mode(),sid:REPLAY?REPLAY.sid:null,note:$("t-note").value.trim(),
  sys:s?{setup:s.setup[c],score:s.score[c],P:s.P[c],sig:s.sig[c]}:null});
 saveOrders();draft.show=false;$("t-note").value="";renderLive();annotate();
 $("t-msg").innerHTML=`<div class="okm">${side>0?"Bought":"Sold short"} ${qty} ${esc(st.sym)}: ${A.fill==="open"?"fills at the next open":"filled at "+fp(d.c[c])}. See My trades.</div>`});

// ------------------------------------------------ signal strip (latest bar, or the replay bar)
function gaugeSvg(p,col){const a=Math.PI*(1-Math.max(0,Math.min(1,p))),R=34,cx=40,cy=40,x=cx+R*Math.cos(a),y=cy-R*Math.sin(a);
 return `<svg width="80" height="46" viewBox="0 0 80 46" role="img" aria-label="Probability ${Math.round(100*p)}%"><path d="M6 40 A34 34 0 0 1 74 40" fill="none" stroke="#2c2c2a" stroke-width="7" stroke-linecap="round"/><path d="M6 40 A34 34 0 0 1 ${x.toFixed(1)} ${y.toFixed(1)}" fill="none" stroke="${col}" stroke-width="7" stroke-linecap="round"/><text x="40" y="38" text-anchor="middle" font-size="15" font-family="JetBrains Mono,monospace" fill="#fff">${isF(p)?Math.round(100*p)+"%":"—"}</text></svg>`}
function lastStep(s,c){let st0=null;for(const x of s.steps)if(x.i<=c)st0=x;return st0}
function chipName(k,v){if(k==="gap_size")return v>0?"No news-like gap":"News-like gap";if(k==="lower_wick")return v>0?"No long lower wick":"Long lower wick";return signLabel(k)}
function topSigns(s,i,n=4){return RES.names.map(k=>[k,s.C[k][i]]).filter(x=>isF(x[1])).sort((a,b)=>Math.abs(b[1])-Math.abs(a[1])).slice(0,n)}
function renderSigbar(){
 const d=D(),el=$("sigbar");if(!d){el.innerHTML='<span class="note">Load a price file in the Data tab.</span>';return}
 const c=cur(),s=S(),when=REPLAY?`as of ${d.d[c]} (replay)`:`after the close of ${d.d[c]}`;
 if(!s){el.innerHTML=`<span class="vp none">${busy?"Computing":"No model"}</span><div class="say">${busy?"The engine is computing on this file; signals appear in a moment.":lastErr?esc(lastErr):"Run the system in the Data tab."}</div><div></div>`;return}
 if(c<s.first){el.innerHTML=`<span class="vp none">Warm-up</span><div class="say">The score starts on ${s.d[s.first]} (it needs about a year of history for the volatility and volume baselines).</div><div></div>`;return}
 const sd=s.side,setup=!!s.setup[c],sig=!!s.sig[c],sc=s.score[c],th=thirdOf(sc),P=s.P[c],plan=sysPlan(c),stp=lastStep(s,c);
 let cls="none",lab="No setup",say;
 const rsiTxt=`RSI(2) is <b>${fmt(s.rsi2[c],0)}</b>`;
 if(setup&&sig){cls=sd>0?"long":"short";lab=sd>0?"Buy setup":"Sell setup"}else if(setup){cls="watch";lab="Weak setup"}
 if(setup){say=`${rsiTxt}: a short-term ${sd>0?"oversold":"overbought"} setup. Its Reversal Edge Score is <b style="color:${THIRD_COL[th]}">${fmt(sc,1)} (${THIRD_NAME[th]})</b>. `;
  const own=stp&&stp.thirds[th];
  say+=`Chance this bounce trade is profitable: <b>${pct(P,0)}</b>.`;
  if(own&&own.n>=8)say+=` On this stock, past setups in the ${THIRD_NAME[th]} averaged <b class="${cl(own.avg)}">${spct(own.avg,2)}</b> per trade (${own.n} trades, ${pct(own.win,0)} won).`;
  say+=` Across 87 stocks the ${THIRD_NAME[th]} averaged ${(RESEARCH_THIRDS.avg87[th]/100).toFixed(2)}%.`;
  if(cls==="watch")say+=` Below your filter (${$("c-scoreThr").selectedOptions[0].textContent}), so the system skips it.`;
  if(sig)say+=` Plan: ${sd>0?"buy":"sell"} at the next open, stop ${fp(plan.stop)} (${ECFG.stopATR} ATR), exit on the first close back ${sd>0?"above":"below"} the 5-day average (now ${fp(plan.exitLine)}) or after ${ECFG.maxHold} days.`}
 else say=`${rsiTxt}: no ${sd>0?"oversold":"overbought"} setup (needs RSI(2) ${sd>0?"below "+ECFG.trig:"above "+(100-ECFG.trig)}). Price is ${fmt(Math.abs(s.z20[c]),2)}σ ${s.z20[c]<0?"below":"above"} its 20-day mean${s.zone[c]>=0?`, in zone ${["below 2.5%","2.5–10%","10–25%","25–75%","75–90%","90–97.5%","above 97.5%"][s.zone[c]]} of its own history`:""}.`;
 if(!isF(s.frank[c]))say+=` <span class="acc">No fear-index value for this date; that sign counts as neutral.</span>`;
 const chips=setup?topSigns(s,c).map(([k,v])=>`<span class="${v>0.05?"y":v<-0.05?"n":"m"}" title="${esc(signMeaning(k))}">${v>0.05?"▲":v<-0.05?"▼":"·"} ${esc(chipName(k,v))}</span>`).join(""):"";
 el.innerHTML=`<div><span class="vp ${cls}">${lab}</span><div class="note" style="margin-top:4px">${when}</div></div><div class="say">${say}</div>
  <div class="acts">${setup?`<div class="gauge">${gaugeSvg(P,THIRD_COL[th])}<span>chance of profit</span></div>`:""}<div style="display:grid;gap:6px"><button class="btn sm" id="use-plan">Trade this plan</button>${REPLAY?"":`<div style="display:flex;gap:6px"><button class="btn ghost sm" id="sig-prev">◀ prev</button><button class="btn ghost sm" id="sig-next">next ▶</button></div>`}</div></div>
  <div class="row3">${plan?`<div class="lvls"><div><span>entry ≈</span><b>${fp(plan.e)}</b></div><div><span>stop</span><b class="down">${fp(plan.stop)}</b></div><div><span>exit line (5d avg)</span><b class="acc">${fp(plan.exitLine)}</b></div><div><span>20-day mean</span><b>${fp(plan.mean)}</b></div><div><span>ATR</span><b>${fp(plan.atr)}</b></div></div>`:""}<div class="chips">${chips}</div></div>`}
$("sigbar").addEventListener("click",e=>{const id=e.target.id;
 if(id==="use-plan"){const p=sysPlan(cur());if(!p)return;setSide(p.lg?1:-1);const dg=pdig(p.e);$("t-stop").value=p.stop.toFixed(dg);$("t-target").value=p.target.toFixed(dg);$("t-time").value=ECFG.maxHold;$("t-sys").checked=true;draft.show=true;ticketChanged(true)}
 if((id==="sig-prev"||id==="sig-next")&&S()){const s=S(),idx=[];for(let i=0;i<s.sig.length;i++)if(s.sig[i])idx.push(i);if(!idx.length)return;
  const r=chart.timeScale().getVisibleLogicalRange(),mid=st.pinned&&st.cursor!=null?st.cursor:r?(r.from+r.to)/2:lastIdx(),w=r?r.to-r.from:160;
  const tg=id==="sig-next"?idx.find(i=>i>mid):[...idx].reverse().find(i=>i<mid);if(tg==null)return;
  chart.timeScale().setVisibleLogicalRange({from:tg-w*.6,to:tg+w*.4});st.pinned=true;st.cursor=tg;syncScrub();inspector(tg);renderLegend()}});

// ------------------------------------------------ inspector: reversal radar, zones, look-alike setups, context
function analogs(s,i,K=25,H=10){ // nearest past bars by the nine signs + RSI(2), outcomes fully known before bar i
 const keys=RES.names,cand=[];const lim=i-H;if(lim<300)return null;
 const want=s.setup[i];
 for(let j=s.first;j<=lim;j++){if(want&&!s.setup[j])continue;let d2=0;for(const k of keys)d2+=(s.Z[k][j]-s.Z[k][i])**2;d2+=((s.rsi2[j]-s.rsi2[i])/15)**2;if(isF(d2))cand.push([d2,j])}
 if(cand.length<10)return null;cand.sort((a,b)=>a[0]-b[0]);const pick=cand.slice(0,K).map(x=>x[1]);
 const paths=pick.map(j=>{const a=[];for(let k=0;k<=H;k++)a.push(s.c[j+k]/s.c[j]-1);return a});
 const q=(arr,p)=>{const v=arr.slice().sort((a,b)=>a-b);return quantSortedUI(v,p)};
 const band=[...Array(H+1).keys()].map(k=>{const col=paths.map(p=>p[k]);return [q(col,.1),q(col,.25),q(col,.5),q(col,.75),q(col,.9)]});
 const tr=pick.map(j=>s.tret[j]).filter(isF);
 return {pick,paths,band,up5:paths.filter(p=>p[5]>0).length/paths.length,trade:tr.length?tr.reduce((a,b)=>a+b,0)/tr.length:NaN,win:tr.length?tr.filter(x=>x>0).length/tr.length:NaN,dates:pick.map(j=>s.d[j])}}
function quantSortedUI(a,q){if(!a.length)return NaN;const p=q*(a.length-1),i=Math.floor(p),f=p-i;return i+1<a.length?a[i]+f*(a[i+1]-a[i]):a[i]}
function fanSvg(A){const W=300,H=150,L=34,B=18,T=6,R=6,n=A.band.length,all=A.band.flat(),lo=Math.min(-.02,...all),hi=Math.max(.02,...all);
 const x=k=>L+k*(W-L-R)/(n-1),y=v=>T+(hi-v)/(hi-lo)*(H-T-B);
 const area=(a,b)=>A.band.map((r,k)=>`${x(k).toFixed(1)},${y(r[a]).toFixed(1)}`).join(" ")+" "+A.band.map((r,k)=>[k,r]).reverse().map(([k,r])=>`${x(k).toFixed(1)},${y(r[b]).toFixed(1)}`).join(" ");
 let g=`<svg class="fan" viewBox="0 0 ${W} ${H}" role="img" aria-label="Paths after similar setups">`;
 for(const v of [lo,0,hi])g+=`<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="${v===0?"#555":"#2c2c2a"}"/><text x="${L-4}" y="${y(v)+3}" font-size="9" text-anchor="end" fill="#898781">${(v*100).toFixed(0)}%</text>`;
 for(const k of [0,5,10])if(k<n)g+=`<text x="${x(k)}" y="${H-4}" font-size="9" text-anchor="middle" fill="#898781">${k===0?"today":"+"+k+"d"}</text>`;
 A.paths.forEach(p=>{g+=`<polyline fill="none" stroke="rgba(195,194,183,.12)" points="${p.map((v,k)=>`${x(k).toFixed(1)},${y(v).toFixed(1)}`).join(" ")}"/>`});
 g+=`<polygon fill="rgba(57,135,229,.16)" points="${area(0,4)}"/><polygon fill="rgba(57,135,229,.3)" points="${area(1,3)}"/>`;
 g+=`<polyline fill="none" stroke="#4fd1a5" stroke-width="2" points="${A.band.map((r,k)=>`${x(k).toFixed(1)},${y(r[2]).toFixed(1)}`).join(" ")}"/></svg>`;return g}
function zoneTable(s,i){const names=["below 2.5%","2.5–10%","10–25%","25–75%","75–90%","90–97.5%","above 97.5%"],cnt=new Array(7).fill(0),t=new Array(7).fill(0),f=new Array(7).fill(0);
 for(let j=0;j<=i-10;j++){const z=s.zone[j];if(z>=0&&isF(s.touch[j])){cnt[z]++;t[z]+=s.touch[j];f[z]+=s.fwd5[j]}}
 return `<table class="ztab"><tr><td class="lab">zone (own z-percentile)</td><td class="n lab">n</td><td class="n lab">touched mean ≤10d</td><td class="n lab">avg 5d</td></tr>`+names.map((nm,k)=>`<tr class="${s.zone[i]===k?"cur":""}"><td>${s.zone[i]===k?"▶ ":""}${nm}</td><td class="n">${cnt[k]}</td><td class="n">${cnt[k]?pct(t[k]/cnt[k],0):"—"}</td><td class="n ${cl(f[k])}">${cnt[k]?spct(f[k]/cnt[k],1):"—"}</td></tr>`).join("")+`</table>`}
function inspector(i){const el=$("inspbody"),d=D();if(!d){el.innerHTML="";return}
 const s=S();let h=`<div class="ih"><b>${esc(st.sym)}</b><span>${d.d[i]}</span><span class="pin ${st.pinned?"on":""}">${st.pinned?"PINNED":"hover"}</span></div>`;
 if(!s){el.innerHTML=h+`<div class="note">O ${fp(d.o[i])} · H ${fp(d.h[i])} · L ${fp(d.l[i])} · C ${fp(d.c[i])}<br>Reversal details appear once the system has run.</div>`;return}
 const sc=s.score[i],th=thirdOf(sc),P=s.P[i];
 h+=`<div class="top2"><div><div class="lab">chance of profit (bounce trade)</div><div class="bigp">${isF(P)?pct(P,0):"—"}</div><div class="note">research weights alone: ${isF(s.Pr[i])?pct(s.Pr[i],0):"—"}</div></div><div><div class="lab">reversal edge score</div><div class="act" style="color:${THIRD_COL[th]||"inherit"}">${fmt(sc,2)} · ${THIRD_NAME[th]||"—"}</div><div class="note">${s.setup[i]?(s.sig[i]?"setup · passes your filter":"setup · below your filter"):"no RSI(2) setup on this bar"}</div></div></div>`;
 // radar: weighted contributions
 const mx=Math.max(.5,...RES.names.map(k=>Math.abs(s.C[k][i]||0)));
 h+=`<div class="sec">reversal radar · what moves the score (weight × how unusual today is)</div><div class="radar">`+RES.names.map(k=>{const v=s.C[k][i],w=Math.abs(v||0)/mx*50,raw=s.X[k][i],ev=signEvidence(k);
  const shown=k==="fear_rank"||k==="vol_rank"?pct(raw,0):k==="down_streak"?fmt(raw,0):k==="lower_wick"?pct(raw,0):fmt(raw,2);
  return `<div class="rr" title="${esc(signMeaning(k))} Research: top-vs-bottom-third trade difference ${ev?ev.map(x=>(x>0?"+":"")+x+"bp").join(" / "):""} (87 stocks / TSLA 11-17 / TSLA 18-26)."><span class="nm">${esc(signLabel(k))}</span><span class="vv">${shown}</span><div class="cb"><i style="left:${(v||0)>=0?50:50-w}%;width:${w}%;background:${(v||0)>=0?"#4fd1a5":"#e66767"}"></i></div></div>`}).join("")+`</div>`;
 const stp=lastStep(s,i);if(stp)h+=`<div class="note" style="margin-top:4px">weights: ${stp.own<30?"research (not enough own setups yet)":`${Math.round(100*(1-stp.lam))}% research, ${Math.round(100*stp.lam)}% this stock (${stp.own} own setups)`} · refit ${stp.d}</div>`;
 // other quick reads
 h+=`<div class="sec">quick read</div><table class="t"><tr><td>RSI(2) / RSI(14)</td><td class="n">${fmt(s.rsi2[i],0)} / ${fmt(s.rsi14[i],0)}</td></tr><tr><td>streak · close in range (IBS)</td><td class="n">${fmt(s.streak[i],0)} · ${pct(s.ibs[i],0)}</td></tr>
  <tr><td>volume vs normal</td><td class="n">${isF(s.volz[i])?(s.volz[i]>=0?"+":"")+s.volz[i].toFixed(1)+"σ":"—"}</td></tr><tr><td>range / gap (ATR)</td><td class="n">${fmt(s.rangex[i],2)} / ${fmt(s.gap[i],2)}</td></tr>
  <tr><td>Yang-Zhang vol (5/20/60d)</td><td class="n">${fmt(s.yz5[i],0)} / ${fmt(s.yz20[i],0)} / ${fmt(s.yz60[i],0)}%</td></tr><tr><td>GARCH next-day vol</td><td class="n">${fmt(s.garch[i],0)}%</td></tr><tr><td>VIX · rank</td><td class="n">${fmt(s.vix[i],1)} · ${pct(s.frank[i],0)}</td></tr></table>`;
 h+=`<div class="sec">stock-specific z-zones · what happened next from each zone (data before this bar)</div>`+zoneTable(s,i);
 const A=analogs(s,i);
 if(A){h+=`<div class="sec">look-alike setups · ${A.pick.length} most similar past ${s.setup[i]?"setups":"bars"} (signs + RSI(2))</div>${fanSvg(A)}<div class="note">${pct(A.up5,0)} were higher 5 days later · system exit averaged <span class="${cl(A.trade)}">${spct(A.trade,2)}</span> (${pct(A.win,0)} won). Median path green; bands 25–75% and 10–90%. Most recent: ${A.dates.slice().sort().slice(-3).join(", ")}.</div>`}
 if(!REPLAY&&isF(s.tret[i])&&s.setup[i])h+=`<div class="hind">hindsight (not known at the time): this setup's trade returned ${spct(s.tret[i],2)} after ${s.thold[i]} bars (${esc(s.texit[i])})</div>`;
 h+=`<div class="sec">fair-value context (earlier system)</div><table class="t">`;
 [["kalman","Kalman"],["ou","OU mean"],["trend","Trend line"],["factor","Market residual"]].forEach(([m,nm])=>{if(!s["zz_"+m])return;const zz=s["zz_"+m][i];h+=`<tr><td><span style="color:${C.mean[m]}">■</span> ${nm}</td><td><span class="pill" style="background:${zc(zz)};color:#fff">${isF(zz)?(zz>=0?"+":"")+zz.toFixed(2)+"σ":"—"}</span></td><td class="n">${fmt(s["lv_"+m]&&s["lv_"+m][i],2)}</td></tr>`});
 h+=`</table><div class="note" style="margin-top:4px">Hurst ${fmt(s.hurst[i])} · ADF p ${fmt(s.adf[i])} · VR(4) ${fmt(s.vr4[i])} · OU half-life ${fmt(s.hl[i],1)} bars</div>`;
 el.innerHTML=h}

// ------------------------------------------------ scanner
function drawScan(){
 if(!RES){clr("scan-t",'<tr><td class="empty">Run the system in the Data tab first.</td></tr>');return}
 const rows=RES.syms.filter(SY).map(sym=>{const s=SY(sym),i=s.d.length-1,stp=lastStep(s,i),th=thirdOf(s.score[i]);return {sym,s,i,th,own:stp&&stp.thirds[th]}});
 rows.sort((a,b)=>(b.s.sig[b.i]-a.s.sig[a.i])||(b.s.setup[b.i]-a.s.setup[a.i])||(b.s.score[b.i]-a.s.score[a.i]));
 $("scan-note").innerHTML=`${rows.filter(r=>r.s.sig[r.i]).length} signal(s) and ${rows.filter(r=>r.s.setup[r.i]).length} setup(s) on the latest bar across ${rows.length} symbol(s). Click a row to open it on the chart.`;
 const zn=["<2.5%","2.5–10%","10–25%","25–75%","75–90%","90–97.5%",">97.5%"];
 $("scan-t").innerHTML="<tr>"+["symbol","date","close","1d","RSI(2)","state","edge score","chance of profit","this stock, same third","zone","vol rank","vol trend","fear rank","top signs"].map(h=>`<th>${h}</th>`).join("")+"</tr>"+rows.map(({sym,s,i,th,own})=>{
  const state=s.sig[i]?`<span class="vp long" style="padding:1px 6px">${s.side>0?"buy":"sell"}</span>`:s.setup[i]?'<span class="vp watch" style="padding:1px 6px">weak setup</span>':'<span class="note">—</span>';
  return `<tr data-s="${esc(sym)}"><td>${esc(sym)}</td><td>${s.d[i]}</td><td>${fp(s.c[i])}</td><td class="${cl(s.c[i]/s.c[i-1]-1)}">${spct(s.c[i]/s.c[i-1]-1,1)}</td><td>${fmt(s.rsi2[i],0)}</td><td>${state}</td><td style="color:${THIRD_COL[th]}">${fmt(s.score[i],1)}</td><td>${pct(s.P[i],0)}</td><td>${own&&own.n?`${spct(own.avg,2)} (n ${own.n})`:"—"}</td><td>${s.zone[i]>=0?zn[s.zone[i]]:"—"}</td><td>${pct(s.vrank[i],0)}</td><td>${isF(s.vterm[i])?(s.vterm[i]>0?"rising":"falling"):"—"}</td><td>${pct(s.frank[i],0)}</td><td style="text-align:left">${topSigns(s,i,3).map(([k,v])=>`<span class="${v>0?"up":"down"}">${v>0?"▲":"▼"}${esc(chipName(k,v))}</span>`).join(" ")}</td></tr>`}).join("")}
$("scan-t").addEventListener("click",e=>{const tr=e.target.closest("tr[data-s]");if(!tr)return;const sym=tr.dataset.s;focusDate(sym,DS[sym].d[DS[sym].d.length-1])});
