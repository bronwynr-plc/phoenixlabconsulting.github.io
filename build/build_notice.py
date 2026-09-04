#!/usr/bin/env python3
"""
Build the NYSDOH September 2026 change-notice page for phoenixlabconsulting.com.

Takes the standalone one-pager and wraps it in the live site's chrome
(document-control strip, header/nav, footer, theme system) so it reads as part
of the site rather than a foreign page.

NO REGULATORY TEXT IS ALTERED. The article body is copied verbatim except for
two link/attribute changes noted in LINK_FIXES below.
"""
import re, sys, pathlib

SITE   = pathlib.Path(sys.argv[1])   # index.html of live site
SRC    = pathlib.Path(sys.argv[2])   # standalone one-pager
OUT    = pathlib.Path(sys.argv[3])   # destination
SLUG   = "nysdoh-september-2026-changes"

site = SITE.read_text(encoding="utf-8")
src  = SRC.read_text(encoding="utf-8")

# ---------------------------------------------------------------- site chrome
site_css   = re.search(r"(?s)<style>(.*?)</style>", site).group(1)
header_html= re.search(r"(?s)<header>.*?</header>", site).group(0)
doccontrol = re.search(r'(?s)<div class="doccontrol">.*?</div></div>', site).group(0)
footer_html= re.search(r'(?s)<footer class="site">.*?</footer>', site).group(0)
prepaint   = re.search(r"(?s)<script>\(function\(\)\{try\{var t=localStorage.*?</script>", site).group(0)

# Google tag, lifted from the live site so this page reports to the same property.
# Fail loudly rather than silently shipping the placeholder (see the guard before write).
_an = re.search(
    r'(?s)<!-- Google tag \(gtag\.js\).*?-->\s*'
    r'<script async src="https://www\.googletagmanager\.com/gtag/js\?id=[^"]+"></script>\s*'
    r'<script>.*?</script>',
    site)
if not _an:
    sys.exit(f"ERROR: no Google tag block found in {SITE}. "
             "The notice page would ship without analytics. "
             "Check the gtag markup in index.html, then re-run.")
analytics = _an.group(0)

# Sub-page nav: homepage anchors must become root-relative.
header_html = re.sub(r'href="#(about|services|nysdoh|finder|contact|top)"',
                     r'href="/#\1"', header_html)
# Brandmark should go home, not to this page's top.
header_html = header_html.replace('class="brandmark" href="/#top"', 'class="brandmark" href="/"')

# ------------------------------------------------------------- article pieces
art_css  = re.search(r"(?s)<style>(.*?)</style>", src).group(1)
art_body = re.search(r"(?s)<body>\s*(.*?)\s*</body>", src).group(1)
title    = re.search(r"<title>(.*?)</title>", src, re.S).group(1).strip()
desc     = re.search(r'<meta name="description" content="(.*?)">', src, re.S).group(1).strip()

# Container rename so the article's 47rem measure doesn't collide with the
# site's 1180px .wrap.
art_body = art_body.replace('<div class="wrap">', '<div class="notice-wrap">', 1)

# --------------------------------------------------------------- LINK_FIXES
# Non-regulatory link corrections only.
LINK_FIXES = [
    # "Consulting enquiries" pointed at the site root from an external context;
    # on-site it should go to the contact section.
    ('<a class="btn ghost" href="https://phoenixlabconsulting.com">Consulting enquiries</a>',
     '<a class="btn ghost" href="/#contact">Consulting enquiries</a>'),
]
for old, new in LINK_FIXES:
    if old not in art_body:
        sys.exit("LINK_FIX target not found -- aborting rather than guessing:\n" + old)
    art_body = art_body.replace(old, new)

# ------------------------------------------------- scope article CSS to .notice
# Drop the article's :root (its tokens are re-declared against site tokens below)
art_css = re.sub(r"(?s):root\{.*?\}", "", art_css, count=1)
# Drop its body/* resets -- the site supplies those.
art_css = re.sub(r"(?s)\*\{box-sizing:border-box\}", "", art_css)
art_css = re.sub(r"(?s)\bbody\{[^}]*\}", "", art_css, count=1)

def scope(css):
    out, i = [], 0
    while i < len(css):
        if css[i] == "@":                      # at-rule: recurse into its block
            j = css.index("{", i); head = css[i:j]
            depth, k = 1, j + 1
            while depth:
                if css[k] == "{": depth += 1
                elif css[k] == "}": depth -= 1
                k += 1
            out.append(head + "{" + scope(css[j+1:k-1]) + "}")
            i = k
            continue
        m = re.compile(r"[^{}@]+\{[^{}]*\}").match(css, i)
        if not m:
            out.append(css[i]); i += 1; continue
        rule = m.group(0)
        sels, body = rule.split("{", 1)
        newsel = ",".join(
            (s.strip() if s.strip().startswith(".notice") else ".notice " + s.strip())
            for s in sels.split(",") if s.strip()
        )
        out.append(newsel + "{" + body)
        i = m.end()
    return "".join(out)

art_css = scope(art_css)

# ------------------------------------------------------- article theme tokens
# Map the one-pager's palette onto the site's tokens so dark mode works and the
# site's existing AA decision (#D8501C on dark) is reused rather than re-derived.
TOKENS = """
/* ---- change-notice article: palette bound to site tokens ---- */
.notice{--flame:var(--orange);--teal:#2B6164;--gold:#E9B44C;--cornsilk:#F1ECCE;
        --card:#ffffff;--thead-bg:var(--cornsilk);--btn-hover:#a53010;
        --serif:"IBM Plex Serif",Georgia,"Times New Roman",serif;
        --sans:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
        --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace;}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]) .notice{--teal:#7FB2B5;--cornsilk:#2A2724;
        --card:#171614;--thead-bg:#232120;--btn-hover:#E8703F;}
}
:root[data-theme="dark"] .notice{--teal:#7FB2B5;--cornsilk:#2A2724;
        --card:#171614;--thead-bg:#232120;--btn-hover:#E8703F;}
.notice .notice-wrap{max-width:47rem;margin:0 auto;padding:3.5rem 1.5rem 5rem}
.notice{font-size:17px;line-height:1.6}
"""

# Replace hardcoded #fff surfaces with the themable --card token, and the
# thead band with --thead-bg, so nothing goes white-on-white in dark mode.
art_css = art_css.replace("background:#fff", "background:var(--card)")
art_css = art_css.replace("background:var(--cornsilk);font-weight:600",
                          "background:var(--thead-bg);font-weight:600")
art_css = art_css.replace("background:#a53010", "background:var(--btn-hover)")
art_css = art_css.replace(".notice .btn.ghost:hover{background:var(--cornsilk)",
                          ".notice .btn.ghost:hover{background:var(--thead-bg)")
art_css = art_css.replace(".notice a:hover{background:var(--cornsilk)}",
                          ".notice a:hover{background:var(--thead-bg)}")


CHROME_FIX = """
/* Narrow-viewport header fix. The site header lays brandmark + theme toggle +
   CTA in a fixed-height flex row; below ~414px that row is wider than the
   viewport and the page scrolls sideways. Allowing the row to wrap removes the
   overflow without changing the design at any width where it already fits.
   NOTE: index.html has the same overflow and is NOT changed by this build. */
@media (max-width:520px){
  .nav{flex-wrap:wrap;height:auto;padding-top:14px;padding-bottom:14px;row-gap:12px}
}
"""

PRINT = """
@media print{
  .doccontrol,header,footer.site,.themebtn,.skip{display:none!important}
  .notice .notice-wrap{padding:0;max-width:100%}
  .notice{font-size:10.5pt}
  .notice a{color:#000;text-decoration:none}
  .notice .cta{page-break-inside:avoid}
  .notice table{page-break-inside:auto}
  .notice tr{page-break-inside:avoid}
}
"""

FONTS = ('<link href="https://fonts.googleapis.com/css2?'
         'family=IBM+Plex+Mono:wght@400;500;600&'
         'family=IBM+Plex+Sans:wght@400;500;600;700&'
         'family=IBM+Plex+Serif:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">')

url = f"https://phoenixlabconsulting.com/{SLUG}"

page = f"""<!DOCTYPE html>
<!-- Regulatory change notice — built from Marketing_Sept2026/nysdoh-september-2026-changes.html
     by build/build_notice.py. Article text is verbatim; chrome comes from index.html. -->
<html lang="en" data-shop="live">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#c0390e">

<meta property="og:type" content="article">
<meta property="og:site_name" content="Phoenix Laboratory Consulting">
<meta property="og:url" content="{url}">
<meta property="og:title" content="New York clinical laboratory regulations changed on 2 September 2026">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="https://phoenixlabconsulting.com/og-v2.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Phoenix Laboratory Consulting">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="New York clinical laboratory regulations changed on 2 September 2026">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="https://phoenixlabconsulting.com/og-v2.png">

<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-32.png" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{FONTS}

{prepaint}

<style>
/* ===================== site chrome (from index.html) ===================== */
{site_css}
/* ===================== change-notice article ===================== */
{TOKENS}
{art_css}
{CHROME_FIX}
{PRINT}
</style>
__ANALYTICS__
</head>
<body>
<a class="skip" href="#top">Skip to content</a>

{doccontrol}

{header_html}

<main class="notice" id="top">
{art_body}
</main>

{footer_html}

<script>(function(){{var b=document.getElementById('tt');if(!b)return;function lbl(){{b.textContent=document.documentElement.getAttribute('data-theme')==='dark'?'Light':'Dark';}}
var mq=window.matchMedia('(prefers-color-scheme:dark)');
function cur(){{return document.documentElement.getAttribute('data-theme')||(mq.matches?'dark':'light');}}
b.textContent=cur()==='dark'?'Light':'Dark';
b.addEventListener('click',function(){{var n=cur()==='dark'?'light':'dark';document.documentElement.setAttribute('data-theme',n);try{{localStorage.setItem('plc-theme',n);}}catch(e){{}}b.textContent=n==='dark'?'Light':'Dark';}});}})();</script>
</body>
</html>
"""

page = page.replace("__ANALYTICS__", analytics)

# Guard: no template placeholder may reach the published page. This exists because
# __ANALYTICS__ shipped unsubstituted once, dropping analytics and printing the raw
# token into <head>. Catches any future __TOKEN__ too.
_left = sorted(set(re.findall(r"__[A-Z][A-Z0-9_]*__", page)))
if _left:
    sys.exit(f"ERROR: unsubstituted placeholder(s) in output: {', '.join(_left)}. "
             "Nothing written.")

OUT.write_text(page, encoding="utf-8")
print(f"wrote {OUT}  ({len(page):,} bytes)  [analytics: {len(analytics)} chars, placeholders: 0]")
