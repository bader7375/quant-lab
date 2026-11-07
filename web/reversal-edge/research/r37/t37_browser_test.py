import asyncio, json
from playwright.async_api import async_playwright
SP = "/tmp/claude-0/-home-user-quant-lab/9205d36d-68a1-5401-8852-b575f8097dc2/scratchpad"
ML = open(f"{SP}/r27/today27.json").read(); SC = open(f"{SP}/ml26/sectors.json").read()
MOCK = """window.__ML=%s;window.__SC=%s;window.claude={use:async k=>k==='db'?{collection:n=>{const q={onSnapshot:(cb)=>{setTimeout(()=>cb({docs:n==='ml'?[{id:'latest',data:()=>window.__ML},{id:'sectors',data:()=>window.__SC}]:[]}),1500);return()=>{}},orderBy:()=>q,limit:()=>q};return q}}:null};""" % (ML, SC)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg = await b.new_page(viewport={"width": 1400, "height": 2400}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e))); await pg.add_init_script(MOCK)
        await pg.goto(f"file://{SP}/QuantLab-ReversalEdge-v22.html"); await pg.wait_for_timeout(9000)
        await pg.click("#tabs button[data-t=scan]"); await pg.wait_for_timeout(1500)
        for bx in ("zsa", "zus"):
            hid = await pg.evaluate(f"document.getElementById('{bx}-box').hidden"); note = await pg.inner_text(f"#{bx}-note"); rows = await pg.evaluate(f"[...document.querySelectorAll('#{bx}-t tr')].slice(0,6).map(r=>r.innerText.replace(/\\n/g,' | ').replace(/\\t/g,' | ').slice(0,230))")
            print(bx, "hidden:", hid, "\n NOTE:", note[:420].replace("\n", " ")); [print("  ", r) for r in rows]
        el = await pg.query_selector("#zus-box"); await el.screenshot(path=f"{SP}/v22_us.png"); el = await pg.query_selector("#zsa-box"); await el.screenshot(path=f"{SP}/v22_sa.png")
        await pg.set_viewport_size({"width": 390, "height": 900}); await pg.wait_for_timeout(500); print("phone hscroll:", await pg.evaluate("document.documentElement.scrollWidth>innerWidth"))
        print("errors:", errs[:5]); await b.close()
asyncio.run(main())
