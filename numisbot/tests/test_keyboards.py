"""Pure-logic tests for bot/keyboards.py (aiogram models built offline)."""
from __future__ import annotations

from bot.keyboards import (_fit_cb, auctions_kb, interests_kb, lang_kb,
                           listing_kb, lot_kb, main_reply_kb, menu_kb,
                           price_kb, watchlist_kb)
from bot.services.certs import lookup_url
from bot.texts import BTN, INTERESTS


def buttons(markup):
    """Flatten InlineKeyboardMarkup (possibly None) to a list of buttons."""
    if markup is None:
        return []
    return [b for row in markup.inline_keyboard for b in row]


# -------------------------------------------------------------------- _fit_cb
def test_fit_cb_ascii_exact_64_unchanged():
    text = "a" * 61
    out = _fit_cb("wq:", text)
    assert out == "wq:" + text
    assert len(out.encode("utf-8")) == 64


def test_fit_cb_ascii_over_limit_trimmed_to_64():
    out = _fit_cb("wq:", "a" * 100)
    assert len(out.encode("utf-8")) == 64


def test_fit_cb_cyrillic_cut_on_char_boundary():
    # 'я' is 2 bytes; 61 remaining bytes fit 30 chars, the split byte is dropped
    out = _fit_cb("wq:", "я" * 50)
    assert out == "wq:" + "я" * 30
    assert len(out.encode("utf-8")) == 63          # <= 64, no broken char
    assert "�" not in out
    out.encode("utf-8").decode("utf-8")            # strict re-decode round-trips


def test_fit_cb_cyrillic_realistic_query():
    out = _fit_cb("wq:", "полтина серебро николай второй античность")
    assert out.startswith("wq:")
    assert len(out.encode("utf-8")) <= 64
    assert "�" not in out


def test_fit_cb_4byte_emoji_boundary():
    out = _fit_cb("wq:", "🪙" * 20)                 # 3 + 15*4 = 63 fits
    assert out == "wq:" + "🪙" * 15
    assert len(out.encode("utf-8")) <= 64


def test_fit_cb_short_text_untouched():
    assert _fit_cb("wq:", "рубль") == "wq:рубль"


# --------------------------------------------------------------------- lot_kb
def test_lot_kb_live_lot_has_url_and_watch_buttons():
    lot = {"id": 7, "url": "https://katz/lot/7", "realized": None}
    bs = buttons(lot_kb(lot, "ru"))
    assert [b.url for b in bs if b.url] == ["https://katz/lot/7"]
    assert [b.callback_data for b in bs if b.callback_data] == ["wl:7"]


def test_lot_kb_realized_lot_has_no_watch_button():
    lot = {"id": 8, "url": "https://katz/lot/8", "realized": 120.0}
    bs = buttons(lot_kb(lot, "en"))
    assert len(bs) == 1
    assert bs[0].url == "https://katz/lot/8"
    assert bs[0].callback_data is None


def test_lot_kb_live_lot_without_url():
    lot = {"id": 9, "url": None, "realized": None}
    bs = buttons(lot_kb(lot, "ru"))
    assert [b.callback_data for b in bs] == ["wl:9"]


def test_lot_kb_realized_without_url_is_empty():
    lot = {"id": 10, "url": "", "realized": 5.0}
    assert buttons(lot_kb(lot, "ru")) == []


def test_lot_kb_in_radar_hides_watch_button():
    """Radar alerts pass in_radar=True — no '+ watch' for an already-watched lot."""
    lot = {"id": 11, "url": "https://katz/lot/11", "realized": None}
    bs = buttons(lot_kb(lot, "ru", in_radar=True))
    assert [b.url for b in bs] == ["https://katz/lot/11"]
    assert all(b.callback_data is None for b in bs)


# ----------------------------------------------------------------- listing_kb
def _listing(**over):
    listing = {"id": 3, "user_id": 42, "contact": "@ivan",
               "cert_service": "", "cert_number": ""}
    listing.update(over)
    return listing


def test_listing_kb_username_contact_gets_tme_link():
    bs = buttons(listing_kb(_listing(contact="@ivan"), "ru"))
    assert [b.url for b in bs] == ["https://t.me/ivan"]


def test_listing_kb_digits_contact_no_tme_link():
    """Sellers without a username are stored as bare digits (user id):
    t.me/<digits> is not a valid profile link and must not be rendered."""
    kb = listing_kb(_listing(contact="5551234567"), "ru")
    bs = buttons(kb)
    assert all(not (b.url and "t.me" in b.url) for b in bs)
    assert bs == []                                   # nothing else to show


def test_listing_kb_digits_contact_keeps_cert_button():
    listing = _listing(contact="5551234567", cert_service="PCGS",
                       cert_number="45689164")
    bs = buttons(listing_kb(listing, "en"))
    assert len(bs) == 1
    assert bs[0].url == lookup_url("PCGS", "45689164")
    assert "t.me" not in bs[0].url


def test_listing_kb_owner_gets_sold_button():
    bs = buttons(listing_kb(_listing(), "ru", is_owner=True))
    assert "mksold:3" in [b.callback_data for b in bs]


def test_listing_kb_none_contact_ok():
    bs = buttons(listing_kb(_listing(contact=None), "ru"))
    assert bs == []


def test_listing_kb_cert_button_url_matches_registry():
    listing = _listing(cert_service="NGC", cert_number="6805461-001")
    bs = buttons(listing_kb(listing, "ru"))
    assert lookup_url("NGC", "6805461-001") in [b.url for b in bs]


# --------------------------------------------------------------- watchlist_kb
def test_watchlist_kb_rows_and_cap():
    watches = [
        {"id": 1, "query": "рубль 1912", "max_price": 250.0},
        {"id": 2, "query": "poltina", "max_price": None},
    ]
    kb = watchlist_kb(watches, "ru")
    assert [len(r) for r in kb.inline_keyboard] == [1, 1]   # adjust(1)
    b1, b2 = buttons(kb)
    assert b1.text == "🗑 рубль 1912 <250" and b1.callback_data == "unwatch:1"
    assert b2.text == "🗑 poltina" and b2.callback_data == "unwatch:2"


def test_watchlist_kb_long_query_label_trimmed():
    (b,) = buttons(watchlist_kb([{"id": 3, "query": "q" * 40, "max_price": None}], "ru"))
    assert b.text == "🗑 " + "q" * 30 + "…"


# ------------------------------------------------------------------- price_kb
def test_price_kb_callback_fits_64_bytes_cyrillic():
    query = "полтина серебряная николаевская дореформенная"
    kb = price_kb(query, "ru")
    (b,) = buttons(kb)
    assert b.callback_data.startswith("wq:")
    assert len(b.callback_data.encode("utf-8")) <= 64
    assert query[:20] in b.text and b.text.endswith("…")


def test_price_kb_short_query_no_ellipsis():
    (b,) = buttons(price_kb("рубль", "en"))
    assert "рубль" in b.text and not b.text.endswith("…")
    assert b.callback_data == "wq:рубль"


# ---------------------------------------------------------------- auctions_kb
def test_auctions_kb_caps_at_8_and_trims_titles():
    auctions = [
        {"status": "live", "title": "T" * 60, "url": f"https://katz/a{i}"}
        for i in range(10)
    ]
    bs = buttons(auctions_kb(auctions, "ru"))
    assert len(bs) == 8
    assert all(b.text.startswith("🟢 ") for b in bs)
    assert all(b.text.endswith("…") for b in bs)
    assert all(len(b.text) - len("🟢 ") == 39 for b in bs)   # 38 chars + ellipsis


def test_auctions_kb_upcoming_marker_and_short_title():
    auctions = [{"status": "upcoming", "title": "  Auction 95  ", "url": "https://k/a"}]
    (b,) = buttons(auctions_kb(auctions, "ru"))
    assert b.text == "🗓 Auction 95"


# ----------------------------------------------------- static menus / selects
def test_lang_kb_callbacks():
    assert [b.callback_data for b in buttons(lang_kb())] == ["lang:ru", "lang:en", "lang:de", "lang:cs"]


def test_menu_kb_has_8_sections():
    bs = buttons(menu_kb("ru"))
    assert len(bs) == 8
    assert all(b.callback_data.startswith("m:") for b in bs)


def test_interests_kb_marks_selected_and_has_done():
    kb = interests_kb("ru", selected={"gold"})
    bs = buttons(kb)
    assert len(bs) == len(INTERESTS) + 1
    by_cb = {b.callback_data: b for b in bs}
    assert by_cb["int:gold"].text.startswith("✅ ")
    assert not by_cb["int:world"].text.startswith("✅")
    assert by_cb["int:done"].callback_data == "int:done"


def test_main_reply_kb_labels_match_btn_registry():
    """Bottom-nav labels must equal BTN texts — handlers route on exact match."""
    for lang in ("ru", "en"):
        kb = main_reply_kb(lang)
        texts = [b.text for row in kb.keyboard for b in row]
        assert sorted(texts) == sorted(BTN[lang].values())
        assert kb.resize_keyboard and kb.is_persistent
        assert len(kb.keyboard) == 4                        # 4 rows x 2 buttons
        assert all(len(row) == 2 for row in kb.keyboard)
