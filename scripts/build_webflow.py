#!/usr/bin/env python3
"""Build Webflow-safe minified bundles and a local browser preview from webflow/*.html.
Requires Node/npm so npx can run esbuild and html-minifier-terser.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "webflow"
OUT = ROOT / "webflow-embeds"
ASSETS = ROOT / "assets"
CSS_SOURCE = ROOT / "scripts" / "thanksgiving.base.css"
PREVIEW = ROOT / "preview" / "index.html"
BASE_URL = "https://cdn.jsdelivr.net/gh/supervity-ai/thanksgiving@main/assets/"
MAX_CHARS = 50_000


def run(args):
    subprocess.run(args, cwd=ROOT, check=True)


def css_body(filename):
    text = (SRC / filename).read_text()
    blocks = re.findall(r"<style[^>]*>([\s\S]*?)</style>", text, flags=re.I)
    if not blocks:
        raise ValueError(f"No style block in {filename}")
    return "\n".join(blocks)


def split_css(css, max_chars=47_000):
    """Split minified CSS only between top-level rules (never inside @media/keyframes)."""
    rules, start, depth = [], 0, 0
    quote = None
    escaped = False
    comment = False
    i = 0
    while i < len(css):
        ch = css[i]
        nxt = css[i + 1] if i + 1 < len(css) else ""
        if comment:
            if ch == "*" and nxt == "/":
                comment = False
                i += 2
                continue
        elif quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch == "/" and nxt == "*":
            comment = True
            i += 2
            continue
        elif ch in "\"'":
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                rules.append(css[start:i + 1])
                start = i + 1
        elif ch == ";" and depth == 0:
            rules.append(css[start:i + 1])
            start = i + 1
        i += 1
    if css[start:].strip():
        rules.append(css[start:])
    parts, current = [], ""
    for rule in rules:
        if current and len(current) + len(rule) > max_chars:
            parts.append(current)
            current = ""
        current += rule
    if current:
        parts.append(current)
    return parts


def script_body(filename):
    text = (SRC / filename).read_text()
    blocks = re.findall(r"<script[^>]*>([\s\S]*?)</script>", text, flags=re.I)
    if not blocks:
        raise ValueError(f"No script block in {filename}")
    return "\n;\n".join(blocks)


def minify_css(css, tmp):
    source = tmp / "styles.css"
    target = tmp / "styles.min.css"
    source.write_text(css)
    run(["npx", "--yes", "esbuild", str(source), "--minify", f"--outfile={target}"])
    return target.read_text().strip()


def minify_js(js, tmp):
    source = tmp / "scripts.js"
    target = tmp / "scripts.min.js"
    source.write_text(js)
    run(["npx", "--yes", "esbuild", str(source), "--minify", f"--outfile={target}"])
    return target.read_text().strip()


def minify_html(text, target, tmp):
    source = tmp / target.name
    source.write_text(text)
    run([
        "npx", "--yes", "html-minifier-terser",
        "--collapse-whitespace", "--conservative-collapse", "--remove-comments", "--case-sensitive",
        str(source), "-o", str(target),
    ])
    return target.read_text()


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    (ROOT / "preview").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="thanksgiving-build-") as temp:
        tmp = Path(temp)
        # Use the full authored stylesheet: the old Webflow fragments had lost
        # @keyframes blocks during an earlier extraction, leaving animation steps
        # orphaned as invalid CSS.
        css_patch = """
:root{--tgv-top:0px;--tgv-nav:12rem}
@media(max-width:900px){:root{--tgv-top:30px;--tgv-nav:80px}}
.svtg-mobile-game-hint{display:none}
@media (min-width:992px) and (max-width:1199px){:root{--tgv-nav:13rem}}
.svtg-thx26.tg-bar,.svtg-thx26.tg-nav{display:none!important}
.w-nav{z-index:10001!important}
.tg-modal:where(.svtg-thx26,.svtg-thx26 *){z-index:999999!important}
.c5:where(.svtg-thx26,.svtg-thx26 *){z-index:999999!important}
.s5dim:where(.svtg-thx26,.svtg-thx26 *){z-index:999998!important}
.over:where(.svtg-thx26,.svtg-thx26 *){z-index:999999!important}
.s5floor.down:where(.svtg-thx26,.svtg-thx26 *){width:100%;height:100%}
.s5vp:where(.svtg-thx26,.svtg-thx26 *){padding-top:clamp(52px,7vh,76px)}
.s5art:where(.svtg-thx26,.svtg-thx26 *) .tl-img{top:auto;bottom:0;height:216.6667%;-webkit-mask-image:none!important;mask-image:none!important}
.s7:where(.svtg-thx26,.svtg-thx26 *){position:relative;z-index:2;height:auto!important;min-height:0!important;max-height:none!important;overflow:visible!important}
.s7:where(.svtg-thx26,.svtg-thx26 *)>.tg-wrap{height:auto!important;min-height:0!important;max-height:none!important;overflow:visible!important}
.w7wall:where(.svtg-thx26,.svtg-thx26 *){height:auto!important;min-height:0!important;max-height:none!important;overflow:visible!important;grid-auto-rows:auto;align-items:stretch}
.w-embed:has(.svtg-thx26.s7){position:relative!important;z-index:2;height:auto!important;min-height:0!important;max-height:none!important;overflow:visible!important}
#hero .copy{top:var(--tgv-nav)!important}
.svtg-thx26 p{color:#5D514C}
.svtg-thx26 svg{max-width:100%}
.svtg-thx26 .btn{max-width:100%;white-space:normal;overflow-wrap:anywhere}
.svtg-thx26 .btn svg{flex:none;max-width:22px}
.svtg-thx26 .cs-panel{min-width:0;overflow:visible}
.svtg-thx26 .cs-acts{min-width:0;flex-wrap:wrap}
.svtg-thx26 .cs-acts button{min-width:0;max-width:100%;white-space:normal}
.svtg-thx26 .cs-canvas{max-width:100%}
.svtg-thx26 svg{overflow:visible}
.svtg-thx26 button{box-sizing:border-box;min-width:0;max-width:100%}
.svtg-thx26 .s5{width:100vw;max-width:none;margin-left:calc(50% - 50vw)}
@media(max-width:760px){
:root{--tgv-top:30px;--tgv-nav:80px}
.svtg-mobile-game-hint{display:inline}
.svtg-desktop-game-hint{display:none!important}
.s4:where(.svtg-thx26,.svtg-thx26 *){display:none!important}
.hero:where(.svtg-thx26,.svtg-thx26 *){min-height:0;height:100svh;height:100dvh}
#hero .copy{top:calc(var(--chrome) + clamp(10px,1.8vh,16px))!important;width:100%;padding:0 18px;gap:8px}
.copy:where(.svtg-thx26,.svtg-thx26 *) h1{font-size:clamp(30px,8vw,38px);line-height:1.04}
.copy:where(.svtg-thx26,.svtg-thx26 *) p{max-width:34ch;font-size:13px!important;line-height:1.34!important;color:#5D514C}
.copy:where(.svtg-thx26,.svtg-thx26 *) .btn{margin-top:0;min-height:46px}
.desk:where(.svtg-thx26,.svtg-thx26 *){z-index:2;visibility:visible;opacity:1}
.hit:where(.svtg-thx26,.svtg-thx26 *){touch-action:pan-y}
.s5:where(.svtg-thx26,.svtg-thx26 *){width:100vw;max-width:none;margin-left:calc(50% - 50vw);overflow:visible}
.s5vp:where(.svtg-thx26,.svtg-thx26 *){min-height:0;max-height:none;padding:0 0 20px;overflow:visible}
.s5head:where(.svtg-thx26,.svtg-thx26 *){position:relative;inset:auto;padding:24px 18px 0;margin:0 auto 14px;z-index:6}
.s5scene:where(.svtg-thx26,.svtg-thx26 *){position:relative;inset:auto;display:block;width:100%;height:clamp(220px,56vw,270px);flex:none;overflow:hidden}
.s5tom:where(.svtg-thx26,.svtg-thx26 *){width:clamp(64px,18vw,88px)}
.g5-tag:where(.svtg-thx26,.svtg-thx26 *){display:none!important}
.g5m:where(.svtg-thx26,.svtg-thx26 *){display:none!important}
.g5:where(.svtg-thx26,.svtg-thx26 *){width:clamp(90px,24vw,112px);bottom:10%;z-index:9}
.svtg-thx26 #g1{left:21%!important}
.svtg-thx26 #g2{left:77%!important}
.svtg-thx26 .cs-hint{display:none}
.s5:where(.svtg-thx26,.svtg-thx26 *){position:relative;left:auto;width:100vw;max-width:none;margin-left:calc(50% - 50vw);margin-right:calc(50% - 50vw);transform:none;overflow:visible}
.s5dim:where(.svtg-thx26,.svtg-thx26 *){position:fixed!important;inset:0!important}
.s5head:where(.svtg-thx26,.svtg-thx26 *){text-align:center}
.s5head:where(.svtg-thx26,.svtg-thx26 *) h2{font-size:clamp(26px,7vw,32px);line-height:1.08}
.s5head:where(.svtg-thx26,.svtg-thx26 *) p{max-width:34ch;margin:10px auto 0;font-size:14px;line-height:1.45;color:#5D514C}
.c5:where(.svtg-thx26,.svtg-thx26 *){position:fixed!important;top:calc(var(--tgv-top) + var(--tgv-nav) + 12px)!important;right:14px;bottom:12px;left:14px!important;width:auto!important;max-height:none!important;transform:none!important;grid-template-columns:minmax(0,1fr);grid-template-rows:minmax(108px,24vh) minmax(0,1fr);overflow:hidden!important}
.c5.show:where(.svtg-thx26,.svtg-thx26 *){transform:none!important}
.c5-vis:where(.svtg-thx26,.svtg-thx26 *){min-height:0;padding:12px!important}
.c5-vis:where(.svtg-thx26,.svtg-thx26 *) svg{max-width:100px;max-height:100%;width:auto}
.c5-body:where(.svtg-thx26,.svtg-thx26 *){min-height:0;overflow-y:auto;overscroll-behavior:contain;padding:18px 20px 24px;gap:8px}
.s5:not(.arrived):where(.svtg-thx26,.svtg-thx26 *) .g5{pointer-events:none}
.svtg-thx26 .cs-tabs,.svtg-thx26 .cs-pane[data-pane=look],.svtg-thx26 .cs-pane[data-pane=stick],.svtg-thx26 .svtg-card-message,.svtg-thx26 .cs-two,.svtg-thx26 .cs-chips{display:none!important}
.svtg-thx26 .cs-pane[data-pane=words]{display:flex!important;gap:12px}
.svtg-thx26 .cs-acts #csMore{display:none!important}
.svtg-thx26 .cs-acts .cs-shuffle{order:-1;justify-content:center;border:1px solid #E8D3C9;border-radius:999px;background:#fff;padding:12px 16px;font-size:15px}
.svtg-thx26 .cs-acts .cs-shuffle svg{flex:none}
.svtg-thx26 .cs{grid-template-columns:minmax(0,1fr);gap:18px}
.svtg-thx26 .cs-stage{order:2}
.svtg-thx26 .cs-panel{order:1;padding:20px;gap:12px}
.svtg-thx26 .cs-f input{min-width:0;width:100%;box-sizing:border-box;color:#21150F}
.svtg-card-note{margin:0;color:#5D514C;font-size:14px;line-height:1.45}
.svtg-thx26 .cs-acts{display:grid;grid-template-columns:1fr;gap:10px}
.svtg-thx26 .cs-acts button{width:100%;min-height:48px}
.svtg-thx26 .cs-canvas{overflow:hidden}
.svtg-thx26 .cs-canvas canvas{touch-action:pan-y}
.svtg-thx26 .cs-shuffle{justify-content:center;border:1px solid #E8D3C9;border-radius:999px;background:#fff;padding:12px 16px;font-size:15px}
.svtg-thx26 .cs-shuffle svg{flex:none}
}
"""
        css_source = CSS_SOURCE.read_text() + css_patch
        css_full = minify_css(css_source, tmp)
        css_parts = split_css(css_full)
        if len(css_parts) > 2:
            raise ValueError(f"CSS needs {len(css_parts)} embeds; expected no more than 2")
        if len(css_parts) == 1:
            css_parts.append("")
        js = minify_js("\n;\n".join(script_body(f) for f in ("12-script-a.html", "13-script-b.html")), tmp)

        (OUT / "01-head.html").write_text((SRC / "00-page-head-code.html").read_text())
        (OUT / "02-styles-a.html").write_text(f"<style>{css_parts[0]}</style>")
        (OUT / "03-styles-b.html").write_text(f"<style>{css_parts[1]}</style>")
        (SRC / "01-styles-a.html").write_text(f"<style>{css_parts[0]}</style>")
        (SRC / "02-styles-b.html").write_text(f"<style>{css_parts[1]}</style>")

        groups = {
            "04-content-a.html": ("03-defs.html", "05-hero-game.html", "06-opportunity-engine.html"),
            "05-content-b.html": ("07-busywork-to-pie.html", "08-gifts.html"),
            "06-content-c.html": ("09-thank-you-cards.html", "10-wall-of-thanks.html", "11-celebrate.html"),
        }
        for name, files in groups.items():
            minify_html("\n".join((SRC / f).read_text() for f in files), OUT / name, tmp)
        (OUT / "07-scripts.html").write_text(f"<script>{js}</script>")

        # Hosted-option files mirror the current embed CSS and JS.
        (ASSETS / "thanksgiving.css").write_text(css_full)
        (ASSETS / "thanksgiving.js").write_text(js)

        # Preview uses local assets plus a minimal stand-in for the site's sticky navbar.
        head = (SRC / "00-page-head-code.html").read_text().replace(BASE_URL, "../assets/")
        preview_base = """<style>
html{height:100%}body{margin:0;min-height:100%;background:#fff;font:14px/20px Arial,sans-serif;color:#333}
h1{font-size:38px;line-height:44px;margin:20px 0 10px;font-weight:bold}h2{font-size:32px;line-height:36px;margin:20px 0 10px;font-weight:bold}h3{font-size:24px;line-height:30px;margin:20px 0 10px;font-weight:bold}
p{margin:0 0 10px}ul,ol{margin:0 0 10px;padding-left:40px}label{display:block;margin-bottom:5px;font-weight:bold}img{max-width:100%;vertical-align:middle;display:inline-block}button,[type=button],[type=reset]{border:0;cursor:pointer;-webkit-appearance:button}
.preview-navbar{position:fixed;z-index:10000;inset:0 0 auto;height:137px;box-sizing:border-box;padding:30px 32px;background:rgba(255,255,255,.96);box-shadow:0 2px 8px #0002;display:flex;align-items:end;justify-content:space-between;font:500 15px Arial,sans-serif;color:#171717}
.preview-navbar .links{display:flex;gap:28px}.w-embed:before,.w-embed:after{content:\" \";display:table;grid-area:1/1/2/3}.w-embed:after{clear:both}
</style>"""
        content = []
        for files in groups.values():
            content.extend((SRC / f).read_text() for f in files)
        markup = "\n".join(content)
        preview_html = (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Supervity Thanksgiving 2026 — final</title>' + preview_base + head +
            f"<style>{css_full}</style></head><body>"
            '<nav class="preview-navbar"><strong>Supervity</strong><div class="links"><span>Platform</span><span>Solutions</span><span>AI Employee Hub</span><span>Resources</span></div><strong>Book a Demo</strong></nav>'
            f"<div class=\"w-embed\">{markup}</div><div class=\"w-embed\"><script>{js}</script></div>"
            '</body></html>'
        )
        PREVIEW.write_text(preview_html)

    for path in sorted(OUT.glob("*.html")):
        size = len(path.read_text())
        if size >= MAX_CHARS:
            raise ValueError(f"Webflow limit exceeded: {path.name} ({size} chars)")
        print(f"{path.relative_to(ROOT)}: {size:,} chars")


if __name__ == "__main__":
    build()
