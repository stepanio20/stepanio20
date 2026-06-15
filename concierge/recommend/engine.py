"""Recommendation engine — Health Graph facts -> deterministic weekly targets.

Milestone M1 of PRODUCT_ARCHITECTURE.md (§7). DETERMINISTIC and auditable: no LLM,
no randomness, no network. Same input -> same output, every time. The LLM (Phase 7
style) is only ever used downstream for *narrative*, never for these safety-relevant
numbers.

Every target carries a `source` and, where relevant, a `why`, so the renderer can
show provenance and the data-gap module can say what would sharpen it.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any, Optional


# --------------------------------------------------------------------------- #
# Output types
# --------------------------------------------------------------------------- #
@dataclass
class Item:
    """A single recommendation line with provenance."""
    text: str
    source: str = "profile"          # profile | bloods | wearable | goals | lifestyle | gaps
    why: str = ""
    rung: str = ""                   # cook | order | book_api | book_handoff | self | "" (n/a)


@dataclass
class Targets:
    # energy / macros
    bmr_kcal: int = 0
    bmr_method: str = ""
    activity_factor: float = 0.0
    tdee_kcal: int = 0
    calorie_target_kcal: int = 0
    calorie_strategy: str = ""
    protein_g: int = 0
    fat_g: int = 0
    carb_g: int = 0
    protein_g_per_kg: float = 0.0
    # plans (lists of Item)
    supplements: list[Item] = field(default_factory=list)
    training: list[Item] = field(default_factory=list)
    recovery: list[Item] = field(default_factory=list)
    screenings: list[Item] = field(default_factory=list)   # the Ornament-style, non-blocking module
    behavioral: list[Item] = field(default_factory=list)
    data_gaps: list[Item] = field(default_factory=list)     # "add X to sharpen this"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _months_between(earlier: date, later: date) -> int:
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _activity_factor(training_days: int) -> float:
    if training_days <= 0:
        return 1.2
    if training_days <= 2:
        return 1.375
    if training_days <= 4:
        return 1.55
    if training_days <= 6:
        return 1.725
    return 1.9


# --------------------------------------------------------------------------- #
# Core
# --------------------------------------------------------------------------- #
def compute_targets(ctx: dict[str, Any], today: Optional[date] = None) -> Targets:
    """ctx is the assembled context (see make_weekly_plan.assemble_context).

    Required: weight_kg. Optional but used: lean_mass_kg, height_cm, age, sex,
    body_fat_pct, goals[], training_days, bloods{}, last_tests{}, lifestyle{}.
    """
    today = today or date.today()
    t = Targets()

    weight = float(ctx["weight_kg"])
    lean = ctx.get("lean_mass_kg")
    height = ctx.get("height_cm")
    age = ctx.get("age")
    sex = ctx.get("sex", "XY")
    goals = [g.lower() for g in ctx.get("goals", [])]
    training_days = int(ctx.get("training_days", 3))
    bloods = ctx.get("bloods", {}) or {}
    last_tests = ctx.get("last_tests", {}) or {}
    lifestyle = ctx.get("lifestyle", {}) or {}

    # --- BMR ---------------------------------------------------------------- #
    if lean:
        # Katch-McArdle (uses lean mass; age-independent — the most accurate when
        # body composition is known, e.g. from a smart scale / DEXA).
        t.bmr_kcal = round(370 + 21.6 * float(lean))
        t.bmr_method = "Katch-McArdle (lean mass)"
    elif height and age:
        # Mifflin-St Jeor fallback.
        s = 5 if sex == "XY" else -161
        t.bmr_kcal = round(10 * weight + 6.25 * float(height) - 5 * float(age) + s)
        t.bmr_method = "Mifflin-St Jeor"
    else:
        t.bmr_kcal = round(22 * weight)  # crude last resort
        t.bmr_method = "weight-only estimate"

    # --- TDEE + calorie strategy ------------------------------------------- #
    t.activity_factor = _activity_factor(training_days)
    t.tdee_kcal = round(t.bmr_kcal * t.activity_factor)

    if "lose_fat" in goals:
        adj, t.calorie_strategy = -400, "cut (~0.4 kg/wk fat loss)"
        t.protein_g_per_kg = 2.0
    elif "gain_muscle" in goals:
        adj, t.calorie_strategy = +250, "lean bulk"
        t.protein_g_per_kg = 1.8
    elif "recomposition" in goals:
        adj, t.calorie_strategy = 0, "maintenance (recomposition, high protein)"
        t.protein_g_per_kg = 1.8
    else:
        adj, t.calorie_strategy = 0, "maintenance"
        t.protein_g_per_kg = 1.6

    t.calorie_target_kcal = t.tdee_kcal + adj
    t.protein_g = round(t.protein_g_per_kg * weight)
    t.fat_g = round(0.8 * weight)
    carb_kcal = t.calorie_target_kcal - (t.protein_g * 4 + t.fat_g * 9)
    t.carb_g = max(0, round(carb_kcal / 4))

    # --- Supplements (from bloods) ----------------------------------------- #
    vit_d = bloods.get("vitamin_d_ng_ml")
    if vit_d is not None:
        if vit_d < 30:
            t.supplements.append(Item("Vitamin D3 4000 IU/day", "bloods",
                                      f"25-OH-D {vit_d} ng/mL is below sufficiency (30).", "self"))
        elif vit_d < 40:
            t.supplements.append(Item("Vitamin D3 2000 IU/day", "bloods",
                                      f"25-OH-D {vit_d} ng/mL is adequate but below the 40–60 optimum.", "self"))
    b12 = bloods.get("b12_pg_ml")
    if b12 is not None and b12 < 500:
        dose = "1000 µg/day" if b12 < 300 else "500 µg 2×/week (or prioritise dietary B12)"
        t.supplements.append(Item(f"Vitamin B12 {dose}", "bloods",
                                  f"B12 {b12} pg/mL is in the lower part of range (optimum >500).", "self"))
    tg = bloods.get("triglycerides_mg_dl")
    if tg is not None and tg > 150:
        t.supplements.append(Item("Omega-3 (EPA/DHA) 2 g/day", "bloods",
                                  f"Triglycerides {tg} mg/dL are elevated.", "self"))
    if any(g in goals for g in ("lower_blood_pressure", "sleep", "stress")):
        t.supplements.append(Item("Magnesium glycinate ~300 mg, evening", "goals",
                                  "Supports sleep / blood-pressure / stress goals.", "self"))

    # --- Training ----------------------------------------------------------- #
    zone2 = 1 if training_days >= 3 else 0
    resistance = max(0, training_days - zone2)
    if resistance:
        t.training.append(Item(f"{resistance}× resistance (compound-focused)", "goals", rung="self"))
    if zone2:
        t.training.append(Item(f"{zone2}× Zone-2 cardio, 40–50 min", "goals", rung="self"))
    if ctx.get("wearable"):
        t.training.append(Item("Deload any day recovery/HRV trends low two days running", "wearable", rung="self"))

    # --- Recovery / therapy ------------------------------------------------- #
    wants_recovery = any(g in goals for g in ("lower_blood_pressure", "stress", "longevity", "sleep"))
    wellness_budget = ctx.get("wellness_eur")
    booking_rung = "book_api" if ctx.get("wellness_booking") in ("mindbody", "fresha", "vagaro") else "book_handoff"
    if wants_recovery and (wellness_budget is None or wellness_budget > 0):
        t.recovery.append(Item("2× sauna session", "goals",
                               "Recovery + cardiovascular/relaxation benefit.", booking_rung))
        t.recovery.append(Item("1× massage", "goals", "Stress + recovery.", booking_rung))
    t.recovery.append(Item("Lights-down 60 min before target sleep time", "goals", rung="self"))

    # --- Screenings (Ornament-style; non-blocking) ------------------------- #
    lipid_date = _parse_date(last_tests.get("lipid_panel"))
    if lipid_date is None:
        t.screenings.append(Item("Lipid panel (LDL/HDL/TG) — no prior on file", "gaps",
                                 "Establish a baseline.", "book_handoff"))
    elif _months_between(lipid_date, today) >= 12:
        m = _months_between(lipid_date, today)
        t.screenings.append(Item("Repeat lipid panel + liver/metabolic basics", "bloods",
                                 f"Last panel was {m} months ago (>12).", "book_handoff"))
    if "apob_mg_dl" not in bloods:
        t.screenings.append(Item("Add ApoB to next lipid draw (~€30)", "gaps",
                                 "ApoB is the better long-term cardiovascular risk metric than calculated LDL.", "book_handoff"))
    if "lpa_nmol_l" not in bloods:
        t.screenings.append(Item("Lp(a) — once in a lifetime", "gaps",
                                 "Genetically fixed; a single measurement settles a major risk modifier.", "book_handoff"))
    if lifestyle.get("bp_systolic") is None:
        t.screenings.append(Item("Home blood pressure: 2×/day for 7 days, then average", "gaps",
                                 "BP is currently unknown; one reading is not a diagnosis.", "self"))

    # --- Behavioral --------------------------------------------------------- #
    nic = lifestyle.get("nicotine")
    if nic:
        t.behavioral.append(Item(f"Nicotine taper this week ({nic}) — step down per cessation plan", "lifestyle",
                                 "Primary modifiable cardiovascular risk factor.", "self"))
    alc = lifestyle.get("alcohol_units_per_week")
    if alc is not None and alc > 7:
        t.behavioral.append(Item("Keep alcohol ≤7 units/week", "lifestyle", rung="self"))

    # --- Data gaps (what would sharpen the plan) --------------------------- #
    if not ctx.get("wearable"):
        t.data_gaps.append(Item("Connect Whoop/Apple Health", "gaps",
                                "Unlocks recovery-aware training + sleep scheduling."))
    if not bloods:
        t.data_gaps.append(Item("Upload a recent blood panel", "gaps",
                                "Turns generic targets into a personalised supplement + screening plan."))
    if not ctx.get("has_dna"):
        t.data_gaps.append(Item("Upload your 23andMe/Ancestry raw file", "gaps",
                                "Unlocks PGx (drug response) + polygenic risk percentiles."))

    return t
