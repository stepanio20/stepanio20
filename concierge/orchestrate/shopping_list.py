"""Shopping list generator — week's cook-meals -> grouped, scaled ingredient list.

Deterministic. Reads the same plan structure the renderer reads. Scales every
ingredient by its meal's portion factor, sums by item name, groups by category,
and renders Markdown with Barcelona supermarket deep-links per section.

Order-meals are excluded by design — those are bought through the delivery app,
not the supermarket.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

# --- Quantity scaling helpers ---------------------------------------------- #
_QTY_RX = re.compile(r"^([\d¼½¾.]+)\s*(.*)$")
_FRACT = {"¼": 0.25, "½": 0.5, "¾": 0.75}


def _parse_qty(qty: str) -> tuple[float | None, str]:
    """Return (number, unit_or_rest). E.g. '180 g' -> (180.0, 'g'),
    '1' -> (1.0, ''), '½' -> (0.5, ''), 'to taste' -> (None, 'to taste')."""
    s = qty.strip()
    if s in _FRACT:
        return _FRACT[s], ""
    m = _QTY_RX.match(s)
    if not m:
        return None, s
    num_str, rest = m.group(1), m.group(2).strip()
    if num_str in _FRACT:
        n = _FRACT[num_str]
    else:
        try:
            n = float(num_str)
        except ValueError:
            return None, qty
    return n, rest


def _fmt_qty(n: float, unit: str) -> str:
    if n == int(n):
        return f"{int(n)}{(' ' + unit) if unit else ''}".strip()
    return f"{n:.1f}{(' ' + unit) if unit else ''}".strip()


# --- Aggregation ----------------------------------------------------------- #
_CATEGORIES_ORDER = ["produce", "protein", "dairy", "bakery", "pantry", "frozen", "other"]

# Deep links per supermarket section — Barcelona-specific.
_SUPERMARKETS = {
    "Mercadona Online":  "https://tienda.mercadona.es/",
    "Carrefour Online":  "https://www.carrefour.es/supermercado",
    "BonÀrea":           "https://botiga.bonarea.com/",
}


def aggregate(plan: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """plan -> {category: [{item, total_qty_str, count, meals[]}, ...]} sorted."""
    bucket: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    for day in plan["days"]:
        for m in day["meals"]:
            if m["rung"] != "cook":
                continue
            # find the source meal entry in the library by name to get ingredients
            meal_name = m["name"]
            source = _meal_by_name(meal_name)
            if not source or not source.get("ingredients"):
                continue
            factor = m.get("portion", 1.0)
            for ing in source["ingredients"]:
                key = (ing["item"], ing["category"])
                cat = ing["category"]
                store = bucket[cat].setdefault(ing["item"], {
                    "item": ing["item"],
                    "qty_total_num": 0.0,
                    "qty_unit": "",
                    "qty_raw_parts": [],
                    "count": 0,
                    "meals": set(),
                })
                num, unit = _parse_qty(ing["qty"])
                if num is None:
                    store["qty_raw_parts"].append(ing["qty"])
                else:
                    store["qty_total_num"] += num * factor
                    if unit and not store["qty_unit"]:
                        store["qty_unit"] = unit
                    elif unit and store["qty_unit"] and unit != store["qty_unit"]:
                        # mixed units — keep both as raw
                        store["qty_raw_parts"].append(_fmt_qty(num * factor, unit))
                        store["qty_total_num"] -= num * factor
                store["count"] += 1
                store["meals"].add(meal_name)

    # finalise
    out: dict[str, list[dict[str, Any]]] = {}
    for cat, items in bucket.items():
        rows = []
        for it in items.values():
            parts: list[str] = []
            if it["qty_total_num"] > 0:
                parts.append(_fmt_qty(it["qty_total_num"], it["qty_unit"]))
            parts.extend(it["qty_raw_parts"])
            rows.append({
                "item": it["item"],
                "qty": " + ".join(parts) if parts else "—",
                "count": it["count"],
                "meals": sorted(it["meals"]),
            })
        rows.sort(key=lambda r: (-r["count"], r["item"].lower()))
        out[cat] = rows
    return out


def _meal_by_name(name: str) -> dict[str, Any] | None:
    # Lazy import to avoid circular at module load.
    from ..recommend.meals import MEALS
    for m in MEALS:
        if m["name"] == name:
            return m
    return None


# --- Render ---------------------------------------------------------------- #
def render(plan: dict[str, Any]) -> str:
    agg = aggregate(plan)
    L: list[str] = []
    L.append(f"# Shopping list — week of {plan['start']}")
    L.append("")
    L.append("_Cook-meals only. Order-meals are bought through the delivery app, not the supermarket._")
    L.append("")

    # quick top
    total_lines = sum(len(items) for items in agg.values())
    cooked = sum(1 for d in plan["days"] for m in d["meals"] if m["rung"] == "cook")
    L.append(f"**{total_lines} distinct ingredients · {cooked} cook-meals this week**")
    L.append("")
    L.append("Online order shortcuts:")
    for label, url in _SUPERMARKETS.items():
        L.append(f"- 🛒 [{label}]({url})")
    L.append("")

    for cat in _CATEGORIES_ORDER:
        if cat not in agg:
            continue
        L.append(f"## {cat.capitalize()}")
        L.append("")
        L.append("| ☐ | Item | Qty | Used in |")
        L.append("|---|---|---|---|")
        for row in agg[cat]:
            meals = ", ".join(row["meals"][:3]) + (" …" if len(row["meals"]) > 3 else "")
            L.append(f"| ☐ | {row['item']} | {row['qty']} | _{meals}_ |")
        L.append("")

    # leftover categories not in our preferred order (defensive)
    for cat in sorted(set(agg.keys()) - set(_CATEGORIES_ORDER)):
        L.append(f"## {cat.capitalize()}")
        L.append("")
        for row in agg[cat]:
            L.append(f"- {row['item']} · {row['qty']}")
        L.append("")

    L.append("---")
    L.append("_Quantities are summed across the week, scaled to your daily calorie target. "
             "Adjust portions to taste — these are starting estimates from the meal library._")
    return "\n".join(L) + "\n"


def write(plan: dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(plan))
    return out_path
