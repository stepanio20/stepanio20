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


def draw_brilliant(d, cx: float, cy: float, s: float, color, width: int = 6) -> None:
    """Draw a clean round-brilliant diamond outline (crown table + pavilion facets).

    Shared by the deal card, the match card and the branding avatar so the mark
    is identical everywhere. `s` is the half-width of the stone.
    """
    tw = s * 0.46            # half table width
    ty = cy - s * 0.42       # table (girdle-crown) height
    gL, gR = cx - s, cx + s  # girdle corners
    tip = cy + s             # pavilion tip
    # crown outline (table + two crown flanks down to the girdle)
    d.polygon([(cx - tw, cy - s), (cx + tw, cy - s), (gR, ty), (gL, ty)],
              outline=color, width=width)
    # pavilion (girdle down to the culet tip)
    d.polygon([(gL, ty), (gR, ty), (cx, tip)], outline=color, width=width)
    # crown facet lines
    d.line([(cx - tw, cy - s), (gL, ty)], fill=color, width=max(2, width - 3))
    d.line([(cx + tw, cy - s), (gR, ty)], fill=color, width=max(2, width - 3))
    d.line([(cx - tw, cy - s), (cx + tw, cy - s)], fill=color, width=max(2, width - 3))
    # pavilion facet lines converging to the tip
    for gx in (gL, cx - tw, cx, cx + tw, gR):
        d.line([(gx, ty), (cx, tip)], fill=color, width=max(2, width - 4))


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

    # diamond glyph (shared brilliant-cut mark)
    draw_brilliant(d, W / 2, 320, 82, BRAND["gold"], width=6)

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


def match_caption(demand: dict, listing: dict, score: float, *,
                  seller_contact: str = "", revealed: bool = False,
                  bot_username: str = "DiamondScanBot") -> str:
    """Telegram HTML caption for a buyer↔seller match alert."""
    e = html.escape
    lines = [f"⚡ <b>MATCH FOUND</b> · {score:.0%}\n"]
    want = demand.get("raw_text") or _title(demand)
    lines.append(f"\U0001F50E <b>You wanted:</b> <i>{e(str(want)[:90])}</i>")
    lines.append(f"\U0001F48E <b>Now available:</b> <b>{e(_title(listing))}</b>")
    price = _fmt_price(listing.get("price_per_carat"), listing.get("total_price"))
    disc = listing.get("rap_discount")
    lines.append(f"\U0001F4B0 {e(price)}" + (f"  ·  Rap {disc:+g}%" if disc is not None else "") + "\n")
    if revealed and seller_contact:
        lines.append(f"\U0001F91D <b>Seller:</b> {e(seller_contact)}")
        lines.append("<i>Verify the GIA laser inscription before paying.</i>")
    else:
        lines.append("\U0001F91D <i>Tap Connect to reach the seller.</i>")
    lines.append(f"@{e(bot_username)}")
    return "\n".join(lines)


def render_match_card(demand: dict, listing: dict, score: float, out_path: str, *,
                      buyer_contact: str = "", seller_contact: str = "",
                      revealed: bool = False) -> Optional[str]:
    """Render the money-moment card: a buyer request linked to a seller's stone."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    W, H = 1080, 1080
    img = Image.new("RGB", (W, H), BRAND["bg1"])
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(
            int(BRAND["bg1"][i] * (1 - t) + BRAND["bg2"][i] * t) for i in range(3)))

    def font(sz, bold=True):
        for name in (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        ):
            try:
                return ImageFont.truetype(name, sz)
            except Exception:
                continue
        return ImageFont.load_default()

    def center(text, y, f, fill):
        bb = d.textbbox((0, 0), text, font=f)
        d.text(((W - (bb[2] - bb[0])) / 2, y), text, font=f, fill=fill)

    def fit(text, start, min_sz, max_w, bold=True):
        sz = start
        while sz > min_sz:
            f = font(sz, bold)
            if d.textbbox((0, 0), text, font=f)[2] <= max_w:
                return f
            sz -= 3
        return font(min_sz, bold)

    def panel(y0, y1, label, title, sub, lcol):
        # outline-only card on the dark gradient (no fill: RGBA alpha would flatten to solid)
        d.rounded_rectangle([70, y0, W - 70, y1], radius=28, outline=lcol, width=3)
        d.text((100, y0 + 26), label, font=font(30), fill=lcol)
        center(title, y0 + 78, fit(title, 56, 30, W - 260), BRAND["ink"])
        if sub:
            center(sub, y0 + 150, font(30, bold=False), BRAND["muted"])

    def compact(stone: dict, limit: int = 40) -> str:
        t = _title(stone)
        if t and t != "Diamond":
            return t
        raw = str(stone.get("raw_text") or "").strip()
        return (raw[:limit] + "…") if len(raw) > limit else (raw or "Buyer request")

    # header
    d.rounded_rectangle([W/2 - 250, 70, W/2 + 250, 156], radius=43, fill=BRAND["gold"])
    center("✦  MATCH FOUND  ✦", 92, font(44), BRAND["bg1"])
    center(f"{score:.0%} fit", 180, font(38, bold=False), BRAND["muted"])

    # BUYER panel
    panel(250, 470, "BUYER WANTS", compact(demand),
          buyer_contact if revealed else "on the radar", BRAND["accent"])

    # connector diamond in the middle
    draw_brilliant(d, W / 2, 505, 42, BRAND["gold"], width=5)

    # SELLER panel
    price = _fmt_price(listing.get("price_per_carat"), listing.get("total_price"))
    disc = listing.get("rap_discount")
    subttl = price + (f"  ·  Rap {disc:+g}%" if disc is not None else "")
    panel(560, 800, "SELLER HAS", _title(listing), subttl, BRAND["gold"])

    # contact / CTA
    if revealed and seller_contact:
        center("✓ Seller: " + seller_contact, 852, font(38), BRAND["gold"])
    else:
        center("Tap Connect to reveal the seller", 852, font(36, bold=False), BRAND["muted"])
    center("Verify the laser inscription before paying", 906, font(28, bold=False), BRAND["muted"])
    center("DiamondScan · Dubai diamond radar", 1004, font(30, bold=False), BRAND["muted"])

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

    want = {"shape": "cushion", "carat": 0.9, "fancy_color": "pink",
            "clarity": "SI1", "intent": "want",
            "raw_text": "Looking for cushion ~0.9ct fancy pink SI GIA, Dubai"}
    m = render_match_card(want, demo, 0.92,
                          str(BASE_DIR / "branding" / "sample_matchcard.png"),
                          buyer_contact="@dubai_buyer", seller_contact="+971 56 000 0000",
                          revealed=True)
    print("match card:", m)
    print(match_caption(want, demo, 0.92, seller_contact="+971 56 000 0000", revealed=True))
