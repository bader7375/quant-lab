import asyncio, json
from playwright.async_api import async_playwright
SP = "/tmp/claude-0/-home-user-quant-lab/9205d36d-68a1-5401-8852-b575f8097dc2/scratchpad"
ML = open(f"{SP}/ml26/today.json").read(); SC = open(f"{SP}/ml26/sectors.json").read()
BARS = {k: json.load(open(f"{SP}/docs2/{k}.json")) for k in ["1111", "2222", "6022", "4013", "7203", "TSLA", "NVDA", "SPY", "AAPL", "F"]}
MOCK = """window.__ML=%s;window.__SC=%s;window.__B=%s;window.claude={use:async k=>k==='db'?{collection:n=>{const q={onSnapshot:(cb)=>{setTimeout(()=>cb({docs:n==='ml'?[{id:'latest',data:()=>window.__ML},{id:'sectors',data:()=>window.__SC}]:n==='bars'?Object.entries(window.__B).map(([id,b])=>({id,data:()=>b})):[]}),2500);return()=>{}},orderBy:()=>q,limit:()=>q};return q}}:null};""" % (ML, SC, json.dumps(BARS))
async def done(pg): await pg.wait_for_function("document.getElementById('runmsg').textContent.startsWith('Done') && !document.getElementById('run').disabled", timeout=300000)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); ctx = await b.new_context(viewport={"width": 1400, "height": 1200}); pg = await ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e))); await pg.add_init_script(MOCK)
        await pg.goto(f"file://{SP}/QuantLab-ReversalEdge-v14.html"); await done(pg); await pg.wait_for_timeout(4000); await done(pg)
        ds = await pg.evaluate("[...document.querySelectorAll('#sym option')].map(o=>o.value)"); print("DS after db snapshot:", ds)
        print("upd table:", (await pg.inner_text("#upd-t"))[:1500])
        await pg.click("#tabs button[data-t=data]"); await pg.wait_for_timeout(300); print("note:", await pg.inner_text("#lib-note"))
        await pg.select_option("#lib-sector", "US stocks"); await pg.wait_for_timeout(500); print(await pg.inner_text("#lib-t"))
        await pg.select_option("#lib-sector", "New listings 2020+"); await pg.wait_for_timeout(500); print(await pg.inner_text("#lib-t"))
        print("6022 disabled:", await pg.evaluate("document.querySelector('#lib-t input[data-lib=\"6022\"]').disabled"))
        await pg.check('#lib-t input[data-lib="1111"]'); await pg.wait_for_timeout(1500); await done(pg)
        await pg.click("#tabs button[data-t=data]"); await pg.wait_for_timeout(300); await pg.select_option("#lib-sector", "US stocks"); await pg.wait_for_timeout(300)
        await pg.check('#lib-t input[data-lib="NVDA"]'); await pg.wait_for_timeout(1500); await done(pg)
        await pg.click("#tabs button[data-t=data]"); await pg.wait_for_timeout(300); print("msg:", await pg.inner_text("#lib-msg")); print("DS:", await pg.evaluate("[...document.querySelectorAll('#sym option')].map(o=>o.value)"))
        print("stored ds keys:", await pg.evaluate("Object.keys(JSON.parse(localStorage.getItem('qlab-ds')||'{}'))"), "libsel:", await pg.evaluate("localStorage.getItem('qlab-lib')"))
        await pg.click("#tabs button[data-t=chart]"); await pg.wait_for_timeout(800); await pg.select_option("#sym", "1111"); await pg.wait_for_timeout(2500)
        print("1111 card:", (await pg.inner_text("#inspbody"))[:700]); await pg.screenshot(path=f"{SP}/v14_1111.png")
        await pg.select_option("#sym", "NVDA"); await pg.wait_for_timeout(2500); print("NVDA card:", (await pg.inner_text("#inspbody"))[:500])
        await pg.click("#tabs button[data-t=data]"); await pg.wait_for_timeout(300)
        print("updates table:", (await pg.inner_text("#upd-t"))[:1200])
        # reload: selections should come back from the db without being stored in the browser
        await pg.reload(); await done(pg); await pg.wait_for_timeout(4000); await done(pg)
        print("after reload DS:", await pg.evaluate("[...document.querySelectorAll('#sym option')].map(o=>o.value)")); await pg.click("#tabs button[data-t=data]"); await pg.wait_for_timeout(300)
        await pg.select_option("#lib-sector", "US stocks"); await pg.wait_for_timeout(300)
        await pg.uncheck('#lib-t input[data-lib="NVDA"]'); await pg.wait_for_timeout(1500); await done(pg)
        print("after unload DS:", await pg.evaluate("[...document.querySelectorAll('#sym option')].map(o=>o.value)"), await pg.evaluate("localStorage.getItem('qlab-lib')"))
        await pg.click("#tabs button[data-t=data]"); await pg.set_viewport_size({"width": 390, "height": 900}); await pg.wait_for_timeout(500)
        el = await pg.query_selector("#lib-t"); await pg.evaluate("document.querySelector('#lib-t').scrollIntoView()"); await pg.screenshot(path=f"{SP}/v14_lib_phone.png")
        print("hscroll:", await pg.evaluate("document.documentElement.scrollWidth>innerWidth"))
        print("errors:", errs[:5]); await b.close()
asyncio.run(main())
