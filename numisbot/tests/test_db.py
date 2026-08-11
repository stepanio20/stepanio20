"""Database logic tests on an in-memory SQLite (aiosqlite), no network."""
from __future__ import annotations

import time

import pytest
import pytest_asyncio

from bot.config import Config
from bot.db import Database

pytestmark = pytest.mark.asyncio

NOW = int(time.time())


@pytest_asyncio.fixture
async def db():
    d = Database(":memory:")
    await d.connect()
    yield d
    await d.close()


def make_lot(i: int, **over) -> dict:
    lot = {
        "id": i, "auction_id": 1, "number": i, "title": f"Lot {i}",
        "category": "Coins", "country": "", "year": "", "metal": "",
        "grade": "", "start_price": 5.0, "current_bid": None, "bids": 0,
        "estimate": None, "currency": "EUR", "realized": None, "ends": None,
        "url": f"https://k/lot/{i}", "image": "", "updated": NOW,
    }
    lot.update(over)
    return lot


def make_listing(user_id=42, **over) -> dict:
    listing = {
        "user_id": user_id, "contact": "@u", "title": "t", "description": "d",
        "price": None, "photos": "[]", "cert_service": "", "cert_number": "",
        "cert_status": "none", "cert_note": "", "created": NOW,
    }
    listing.update(over)
    return listing


# ---------------------------------------------------------------------- users
async def test_upsert_user_idempotent_updates_username(db):
    await db.upsert_user(1, "alice")
    await db.upsert_user(1, "alice_new")
    u = await db.get_user(1)
    assert u["username"] == "alice_new"
    cur = await db.db.execute("SELECT COUNT(*) c FROM users")
    assert (await cur.fetchone())["c"] == 1


async def test_upsert_user_none_username_stored_as_empty(db):
    await db.upsert_user(2, None)
    assert (await db.get_user(2))["username"] == ""


async def test_user_defaults_and_lang_interests(db):
    await db.upsert_user(3, "bob")
    u = await db.get_user(3)
    assert (u["lang"], u["tier"], u["sub_until"], u["interests"]) == ("ru", "free", 0, "")
    await db.set_lang(3, "en")
    await db.set_interests(3, "gold,ancient")
    u = await db.get_user(3)
    assert u["lang"] == "en" and u["interests"] == "gold,ancient"


async def test_effective_tier_free_active_expired(db):
    await db.upsert_user(4, "u")
    assert await db.effective_tier(4) == "free"
    await db.set_tier(4, "pro", NOW + 3600)
    assert await db.effective_tier(4) == "pro"
    await db.set_tier(4, "pro", NOW - 3600)          # expired subscription
    assert await db.effective_tier(4) == "free"
    assert await db.effective_tier(99999) == "free"  # unknown user


# -------------------------------------------------------- watches (and slots)
async def test_add_list_delete_watch(db):
    await db.upsert_user(5, "u")
    w1 = await db.add_watch(5, "  рубль 1912  ", None)
    w2 = await db.add_watch(5, "poltina", 300.0)
    rows = await db.list_watches(5)
    assert [r["id"] for r in rows] == [w1, w2]
    assert rows[0]["query"] == "рубль 1912"          # trimmed
    assert rows[1]["max_price"] == 300.0
    await db.delete_watch(5, w1)
    assert [r["id"] for r in await db.list_watches(5)] == [w2]


async def test_delete_watch_checks_ownership(db):
    wid = await db.add_watch(6, "q", None)
    await db.delete_watch(777, wid)                  # someone else's id
    assert len(await db.list_watches(6)) == 1


async def test_watch_slots_per_tier():
    cfg = Config(bot_token="123:test")
    assert cfg.watch_slots("free") == 3
    assert cfg.watch_slots("pro") == 25
    assert cfg.watch_slots("sniper") == 999
    assert cfg.watch_slots("dealer") == 999          # any paid non-pro tier
    assert cfg.watch_slots("unknown") == 999


async def test_free_limit_scenario_via_slots(db):
    """The handler blocks at used >= watch_slots(tier): model it on the db."""
    cfg = Config(bot_token="123:test")
    await db.upsert_user(7, "u")
    total = cfg.watch_slots(await db.effective_tier(7))
    for i in range(total):
        await db.add_watch(7, f"q{i}", None)
    used = len(await db.list_watches(7))
    assert used == total == 3
    assert used >= total                             # -> handler must refuse


# ----------------------------------------------------------------------- lots
async def test_upsert_lots_idempotent_and_partial_update(db):
    await db.upsert_lots([make_lot(100), make_lot(101)])
    await db.upsert_lots([make_lot(100, current_bid=50.0, bids=3,
                                   title="CHANGED", realized=None, ends=555)])
    cur = await db.db.execute("SELECT COUNT(*) c FROM lots")
    assert (await cur.fetchone())["c"] == 2
    lot = await db.get_lot(100)
    assert lot["current_bid"] == 50.0 and lot["bids"] == 3
    assert lot["title"] == "Lot 100"                 # title NOT refreshed by design
    # archive flip: realized set on a later sync
    await db.upsert_lots([make_lot(100, realized=77.0)])
    assert (await db.get_lot(100))["realized"] == 77.0
    # COALESCE semantics: None in a later sync must not wipe known values
    await db.upsert_lots([make_lot(100, current_bid=None, realized=None, ends=None)])
    lot = await db.get_lot(100)
    assert lot["current_bid"] == 50.0
    assert lot["realized"] == 77.0
    assert lot["ends"] == 555


async def test_upsert_lots_empty_iterable_noop(db):
    await db.upsert_lots([])
    cur = await db.db.execute("SELECT COUNT(*) c FROM lots")
    assert (await cur.fetchone())["c"] == 0


async def test_search_lots_ascii_case_insensitive(db):
    await db.upsert_lots([make_lot(1, title="Rouble of Peter I")])
    assert len(await db.search_lots("ROUBLE")) == 1
    assert len(await db.search_lots("rouble")) == 1
    assert len(await db.search_lots("  rouble  ")) == 1   # query trimmed


async def test_has_watch_ascii_case_insensitive(db):
    await db.add_watch(8, "Rouble 1912", None)
    assert await db.has_watch(8, "rouble 1912")
    assert await db.has_watch(8, "  ROUBLE 1912  ")
    assert not await db.has_watch(8, "poltina")
    assert not await db.has_watch(9, "Rouble 1912")       # other user


async def test_search_lots_cyrillic_case_insensitive():
    """KNOWN BUG: LIKE/= ... COLLATE NOCASE folds case for ASCII only.
    The schema comment promises 'matched case-insensitively' and the bot's
    own onboarding suggests Cyrillic watches ('/watch рубль 1912'), but a
    lowercase Cyrillic query does not match a capitalized title, so /find,
    radar alerts and has_watch dedup silently miss for RU users."""
    d = Database(":memory:")
    await d.connect()
    try:
        await d.upsert_lots([make_lot(1, title="Рубль Николая II 1912")])
        assert len(await d.search_lots("Рубль")) == 1     # exact case works
        await d.add_watch(1, "Рубль 1912", None)
        assert len(await d.search_lots("рубль")) == 1     # FAILS: NOCASE is ASCII-only
        assert await d.has_watch(1, "рубль 1912")         # same root cause
    finally:
        await d.close()


async def test_search_lots_excludes_realized_and_orders_by_ends(db):
    await db.upsert_lots([
        make_lot(1, title="rouble a", ends=2000),
        make_lot(2, title="rouble b", ends=None),
        make_lot(3, title="rouble c", ends=1000),
        make_lot(4, title="rouble sold", realized=99.0),
    ])
    rows = await db.search_lots("rouble")
    assert [r["id"] for r in rows] == [3, 1, 2]      # soonest end first, NULL last
    assert all(r["realized"] is None for r in rows)


async def test_search_lots_limit(db):
    await db.upsert_lots([make_lot(i, title=f"rouble {i}") for i in range(1, 15)])
    assert len(await db.search_lots("rouble", limit=8)) == 8


async def test_price_history_sorted_new_auctions_first(db):
    await db.upsert_lots([
        make_lot(1, auction_id=1, title="rouble", realized=500.0),
        make_lot(2, auction_id=2, title="rouble", realized=100.0),
        make_lot(3, auction_id=2, title="rouble", realized=300.0),
        make_lot(4, auction_id=3, title="rouble live", realized=None),
    ])
    rows = await db.price_history("rouble")
    assert [r["id"] for r in rows] == [3, 2, 1]      # auction DESC, price DESC
    assert all(r["realized"] is not None for r in rows)


async def test_price_history_case_and_limit(db):
    await db.upsert_lots([make_lot(i, title="Thaler", realized=float(i))
                          for i in range(1, 12)])
    assert len(await db.price_history("thaler", limit=5)) == 5


# ------------------------------------------------------------- interest_lots
async def _seed_interest_lots(db):
    await db.upsert_lots([
        make_lot(1, country="Russia", category="Coins - Europe"),
        make_lot(2, category="Ancient coins"),
        make_lot(3, category="Banknotes"),
        make_lot(4, category="Phaleristics"),
        make_lot(5, metal="Gold"),
        make_lot(6, category="Coins - Europe", country="Austria"),
        make_lot(7, country="Russia", realized=10.0),     # archived — excluded
    ])


async def test_interest_lots_fixed_map(db):
    await _seed_interest_lots(db)
    assert (await db.interest_lots(["gold"]))[0] == 1
    assert (await db.interest_lots(["ru_imperial"]))[0] == 1
    assert (await db.interest_lots(["banknotes"]))[0] == 1
    assert (await db.interest_lots(["medals"]))[0] == 1
    assert (await db.interest_lots(["ancient"]))[0] == 1
    # world = 'Coins - %' categories excluding Russia -> only lot 6
    assert (await db.interest_lots(["world"]))[0] == 1
    total, sample = await db.interest_lots(["ru_imperial", "gold"])
    assert total == 2 and len(sample) == 2


async def test_interest_lots_no_or_unknown_interests_mean_all_live(db):
    await _seed_interest_lots(db)
    # unknown keys are skipped; empty conds fall back to 1=1 over live lots
    assert (await db.interest_lots([]))[0] == 6
    assert (await db.interest_lots(["no_such_interest"]))[0] == 6


async def test_interest_lots_sample_limit(db):
    await _seed_interest_lots(db)
    _, sample = await db.interest_lots([], limit=3)
    assert len(sample) == 3


async def test_closing_soon_window(db):
    await db.upsert_lots([
        make_lot(1, ends=NOW + 30 * 60),
        make_lot(2, ends=NOW + 3 * 3600),                 # too far
        make_lot(3, ends=NOW - 60),                       # already closed
        make_lot(4, ends=None),
        make_lot(5, ends=NOW + 10 * 60, realized=5.0),    # sold already
    ])
    rows = await db.closing_soon(within_minutes=70)
    assert [r["id"] for r in rows] == [1]


# --------------------------------------------------------------------- alerts
async def test_alert_sent_roundtrip_and_duplicates(db):
    assert not await db.alert_already_sent(1, 100, "match")
    await db.mark_alert_sent(1, 100, "match")
    assert await db.alert_already_sent(1, 100, "match")
    await db.mark_alert_sent(1, 100, "match")             # OR IGNORE — no raise
    assert not await db.alert_already_sent(1, 100, "closing")   # per-kind
    assert not await db.alert_already_sent(2, 100, "match")     # per-user


# ------------------------------------------------------------------- listings
async def test_add_get_listing(db):
    lid = await db.add_listing(make_listing(price=150.0, title="Poltina"))
    assert lid > 0
    row = await db.get_listing(lid)
    assert row["title"] == "Poltina" and row["status"] == "active"
    assert row["cert_status"] == "none"


async def test_browse_listings_filters_and_pagination(db):
    ids = [await db.add_listing(make_listing(title=f"L{i}")) for i in range(1, 7)]
    await db.set_listing_status(ids[0], None, "sold")
    await db.set_listing_status(ids[1], None, "hidden")
    await db.set_cert_status(ids[2], "rejected")
    page1 = await db.browse_listings(limit=2)
    assert [r["id"] for r in page1] == [ids[5], ids[4]]   # newest first
    page2 = await db.browse_listings(before_id=page1[-1]["id"], limit=2)
    assert [r["id"] for r in page2] == [ids[3]]           # sold/hidden/rejected gone


async def test_active_listings_of_counts_only_active(db):
    a = await db.add_listing(make_listing(user_id=10))
    await db.add_listing(make_listing(user_id=10))
    await db.add_listing(make_listing(user_id=20))
    await db.set_listing_status(a, 10, "sold")
    assert await db.active_listings_of(10) == 1
    assert await db.active_listings_of(20) == 1
    assert await db.active_listings_of(30) == 0


async def test_cert_in_use_lifecycle(db):
    assert not await db.cert_in_use("PCGS", "45689164")
    lid = await db.add_listing(make_listing(
        cert_service="PCGS", cert_number="45689164", cert_status="linked"))
    assert await db.cert_in_use("PCGS", "45689164")
    assert not await db.cert_in_use("NGC", "45689164")    # per-service
    await db.set_listing_status(lid, None, "sold")
    assert not await db.cert_in_use("PCGS", "45689164")   # slab freed


async def test_cert_in_use_ignores_rejected(db):
    lid = await db.add_listing(make_listing(
        cert_service="NGC", cert_number="6805461-001", cert_status="linked"))
    await db.set_cert_status(lid, "rejected", "fake slab")
    assert not await db.cert_in_use("NGC", "6805461-001")


async def test_set_cert_status_updates_note(db):
    lid = await db.add_listing(make_listing(cert_service="PCGS", cert_number="1"))
    await db.set_cert_status(lid, "verified", "1912 Rouble MS62")
    row = await db.get_listing(lid)
    assert row["cert_status"] == "verified" and row["cert_note"] == "1912 Rouble MS62"


async def test_set_listing_status_ownership(db):
    lid = await db.add_listing(make_listing(user_id=42))
    await db.set_listing_status(lid, 999, "sold")         # wrong owner — no-op
    assert (await db.get_listing(lid))["status"] == "active"
    await db.set_listing_status(lid, 42, "sold")          # owner
    assert (await db.get_listing(lid))["status"] == "sold"
    await db.set_listing_status(lid, None, "hidden")      # admin override
    assert (await db.get_listing(lid))["status"] == "hidden"


# -------------------------------------------------------------------- metrics
async def test_metrics_on_empty_db_no_zero_division(db):
    m = await db.metrics()
    assert m == {"dau": 0, "wau": 0, "mau": 0, "activation_pct": 0.0,
                 "conversion_pct": 0.0, "searches_7d": 0, "listings_active": 0}


async def test_metrics_with_activity(db):
    await db.upsert_user(1, "a")
    await db.upsert_user(2, "b")
    await db.add_watch(1, "q", None)
    await db.track(1, "find")
    await db.track(1, "price")
    await db.track(2, "menu")
    await db.set_tier(2, "pro", NOW + 3600)
    m = await db.metrics()
    assert m["dau"] == m["wau"] == m["mau"] == 2
    assert m["activation_pct"] == 50.0                    # 1 of 2 users has a watch
    assert m["conversion_pct"] == 50.0
    assert m["searches_7d"] == 2                          # only find/price events
    assert m["listings_active"] == 0


async def test_stats_on_empty_db(db):
    s = await db.stats()
    assert s == {"users": 0, "paying": 0, "watches": 0, "lots": 0, "leads": 0}


async def test_seller_lead_and_payment(db):
    lead = await db.add_seller_lead(1, "@u", "5 roubles 1898")
    assert lead == 1
    await db.add_payment(1, "ch_1", "pro", 299, True)
    s = await db.stats()
    assert s["leads"] == 1
