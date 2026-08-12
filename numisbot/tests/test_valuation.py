"""Valuation engine: keywords, transliteration, anchor/refine logic."""
import pytest
import pytest_asyncio

from bot.db import Database
from bot.services.valuation import keywords, valuate


def test_keywords_translit_and_stopwords():
    assert "poltina" in keywords("Россия полтина 1849 монета")
    assert "russia" in keywords("россия рубль")
    assert "rouble" in keywords("рубль Николай")
    assert "1849" in keywords("полтина 1849")
    assert keywords("и в с за") == []


@pytest_asyncio.fixture
async def db(tmp_path):
    d = Database(str(tmp_path / "v.sqlite3"))
    await d.connect()
    base = {"auction_id": 1, "number": 1, "category": "", "country": "", "year": "",
            "metal": "", "grade": "", "start_price": 5.0, "current_bid": None,
            "bids": 0, "estimate": None, "currency": "EUR", "ends": None,
            "url": "", "image": "", "updated": 1}
    await d.upsert_lots([
        dict(base, id=1, title="Russia Poltina 1849 SPB", realized=40.0),
        dict(base, id=2, title="Russia Poltina 1850", realized=60.0),
        dict(base, id=3, title="Russia Poltina 1849 R", realized=90.0),
        dict(base, id=4, title="Germany 3 Mark 1849", realized=25.0),
        dict(base, id=5, title="France 5 Francs 1849", realized=20.0),
    ])
    yield d
    await d.close()


@pytest.mark.asyncio
async def test_valuate_anchors_on_rare_word(db):
    v = await valuate(db, "Россия полтина 1849")
    assert v is not None
    assert "poltina" in v.used_words
    titles = [r["title"] for r in v.comparables]
    assert all("Poltina" in t for t in titles)


@pytest.mark.asyncio
async def test_year_alone_with_unknown_words_is_none(db):
    assert await valuate(db, "Атлантида космодрайв 1849") is None


@pytest.mark.asyncio
async def test_no_comps_returns_none(db):
    assert await valuate(db, "Mars colony token") is None
