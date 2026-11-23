"""v27 -> v28: two signal sets, both on by default: "Z score" (the live Z-swing rule) and "Market returned" (option 7), each with its own switch."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
p = "index.html"; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:90], s.count(old)); s = s.replace(old, new)
rep("reversal edge v27 · Saudi + US scanner · option 7 switch", "reversal edge v28 · Saudi + US scanner · Z score + market returned")
# ---- Settings: two switches
rep('>Z swing: option 7 (buy only after the market turns)</label><select id="o7-mode">',
    '>Market returned signals (option 7)</label><select id="o7-mode">')
rep('<label for="o7-mode" title="Option 7 (round 47, pending decision):',
    '<label for="zs-mode" title="Z score signals: the live Z-swing rule (first close at stretch Z -2.62 daily / -2.08 weekly, ML rank 50%+, market model positive, market momentum -1.18 or lower, profitable company). Buy at the next open, 5%, hold 40 sessions, at most 5 positions.">Z score signals</label>'
    '<select id="zs-mode"><option value="auto">as the daily list</option><option value="on">on</option><option value="off">off</option></select>\n'
    '          <label for="o7-mode" title="Market returned signals (option 7, round 47):')
rep('The daily list follows its own switch (daily/settings.json); this setting changes how the terminal shows Z-swing signals.">',
    'Its own list: at most 5 positions; a stock on both lists is one trade. The daily list follows its own switches (daily/settings.json); these settings change how the terminal shows the signals.">')
rep(' if(el.id==="o7-mode"){UI.o7=el.value;saveUI();try{drawZScans()}catch(e){}return}',
    ' if(el.id==="o7-mode"||el.id==="zs-mode"){UI[el.id==="o7-mode"?"o7":"zs"]=el.value;saveUI();try{drawZScans()}catch(e){}return}')
rep('UI.o7=["auto","on","off"].includes(UI.o7)?UI.o7:"auto";try{$("o7-mode").value=UI.o7}catch(e){}',
    'UI.o7=["auto","on","off"].includes(UI.o7)?UI.o7:"auto";try{$("o7-mode").value=UI.o7}catch(e){}\nUI.zs=["auto","on","off"].includes(UI.zs)?UI.zs:"auto";try{$("zs-mode").value=UI.zs}catch(e){}')
# ---- helpers
rep("function o7On(){", "function zsOn(){const O=typeof MLPF!==\"undefined\"&&MLPF?MLPF.opt7:null;return UI.zs===\"on\"||(UI.zs!==\"off\"&&!(O&&O.zscore===false))}\nfunction o7On(){")
rep('<span><b>Option 7</b> (Z swing only after the market turns): <b class="${on?"up":""}">${on?"ON":"off"}</b> ${UI.o7==="auto"?"(as the daily list)":"(your terminal setting; the daily list is "+(O.on?"on":"off")+")"}',
    '<span><b>Market returned signals</b> (Z score signals taken only after the market turns): <b class="${on?"up":""}">${on?"ON":"off"}</b> ${UI.o7==="auto"?"(as the daily list)":"(your terminal setting; the daily list is "+(O.on?"on":"off")+")"}')
rep("stocks blocked (bought by the live rule before the turn)`:\"\")+`. Settings → Z swing: option 7.</span></div>`}",
    "stocks blocked (Z score bought them before the turn)`:\"\")+`. Z score signals: <b>${zsOn()?\"ON\":\"off\"}</b>. Switches: Data &amp; settings.</span></div>`}")
# ---- scanner: each fresh touch shows both signal sets
rep('''if(r.loss)why.push("loss-making (your rule)");if(o7On()&&MLPF.opt7){if(!MLPF.opt7.gate)why.push("option 7: the market has not turned");else if(r.b7)why.push("option 7: bought before the turn")}
     return why.length?`<span class="note">fresh ${r.fd?"daily":"weekly"} touch · skip: ${why.join(", ")}</span>`:`<span class="up"><b>BUY next open</b> · ${r.fd?"Z swing":"weekly Z swing"} · 5%, hold 40 sessions</span>`}''',
    '''if(r.loss)why.push("loss-making (your rule)");
     if(why.length)return `<span class="note">fresh ${r.fd?"daily":"weekly"} touch · skip: ${why.join(", ")}</span>`;
     const O7=MLPF.opt7,zsT=zsOn()?`<span class="up"><b>BUY next open</b> · Z score${r.fd?"":" (weekly)"}</span>`:'<span class="note">Z score off</span>',
      mrT=!o7On()||!O7?"":!O7.gate?'<span class="note">market returned: skip (the market has not turned)</span>':r.b7?'<span class="note">market returned: skip (bought before the turn)</span>':'<span class="up"><b>BUY</b> · market returned</span>';
     return zsT+(mrT?" · "+mrT:"")+'<span class="note"> · 5%, hold 40 sessions</span>'}''')
# ---- research note
rep("<h2>Option 7 switch: Z swing only after the market turns</h2>", "<h2>Two signal sets: Z score and Market returned</h2>")
rep("<p>Settings → <i>Z swing: option 7</i>. When it is on, a Z-swing signal counts only while the market-turn window is open:",
    "<p><b>Z score</b> is the live Z-swing rule. <b>Market returned</b> (option 7) is its own signal set: a Z score signal counts for it only while the market-turn window is open:")
rep("The daily list has its own switch (ask Claude to turn it on or off); the terminal setting can follow it or override it for this browser.</p>",
    "Both are on. Each keeps its own limit of 5 positions, and a stock on both lists is one trade. The daily list has its own switches (ask Claude to turn either on or off); the terminal settings (Data &amp; settings) can follow them or override them for this browser.</p>")
open(p, "w").write(s); print("patched v28:", len(s), "bytes")
