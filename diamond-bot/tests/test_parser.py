"""
Parser tests anchored to REAL messages captured from the target Telegram groups
(@demandsnatural, @diamondsexport, @certifieddiamonds, @diamonds_jewels_antwerp)
plus canonical dealer shorthand. Run: `python -m pytest -q` or `python tests/test_parser.py`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser import parse_message, Intent  # noqa: E402


def test_fancy_intense_pink_offer():
    r = parse_message("Today deal 1.43ct oval Fancy intense pink $32,000 per ct")
    assert r is not None
    assert r.shape == "oval"
    assert r.carat == 1.43
    assert r.fancy_color == "pink"
    assert r.fancy_intensity == "fancy intense"
    assert r.price_per_carat == 32000
    assert r.intent == Intent.HAVE.value


def test_european_decimal_price():
    # "$26.000" is 26,000 not 26.0 — dealer European-style thousands
    r = parse_message("GIA Cushion 0.90ct Fancy light Pink SI1 like VS $26.000 per ct")
    assert r.shape == "cushion"
    assert r.carat == 0.90
    assert r.fancy_color == "pink"
    assert r.fancy_intensity == "fancy light"
    assert r.clarity == "SI1"
    assert r.lab == "GIA"
    assert r.price_per_carat == 26000


def test_pear_d_if_hyphen_notation():
    r = parse_message("Pear shape 3.24ct D-IF")
    assert r.shape == "pear"
    assert r.carat == 3.24
    assert r.color == "D"
    assert r.clarity == "IF"


def test_looking_for_is_want():
    r = parse_message("LOOKING FOR 2ct D VS1 GIA only, Rap -25%")
    assert r.intent == Intent.WANT.value
    assert r.carat == 2.0
    assert r.color == "D"
    assert r.clarity == "VS1"
    assert r.lab == "GIA"
    assert r.rap_discount == -25.0


def test_bare_decimal_carat_and_cert():
    r = parse_message("Available: Round 1.01 G VS2 GIA 2185763456 Rap -22%")
    assert r.intent == Intent.HAVE.value
    assert r.shape == "round"
    assert r.carat == 1.01
    assert r.color == "G"
    assert r.clarity == "VS2"
    assert r.lab == "GIA"
    assert r.cert_number == "2185763456"
    assert r.rap_discount == -22.0


def test_want_range_carat():
    r = parse_message("Looking for 1.50-2.00ct round E-F VVS")
    assert r.intent == Intent.WANT.value
    assert r.shape == "round"
    assert r.carat_min == 1.50
    assert r.carat_max == 2.00


def test_lab_grown_flagged():
    r = parse_message("For sale 2.05ct round E VS1 IGI lab grown CVD")
    assert "lab_grown" in r.flags
    assert r.lab == "IGI"


def test_scam_flagged():
    r = parse_message("God bless, send western union advance fee for 5ct D IF diamond")
    assert "scam_suspect" in r.flags


def test_pure_chatter_is_none():
    assert parse_message("good morning everyone, mazal!") is None
    assert parse_message("") is None


def test_group_default_intent_applies():
    # supply-side group with a bare listing and no explicit verb
    r = parse_message("Emerald 5.02ct F VVS2", default_intent=Intent.HAVE.value)
    assert r.intent == Intent.HAVE.value
    assert r.shape == "emerald"
    assert r.carat == 5.02


def test_total_price_when_no_per_ct():
    r = parse_message("1.43ct oval fancy intense pink, ask $46000")
    assert r.total_price == 46000
    assert r.price_per_carat is None


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn()
            passed += 1
            print(f"  PASS  {fn.__name__}")
        except AssertionError as e:
            print(f"  FAIL  {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(fns)} passed")
    return passed == len(fns)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
