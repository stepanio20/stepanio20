"""
Ingestion paths (the defensible ones, per the market study):

  1. forward()        — a dealer forwards messages/stock into the bot (opt-in, zero risk)
  2. import_csv()     — a supplier uploads a stock file in the RapNet-ish schema
  3. TelethonIngestor — per-subscriber BYO-session read-only reader for Telegram groups
                        the subscriber ALREADY belongs to (Telegram-sanctioned for user
                        sessions; never a central scraper account)

There is deliberately NO WhatsApp central-scraping path: covert WhatsApp parsing is a
ToS/ban/legal non-starter (see the market report §5).

The Telethon class is import-guarded so the bot runs without Telethon installed; the
group ingestor is opt-in and run per consenting subscriber.
"""
from __future__ import annotations

import csv
import io
from typing import Callable, Iterable, Optional

from parser import parse_message, Intent, SHAPES, FANCY_COLORS, FANCY_INTENSITY, CLARITIES
import db


# ─────────────────────────── forward / manual ────────────────────────────────

def ingest_text(text: str, *, tg_id: Optional[int] = None, source: str = "forward",
                source_group: str = "", default_intent: Optional[str] = None) -> Optional[dict]:
    """Parse one message and store it as a listing or demand. Returns a summary dict."""
    stone = parse_message(text, default_intent=default_intent)
    if not stone:
        return None
    if "scam_suspect" in stone.flags:
        db.log_event("scam_filtered", tg_id, {"text": text[:200]})
        return {"stored": False, "reason": "scam_suspect", "summary": stone.key_summary()}
    payload = stone.to_dict()
    if stone.intent == Intent.WANT.value:
        did = db.add_demand(payload, tg_id=tg_id, source=source, source_group=source_group)
        return {"stored": True, "kind": "demand", "id": did, "summary": stone.key_summary(),
                "confidence": stone.confidence}
    else:
        lid = db.add_listing(payload, tg_id=tg_id, source=source, source_group=source_group)
        return {"stored": True, "kind": "listing", "id": lid, "summary": stone.key_summary(),
                "confidence": stone.confidence}


# ─────────────────────────── stock file (CSV / Excel) ────────────────────────
#
# Real seller files (RapNet-ish, but messy) — headers map case-insensitively with
# spaces/underscores/'#'/'%' stripped. Covers the columns dealers actually send:
# Stock #, Availability, Shape, Weight, Color, shade colour, Fancy Color Intensity,
# Clarity, Cut, Fluorescence Intensity, Measurements, Lab, Report #, Growth Type, …

_HEADER_MAP = {
    "s": "nature", "type": "nature", "naturalorlabgrown": "nature",
    "stock": "stock", "stockno": "stock", "stocknumber": "stock", "stockid": "stock",
    "availability": "availability", "status": "availability", "avail": "availability",
    "shape": "shape",
    "weight": "carat", "carat": "carat", "caratweight": "carat", "cts": "carat",
    "carats": "carat", "size": "carat",
    "color": "color", "colour": "color", "col": "color",
    "clarity": "clarity", "cla": "clarity", "clar": "clarity",
    "flr": "fluorescence", "flu": "fluorescence",
    "pol": "polish", "sym": "symmetry",
    "price": "price_per_carat", "wgt": "carat",
    "shadecolour": "fancy_color", "shadecolor": "fancy_color",
    "fancycolor": "fancy_color", "fancycolour": "fancy_color",
    "fancycolorintensity": "fancy_intensity", "fancycolourintensity": "fancy_intensity",
    "fancyintensity": "fancy_intensity", "intensity": "fancy_intensity",
    "clarity": "clarity",
    "cut": "cut", "cutgrade": "cut",
    "polish": "polish", "symmetry": "symmetry", "sym": "symmetry",
    "fluorescence": "fluorescence", "fluorescenceintensity": "fluorescence",
    "fluor": "fluorescence", "flo": "fluorescence",
    "measurements": "measurements", "measurement": "measurements", "meas": "measurements",
    "lab": "lab", "labname": "lab", "laboratory": "lab",
    "certificate": "cert_number", "certno": "cert_number", "certnumber": "cert_number",
    "reportnumber": "cert_number", "report": "cert_number", "reportno": "cert_number",
    "certification": "cert_number", "certificateno": "cert_number",
    "treatment": "treatment", "growthtype": "growth", "growth": "growth", "type": "nature",
    "depth": "depth", "table": "table_pct",
    "cashprice": "total_price", "totalprice": "total_price", "amount": "total_price",
    "priceperct": "price_per_carat", "pricepercarat": "price_per_carat",
    "pricecrt": "price_per_carat", "pricect": "price_per_carat", "ppc": "price_per_carat",
    "rapnetdiscountpercent": "rap_discount", "discount": "rap_discount",
    "rapdiscount": "rap_discount", "rap": "rap_discount", "back": "rap_discount",
    "off": "rap_discount", "offrap": "rap_discount",
    "diamondvideo": "video", "video": "video", "diamondimage": "image", "image": "image",
    "certfile": "cert_file",
}

_SHAPE_ALIAS = {v: canon for canon, variants in SHAPES.items() for v in variants}
# extra dealer codes safe in a dedicated shape column (from the LuxeDiam alias map).
# NB: RD=round (not radiant), OMB=Oval Modified Brilliant→oval, PS=pear, PR=princess.
_SHAPE_ALIAS.update({
    "rd": "round", "rbc": "round", "rnd": "round", "b": "round", "rb": "round", "br": "round",
    "as": "asscher", "asc": "asscher",
    "ov": "oval", "oc": "oval", "omb": "oval",
    "ps": "pear", "psh": "pear", "pb": "pear", "pmb": "pear", "pe": "pear",
    "mq": "marquise", "mqb": "marquise", "mc": "marquise",
    "cu": "cushion", "cush": "cushion", "csh": "cushion", "cmb": "cushion",
    "cb": "cushion", "cux": "cushion", "cm": "cushion", "cc": "cushion",
    "pc": "princess", "prn": "princess", "prin": "princess", "pn": "princess",
    "ec": "emerald", "em": "emerald", "sqe": "emerald", "sqem": "emerald",
    "ac": "asscher", "css": "asscher", "cssc": "asscher",
    "hs": "heart", "hrt": "heart", "ht": "heart", "he": "heart", "hc": "heart",
    "rad": "radiant", "rdn": "radiant", "ra": "radiant", "rc": "radiant",
    "bag": "baguette", "bg": "baguette",
    "tr": "trilliant", "tril": "trilliant", "trill": "trilliant", "trillion": "trilliant",
})
_LABGROWN_TOKENS = ("cvd", "hpht", "lab", "labgrown", "lab grown", "synthetic", "created")


def _hkey(h: str) -> str:
    return "".join(ch for ch in str(h).strip().lower() if ch.isalnum())


def _norm_shape(v: str):
    s = str(v).strip().lower().replace("-", " ")
    s = s.replace(" cut", "").replace(" shape", "").strip()
    # dealer prefixes like "SQ EM", "LONG RADIANT", "SQ RADIANT" → base shape
    for pre in ("sq ", "square ", "long ", "sqr "):
        if s.startswith(pre):
            s = s[len(pre):].strip()
    if s in _SHAPE_ALIAS:
        return _SHAPE_ALIAS[s]
    words = s.split()
    for w in words:                       # e.g. "cushion modified brilliant" → cushion
        if w in _SHAPE_ALIAS:
            return _SHAPE_ALIAS[w]
    return s.title() or None


def _norm_clarity(v: str):
    c = str(v).upper().replace(" ", "")
    return c if c.lower() in CLARITIES else None


def _num(v):
    try:
        return float(str(v).replace(",", "").replace("%", "").strip())
    except (ValueError, AttributeError):
        return None


def _map_row(row: dict) -> Optional[dict]:
    """Map one raw stock row (header->value) to a stone dict, or None to skip."""
    f: dict = {}
    for k, v in row.items():
        if k is None or v in (None, ""):
            continue
        dest = _HEADER_MAP.get(_hkey(k))
        if dest:
            f[dest] = str(v).strip() if isinstance(v, str) else v

    # skip sold / not-available rows
    avail = str(f.get("availability", "")).replace(" ", "").upper()
    if avail in {"SOLD", "MEMO", "ONHOLD", "HOLD", "NOTAVAILABLE", "NA"}:
        return None

    out: dict = {}
    flags: list[str] = []
    if f.get("shape"):
        out["shape"] = _norm_shape(f["shape"])
    if f.get("carat") is not None:
        out["carat"] = _num(f["carat"])
    # color grade vs fancy color
    col = str(f.get("color", "")).strip().upper()
    if col and len(col) <= 2 and col[0].isalpha():
        out["color"] = col
    if f.get("fancy_color"):
        fc = str(f["fancy_color"]).strip().lower()
        out["fancy_color"] = fc if fc in FANCY_COLORS else fc
    if f.get("fancy_intensity"):
        fi = str(f["fancy_intensity"]).strip().lower()
        out["fancy_intensity"] = next((it for it in FANCY_INTENSITY if it == fi), fi)
    if f.get("clarity"):
        out["clarity"] = _norm_clarity(f["clarity"]) or str(f["clarity"]).upper().replace(" ", "")
    if f.get("cut"):
        out["cut"] = {"excellent": "EX", "very good": "VG", "good": "GD"}.get(
            str(f["cut"]).strip().lower(), str(f["cut"]).strip().upper()[:3])
    if f.get("fluorescence"):
        out["fluorescence"] = str(f["fluorescence"]).strip().title()
    if f.get("lab"):
        out["lab"] = str(f["lab"]).strip().upper()
    if f.get("cert_number"):
        out["cert_number"] = str(f["cert_number"]).strip()
    for nk in ("price_per_carat", "total_price", "rap_discount"):
        if f.get(nk) is not None:
            n = _num(f[nk])
            if n is not None:
                out[nk] = n

    # lab-grown detection (growth type / nature / treatment)
    blob = " ".join(str(f.get(k, "")) for k in ("growth", "nature", "treatment")).lower()
    if any(t in blob for t in _LABGROWN_TOKENS):
        flags.append("lab_grown")
    out["flags"] = flags

    if not (out.get("shape") or out.get("carat")):
        return None

    # human-readable summary (also carries fields we don't have columns for)
    bits = [f.get("stock"), out.get("shape"),
            f"{out['carat']:g}ct" if out.get("carat") else None,
            out.get("fancy_intensity"), out.get("fancy_color") or out.get("color"),
            out.get("clarity"), out.get("lab"),
            (f"#{out['cert_number']}" if out.get("cert_number") else None),
            f.get("measurements"), ("LAB-GROWN" if "lab_grown" in flags else None)]
    out["raw_text"] = " ".join(str(b) for b in bits if b)
    out["confidence"] = 1.0
    return out


def _import_rows(rows, *, tg_id, source_group, source="csv", remaining=None) -> dict:
    """Map rows and bulk-insert (one connection). `remaining` caps how many are stored
    (the rest are counted as limit_skipped) to enforce a subscriber's stock quota."""
    keep: list[dict] = []
    skipped = limit_skipped = 0
    for row in rows:
        norm = _map_row(row)
        if not norm:
            skipped += 1
            continue
        if remaining is not None and len(keep) >= remaining:
            limit_skipped += 1
            continue
        keep.append(norm)
    if keep:
        db.add_listings_bulk(keep, tg_id=tg_id, source=source, source_group=source_group, ttl_days=30)
    return {"stored": len(keep), "skipped": skipped, "limit_skipped": limit_skipped}


def import_csv(data: bytes, *, tg_id: Optional[int] = None, source_group: str = "",
               remaining: Optional[int] = None) -> dict:
    """Import a CSV supplier stock file."""
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return _import_rows(reader, tg_id=tg_id, source_group=source_group, source="csv", remaining=remaining)


def import_xlsx(data: bytes, *, tg_id: Optional[int] = None, source_group: str = "",
                remaining: Optional[int] = None) -> dict:
    """Import an Excel (.xlsx) supplier stock file. Skips leading banner/blank rows."""
    try:
        import openpyxl
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("openpyxl required for Excel import: pip install openpyxl") from e
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    it = ws.iter_rows(values_only=True)
    headers = None
    for raw in it:                                   # first row with >=4 non-empty cells = header
        cells = [str(h).strip() if h is not None else "" for h in raw]
        if sum(bool(c) for c in cells) >= 4:
            headers = cells
            break
    if not headers:
        return {"stored": 0, "skipped": 0, "limit_skipped": 0}
    rows = (dict(zip(headers, r)) for r in it)
    return _import_rows(rows, tg_id=tg_id, source_group=source_group, source="xlsx", remaining=remaining)


def import_stock(data: bytes, filename: str = "", *, tg_id: Optional[int] = None,
                 source_group: str = "", remaining: Optional[int] = None) -> dict:
    """Dispatch by file extension: .xlsx/.xls → Excel, else CSV/TXT."""
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        return import_xlsx(data, tg_id=tg_id, source_group=source_group, remaining=remaining)
    return import_csv(data, tg_id=tg_id, source_group=source_group, remaining=remaining)


# ─────────────────────── Telegram BYO-session reader ──────────────────────────

class TelethonIngestor:  # pragma: no cover  (requires network + a real session)
    """
    Read-only ingestion of Telegram groups a *consenting subscriber* already belongs to.

    Usage (per subscriber, with their own api_id/api_hash + a StringSession they authorized):
        ing = TelethonIngestor(api_id, api_hash, session_string)
        await ing.run(groups=["@demandsnatural", ...], on_stone=callback)

    This is the Telegram-sanctioned path for user sessions. It NEVER sends messages
    (read-only => lowest ban risk) and processes per subscriber, not from a central account.
    """

    def __init__(self, api_id: int, api_hash: str, session_string: str):
        try:
            from telethon import TelegramClient, events           # noqa: F401
            from telethon.sessions import StringSession
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("Install telethon to use BYO-session ingestion: pip install telethon") from e
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        self._events = __import__("telethon").events
        self.client = TelegramClient(StringSession(session_string), api_id, api_hash)

    async def run(self, groups: Iterable[str], on_stone: Callable[[dict], None],
                  group_nature: Optional[dict] = None) -> None:
        group_nature = group_nature or {}
        events = self._events

        @self.client.on(events.NewMessage(chats=list(groups)))
        async def _handler(event):  # noqa: ANN001
            text = event.raw_text or ""
            handle = getattr(event.chat, "username", None)
            default = group_nature.get(f"@{handle}") if handle else None
            res = ingest_text(text, source="session",
                              source_group=f"@{handle}" if handle else "",
                              default_intent=default)
            if res and res.get("stored"):
                on_stone(res)

        await self.client.start()
        await self.client.run_until_disconnected()
