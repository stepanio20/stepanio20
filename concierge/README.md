# concierge/

The **Concierge layer** — turns the Knowledge Engine's facts + reports into a planned,
booked, calendar-synced week. Design doc: [`../PRODUCT_ARCHITECTURE.md`](../PRODUCT_ARCHITECTURE.md).

**Status:** scaffolding only. This directory will hold the recommendation engine,
orchestration engine, connectors, and the weekly-plan renderer as they're built
(roadmap §13 of the product doc, milestones M0–M7).

## Layout (planned)

| Path | Role | Milestone |
|---|---|---|
| `config.schema.json` | JSON Schema for a user's concierge config (prefs, budget, integrations) | M0 ✅ |
| `recommend/` | Health Graph → weekly targets (deterministic; macros, training, recovery, screening, data gaps) | **M1 ✅** |
| `orchestrate/` | targets + prefs → a concrete dated 7-day plan, rendered to Markdown | **M3 ✅** |
| `make_weekly_plan.py` | CLI that assembles context and writes the plan | **M1/M3 ✅** |
| `tests/` | deterministic engine + render tests (`python -m concierge.tests.test_engine`) | ✅ |
| `connectors/whoop/` | OAuth + webhook → wearable facts into the graph | M2 |
| `connectors/gcal/` | Google Calendar read free/busy + write confirmed plan | M5 |
| `action/` | execute plan at best available "rung" (API book / deep-link / hand-off) | M6 |
| `datagap/` | gap → Barcelona test recommendation (extends pipeline phase 6g) — partial, in `recommend/engine.py` | M7 |
| `app/` | Next.js PWA — the weekly review/edit/approve screen | M4 |

## Run (M1 + M3, works today — stdlib only, no deps)

```bash
python -m concierge.make_weekly_plan --user me              # writes users/me/reports/weekly_plan.md
python -m concierge.make_weekly_plan --user me --out -      # print to stdout
python -m concierge.tests.test_engine                       # run the tests
```

Reads `users/<user>/concierge.json` (prefs) + `users/<user>/bundles/health_graph.json`
(your real facts, gitignored). If no real graph exists it falls back to
`recommend/health_graph.sample.json` so it always runs. Render to PDF by feeding the
output through `pipeline/08_build_pdfs.sh` (reuses the Phase-8 stylesheet).

## Config

Each user gets a `concierge.json` validated against `config.schema.json`. The personal
template lives at [`../users/me/concierge.json`](../users/me/concierge.json). It holds
**preferences only** (diet, budget, neighbourhood, connected services) — never medical
data, which stays in the gitignored Health Graph.

## Connector reality (see product doc §5)

- **Live APIs:** Whoop ✅, Google Calendar ✅, Oura ✅, Mindbody-Affiliate (booking+pay) 🟡.
- **Hand-off only (deep link / one tap in native app):** Uber Eats (until partner
  approval), Glovo (no consumer API), groceries, bespoke studio pages, most Barcelona labs.
- **Upload-only:** all consumer DNA (23andMe API dead since 2018), blood-test PDFs.

Nothing spends money or books a medical test without an explicit weekly **Approve**.
