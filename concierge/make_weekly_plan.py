"""CLI: assemble context for a user, compute targets, build the week, write the plan.

    python -m concierge.make_weekly_plan --user me
    python -m concierge.make_weekly_plan --user me --start 2026-06-22 --out -

Reads (all relative to repo root):
  users/<user>/concierge.json                 preferences + integrations (tracked)
  users/<user>/profile.json                    optional demographics (tracked template)
  users/<user>/bundles/health_graph.json       real facts if present (gitignored)
  concierge/recommend/health_graph.sample.json fallback so it always runs

Writes:
  users/<user>/reports/weekly_plan.md          (gitignored — contains personal facts)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from .recommend import compute_targets
from .orchestrate import build_week, render_markdown, write_ics, write_shopping_list

ROOT = Path(__file__).resolve().parent.parent


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _next_monday(d: date) -> date:
    return d if d.weekday() == 0 else d + timedelta(days=(7 - d.weekday()))


def assemble_context(user: str) -> tuple[dict, dict]:
    """Return (ctx_for_engine, prefs_for_orchestrator)."""
    udir = ROOT / "users" / user
    concierge = _load_json(udir / "concierge.json")
    profile = _load_json(udir / "profile.json")

    graph_path = udir / "bundles" / "health_graph.json"
    if graph_path.exists():
        graph = _load_json(graph_path)
        graph_source = str(graph_path.relative_to(ROOT))
    else:
        graph = _load_json(ROOT / "concierge" / "recommend" / "health_graph.sample.json")
        graph_source = "concierge/recommend/health_graph.sample.json (SAMPLE — add your real graph)"

    diet = concierge.get("diet", {})
    sched = concierge.get("schedule", {})
    budget = concierge.get("budget", {})
    integ = concierge.get("integrations", {})

    ctx = {
        "weight_kg": graph.get("weight_kg") or profile.get("anthropometric", {}).get("weight_kg"),
        "height_cm": graph.get("height_cm") or profile.get("anthropometric", {}).get("height_cm"),
        "age": graph.get("age"),
        "sex": graph.get("sex") or (profile.get("sex") if profile.get("sex") != "TBD" else "XY"),
        "lean_mass_kg": graph.get("lean_mass_kg"),
        "body_fat_pct": graph.get("body_fat_pct"),
        "goals": concierge.get("goals", []),
        "training_days": sched.get("training_days_per_week", 3),
        "bloods": graph.get("bloods", {}),
        "last_tests": graph.get("last_tests", {}),
        "lifestyle": graph.get("lifestyle", {}),
        "wearable": graph.get("wearable"),
        "wellness_eur": budget.get("wellness_eur"),
        "wellness_booking": integ.get("wellness_booking"),
        "has_dna": integ.get("dna_vendor", "none") != "none",
        "city": concierge.get("locale", {}).get("city", ""),
        "_graph_source": graph_source,
    }
    prefs = {"diet": diet, "schedule": sched, "budget": budget}
    return ctx, prefs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate a weekly plan from a user's Health Graph.")
    ap.add_argument("--user", default="me")
    ap.add_argument("--start", help="YYYY-MM-DD (default: next Monday)")
    ap.add_argument("--out", help="output path, or '-' for stdout (default: users/<user>/reports/weekly_plan.md)")
    args = ap.parse_args(argv)

    ctx, prefs = assemble_context(args.user)
    if not ctx.get("weight_kg"):
        print("ERROR: no weight_kg in health graph or profile — cannot compute targets.", file=sys.stderr)
        return 2

    start = date.fromisoformat(args.start) if args.start else _next_monday(date.today())
    targets = compute_targets(ctx)
    plan = build_week(targets, prefs, start)
    md = render_markdown(plan, ctx)

    if args.out == "-":
        sys.stdout.write(md)
    else:
        out = Path(args.out) if args.out else ROOT / "users" / args.user / "reports" / "weekly_plan.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md)
        ics_path = ROOT / "users" / args.user / "exports" / f"week_{start.isoformat()}.ics"
        write_ics(plan, ics_path)
        shop_path = ROOT / "users" / args.user / "reports" / "shopping_list.md"
        write_shopping_list(plan, shop_path)
        print(f"Wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
        print(f"Wrote {shop_path.relative_to(ROOT)} (grouped by category, with Mercadona/Carrefour links)")
        print(f"Wrote {ics_path.relative_to(ROOT)} (drag-and-drop into Google Calendar)")
        print(f"  graph source : {ctx['_graph_source']}")
        print(f"  energy       : {targets.calorie_target_kcal} kcal/day ({targets.calorie_strategy})")
        print(f"  protein      : {targets.protein_g} g  · BMR {targets.bmr_kcal} ({targets.bmr_method})")
        print(f"  screenings   : {len(targets.screenings)} · data gaps: {len(targets.data_gaps)}")
        print("  → render to PDF with: pipeline/08_build_pdfs.sh (reuses the Phase-8 stylesheet)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
