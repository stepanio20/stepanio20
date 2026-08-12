"""
Diamond chat-message parser.

Turns free-text dealer messages ("have" offers and "looking-for" demands) into a
canonical, machine-matchable record aligned with the de-facto RapNet upload schema.

Design notes
------------
* Regex-first, deterministic, and dependency-free so it runs anywhere and is unit-testable.
* `parse_message()` returns a `ParsedStone` (or None if it doesn't look like a stone).
* Handles the compact dealer shorthand seen in real groups, e.g.
    "GIA Cushion 0.90ct Fancy light Pink SI1 $26.000 per ct"
    "Pear shape 3.24ct D-IF"
    "LOOKING FOR 2ct D VS1 GIA, Rap -25%"
* An optional LLM fallback (`llm_parse`) can be wired in for the long tail; the regex
  core intentionally covers the bulk so the product works with zero API cost.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Optional


# ─────────────────────────── canonical vocabularies ───────────────────────────

class Intent(str, Enum):
    HAVE = "have"        # seller offering a stone
    WANT = "want"        # buyer looking for a stone
    UNKNOWN = "unknown"


SHAPES = {
    "round": ["round", "rbc", "brilliant", "rd", "rnd", "bril"],
    "princess": ["princess", "prin", "pr"],
    "cushion": ["cushion", "cush", "cu"],
    "oval": ["oval", "ov"],
    "emerald": ["emerald", "em", "emrld"],
    "pear": ["pear", "ps", "pear shape", "pearshape"],
    "marquise": ["marquise", "marq", "mq"],
    "asscher": ["asscher", "ash"],
    "radiant": ["radiant", "rad"],
    "heart": ["heart", "hs", "ht"],
    "trilliant": ["trilliant", "trillion", "tri"],
    "baguette": ["baguette", "bag"],
}

# color: D–Z, plus fancy colors
FANCY_COLORS = [
    "pink", "blue", "yellow", "green", "orange", "red", "purple",
    "violet", "brown", "champagne", "cognac", "gray", "grey", "black",
]
# "white" is universal dealer slang for colorless (D–F), NOT a fancy color — never treat it as fancy.
FANCY_INTENSITY = [
    "faint", "very light", "light", "fancy light", "fancy",
    "fancy intense", "intense", "fancy vivid", "vivid", "fancy deep", "deep", "fancy dark",
]

CLARITIES = ["fl", "if", "vvs1", "vvs2", "vs1", "vs2", "si1", "si2", "si3", "i1", "i2", "i3"]
CUT_GRADES = {"3ex": "3EX", "ex": "EX", "excellent": "EX", "vg": "VG", "gd": "GD", "good": "VG"}
LABS = ["gia", "igi", "hrd", "gcal", "gsi", "egl"]
FLUORESCENCE = ["none", "nil", "faint", "medium", "med", "strong", "very strong", "vst"]


# ───────────────────────────── result container ──────────────────────────────

@dataclass
class ParsedStone:
    intent: str = Intent.UNKNOWN.value
    shape: Optional[str] = None
    carat: Optional[float] = None
    carat_min: Optional[float] = None          # for demands expressed as a range
    carat_max: Optional[float] = None
    color: Optional[str] = None                # D..Z (uppercase) for white
    fancy_color: Optional[str] = None          # e.g. "pink"
    fancy_intensity: Optional[str] = None      # e.g. "fancy intense"
    clarity: Optional[str] = None              # uppercase, e.g. "VS1"
    cut: Optional[str] = None                  # EX/VG/GD/3EX
    lab: Optional[str] = None                  # GIA/IGI/HRD...
    cert_number: Optional[str] = None          # 5–12 digit report number if present
    fluorescence: Optional[str] = None
    price_per_carat: Optional[float] = None    # USD/ct
    total_price: Optional[float] = None        # USD
    rap_discount: Optional[float] = None       # negative = below Rap, e.g. -25.0
    raw_text: str = ""
    confidence: float = 0.0                    # 0..1 heuristic
    flags: list = field(default_factory=list)  # e.g. ["scam_suspect", "lab_grown"]

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items()}

    def key_summary(self) -> str:
        """Short human label used in match cards, e.g. 'Cushion 0.90ct Fancy Light Pink SI1'."""
        parts = []
        if self.shape:
            parts.append(self.shape.capitalize())
        if self.carat:
            parts.append(f"{self.carat:g}ct")
        elif self.carat_min or self.carat_max:
            lo = f"{self.carat_min:g}" if self.carat_min else ""
            hi = f"{self.carat_max:g}" if self.carat_max else ""
            parts.append(f"{lo}-{hi}ct")
        if self.fancy_color:
            fc = " ".join(x for x in [self.fancy_intensity, self.fancy_color] if x)
            parts.append(fc.title())
        elif self.color:
            parts.append(self.color)
        if self.clarity:
            parts.append(self.clarity)
        if self.lab:
            parts.append(self.lab)
        return " ".join(parts) if parts else "(unparsed)"


# ─────────────────────────────── regexes ─────────────────────────────────────

# carat accepts a dot OR comma decimal (RU/EU/HE dealers write "1,50ct"); converted in parse.
_CARAT_RE = re.compile(
    r"(?<![\d.,])(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:ct|cts|carat|carats|c)\b", re.I,
)
_CARAT_RANGE_RE = re.compile(
    r"(\d{1,2}(?:[.,]\d{1,2})?)\s*[-–to]{1,3}\s*(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:ct|cts|carat|carats)\b", re.I,
)
_WHITE_COLOR_RE = re.compile(r"\b([D-N])\b(?!['a-z])")
# bare-decimal carat fallback, e.g. "Round 1.01 G VS2" (no 'ct' suffix)
_BARE_CARAT_RE = re.compile(r"(?<![\$\d.])\b(\d{1,2}\.\d{1,2})\b(?!\s*%)")
_CLARITY_RE = re.compile(r"\b(FL|IF|VVS[12]|VS[12]|SI[123]|I[123])\b", re.I)
_CERT_RE = re.compile(r"\b(\d{7,12})\b")
_PRICE_PER_CT_RE = re.compile(
    r"(?:\$|usd|aed|د\.إ)\s*([\d.,]+)\s*(?:/|per\s*)?\s*(?:ct|carat|c)\b", re.I,
)
# symbol-less per-carat, common in Dubai ("5040/ct", "26000 per ct"); guarded by min value in parse.
_PRICE_PER_CT_BARE_RE = re.compile(
    r"(?<![\d.,])([\d.,]{3,})\s*(?:/\s*ct|per\s*ct|per\s*carat|p\s*/?\s*c)\b", re.I,
)
_PRICE_TOTAL_RE = re.compile(r"(?:\$|usd|aed)\s*([\d.,]+)\b", re.I)
_RAP_RE = re.compile(r"rap\s*(?:net)?\s*([+-]?\s*\d{1,2}(?:\.\d)?)\s*%?", re.I)
_DISCOUNT_PCT_RE = re.compile(r"([+-]\s*\d{1,2}(?:\.\d)?)\s*%")

_WANT_HINTS = re.compile(
    r"\b(looking for|look for|lf|want|wtb|need|required?|require|searching|search for|demand|"
    r"anyone (?:have|has)|who (?:has|have)|in the market for|rfq|requirement)\b", re.I,
)
_HAVE_HINTS = re.compile(
    r"\b(available|avail|in stock|for sale|fs|offer(?:ing)?|selling|we have|i have|have\b|"
    r"stock list|today deal|deal of|on hand|ready stock|wts|for offer)\b", re.I,
)
_LABGROWN_HINTS = re.compile(r"\b(lab[\s-]?grown|labgrown|lgd|cvd|hpht|synthetic|created|lab\b)\b", re.I)
_SCAM_HINTS = re.compile(
    r"\b(western union|advance fee|inheritance|prophet|pastor|god bless|"
    r"crypto giveaway|double your|investment opportunity|wire transfer fee)\b", re.I,
)


def _norm_number(s: str) -> Optional[float]:
    """Parse dealer number formats. '$26.000' → 26000; '5,040' → 5040; '32,000' → 32000."""
    s = s.strip().replace(" ", "")
    if not s:
        return None
    # European thousand-dot like 26.000 (3 trailing digits, no other dot) → 26000
    if re.fullmatch(r"\d{1,3}\.\d{3}", s):
        s = s.replace(".", "")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _find_shape(text: str) -> Optional[str]:
    low = text.lower()
    for canon, variants in SHAPES.items():
        for v in sorted(variants, key=len, reverse=True):
            if re.search(rf"\b{re.escape(v)}\b", low):
                return canon
    return None


def _find_fancy(text: str) -> tuple[Optional[str], Optional[str]]:
    low = text.lower()
    color = None
    for c in FANCY_COLORS:
        if re.search(rf"\b{c}\b", low):
            color = "gray" if c == "grey" else c
            break
    if not color:
        return None, None
    intensity = None
    for it in sorted(FANCY_INTENSITY, key=len, reverse=True):
        if re.search(rf"\b{re.escape(it)}\b", low):
            intensity = it
            break
    return color, intensity


def detect_intent(text: str) -> str:
    want = bool(_WANT_HINTS.search(text))
    have = bool(_HAVE_HINTS.search(text))
    if want and not have:
        return Intent.WANT.value
    if have and not want:
        return Intent.HAVE.value
    if want and have:
        # "looking for ... i have alternatives" — lean WANT if a demand verb leads
        w = _WANT_HINTS.search(text).start()
        h = _HAVE_HINTS.search(text).start()
        return Intent.WANT.value if w < h else Intent.HAVE.value
    return Intent.UNKNOWN.value


def parse_message(text: str, default_intent: Optional[str] = None) -> Optional[ParsedStone]:
    """
    Parse a single chat message into a ParsedStone.

    Returns None if the message shows no diamond signal at all (so callers can skip chatter).
    `default_intent` lets a caller pass the group's known nature (e.g. a demand-only group).
    """
    if not text or not text.strip():
        return None
    original = text.strip()
    low = original.lower()

    st = ParsedStone(raw_text=original)

    # carat (range first, then single); accept comma decimals ("1,50ct" → 1.5)
    m = _CARAT_RANGE_RE.search(original)
    if m:
        st.carat_min = float(m.group(1).replace(",", "."))
        st.carat_max = float(m.group(2).replace(",", "."))
    m = _CARAT_RE.search(original)
    if m:
        st.carat = float(m.group(1).replace(",", "."))

    st.shape = _find_shape(original)

    # Fallback: bare decimal carat ("Round 1.01 G VS2") once we know it looks like a stone.
    if st.carat is None and st.carat_min is None:
        bm = _BARE_CARAT_RE.search(original)
        if bm and (st.shape or _CLARITY_RE.search(original) or _WHITE_COLOR_RE.search(original)):
            val = float(bm.group(1))
            if 0.15 <= val <= 30:
                st.carat = val

    # fancy vs white color
    fc, fi = _find_fancy(original)
    if fc:
        st.fancy_color = fc
        st.fancy_intensity = fi or "fancy"
    else:
        cm = _WHITE_COLOR_RE.search(original)
        if cm:
            st.color = cm.group(1).upper()

    cl = _CLARITY_RE.search(original)
    if cl:
        st.clarity = cl.group(1).upper()

    for lab in LABS:
        if re.search(rf"\b{lab}\b", low):
            st.lab = lab.upper()
            break

    for tok, canon in CUT_GRADES.items():
        if re.search(rf"\b{re.escape(tok)}\b", low):
            st.cut = canon
            break

    for fl in sorted(FLUORESCENCE, key=len, reverse=True):
        if re.search(rf"\bfl(?:uor)?\w*\s+{re.escape(fl)}\b", low) or \
           re.search(rf"\b{re.escape(fl)}\s+fluor", low):
            st.fluorescence = "none" if fl == "nil" else fl
            break

    # price per carat ($/usd/aed, then symbol-less "…/ct"), then total
    m = _PRICE_PER_CT_RE.search(original)
    if m:
        st.price_per_carat = _norm_number(m.group(1))
    else:
        bm = _PRICE_PER_CT_BARE_RE.search(original)
        if bm:
            v = _norm_number(bm.group(1))
            if v and v >= 100:  # ignore tiny numbers (carats/counts); no real $/ct is under $100
                st.price_per_carat = v
        if st.price_per_carat is None:
            m = _PRICE_TOTAL_RE.search(original)
            if m:
                st.total_price = _norm_number(m.group(1))

    # Rap discount / premium
    m = _RAP_RE.search(original)
    if m:
        st.rap_discount = float(m.group(1).replace(" ", ""))
    else:
        m = _DISCOUNT_PCT_RE.search(original)
        if m and re.search(r"\brap\b|\bback\b|\boff\b", low):
            st.rap_discount = float(m.group(1).replace(" ", ""))

    # cert number: only trust a bare 7–12 digit run when a lab is named or 'cert'/'report' nearby
    if st.lab or re.search(r"\b(cert|certificate|report|no\.?)\b", low):
        cm = _CERT_RE.search(original)
        if cm:
            st.cert_number = cm.group(1)

    # intent
    st.intent = detect_intent(original)
    if st.intent == Intent.UNKNOWN.value and default_intent:
        st.intent = default_intent

    # flags
    if _LABGROWN_HINTS.search(original):
        st.flags.append("lab_grown")
    if _SCAM_HINTS.search(original):
        st.flags.append("scam_suspect")

    # confidence: reward the presence of core attributes
    filled = sum(bool(x) for x in [st.shape, st.carat or st.carat_min, st.color or st.fancy_color, st.clarity])
    st.confidence = round(min(1.0, 0.25 * filled + (0.1 if st.lab else 0) + (0.1 if (st.price_per_carat or st.total_price) else 0)), 2)

    # If nothing diamond-ish was found, bail (avoid indexing pure chatter)
    if filled == 0 and not st.lab and not (st.price_per_carat or st.total_price):
        return None
    return st


def llm_parse(text: str, api_key: str) -> Optional[ParsedStone]:  # pragma: no cover
    """
    Optional long-tail fallback using an LLM. Wired but off by default (regex covers the bulk).
    Kept as a thin interface so the product costs $0 to parse until you flip it on.
    """
    raise NotImplementedError(
        "LLM fallback is a deliberate no-op in the MVP. Implement with the Anthropic SDK "
        "when regex confidence < 0.5 on high-value groups."
    )


if __name__ == "__main__":  # quick manual check
    samples = [
        "Today deal 1.43ct oval Fancy intense pink $32,000 per ct",
        "GIA Cushion 0.90ct Fancy light Pink SI1 TOP TOP SI1 like VS $26.000 per ct",
        "Pear shape 3.24ct D-IF",
        "LOOKING FOR 2ct D VS1 GIA only, Rap -25%",
        "Available: Round 1.01 G VS2 GIA 2185763456 Rap -22%",
        "good morning everyone",
    ]
    for s in samples:
        r = parse_message(s)
        print(f"{s!r}\n  -> {r.key_summary() if r else None} | intent={r.intent if r else '-'} "
              f"| conf={r.confidence if r else '-'}\n")
