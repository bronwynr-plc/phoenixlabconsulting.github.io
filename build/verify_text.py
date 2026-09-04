#!/usr/bin/env python3
"""Prove the built page's article text is identical to the verified source."""
import re, sys, html, difflib, pathlib

def visible(s, only_main=False):
    if only_main:
        s = re.search(r'(?s)<main class="notice".*?>(.*)</main>', s).group(1)
    else:
        s = re.search(r"(?s)<body>(.*)</body>", s).group(1)
    s = re.sub(r"(?s)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?s)<!--.*?-->", " ", s)
    s = re.sub(r"<[^>]+>", "\n", s)
    s = html.unescape(s)
    return [l.strip() for l in s.split("\n") if l.strip()]

src  = visible(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
new  = visible(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"), only_main=True)

d = list(difflib.unified_diff(src, new, "SOURCE(verified)", "BUILT(article)", lineterm="", n=1))
if not d:
    print("PASS: article text is character-identical to the verified source.")
else:
    print("DIFFERENCES FOUND (%d lines):" % len(d))
    print("\n".join(d))
    sys.exit(1)
