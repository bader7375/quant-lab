"""v32 -> v33 (2026-11-13): Industry Z panel (round 72, H3). The average stretch Z of the OTHER liquid stocks of the same industry
(at least 3; liquid = 120+ bars and a 60-day median traded value of SAR 3m or more; industries as in strat/sectors.py, the same groups as
the sector view), computed in the browser from the stored daily bars (collection "bars", from 2019). Shown as a chart panel under Market
momentum (with the stock's own stretch Z dotted for comparison), in the legend, and in the Z-touch plan text. Context only: the live rule
is unchanged (round 72: no helper passed the account test)."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
p = "index.html"; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:90], s.count(old)); s = s.replace(old, new)
rep("reversal edge v32 · Saudi + US scanner · Z score plan with its plan book", "reversal edge v33 · Saudi + US scanner · Z score plan with its plan book · Industry Z")
rep("ms:true,zl:false,vol:true,reg:false,fear:false},UI.pn||{});", "ms:true,iz:true,zl:false,vol:true,reg:false,fear:false},UI.pn||{});")
rep('["ms","Market momentum (dip-buy gate)"],', '["ms","Market momentum (dip-buy gate)"],["iz","Industry Z (whole industry stretched?)"],')
rep('!(k==="ms"&&!msOn(st.sym))', '!((k==="ms"||k==="iz")&&!msOn(st.sym))&&!(k==="iz"&&!izCode(st.sym))')
# ---- the computation (after msZone)
rep("function msZone(v){", r"""// ---------- v33 (round 72, H3): Industry Z = the average stretch Z of the OTHER liquid stocks in the same industry (at least 3), computed here
// from the stored daily bars (collection "bars", from 2019). Liquid = 120+ bars and a 60-day median traded value of SAR 3m or more (as the scanner).
// Industries: the sector view's groups (ml/sectors), else the same code rules as the research (strat/sectors.py). Context only: not part of the rule.
const IZ_SELL=-1.0,IZ_CALM=-0.5,IZ_MIN=3,IZ_VAL=3e6,IZ_BANKS=new Set([1010,1020,1030,1050,1060,1080,1120,1140,1150,1180]);let IZC={},IZ_T=0,IZH=null;
function indOf(code){const k=String(code);try{if(typeof SECT!=="undefined"&&SECT&&SECT.groups&&SECT.groups[k])return SECT.groups[k]}catch(e){}
 if(!/^\d{4}$/.test(k))return null;const c=+k,inn=(...a)=>a.includes(c);let meta=null;try{meta=LIBMETA&&LIBMETA[k]||null}catch(e){}const sec=meta&&meta.sector||null;
 if(IZ_BANKS.has(c))return "Banks";if(c>=8000&&c<8400)return "Insurance";if(inn(1111,1182,1183,4130,4280,2120)||(c>=4080&&c<=4084))return "Diversified Financials";
 if(c>=3000&&c<3100)return "Cement";if(c>=4330&&c<=4350)return "REITs";if(c>=7010&&c<=7040)return "Telecom";if(c>=7200&&c<7300)return "Software & IT";
 if(inn(2222,2030,2380,2381,2382,2223,4030,4200))return "Energy";if(inn(5110,2080,2081,2082,2083,2084))return "Utilities";
 if(sec==="Health Care"||(!meta&&c>=4013&&c<=4021))return "Health Care";
 if(sec==="Materials"||(c>=1200&&c<1400)||inn(2001,2010,2020,2060,2170,2210,2250,2290,2310,2330,2350))return "Petrochem & Materials";
 if(sec==="Consumer Staples"||(c>=6000&&c<=6100)||(c>=2280&&c<=2288)||inn(2050,2270,2100,4001,4061,4160,4161,4162,4163,4164))return "Food & Staples";
 if(sec==="Real Estate"||(c>=4300&&c<4330)||inn(4020,4090,4100,4150,4220,4230,4250))return "Real Estate";
 if(sec==="Industrials"||inn(4031,4040,4260,4261,4262,4263,4264,4265,4110,4140,4141,4142,4143,4144,4145,4146,4147,4148,1212,1213,1214,2040,2110,2160,2320,2360,2370))return "Industrials & Transport";
 if(sec==="Communication Services")return "Media";return "Consumer & Retail"}
function izCode(sym){const k=String(sym||"");if(/^\d{4}$/.test(k))return k;try{for(const [c,a] of Object.entries(UPD_ALIAS))if(a.includes(k))return c}catch(e){}return null}
function izMed60(x){const n=x.length,o=new Array(n).fill(NaN),w=[],lb=(a,v)=>{let lo=0,hi=a.length;while(lo<hi){const m=(lo+hi)>>1;if(a[m]<v)lo=m+1;else hi=m}return lo};
 for(let i=0;i<n;i++){const v=x[i];if(isF(v))w.splice(lb(w,v),0,v);if(i>=60){const u=x[i-60];if(isF(u))w.splice(lb(w,u),1)}const m=w.length;if(m>=20)o[i]=m%2?w[(m-1)>>1]:(w[m/2-1]+w[m/2])/2}return o}
// market holidays as the research panel finds them: calendar days when fewer than 30% of the usual number of stocks traded are dropped
function izHol(){const ks=Object.keys(UPD).filter(k=>/^\d{4}$/.test(k));let nr=0,mx="";for(const k of ks){const d=UPD[k];nr+=(d.rows||[]).length;const f=String(d.fetched_at||"");if(f>mx)mx=f}
 const stamp=ks.length+"|"+nr+"|"+mx;if(IZH&&IZH.stamp===stamp)return IZH;const cnt=new Map();
 for(const k of ks)for(const r of UPD[k].rows||[]){const t=+r[0];if(!cnt.has(t))cnt.set(t,0);if(r[5]>0&&r[4]>0)cnt.set(t,cnt.get(t)+1)}
 const ds=[...cnt.keys()].sort((a,b)=>a-b),c=ds.map(t=>cnt.get(t)),hol=new Set();
 for(let i=0;i<ds.length;i++){const w=c.slice(Math.max(0,i-10),i+11).sort((a,b)=>a-b),L=w.length,m=L%2?w[(L-1)>>1]:(w[L/2-1]+w[L/2])/2;if(m>=5&&c[i]<.3*m)hol.add(ds[i])}
 return IZH={stamp,hol}}
function izPeer(k){const doc=UPD[k];if(!doc||!Array.isArray(doc.rows)||doc.rows.length<130)return null;const HL=izHol(),at=String(doc.fetched_at||"")+"|"+doc.rows.length+"|"+HL.stamp,o=IZC[k];if(o&&o.at===at)return o;
 const s=updSeries({rows:doc.rows.filter(r=>!HL.hol.has(+r[0]))}),n=s.d.length,tc=s.c.map((c,i)=>isF(c)&&c>0&&isF(s.v[i])&&s.v[i]>0?c:NaN);   // a stock's own non-trading days (suspensions) are gaps, as in the research panel
 const z=stretchZ(tc),med=izMed60(tc.map((c,i)=>isF(c)?c*s.v[i]:NaN)),liq=new Array(n);let cnt=0;
 for(let i=0;i<n;i++){if(isF(tc[i]))cnt++;liq[i]=isF(tc[i])&&cnt>=120&&med[i]>=IZ_VAL}return IZC[k]={at,d:s.d,z,liq}}
function izSeries(sym,dates){const code=izCode(sym);if(!code)return null;const g=indOf(code);if(!g)return null;
 const peers=Object.keys(UPD).filter(k=>k!==code&&/^\d{4}$/.test(k)&&indOf(k)===g),acc=new Map();
 for(const k of peers){const P=izPeer(k);if(!P)continue;for(let i=0;i<P.d.length;i++)if(P.liq[i]&&isF(P.z[i])){const a=acc.get(P.d[i]);if(a){a[0]+=P.z[i];a[1]++}else acc.set(P.d[i],[P.z[i],1])}}
 const v=new Array(dates.length).fill(NaN),nn=new Array(dates.length).fill(0);
 for(let i=0;i<dates.length;i++){const a=acc.get(dates[i]);if(a){nn[i]=a[1];if(a[1]>=IZ_MIN)v[i]=a[0]/a[1]}}return {g,v,n:nn,peers:peers.length}}
function izZone(v){return !isF(v)?null:v<=IZ_SELL?{txt:"the whole industry is selling",col:"#4fd1a5"}:v>IZ_CALM?{txt:"the industry is calm",col:"#e6a667"}:{txt:"the industry is partly weak",col:"#c3c2b7"}}
function izNote(i){if(!ARR||!ARR.izArr)return "";const v=ARR.izArr[i];if(!isF(v))return "";const n=ARR.izN?ARR.izN[i]:0;
 return ` <b>Industry Z ${fmt(v,2)}</b> (${esc(ARR.izG||"its industry")}, ${n} other liquid stocks): `+(v<=IZ_SELL?"the whole industry is selling. In round 72 such dips earned 5 to 10 points more per trade during sell-offs. Context only: the live rule does not use it."
  :v>IZ_CALM?"the industry is calm, so this drop is the stock's own. Such dips did worse in round 72 (few cases). Context only.":"the industry is partly weak (between −1.0 and −0.5). Context only.")}
function izOnUpdate(){clearTimeout(IZ_T);IZ_T=setTimeout(()=>{try{if(chart&&UI.pn.iz&&msOn(st.sym)&&(!UI.tf||UI.tf==="D"))refreshOverlays(chart.timeScale().getVisibleLogicalRange())}catch(e){}},1200)}
function msZone(v){""")
# ---- the pane
rep(" if(UI.pn.zl){P.zl=pane++;", """ if(UI.pn.iz&&msOn(st.sym)&&izCode(st.sym)){P.iz=pane++;SER.iz=chart.addSeries(LW.BaselineSeries,{baseValue:{type:"price",price:IZ_SELL},lineWidth:2,priceLineVisible:false,lastValueVisible:true,title:"industry Z",topLineColor:"#e8e6dc",topFillColor1:"rgba(232,230,220,.05)",topFillColor2:"rgba(232,230,220,0)",bottomLineColor:"#4fd1a5",bottomFillColor1:"rgba(79,209,165,.05)",bottomFillColor2:"rgba(79,209,165,.32)",priceFormat:{type:"price",precision:2,minMove:.01}},P.iz);
  SER.izs=line("rgba(79,150,240,.8)",{lineWidth:1,title:"stock Z",lastValueVisible:true,priceFormat:{type:"price",precision:2,minMove:.01}},P.iz);
  for(const [p,c,t] of [[IZ_SELL,"rgba(79,209,165,.9)","−1.0 selling"],[IZ_CALM,"rgba(230,166,103,.9)","−0.5 calm"]])SER.iz.createPriceLine({price:p,color:c,lineWidth:1,lineStyle:LW.LineStyle.Dashed,axisLabelVisible:true,title:t})}
 if(UI.pn.zl){P.zl=pane++;""")
rep('const DKEYS=["zbd","zb0","zs","ztm","vz","ms",', 'const DKEYS=["zbd","zb0","zs","ztm","vz","ms","iz","izs",')
rep('A.ms=L(A.msArr);for(let k=0;k<6;k++)A["zq"+k]=L(s&&s.zq[k]);',
    'A.ms=L(A.msArr);\n {A.izArr=new Array(n).fill(NaN);A.izN=null;A.izG=null;A.izPeers=0;if(UI.pn.iz&&msOn(st.sym)){try{const R=izSeries(st.sym,d.d);if(R){A.izArr=R.v;A.izN=R.n;A.izG=R.g;A.izPeers=R.peers}}catch(e){}}A.iz=L(A.izArr);A.izs=L(A.zsArr)}\n for(let k=0;k<6;k++)A["zq"+k]=L(s&&s.zq[k]);')
# ---- legend
rep("mm=ARR&&ARR.msArr?ARR.msArr[i]:NaN,mz=msZone(mm);", "mm=ARR&&ARR.msArr?ARR.msArr[i]:NaN,mz=msZone(mm),iz=ARR&&ARR.izArr?ARR.izArr[i]:NaN,izz=izZone(iz);")
rep('${fmt(mm,2)}</span></span>`:""}<span class="lk">Z250 ${fmt(zl,2)}</span>',
    '${fmt(mm,2)}</span></span>`:""}${izz?`<span title="industry Z: the average stretch Z of the other liquid stocks in ${esc(ARR.izG||"its industry")} (${ARR.izN?ARR.izN[i]:0} today): ${esc(izz.txt)}. Round 72: stretch-Z dips during sell-offs did better when the industry was at −1.0 or lower and worse when it was calm (above −0.5); context only, not part of the rule.">ind Z <span style="color:${izz.col};font-weight:600">${fmt(iz,2)}</span></span>`:""}<span class="lk">Z250 ${fmt(zl,2)}</span>')
# ---- plan text at daily and weekly Z touches
rep('.filter(Boolean).join(" and ")}.`)}\n  else if(WZc&&WZc.first){', '.filter(Boolean).join(" and ")}.`)+izNote(c)}\n  else if(WZc&&WZc.first){')
rep('.filter(Boolean).join(" and ")}.`)}\n  else say=`No trend signal.', '.filter(Boolean).join(" and ")}.`)+izNote(c)}\n  else say=`No trend signal.')
# ---- refresh when stored bars arrive
rep("applyAllUpdates(true);drawLibrary()},e=>{", "applyAllUpdates(true);drawLibrary();try{izOnUpdate()}catch(e){}},e=>{")
# ---- research page and the analyst's research summary
rep("<h2>Momentum Pulse (the pane under the chart)</h2>", """<h2>Industry Z (round 72, the pane under Market momentum)</h2>
<p>The average stretch Z of the <b>other</b> liquid stocks in the same industry (at least 3 of them; liquid = at least 120 days of history and a 60-day median traded value of SAR 3m or more; industries as in the sector view). It tells you whether a dip is the whole industry selling or this stock alone. The green area is below −1.0: the whole industry is selling. Above the dashed −0.5 line the industry is calm, so the drop is the stock's own. The thin blue line is the stock's own stretch Z, for comparison. It is computed in your browser from the stored daily prices (kept from 2019), so it starts in mid-2019.</p>
<p><b>What the test found</b> (round 72, pre-registered; Saudi 2013–19 and 2020–26, plus a US check). Among stretch-Z dips during market sell-offs (market momentum −1.18 or lower), dips whose industry was at −1.0 or lower earned 5 to 10 points more per 40-session trade than the rest (t 1.7 to 2.5 in both periods). The few dips in a calm industry (above −0.5; 7 to 9 per period) lost money on average. But the US did not agree in 2010–17, and inside the live rule's own 65 trades it barely separated winners from losers (kept +9.0% a trade, removed +8.7%): the ML rank and the market gates already catch it. So the live rule does not use it. Read it as context, not a filter.</p>
<h2>Momentum Pulse (the pane under the chart)</h2>""")
rep("- Costs matter: 87-stock Sharpe 1.23 at 5bp per side, 0.59 at 20bp.", "- ROUND 72 (Saudi, pre-registered: four momentum helpers for the Z swing): pulse acceleration, prior momentum, industry stretch and RSI with heavy volume, alone and combined, plus Capitulation-score slot order and 6-ATR or -25% stops. None improved the 5 x 5% account (all lowered Sharpe and Calmar in 2013-19); the live rule is unchanged. Industry Z (the other liquid stocks of the industry at stretch Z -1.0 or lower) added 5 to 10 points per trade inside sell-offs in 2013-19 and 2020-26 but not in the US 2010-17 and not inside the live rule's own trades; shown on the chart as context. Buying at the next open beat waiting for a bounce by 1.3 to 3.4 points.\n- Costs matter: 87-stock Sharpe 1.23 at 5bp per side, 0.59 at 20bp.")
open(p, "w").write(s); print("v33 written", len(s))
