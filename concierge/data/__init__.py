"""Static reference data shipped with the package (catalogues, mappings).

Personal / time-varying data lives in users/<user>/, never here.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).resolve().parent


@lru_cache(maxsize=4)
def load_venues(city: str = "barcelona") -> dict:
    p = _DATA / f"{city.lower()}_venues.json"
    if not p.exists():
        return {"labs": [], "wellness": [], "food_delivery": [],
                "service_to_test_map": {}, "dish_to_venue_map": {}}
    return json.loads(p.read_text())


def venue_for_service(service: str, city: str = "barcelona") -> dict | None:
    v = load_venues(city)
    ids = v.get("service_to_test_map", {}).get(service, [])
    if not ids:
        return None
    for lab in v["labs"]:
        if lab["id"] == ids[0]:
            return lab
    return None


def venues_for_dish(dish_name: str, city: str = "barcelona", limit: int = 2) -> list[dict]:
    v = load_venues(city)
    ids = v.get("dish_to_venue_map", {}).get(dish_name, [])[:limit]
    if not ids:
        return []
    out = []
    by_id = {p["id"]: p for p in v["food_delivery"]}
    for i in ids:
        if i in by_id:
            out.append(by_id[i])
    return out


def wellness_venue(kind_hint: str, city: str = "barcelona") -> dict | None:
    """Return a default wellness venue. kind_hint: 'sauna' | 'massage' | 'hammam'."""
    v = load_venues(city)
    h = kind_hint.lower()
    for w in v["wellness"]:
        if h in w.get("kind", "").lower() or h in " ".join(w.get("services", [])).lower():
            return w
    return v["wellness"][0] if v["wellness"] else None
