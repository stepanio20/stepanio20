"""
Matching engine: score a demand ("want") against a listing ("have").

Diamond matching is fuzzy on purpose — a buyer asking for "2ct D VS1" will happily
look at 1.95ct D VS1 or 2.02ct E VS1. We score on the 4Cs with graded tolerances and
a price ceiling, returning 0..1. Callers persist matches above a threshold.
"""
from __future__ import annotations

from typing import Optional

COLOR_ORDER = list("DEFGHIJKLMNOPQRSTUVWXYZ")
CLARITY_ORDER = ["FL", "IF", "VVS1", "VVS2", "VS1", "VS2", "SI1", "SI2", "SI3", "I1", "I2", "I3"]


def _rank(seq: list[str], v: Optional[str]) -> Optional[int]:
    if not v:
        return None
    v = v.upper()
    return seq.index(v) if v in seq else None


def _carat_ok(demand: dict, listing: dict) -> Optional[float]:
    """Return a 0..1 closeness on carat, or None if hard-incompatible."""
    lc = listing.get("carat")
    if lc is None:
        return 0.5  # unknown listing carat — neutral, don't hard-fail
    lo = demand.get("carat_min")
    hi = demand.get("carat_max")
    target = demand.get("carat")
    if lo or hi:
        lo = lo or 0
        hi = hi or 99
        # allow a small 3% spill over the range edges
        if lo * 0.97 <= lc <= hi * 1.03:
            return 1.0
        return None
    if target:
        # within ±5% → strong; ±12% → ok; else fail
        diff = abs(lc - target) / target
        if diff <= 0.05:
            return 1.0
        if diff <= 0.12:
            return 0.7
        return None
    return 0.6  # demand has no carat constraint


def score(demand: dict, listing: dict) -> float:
    """Weighted 0..1 match score. 0 means incompatible."""
    # shape is a hard filter when the demand specifies one
    if demand.get("shape") and listing.get("shape") and demand["shape"] != listing["shape"]:
        return 0.0

    # fancy vs white: a fancy demand needs a fancy listing (and color family must match)
    d_fancy, l_fancy = demand.get("fancy_color"), listing.get("fancy_color")
    if d_fancy and l_fancy and d_fancy != l_fancy:
        return 0.0
    if d_fancy and not l_fancy:
        return 0.0

    carat_c = _carat_ok(demand, listing)
    if carat_c is None:
        return 0.0

    # natural and lab-grown never cross-match — separate pools both directions
    if ("lab_grown" in (listing.get("flags") or "")) != ("lab_grown" in (demand.get("flags") or "")):
        return 0.0

    weights = {"carat": 0.30, "color": 0.25, "clarity": 0.25, "shape": 0.10, "price": 0.10}
    s = 0.0
    s += weights["carat"] * carat_c

    # color: listing must be same-or-better (lower index) within 1 grade of tolerance
    dc, lcx = _rank(COLOR_ORDER, demand.get("color")), _rank(COLOR_ORDER, listing.get("color"))
    if demand.get("color"):
        if lcx is None:
            s += weights["color"] * 0.4
        elif lcx <= dc:
            s += weights["color"]                       # equal or whiter
        elif lcx - dc == 1:
            s += weights["color"] * 0.6                 # one grade off
        else:
            s += weights["color"] * 0.1
    else:
        s += weights["color"] * 0.7

    # clarity: same logic
    dcl, lcl = _rank(CLARITY_ORDER, demand.get("clarity")), _rank(CLARITY_ORDER, listing.get("clarity"))
    if demand.get("clarity"):
        if lcl is None:
            s += weights["clarity"] * 0.4
        elif lcl <= dcl:
            s += weights["clarity"]
        elif lcl - dcl == 1:
            s += weights["clarity"] * 0.6
        else:
            s += weights["clarity"] * 0.1
    else:
        s += weights["clarity"] * 0.7

    # shape present & equal
    if demand.get("shape") and demand.get("shape") == listing.get("shape"):
        s += weights["shape"]
    elif not demand.get("shape"):
        s += weights["shape"] * 0.7

    # price ceiling: if demand has a max $/ct, listing must be under it
    cap = demand.get("price_max_per_carat")
    lp = listing.get("price_per_carat")
    if cap and lp:
        s += weights["price"] if lp <= cap * 1.05 else 0.0
    else:
        s += weights["price"] * 0.6

    # lab preference (GIA-only demands)
    if demand.get("lab") and listing.get("lab") and demand["lab"] != listing["lab"]:
        s *= 0.85

    return round(min(1.0, s), 3)


def run_matching(demands: list[dict], listings: list[dict], threshold: float = 0.6):
    """Yield (demand, listing, score) for every pair above threshold, best first."""
    out = []
    for d in demands:
        for l in listings:
            sc = score(d, l)
            if sc >= threshold:
                out.append((d, l, sc))
    out.sort(key=lambda t: t[2], reverse=True)
    return out


if __name__ == "__main__":
    demand = {"shape": "round", "carat": 2.0, "color": "D", "clarity": "VS1", "lab": "GIA"}
    tests = [
        {"shape": "round", "carat": 2.02, "color": "D", "clarity": "VS1", "lab": "GIA"},
        {"shape": "round", "carat": 1.95, "color": "E", "clarity": "VS2", "lab": "GIA"},
        {"shape": "oval", "carat": 2.0, "color": "D", "clarity": "VS1"},
        {"shape": "round", "carat": 2.0, "color": "H", "clarity": "SI2"},
    ]
    for t in tests:
        print(f"{t} -> {score(demand, t)}")
