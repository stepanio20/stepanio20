"""Pure-logic tests for bot/services/certs.py (no network: only parse/lookup)."""
from __future__ import annotations

import pytest

from bot.services.certs import LOOKUP_URLS, lookup_url, parse_cert_input


# ---------------------------------------------------------------- valid input
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("PCGS 45689164", ("PCGS", "45689164")),
        ("pcgs 45689164", ("PCGS", "45689164")),          # lowercase service
        ("Pcgs:45689164", ("PCGS", "45689164")),          # colon separator
        ("PCGS#45689164", ("PCGS", "45689164")),          # hash separator
        ("PCGS-45689164", ("PCGS", "45689164")),          # dash separator
        ("pcgs45689164", ("PCGS", "45689164")),           # no separator at all
        ("  PCGS   45689164  ", ("PCGS", "45689164")),    # stray whitespace
        ("PCGS 1234567", ("PCGS", "1234567")),            # 7 digits (min)
        ("PCGS 123456789", ("PCGS", "123456789")),        # 9 digits (max)
        ("NGC 6805461-001", ("NGC", "6805461-001")),
        ("ngc 123456-001", ("NGC", "123456-001")),        # 6-digit prefix (min)
        ("NGC 12345678-001", ("NGC", "12345678-001")),    # 8-digit prefix (max)
        ("ngc -6805461-001-", ("NGC", "6805461-001")),    # leading/trailing dashes stripped
        ("PMG 1234567-001", ("PMG", "1234567-001")),
        ("pmg:1234567-001", ("PMG", "1234567-001")),
    ],
)
def test_parse_valid(raw, expected):
    assert parse_cert_input(raw) == expected


# -------------------------------------------------------------- invalid input
@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "PCGS",                          # no number
        "NGC",
        "PCGS 123456",                   # 6 digits — too short
        "PCGS 1234567890",               # 10 digits — too long
        "NGC 6805461",                   # NGC requires -NNN suffix
        "NGC 6805461-01",                # suffix too short
        "NGC 6805461-0011",              # suffix too long
        "NGC 123456789-001",             # 9-digit prefix — too long
        "PMG 12345-001",                 # 5-digit prefix — too short
        "NGC 6805461_001",               # wrong suffix separator
        "ICG 1234567",                   # unknown grading service
        "PCGS 45689164 and something",   # trailing garbage
        "sell me 45689164",              # no service token at start
        "45689164",                      # bare number, unknown service
        "'; DROP TABLE listings; --",    # SQL-injection garbage
        "<script>alert(1)</script>",     # HTML-injection garbage
        "PCGS <b>45689164</b>",
        "NGC 68054 61-001",              # space inside the number
    ],
)
def test_parse_invalid(raw):
    assert parse_cert_input(raw) is None


def test_parse_rejects_non_ascii_digits():
    """KNOWN BUG: regexes in certs.py use \\d / no re.ASCII, so Unicode digits
    (Arabic-Indic, full-width) pass validation. A homoglyph cert number looks
    identical to buyers, defeats db.cert_in_use() exact-string dedup
    ("one slab - one listing" anti-fraud) and produces a bogus registry URL.
    """
    assert parse_cert_input("PCGS 4568916٤") is None      # ٤ ARABIC-INDIC FOUR
    assert parse_cert_input("PCGS ４５６８９１６４") is None  # full-width


# ----------------------------------------------------------------- lookup_url
def test_lookup_url_pcgs():
    assert lookup_url("PCGS", "45689164") == "https://www.pcgs.com/cert/45689164"


def test_lookup_url_ngc():
    assert lookup_url("NGC", "6805461-001") == "https://www.ngccoin.com/certlookup/6805461-001/"


def test_lookup_url_pmg():
    assert lookup_url("PMG", "1234567-001") == "https://www.pmgnotes.com/certlookup/1234567-001/"


def test_lookup_url_https_only():
    for tpl in LOOKUP_URLS.values():
        assert tpl.startswith("https://")


def test_parse_then_lookup_roundtrip():
    service, number = parse_cert_input("ngc 6805461-001")
    url = lookup_url(service, number)
    assert number in url and url.startswith("https://")


def test_lookup_url_unknown_service_raises():
    with pytest.raises(KeyError):
        lookup_url("ICG", "123")
