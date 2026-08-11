"""Offline tests for bot/services/katz_parser.py: raw-dict fixtures only,
no HTTP. Fixtures mirror the real API quirks documented in the module:
numbers as strings, sold_price '-'/'None', images main='True' (string)."""
from __future__ import annotations

import asyncio
import datetime as dt

import pytest

from bot.services.katz_parser import (STATUS_MAP, KatzParser, _int, _num,
                                      _ts, category_icon, enrich_from_title)

UTC = dt.timezone.utc

try:
    from zoneinfo import ZoneInfo
    ZoneInfo("Europe/Prague")
    HAS_TZDATA = True
except Exception:
    HAS_TZDATA = False


@pytest.fixture()
def parser():
    p = KatzParser("https://katzauction.com/")     # trailing slash stripped
    yield p
    asyncio.run(p.close())


# ----------------------------------------------------------------------- _num
@pytest.mark.parametrize(
    "value, expected",
    [
        (None, None),
        (True, None), (False, None),               # bools are not prices
        (5, 5.0), (5.5, 5.5), (0, 0.0),
        ("5", 5.0), (" 5.5 ", 5.5),
        ("1,234.56", 1234.56),                     # thousands separators
        ("-", None),                               # sold_price during a sale
        ("None", None), ("null", None),
        ("", None), ("   ", None),
        ("abc", None), ("12abc", None),
        ("-5", -5.0),
    ],
)
def test_num(value, expected):
    assert _num(value) == expected


# ----------------------------------------------------------------------- _int
@pytest.mark.parametrize(
    "value, expected",
    [("48", 48), (None, 0), ("-", 0), ("3.9", 3), (7, 7), (True, 0), ("", 0)],
)
def test_int(value, expected):
    assert _int(value) == expected


# ------------------------------------------------------------------------ _ts
def test_ts_rejects_non_strings_and_garbage():
    assert _ts(None) is None
    assert _ts("") is None
    assert _ts(123) is None
    assert _ts("not-a-date") is None
    assert _ts("2025-13-45T99:99:99") is None


def test_ts_summer_prague_is_utc_plus_2():
    # +02:00 both with real tzdata (CEST) and with the fixed fallback
    expected = int(dt.datetime(2025, 7, 15, 10, 0, tzinfo=UTC).timestamp())
    assert _ts("2025-07-15T12:00:00") == expected


@pytest.mark.skipif(not HAS_TZDATA, reason="needs IANA tzdata for DST check")
def test_ts_winter_prague_is_utc_plus_1():
    expected = int(dt.datetime(2025, 1, 15, 11, 0, tzinfo=UTC).timestamp())
    assert _ts("2025-01-15T12:00:00") == expected


def test_ts_truncates_fraction_and_offset_suffix():
    base = _ts("2025-07-15T12:00:00")
    assert _ts("2025-07-15T12:00:00.123456") == base
    assert _ts("2025-07-15T12:00:00+07:00") == base    # only first 19 chars used


# ---------------------------------------------------------- enrich_from_title
def test_enrich_full_house():
    out = enrich_from_title("Russia 1 Rouble 1912 EB, Silver, NGC MS 63")
    assert out == {"year": "1912", "metal": "Silver", "grade": "NGC MS 63"}


def test_enrich_year_only_from_title_not_description():
    out = enrich_from_title("Rouble of Peter", "restrike of 1912")
    assert out["year"] == ""


def test_enrich_metal_found_in_description():
    out = enrich_from_title("5 Roubles", "struck in gold, mint luster")
    assert out["metal"] == "Gold"


def test_enrich_av_marker_means_gold():
    assert enrich_from_title("AV Stater of Lysimachos")["metal"] == "Gold"


def test_enrich_cyrillic_metal():
    assert enrich_from_title("Рубль 1912, серебро")["metal"] == "Silver"


def test_enrich_standalone_grade_uppercased():
    assert enrich_from_title("Thaler 1620, nice xf")["grade"] == "XF"


def test_enrich_year_bounds():
    assert enrich_from_title("Lot 2030 catalogue")["year"] == ""   # > 2029
    assert enrich_from_title("Denar 999")["year"] == ""            # < 1000
    assert enrich_from_title("Coins 1898-1912")["year"] == "1898"  # first match
    assert enrich_from_title("25000 Roubles 1923")["year"] == "1923"


def test_enrich_no_signals():
    assert enrich_from_title("Interesting old coin") == {"year": "", "metal": "", "grade": ""}


# ------------------------------------------------------------------ STATUS_MAP
def test_status_map_exact():
    assert STATUS_MAP == {
        "created": "upcoming",
        "prebidding": "live",
        "waiting_room": "live",
        "live": "live",
        "paused": "live",
        "completed": "past",
    }


def test_category_icon_parser():
    assert category_icon("Banknotes of the world") == "💵"
    assert category_icon("Phaleristics") == "🎖"
    assert category_icon("") == "🪙"


# ----------------------------------------------------------------- _auction_row
def test_auction_row_from_raw_strings(parser):
    raw = {
        "id": "217", "title": "  Auction 105. World Coins  ",
        "status": "prebidding",
        "planned_starting_time": "2025-07-15T18:00:00",
        "starting_time": None,
        "planned_ending_time": None,
        "ending_time": "2025-07-20T18:00:00",
        "count_all_items": "2880",
    }
    row = parser._auction_row(raw, 217)
    assert row["id"] == 217
    assert row["title"] == "Auction 105. World Coins"
    assert row["status"] == "live"
    assert row["starts"] == _ts("2025-07-15T18:00:00")
    assert row["ends"] == _ts("2025-07-20T18:00:00")     # fallback field used
    assert row["lots_count"] == 2880
    assert row["url"] == "https://katzauction.com/lots?auction_id=217"


def test_auction_row_defaults(parser):
    row = parser._auction_row({"title": None, "status": "weird"}, 9)
    assert row["title"] == "Auction 9"
    assert row["status"] == "upcoming"                   # unknown status
    assert row["starts"] is None and row["ends"] is None
    assert row["lots_count"] == 0


def test_auction_row_title_capped_200(parser):
    row = parser._auction_row({"title": "T" * 500, "status": "live"}, 1)
    assert len(row["title"]) == 200


# -------------------------------------------------------------------- _lot_row
def raw_lot(**over):
    raw = {
        "id": "555001", "lot_number": "45",
        "title": "Russia 1 Rouble 1912 EB, Silver, NGC MS 63",
        "description": "Nice provenance",
        "status": "active",
        "sold_price": "-",                                # live sale
        "start_price": "5",
        "context": {"highest_bid": "25"},
        "category": "Coins", "country": "Russia",
        "year": None, "currency": "EUR",
        "images": [
            {"main": "False", "file_path": "https://cdn/a.jpg"},
            {"main": "True", "file_path": "https://cdn/b.jpg"},
        ],
    }
    raw.update(over)
    return raw


def test_lot_row_live_lot(parser):
    row = parser._lot_row(raw_lot(), auction_id=217, auction_ends=1234567890)
    assert row["id"] == 555001
    assert row["auction_id"] == 217
    assert row["number"] == 45
    assert row["start_price"] == 5.0
    assert row["current_bid"] == 25.0
    assert row["realized"] is None                        # '-' while live
    assert row["ends"] == 1234567890
    assert row["url"] == "https://katzauction.com/lot/555001"
    assert row["image"] == "https://cdn/b.jpg"            # main='True' wins
    assert row["currency"] == "EUR"
    assert row["bids"] == 0 and row["estimate"] is None


def test_lot_row_enriches_from_title_when_fields_null(parser):
    row = parser._lot_row(raw_lot(year=None), 1, None)
    assert row["year"] == "1912"                          # from title regex
    assert row["metal"] == "Silver"
    assert row["grade"] == "NGC MS 63"


def test_lot_row_year_string_none_treated_as_missing(parser):
    row = parser._lot_row(raw_lot(year="None"), 1, None)
    assert row["year"] == "1912"


def test_lot_row_year_int_passthrough(parser):
    row = parser._lot_row(raw_lot(year=1915), 1, None)
    assert row["year"] == "1915"


def test_lot_row_sold_lot_realized(parser):
    row = parser._lot_row(raw_lot(status="sold", sold_price="150"), 1, None)
    assert row["realized"] == 150.0


def test_lot_row_unsold_last_bid_is_not_a_sale(parser):
    # sold_price of an unsold lot is just the last bid — must not be realized
    row = parser._lot_row(raw_lot(status="unsold", sold_price=200), 1, None)
    assert row["realized"] is None


def test_lot_row_sold_price_none_string(parser):
    row = parser._lot_row(raw_lot(status="sold", sold_price="None"), 1, None)
    assert row["realized"] is None


def test_lot_row_missing_optionals(parser):
    raw = {"id": "7", "title": None, "images": None, "context": None,
           "sold_price": None, "start_price": None, "category": None,
           "country": None, "year": None, "currency": None, "status": None,
           "description": None, "lot_number": None}
    row = parser._lot_row(raw, 1, None)
    assert row["title"] == ""
    assert row["image"] == ""
    assert row["current_bid"] is None
    assert row["currency"] == "EUR"
    assert row["category"] == "" and row["country"] == ""
    assert row["number"] == 0


def test_lot_row_image_fallback_first_when_no_main(parser):
    raw = raw_lot(images=[{"main": "False", "file_path": "https://cdn/a.jpg"},
                          {"main": "False", "file_path": "https://cdn/c.jpg"}])
    assert parser._lot_row(raw, 1, None)["image"] == "https://cdn/a.jpg"


def test_lot_row_image_main_first_kept(parser):
    raw = raw_lot(images=[{"main": "True", "file_path": "https://cdn/m.jpg"},
                          {"main": "False", "file_path": "https://cdn/x.jpg"}])
    assert parser._lot_row(raw, 1, None)["image"] == "https://cdn/m.jpg"


def test_lot_row_title_capped_300(parser):
    row = parser._lot_row(raw_lot(title="T" * 400), 1, None)
    assert len(row["title"]) == 300


def test_lot_row_matches_db_upsert_columns(parser):
    """Every parser row must carry exactly the named params db.upsert_lots binds."""
    expected = {"id", "auction_id", "number", "title", "category", "country",
                "year", "metal", "grade", "start_price", "current_bid", "bids",
                "estimate", "currency", "realized", "ends", "url", "image",
                "updated"}
    assert set(parser._lot_row(raw_lot(), 1, None)) == expected
