"""Wrap an artifact-style HTML fragment into a standalone offline document.

Pages written for the Artifact host omit <!doctype>/<head> — the host adds
them. Opened straight from disk (iOS Files, email attachment, Telegram
preview) that means no charset (Cyrillic turns into mojibake) and no
viewport (desktop-width layout on a phone). This adds both.

Usage: python -m scripts.make_standalone src.html dst.html
"""
from __future__ import annotations

import re
import sys

HEAD = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
{title}<style>
*,*::before,*::after{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%}}
body{{margin:0}}
img,svg{{max-width:100%;height:auto}}
</style>
</head>
<body>
"""

TAIL = "\n</body>\n</html>\n"


def wrap(src: str, dst: str) -> None:
    html = open(src, encoding="utf-8").read()
    if html.lstrip().lower().startswith("<!doctype"):
        open(dst, "w", encoding="utf-8").write(html)
        return
    m = re.search(r"<title>.*?</title>\s*", html, re.IGNORECASE | re.DOTALL)
    title = m.group(0).strip() + "\n" if m else ""
    body = html[m.end():] if m else html
    open(dst, "w", encoding="utf-8").write(HEAD.format(title=title) + body + TAIL)


if __name__ == "__main__":
    wrap(sys.argv[1], sys.argv[2])
