"""Deterministic tests for the recommendation engine + weekly-plan builder.

Run:  python -m concierge.tests.test_engine
No pytest dependency — plain asserts, exits non-zero on failure.
"""
from __future__ import annotations

from datetime import date

from ..recommend import compute_targets
from ..orchestrate import build_week, render_markdown

FIXED_TODAY = date(2026, 6, 15)


def _has(items, needle):
    return any(needle.lower() in it.text.lower() for it in items)


def test_katch_mcardle_and_macros():
    ctx = {
        "weight_kg": 70, "lean_mass_kg": 58, "height_cm": 175, "age": 30, "sex": "XY",
        "goals": ["recomposition", "longevity"], "training_days": 3,
        "bloods": {"vitamin_d_ng_ml": 28, "b12_pg_ml": 410, "triglycerides_mg_dl": 95},
        "last_tests": {"lipid_panel": "2025-01-01"},
        "lifestyle": {"nicotine": None, "bp_systolic": None},
        "wearable": None, "has_dna": True,
    }
    t = compute_targets(ctx, today=FIXED_TODAY)
    assert t.bmr_kcal == 1623, t.bmr_kcal                      # 370 + 21.6*58
    assert "Katch" in t.bmr_method
    assert t.activity_factor == 1.55
    assert t.tdee_kcal == 2516, t.tdee_kcal
    assert t.calorie_target_kcal == 2516                        # recomposition => maintenance
    assert t.protein_g_per_kg == 1.8 and t.protein_g == 126
    assert t.fat_g == 56
    assert t.carb_g == 377, t.carb_g                            # (2516-(126*4+56*9))/4
    # vitamin D 28 (<30) => 4000 IU ; B12 410 (<500) => present ; TG 95 => no omega-3
    assert _has(t.supplements, "4000 IU")
    assert _has(t.supplements, "B12")
    assert not _has(t.supplements, "Omega-3")
    assert not _has(t.supplements, "Magnesium")                 # no BP/sleep/stress goal
    assert len(t.training) == 2                                 # 2x resistance + 1x zone-2
    assert _has(t.screenings, "ApoB") and _has(t.screenings, "Lp(a)")
    assert _has(t.screenings, "blood pressure")                 # bp unknown
    assert _has(t.screenings, "lipid")                          # 17 months since last
    assert len(t.behavioral) == 0
    assert _has(t.data_gaps, "Whoop")                           # no wearable


def test_real_profile_branches():
    ctx = {
        "weight_kg": 66.1, "lean_mass_kg": 55.26, "height_cm": 166, "age": 28, "sex": "XY",
        "goals": ["quit_nicotine", "lower_blood_pressure", "recomposition", "longevity"],
        "training_days": 3,
        "bloods": {"vitamin_d_ng_ml": 35, "b12_pg_ml": 390, "ggt_u_l": 35,
                   "ldl_mg_dl": 91.6, "hdl_mg_dl": 88, "triglycerides_mg_dl": 72, "hba1c_pct": 5.2},
        "last_tests": {"lipid_panel": "2025-01-29"},
        "lifestyle": {"nicotine": "snus 10 mg, half-pack/day", "bp_systolic": None},
        "wearable": None, "has_dna": True, "wellness_booking": "manual",
    }
    t = compute_targets(ctx, today=FIXED_TODAY)
    assert t.bmr_kcal == 1564, t.bmr_kcal                       # 370 + 21.6*55.26
    assert t.protein_g == 119                                    # round(1.8*66.1)
    assert _has(t.supplements, "2000 IU")                       # vit D 35 in [30,40)
    assert _has(t.supplements, "Magnesium")                     # lower_blood_pressure goal
    assert _has(t.behavioral, "taper")                          # nicotine present
    assert len(t.screenings) >= 3


def test_lose_fat_path():
    ctx = {"weight_kg": 80, "lean_mass_kg": 60, "goals": ["lose_fat"], "training_days": 5,
           "bloods": {}, "last_tests": {}, "lifestyle": {}, "wearable": {"x": 1}, "has_dna": False}
    t = compute_targets(ctx, today=FIXED_TODAY)
    assert t.protein_g_per_kg == 2.0 and t.protein_g == 160
    assert "cut" in t.calorie_strategy
    assert t.calorie_target_kcal == t.tdee_kcal - 400
    assert t.activity_factor == 1.725                            # 5 days
    assert _has(t.training, "Deload")                            # wearable present
    assert _has(t.data_gaps, "blood panel")                     # no bloods
    assert _has(t.data_gaps, "23andMe")                          # has_dna False


def test_weekly_plan_renders():
    ctx = {
        "weight_kg": 66.1, "lean_mass_kg": 55.26, "goals": ["recomposition", "lower_blood_pressure"],
        "training_days": 3, "bloods": {"vitamin_d_ng_ml": 35}, "last_tests": {},
        "lifestyle": {"nicotine": "snus"}, "wearable": None, "has_dna": True, "city": "Barcelona",
    }
    t = compute_targets(ctx, today=FIXED_TODAY)
    prefs = {"diet": {"pattern": "mediterranean", "allergies": ["lactose"], "meals_per_day": 3},
             "budget": {"weekly_eur": 200}}
    plan = build_week(t, prefs, start=date(2026, 6, 22))
    assert len(plan["days"]) == 7
    assert plan["days"][0]["weekday"] == "Monday"
    # lactose allergy must exclude lactose-tagged meals
    names = [m["name"] for d in plan["days"] for m in d["meals"]]
    assert not any("yogurt" in n.lower() or "cottage" in n.lower() for n in names), names
    md = render_markdown(plan, ctx)
    assert "# Weekly Plan" in md and "Barcelona" in md
    assert "Tests & screening due" in md
    assert "Approve & pay" in md


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
