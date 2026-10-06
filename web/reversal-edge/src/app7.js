// ------------------------------------------------ v13: Tadawul library, safe merging, data updates through a Claude Code session on the viewer's account
const ART_URL="https://claude.ai/artifact/HQMRJpu3hpLyj7ahSxSQDn",CCR="Claude Code Remote";
var NAMES;let LIBMETA=null,LIBTEXT=null;NAMES={};
const EXTRA_NAMES={"1111":"SAUDI TADAWUL","1182":"AMLAK INTERNATIONAL FINANCE","1183":"SHL FINANCE","1321":"EAST PIPES INTEGRATED","1322":"AL MASANE AL","1323":"UNITED CARTON INDUSTRIES","1324":"SALEH ABDULAZIZ AL","1831":"MAHARAH FOR HUMAN","1832":"SADR LOGISTICS","1833":"ALMAWARID MANPOWER","1834":"SAUDI MANPOWER SOLUTIONS","1835":"TAMKEEN HUMAN RESOURCES","2081":"ALKHORAYEF WATER AND","2082":"ACWA POWER","2083":"POWER AND WATER","2084":"MIAHONA LIMITED","2223":"SAUDI ARAMCO BASE","2281":"TANMIAH FOOD","2282":"NAQI WATER","2283":"THE FIRST MILLING","2284":"MODERN MILLS","2285":"ARABIAN MILLS FOR","2286":"FOURTH MILLING","2287":"ARABIAN FOR AGRICULTURAL","2288":"NOFOTH FOOD PRODUCTS","2381":"ARABIAN DRILLING","2382":"ADES","3092":"RIYADH CEMENT","4013":"DR. SULAIMAN AL","4014":"SCIENTIFIC AND MEDICAL","4015":"JAMJOOM PHARMACEUTICALS FACTORY","4016":"MIDDLE EAST PHARMACEUTICAL","4017":"DR. SOLIMAN ABDEL","4018":"ALMOOSA HEALTH","4019":"SPECIALIZED MEDICAL","4021":"CANADIAN GENERAL MEDICAL","4071":"ARABIAN CONTRACTING SERVICES","4072":"MBC","4081":"NAYIFAT FINANCE","4082":"MORABAHA MARINA FINANCING","4083":"UNITED INTERNATIONAL","4084":"DERAYAH FINANCIAL","4141":"AL-OMRAN INDUSTRIAL TRADING","4142":"RIYADH CABLES","4143":"AL TAISEER TALCO","4144":"RAOOM TRADING","4145":"AL OBEIKAN GLASS","4146":"GAS ARABIAN SERVICES","4147":"CONSOLIDATED GRUNENFELDER SAADY","4148":"ALWASAIL INDUSTRIAL","4161":"BINDAWOOD","4162":"ALMUNAJEM FOODS","4163":"AL-DAWAA MEDICAL SERVICES","4164":"NAHDI MEDICAL","4165":"AL MAJED FOR","4192":"AL-SAIF STORES FOR","4193":"NICE ONE BEAUTY","4194":"MARKETING HOME","4261":"THEEB RENT A","4262":"LUMI RENTAL","4263":"SAL SAUDI LOGISTICS","4264":"FLYNAS","4265":"CHERRY TRADING","4292":"ATAA EDUCATIONAL","4321":"ARABIAN CENTRES","4322":"RETAL URBAN DEVELOPMENT","4323":"SUMOU REAL ESTATE","4324":"BANAN REAL ESTATE","4325":"UMM AL QURA","4326":"DAR AL MAJED","4327":"AL RAMZ REAL","4328":"LADUN INVESTMENT","4348":"ALKHABEER REIT FUND","4349":"ALINMA HOSPITALITY REIT","4350":"ALISTITHMAR AREIC DIVERSIFIED","6013":"DEVELOPMENT WORKS FOOD","6014":"ALAMAR FOODS","6015":"AMERICANA RESTAURANTS INTERNATIONAL","6016":"SHATIRAH HOUSE RESTAURANT","6017":"JAHEZ INTERNATIONAL FOR","6018":"SPORT CLUBS","6019":"ALMASAR ALSHAMIL EDUCATION","6022":"ARMAH SPORTS","7200":"AL MOAMMAR INFORMATION","7202":"ARABIAN INTERNET AND","7203":"ELM","7204":"PERFECT PRESENTATION FOR","7205":"DAR ALBALAD FOR","7211":"SAUDI AZM FOR","8313":"RASAN INFORMATION TECHNOLOGY","2222":"ARAMCO"};Object.assign(NAMES,EXTRA_NAMES);   // listings after 2020 (Yahoo names), v14
function nameOf(s){return NAMES&&NAMES[s]?`${s} · ${NAMES[s]}`:s}
async function libMeta(){if(LIBMETA)return LIBMETA;try{const el=document.getElementById("tadawul-meta");LIBMETA=el?JSON.parse(el.textContent):await (await fetch("tadawul_meta.json")).json()}catch(e){LIBMETA={}}
 for(const [k,v] of Object.entries(LIBMETA))NAMES[k]=v.name;return LIBMETA}
async function libText(){if(LIBTEXT)return LIBTEXT;let bytes;const el=document.getElementById("tadawul-b64");
 if(el){const b=atob(el.textContent.trim());bytes=new Uint8Array(b.length);for(let i=0;i<b.length;i++)bytes[i]=b.charCodeAt(i)}
 else{const r=await fetch("tadawul_gz_base64.txt");if(!r.ok)throw new Error("library file not found");const b=atob((await r.text()).trim());bytes=new Uint8Array(b.length);for(let i=0;i<b.length;i++)bytes[i]=b.charCodeAt(i)}
 if(bytes[0]===0x1f&&bytes[1]===0x8b){if(typeof DecompressionStream==="undefined")throw new Error("This browser cannot unpack the library (needs a 2023+ Chrome, Edge, Safari or Firefox).");
  LIBTEXT=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}
 else LIBTEXT=new TextDecoder().decode(bytes);   // the host already decompressed it
 return LIBTEXT}
function libParse(text,want){const out={};let cur=null,s=null;
 for(const line of text.split("\n")){if(!line)continue;
  if(line[0]==="#"){const p=line.slice(1).split("|");cur=want.has(p[0])?p[0]:null;if(cur)s=out[cur]={d:[],o:[],h:[],l:[],c:[],v:[],src:"Tadawul library 2001–2020",lib:true};continue}
  if(!cur)continue;const f=line.split(",");s.d.push(`${f[0].slice(0,4)}-${f[0].slice(4,6)}-${f[0].slice(6,8)}`);s.o.push(+f[1]);s.h.push(+f[2]);s.l.push(+f[3]);s.c.push(+f[4]);s.v.push(f[5]===""?NaN:+f[5])}
 return out}
// newer wins where both have data; older history before the newer series starts is rescaled by the price ratio measured on the overlap
// (providers adjust past prices for bonus shares and splits as of the day you download, so two downloads differ by a constant factor)
function mergeSeries(base,newer){const bi=new Map(base.d.map((d,i)=>[d,i])),ratios=[];
 for(let j=0;j<newer.d.length&&ratios.length<10;j++){const i=bi.get(newer.d[j]);if(i!=null&&base.c[i]>0&&newer.c[j]>0)ratios.push(newer.c[j]/base.c[i])}
 let r=1,note="",ok=true;
 if(ratios.length>=5){const s=ratios.slice().sort((a,b)=>a-b);r=s[s.length>>1];const disp=ratios.map(x=>Math.abs(x/r-1)).sort((a,b)=>a-b)[ratios.length>>1];
  if(disp>0.01){ok=false;note=`the two sources disagree on the overlap (median gap ${(100*disp).toFixed(1)}%)`}else if(Math.abs(r-1)>0.003)note=`older history rescaled ×${r.toFixed(4)} for corporate actions since then`}
 else if(base.d[base.d.length-1]<newer.d[0])note=`no overlap with the older data: history before ${newer.d[0]} may be on a different price basis`;
 else note=`only ${ratios.length} overlapping days: older history kept unscaled`;
 const cut=newer.d[0],o={d:[],o:[],h:[],l:[],c:[],v:[]};
 for(let i=0;i<base.d.length&&base.d[i]<cut;i++){o.d.push(base.d[i]);o.o.push(base.o[i]*r);o.h.push(base.h[i]*r);o.l.push(base.l[i]*r);o.c.push(base.c[i]*r);o.v.push(isF(base.v[i])?base.v[i]/r:NaN)}
 for(let j=0;j<newer.d.length;j++){o.d.push(newer.d[j]);o.o.push(newer.o[j]);o.h.push(newer.h[j]);o.l.push(newer.l[j]);o.c.push(newer.c[j]);o.v.push(newer.v[j])}
 return {s:o,ratio:r,note,ok,overlap:ratios.length}}
function validateSeries(s){const w=[];let big=0,bad=0;for(let i=0;i<s.d.length;i++){if(i&&s.d[i]<=s.d[i-1])bad++;if(!(s.c[i]>0))bad++;if(i&&Math.abs(s.c[i]/s.c[i-1]-1)>.105)big++}
 if(bad)w.push(`${bad} bad rows`);if(big)w.push(`${big} daily moves above 10.5% (Saudi limit is ±10%; IPO days and old data can exceed it)`);return w}

// ---------- library UI
const LIB_KEY="qlab-lib";let LIBSEL=new Set(load(LIB_KEY,[]));
async function drawLibrary(){const m=await libMeta(),el=$("lib-t");if(!el)return;const ks=Object.keys(m);if(!ks.length){$("lib-note").textContent="Library file not available in this copy.";return}
 const sec=$("lib-sector").value,q=($("lib-q").value||"").toLowerCase();
 const rows=ks.filter(k=>(!sec||m[k].sector===sec)&&(!q||k.includes(q)||m[k].name.toLowerCase().includes(q)||m[k].full.toLowerCase().includes(q)));
 if(!$("lib-sector").dataset.ready){const secs=[...new Set(ks.map(k=>m[k].sector))].sort();$("lib-sector").innerHTML='<option value="">all sectors</option>'+secs.map(s=>`<option>${esc(s)}</option>`).join("");$("lib-sector").dataset.ready=1;$("lib-sector").value=sec}
 $("lib-note").innerHTML=`<b>${ks.length}</b> Tadawul stocks built in (daily prices 2001 → 2020-03-05, adjusted as of 2020). ${[...LIBSEL].filter(k=>DS[k]).length} loaded. Showing ${rows.length}, most traded first. Saudi stocks run in momentum mode (Settings).`;
 el.innerHTML="<tr><th></th><th>code</th><th>name</th><th>sector</th><th>from</th><th>to</th><th>median daily value (SAR m)</th></tr>"+rows.slice(0,400).map(k=>`<tr><td><input type="checkbox" data-lib="${k}" ${DS[k]?"checked":""} aria-label="select ${esc(k)}"></td><td>${k}</td><td style="text-align:left">${esc(m[k].name)}</td><td style="text-align:left">${esc(m[k].sector)}</td><td>${m[k].start}</td><td>${m[k].end}</td><td>${(m[k].value_med/1e6).toFixed(1)}</td></tr>`).join("")}
async function loadLibrary(codes,{quiet=false}={}){const want=new Set(codes.filter(Boolean));if(!want.size)return;$("lib-msg").textContent=`Unpacking ${want.size} stock(s)…`;
 try{const got=libParse(await libText(),want);await libMeta();const msgs=[];
  for(const [k,v] of Object.entries(got)){LIBSEL.add(k);
   if(DS[k]&&!DS[k].lib){const m=mergeSeries(v,DS[k]);DS[k]=Object.assign(m.s,{src:`library + ${DS[k].src||"your file"}`,lib:"merged",bad:0});msgs.push(`${k}: joined with your file (${m.note||"same price basis"})`)}
   else DS[k]=v}
  store(LIB_KEY,JSON.stringify([...LIBSEL]));applyAllUpdates(false);
  $("lib-msg").innerHTML=`Loaded ${Object.keys(got).length} stock(s).`+(msgs.length?"<br>"+msgs.map(esc).join("<br>"):"");
  if(!quiet){if(!DS[st.sym])st.sym=Object.keys(got)[0];saveDS();afterDataChange(true)}}
 catch(e){$("lib-msg").innerHTML=`<span class="err">${esc(e.message)}</span>`}}
function unloadLibrary(codes){for(const k of codes){LIBSEL.delete(k);if(DS[k]&&DS[k].lib===true)delete DS[k]}store(LIB_KEY,JSON.stringify([...LIBSEL]));saveDS();afterDataChange()}
// browser storage cannot hold 193 long histories: plain library series are reloaded from the built-in file instead of being saved
saveDS=function(){const keep={};for(const [k,v] of Object.entries(DS))if(v.lib!==true)keep[k]=v;
 if(store("qlab-ds",JSON.stringify(keep))===null&&Object.keys(keep).length)$("parsemsg").innerHTML='<span class="err">The browser would not store these files, so they will need reloading next visit.</span>'};

// ---------- updates written by the Claude Code session into this artifact's database (collection "bars": one document per symbol)
let DB=null,UPD={},UPDLOG={};
function updSeries(doc){const rows=doc.rows||[];const s={d:[],o:[],h:[],l:[],c:[],v:[]};
 for(const r of rows){const t=String(r[0]);if(t.length!==8)continue;s.d.push(`${t.slice(0,4)}-${t.slice(4,6)}-${t.slice(6,8)}`);s.o.push(+r[1]);s.h.push(+r[2]);s.l.push(+r[3]);s.c.push(+r[4]);s.v.push(r[5]==null?NaN:+r[5])}
 const ix=s.d.map((d,i)=>i).sort((a,b)=>s.d[a]<s.d[b]?-1:1),o={};for(const k of ["d","o","h","l","c","v"])o[k]=ix.map(i=>s[k][i]);return o}
const UPD_ALIAS={"2222":["ARAMCO","SAUDI ARAMCO","2222.SR"],"1120":["ALRAJHI","AL RAJHI","RAJHI","1120.SR"],"TASI":["^TASI","TASI.SR","^TASI.SR"]};
function applyUpdate(sym0){const doc=UPD[sym0];if(!doc)return false;let sym=sym0;
 if(!DS[sym])for(const a of UPD_ALIAS[sym0]||[])if(DS[a]){sym=a;break}
 if(!DS[sym]){if(LIBMETA&&LIBMETA[sym0]&&!LIBSEL.has(sym0))return false;const nw=updSeries(doc);if(nw.d.length<250)return false;
  DS[sym]=Object.assign(nw,{src:`update ${String(doc.fetched_at||"").slice(0,10)} (${doc.source||"?"})`,lib:"merged",updAt:doc.fetched_at,bad:0});UPDLOG[sym0]={note:"added from update",ok:true,w:validateSeries(nw),last:nw.d[nw.d.length-1],rows:nw.d.length};return true}
 if(DS[sym].updAt===doc.fetched_at)return false;
 const nw=updSeries(doc);if(nw.d.length<5){UPDLOG[sym0]={note:"too few rows",ok:false};return false}
 const w=validateSeries(nw),m=mergeSeries(DS[sym],nw);
 if(!m.ok&&m.overlap>=5){UPDLOG[sym0]={note:`not applied: ${m.note}`,ok:false,w};return false}
 const lastOld=DS[sym].d[DS[sym].d.length-1];
 if(m.overlap<5&&(Date.parse(nw.d[0])-Date.parse(lastOld))/864e5>30){DS[sym]=Object.assign(nw,{src:`update ${String(doc.fetched_at||"").slice(0,10)} (${doc.source||"?"})`,lib:"merged",updAt:doc.fetched_at,bad:0});
  UPDLOG[sym0]={note:`older history ends ${lastOld} and the new source starts ${nw.d[0]}: using the new history only (not joined across the gap)`,ok:true,w,last:nw.d[nw.d.length-1],rows:nw.d.length};return true}
 DS[sym]=Object.assign(m.s,{src:`${DS[sym].src||""} + update ${String(doc.fetched_at||"").slice(0,10)} (${doc.source||"?"})`,lib:"merged",updAt:doc.fetched_at,bad:0});
 UPDLOG[sym0]={note:m.note||"appended",ok:true,w,last:nw.d[nw.d.length-1],rows:nw.d.length};return true}
function applyAllUpdates(run=true){let n=0;for(const k of Object.keys(UPD))if(applyUpdate(k))n++;drawUpdates();if(n&&run){saveDS();afterDataChange()}return n}
function drawUpdates(){const el=$("upd-t");if(!el)return;const ks=Object.keys(UPD).sort();
 el.innerHTML=ks.length?"<tr><th>symbol</th><th>rows</th><th>to</th><th>source</th><th>fetched</th><th>result</th></tr>"+ks.map(k=>{const d=UPD[k],lg=UPDLOG[k]||{},rows=(d.rows||[]).length,last=rows?String(d.rows[d.rows.length-1][0]):"";
  return `<tr><td>${esc(nameOf(k))}</td><td>${rows}</td><td>${last?`${last.slice(0,4)}-${last.slice(4,6)}-${last.slice(6,8)}`:"—"}</td><td style="text-align:left">${esc(d.source||"")}</td><td>${esc(String(d.fetched_at||"").slice(0,16))}</td><td style="text-align:left" class="${lg.ok===false?"down":""}">${DS[k]||lg.ok!=null?esc(lg.note||"applied"):"stored (load the stock to use it)"}${lg.w&&lg.w.length?` · ${esc(lg.w.join("; "))}`:""}</td></tr>`}).join(""):'<tr><td class="empty">No updates stored yet.</td></tr>'}
(async()=>{try{if(!window.claude||!claude.use)return;DB=await claude.use("db");if(!DB)return;
 DB.collection("bars").onSnapshot(snap=>{for(const d of snap.docs){const b=d.data();if(b)UPD[d.id]=b}applyAllUpdates(true)},e=>{$("upd-msg").textContent="Update store unavailable: "+e.code});
 DB.collection("ml").onSnapshot(snap=>{for(const d of snap.docs)if(d.id==="latest"){MLPF=d.data();try{drawML()}catch(e){};try{if(RES)drawPlan()}catch(e){}}},()=>{});
 DB.collection("runs").orderBy("started","desc").limit(5).onSnapshot(snap=>{const r=snap.docs[0]&&snap.docs[0].data();if(!r)return;
  const el=$("upd-run");el.innerHTML=`Last update run <b>${esc(snap.docs[0].id)}</b>: <b class="${r.state==="done"?"up":r.state==="blocked"||r.state==="failed"?"down":""}">${esc(r.state||"?")}</b> ${r.done!=null?`· ${r.done}/${r.total} symbols`:""} · ${esc(r.message||"")}`
   +(r.state==="blocked"?`<br><span class="acc">Fix: open claude.ai/code → your environment (${esc(r.environment||"Default")}) → Edit → Network access → Custom, add <b>${esc(r.host||"query1.finance.yahoo.com")}</b> under Allowed domains (keep the default list), save, then press Update again.</span>`:"")},()=>{});
 document.querySelectorAll(".db-only").forEach(e=>e.hidden=false)}catch(e){}})();

// ---------- the "Update data" button: start a Claude Code session (your account, your usage) that fetches real prices and writes them here
let MCP=null;
(async()=>{try{if(!window.claude||!claude.use)return;MCP=await claude.use("mcp");if(MCP)document.querySelectorAll(".mcp-only").forEach(e=>e.hidden=false),document.querySelectorAll(".mcp-off").forEach(e=>e.hidden=true)}catch(e){}})();
const MCP_ERR={server_not_connected:`The "${CCR}" connector is not available for your account here.`,needs_reauth:`Reconnect "${CCR}" in claude.ai Settings → Connectors.`,not_in_manifest:"Claude Code access is turned off for this page. Open the page's Permissions menu (top of the artifact view), allow \"Claude Code Remote\", then reload and press \"Ask for Claude Code access\".",
 blocked_by_policy:"Your account blocks pages from starting Claude Code sessions, so updates run from the Routine \"QuantLab daily data update\" instead: it runs Sunday to Thursday after the market close, and you can start it any time from the Claude app (Routines → QuantLab daily data update → Run now). Results appear here automatically.",approval_required:"Your organization requires approval for this action.",selection_required:"Choose which Claude Code connector to use in the prompt Claude showed, then try again.",
 tool_error:"Claude Code refused the request: ",server_unavailable:"Claude Code did not answer in time; try again in a minute.",not_granted:"This view cannot use connectors.",capability_disabled:"This view cannot use connectors."};
const mcpErr=e=>(MCP_ERR[e&&e.code]||"Could not reach Claude Code: ")+(e&&(e.code==="tool_error"||!MCP_ERR[e.code])?String(e.message||e.code||e).slice(0,200):"");
async function loadEnvs(){if(!MCP)return;const sel=$("upd-env");sel.innerHTML="<option>loading…</option>";
 try{const r=await MCP.callTool(CCR,"list_environments",{limit:20});const envs=((r.payload||{}).environments)||[];
  sel.innerHTML=envs.length?envs.map(e=>`<option value="${esc(e.environment_id)}">${esc(e.name||"environment")} · ${esc((e.description||"").slice(0,40))} · …${esc(e.environment_id.slice(-6))}</option>`).join(""):"<option value=''>no environments</option>"}
 catch(e){sel.innerHTML="<option value=''>unavailable</option>";$("upd-msg").innerHTML=`<span class="err">${esc(mcpErr(e))}</span>`}}
function updatePrompt(runId,last){
 const list=Object.entries(last).map(([k,d])=>`${k}: ${d}`).join(", ");
 return `You are the data updater for the user's QuantLab terminal (a Claude artifact). The user started you from the terminal's "Update data" button. Use real market data only.

TASK: bring daily OHLCV price history up to date for these Saudi (Tadawul) symbols and store it in the terminal's database.
Artifact: ${ART_URL}
Write with the ArtifactData tool (load it first with ToolSearch, query "select:ArtifactData"), using the artifact URL above.
Every write to a document that already exists needs its current version: read it first ("get", or "list" the collection) and pass that version as if_version (in a "batch", on each entry). Documents that do not exist yet are written without it.
Run id: ${runId}
Symbols (code: last date the terminal already has): ${list}

STEPS
1. The terminal already created document runs/${runId} (collection "runs", doc id "${runId}", state "starting"). Read it, then update it (with if_version) to {state:"running", started:"<ISO now>", total:<number of symbols>, done:0, errors:[], message:"fetching"}.
2. For each symbol download daily bars from 400 calendar days before its last date up to today. Preferred source, the Yahoo Finance chart API, e.g.
   curl -s -A "Mozilla/5.0" "https://query1.finance.yahoo.com/v8/finance/chart/1120.SR?period1=<unix start>&period2=<unix now>&interval=1d&events=div%2Csplit&includeAdjustedClose=true"
   (the TASI index is ^TASI.SR). Scale open, high and low by adjclose/close and use adjclose as the close. Drop days without a close.
   If Yahoo is not reachable you may use another provider that returns machine-readable daily history (CSV or JSON) for Tadawul stocks.
   NEVER take prices from search-result summaries, news text or memory, and never estimate missing days.
3. Validate each symbol: dates ascending and unique, close > 0, high >= max(open, close), low <= min(open, close). Note daily moves above 10.5% (the Tadawul limit is ±10%) as warnings.
4. Write one document per symbol into collection "bars" with doc id = the symbol code exactly as listed: {sym, source:"<provider and URL pattern>", fetched_at:"<ISO time>", adjusted:true, run:"${runId}", rows:[[YYYYMMDD, open, high, low, close, volume], ...], warnings:[...]}; YYYYMMDD as an integer, prices rounded to 4 decimals, oldest row first. Keep each document under 250 KB (drop the oldest rows if needed). Prefer one "batch" call per 10 symbols (write the JSON to a local file and pass file_path if it is large).
5. After every 10 symbols update runs/${runId} {done, message}. At the end set state "done" (or "partial", with errors naming each failed symbol and why).
6. If the data source is blocked by the network policy (HTTP 403 from the proxy, "egress blocked", "CONNECT tunnel failed"), do not look for prices elsewhere on the web: set runs/${runId} {state:"blocked", host:"<the blocked host>", message:"The cloud environment's network policy blocks <host>."} and stop.
Do nothing else: no repository changes, no other artifacts, no messages to anyone.`}
async function startUpdate(){if(!MCP){$("upd-msg").textContent="Open this page inside Claude to use this button.";return}
 const scope=$("upd-scope").value,env=$("upd-env").value,model=$("upd-model").value.trim()||"claude-opus-5-5";
 if(!env){$("upd-msg").innerHTML='<span class="err">Choose a Claude Code environment first.</span>';return}
 const syms=scope==="all"?Object.keys(await libMeta()).concat(Object.keys(DS).filter(k=>saudiSym(k))):Object.keys(DS);const uniq=[...new Set(syms)].filter(k=>/^\d{4}$/.test(k)||k==="TASI");
 if(!uniq.length){$("upd-msg").innerHTML='<span class="err">No Saudi symbols to update: load stocks from the library or upload files first.</span>';return}
 const last={};for(const k of uniq){const d=DS[k];last[k]=d?d.d[d.d.length-1]:((LIBMETA||{})[k]||{}).end||"2020-03-05"}
 const runId="run-"+new Date().toISOString().slice(0,16).replace(/[-:T]/g,"")+"-"+Math.random().toString(36).slice(2,6);
 $("upd-go").disabled=true;$("upd-msg").textContent=`Starting a ${model} session for ${uniq.length} symbol(s)…`;
 try{if(DB)await DB.doc("runs/"+runId).set({state:"starting",started:new Date().toISOString(),total:uniq.length,done:0,message:"session starting",environment:$("upd-env").selectedOptions[0].textContent.split(" · ")[0]});
  let r;const args={environment_id:env,prompt:updatePrompt(runId,last),title:`QuantLab data update ${new Date().toISOString().slice(0,10)}`,model,tags:["quantlab-update"]};
  try{r=await MCP.callTool(CCR,"create_session",Object.assign({permission_mode:"auto"},args))}catch(e){if(e&&e.code==="tool_error")r=await MCP.callTool(CCR,"create_session",args);else throw e}
  const pl=r.payload||{},sid=(typeof pl==="object"&&((pl.ccr&&pl.ccr.id)||pl.session_id||pl.id||(pl.session&&pl.session.id)))||(JSON.stringify(r.payload||r.content||"").match(/\bsession_(?!id\b)[A-Za-z0-9]{6,}/)||[""])[0];
  $("upd-msg").innerHTML=`Session started${sid?` (<a href="https://claude.ai/code/${esc(sid)}" target="_blank" rel="noopener">${esc(sid)}</a>)`:""}. It fetches the prices and writes them here; new bars appear below and in the charts automatically. A full library update can take 10–30 minutes.`}
 catch(e){$("upd-msg").innerHTML=`<span class="err">${esc(mcpErr(e))}</span>`}
 finally{$("upd-go").disabled=false}}

// ---------- wiring
$("lib-sector").addEventListener("change",drawLibrary);$("lib-q").addEventListener("input",()=>{clearTimeout(drawLibrary.t);drawLibrary.t=setTimeout(drawLibrary,200)});
$("lib-t").addEventListener("change",e=>{const k=e.target.dataset.lib;if(!k)return;if(e.target.checked)loadLibrary([k]);else unloadLibrary([k])});
$("lib-top30").addEventListener("click",async()=>{const m=await libMeta();loadLibrary(Object.keys(m).slice(0,30))});
$("lib-shown").addEventListener("click",()=>loadLibrary([...document.querySelectorAll("#lib-t input[data-lib]")].map(x=>x.dataset.lib)));
$("lib-none").addEventListener("click",()=>unloadLibrary([...LIBSEL]));
async function permState(){try{const P=await claude.use("permissions");if(!P)return "unavailable";return await P.state("mcp:"+CCR)}catch(e){return "unavailable"}}
async function showPerm(){const st=await permState(),el=$("upd-perm");if(!el)return;
 el.innerHTML=st==="granted"?'<span class="up">Claude Code access: allowed.</span>':st==="prompt"?'Claude Code access: not asked yet (you will be asked on the first use).':
  st==="denied"?'<span class="down">Claude Code access is blocked for this page.</span> To undo: open this artifact\'s <b>Permissions</b> menu at the top of the artifact view and allow "Claude Code Remote", then reload the page and press "Ask for Claude Code access".':'Claude Code access: not available in this view.'}
async function askPerm(){try{const P=await claude.use("permissions");if(P)await P.request(["mcp:"+CCR])}catch(e){}showPerm()}
$("upd-go").addEventListener("click",startUpdate);$("upd-ask").addEventListener("click",askPerm);setTimeout(showPerm,1500);$("upd-envs").addEventListener("click",loadEnvs);
(async()=>{await libMeta();drawLibrary();renderSymSelect();if(LIBSEL.size)await loadLibrary([...LIBSEL],{quiet:true}).then(()=>afterDataChange())})();

// ---------- v14: Saudi ML monthly portfolio (models trained offline on 270 stocks; picks written to collection "ml", doc "latest")
let MLPF=null;
function drawML(){const box=$("ml-box");if(!box||!MLPF||!MLPF.picks)return;box.hidden=false;const inv=MLPF.pm>0,S=MLPF.summary||{};
 const age=Math.round((Date.now()-Date.parse(MLPF.date))/864e5);
 $("ml-note").innerHTML=`<b>Strategy:</b> once a month buy the 10 highest-ranked stocks (equal weight, buy at the open, liquid names only: 60-day median traded value ≥ SAR 3m) and hold for 20 trading days, <b>only when the market model's 20-day forecast is positive</b>; otherwise stay in cash. Walk-forward test 2013–2026 (each year predicted by a model trained only on earlier years, 0.40% round-trip costs): <b>${(100*S.cagr_avg_offsets).toFixed(1)}% a year, Sharpe ${S.sharpe}, worst drawdown ${(100*S.maxdd).toFixed(0)}%</b> vs the market ${(100*S.mkt_cagr).toFixed(1)}% a year with ${(100*S.mkt_maxdd).toFixed(0)}%. Results varied from about +9% to +20% a year depending on which day of the month you rebalance.<br>
 <b>Today (${esc(MLPF.date)}${age>3?`, ${age} days ago`:""}): market model ${inv?'<span class="up">INVESTED':'<span class="down">CASH'}</span></b> (20-day market forecast ${spct(MLPF.pm,2)}; positive on ${Math.round(100*Object.values(MLPF.pm_hist||{}).filter(v=>v>0).length/Math.max(1,Object.keys(MLPF.pm_hist||{}).length))}% of the last 60 sessions). ${inv?"Buy the top 10 at the next open.":"The ranking below is what it would buy; wait for the market model to turn positive."}<br>
 <b>Signal filter:</b> Saudi momentum signals in the plan are taken only for stocks in the ML top 30%${(ECFG.mlf||"on")==="on"?" while the market model is positive":""} (Settings → Saudi ML filter: ${esc(ECFG.mlf||"on")}); Saudi dip-buy signals are skipped. 2013–2026 test: momentum +0.08% net per trade unfiltered, +0.65% filtered.<br><span class="note">What the model learned: it prefers calm stocks (low volatility, no lottery-style spikes) in long-term uptrends (near 52-week highs, positive 12-month momentum, above the 200-day average) that paused in the last few days. Columns show the stock's percentile among ${MLPF.universe} liquid stocks (100 = highest).</span>`;
 const P=x=>isF(x)?Math.round(100*x):"—";
 $("ml-t").innerHTML="<tr>"+["rank","stock","model score","median daily value","near 52w high","12-month momentum","volatility (low = calm)","last 5 days","vs 200-day avg","action"].map(h=>`<th>${h}</th>`).join("")+"</tr>"+MLPF.picks.slice(0,20).map(p=>`<tr><td>${p.rank}</td><td><b>${esc(nameOf(p.sym))}</b></td><td>${p.score.toFixed(3)}</td><td>SAR ${p.val_m}m</td><td>${P(p.hi52)}</td><td>${P(p.mom12_1)}</td><td>${P(p.vol60)}</td><td>${P(p.r5)}</td><td>${P(p.dma200)}</td><td>${p.rank<=10?(inv?'<span class="up">buy / hold</span>':'<span class="note">top 10 (cash for now)</span>'):'<span class="note">reserve</span>'}</td></tr>`).join("");
 const rec=MLPF.record||{};$("ml-rec").innerHTML="<tr><th>year</th>"+Object.keys(rec).map(y=>`<th>${y}</th>`).join("")+"</tr><tr><td>ML strategy</td>"+Object.values(rec).map(v=>`<td class="${cl(v[0])}">${spct(v[0],0)}</td>`).join("")+"</tr><tr><td>market</td>"+Object.values(rec).map(v=>`<td class="${cl(v[1])}">${spct(v[1],0)}</td>`).join("")+"</tr><tr><td>time invested</td>"+Object.values(rec).map(v=>`<td>${Math.round(100*v[2])}%</td>`).join("")+"</tr>"}

// ---------- v14: ML filter for Saudi momentum / reversal signals (uses ml/latest ranks)
function mlGate(sym){const mode=ECFG.mlf||"on";if(!MLPF||!MLPF.ranks)return {ok:true,why:"ML ranking not loaded",pct:NaN};
 const age=(Date.now()-Date.parse(MLPF.date))/864e5;if(age>45)return {ok:true,why:"ML ranking is stale",pct:NaN};
 const pct=MLPF.ranks[sym];if(!isF(pct))return {ok:false,why:"not in the ML ranking (too illiquid or too new)",pct:NaN};
 if(pct<.7)return {ok:false,why:`ML rank ${Math.round(100*pct)}th percentile, below the top 30%`,pct};
 if(mode==="on"&&!(MLPF.pm>0))return {ok:false,why:`market model negative (20-day forecast ${spct(MLPF.pm,1)})`,pct};
 return {ok:true,why:"",pct,mkt:MLPF.pm>0}}

// ---------- v14: Saudi Core Strategy = ML sleeve (4 weekly tranches of the top 10) + trend sleeve (55-day breakouts, ML top 30%, 3-ATR trailing stop), both only while the market model is positive
function coreRows(){if(!RES)return [];const out=[];
 for(const sym of RES.syms){if(!saudiSym(sym)||/^TASI/i.test(sym))continue;const s=SY(sym);if(!s||s.d.length<220)continue;const i=s.d.length-1,c=s.c[i];
  let hi=-1e99;for(let k=i-54;k<=i;k++)hi=Math.max(hi,s.c[k]);let m=0;for(let k=i-199;k<=i;k++)m+=s.c[k];m/=200;
  let a=0,n=0;for(let k=i-19;k<=i;k++){const tr=Math.max(s.h[k]-s.l[k],Math.abs(s.h[k]-s.c[k-1]),Math.abs(s.l[k]-s.c[k-1]));if(isF(tr)){a+=tr;n++}}a=n?a/n:NaN;
  const pct=MLPF&&MLPF.ranks?MLPF.ranks[sym]:NaN;  out.push({sym,s,i,c,hi,sma:m,atr:a,pct,brk:c>=hi&&c>m,up:c>m,date:s.d[i]})}
 return out.sort((x,y)=>(y.brk-x.brk)||((isF(y.pct)?y.pct:-1)-(isF(x.pct)?x.pct:-1)))}
function drawCore(){const box=$("core-box");if(!box)return;if(!MLPF){box.hidden=true;return}box.hidden=false;const on=MLPF.pm>0,R=coreRows();
 const top10=(MLPF.picks||[]).slice(0,10).map(p=>esc(nameOf(p.sym))).join(", ");
 $("core-note").innerHTML=`<b>How it works</b> (one account, swing trades only, decisions at the close, orders at the next open):<br>
 <b>1 · ML sleeve:</b> the account is split into 4 tranches of 25%. Every 5 trading days one tranche is re-invested in the current ML top 10 (equal weight, about 2.5% of the account per stock) and held 20 trading days; if the market model is negative that tranche goes to cash instead.<br>
 <b>2 · Trend sleeve:</b> buy a stock (10% of the account, at most 10) when it closes at its 55-day high, above its 200-day average, ranks in the ML top 30% and the market model is positive. Exit at the next open after a close below (highest close since entry − 3 × ATR20). If both sleeves together would exceed 100%, scale them down.<br>
 <b>Cash</b> (most of the time) goes to a money-market or sukuk fund. <b>Long-term Z</b> (250-day, chart panel) is context: a turn back above −2.5 is flagged as a small-size deep-value watch, not part of the tested strategy.<br>
 <b>Test 2013–2026</b> (walk-forward, 0.40% costs, cash at T-bill rates): <b>+19.6% a year, volatility 12%, Sharpe 1.55, worst drawdown −17%, no losing calendar year</b> (market: +1.7% a year, −55%). 2013–19 +13.6% (Sharpe 1.18), 2020–26 +26.4% (Sharpe 1.91). At 1% costs: +15.8%; without 2020: +16.4%. Caveats: survivorship (stocks delisted before 2026 are missing), filters partly chosen with the whole period in view, not yet traded live.<br>
 <b>Now (${esc(MLPF.date)}): market model ${on?'<span class="up">POSITIVE: both sleeves active':'<span class="down">NEGATIVE: hold cash, no new positions'}</span></b> (20-day forecast ${spct(MLPF.pm,1)}). ML sleeve list: ${top10}.`;
 $("core-t").innerHTML=R.length?"<tr>"+["stock","close","trend-sleeve signal today","55-day high (buy trigger: close at or above)","200-day avg","ML rank","stop if bought now (close − 3 ATR)","in ML top 10?"].map(h=>`<th>${h}</th>`).join("")+"</tr>"+R.map(r=>{
  const okml=isF(r.pct)&&r.pct>=.7,inTop=(MLPF.picks||[]).slice(0,10).some(p=>p.sym===r.sym),sig=r.brk&&okml;
  return `<tr data-s="${esc(r.sym)}"><td><b>${esc(nameOf(r.sym))}</b> <span class="note">${r.date}</span></td><td>${fp(r.c)}</td><td>${sig?(on?'<span class="up">BUY at next open</span>':'<span class="note">signal, but market model negative</span>'):r.brk?'<span class="note">breakout, ML rank too low</span>':'—'}</td>
   <td>${fp(r.hi)}</td><td class="${r.up?"up":"down"}">${fp(r.sma)}</td><td class="${okml?"up":""}">${isF(r.pct)?Math.round(100*r.pct)+"th":"—"}</td><td>${isF(r.atr)?fp(r.c-3*r.atr):"—"}</td><td>${inTop?(on?'<span class="up">yes: buy/hold</span>':'yes (cash for now)'):"—"}</td></tr>`}).join(""):'<tr><td class="empty">Load Saudi stocks (Data tab → Tadawul library, or upload files) to see trend-sleeve signals.</td></tr>'}
{const _dc=drawCore;drawCore=function(){_dc.apply(this,arguments);const el=$("core-rec");if(!el||!MLPF||!MLPF.record)return;const rec=MLPF.record;
 el.innerHTML="<tr><th>ML sleeve by year</th>"+Object.keys(rec).map(y=>`<th>${y}</th>`).join("")+"</tr><tr><td>ML sleeve</td>"+Object.values(rec).map(v=>`<td class="${cl(v[0])}">${spct(v[0],0)}</td>`).join("")+"</tr><tr><td>market</td>"+Object.values(rec).map(v=>`<td class="${cl(v[1])}">${spct(v[1],0)}</td>`).join("")+"</tr><tr><td>time invested</td>"+Object.values(rec).map(v=>`<td>${Math.round(100*v[2])}%</td>`).join("")+"</tr>"}}
{const _dm=drawML;drawML=function(){_dm.apply(this,arguments);try{drawCore()}catch(e){}}}
{const _dp2=drawPlan;drawPlan=function(){_dp2.apply(this,arguments);try{drawCore()}catch(e){}}}
