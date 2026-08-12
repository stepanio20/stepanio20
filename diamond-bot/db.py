"""
SQLite persistence for the MVP (zero-setup, file-based). Mirrors the Dubai bot's
leads/events shape but modeled for diamonds: users, subscriptions, listings (have),
demands (want), matches, groups, events.

Swap to Postgres (Neon) later by re-implementing this module's function surface — the
rest of the bot only calls these functions, never SQL directly.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Iterable, Optional

from config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    tg_id       INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    role        TEXT DEFAULT 'buyer',         -- buyer | seller | broker
    company     TEXT,
    phone       TEXT,
    vetting     TEXT DEFAULT 'unverified',    -- unverified | pending | verified | rejected
    vetting_note TEXT,
    created_at  REAL,
    updated_at  REAL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id       INTEGER NOT NULL,
    tier        TEXT NOT NULL,                -- buyer | broker
    status      TEXT NOT NULL DEFAULT 'active',
    stars_paid  INTEGER DEFAULT 0,
    charge_id   TEXT,
    started_at  REAL,
    expires_at  REAL
);

CREATE TABLE IF NOT EXISTS listings (            -- "have" (supply)
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id       INTEGER,                       -- who posted (owner)
    source      TEXT DEFAULT 'forward',        -- forward | session | csv | manual | channel
    source_group TEXT,
    intent      TEXT DEFAULT 'have',
    shape TEXT, carat REAL, color TEXT, fancy_color TEXT, fancy_intensity TEXT,
    clarity TEXT, cut TEXT, lab TEXT, cert_number TEXT, fluorescence TEXT,
    price_per_carat REAL, total_price REAL, rap_discount REAL,
    raw_text TEXT, confidence REAL, flags TEXT,
    status      TEXT DEFAULT 'active',         -- active | sold | expired | flagged
    created_at  REAL,
    expires_at  REAL
);

CREATE TABLE IF NOT EXISTS demands (             -- "want" (looking for)
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id       INTEGER,
    source      TEXT DEFAULT 'manual',
    source_group TEXT,
    intent      TEXT DEFAULT 'want',
    shape TEXT, carat REAL, carat_min REAL, carat_max REAL,
    color TEXT, fancy_color TEXT, fancy_intensity TEXT,
    clarity TEXT, cut TEXT, lab TEXT,
    price_max_per_carat REAL, rap_discount REAL,
    raw_text TEXT, confidence REAL, flags TEXT,
    status      TEXT DEFAULT 'active',
    created_at  REAL
);

CREATE TABLE IF NOT EXISTS matches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    demand_id   INTEGER, listing_id INTEGER,
    score       REAL,
    notified    INTEGER DEFAULT 0,
    created_at  REAL,
    UNIQUE(demand_id, listing_id)
);

CREATE TABLE IF NOT EXISTS groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    handle      TEXT UNIQUE,
    title       TEXT,
    members     INTEGER,
    nature      TEXT,                          -- demand | supply | mixed | channel
    market      TEXT DEFAULT 'dubai',
    enabled     INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT,
    tg_id       INTEGER,
    data        TEXT,
    created_at  REAL
);

CREATE TABLE IF NOT EXISTS reveal_grants (
    tg_id       INTEGER NOT NULL,
    listing_id  INTEGER NOT NULL,
    created_at  REAL,
    UNIQUE(tg_id, listing_id)
);

CREATE INDEX IF NOT EXISTS ix_listings_match ON listings(status, shape, carat);
CREATE INDEX IF NOT EXISTS ix_listings_owner ON listings(tg_id, status);
CREATE INDEX IF NOT EXISTS ix_demands_active ON demands(status, tg_id);
CREATE INDEX IF NOT EXISTS ix_events        ON events(type, tg_id, created_at);
CREATE INDEX IF NOT EXISTS ix_subs_charge   ON subscriptions(charge_id);
"""

_LISTING_COLS = ["tg_id", "source", "source_group", "intent", "shape", "carat", "color",
                 "fancy_color", "fancy_intensity", "clarity", "cut", "lab", "cert_number",
                 "fluorescence", "price_per_carat", "total_price", "rap_discount",
                 "raw_text", "confidence", "flags", "status", "created_at", "expires_at"]

_DEMAND_COLS = ["tg_id", "source", "source_group", "intent", "shape", "carat", "carat_min",
                "carat_max", "color", "fancy_color", "fancy_intensity", "clarity", "cut",
                "lab", "price_max_per_carat", "rap_discount", "raw_text", "confidence",
                "flags", "status", "created_at"]


@contextmanager
def _conn():
    con = sqlite3.connect(settings.database_path, timeout=5.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")     # concurrent readers + one writer, no 'database is locked'
    con.execute("PRAGMA busy_timeout=5000")
    con.execute("PRAGMA synchronous=NORMAL")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    # ensure the DB directory exists (e.g. a mounted Railway volume at /data)
    import os
    parent = os.path.dirname(os.path.abspath(settings.database_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with _conn() as con:
        con.executescript(SCHEMA)


def log_event(type_: str, tg_id: Optional[int] = None, data: Optional[dict] = None) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO events(type, tg_id, data, created_at) VALUES (?,?,?,?)",
            (type_, tg_id, json.dumps(data or {}), time.time()),
        )


# ── users ──
def upsert_user(tg_id: int, username: str = "", full_name: str = "", **fields: Any) -> None:
    now = time.time()
    with _conn() as con:
        row = con.execute("SELECT tg_id FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        if row:
            sets = ", ".join(f"{k}=?" for k in fields)
            params = list(fields.values())
            if sets:
                con.execute(f"UPDATE users SET {sets}, username=?, full_name=?, updated_at=? WHERE tg_id=?",
                            [*params, username, full_name, now, tg_id])
            else:
                con.execute("UPDATE users SET username=?, full_name=?, updated_at=? WHERE tg_id=?",
                            (username, full_name, now, tg_id))
        else:
            con.execute(
                "INSERT INTO users(tg_id, username, full_name, created_at, updated_at) VALUES (?,?,?,?,?)",
                (tg_id, username, full_name, now, now),
            )
            if fields:
                sets = ", ".join(f"{k}=?" for k in fields)
                con.execute(f"UPDATE users SET {sets} WHERE tg_id=?", [*fields.values(), tg_id])


def get_user(tg_id: int) -> Optional[dict]:
    with _conn() as con:
        row = con.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        return dict(row) if row else None


def set_vetting(tg_id: int, status: str, note: str = "") -> None:
    with _conn() as con:
        con.execute("UPDATE users SET vetting=?, vetting_note=?, updated_at=? WHERE tg_id=?",
                    (status, note, time.time(), tg_id))


# ── subscriptions ──
def add_subscription(tg_id: int, tier: str, stars: int, days: int, charge_id: str = "") -> None:
    now = time.time()
    with _conn() as con:
        con.execute(
            "INSERT INTO subscriptions(tg_id, tier, status, stars_paid, charge_id, started_at, expires_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (tg_id, tier, "active", stars, charge_id, now, now + days * 86400),
        )


def subscription_by_charge(charge_id: str) -> Optional[dict]:
    if not charge_id:
        return None
    with _conn() as con:
        row = con.execute("SELECT * FROM subscriptions WHERE charge_id=? LIMIT 1", (charge_id,)).fetchone()
        return dict(row) if row else None


def active_subscription(tg_id: int) -> Optional[dict]:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM subscriptions WHERE tg_id=? AND status='active' AND expires_at>? "
            "ORDER BY expires_at DESC LIMIT 1", (tg_id, time.time()),
        ).fetchone()
        return dict(row) if row else None


# ── listings / demands ──
def _insert(con, table: str, cols: list[str], values: dict) -> int:
    ordered = [values.get(c) for c in cols]
    placeholders = ",".join("?" for _ in cols)
    cur = con.execute(f"INSERT INTO {table}({','.join(cols)}) VALUES ({placeholders})", ordered)
    return cur.lastrowid


def add_listing(stone: dict, tg_id: Optional[int] = None, source: str = "forward",
                source_group: str = "", ttl_days: int = 30) -> int:
    now = time.time()
    v = dict(stone)
    v["flags"] = json.dumps(v.get("flags") or [])
    v.update(tg_id=tg_id, source=source, source_group=source_group,
             status="active", created_at=now, expires_at=now + ttl_days * 86400,
             intent="have")
    with _conn() as con:
        return _insert(con, "listings", _LISTING_COLS, v)


def add_listings_bulk(stones: list[dict], tg_id: Optional[int] = None, source: str = "seed",
                      source_group: str = "", ttl_days: int = 3650) -> int:
    """Insert many listings on one connection (for seeding large inventories)."""
    now = time.time()
    rows = []
    for stone in stones:
        v = dict(stone)
        v["flags"] = json.dumps(v.get("flags") or [])
        v.update(tg_id=tg_id, source=source, source_group=source_group,
                 status="active", created_at=now, expires_at=now + ttl_days * 86400,
                 intent="have")
        rows.append([v.get(c) for c in _LISTING_COLS])
    placeholders = ",".join("?" for _ in _LISTING_COLS)
    with _conn() as con:
        con.executemany(
            f"INSERT INTO listings({','.join(_LISTING_COLS)}) VALUES ({placeholders})", rows)
    return len(rows)


def add_demand(stone: dict, tg_id: Optional[int] = None, source: str = "manual",
               source_group: str = "") -> int:
    now = time.time()
    v = dict(stone)
    v["flags"] = json.dumps(v.get("flags") or [])
    v["price_max_per_carat"] = v.get("price_per_carat") or v.get("price_max_per_carat")
    v.update(tg_id=tg_id, source=source, source_group=source_group,
             status="active", created_at=now, intent="want")
    with _conn() as con:
        return _insert(con, "demands", _DEMAND_COLS, v)


def active_listings() -> list[dict]:
    with _conn() as con:
        rows = con.execute("SELECT * FROM listings WHERE status='active' AND expires_at>?",
                           (time.time(),)).fetchall()
        return [dict(r) for r in rows]


def candidate_listings(demand: dict, limit: int = 1500) -> list[dict]:
    """SQL pre-filter for matching: narrow a large inventory by shape, carat range
    and growth pool before Python scoring. Falls back to broad if demand is vague."""
    where = ["status='active'", "expires_at>?"]
    params: list = [time.time()]
    if demand.get("shape"):
        where.append("(shape=? OR shape IS NULL)")
        params.append(demand["shape"])
    target = demand.get("carat")
    lo, hi = demand.get("carat_min"), demand.get("carat_max")
    if lo or hi:
        where.append("(carat IS NULL OR carat BETWEEN ? AND ?)")
        params += [(lo or 0) * 0.95, (hi or 99) * 1.05]
    elif target:
        where.append("(carat IS NULL OR carat BETWEEN ? AND ?)")
        params += [target * 0.85, target * 1.15]
    # keep natural and lab-grown in separate pools (matcher enforces it too)
    if "lab_grown" in (demand.get("flags") or ""):
        where.append("flags LIKE '%lab_grown%'")
    else:
        where.append("(flags IS NULL OR flags NOT LIKE '%lab_grown%')")
    # order by carat proximity to the target so LIMIT keeps the closest stones (not arbitrary rowids)
    order = ""
    if target:
        order = " ORDER BY ABS(COALESCE(carat, ?) - ?)"
        params += [target, target]
    q = f"SELECT * FROM listings WHERE {' AND '.join(where)}{order} LIMIT ?"
    params.append(limit)
    with _conn() as con:
        return [dict(r) for r in con.execute(q, params).fetchall()]


def active_demands() -> list[dict]:
    with _conn() as con:
        rows = con.execute("SELECT * FROM demands WHERE status='active'").fetchall()
        return [dict(r) for r in rows]


def get_listing(listing_id: int) -> Optional[dict]:
    with _conn() as con:
        row = con.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
        return dict(row) if row else None


def listings_for_user(tg_id: int, status: str = "active", limit: int = 50) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM listings WHERE tg_id=? AND status=? ORDER BY created_at DESC LIMIT ?",
            (tg_id, status, limit)).fetchall()
        return [dict(r) for r in rows]


def count_active_listings(tg_id: int) -> int:
    with _conn() as con:
        return con.execute(
            "SELECT COUNT(*) FROM listings WHERE tg_id=? AND status='active'", (tg_id,)
        ).fetchone()[0]


def demands_for_user(tg_id: int, limit: int = 50) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM demands WHERE tg_id=? AND status='active' ORDER BY created_at DESC LIMIT ?",
            (tg_id, limit)).fetchall()
        return [dict(r) for r in rows]


def mark_listing_sold(listing_id: int, tg_id: Optional[int] = None) -> bool:
    """Mark a listing sold. If tg_id is given, only the owner can do it. Returns success."""
    with _conn() as con:
        if tg_id is not None:
            cur = con.execute("UPDATE listings SET status='sold' WHERE id=? AND tg_id=? AND status='active'",
                              (listing_id, tg_id))
        else:
            cur = con.execute("UPDATE listings SET status='sold' WHERE id=? AND status='active'", (listing_id,))
        return cur.rowcount > 0


def get_demand(demand_id: int) -> Optional[dict]:
    with _conn() as con:
        row = con.execute("SELECT * FROM demands WHERE id=?", (demand_id,)).fetchone()
        return dict(row) if row else None


# ── matches ──
def record_match(demand_id: int, listing_id: int, score: float, notified: int = 0) -> Optional[int]:
    with _conn() as con:
        try:
            cur = con.execute(
                "INSERT INTO matches(demand_id, listing_id, score, notified, created_at) VALUES (?,?,?,?,?)",
                (demand_id, listing_id, score, notified, time.time()),
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None  # already recorded


def unnotified_matches() -> list[dict]:
    with _conn() as con:
        rows = con.execute("SELECT * FROM matches WHERE notified=0 ORDER BY score DESC").fetchall()
        return [dict(r) for r in rows]


def mark_notified(match_id: int) -> None:
    with _conn() as con:
        con.execute("UPDATE matches SET notified=1 WHERE id=?", (match_id,))


def user_matched_listing(tg_id: int, listing_id: int) -> bool:
    """True if this user has a search that matched this listing (anti-enumeration for Connect)."""
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM matches m JOIN demands d ON d.id=m.demand_id "
            "WHERE m.listing_id=? AND d.tg_id=? LIMIT 1", (listing_id, tg_id)).fetchone()
        return row is not None


def grant_reveal(tg_id: int, listing_id: int) -> None:
    """Record that a user may reveal a listing (e.g. arrived via a seller's share link)."""
    with _conn() as con:
        con.execute("INSERT OR IGNORE INTO reveal_grants(tg_id, listing_id, created_at) VALUES (?,?,?)",
                    (tg_id, listing_id, time.time()))


def has_reveal_grant(tg_id: int, listing_id: int) -> bool:
    with _conn() as con:
        row = con.execute("SELECT 1 FROM reveal_grants WHERE tg_id=? AND listing_id=? LIMIT 1",
                          (tg_id, listing_id)).fetchone()
        return row is not None


def matches_for_user(tg_id: int, limit: int = 20) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT m.*, l.raw_text AS listing_text, d.raw_text AS demand_text "
            "FROM matches m JOIN demands d ON d.id=m.demand_id JOIN listings l ON l.id=m.listing_id "
            "WHERE d.tg_id=? ORDER BY m.created_at DESC LIMIT ?", (tg_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ── groups ──
def seed_groups(rows: Iterable[dict]) -> None:
    with _conn() as con:
        for r in rows:
            con.execute(
                "INSERT OR IGNORE INTO groups(handle, title, members, nature, market) "
                "VALUES (?,?,?,?,?)",
                (r["handle"], r.get("title", ""), r.get("members", 0),
                 r.get("nature", "mixed"), r.get("market", "dubai")),
            )


def funnel() -> dict:
    """Acquisition→revenue funnel from the events table (distinct users per stage)."""
    stages = {
        "started": "type='start'",
        "role_set": "type='role_selected'",
        "uploaded": "type IN ('listing_created','csv_imported')",
        "searched": "type='demand_created'",
        "matched": "type='match_shown'",
        "connected": "type='contact_revealed'",
        "buy_clicked": "type='buy_clicked'",
        "subscribed": "type='subscription_paid'",
    }
    out = {}
    with _conn() as con:
        for name, cond in stages.items():
            out[name] = con.execute(
                f"SELECT COUNT(DISTINCT tg_id) FROM events WHERE {cond}").fetchone()[0]
    return out


def counts() -> dict:
    with _conn() as con:
        def one(q):
            return con.execute(q).fetchone()[0]
        return {
            "users": one("SELECT COUNT(*) FROM users"),
            "listings": one("SELECT COUNT(*) FROM listings WHERE status='active'"),
            "demands": one("SELECT COUNT(*) FROM demands WHERE status='active'"),
            "matches": one("SELECT COUNT(*) FROM matches"),
            "subs": one("SELECT COUNT(*) FROM subscriptions WHERE status='active'"),
        }
