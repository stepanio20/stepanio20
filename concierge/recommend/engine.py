"""Recommendation engine — Health Graph facts -> deterministic weekly targets.

Milestone M1 of PRODUCT_ARCHITECTURE.md (§7). DETERMINISTIC and auditable: no LLM,
no randomness, no network. Same input -> same output, every time. The LLM (Phase 7
style) is only ever used downstream for *narrative*, never for these safety-relevant
numbers.

Every target carries a `source` and, where relevant, a `why`, so the renderer can
show provenance and the data-gap module can say what would sharpen it.

CLINICAL FRAMING (non-negotiable):
- Output is INFORMATION, not diagnosis or treatment. All text is phrased as
  "below the commonly used threshold of X", "informative for risk discussions
  with a clinician", etc. — never "you have Y" or "you should take Y".
- Supplement doses cited stay within widely-published OTC ranges (e.g. D3
  ≤ 4000 IU/day per EFSA UL; magnesium supplemental ≤ 350 mg/day per IOM UL;
  B12 has no UL but stays at standard 500–1000 µg/day OTC strengths).
- Thresholds match referenced guidelines (ATP III / ACC-AHA / ESC) where
  applicable, with the source cited in the prose.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any, Optional

from ..data import load_venues, venue_for_service, wellness_venue


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
    venue_name: str = ""             # display name from the catalog
    venue_url: str = ""              # one-tap deep link (book/order/info)
    venue_address: str = ""          # short address for the card


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
    medications = [m for m in (ctx.get("medications") or []) if isinstance(m, dict)]
    chronic = [c for c in (ctx.get("chronic_conditions") or []) if isinstance(c, dict)]
    allergies = {a.lower() for a in (ctx.get("allergies") or [])}
    fam_hx = ctx.get("family_history") or {}
    wearable = ctx.get("wearable") or {}

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
    # Doses cited stay within OTC strengths; framing is informational only.
    vit_d = bloods.get("vitamin_d_ng_ml")
    if vit_d is not None:
        if vit_d < 30:
            t.supplements.append(Item("Vitamin D3 ~4000 IU/day (within the EFSA tolerable upper intake of 4000 IU)", "bloods",
                                      f"25-OH-D {vit_d} ng/mL is below the commonly used sufficiency threshold of 30 ng/mL — informative for a clinician discussion.", "self"))
        elif vit_d < 40:
            t.supplements.append(Item("Vitamin D3 ~2000 IU/day", "bloods",
                                      f"25-OH-D {vit_d} ng/mL meets the sufficiency floor of 30 ng/mL; some guidelines target 40–60 ng/mL for optimum.", "self"))
    b12 = bloods.get("b12_pg_ml")
    if b12 is not None and b12 < 500:
        dose = "~1000 µg/day (oral methylcobalamin)" if b12 < 300 else "~500 µg/day or dietary emphasis"
        t.supplements.append(Item(f"Vitamin B12 {dose}", "bloods",
                                  f"B12 {b12} pg/mL is in the lower part of the reference interval; some sources prefer >500 pg/mL.", "self"))
    tg = bloods.get("triglycerides_mg_dl")
    if tg is not None and tg > 150:
        t.supplements.append(Item("EPA/DHA ~2 g/day (combined)", "bloods",
                                  f"Triglycerides {tg} mg/dL are above the ATP III borderline-high threshold of 150 mg/dL. Discuss with a clinician.", "self"))
    if any(g in goals for g in ("lower_blood_pressure", "sleep", "stress")):
        t.supplements.append(Item("Magnesium glycinate ~300 mg in the evening (within the IOM supplemental UL of 350 mg)", "goals",
                                  "May support sleep / blood-pressure / stress goals; evidence quality varies by outcome.", "self"))

    # --- Medication / allergy / chronic-condition interactions ------------ #
    med_names = " ".join((m.get("drug") or "").lower() for m in medications)
    if any(k in med_names for k in ("warfarin", "apixaban", "rivaroxaban", "dabigatran", "acenocoumarol")):
        for sup in t.supplements:
            if "EPA" in sup.text or "Omega" in sup.text:
                sup.why += " Note: high-dose fish oil may interact with anticoagulants — discuss with your clinician before starting."
    if any(k in med_names for k in ("statin", "atorvastatin", "rosuvastatin", "simvastatin", "pravastatin")):
        t.supplements.append(Item("Coenzyme Q10 100–200 mg/day (optional)", "lifestyle",
                                  "Some patients on statins report myalgia improvement with CoQ10. Evidence is mixed; discuss with your clinician.", "self"))
    if "fish" in allergies or "seafood" in allergies:
        t.supplements = [s for s in t.supplements if "EPA" not in s.text]
        t.supplements.append(Item("Algae-based DHA/EPA (instead of fish-oil)", "lifestyle",
                                  "Fish allergy on file — algae oil is the vegan EPA/DHA alternative.", "self"))
    if any(c.get("condition", "").lower() in ("hypothyroidism",) for c in chronic):
        t.notes.append("Hypothyroidism noted — confirm any iodine-rich supplements with your endocrinologist; soy and brassicas can affect levothyroxine absorption when taken together.")
    if any(c.get("condition", "").lower() in ("ckd", "chronic kidney disease") for c in chronic):
        # Re-cap protein for safety; CKD nutrition is patient-specific.
        if t.protein_g_per_kg > 1.0:
            t.protein_g_per_kg = 1.0
            t.protein_g = round(1.0 * weight)
            t.notes.append("CKD on file — protein target reduced to 1.0 g/kg as a safety default. Your nephrologist should set the actual target.")

    # --- Training ----------------------------------------------------------- #
    # Optional recovery-aware tweak: if Whoop reports low average recovery,
    # quietly drop one resistance day.
    rec_avg = wearable.get("recovery_avg") if isinstance(wearable, dict) else None
    eff_training_days = training_days
    if rec_avg is not None and rec_avg < 40 and training_days > 2:
        eff_training_days = training_days - 1

    zone2 = 1 if eff_training_days >= 3 else 0
    resistance = max(0, eff_training_days - zone2)
    if resistance:
        t.training.append(Item(f"{resistance}× resistance (compound-focused)", "goals", rung="self"))
    if zone2:
        t.training.append(Item(f"{zone2}× Zone-2 cardio, 40–50 min", "goals", rung="self"))
    if wearable:
        low_days = wearable.get("recovery_low_days")
        hrv_ms = wearable.get("hrv_rmssd_avg_ms")
        if rec_avg is None:
            t.training.append(Item("Deload any day recovery/HRV trends low two days running", "wearable", rung="self"))
        elif rec_avg < 40:
            t.training.append(Item(f"Recovery averaged {rec_avg}/100 — dropped one session this week", "wearable",
                                   "Recovery scores in the red/yellow band suggest cumulative load.", "self"))
        elif low_days and low_days >= 3:
            t.training.append(Item(f"{low_days} low-recovery days in the last window — keep an eye on sleep + caffeine timing", "wearable", rung="self"))
        else:
            t.training.append(Item(f"Recovery trend OK (avg {rec_avg}/100, HRV {hrv_ms} ms)", "wearable", rung="self"))

    # --- Recovery / therapy ------------------------------------------------- #
    wants_recovery = any(g in goals for g in ("lower_blood_pressure", "stress", "longevity", "sleep"))
    wellness_budget = ctx.get("wellness_eur")
    booking_rung = "book_api" if ctx.get("wellness_booking") in ("mindbody", "fresha", "vagaro") else "book_handoff"
    city = (ctx.get("city") or "").lower()
    if wants_recovery and (wellness_budget is None or wellness_budget > 0):
        sauna = wellness_venue("sauna", city) if city else None
        massage = wellness_venue("massage", city) if city else None
        sauna_item = Item("2× sauna session", "goals",
                          "Recovery + cardiovascular/relaxation benefit.", booking_rung)
        if sauna:
            sauna_item.venue_name = sauna["name"]
            sauna_item.venue_url = sauna.get("booking_url") or sauna["url"]
            sauna_item.venue_address = sauna["address"]
        t.recovery.append(sauna_item)
        massage_item = Item("1× massage", "goals", "Stress + recovery.", booking_rung)
        if massage:
            massage_item.venue_name = massage["name"]
            massage_item.venue_url = massage.get("booking_url") or massage["url"]
            massage_item.venue_address = massage["address"]
        t.recovery.append(massage_item)
    t.recovery.append(Item("Lights-down 60 min before target sleep time", "goals", rung="self"))

    # --- Screenings (Ornament-style; non-blocking) ------------------------- #
    def _attach_lab(item: Item, service_key: str) -> Item:
        v = venue_for_service(service_key, city) if city else None
        if v:
            item.venue_name = v["name"]
            item.venue_url = v.get("booking_url") or v["url"]
            item.venue_address = v["address"]
        return item

    lipid_date = _parse_date(last_tests.get("lipid_panel"))
    if lipid_date is None:
        t.screenings.append(_attach_lab(Item("Lipid panel (LDL/HDL/TG) — no prior on file", "gaps",
                                             "Establish a baseline.", "book_handoff"), "lipid_panel"))
    elif _months_between(lipid_date, today) >= 12:
        m = _months_between(lipid_date, today)
        t.screenings.append(_attach_lab(Item("Repeat lipid panel + liver/metabolic basics", "bloods",
                                             f"Last panel was {m} months ago (>12).", "book_handoff"), "lipid_panel"))
    if "apob_mg_dl" not in bloods:
        t.screenings.append(_attach_lab(Item("Add ApoB to next lipid draw (~€20–30)", "gaps",
                                             "ApoB measures the count of atherogenic lipoprotein particles; "
                                             "informative for long-term cardiovascular risk discussions with a clinician.",
                                             "book_handoff"), "apob"))
    if "lpa_nmol_l" not in bloods:
        t.screenings.append(_attach_lab(Item("Lp(a) — once in a lifetime", "gaps",
                                             "Lp(a) is genetically determined; a single measurement is informative for risk discussions.",
                                             "book_handoff"), "lpa"))
    if lifestyle.get("bp_systolic") is None:
        t.screenings.append(Item("Home blood pressure: 2×/day for 7 days, then average", "gaps",
                                 "BP is currently unknown; a single reading is not a diagnosis.", "self"))

    # --- Behavioral --------------------------------------------------------- #
    nic = lifestyle.get("nicotine")
    if nic:
        t.behavioral.append(Item(f"Nicotine taper this week ({nic}) — step down per cessation plan", "lifestyle",
                                 "Primary modifiable cardiovascular risk factor.", "self"))
    alc = lifestyle.get("alcohol_units_per_week")
    if alc is not None and alc > 14:
        t.behavioral.append(Item("Keep alcohol ≤14 units/week (UK/EU low-risk threshold)", "lifestyle", rung="self"))

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
