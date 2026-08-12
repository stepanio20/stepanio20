"""Growth mechanics: trial, referrals, digest flag, new-auction announcements."""
import time

import pytest
import pytest_asyncio

from bot.db import Database


@pytest_asyncio.fixture
async def db(tmp_path):
    d = Database(str(tmp_path / "t.sqlite3"))
    await d.connect()
    yield d
    await d.close()


@pytest.mark.asyncio
async def test_trial_granted_once(db):
    await db.upsert_user(1, "u1")
    assert await db.try_use_trial(1) is True
    assert await db.effective_tier(1) == "pro"
    # second attempt: no double trial
    assert await db.try_use_trial(1) is False


@pytest.mark.asyncio
async def test_trial_not_granted_to_paying(db):
    await db.upsert_user(2, "u2")
    await db.set_tier(2, "sniper", int(time.time()) + 86400)
    assert await db.try_use_trial(2) is False
    assert await db.effective_tier(2) == "sniper"


@pytest.mark.asyncio
async def test_referral_reward_once(db):
    await db.upsert_user(10, "referrer")
    # referee arrives via link BEFORE being created
    await db.set_referrer(20, 10)
    await db.upsert_user(20, "referee")
    assert await db.reward_referral(20) == 10
    assert await db.effective_tier(10) == "pro"
    # activation fires again → no double reward
    assert await db.reward_referral(20) is None


@pytest.mark.asyncio
async def test_referral_ignores_self_and_existing(db):
    await db.upsert_user(30, "old")
    await db.set_referrer(30, 31)      # existing user can't be invited
    assert await db.reward_referral(30) is None
    await db.set_referrer(32, 32)      # self-invite
    await db.upsert_user(32, "selfie")
    assert await db.reward_referral(32) is None


@pytest.mark.asyncio
async def test_referral_yearly_cap(db):
    await db.upsert_user(100, "big")
    for i in range(8):
        await db.set_referrer(200 + i, 100)
        await db.upsert_user(200 + i, f"r{i}")
    rewarded = [await db.reward_referral(200 + i) for i in range(8)]
    assert rewarded.count(100) == 6      # capped at 6/year
    assert rewarded[6:] == [None, None]


@pytest.mark.asyncio
async def test_grant_tier_days_extends(db):
    await db.upsert_user(5, "x")
    until1 = await db.grant_tier_days(5, "pro", 7)
    until2 = await db.grant_tier_days(5, "pro", 30)
    assert until2 - until1 == 30 * 86400  # stacked, not reset


@pytest.mark.asyncio
async def test_digest_toggle_and_recipients(db):
    await db.upsert_user(7, "a")
    await db.upsert_user(8, "b")
    assert len(await db.digest_recipients()) == 2
    assert await db.toggle_digest(7) is True     # now off
    assert [r["id"] for r in await db.digest_recipients()] == [8]
    assert await db.toggle_digest(7) is False    # back on


@pytest.mark.asyncio
async def test_announce_lifecycle(db):
    await db.upsert_auction({"id": 300, "title": "A300", "status": "live",
                             "starts": 1, "ends": 2, "lots_count": 10, "url": ""})
    await db.upsert_auction({"id": 301, "title": "A301", "status": "past",
                             "starts": 1, "ends": 2, "lots_count": 5, "url": ""})
    fresh = await db.unannounced_auctions()
    assert [a["id"] for a in fresh] == [300]     # past auctions never announced
    await db.mark_announced(300)
    assert await db.unannounced_auctions() == []
    await db.mark_announced(300)                 # idempotent


@pytest.mark.asyncio
async def test_top_live_lots_interest_filter(db):
    lot = {"id": 1, "auction_id": 1, "number": 1, "title": "Russia Rouble 1912",
           "category": "Coins - Russia", "country": "Russia", "year": "1912",
           "metal": "Silver", "grade": "", "start_price": 5.0, "current_bid": 100.0,
           "bids": 0, "estimate": None, "currency": "EUR", "realized": None,
           "ends": None, "url": "", "image": "", "updated": 1}
    await db.upsert_lots([lot, dict(lot, id=2, title="Germany Taler", country="Germany",
                                    category="Coins - Europe", current_bid=50.0)])
    top = await db.top_live_lots(["ru_imperial"], limit=3)
    assert [r["id"] for r in top] == [1]
    top_all = await db.top_live_lots([], limit=3)
    assert [r["id"] for r in top_all] == [1, 2]  # bid-descending
