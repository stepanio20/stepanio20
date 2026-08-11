"""Generate brand assets (avatar, promo banner) with a real brilliant-cut diamond mark.
Run: python branding/make_branding.py    Output PNGs land next to this file."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from dealcard import draw_brilliant  # shared clean brilliant-cut mark  # noqa: E402
NAVY1, NAVY2 = (10, 22, 40), (18, 58, 79)
EMERALD = (31, 111, 92)
GOLD = (206, 175, 120)
GOLD_HI = (232, 210, 165)
INK = (240, 244, 248)
MUTED = (150, 165, 180)


def font(sz, bold=True):
    base = "/usr/share/fonts/truetype/dejavu/"
    for n in ([base + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")]):
        try:
            return ImageFont.truetype(n, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def gradient(w, h, c1=NAVY1, c2=NAVY2, diagonal=True):
    img = Image.new("RGB", (w, h), c1)
    d = ImageDraw.Draw(img)
    span = (w + h) if diagonal else h
    for i in range(span):
        t = i / span
        col = tuple(int(c1[k] * (1 - t) + c2[k] * t) for k in range(3))
        if diagonal:
            d.line([(i, 0), (0, i)], fill=col)
        else:
            d.line([(0, i), (w, i)], fill=col)
    return img


def make_avatar(size=1024):
    img = gradient(size, size)
    d = ImageDraw.Draw(img)
    # subtle vignette ring
    d.ellipse([size * 0.06, size * 0.06, size * 0.94, size * 0.94], outline=MUTED, width=2)
    draw_brilliant(d, size / 2, size * 0.38, size * 0.22, GOLD, width=7)
    # wordmark
    f = font(int(size * 0.11))
    txt = "DiamondScan"
    bb = d.textbbox((0, 0), txt, font=f)
    d.text(((size - (bb[2] - bb[0])) / 2, size * 0.70), txt, font=f, fill=INK)
    f2 = font(int(size * 0.045), bold=False)
    sub = "DUBAI  DIAMOND  RADAR"
    bb2 = d.textbbox((0, 0), sub, font=f2)
    d.text(((size - (bb2[2] - bb2[0])) / 2, size * 0.82), sub, font=f2, fill=GOLD)
    out = HERE / "avatar.png"
    img.save(out)
    return out


def make_banner(w=1280, h=720):
    img = gradient(w, h)
    d = ImageDraw.Draw(img)
    draw_brilliant(d, w * 0.80, h * 0.5, h * 0.30, GOLD, width=8)
    d.text((90, 130), "Stop scrolling", font=font(64, bold=False), fill=MUTED)
    d.text((90, 210), "group history", font=font(64, bold=False), fill=MUTED)
    big = font(92)
    d.text((90, 300), "by hand.", font=big, fill=INK)
    # accent underline
    d.rounded_rectangle([92, 410, 320, 420], radius=5, fill=EMERALD)
    d.text((90, 450), "DiamondScan finds the stone —", font=font(40), fill=INK)
    d.text((90, 500), "and the buyer — for you.", font=font(40), fill=INK)
    d.text((90, 600), "The Dubai diamond radar", font=font(34, bold=False), fill=GOLD)
    d.text((90, 645), "t.me/DiamondScanBot", font=font(34), fill=INK)
    out = HERE / "promo_banner.png"
    img.save(out)
    return out


def make_square_promo(size=1080):
    img = gradient(size, size)
    d = ImageDraw.Draw(img)
    draw_brilliant(d, size / 2, size * 0.30, size * 0.17, GOLD, width=7)
    def center(txt, y, f, fill):
        bb = d.textbbox((0, 0), txt, font=f)
        d.text(((size - (bb[2] - bb[0])) / 2, y), txt, font=f, fill=fill)
    center("2ct D VS1 GIA?", size * 0.46, font(70), INK)
    center("Someone in the group has it.", size * 0.55, font(40, bold=False), MUTED)
    center("We already found it.", size * 0.61, font(40, bold=False), MUTED)
    d.rounded_rectangle([size*0.30, size*0.72, size*0.70, size*0.80], radius=40, fill=EMERALD)
    center("Try DiamondScan", size*0.735, font(38), INK)
    center("t.me/DiamondScanBot", size*0.85, font(34, bold=False), GOLD)
    out = HERE / "promo_square.png"
    img.save(out)
    return out


if __name__ == "__main__":
    print(make_avatar())
    print(make_banner())
    print(make_square_promo())
