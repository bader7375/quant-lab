"""Builds two outputs from src/app.template.html:
  label-studio.html      - one self-contained offline file (libraries inlined, prints via browser)
  web/label-studio.html  - the claude.ai link version (libraries from jsDelivr, page body only)
"""
import base64, json, pathlib, re
root = pathlib.Path(__file__).parent
src = root / "src"
tpl = (src / "app.template.html").read_text()
b64 = lambda f: "data:image/png;base64," + base64.b64encode((src / f).read_bytes()).decode()
common = (tpl.replace("__LABELS_JSON__", json.dumps(json.loads((src / "labels.json").read_text()), ensure_ascii=False))
             .replace("__LOGO_L__", b64("logo-left.png")).replace("__LOGO_R__", b64("logo-right.png")))

offline = (common.replace("/*__QRCODE__*/", (src / "vendor/qrcode-generator-1.4.4.js").read_text())
                 .replace("/*__JSPDF__*/", (src / "vendor/jspdf-2.5.1.umd.min.js").read_text())
                 .replace("__IS_WEB__", "false"))
(root / "label-studio.html").write_text(offline)

web = (common.replace("<script>/*__QRCODE__*/</script>", '<script src="https://cdn.jsdelivr.net/npm/qrcode-generator@1.4.4/qrcode.js"></script>')
             .replace("<script>/*__JSPDF__*/</script>", '<script src="https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js"></script>')
             .replace("__IS_WEB__", "true"))
web = re.sub(r'<!doctype html>\s*<html lang="en">\s*<head>\s*<meta charset="utf-8">\s*<meta name="viewport"[^>]*>\s*', "", web)
web = web.replace("</head>\n<body>\n", "\n").replace("</body>\n</html>\n", "")
(root / "web").mkdir(exist_ok=True)
(root / "web/label-studio.html").write_text(web)
for f in ("label-studio.html", "web/label-studio.html"):
    print(f, (root / f).stat().st_size // 1024, "KB")
