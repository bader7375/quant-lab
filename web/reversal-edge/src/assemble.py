P=lambda n:open('../v4/'+n+'.part').read()
css=P('css'); helpers=P('helpers'); mp=P('modelperf'); sec=P('sections')
old_fam='fam:{stochastic:"#3987e5",deviation:"#d95926",volatility:"#199e70",tail:"#c98500",market:"#d55181",micro:"#008300",confluence:"#9085e9"}'
helpers=helpers.replace(old_fam,'fam:{volume:"#3987e5",volatility:"#199e70",fear:"#d55181",oversold:"#d95926",news:"#c98500",candle:"#9085e9"}')
reps=[('["impbars","famarea","calib","roc"].forEach(id=>$(id).innerHTML="")','["impbars","famarea","calib","roc"].forEach(id=>clr(id))'),
('["eqplot","rhist","exits","monthly"].forEach(id=>$(id).innerHTML="")','["eqplot","rhist","exits","monthly"].forEach(id=>clr(id))'),
("""{$("eqplot").innerHTML='<div class="empty">No out-of-sample period to simulate.</div>';return}""","""{clr("eqplot",'<div class="empty">No out-of-sample period to simulate.</div>');return}"""),
("""const tr=e.target.closest("tr[data-s]");if(!tr)return;st.sym=tr.dataset.s;sel.value=st.sym;const d=S(),i=d.d.indexOf(tr.dataset.d);st.n=Math.max(252,d.d.length-i+60);document.querySelectorAll("#rng button").forEach(b=>b.classList.remove("on"));st.cursor=i;st.pinned=true;show("chart")});""","""const tr=e.target.closest("tr[data-s]");if(!tr)return;focusDate(tr.dataset.s,tr.dataset.d)});"""),
("d.p.forEach((p,i)=>{if(isF(p)&&d.dom[i]&&isF(d.y[i]))pairs.push([p,d.y[i]])})","d.P.forEach((p,i)=>{if(isF(p)&&d.setup[i]&&isF(d.y[i]))pairs.push([p,d.y[i]])})"),
("coefficients at retrain ${s.d} (${s.n} samples, ${s.own} own) · + raises P(revert)","weights at refit ${s.d} (${s.n} setups, ${s.own} own) · bigger = more influence on the score"),
('Plotly.react("eqplot",[{x:bt.d,y:bt.eq,name:"strategy",line:{color:C.blue,width:2},hovertemplate:"strategy %{y:,.0f}<extra></extra>"},','Plotly.react("eqplot",[{x:bt.d,y:bt.eq,name:"strategy (score filter)",line:{color:C.blue,width:2},hovertemplate:"strategy %{y:,.0f}<extra></extra>"},{x:RES.btAll.d,y:RES.btAll.eq,name:"all RSI(2) setups",line:{color:"#8a8a85",width:1.2,dash:"dot"},hovertemplate:"all setups %{y:,.0f}<extra></extra>"},{x:RES.btA.d,y:RES.btA.eq,name:"A+ only",line:{color:"#fab219",width:1.4,dash:"dash"},hovertemplate:"A+ only %{y:,.0f}<extra></extra>"},'),
('+K("OOS AUC",fmt(c.roc_auc),"Brier skill "+fmt(c.brier_skill,3));','+K("OOS AUC",fmt(c.roc_auc),"Brier skill "+fmt(c.brier_skill,3))+K("All setups, no filter",fmt(RES.metrics.portfolioAll.expectancy_R,2,"R"),"Sharpe "+fmt(RES.metrics.portfolioAll.sharpe,2)+" · "+RES.metrics.portfolioAll.n_trades+" trades")+K("Time in market",pct(RES.bt.exposure,0),"total return "+pct(p.total_return,0))+(RES.metrics.portfolioAPlus&&RES.metrics.portfolioAPlus.n_trades?K("A+ only (comparison)",pct(RES.metrics.portfolioAPlus.total_return,0),"Sharpe "+fmt(RES.metrics.portfolioAPlus.sharpe,2)+" · "+RES.metrics.portfolioAPlus.n_trades+" trades · max DD "+pct(RES.metrics.portfolioAPlus.max_drawdown,0)):"");'),
('["p","P"],["p_lo","P low"],["z_entry","z"],["regime","regime"]','["p","P(profit)"],["score","edge score"],["z_entry","z20"],["fear","fear rank"]'),
]
for a,b in reps:
    assert a in mp, a[:60]; mp=mp.replace(a,b)
i=sec.index('<section id="t-about"'); j=sec.index('</section>',i)+len('</section>'); sec=sec[:i]+sec[j:]
sec=sec.replace('<div class="cards" id="cards"></div>','<div class="cards" id="cards"></div><div id="edgebox" style="margin-top:14px"></div>')
body=open('body.html').read().replace('{{SECTIONS}}',sec)
js='\n'.join(open(f).read() for f in ['app1.js','app2.js','app3.js','app4.js'])+'\n'+mp+'\n'+open('app5.js').read()+'\n'+open('app6.js').read()
open('index.html','w').write(css+'\n'+body+'\n<script src="lwc.js"></script>\n<script>\n(async function(){\n"use strict";\n'+helpers+'\n'+js+'\n})();\n</script>\n')
