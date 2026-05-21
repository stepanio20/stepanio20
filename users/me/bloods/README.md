# bloods/

**Put blood-test source files here** — PDF lab reports, Excel exports, lab-portal
screenshots, or scans of paper results.

Naming convention (recommended, not enforced):

```
YYYY-MM-DD_<lab>_<panel>.pdf
```

Examples:
- `2026-04-24_umcg_full-panel.pdf`
- `2026-04-24_umcg_full-panel.json`  ← produced by Phase 5
- `screenshots/2026-04-24_lipid.png`

What the pipeline does:

1. **Phase 5** (`pipeline/05_extract_bloods.py --user me`) reads the source file
   and produces a structured JSON like `bloods/2026-04-24.json` with per-test
   `{value, unit, reference_range, flag}` rows. Flag is one of
   `GOOD / WATCH / HIGH / LOW`.
2. The healthlake (`pipeline/healthlake/run_all.py --user me`) also picks up
   anything in this directory and produces canonical FHIR Observation rows.

The contents of this folder are **gitignored** — blood tests typically contain
your name, date of birth, lab account number, and other PII.
