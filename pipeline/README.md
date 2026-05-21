# pipeline/

Executable scripts for the numbered phases (see [`../ARCHITECTURE.md`](../ARCHITECTURE.md) §4 and §8a).
Currently empty — port scripts in as you reach each phase.

Naming convention:

```
_paths.py                       ← single source of truth for the layout (shared)
_pl_screen_core.py              ← shared core for Phase 4 / 4b
01_normalize.py / 01_verify.py  ← Phase 1
02_opencravat.sh / 02_verify.py ← Phase 2
03_pharmcat.sh / 03_verify.py   ← Phase 3
04_pl_screen.py                 ← Phase 4
04b_pl_screen_topmed.py         ← Phase 4b
05_extract_bloods.py
05_pgs_compute.py
05_pgs_report.py
06_bundle.py                    ← Phase 6 — 5 core domains
06b_bundle_new_domains.py       ←           9 wellness domains
06c_nutrigenomic_topmed_delta.py
06d_v1_v2_diff.py
06e_dashboard.py
06f_wellness_overview.py
06g_data_inventory.py
06h_wearable.py
06i_cgm_analysis.py
07_prepare_prompts.py / 07_synthesize.py
08_build_pdfs.sh
parse_apple_health.py
impute_topmed.sh / topmed_monitor.sh / topmed_postprocess.sh
local_imputation_run.sh / local_imputation_liftover.py
impute_family_member.sh
verify_all.sh
healthlake/                     ← 00_manifest.py … 04_build_gold_views.py + run_all.py
```

Every script takes `--user <name>` (Python) or `$1` / `$HEATH_USER` (shell).
There are no hardcoded paths — `_paths.py::paths_for(user)` is the resolver.
