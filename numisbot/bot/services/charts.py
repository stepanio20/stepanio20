"""Price-history chart rendered with PIL — a dark branded card for Telegram.

One magnitude series → one hue (Katz bronze) on the dark brand surface,
median line + direct value labels on the ends, no chart-junk.
"""
from __future__ import annotations

import io
import statistics

from PIL import Image, ImageDraw, ImageFont

W, H = 1000, 560
BG = "#0D0D0C"
PANEL = "#161412"
INK = "#EDE4DD"
INK_SOFT = "#A99C92"
BAR = "#DCAC98"
BAR_DIM = "#8A6C5C"
MEDIAN = "#E7C1AF"
GRID = "#2A2622"

_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(_FONT_B if bold else _FONT, size)
    except OSError:
        return ImageFont.load_default()


def _money(v: float) -> str:
    return f"€{v:,.0f}".replace(",", " ")


def price_chart(query: str, prices: list[float], lang: str = "ru") -> bytes:
    """Bars = realized prices (oldest→newest auctions, capped at 16)."""
    prices = prices[:16][::-1]  # rows come newest-first; draw oldest → newest
    med = statistics.median(prices)

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    title = f"«{query}» — проходы на Katz" if lang == "ru" else f"“{query}” — Katz results"
    d.text((44, 34), title[:60], font=_font(34, bold=True), fill=INK)
    sub = (f"{len(prices)} продаж · медиана {_money(med)}" if lang == "ru"
           else f"{len(prices)} sales · median {_money(med)}")
    d.text((44, 82), sub, font=_font(22), fill=INK_SOFT)

    # plot area (extra headroom right so direct labels never clip)
    x0, y0, x1, y1 = 44, 150, W - 60, H - 92
    d.rounded_rectangle([x0 - 12, y0 - 22, x1 + 28, y1 + 46], radius=12, fill=PANEL)

    mx = max(prices)
    # light horizontal gridlines at half / max, labeled inside-left
    for gy_val in (mx / 2, mx):
        gy = y1 - (y1 - y0) * (gy_val / mx if mx else 0)
        d.line([x0, gy, x1 + 16, gy], fill=GRID, width=1)
        d.text((x0, gy - 6), _money(gy_val), font=_font(14), fill=INK_SOFT, anchor="ls")
    d.line([x0, y1, x1 + 16, y1], fill=GRID, width=1)

    n = len(prices)
    gap = 8
    bw = max(10, int((x1 - x0 - gap * (n + 1)) / max(n, 1)))
    total_w = n * bw + (n + 1) * gap
    ox = x0 + max(0, (x1 - x0 - total_w) // 2) + gap

    label_last = n - 1
    label_max = prices.index(mx)
    for i, p in enumerate(prices):
        bx = ox + i * (bw + gap)
        bh = int((y1 - y0) * (p / mx)) if mx else 0
        top = y1 - max(bh, 3)
        color = BAR if i in (label_last, label_max) else BAR_DIM
        d.rounded_rectangle([bx, top, bx + bw, y1], radius=4, fill=color)
        if i in (label_last, label_max):  # selective direct labels only
            lx = min(max(bx + bw / 2, x0 + 40), x1 - 20)
            d.text((lx, top - 8), _money(p),
                   font=_font(17, bold=True), fill=INK, anchor="ms")

    # median line over the bars
    my = y1 - (y1 - y0) * (med / mx if mx else 0)
    for lx in range(x0, x1, 14):
        d.line([lx, my, min(lx + 7, x1), my], fill=MEDIAN, width=2)
    d.text((x0 + 2, my - 22), ("медиана" if lang == "ru" else "median"),
           font=_font(16), fill=MEDIAN)

    hint = ("старые → новые аукционы" if lang == "ru" else "older → newer auctions")
    d.text((x0, y1 + 16), hint, font=_font(16), fill=INK_SOFT)
    d.text((x1, H - 34), "@KatzCoinsBot", font=_font(17, bold=True),
           fill=INK_SOFT, anchor="ra")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
