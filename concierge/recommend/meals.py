"""Small curated meal library + deterministic daily selection.

Mediterranean-leaning, macro-tagged. Each meal carries dietary tags so the
preference filter (allergies / pattern / dislikes) can exclude it, and a `rung`
(cook | order) for the action layer. Selection is deterministic: it rotates the
filtered library by day index and scales the day to the calorie target, so the
same inputs always produce the same week.

This is intentionally a *small, honest* library, not a nutrition database — enough
to make the weekly plan concrete. The productised version swaps this for a real
food DB + the LLM picking dishes (PRODUCT_ARCHITECTURE.md §8).
"""
from __future__ import annotations

from typing import Any

# tags: lactose, gluten, fish, meat, egg, vegetarian, vegan, nuts
# ingredients: short shopping-list lines (item, qty, category).
#   categories: produce | protein | dairy | pantry | bakery | frozen
MEALS: list[dict[str, Any]] = [
    # ---- breakfasts ---------------------------------------------------------
    {"name": "Greek yogurt, berries, walnuts, honey", "slot": "breakfast",
     "kcal": 420, "p": 28, "c": 38, "f": 18, "tags": ["lactose", "nuts", "vegetarian"], "rung": "cook",
     "ingredients": [
         {"item": "Greek yogurt (0% fat)", "qty": "200 g", "category": "dairy"},
         {"item": "Mixed berries", "qty": "100 g", "category": "produce"},
         {"item": "Walnuts", "qty": "20 g", "category": "pantry"},
         {"item": "Honey", "qty": "10 g", "category": "pantry"}]},
    {"name": "3-egg veggie omelette + sourdough", "slot": "breakfast",
     "kcal": 450, "p": 27, "c": 32, "f": 22, "tags": ["egg", "gluten", "vegetarian"], "rung": "cook",
     "ingredients": [
         {"item": "Eggs", "qty": "3", "category": "dairy"},
         {"item": "Spinach", "qty": "50 g", "category": "produce"},
         {"item": "Tomato", "qty": "1", "category": "produce"},
         {"item": "Sourdough", "qty": "60 g", "category": "bakery"},
         {"item": "Olive oil", "qty": "5 g", "category": "pantry"}]},
    {"name": "Oats, whey, banana, peanut butter", "slot": "breakfast",
     "kcal": 520, "p": 38, "c": 60, "f": 16, "tags": ["lactose", "nuts", "gluten", "vegetarian"], "rung": "cook",
     "ingredients": [
         {"item": "Rolled oats", "qty": "70 g", "category": "pantry"},
         {"item": "Whey protein powder", "qty": "30 g", "category": "pantry"},
         {"item": "Banana", "qty": "1", "category": "produce"},
         {"item": "Peanut butter", "qty": "15 g", "category": "pantry"}]},
    {"name": "Smoked salmon, avocado, rye toast", "slot": "breakfast",
     "kcal": 470, "p": 26, "c": 34, "f": 24, "tags": ["fish", "gluten"], "rung": "cook",
     "ingredients": [
         {"item": "Smoked salmon", "qty": "80 g", "category": "protein"},
         {"item": "Avocado", "qty": "½", "category": "produce"},
         {"item": "Rye bread", "qty": "60 g", "category": "bakery"}]},
    {"name": "Tofu scramble, spinach, tomato, rye", "slot": "breakfast",
     "kcal": 410, "p": 26, "c": 36, "f": 18, "tags": ["gluten", "vegan", "vegetarian"], "rung": "cook",
     "ingredients": [
         {"item": "Firm tofu", "qty": "150 g", "category": "protein"},
         {"item": "Spinach", "qty": "60 g", "category": "produce"},
         {"item": "Tomato", "qty": "1", "category": "produce"},
         {"item": "Rye bread", "qty": "60 g", "category": "bakery"},
         {"item": "Turmeric", "qty": "1 tsp", "category": "pantry"}]},
    # ---- mains (lunch / dinner) --------------------------------------------
    {"name": "Grilled chicken, quinoa, roasted veg", "slot": "main",
     "kcal": 620, "p": 50, "c": 55, "f": 18, "tags": ["meat"], "rung": "cook",
     "ingredients": [
         {"item": "Chicken breast", "qty": "180 g", "category": "protein"},
         {"item": "Quinoa", "qty": "70 g (dry)", "category": "pantry"},
         {"item": "Mixed vegetables (zucchini, pepper)", "qty": "200 g", "category": "produce"},
         {"item": "Olive oil", "qty": "10 g", "category": "pantry"}]},
    {"name": "Baked salmon, sweet potato, broccoli", "slot": "main",
     "kcal": 640, "p": 42, "c": 50, "f": 26, "tags": ["fish"], "rung": "cook",
     "ingredients": [
         {"item": "Salmon fillet", "qty": "150 g", "category": "protein"},
         {"item": "Sweet potato", "qty": "200 g", "category": "produce"},
         {"item": "Broccoli", "qty": "200 g", "category": "produce"},
         {"item": "Olive oil", "qty": "10 g", "category": "pantry"}]},
    {"name": "Lentil + chickpea stew, brown rice", "slot": "main",
     "kcal": 580, "p": 28, "c": 86, "f": 12, "tags": ["vegan", "vegetarian"], "rung": "cook",
     "ingredients": [
         {"item": "Lentils (dry)", "qty": "50 g", "category": "pantry"},
         {"item": "Chickpeas (canned)", "qty": "150 g drained", "category": "pantry"},
         {"item": "Brown rice (dry)", "qty": "70 g", "category": "pantry"},
         {"item": "Onion", "qty": "1", "category": "produce"},
         {"item": "Tomato sauce", "qty": "150 g", "category": "pantry"}]},
    {"name": "Lean beef, bulgur, mixed salad", "slot": "main",
     "kcal": 660, "p": 48, "c": 52, "f": 24, "tags": ["meat", "gluten"], "rung": "cook",
     "ingredients": [
         {"item": "Lean beef (sirloin / lomo)", "qty": "180 g", "category": "protein"},
         {"item": "Bulgur (dry)", "qty": "70 g", "category": "pantry"},
         {"item": "Mixed salad greens", "qty": "100 g", "category": "produce"},
         {"item": "Cucumber", "qty": "1", "category": "produce"}]},
    {"name": "Tuna + white-bean salad, olive oil", "slot": "main",
     "kcal": 540, "p": 44, "c": 40, "f": 20, "tags": ["fish"], "rung": "cook",
     "ingredients": [
         {"item": "Tuna (canned in water)", "qty": "150 g", "category": "pantry"},
         {"item": "White beans (canned)", "qty": "200 g drained", "category": "pantry"},
         {"item": "Cherry tomatoes", "qty": "150 g", "category": "produce"},
         {"item": "Red onion", "qty": "½", "category": "produce"},
         {"item": "Olive oil", "qty": "15 g", "category": "pantry"}]},
    {"name": "Turkey + veg stir-fry, jasmine rice", "slot": "main",
     "kcal": 600, "p": 46, "c": 64, "f": 14, "tags": ["meat"], "rung": "cook",
     "ingredients": [
         {"item": "Turkey breast", "qty": "180 g", "category": "protein"},
         {"item": "Jasmine rice (dry)", "qty": "80 g", "category": "pantry"},
         {"item": "Pak choi / mixed stir-fry veg", "qty": "200 g", "category": "produce"},
         {"item": "Soy sauce", "qty": "15 g", "category": "pantry"},
         {"item": "Ginger", "qty": "10 g", "category": "produce"}]},
    {"name": "Poke bowl (salmon, rice, edamame)", "slot": "main",
     "kcal": 610, "p": 38, "c": 66, "f": 20, "tags": ["fish"], "rung": "order", "ingredients": []},
    {"name": "Falafel + hummus bowl, salad", "slot": "main",
     "kcal": 560, "p": 22, "c": 72, "f": 22, "tags": ["vegan", "vegetarian", "gluten"], "rung": "order", "ingredients": []},
    {"name": "Grilled prawn + veg paella (small)", "slot": "main",
     "kcal": 590, "p": 34, "c": 70, "f": 16, "tags": ["fish"], "rung": "order", "ingredients": []},
    # ---- snacks -------------------------------------------------------------
    {"name": "Cottage cheese + almonds", "slot": "snack",
     "kcal": 260, "p": 26, "c": 10, "f": 14, "tags": ["lactose", "nuts", "vegetarian"], "rung": "cook",
     "ingredients": [
         {"item": "Cottage cheese", "qty": "150 g", "category": "dairy"},
         {"item": "Almonds", "qty": "20 g", "category": "pantry"}]},
    {"name": "Apple + 30 g almonds", "slot": "snack",
     "kcal": 250, "p": 7, "c": 28, "f": 15, "tags": ["nuts", "vegan", "vegetarian"], "rung": "cook",
     "ingredients": [
         {"item": "Apple", "qty": "1", "category": "produce"},
         {"item": "Almonds", "qty": "30 g", "category": "pantry"}]},
]

_PATTERN_REQUIRES = {
    "vegan": lambda m: "vegan" in m["tags"],
    "vegetarian": lambda m: "vegetarian" in m["tags"] or "vegan" in m["tags"],
    "pescatarian": lambda m: "meat" not in m["tags"],
}


def filter_meals(prefs: dict[str, Any]) -> list[dict[str, Any]]:
    pattern = (prefs.get("pattern") or "omnivore").lower()
    allergies = {a.lower() for a in prefs.get("allergies", [])}
    dislikes = {d.lower() for d in prefs.get("dislikes", [])}
    req = _PATTERN_REQUIRES.get(pattern)

    out = []
    for m in MEALS:
        tags = set(m["tags"])
        if allergies & tags:                       # exclude allergens
            continue
        if any(d in m["name"].lower() for d in dislikes):
            continue
        if req and not req(m):
            continue
        out.append(m)
    return out


def _scaled(meal: dict[str, Any], factor: float) -> dict[str, Any]:
    return {
        "name": meal["name"],
        "slot": meal["slot"],
        "rung": meal["rung"],
        "kcal": round(meal["kcal"] * factor),
        "p": round(meal["p"] * factor),
        "c": round(meal["c"] * factor),
        "f": round(meal["f"] * factor),
        "portion": round(factor, 2),
    }


def select_day(library: list[dict[str, Any]], targets, day_index: int) -> dict[str, Any]:
    """Pick a breakfast + N mains for one day, scaled to hit the calorie target.

    Deterministic: rotation is purely a function of day_index.
    """
    breakfasts = [m for m in library if m["slot"] == "breakfast"] or library
    mains = [m for m in library if m["slot"] == "main"] or library
    meals_per_day = max(1, getattr(targets, "_meals_per_day", 3))
    n_mains = max(1, meals_per_day - 1)

    chosen = [breakfasts[day_index % len(breakfasts)]]
    for k in range(n_mains):
        chosen.append(mains[(day_index + k) % len(mains)])

    base_kcal = sum(m["kcal"] for m in chosen)
    factor = targets.calorie_target_kcal / base_kcal if base_kcal else 1.0
    # keep portions sane
    factor = max(0.6, min(1.6, factor))
    scaled = [_scaled(m, factor) for m in chosen]

    totals = {
        "kcal": sum(m["kcal"] for m in scaled),
        "p": sum(m["p"] for m in scaled),
        "c": sum(m["c"] for m in scaled),
        "f": sum(m["f"] for m in scaled),
    }
    return {"meals": scaled, "totals": totals,
            "protein_ok": totals["p"] >= targets.protein_g - 10}
