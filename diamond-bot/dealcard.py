"""
Deal-card generation for channel publishing.

Two outputs, mirroring the Dubai bot's channel format:
  1. generate_caption()  -> Telegram HTML caption (FOMO framing, verified badge, contact)
  2. render_card()       -> a PNG infographic (Pillow) for the eye-catching photo post

The PNG is drawn programmatically (no external assets) so it renders anywhere and
stays on-brand. Colors match the report/branding palette.
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
BRAND = {
    "bg1": (13, 27, 42),      # deep navy
    "bg2": (18, 58, 79),      # teal-navy
    "accent": (31, 111, 92),  # emerald
    "gold": (200, 169, 110),
    "ink": (240, 244, 248),
    "muted": (150, 165, 180),
    "card": (255, 255, 255),
}


def _fmt_price(ppc: Optional[float], total: Optional[float]) -> str:
    if ppc:
        return f"${ppc:,.0f}/ct"
    if total:
        return f"${total:,.0f}"
    return "Price on request"


def _title(stone: dict) -> str:
    parts = []
    if stone.get("shape"):
        parts.append(str(stone["shape"]).capitalize())
    if stone.get("carat"):
        parts.append(f"{stone['carat']:g}ct")
    if stone.get("fancy_color"):
        fc = " ".join(x for x in [stone.get("fancy_intensity"), stone.get("fancy_color")] if x)
        parts.append(fc.title())
    elif stone.get("color"):
        parts.append(str(stone["color"]))
    if stone.get("clarity"):
        parts.append(str(stone["clarity"]))
    return " ".join(parts) or "Diamond"


def generate_caption(stone: dict, *, verified: bool = False, contact: str = "",
                     bot_username: str = "DiamondScanBot", is_test: bool = False,
                     match_note: str = "") -> str:
    """Telegram HTML caption. Mirrors the Dubai FOMO style, adapted to diamonds."""
    e = html.escape
    lines: list[str] = []
    if is_test:
        lines.append("Test post\n")

    disc = stone.get("rap_discount")
    if disc is not None and disc <= -1:
        lines.append("\U0001F525 <b>HOT PRICE</b> \U0001F525\n")
    elif stone.get("intent") == "want":
        lines.append("\U0001F50E <b>BUYER LOOKING</b> \U0001F50E\n")
    else:
        lines.append("\U0001F48E <b>NEW STONE</b> \U0001F48E\n")

    lines.append(f"<b>{e(_title(stone))}</b>\n")

    price = _fmt_price(stone.get("price_per_carat"), stone.get("total_price"))
    if disc is not None:
        lines.append(f"\U0001F4B0 <b>{e(price)}</b>  ·  Rap {disc:+g}%\n")
    else:
        lines.append(f"\U0001F4B0 <b>{e(price)}</b>\n")

    details = []
    if stone.get("cut"):
        details.append(f"✂️ Cut {e(str(stone['cut']))}")
    if stone.get("fluorescence"):
        details.append(f"\U0001F526 Fluor {e(str(stone['fluorescence']))}")
    if stone.get("lab") and stone.get("cert_number"):
        details.append(f"\U0001F4C4 {e(str(stone['lab']))} {e(str(stone['cert_number']))}")
    elif stone.get("lab"):
        details.append(f"\U0001F4C4 {e(str(stone['lab']))}")
    if details:
        lines.append("\n".join(details) + "\n")

    if match_note:
        lines.append(f"⚡ <i>{e(match_note)}</i>\n")
    elif stone.get("intent") == "want":
        lines.append("⚡ <i>Have this stone? Tap to connect — first to reply wins.</i>\n")
    else:
        lines.append("⚡ <i>Serious buyers only — DM before it’s gone.</i>\n")

    lines.append("─" * 10)
    lines.append("✅ Verified dealer" if verified else "⏳ Verification pending")
    if contact:
        lines.append(f"\U0001F4DE Contact: {e(contact)}")
    lines.append(f"@{e(bot_username)}")
    return "\n".join(lines)


def render_card(stone: dict, out_path: str, *, verified: bool = False,
                subtitle: str = "New on the Dubai desk") -> Optional[str]:
    """Render a PNG deal card. Returns the path, or None if Pillow is unavailable."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    W, H = 1080, 1080
    img = Image.new("RGB", (W, H), BRAND["bg1"])
    d = ImageDraw.Draw(img)

    # vertical gradient
    for y in range(H):
        t = y / H
        r = int(BRAND["bg1"][0] * (1 - t) + BRAND["bg2"][0] * t)
        g = int(BRAND["bg1"][1] * (1 - t) + BRAND["bg2"][1] * t)
        b = int(BRAND["bg1"][2] * (1 - t) + BRAND["bg2"][2] * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    def font(sz, bold=True):
        for name in ([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        ]):
            try:
                return ImageFont.truetype(name, sz)
            except Exception:
                continue
        return ImageFont.load_default()

    def center(text, y, f, fill):
        bb = d.textbbox((0, 0), text, font=f)
        d.text(((W - (bb[2] - bb[0])) / 2, y), text, font=f, fill=fill)

    def fit_font(text, start, min_sz, max_w, bold=True):
        sz = start
        while sz > min_sz:
            f = font(sz, bold)
            bb = d.textbbox((0, 0), text, font=f)
            if bb[2] - bb[0] <= max_w:
                return f
            sz -= 3
        return font(min_sz, bold)

    # header ribbon
    disc = stone.get("rap_discount")
    ribbon = "HOT PRICE" if (disc is not None and disc <= -1) else \
             ("BUYER LOOKING" if stone.get("intent") == "want" else "NEW STONE")
    d.rounded_rectangle([W/2 - 200, 90, W/2 + 200, 170], radius=40, fill=BRAND["accent"])
    center(ribbon, 108, font(46), BRAND["ink"])

    # diamond glyph
    cx, cy, s = W / 2, 330, 78
    d.polygon([(cx, cy - s), (cx + s, cy - s/3), (cx, cy + s), (cx - s, cy - s/3)],
              outline=BRAND["gold"], width=6)
    d.line([(cx - s, cy - s/3), (cx + s, cy - s/3)], fill=BRAND["gold"], width=4)
    d.line([(cx, cy - s), (cx, cy + s)], fill=BRAND["gold"], width=2)

    # title (auto-fit to width)
    center(_title(stone), 460, fit_font(_title(stone), 76, 40, W - 120), BRAND["ink"])
    center(subtitle, 552, font(34, bold=False), BRAND["muted"])

    # price block
    price = _fmt_price(stone.get("price_per_carat"), stone.get("total_price"))
    center(price, 640, font(88), BRAND["gold"])
    if disc is not None:
        center(f"Rap {disc:+g}%", 745, font(40, bold=False), BRAND["muted"])

    # attribute chips
    chips = []
    if stone.get("lab"):
        chips.append(f"{stone['lab']}" + (f" {stone['cert_number']}" if stone.get("cert_number") else ""))
    if stone.get("cut"):
        chips.append(f"Cut {stone['cut']}")
    if stone.get("fluorescence"):
        chips.append(f"Fl {stone['fluorescence']}")
    y = 830
    fchip = font(34, bold=False)
    xs = 0
    widths = [d.textbbox((0, 0), c, font=fchip)[2] + 60 for c in chips]
    total_w = sum(widths) + 20 * (len(chips) - 1 if chips else 0)
    x = (W - total_w) / 2
    for c, w in zip(chips, widths):
        d.rounded_rectangle([x, y, x + w, y + 62], radius=31, outline=BRAND["muted"], width=2)
        bb = d.textbbox((0, 0), c, font=fchip)
        d.text((x + (w - (bb[2] - bb[0])) / 2, y + 12), c, font=fchip, fill=BRAND["ink"])
        x += w + 20

    # verified badge + footer (no emoji — DejaVu can't render them; draw a check mark)
    badge = "VERIFIED DEALER" if verified else "VERIFICATION PENDING"
    bcol = BRAND["accent"] if verified else BRAND["muted"]
    bf = font(36)
    bb = d.textbbox((0, 0), badge, font=bf)
    bw = bb[2] - bb[0]
    bx = (W - bw) / 2
    if verified:
        # drawn checkmark to the left of the text
        d.line([(bx - 46, 958), (bx - 34, 972), (bx - 12, 944)], fill=bcol, width=6)
    d.text((bx, 940), badge, font=bf, fill=bcol)
    center("DiamondScan · Dubai diamond radar", 1000, font(30, bold=False), BRAND["muted"])

    img.save(out_path, "PNG")
    return out_path


if __name__ == "__main__":
    demo = {"shape": "cushion", "carat": 0.90, "fancy_color": "pink",
            "fancy_intensity": "fancy light", "clarity": "SI1", "lab": "GIA",
            "cert_number": "2185763456", "price_per_carat": 26000, "rap_discount": -18,
            "cut": "EX", "fluorescence": "none", "intent": "have"}
    print(generate_caption(demo, verified=True, contact="+971 56 000 0000"))
    p = render_card(demo, str(BASE_DIR / "branding" / "sample_dealcard.png"), verified=True)
    print("card:", p)
