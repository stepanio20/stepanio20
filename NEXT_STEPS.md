# Onboarding Checklist

Practical roadmap for going from "empty repo" → "first PDF report" using the
architecture in [`ARCHITECTURE.md`](./ARCHITECTURE.md). Tick items off in order.

## 0. Profile (15 min — no data needed)

- [ ] Fill in [`users/me/profile.json`](./users/me/profile.json):
  - `name`, `sex` (`"XY"` / `"XX"`), `date_of_birth`
  - `country_of_residence` (ISO-2)
  - `anthropometric.height_cm`, `anthropometric.weight_kg`
  - `family_history.{mother,father,siblings,…}` — each diagnosis: `{condition, age_of_onset, status}`
  - `current_medications`, `chronic_conditions`
  - Remove the `_instructions` and `_*_help` fields once you understand them.

The closer the relative and the earlier the onset of any cancer / cardio / metabolic
condition, the heavier the prior the Phase-4 P/LP screen will use. Don't skip this.

## 1. Get raw data (1–8 weeks, depending on source)

- [ ] **Consumer DNA** (pick one — they're all supported via the `snps` library):
  - **MyHeritage** — ~€39, mail-back, ~4 weeks (cheapest)
  - **23andMe** — typically richer SNP coverage than MyHeritage
  - **AncestryDNA V2** — 677k SNPs, but watch for strand-flip artefacts; triple-validation strongly recommended (ARCHITECTURE.md §4 Phase 4)
  - **FTDNA** — supported

  Save the raw CSV (NOT a PDF report — you need the underlying raw download) into:
  ```
  users/me/dna/raw/
  ```

- [ ] **Blood panel** — if you don't already have a recent one (<12 months), order:
  - Lipid panel (LDL, HDL, triglycerides, total cholesterol, ApoB if available)
  - Liver function (ALT, AST, GGT, ALP, bilirubin)
  - Kidney function (creatinine, eGFR, urea)
  - Hematology (CBC + differential)
  - Inflammation (hs-CRP, ferritin)
  - Endocrinology (TSH, free T4, fasting glucose, HbA1c, fasting insulin)
  - Vitamin D, B12, folate

  Save the lab PDF / Excel into:
  ```
  users/me/bloods/
  ```

- [ ] **Apple Health export** (optional but unlocks Phase 6h + 6i):
  - iPhone → Health app → profile (top-right) → Export All Health Data
  - Unzip; place `export.xml` plus the sibling `electrocardiograms/`, `workout-routes/` etc. folders into:
    ```
    users/me/wearables/apple_export/
    ```

- [ ] **CGM** (optional, highest-signal-per-effort wearable):
  - Dexcom G7 / FreeStyle Libre — wear for 2+ weeks; data lives inside the Apple Health export
  - The pipeline auto-extracts it to `users/me/wearables/parsed/glucose.json`

## 2. Reference data (~5 GB, downloaded once)

The `shared/` directory holds reference panels + tool JARs. Nothing in it is
tracked in git. A future `pipeline/setup_shared.sh` will fetch everything; for
now know where each piece lives:

| Path | Source | Approx. size |
|---|---|---|
| `shared/fasta/` | GRCh38 + GRCh37 primary assemblies (Ensembl/UCSC) | ~6 GB |
| `shared/beagle/` | Beagle 5.5 JAR + 1000G b37.bref3 | ~1.5 GB |
| `shared/pharmcat/` | PharmCAT 3.2.0 JAR + data | ~100 MB |
| `shared/liftover/` | UCSC hg38↔hg19 chain files | ~10 MB |
| `shared/pgs_cache/` | PGS Catalog scoring files | per-trait, cached on demand |

## 3. Run the phases (see ARCHITECTURE.md §4)

Pipeline scripts go under `pipeline/`. Port them in as you reach each phase —
the architecture doc has full I/O contracts:

| Phase | Script (to add) | Produces |
|---|---|---|
| 1 | `pipeline/01_normalize.py --user me` | `users/me/dna/normalized/my_dna_grch38.vcf.gz` |
| 2 | `pipeline/02_opencravat.sh me` | `users/me/dna/annotated/*.variant.tsv` (174k × 143) |
| 3 | `pipeline/03_pharmcat.sh me` | `users/me/dna/annotated/pharmcat/*.report.html` |
| 4 | `pipeline/04_pl_screen.py --user me` | `users/me/reports/pl_findings.md` |
| 5 | `pipeline/05_extract_bloods.py --user me` | `users/me/bloods/<date>.json` |
| 5 | `pipeline/05_pgs_compute.py --user me` | PGS percentile scores |
| 6 | `pipeline/06_bundle.py --user me` | 14 × `users/me/bundles/<domain>.json` |
| 7 | (interactive, in Claude Code — see ARCHITECTURE.md §4 Phase 7) | `users/me/reports/domains/<domain>.md` |
| 8 | `pipeline/08_build_pdfs.sh me` | `users/me/reports/*.pdf` |

## 4. Optional: imputation (multiplies usable variants ~47×)

Only run once Phase 1 + 2 produce clean chip output.

- [ ] **TOPMed** (clinical-grade — 422M variants, ~8.1M at R²≥0.3):
  ```bash
  bash pipeline/impute_topmed.sh me
  ```
  Requires a free TOPMed Imputation Server account. ~25 min when the cluster is healthy.

- [ ] **Beagle local** (offline fallback — 30.7M variants, ~2.5M at R²≥0.3):
  ```bash
  bash pipeline/local_imputation_run.sh me
  ```
  ~70 min, no cloud needed, good for cross-validation.

## 5. Iterate

- New blood draw → drop the PDF into `users/me/bloods/`, re-run Phase 5 + 6 + 8.
- New Apple Health export → drop the new `export.xml`, re-run Phase 6h / 6i + 8.
- Re-render any markdown report → re-run `pipeline/08_build_pdfs.sh me`.
- All findings should be traceable through `users/me/reports/data_inventory.md`
  (Phase 6g) — if a report claims something the inventory says isn't derivable
  from your data, that's a bug.
