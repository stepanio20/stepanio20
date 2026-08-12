"""Pure-logic tests for bot/texts.py: cards, escaping, caption budgets."""
from __future__ import annotations

import datetime as dt
import sqlite3
from html import escape as esc

import pytest

from bot.texts import (BTN, INTERESTS, T, category_icon, listing_card,
                       lot_card, photo_url, price_summary, realized_line, t)

UTC = dt.timezone.utc
ENDS_TS = int(dt.datetime(2025, 12, 31, 23, 59, tzinfo=UTC).timestamp())


def make_lot(**over) -> dict:
    lot = {
        "id": 1, "auction_id": 10, "number": 5,
        "title": "Russia 1 Rouble 1912 EB", "category": "Coins",
        "country": "Russia", "year": "1912", "metal": "Silver", "grade": "XF",
        "start_price": 5.0, "current_bid": None, "bids": 0, "estimate": None,
        "currency": "EUR", "realized": None, "ends": None,
        "url": "https://katzauction.com/lot/1", "image": None, "updated": 0,
    }
    lot.update(over)
    return lot


def make_listing(**over) -> dict:
    listing = {
        "id": 3, "user_id": 42, "contact": "@seller",
        "title": "Poltina 1859 silver, nice tone",
        "description": "Poltina 1859 silver, nice tone. Bought at a local fair.",
        "price": 150.0, "photos": "[]",
        "cert_service": "", "cert_number": "", "cert_status": "none",
        "cert_note": "", "status": "active", "created": 0,
    }
    listing.update(over)
    return listing


def as_row(d: dict) -> sqlite3.Row:
    """Real sqlite3.Row with the same columns — Row-compat check."""
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    cols = ", ".join(f'"{k}"' for k in d)
    con.execute(f"CREATE TABLE t ({cols})")
    con.execute(f"INSERT INTO t VALUES ({', '.join('?' for _ in d)})", list(d.values()))
    return con.execute("SELECT * FROM t").fetchone()


# ------------------------------------------------------------------ photo_url
def test_photo_url_none_image():
    assert photo_url(make_lot(image=None)) is None


def test_photo_url_empty_image():
    assert photo_url(make_lot(image="")) is None


def test_photo_url_without_query():
    assert photo_url(make_lot(image="https://cdn/img.jpg")) == "https://cdn/img.jpg?width=700"


def test_photo_url_with_query():
    assert (photo_url(make_lot(image="https://cdn/img.jpg?quality=80"))
            == "https://cdn/img.jpg?quality=80&width=700")


# -------------------------------------------------------------- small helpers
def test_category_icon():
    assert category_icon("Banknotes") == "💵"
    assert category_icon("paper money") == "💵"
    assert category_icon("Phaleristics") == "🎖"
    assert category_icon("Coins") == "🪙"
    assert category_icon(None) == "🪙"


def test_t_known_and_fallback_lang():
    assert "Katz" in t("menu", "ru")
    assert t("menu", "en") != t("menu", "ru")
    # de/cs are real translations now; unknown langs fall back to ru
    assert t("menu", "de") not in (t("menu", "ru"), t("menu", "en"))
    assert t("menu", "xx") == t("menu", "ru")


def test_interests_have_both_langs():
    for key, labels in INTERESTS.items():
        assert labels["ru"] and labels["en"], key


def test_btn_registry_symmetric():
    """Reply-keyboard routing does exact text match — both langs need the
    same set of actions and no duplicate labels within a language."""
    assert set(BTN["ru"]) == set(BTN["en"])
    for lang in ("ru", "en"):
        labels = list(BTN[lang].values())
        assert len(labels) == len(set(labels))


# ------------------------------------------------------------------- lot_card
def test_lot_card_realized_ru():
    card = lot_card(make_lot(realized=1234.0), "ru")
    assert "✅ Продан за <b>€1 234</b>" in card
    assert "Ставка" not in card and "Закрытие" not in card


def test_lot_card_realized_en():
    card = lot_card(make_lot(realized=1234.0), "en")
    assert "Sold for <b>€1 234</b>" in card


def test_lot_card_live_bid_and_ends():
    card = lot_card(make_lot(current_bid=250.0, ends=ENDS_TS), "ru")
    assert "💶 Ставка: <b>€250</b>" in card
    assert "⏳ Закрытие: 31.12 23:59 UTC" in card


def test_lot_card_live_start_price_only():
    card = lot_card(make_lot(start_price=5.0, current_bid=None), "ru")
    assert "💶 Старт: <b>€5</b>" in card


def test_lot_card_non_eur_currency():
    card = lot_card(make_lot(currency="USD", current_bid=1500.0), "en")
    assert "USD 1 500" in card


def test_lot_card_meta_line_joined():
    card = lot_card(make_lot(), "ru")
    assert "<i>Russia · 1912 · Silver · XF</i>" in card


def test_lot_card_all_optional_fields_none():
    lot = make_lot(country=None, year=None, metal=None, grade=None,
                   category=None, currency=None, start_price=None,
                   current_bid=None, ends=None, realized=None)
    card = lot_card(lot, "ru")
    assert card.startswith("🪙 <b>")
    assert "<i>" not in card          # no meta line
    assert "💶" not in card           # no price line at all
    assert "⏳" not in card


def test_lot_card_currency_none_defaults_to_eur():
    card = lot_card(make_lot(currency=None, realized=10.0), "ru")
    assert "€10" in card


def test_lot_card_html_injection_escaped():
    evil = '<b>&"<script>alert(1)</script>'
    card = lot_card(make_lot(title=evil, country='<i>Rus&'), "ru")
    assert esc(evil) in card
    assert "<script>" not in card
    assert esc("<i>Rus&") in card


def test_lot_card_sqlite_row_equals_dict():
    lot = make_lot(current_bid=99.0, ends=ENDS_TS)
    assert lot_card(as_row(lot), "ru") == lot_card(lot, "ru")


def test_lot_card_long_realistic_title_fits_caption():
    """Parser caps title at 300 chars; the full card must fit a 1024 caption."""
    lot = make_lot(title="Russia, Empire, Nicholas II silver Rouble pattern " * 6,
                   current_bid=125000.0, ends=ENDS_TS)
    assert len(lot_card(lot, "ru")) <= 1024


# -------------------------------------------------------------- realized_line
def test_realized_line_trims_title_and_formats_money():
    lot = make_lot(title="R" * 100, realized=2500.0)
    line = realized_line(lot, "ru")
    assert "R" * 70 in line and "R" * 71 not in line
    assert "<b>€2 500</b>" in line


# --------------------------------------------------------------- listing_card
def test_listing_card_with_price_ru():
    card = listing_card(make_listing(), "ru")
    assert "💶 Цена: <b>€150</b>" in card
    assert "Продавец: @seller" in card


def test_listing_card_open_to_offers():
    card = listing_card(make_listing(price=None), "ru")
    assert "💬 Открыт к предложениям" in card
    card_en = listing_card(make_listing(price=None), "en")
    assert "💬 Open to offers" in card_en


def test_listing_card_description_tail_in_blockquote():
    listing = make_listing(title="Coin A", description="Coin A with a long provenance story")
    card = listing_card(listing, "ru")
    assert "<blockquote>with a long provenance story</blockquote>" in card


def test_listing_card_description_equals_title_no_blockquote():
    listing = make_listing(title="Coin A", description="Coin A")
    assert "<blockquote>" not in listing_card(listing, "ru")


@pytest.mark.parametrize("status, marker", [
    ("verified", "✅"),
    ("linked", "🛡"),
    ("pending", "⏳"),
    ("mismatch", "⚠️"),
])
def test_listing_card_cert_badges(status, marker):
    listing = make_listing(cert_service="PCGS", cert_number="45689164", cert_status=status)
    card = listing_card(listing, "ru")
    assert marker in card and "45689164" in card
    assert "Без сертификата" not in card


def test_listing_card_verified_note_shown_escaped_and_trimmed():
    note = "1912 Rouble <MS62> & rare " * 10
    listing = make_listing(cert_service="PCGS", cert_number="1", cert_status="verified",
                           cert_note=note)
    card = listing_card(listing, "ru")
    assert esc(note[:120]) in card
    assert "<MS62>" not in card


def test_listing_card_rejected_status_shows_no_badge():
    listing = make_listing(cert_service="PCGS", cert_number="1", cert_status="rejected")
    card = listing_card(listing, "ru")
    assert "PCGS" not in card                 # no badge for rejected
    assert "Без сертификата" not in card      # and not presented as raw either


def test_listing_card_no_cert_raw_line():
    assert "◽️ Без сертификата (raw)" in listing_card(make_listing(), "ru")
    assert "◽️ No certificate (raw)" in listing_card(make_listing(), "en")


def test_listing_card_contact_none_ok():
    card = listing_card(make_listing(contact=None), "ru")
    assert card.endswith("Продавец: ")


def test_listing_card_html_injection_escaped():
    evil = '<b>&"hack'
    listing = make_listing(title=evil, description=evil + " plus <img src=x onerror=1> tail",
                           contact='<a href="x">c</a>',
                           cert_service="NGC", cert_number='<i>1</i>234567-001',
                           cert_status="linked")
    card = listing_card(listing, "ru")
    assert esc(evil) in card
    assert "<img" not in card and "<a href" not in card and "<i>1</i>" not in card


def test_listing_card_sqlite_row_equals_dict():
    listing = make_listing(cert_service="NGC", cert_number="6805461-001",
                           cert_status="verified", cert_note="1912 Rouble MS62")
    assert listing_card(as_row(listing), "ru") == listing_card(listing, "ru")


def test_listing_card_with_description_false_drops_blockquote():
    listing = make_listing(title="Coin A", description="Coin A with a long story")
    card = listing_card(listing, "ru", with_description=False)
    assert "<blockquote>" not in card
    assert "💶 Цена" in card


def test_listing_card_compact_fallback_always_fits_photo_caption():
    """Contract the market handler relies on: the full card may overflow 1024
    because the description tail is sliced BEFORE html-escaping ('&' -> &amp;
    inflates 5-6x), but then _send_listing_card retries with
    with_description=False and sends THAT without further truncation — so the
    compact variant must always fit Telegram's 1024-char photo-caption cap.
    """
    title = "Rare coin & slab " * 4          # <=70 chars after handler trim
    desc = (title + " " + "&" * 500)[:1500]  # hostile but legal user input
    listing = make_listing(
        title=title[:70], description=desc,
        cert_service="PCGS", cert_number="45689164", cert_status="verified",
        cert_note='"rare" & <fine> ' * 20)
    full = listing_card(listing, "ru")
    compact = listing_card(listing, "ru", with_description=False)
    assert len(full) > 1024                  # why the fallback exists
    assert len(compact) <= 1024


# -------------------------------------------------------------- price_summary
def _rows(prices, auction_id=1):
    return [make_lot(id=i, auction_id=auction_id, realized=p, title=f"Lot {i}")
            for i, p in enumerate(prices, start=1)]


def test_price_summary_stats_ru():
    out = price_summary("рубль", _rows([300.0, 100.0, 200.0]), "ru", shown=3, locked=0)
    assert "📉 <b>«рубль» на аукционах Katz</b>" in out
    assert "Продано: <b>3</b>" in out
    assert "медиана <b>€200</b>" in out
    assert "€100–€300" in out
    assert "🔒" not in out


def test_price_summary_shown_limits_rows():
    out = price_summary("q", _rows([1.0, 2.0, 3.0, 4.0]), "ru", shown=2, locked=2)
    assert out.count("▫️") == 2
    assert "🔒 Ещё 2 проходов — в Pro" in out


def test_price_summary_en_locked_tail():
    out = price_summary("q", _rows([10.0, 20.0]), "en", shown=1, locked=5)
    assert "Sold: <b>2</b>" in out
    assert "🔒 5 more results — in Pro: /pro" in out


def test_price_summary_single_row():
    out = price_summary("q", _rows([500.0]), "ru", shown=1, locked=0)
    assert "медиана <b>€500</b>" in out
    assert "€500–€500" in out


def test_price_summary_query_injection_escaped():
    out = price_summary('<b>&"x', _rows([10.0]), "ru", shown=1, locked=0)
    assert esc('<b>&"x') in out


def test_price_summary_typical_free_tier_fits_caption():
    """/price photo path requires len(caption) <= 1024 (checked in handler)."""
    rows = _rows([1234.0] * 6)
    for r in rows:
        r["title"] = "Russia. Nicholas II. Rouble 1912, silver, PCGS MS62 " * 2
    out = price_summary("рубль 1912", rows, "ru", shown=6, locked=24)
    assert len(out) <= 1024
