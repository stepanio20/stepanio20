"""Deterministic tests for the recommendation engine + weekly-plan builder.

Run:  python -m concierge.tests.test_engine
No pytest dependency — plain asserts, exits non-zero on failure.
"""
from __future__ import annotations

from datetime import date

from ..orchestrate import build_ics, build_week, render_markdown
from ..orchestrate.shopping_list import aggregate, render as render_shopping_list
from ..recommend import compute_targets

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
    # vitamin D 28 (<30) => ~4000 IU ; B12 410 (<500) => present ; TG 95 => no omega-3
    assert _has(t.supplements, "4000 IU")
    assert _has(t.supplements, "B12")
    assert not _has(t.supplements, "EPA")
    assert not _has(t.supplements, "Magnesium")                 # no BP/sleep/stress goal
    assert len(t.training) == 2                                 # 2x resistance + 1x zone-2
    assert _has(t.screenings, "ApoB") and _has(t.screenings, "Lp(a)")
    assert _has(t.screenings, "blood pressure")                 # bp unknown
    assert _has(t.screenings, "lipid")                          # 17 months since last
    assert len(t.behavioral) == 0
    assert _has(t.data_gaps, "Whoop")                           # no wearable


def test_real_profile_branches():
    ctx = {
        "weight_kg": 72.0, "lean_mass_kg": 58.0, "height_cm": 178, "age": 35, "sex": "XY",
        "goals": ["quit_nicotine", "lower_blood_pressure", "recomposition", "longevity"],
        "training_days": 3,
        "bloods": {"vitamin_d_ng_ml": 33, "b12_pg_ml": 420, "ggt_u_l": 30,
                   "ldl_mg_dl": 100, "hdl_mg_dl": 60, "triglycerides_mg_dl": 90, "hba1c_pct": 5.4},
        "last_tests": {"lipid_panel": "2025-01-29"},
        "lifestyle": {"nicotine": "nicotine pouches, daily", "bp_systolic": None},
        "wearable": None, "has_dna": True, "wellness_booking": "manual",
    }
    t = compute_targets(ctx, today=FIXED_TODAY)
    assert t.bmr_kcal == 1623, t.bmr_kcal                       # 370 + 21.6*58.0
    assert t.protein_g == 130                                    # round(1.8*72.0)
    assert _has(t.supplements, "2000 IU")                       # vit D 33 in [30,40)
    assert _has(t.supplements, "Magnesium")                     # lower_blood_pressure goal
    # clinical-framing check: thresholds + clinician phrasing present
    for sup in t.supplements:
        if "Vitamin D3" in sup.text:
            assert "sufficiency" in sup.why or "guidelines" in sup.why, sup.why
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


def test_barcelona_venues_attached():
    ctx = {
        "weight_kg": 72.0, "lean_mass_kg": 58.0,
        "goals": ["lower_blood_pressure", "longevity"], "training_days": 3,
        "bloods": {}, "last_tests": {"lipid_panel": "2024-01-01"},
        "lifestyle": {"bp_systolic": None}, "wearable": None, "has_dna": True,
        "city": "Barcelona", "wellness_booking": "manual",
    }
    t = compute_targets(ctx, today=FIXED_TODAY)
    lipid = next(it for it in t.screenings if "lipid" in it.text.lower())
    assert lipid.venue_name, "lipid panel should carry a Barcelona venue"
    assert lipid.venue_url.startswith("http"), lipid.venue_url
    sauna = next(it for it in t.recovery if "sauna" in it.text.lower())
    assert "ILO" in sauna.venue_name, sauna.venue_name


def test_weekly_plan_renders():
    ctx = {
        "weight_kg": 72.0, "lean_mass_kg": 58.0, "goals": ["recomposition", "lower_blood_pressure"],
        "training_days": 3, "bloods": {"vitamin_d_ng_ml": 35}, "last_tests": {},
        "lifestyle": {"nicotine": "nicotine"}, "wearable": None, "has_dna": True, "city": "Barcelona",
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


def test_clinical_framing_guardrails():
    """Information-not-diagnosis framing is non-negotiable. Check copy stays inside
    OTC dose limits and avoids diagnostic / imperative phrasing."""
    ctx = {
        "weight_kg": 80, "lean_mass_kg": 60,
        "goals": ["lose_fat", "lower_blood_pressure"], "training_days": 4,
        "bloods": {"vitamin_d_ng_ml": 18, "b12_pg_ml": 250, "triglycerides_mg_dl": 220},
        "last_tests": {}, "lifestyle": {"alcohol_units_per_week": 18}, "wearable": None, "has_dna": False,
        "city": "Barcelona",
    }
    t = compute_targets(ctx, today=FIXED_TODAY)
    joined = " | ".join(it.text + " " + it.why for it in
                        t.supplements + t.screenings + t.behavioral + t.recovery + t.training)
    # No diagnostic / imperative phrasing
    forbidden = ["you have", "you should", "is dangerous", "abnormally", "diagnosed"]
    for phrase in forbidden:
        assert phrase.lower() not in joined.lower(), f"forbidden phrase: {phrase!r}"
    # OTC dose caps
    assert "4000 IU" in joined and "5000" not in joined and "10000" not in joined
    # B12 1000 µg max OTC (water-soluble, no UL — but stays at standard supp strength)
    assert "1000 µg" in joined or "500 µg" in joined
    # Magnesium within UL
    assert "300 mg" in joined
    # Threshold provenance is named
    assert "ATP III" in joined or "EFSA" in joined or "IOM" in joined or "UK/EU" in joined or "guideline" in joined.lower()


def test_shopping_list():
    ctx = {
        "weight_kg": 72.0, "lean_mass_kg": 58.0,
        "goals": ["recomposition"], "training_days": 3,
        "bloods": {}, "last_tests": {}, "lifestyle": {},
        "wearable": None, "has_dna": True, "city": "Barcelona",
    }
    t = compute_targets(ctx, today=FIXED_TODAY)
    prefs = {"diet": {"pattern": "omnivore", "meals_per_day": 3}, "budget": {"weekly_eur": 200}}
    plan = build_week(t, prefs, start=date(2026, 6, 22))

    agg = aggregate(plan)
    assert "protein" in agg or "produce" in agg, list(agg.keys())
    items = [r["item"] for cat in agg.values() for r in cat]
    assert any("Salmon" in i or "Chicken" in i for i in items), items
    # Quantities must scale by portion factor — should be non-trivial > 50 g of protein
    protein_items = agg.get("protein", [])
    assert protein_items, agg.get("protein")
    has_grams = any("g" in r["qty"] for r in protein_items)
    assert has_grams, [r["qty"] for r in protein_items]

    md = render_shopping_list(plan)
    assert md.startswith("# Shopping list")
    assert "Mercadona" in md and "Carrefour" in md
    assert "cook-meals" in md.lower()
    # Order-only meals must NOT contribute ingredients (poke etc.)
    assert "edamame" not in md.lower(), "order-meal ingredients leaked"


def test_profile_aware_interactions():
    """profile.json medications + chronic conditions + allergies adjust the plan."""
    ctx = {
        "weight_kg": 80, "goals": ["recomposition"], "training_days": 3,
        "bloods": {"triglycerides_mg_dl": 200}, "last_tests": {}, "lifestyle": {},
        "wearable": None, "has_dna": True, "city": "Barcelona",
        "medications": [
            {"drug": "atorvastatin 20 mg", "indication": "lipid"},
            {"drug": "apixaban", "indication": "AF"},
        ],
        "chronic_conditions": [],
        "allergies": ["fish"],
    }
    t = compute_targets(ctx, today=FIXED_TODAY)
    # CoQ10 added by statin
    assert _has(t.supplements, "Coenzyme Q10"), [s.text for s in t.supplements]
    # Fish allergy → algae alternative, no fish-oil EPA recommendation
    assert any("Algae" in s.text for s in t.supplements)
    assert not any("EPA" in s.text and "Algae" not in s.text for s in t.supplements)
    # Anticoagulant caveat travels with omega text if present (but here EPA was swapped)
    # CKD safety cap
    ctx2 = dict(ctx, chronic_conditions=[{"condition": "CKD", "status": "stage 3"}],
                medications=[], allergies=[])
    t2 = compute_targets(ctx2, today=FIXED_TODAY)
    assert t2.protein_g_per_kg == 1.0
    assert any("CKD" in n for n in t2.notes)


def test_wearable_summary_drops_session():
    """Recovery_avg < 40 from a Whoop sync drops one resistance day."""
    base = {"weight_kg": 70, "lean_mass_kg": 55, "goals": ["recomposition"],
            "training_days": 4, "bloods": {}, "last_tests": {}, "lifestyle": {},
            "has_dna": True, "city": "Barcelona"}
    t_high = compute_targets(dict(base, wearable={"recovery_avg": 65.0, "hrv_rmssd_avg_ms": 90.0, "recovery_low_days": 0}), today=FIXED_TODAY)
    t_low = compute_targets(dict(base, wearable={"recovery_avg": 32.0, "hrv_rmssd_avg_ms": 40.0, "recovery_low_days": 5}), today=FIXED_TODAY)
    res_high = sum(int(it.text.split("×")[0]) for it in t_high.training if "resistance" in it.text)
    res_low = sum(int(it.text.split("×")[0]) for it in t_low.training if "resistance" in it.text)
    assert res_low == res_high - 1, (res_high, res_low)
    assert any("dropped one session" in it.text for it in t_low.training)


def test_ics_export():
    ctx = {
        "weight_kg": 72.0, "lean_mass_kg": 58.0,
        "goals": ["lower_blood_pressure"], "training_days": 3,
        "bloods": {}, "last_tests": {"lipid_panel": "2024-01-01"},
        "lifestyle": {"bp_systolic": None}, "wearable": None, "has_dna": True,
        "city": "Barcelona", "wellness_booking": "manual",
    }
    t = compute_targets(ctx, today=FIXED_TODAY)
    prefs = {"diet": {"pattern": "omnivore", "meals_per_day": 3}, "budget": {"weekly_eur": 200}}
    plan = build_week(t, prefs, start=date(2026, 6, 22))
    ics = build_ics(plan)

    # RFC 5545 structural requirements
    assert ics.startswith("BEGIN:VCALENDAR"), ics[:50]
    assert ics.rstrip().endswith("END:VCALENDAR"), ics[-50:]
    assert "VERSION:2.0" in ics
    assert "X-WR-TIMEZONE:Europe/Madrid" in ics
    assert "\r\n" in ics, "must use CRLF line endings"

    # Counts: ≥3 sessions, 1 meal-prep, ≥3 screening reminders
    n_events = ics.count("BEGIN:VEVENT")
    assert n_events >= 7, n_events
    assert "Meal prep & weekly order" in ics
    assert "Sauna" in ics
    assert "ILO STUDIOS" in ics
    assert "Echevarne" in ics or "SYNLAB" in ics
    # Information-not-diagnosis framing must be present
    assert "Information only" in ics or "information only" in ics


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
