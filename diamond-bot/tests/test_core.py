"""
Core regression tests — matcher, ingest, payments, and the Connect security gate.
Runs standalone (no pytest needed) against a throwaway DB:

    python tests/test_core.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# import from the package root and isolate the DB before importing db/config
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
_TMP = tempfile.mkdtemp()
os.environ["DATABASE_PATH"] = os.path.join(_TMP, "test_core.db")
os.environ["FREE_REVEAL"] = "false"

import db          # noqa: E402
import ingest      # noqa: E402
import matcher     # noqa: E402
import payments    # noqa: E402
import bot         # noqa: E402

db.init_db()

_passed = _failed = 0


def check(name: str, cond: bool) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {name}")
    else:
        _failed += 1
        print(f"  FAIL  {name}")


# ── matcher ──
NAT = lambda **k: {"flags": "[]", **k}  # noqa: E731
LAB = lambda **k: {"flags": '["lab_grown"]', **k}  # noqa: E731

check("natural matches natural",
      matcher.score(NAT(shape="round", carat=1.0, color="G", clarity="VS2"),
                    NAT(shape="round", carat=1.01, color="G", clarity="VS2")) > 0)
check("natural never matches lab-grown",
      matcher.score(NAT(shape="round", carat=1.0), LAB(shape="round", carat=1.0)) == 0.0)
check("lab never matches natural",
      matcher.score(LAB(shape="round", carat=1.0), NAT(shape="round", carat=1.0)) == 0.0)
check("white query excludes fancy listing",
      matcher.score(NAT(shape="round", carat=1.0, color="G"),
                    NAT(shape="round", carat=1.0, fancy_color="pink")) == 0.0)
check("fancy hue must match",
      matcher.score(NAT(shape="oval", carat=1.0, fancy_color="pink"),
                    NAT(shape="oval", carat=1.0, fancy_color="blue")) == 0.0)
check("over-budget is hard-filtered to 0",
      matcher.score(NAT(shape="round", carat=1.0, color="G", clarity="VS2", price_per_carat=4000),
                    NAT(shape="round", carat=1.0, color="G", clarity="VS2", price_per_carat=6000)) == 0.0)
check("under-budget still matches",
      matcher.score(NAT(shape="round", carat=1.0, color="G", clarity="VS2", price_per_carat=4000),
                    NAT(shape="round", carat=1.0, color="G", clarity="VS2", price_per_carat=3800)) > 0)
check("carat far out-of-tolerance fails",
      matcher.score(NAT(shape="round", carat=2.0), NAT(shape="round", carat=1.0)) == 0.0)
check("shape mismatch fails",
      matcher.score(NAT(shape="round", carat=1.0), NAT(shape="oval", carat=1.0)) == 0.0)

# ── ingest ──
CSV = (b"Shape,Weight,Color,Clarity,Lab,Certification #,%Off,Price/Ct\n"
       b"Round,1.01,G,VS2,GIA,111,-22,5040\n"
       b"BR,2.00,F,VS1,GIA,222,-30,9000\n"
       b"Oval,1.50,H,SI1,IGI,333,-40,3000\n")
res = ingest.import_csv(CSV, tg_id=1)
check("csv import stores rows", res["stored"] == 3)
mine = db.listings_for_user(1)
shapes = {l["shape"] for l in mine}
check("csv 'BR' normalized to round", "round" in shapes)
check("csv maps %Off to rap_discount", any(l["rap_discount"] == -22 for l in mine))
check("csv cap honored (remaining=1)", ingest.import_csv(CSV, tg_id=2, remaining=1)["stored"] == 1)

XLSX_LG = b""  # xlsx tested elsewhere; growth flag path:
lg = ingest._map_row({"Shape": "Oval", "Weight": "1.0", "Growth Type": "CVD", "Clarity": "VS1"})
check("lab-grown row flagged", "lab_grown" in (lg or {}).get("flags", []))

# ── payments ──
ev = {"data": {"id": "CH-1", "status": "success", "amount_total": "99",
               "metadata": {"tg_id": "777", "tier": "grow"}}}
check("payment activates", payments.handle_webhook_event(ev) == (777, "grow"))
check("payment idempotent on replay", payments.handle_webhook_event(ev) == (777, "grow"))
check("one subscription row only", db.counts()["subs"] == 1)
check("tier inferred from amount",
      payments.handle_webhook_event({"data": {"id": "CH-2", "status": "success", "amount": "199",
                                              "metadata": {"tg_id": "778"}}}) == (778, "pro"))
check("no charge_id is rejected",
      payments.handle_webhook_event({"data": {"status": "success", "amount": "99",
                                              "metadata": {"tg_id": "779", "tier": "grow"}}}) is None)
check("unknown amount not granted",
      payments.handle_webhook_event({"data": {"id": "CH-9", "status": "success", "amount": "7",
                                              "metadata": {"tg_id": "780"}}}) is None)
check("webhook auth fails closed (no secret)", payments.verify_webhook_auth("anything") is False)

# ── Connect security gate ──
db.upsert_user(50, "seller", "S")
ingest.ingest_text("Round 1ct G VS2 GIA $5000/ct", tg_id=50, source="manual", default_intent="have")
lid = [l for l in db.active_listings() if l["tg_id"] == 50][0]["id"]
check("enumerator cannot reveal", bot._may_reveal(999, lid) is False)
did = db.add_demand({"shape": "round", "carat": 1.0, "color": "G", "clarity": "VS2", "raw_text": "1ct G VS2"}, tg_id=60)
db.record_match(did, lid, 0.95)
check("matched buyer can reveal", bot._may_reveal(60, lid) is True)
db.grant_reveal(70, lid)
check("share-link grant can reveal", bot._may_reveal(70, lid) is True)
check("owner can reveal", bot._may_reveal(50, lid) is True)

print(f"\n{_passed}/{_passed + _failed} passed")
sys.exit(1 if _failed else 0)
