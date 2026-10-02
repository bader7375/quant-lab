const LW=window.LightweightCharts;
const load=(k,d)=>{try{const v=store(k);return v?JSON.parse(v):d}catch(e){return d}};
const TV={up:"#26a69a",down:"#ef5350",upV:"rgba(38,166,154,.42)",downV:"rgba(239,83,80,.42)",you:"#c08cff",line:"#d4b06a"};
const money=(v,d=0)=>isF(v)?(v<0?"−$":"$")+Math.abs(v).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d}):"—";
const smoney=v=>isF(v)?(v>=0?"+":"−")+"$"+Math.abs(v).toLocaleString(undefined,{maximumFractionDigits:0}):"—";
const spct=(v,d=1)=>isF(v)?(v>=0?"+":"−")+Math.abs(v*100).toFixed(d)+"%":"—";
const sR=v=>isF(v)?(v>=0?"+":"−")+Math.abs(v).toFixed(2)+"R":"—";
const cl=v=>!isF(v)?"":v>0?"up":v<0?"down":"";
const pdig=p=>p<1?4:p<20?3:2, fp=v=>isF(v)?v.toFixed(pdig(Math.abs(v))):"—";
let plotlyP=null;
const needPlotly=()=>window.Plotly?Promise.resolve():(plotlyP=plotlyP||new Promise((res,rej)=>{const s=document.createElement("script");s.src="plotly.min.js";s.onload=res;s.onerror=()=>rej(new Error("chart library failed to load"));document.head.appendChild(s)}));
const clr=(id,html="")=>{const el=typeof id==="string"?$(id):id;if(!el)return;if(window.Plotly&&el._fullLayout){try{Plotly.purge(el)}catch(e){}}el.innerHTML=html};
const THIRDS=[-1.7889,0.4356];
const thirdOf=s=>!isF(s)?-1:s<=THIRDS[0]?0:s<=THIRDS[1]?1:2;
const THIRD_NAME=["bottom third","middle third","top third"],THIRD_COL=["#8a8a85","#fab219","#4fd1a5"];
const RESEARCH_THIRDS={avg87:[-21,3,57],win87:[.61,.65,.71],avgT:[-7,-12,135],winT:[.66,.68,.72]};

// ------------------------------------------------ CSV ingestion
const ALIAS={date:["date","datetime","time","timestamp","day"],ticker:["ticker","symbol","stock","code"],open:["open","openprice"],high:["high","highprice"],low:["low","lowprice"],
 close:["close","closelast","last","closeprice","price"],adj:["adjclose","adjustedclose","closeadj"],volume:["volume","vol"]};
const norm=s=>String(s).toLowerCase().replace(/[^a-z0-9]/g,"");
function tickerFromName(name){const parts=name.replace(/\.[^.]+$/,"").split(/[_.\s-]/).filter(Boolean);while(parts.length>1&&(["us","uk","de","sa","se","d","daily","w","m","historical","data","history","prices"].includes(parts[parts.length-1].toLowerCase())||/^\d+$/.test(parts[parts.length-1])))parts.pop();return parts.join("_").toUpperCase()}
function toISO(s){s=String(s).trim().replace(/^"|"$/g,"");let m=s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);if(m)return `${m[1]}-${m[2].padStart(2,"0")}-${m[3].padStart(2,"0")}`;
 m=s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);if(m)return `${m[3]}-${m[1].padStart(2,"0")}-${m[2].padStart(2,"0")}`;m=s.match(/^(\d{4})(\d{2})(\d{2})$/);if(m)return `${m[1]}-${m[2]}-${m[3]}`;const t=Date.parse(s);return isNaN(t)?null:new Date(t).toISOString().slice(0,10)}
const num=v=>{const x=parseFloat(String(v).replace(/[$,\s"]/g,""));return isF(x)?x:NaN};
function splitLine(l,sep){if(!l.includes('"'))return l.split(sep);const out=[];let cur="",q=false;for(const ch of l){if(ch==='"')q=!q;else if(ch===sep&&!q){out.push(cur);cur=""}else cur+=ch}out.push(cur);return out}
function parseCSV(text,fname){
 const lines=text.replace(/\r/g,"").split("\n").filter(l=>l.trim());if(lines.length<2)throw new Error(fname+": the file is empty.");
 const sep=[",",";","\t"].sort((a,b)=>lines[0].split(b).length-lines[0].split(a).length)[0];
 const head=splitLine(lines[0],sep).map(norm),col={};
 for(const [k,al] of Object.entries(ALIAS)){let i=head.findIndex(h=>al.includes(h));if(i<0&&k!=="ticker")i=head.findIndex(h=>al.some(a=>a.length>3&&h.includes(a)));if(i>=0)col[k]=i}
 const miss=["date","open","high","low","close"].filter(k=>col[k]==null);if(miss.length)throw new Error(`${fname}: missing column ${miss.join(", ")}. The first line reads: ${lines[0].slice(0,100)}`);
 const out={};let bad=0;
 for(const l of lines.slice(1)){const r=splitLine(l,sep);const d=toISO(r[col.date]);if(!d){bad++;continue}
  const tk=col.ticker!=null?String(r[col.ticker]).trim().replace(/"/g,"").toUpperCase():tickerFromName(fname);
  let o=num(r[col.open]),h=num(r[col.high]),lo=num(r[col.low]),c=num(r[col.close]);const adj=col.adj!=null?num(r[col.adj]):c;const v=col.volume!=null?num(r[col.volume]):NaN;
  if(!(c>0)||!(adj>0)){bad++;continue}const f=adj/c;o=(o>0?o:c)*f;c=adj;h=Math.max(isF(h)&&h>0?h*f:c,o,c);lo=Math.min(lo>0?lo*f:c,o,c);
  (out[tk]=out[tk]||[]).push([d,o,h,lo,c,v])}
 const res={};for(const [tk,rows] of Object.entries(out)){rows.sort((a,b)=>a[0]<b[0]?-1:1);const u=rows.filter((r,i)=>i===0||r[0]!==rows[i-1][0]);
  res[tk]={d:u.map(r=>r[0]),o:u.map(r=>r[1]),h:u.map(r=>r[2]),l:u.map(r=>r[3]),c:u.map(r=>r[4]),v:u.map(r=>r[5]),src:fname,bad}}
 if(!Object.keys(res).length)throw new Error(fname+": no rows with a valid date and price.");return res}
const isFearName=k=>/^\^?VIX(_|$)|^VIX\d*$|^CBOE_?VIX/i.test(k);

let DS=load("qlab-ds",{});for(const k of Object.keys(DS))if(isFearName(k))delete DS[k];
let FEAR=null,FEAR_SRC="";           // {d:[],c:[]} market fear index (VIX)
let USERFEAR=load("qlab-fear",null);
function saveDS(){if(store("qlab-ds",JSON.stringify(DS))===null&&Object.keys(DS).length)$("parsemsg").innerHTML='<span class="err">The browser would not store these files, so they will need reloading next visit.</span>'}
function mergeFear(a,b){if(!a)return b;if(!b)return a;const m=new Map();a.d.forEach((d,i)=>m.set(d,a.c[i]));b.d.forEach((d,i)=>m.set(d,b.c[i]));const ks=[...m.keys()].sort();return {d:ks,c:ks.map(k=>m.get(k))}}
async function loadFear(){let base=null;try{const t=await (await fetch("VIX.csv")).text();const r=parseCSV(t,"VIX.csv");base=r[Object.keys(r)[0]];base={d:base.d,c:base.c}}catch(e){}
 FEAR=mergeFear(base,USERFEAR);FEAR_SRC=USERFEAR?"built-in VIX + your file":"built-in VIX (CBOE via datasets/finance-vix)";renderFear()}
function renderFear(){const el=$("fearmsg");if(!FEAR){el.innerHTML='<span class="err">No fear index loaded: the fear sign counts as neutral. Upload VIX.csv to add it.</span>';return}
 const last=FEAR.d[FEAR.d.length-1],lastData=Object.values(DS).reduce((m,d)=>d.d[d.d.length-1]>m?d.d[d.d.length-1]:m,"");
 el.innerHTML=`Fear index: ${esc(FEAR_SRC)}, ${FEAR.d[0]} → ${last}.`+(lastData&&lastData>last?` <span class="err">Your prices run to ${lastData}; after ${last} the fear sign counts as neutral. Upload a newer VIX.csv to fix that.</span>`:"")}
function renderDS(){const ks=Object.keys(DS).sort();
 $("dslist").innerHTML=ks.length?ks.map(k=>{const d=DS[k];return `<div class="ds"><div><b>${esc(k)}</b> <span class="note">${d.d.length.toLocaleString()} bars · ${d.d[0]} → ${d.d[d.d.length-1]} · ${esc(d.src||"")}</span></div><span class="note">${d.d.length<600?'<span class="err">short history</span>':""}</span><button class="x" data-rm="${esc(k)}" aria-label="Remove ${esc(k)}">✕</button></div>`}).join(""):`<div class="note">No files loaded.</div>`;
 const m=$("c-market"),cur=m.value;m.innerHTML=`<option value="">none</option>`+ks.map(k=>`<option ${k===cur?"selected":""}>${esc(k)}</option>`).join("");renderFear()}
$("dslist").addEventListener("click",e=>{const k=e.target.dataset.rm;if(k){delete DS[k];saveDS();afterDataChange()}});
async function addFiles(files){const msgs=[];let first=null,fearHit=false;
 for(const f of files){try{const r=parseCSV(await f.text(),f.name);
  for(const [k,v] of Object.entries(r)){if(isFearName(k)||isFearName(tickerFromName(f.name))){USERFEAR=mergeFear(USERFEAR,{d:v.d,c:v.c});store("qlab-fear",JSON.stringify(USERFEAR));fearHit=true;msgs.push(`${esc(f.name)}: fear index (VIX) ${v.d[0]} → ${v.d[v.d.length-1]}`)}
   else{DS[k]=v;first=first||k;msgs.push(`${esc(f.name)}: ${esc(k)} (${v.d.length.toLocaleString()} bars${v.bad?`, ${v.bad} rows skipped`:""})`)}}}
  catch(e){msgs.push(`<span class="err">${esc(e.message)}</span>`)}}
 $("parsemsg").innerHTML=msgs.join("<br>");saveDS();if(fearHit)await loadFear();if(first)st.sym=first;afterDataChange(true)}
$("file").addEventListener("change",e=>{addFiles([...e.target.files]);e.target.value=""});
const drop=$("drop");["dragenter","dragover"].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add("over")}));
["dragleave","drop"].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove("over")}));
drop.addEventListener("drop",e=>addFiles([...e.dataTransfer.files]));
async function loadSample(){try{const t=await (await fetch("sample_TSLA.csv")).text();Object.assign(DS,parseCSV(t,"tsla_us_d.csv"));st.sym="TSLA";saveDS();$("parsemsg").textContent="Loaded TSLA (real daily prices, split-adjusted, 2010–2026).";afterDataChange(true)}catch(e){$("parsemsg").innerHTML=`<span class="err">${esc(e.message)}</span>`}}
$("sample").addEventListener("click",loadSample);
let arm={};function armed(btn,fn){if(arm[btn.id]){clearTimeout(arm[btn.id].t);btn.textContent=arm[btn.id].label;arm[btn.id]=null;fn();return}arm[btn.id]={label:btn.textContent,t:setTimeout(()=>{btn.textContent=arm[btn.id].label;arm[btn.id]=null},3000)};btn.textContent="Click again to confirm"}
$("clear").addEventListener("click",e=>armed(e.target,()=>{DS={};saveDS();RES=null;afterDataChange()}));

// ------------------------------------------------ settings + worker
const NUMS=["trig","n0","pool","testDays","stopATR","maxHold","slippage","riskPct","maxW","maxPos","acThr","limitATR","momTrig","momMaxHold"],SELS=["scoreThr","side","adapt","sizeMode","mode","entry","exit"];
try{const s=JSON.parse(store("qlab-cfg3")||"{}");for(const [k,v] of Object.entries(s)){const el=$("c-"+k);if(el&&k!=="market")el.value=v}}catch(e){}
(()=>{const a=load("desk-acct",{});if(a.start)$("a-start").value=a.start;if(a.fill)$("a-fill").value=a.fill;if(a.lev)$("a-lev").value=a.lev;if(a.risk)$("t-risk").value=a.risk})();
function readCfg(){const c={market:$("c-market").value||null};NUMS.forEach(k=>c[k]=+$("c-"+k).value);
 c.scoreThr=+$("c-scoreThr").value;c.sizeMode=$("c-sizeMode").value;c.mode=$("c-mode").value;c.entry=$("c-entry").value;c.exit=$("c-exit").value;c.side=+$("c-side").value;c.adapt=$("c-adapt").value==="1";c.riskPct/=100;c.maxW/=100;
 const s={};[...NUMS,...SELS].forEach(k=>s[k]=$("c-"+k).value);store("qlab-cfg3",JSON.stringify(s));return c}
const ACCT=()=>({start:Math.max(1000,+$("a-start").value||100000),fill:$("a-fill").value,cost:Math.max(0,+$("c-slippage").value||0)/1e4,lev:Math.max(.5,+$("a-lev").value||1)});
const saveAcct=()=>store("desk-acct",JSON.stringify({start:$("a-start").value,fill:$("a-fill").value,lev:$("a-lev").value,risk:$("t-risk").value}));
let ECFG=readCfg();
const worker=new Worker("engine.js");let RES=null,busy=false,queued=false,lastErr=null;
worker.onmessage=e=>{const m=e.data;
 if(m.type==="progress"){$("prog").style.width=(m.frac*100).toFixed(0)+"%";$("runmsg").textContent=m.msg;$("snap").textContent=`computing · ${Math.round(m.frac*100)}% · ${m.msg}`;return}
 busy=false;$("run").disabled=false;
 if(m.type==="error"){lastErr=m.message.split("\n")[0];$("runmsg").innerHTML=`<span class="err">${esc(lastErr)}</span>`;$("snap").textContent="engine error: see the Data tab";RES=null;refreshOverlays();renderLive();if(queued){queued=false;runNow()}return}
 lastErr=null;RES=m.res;const ok=RES.syms.filter(s=>RES.symbols[s]);
 const pm=RES.metrics.portfolio||{};
 $("runmsg").textContent=`Done: ${ok.length} symbol(s), ${RES.bt.trades.length} system trades (avg ${sR(pm.expectancy_R)}).`+(ok.length<RES.syms.length?` Too little history: ${RES.syms.filter(s=>!RES.symbols[s]).join(", ")}.`:"");
 $("snap").textContent=ok.length?`${ok.join(", ")} · ${ECFG.mode==="auto"?"auto mode (reversal or momentum by market character)":ECFG.mode==="rev"?"reversal mode":"momentum mode"} · ${ECFG.entry==="limit"?"limit entries":"next-open entries"} · exit ${ECFG.exit} · ${$("c-scoreThr").selectedOptions[0].textContent}`+(RES.fearEnd?` · fear index to ${RES.fearEnd}`:" · no fear index"):"Not enough history: load 3+ years of daily data.";
 if(queued){queued=false;runNow();return}
 refreshOverlays();renderLive();
 if(st.tab==="data")show("chart");else show(st.tab)};
function runNow(){if(!Object.keys(DS).length){$("runmsg").innerHTML='<span class="err">Upload at least one price file first.</span>';return}
 if(busy){queued=true;return}busy=true;$("run").disabled=true;$("prog").style.width="0%";ECFG=readCfg();worker.postMessage({cmd:"run",datasets:DS,cfg:ECFG,fear:FEAR})}
$("run").addEventListener("click",runNow);
document.querySelectorAll("#settings input,#settings select").forEach(el=>el.addEventListener("change",()=>{
 if(el.id.startsWith("a-")){saveAcct();ticketChanged(false);renderLive();return}
 if(Object.keys(DS).length)runNow()}));

// ------------------------------------------------ state
const sel=$("sym");const st={sym:null,n:252,tab:"data",cursor:null,pinned:false};
const UI=load("qlab-ui2",{});UI.ov=Object.assign({pdiv:true,zones:true,mean:true,exit:true,kalman:false,trend:false,ou:false,ema20:false,factor:false,vol:true,sys:true,setups:true,signs:true,mine:true},UI.ov||{});
UI.pn=Object.assign({pulse:true,edge:true,rsi:true,z:true,vol:true,reg:false,fear:false},UI.pn||{});
const saveUI=()=>store("qlab-ui2",JSON.stringify(UI));
let ORDERS=load("desk-orders",[]),HLINES=load("desk-hlines",{}),REPLAY=load("desk-replay",null);
const saveOrders=()=>store("desk-orders",JSON.stringify(ORDERS));
const saveReplay=()=>store("desk-replay",REPLAY?JSON.stringify(REPLAY):null);
const D=()=>DS[st.sym];
const S=()=>{const s=RES&&RES.symbols&&RES.symbols[st.sym];return s&&D()&&s.d.length===D().d.length?s:null};
const SY=sym=>{const s=RES&&RES.symbols&&RES.symbols[sym];return s&&DS[sym]&&s.d.length===DS[sym].d.length?s:null};
const lastIdx=()=>D()?D().d.length-1:-1;
const cur=()=>REPLAY&&REPLAY.sym===st.sym?REPLAY.idx:lastIdx();
const mode=()=>REPLAY?"replay":"live";
const needRun=id=>clr(id,`<div class="empty">${busy?"The engine is computing…":"Run the system in the Data tab to see this view."}</div>`);
const idxOf=date=>idxIn(st.sym,String(date).slice(0,10));
function idxIn(sym,date){const d=DS[sym];if(!d)return -1;let lo=0,hi=d.d.length-1;while(lo<=hi){const m=(lo+hi)>>1;if(d.d[m]===date)return m;if(d.d[m]<date)lo=m+1;else hi=m-1}return -1}
const signLabel=k=>{const s=RES&&RES.signs.find(x=>x[0]===k);return s?s[1]:k};
const signMeaning=k=>{const s=RES&&RES.signs.find(x=>x[0]===k);return s?s[3]:""};
const signEvidence=k=>{const s=RES&&RES.signs.find(x=>x[0]===k);return s?s[4]:null};
