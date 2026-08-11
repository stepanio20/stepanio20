"""SQLite storage: users, subscriptions, watchlists, auctions/lots cache, alerts."""
from __future__ import annotations

import time
from typing import Any, Iterable

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,              -- telegram user id
    username TEXT,
    lang TEXT DEFAULT 'ru',
    tier TEXT DEFAULT 'free',            -- free | pro | dealer
    sub_until INTEGER DEFAULT 0,         -- unix ts, 0 = none
    interests TEXT DEFAULT '',           -- csv of onboarding interests
    created INTEGER
);
CREATE TABLE IF NOT EXISTS watches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    query TEXT NOT NULL,                 -- keyword(s), matched case-insensitively
    max_price REAL,                      -- optional cap in auction currency
    created INTEGER
);
CREATE TABLE IF NOT EXISTS auctions (
    id INTEGER PRIMARY KEY,              -- site auction id
    title TEXT,
    status TEXT,                         -- upcoming | live | past
    starts INTEGER,
    ends INTEGER,
    lots_count INTEGER DEFAULT 0,
    url TEXT
);
CREATE TABLE IF NOT EXISTS lots (
    id INTEGER PRIMARY KEY,              -- site lot id
    auction_id INTEGER,
    number INTEGER,
    title TEXT,
    category TEXT,
    country TEXT,
    year TEXT,
    metal TEXT,
    grade TEXT,
    start_price REAL,
    current_bid REAL,
    bids INTEGER DEFAULT 0,
    estimate REAL,
    currency TEXT DEFAULT 'USD',
    realized REAL,                       -- filled for archive lots
    ends INTEGER,
    url TEXT,
    image TEXT,
    updated INTEGER
);
CREATE INDEX IF NOT EXISTS idx_lots_auction ON lots(auction_id);
CREATE INDEX IF NOT EXISTS idx_lots_title ON lots(title);
CREATE TABLE IF NOT EXISTS alerts_sent (
    user_id INTEGER,
    lot_id INTEGER,
    kind TEXT,                           -- match | closing | outbid_digest
    sent INTEGER,
    PRIMARY KEY (user_id, lot_id, kind)
);
CREATE TABLE IF NOT EXISTS seller_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    contact TEXT,
    description TEXT,
    created INTEGER
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    charge_id TEXT,
    tier TEXT,
    stars INTEGER,
    is_recurring INTEGER DEFAULT 0,
    created INTEGER
);
"""


class Database:
    def __init__(self, path: str):
        self.path = path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self.path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    @property
    def db(self) -> aiosqlite.Connection:
        assert self._db is not None, "Database.connect() was not awaited"
        return self._db

    # -- users ------------------------------------------------------------
    async def upsert_user(self, user_id: int, username: str | None) -> None:
        await self.db.execute(
            "INSERT INTO users(id, username, created) VALUES(?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET username=excluded.username",
            (user_id, username or "", int(time.time())),
        )
        await self.db.commit()

    async def get_user(self, user_id: int) -> aiosqlite.Row | None:
        cur = await self.db.execute("SELECT * FROM users WHERE id=?", (user_id,))
        return await cur.fetchone()

    async def set_lang(self, user_id: int, lang: str) -> None:
        await self.db.execute("UPDATE users SET lang=? WHERE id=?", (lang, user_id))
        await self.db.commit()

    async def set_interests(self, user_id: int, interests: str) -> None:
        await self.db.execute("UPDATE users SET interests=? WHERE id=?", (interests, user_id))
        await self.db.commit()

    async def set_tier(self, user_id: int, tier: str, until_ts: int) -> None:
        await self.db.execute(
            "UPDATE users SET tier=?, sub_until=? WHERE id=?", (tier, until_ts, user_id)
        )
        await self.db.commit()

    async def effective_tier(self, user_id: int) -> str:
        row = await self.get_user(user_id)
        if not row:
            return "free"
        if row["tier"] != "free" and row["sub_until"] > time.time():
            return row["tier"]
        return "free"

    async def all_user_ids(self) -> list[int]:
        cur = await self.db.execute("SELECT id FROM users")
        return [r["id"] for r in await cur.fetchall()]

    # -- watches ----------------------------------------------------------
    async def add_watch(self, user_id: int, query: str, max_price: float | None) -> int:
        cur = await self.db.execute(
            "INSERT INTO watches(user_id, query, max_price, created) VALUES(?,?,?,?)",
            (user_id, query.strip(), max_price, int(time.time())),
        )
        await self.db.commit()
        return cur.lastrowid or 0

    async def list_watches(self, user_id: int) -> list[aiosqlite.Row]:
        cur = await self.db.execute(
            "SELECT * FROM watches WHERE user_id=? ORDER BY id", (user_id,)
        )
        return list(await cur.fetchall())

    async def delete_watch(self, user_id: int, watch_id: int) -> None:
        await self.db.execute(
            "DELETE FROM watches WHERE id=? AND user_id=?", (watch_id, user_id)
        )
        await self.db.commit()

    async def all_watches(self) -> list[aiosqlite.Row]:
        cur = await self.db.execute("SELECT * FROM watches")
        return list(await cur.fetchall())

    # -- auctions / lots ---------------------------------------------------
    async def upsert_auction(self, a: dict[str, Any]) -> None:
        await self.db.execute(
            "INSERT INTO auctions(id,title,status,starts,ends,lots_count,url) "
            "VALUES(:id,:title,:status,:starts,:ends,:lots_count,:url) "
            "ON CONFLICT(id) DO UPDATE SET title=:title,status=:status,starts=:starts,"
            "ends=:ends,lots_count=:lots_count,url=:url",
            a,
        )
        await self.db.commit()

    async def upsert_lots(self, lots: Iterable[dict[str, Any]]) -> None:
        rows = list(lots)
        if not rows:
            return
        await self.db.executemany(
            "INSERT INTO lots(id,auction_id,number,title,category,country,year,metal,grade,"
            "start_price,current_bid,bids,estimate,currency,realized,ends,url,image,updated) "
            "VALUES(:id,:auction_id,:number,:title,:category,:country,:year,:metal,:grade,"
            ":start_price,:current_bid,:bids,:estimate,:currency,:realized,:ends,:url,:image,:updated) "
            "ON CONFLICT(id) DO UPDATE SET current_bid=:current_bid,bids=:bids,"
            "realized=:realized,ends=:ends,updated=:updated",
            rows,
        )
        await self.db.commit()

    async def live_auctions(self) -> list[aiosqlite.Row]:
        cur = await self.db.execute(
            "SELECT * FROM auctions WHERE status IN ('live','upcoming') ORDER BY starts"
        )
        return list(await cur.fetchall())

    async def search_lots(self, query: str, limit: int = 8) -> list[aiosqlite.Row]:
        like = f"%{query.strip()}%"
        cur = await self.db.execute(
            "SELECT l.*, a.title AS auction_title FROM lots l "
            "LEFT JOIN auctions a ON a.id=l.auction_id "
            "WHERE l.title LIKE ? COLLATE NOCASE AND (l.realized IS NULL) "
            "ORDER BY l.ends IS NULL, l.ends LIMIT ?",
            (like, limit),
        )
        return list(await cur.fetchall())

    async def price_history(self, query: str, limit: int = 8) -> list[aiosqlite.Row]:
        like = f"%{query.strip()}%"
        cur = await self.db.execute(
            "SELECT * FROM lots WHERE title LIKE ? COLLATE NOCASE AND realized IS NOT NULL "
            "ORDER BY updated DESC LIMIT ?",
            (like, limit),
        )
        return list(await cur.fetchall())

    async def closing_soon(self, within_minutes: int) -> list[aiosqlite.Row]:
        now = int(time.time())
        cur = await self.db.execute(
            "SELECT * FROM lots WHERE realized IS NULL AND ends IS NOT NULL "
            "AND ends BETWEEN ? AND ?",
            (now, now + within_minutes * 60),
        )
        return list(await cur.fetchall())

    # -- alerts ------------------------------------------------------------
    async def alert_already_sent(self, user_id: int, lot_id: int, kind: str) -> bool:
        cur = await self.db.execute(
            "SELECT 1 FROM alerts_sent WHERE user_id=? AND lot_id=? AND kind=?",
            (user_id, lot_id, kind),
        )
        return await cur.fetchone() is not None

    async def mark_alert_sent(self, user_id: int, lot_id: int, kind: str) -> None:
        await self.db.execute(
            "INSERT OR IGNORE INTO alerts_sent(user_id,lot_id,kind,sent) VALUES(?,?,?,?)",
            (user_id, lot_id, kind, int(time.time())),
        )
        await self.db.commit()

    # -- seller leads / payments ------------------------------------------
    async def add_seller_lead(self, user_id: int, contact: str, description: str) -> int:
        cur = await self.db.execute(
            "INSERT INTO seller_leads(user_id,contact,description,created) VALUES(?,?,?,?)",
            (user_id, contact, description, int(time.time())),
        )
        await self.db.commit()
        return cur.lastrowid or 0

    async def add_payment(
        self, user_id: int, charge_id: str, tier: str, stars: int, is_recurring: bool
    ) -> None:
        await self.db.execute(
            "INSERT INTO payments(user_id,charge_id,tier,stars,is_recurring,created) "
            "VALUES(?,?,?,?,?,?)",
            (user_id, charge_id, tier, stars, int(is_recurring), int(time.time())),
        )
        await self.db.commit()

    async def stats(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for key, sql in {
            "users": "SELECT COUNT(*) c FROM users",
            "paying": "SELECT COUNT(*) c FROM users WHERE tier!='free' AND sub_until>strftime('%s','now')",
            "watches": "SELECT COUNT(*) c FROM watches",
            "lots": "SELECT COUNT(*) c FROM lots",
            "leads": "SELECT COUNT(*) c FROM seller_leads",
        }.items():
            cur = await self.db.execute(sql)
            row = await cur.fetchone()
            out[key] = row["c"] if row else 0
        return out
