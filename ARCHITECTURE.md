---
title: "HeathProject — Personal Genomics Pipeline Architecture"
subtitle: "How the whole thing works — inputs, tools, transformations, outputs"
---

# HeathProject — Architecture & Data Flow

**Last updated:** 2026-05-21 — wearable + CGM phases, per-user data inventory, healthlake MVP, clinical-WES track.
**Status:** Active. Three consumer-genomics users (Ruslan, Olga, Sergii) with full report sets, plus a fourth user (Veronika) on a separate clinical-WES track. Multi-user layout stable; cross-user-leak guard in place via `pipeline/verify_all.sh`.
**Audience:** Ruslan (Dutch resident, 42) — no clinical training assumed; technical literacy assumed.

## Users — current state

The consumer-genomics pipeline (the main subject of this document) serves three users. A fourth user, Veronika, runs on a **separate clinical-WES track** described in §8b — different input (raw exome FASTQ, not a chip), different question (a specific paediatric diagnosis), and deliberately outside the `verify_all.sh` report contract.

| User | Vendor | Chip SNPs | Imputation | Bloods | Wearable | Family hx | v1_full.pdf | v2_full.pdf |
|---|---|---|---|---|---|---|---|---|
| **Ruslan** | MyHeritage | 609k | TOPMed + Beagle | Apr 2026 (DNA-DIAG UMCG) | 10y Apple Health + Dexcom G7 CGM | mother BC, father T2D 10y | ✓ 1.0 MB | ✓ 2.0 MB |
| **Olga** | MyHeritage | 609k | TOPMed + Beagle | Dec 2025 (Erasmus MC) | 10y Apple Health | mother pancreatic@55, father prostate@62 | ✓ 588 KB | ✓ 1.3 MB |
| **Sergii** | AncestryDNA V2 | 677k | TOPMed + Beagle | — | — | not provided | ✓ 448 KB | ✓ 600 KB |
| **Veronika** | 3billion clinical WES | — (exome FASTQ) | n/a | Synevo panel (PDF) | — | aunt: GGT↑, ANA+ | clinical-WES track — see §8b | — |

All three consumer-pipeline users pass `pipeline/verify_all.sh` (forbidden-string check + PDF existence + per-user data-inventory page + CGM-report presence + date staleness + profile sanity). Veronika has no `reports/` directory or `profile.json`, so `verify_all.sh` skips her — the clinical-WES track is intentionally not held to the consumer-report contract.

## Multi-user layout

The project supports multiple users under a `users/` namespace:

```
HeathProject/
├── users/
│   ├── ruslan/                ← MyHeritage chip + TOPMed + Beagle + bloods + Apple Health + Dexcom CGM
│   ├── olga/                  ← MyHeritage chip + TOPMed + Beagle + bloods + Apple Health + v3 deep-dive
│   ├── sergii/                ← AncestryDNA chip + TOPMed + Beagle, no bloods/wearable
│   │   ├── profile.json       ← name, sex, age, anthropometric, family hx, key_genetic_findings_v2_topmed, tier_a_actions, headline_findings
│   │   ├── dna/{raw,normalized,imputation_input,imputed_local,topmed,
│   │   │      annotated,annotated_imputed,annotated_topmed}/
│   │   ├── bloods/            ← per-blood-draw JSON + screenshots/   (Olga + Ruslan only)
│   │   ├── wearables/         ← apple_export/ + parsed/*.json        (Olga + Ruslan only)
│   │   │                        parsed/glucose.json = Dexcom CGM    (Ruslan only)
│   │   ├── healthlake/        ← document data-lake (bronze/silver/gold + FHIR)  (Ruslan only — see §8c)
│   │   ├── bundles/           ← per-domain JSON (LLM input)
│   │   └── reports/           ← markdown + PDF
│   └── verinika/ + Verona/    ← clinical-WES track (see §8b) — NOT the consumer pipeline:
│                                raw exome FASTQ, BWA-MEM align, AGS gene-panel screen,
│                                read-based phasing. No profile.json / reports/ contract.
│
├── shared/                    ← cross-user reference data, never per-user
│   ├── CAPABILITY_MATRIX.md   ← "given this data layer, which reports/conclusions unlock?"
│   ├── snippets/              ← canonical fragments referenced by reports
│   │   ├── caveat_bloods.md   ← single source for "wait-for-bloods" callout
│   │   ├── chip_refutation.md ← chip→Beagle→TOPMed triple-validation explainer
│   │   └── data_gaps.md       ← canonical "what each measurement unblocks" page
│   ├── pgs_cache/             ← PGS Catalog scoring files
│   ├── gnomad_cache.json      ← gnomAD AF query cache
│   ├── _1kg_cache/            ← 1000 Genomes phase 3 reference
│   ├── pharmcat/              ← PharmCAT JAR + reference data
│   ├── beagle/                ← Beagle 5.5 + b37.bref3 reference panels
│   ├── fasta/                 ← reference genomes (GRCh38 + GRCh37)
│   ├── liftover/              ← chain files
│   └── prompts/               ← LLM synthesis prompts (system + per-domain)
│
├── pipeline/                  ← all scripts; take --user <name> argument
│   ├── _paths.py              ← single source of truth for the layout
│   │                            (+ family-history helpers + data_stamp())
│   ├── _pl_screen_core.py     ← shared core for Phase 4 / 4b (gene panels, gnomAD, render)
│   ├── healthlake/            ← document data-lake pipeline (5 scripts — see §8c)
│   └── verify_all.sh          ← per-user forbidden-string + PDF + inventory + CGM + staleness + profile check
├── ARCHITECTURE.md            ← this file
├── DATA_ARCHITECTURE_RECOMMENDATION.md  ← design rationale for the healthlake layers
└── spec.md                    ← project plan / decisions log
```

**Path resolution:** every Python script imports `_paths.paths_for(user)` to get a
typed `UserPaths` dataclass with all known per-user paths. Shell scripts take
`USER_NAME` as `$1` or `$HEATH_USER`. There are no hardcoded paths — the layout
is one place.

**Default user:** `HEATH_USER` env var > the only user > `ruslan`. Set
`export HEATH_USER=olga` in a shell to make every command default to her.

**Profile-conditional rendering:** Reports that depend on the user's family
history, bloods presence, or wearable data load `profile.json` and render
conditionally via `paths_for(user).load_profile()` + the helpers
`has_hereditary_cancer_history(profile)` and `family_cancer_summary(profile)`.
Per the `feedback_no_cross_user_comparisons` rule, no report should reference
another user's name or clinical findings — `verify_all.sh` enforces this.

---

## 1. Project goal in one paragraph

Take a single MyHeritage spit-kit raw DNA file (~600,000 measured genomic positions out of 3 billion total) and turn it into a comprehensive personal health & wellness report — equivalent to what services like **SelfDecode**, **Genomelink**, **NutraHacker**, and **FoundMyFitness** sell — but **using only open-source tools, public databases, and the user's own compute resources**, with full reproducibility and zero black-box claims. Output: a stack of PDF reports covering disease risk, drug response, polygenic trait percentiles, nutrigenomics, and a daily-protocol action plan.

The project has been built up incrementally. The architecture below reflects the current state — including two paths for genotype imputation (local Beagle + cloud TOPMed), parallel where they overlap, with TOPMed data being the primary input for v2 outputs.

---

## 2. The 30-second mental model

```
                     ┌────────────────────────────────────────┐
                     │  YOUR INPUTS (one-time + ongoing)      │
                     │  • Consumer DNA raw file (CSV)         │
                     │  • Clinical blood panel (PDF / docx)   │
                     │  • Family medical history (text)       │
                     │  • Apple Health export (export.xml)    │
                     │  • Dexcom CGM (inside Apple Health)    │
                     │  • Anthropometrics: age, height/weight │
                     └────────────────────────────────────────┘
                                       │
                                       ▼
   ┌───────────────────────────────────────────────────────────────┐
   │  TRANSFORMATION PIPELINE                                      │
   │  (~13 phases, ~11,500 lines of code, ~50 GB intermediate data)│
   └───────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
                ┌────────────────────────────────────────┐
                │  YOUR OUTPUTS                          │
                │  • ~25 PDF reports (v1 + v2 bundles)   │
                │  • 14 domain JSON bundles + cgm.json   │
                │  • Per-user data-inventory page        │
                │  • Reproducible scripts in pipeline/   │
                │  • Memory of decisions made            │
                └────────────────────────────────────────┘
```

That's it. Inputs go in, transforms run, reports come out.

---

## 3. Top-level data flow

```
                                        ┌──────────────────────┐
                                        │  PUBLIC DATABASES    │
                                        │  (downloaded once,   │
                                        │   ~5 GB total)       │
                                        │                      │
                                        │  • ClinVar           │
                                        │  • PharmGKB          │
                                        │  • PharmCAT          │
                                        │  • AlphaMissense     │
                                        │  • REVEL, EVE, CADD  │
                                        │  • gnomAD            │
                                        │  • CIViC, COSMIC     │
                                        │  • OMIM, GWAS Cat.   │
                                        │  • PGS Catalog       │
                                        │  • 1000G GRCh38 b37  │
                                        │  • Liftover chains   │
                                        └──────────┬───────────┘
                                                   │
                                                   │
        ┌──────────────────┐                       │
        │ MyHeritage .csv  │                       │
        │ ~609k SNPs       │                       │
        │ build 37         │                       │
        └────────┬─────────┘                       │
                 │                                 │
        ┌────────▼─────────┐                       │
        │ PHASE 1          │                       │
        │ Normalize        │                       │
        │ (snps lib)       │                       │
        │ → GRCh38 VCF     │                       │
        └────────┬─────────┘                       │
                 │                                 │
                 │ 174,317 variants                │
                 ├──────────────────┐              │
                 │                  │              │
        ┌────────▼─────┐  ┌─────────▼──────┐       │
        │ PHASE 2/3/4  │  │ Imputation     │       │
        │ (chip-only)  │  │ (TWO paths)    │       │
        │ • OpenCRAVAT │  │ • Beagle local │       │
        │ • PharmCAT   │  │ • TOPMed cloud │       │
        │ • P/LP screen│  └────────┬───────┘       │
        └──────┬───────┘           │               │
               │                   │ 422M variants │
               │                   ▼               │
               │          ┌────────────────┐       │
               │          │ Re-run 2/3/4   │◀──────┘
               │          │ on imputed VCF │  (annotation)
               │          └────────┬───────┘
               │                   │
               └───────┬───────────┘
                       ▼
            ┌────────────────────────┐
            │ PHASE 5/6              │
            │ Bloods + wearable +    │
            │ CGM extraction;        │
            │ domain bundle assembly │
            │ (14 domains);          │
            │ data-inventory page    │
            └──────────┬─────────────┘
                       │
                       ▼
            ┌────────────────────────┐
            │ PHASE 7                │
            │ Multi-agent LLM        │
            │ synthesis              │
            │ (subagents via Claude) │
            │ • Synthesizer          │
            │ • Adversarial reviewer │
            │ • Reconciler           │
            └──────────┬─────────────┘
                       │
                       ▼
            ┌────────────────────────┐
            │ PHASE 8                │
            │ Render to PDF          │
            │ (pandoc + weasyprint)  │
            └──────────┬─────────────┘
                       │
                       ▼
            ┌────────────────────────┐
            │ DELIVERED PDFs         │
            │ (v1 + v2 bundles —     │
            │  see §8 for the list)  │
            └────────────────────────┘
```

---

## 4. Phase-by-phase deep dive

### Phase 1 — Normalize

**Input:** `data/raw/MyHeritage_raw_dna_data.csv` (CSV with 609,215 rows: rsID, chrom, pos, genotype)
**Output:** `data/normalized/my_dna_grch38.vcf.gz` (standard VCF on GRCh38)
**Tool:** [`snps`](https://pypi.org/project/snps/) Python library
**Key transformations:**
- Auto-detect source (MyHeritage GSA, 23andMe, Ancestry, FTDNA all supported)
- **Remap GRCh37 → GRCh38** (the 2009 reference is too old for modern annotation tools)
- For each position, look up REF allele in the GRCh38 chromosome FASTA, encode user's genotype as standard VCF GT format
- bgzip + tabix index for downstream tools
**Verification:** `pipeline/01_verify.py` cross-checks 25 specific variants from the v0 report — all match.

### Phase 2 — Annotate

**Input:** Phase 1 VCF
**Output:** `data/annotated/my_dna_grch38.vcf.gz.variant.tsv` (174k rows × 143 annotation columns)
**Tool:** [OpenCRAVAT](https://opencravat.org/) — variant annotation hub
**Annotators run:** clinvar, clinvar_acmg, omim, pharmgkb (failed — covered by PharmCAT instead), gwas_catalog, ncbigene, go, ess_gene, alphamissense, revel, eve, cadd_exome, cancer_hotspots, cancer_genome_interpreter, cgl, civic, civic_gene, aloft, loftool

For each variant, attaches: clinical significance, drug-gene interaction, deep-learning pathogenicity score (AlphaMissense, REVEL, EVE), structural prediction (CADD), trait associations, gene context. **The big merged table everything downstream consumes.**

### Phase 3 — Pharmacogenomics (PharmCAT)

**Input:** Phase 1 VCF
**Output:** `data/annotated/pharmcat/my_dna_grch38.report.html` (browsable per-drug report)
**Tool:** [PharmCAT 3.2.0](https://www.pharmcat.org/) — clinical-grade PGx
**What it does:** For 23 pharmacogenes, calls the user's diplotype (e.g., CYP3A5 *1/*3), maps to phenotype (e.g., "Intermediate Metabolizer"), then looks up CPIC + DPWG + FDA guidelines for ~150 medications. Output: drug-by-drug recommendations.

PharmCAT's strict input requirements caused a real headache in the imputation phase (only accepts VCFv4.2, narrow position list). Locally it just works on Phase 1's chip data.

### Phase 4 / 4b — High-penetrance disease screen

**Input:** Phase 2 OpenCRAVAT TSV (chip) or Phase 2 re-run TSV (TOPMed-imputed R²≥0.8)
**Output:** `users/<user>/reports/pl_findings.md` (chip pass) or `v2_pl_findings_topmed.md` (TOPMed pass)
**Tool:** Python + gnomAD GraphQL API
**Shared core:** `pipeline/_pl_screen_core.py` — gene panels, gnomAD lookup, classification, markdown rendering all live in this module. The chip and TOPMed entry points (`04_pl_screen.py`, `04b_pl_screen_topmed.py`) are ~38-line wrappers that resolve paths and call `run_screen(P, profile, tsv_path, out_json, out_md, is_topmed=...)`.

**What it does:** Filters to ClinVar Pathogenic / Likely-Pathogenic variants in priority gene panels (hereditary cancer, FH, inherited cardiac, thrombophilia). Then queries gnomAD for population frequency — drops "common" variants that are mis-classified as pathogenic by single-submitter ClinVar entries. Family-history caveat renders conditionally based on `profile.json`.

**Results across users:**
- Ruslan (chip + TOPMed + Beagle): 0 confirmed P/LP in any priority panel. Triple-validated.
- Olga (chip + TOPMed + Beagle): 0 confirmed P/LP in any priority panel. Triple-validated. False-alarm pattern (ATP6AP2, TIMM8A, MYBPC3) all explained.
- Sergii (chip + TOPMed + Beagle): chip flagged 8 homozygous-ultra-rare ClinVar P/LP variants — *all 8 empirically refuted* by both TOPMed and Beagle. These were AncestryDNA strand-orientation / pseudogene cross-hybridisation artefacts. **Triple-validation is the strongest empirical refutation the home pipeline can produce.**

### Imputation — Two parallel paths (chronological story)

#### Path A: Beagle local

**Tool:** [Beagle 5.5](http://faculty.washington.edu/browning/beagle/) by Brian Browning
**Reference panel:** 1000 Genomes phase 3, GRCh37 (`b37.bref3`, ~1.5 GB total)
**Why local:** TOPMed's cloud service had a 24-hour outage after we hit the 20-sample policy limit; Beagle was the fallback so we'd have *some* imputed data.
**Pipeline:**
1. Liftover user's GRCh38 VCF → GRCh37 (Browning lab only ships b37 reference)
2. Per-chromosome Beagle imputation (`pipeline/local_imputation_run.sh`)
3. Liftover imputed result GRCh37 → GRCh38
4. `bcftools concat` + R² filter
**Output:** 30,738,827 variants total; 2,540,879 at R²≥0.3
**Quality:** decent for common variants; poor for rare ones (small reference panel)
**Time:** ~15 min for setup + ~3 min per chromosome × 22 chromosomes (sequential, since `nthreads=4` causes Beagle to crash on multi-window chromosomes — `nthreads=1` is reliable)

#### Path B: TOPMed Imputation Server

**Tool:** [NIH BioData Catalyst TIS v2](https://imputation.biodatacatalyst.nhlbi.nih.gov/)
**Reference panel:** TOPMed r3 (~200,000 fully-sequenced people)
**Submission:** REST API with `X-Auth-Token`; multipart-form upload of chr_N.vcf.gz files
**Hard-won fixes (in order of discovery):**
1. **20-sample minimum:** padded with 19 EUR-ancestry 1000G samples
2. **CloudFront upload timeout:** filtered padded VCFs to user's chip positions only (5.8 GB → 11 MB)
3. **VCFv4.3 not supported:** downgraded header to VCFv4.2
4. **SV INFO header rejection:** stripped `INFO/SVTYPE`, `INFO/END2`, etc.
5. **chrX haploid/diploid mismatch:** dropped chrX (would need same-sex 1000G fillers; TODO)
6. **Multiple cluster outages:** stop spam-retrying, wait for US business hours
**Output:** 422,729,346 variants total; 8,145,957 at R²≥0.3 (14× more than Beagle)
**Quality:** clinical-grade
**Time:** ~25 min once cluster is healthy

#### Why we keep both
- TOPMed = primary input for v2 reports (better quality)
- Beagle = cross-validation / sanity check / runs offline
- If TOPMed cluster is down, Beagle keeps the project moving

### Phase 5 — Blood test extraction

**Input:** `Health_Genomic_Report_2026.docx` (existing v0 report, contains structured tables for blood values)
**Output:** `data/bloods/2026-04-24.json`
**Tool:** Python + `python-docx`
**What it does:** Reads the 7 blood-panel tables (lipid profile, liver function, hematology, kidney, inflammation, endocrinology, white-cell differential) and the "follow-up tests proposed by v0" table. Produces structured JSON with per-test value, unit, reference range, flag (HIGH/WATCH/GOOD).

**For this user:** 30 measured tests + 9 follow-up tests proposed.

### Phase 6 — Domain bundling

**Input:** Phase 2 TSV + Phase 3 PharmCAT JSON + Phase 4 P/LP findings + Phase 5 blood JSON + family history
**Output:** `bundles/{domain}.json` × 14 (one per domain) + `bundles/integrated.json` (master index)
**Tool:** Python (`pipeline/06_bundle.py`, `pipeline/06b_bundle_new_domains.py`)

The 14 domains:

| # | Domain | What it covers | Variants in panel |
|---|---|---|---|
| 1 | cardiovascular | LDL/HDL/lipid metabolism, FH genes | 31 |
| 2 | metabolic | T2D, NAFLD, insulin resistance | 14 |
| 3 | methylation | MTHFR, B vitamins, homocysteine | 21 |
| 4 | pharmacogenomics | All 23 PharmCAT genes | 53 |
| 5 | hereditary_cancer | BRCA1/2, Lynch, ATM, etc. | 33 |
| 6 | sleep | Chronotype, circadian, insomnia | 27 |
| 7 | gut | LCT, IBD susceptibility, FUT2 | 38 |
| 8 | skin | MC1R, pigmentation, photoaging | 42 |
| 9 | immunity | HLA, inflammation, autoimmune | 30 |
| 10 | hormones | Testosterone, AR, SHBG | 41 |
| 11 | mood_focus | COMT, BDNF, 5HTT (heavy caveats) | 61 |
| 12 | athletic | ACTN3, ACE, recovery, injury | 62 |
| 13 | longevity | FOXO3, APOE, KLOTHO, telomere | 30 |
| 14 | senses | TAS2R38 bitter, OR6A2 cilantro, pain | 42 |

Each bundle is a focused JSON packet (15–50 KB) ready to feed to an LLM without context-bleed across domains.

### Phase 7 — Multi-agent LLM synthesis

**Input:** A bundle JSON (one domain at a time)
**Output:** A v1 markdown report for that domain, in `reports/domains/{domain}.md`
**Tool:** Claude Code's Agent tool (subagents) — uses your existing Claude subscription, no API key
**Pattern:** Three roles per domain, executed sequentially:

```
                     ┌────────────────────────┐
   bundle JSON ────▶ │  SYNTHESIZER           │ ───▶ draft.md
                     │  (Opus 4.7)            │
                     │  Strict citation rules │
                     │  Compares to v0 report │
                     └────────────────────────┘
                                  │
                                  ▼
                     ┌────────────────────────┐
   draft + bundle ─▶ │  ADVERSARIAL REVIEWER  │ ───▶ critique.md
                     │  (Sonnet 4.6)          │
                     │  Find effect-size      │
                     │  overreach, missing    │
                     │  caveats, calibration  │
                     │  errors                │
                     └────────────────────────┘
                                  │
                                  ▼
                     ┌────────────────────────┐
   draft + critique  │  RECONCILER            │ ───▶ {domain}.md (final)
   + bundle ──────▶  │  (Opus 4.7)            │
                     │  Apply Sev-1 fixes,    │
                     │  preserve correct      │
                     │  content, tighten prose│
                     └────────────────────────┘
```

**Why three stages:** the synthesizer alone tends to overstate effect sizes and slip into diagnostic language. The adversarial reviewer (different role + system prompt) catches exactly those overreaches. The reconciler integrates fixes without weakening the parts that were correct. Cost: ~3× more LLM-time per domain than single-pass, but the quality lift is real (we documented dozens of corrections in the actual reports).

### Phase 6c — Nutrigenomic TOPMed delta

**Tool:** `pipeline/06c_nutrigenomic_topmed_delta.py`
**Input:** chip-annotated TSV + TOPMed-annotated TSV (both ~3 GB; TOPMed streamed via `pd.read_csv(chunksize=200_000)` to avoid OOM)
**Output:** `users/<user>/dna/annotated_topmed/nutrigenomic_delta.md` — table of net-new actionable variants surfaced by TOPMed vs chip

### Phase 6d — v1→v2 transition page

**Tool:** `pipeline/06d_v1_v2_diff.py`
**Output:** `users/<user>/reports/v2_diff_from_v1.md` — one-page PGS percentile-shift summary (chip → TOPMed), flagging "material shifts" (≥10 percentile change), plus a brief "what else TOPMed resolved" section (APOE haplotype, PharmCAT runs, chip-P/LP refutation).

### Phase 6e — "Numbers at a Glance" dashboard

**Tool:** `pipeline/06e_dashboard.py`
**Output:** `users/<user>/reports/v2_dashboard.md` — 1-page executive summary: PGS percentile bars with tier colour coding (`tier-a` = watch, `tier-c` = favourable), headline findings list, Tier-A action checklist. Reads from `profile.json` + the appropriate PGS results JSON.

### Phase 6f — Wellness Genetics Overview

**Tool:** `pipeline/06f_wellness_overview.py`
**Output:** `users/<user>/reports/v2_wellness_overview.md` — single consolidated index across the 9 wellness domains (athletic, gut, hormones, immunity, longevity, mood_focus, senses, skin, sleep). Replaces the "9 thin individual reports that all end with the same caveat" pattern for users without bloods/wearable; for users with measured data, the per-domain reports add the data-anchored detail.

### Phase 6g — Per-user data inventory

**Tool:** `pipeline/06g_data_inventory.py`
**Output:** `users/<user>/reports/data_inventory.md` — the per-user instance of the static `shared/CAPABILITY_MATRIX.md`. Reads `profile.json` and checks the filesystem for chip / Beagle / TOPMed / bloods / wearable / CGM / family-history, then renders a ✅/❌ table answering *"what data does this user have, and which reports/conclusions does each layer unlock?"* `verify_all.sh` now requires this page for every consumer-pipeline user — it is the traceability contract: if a finding appears in a report that the matrix says shouldn't be derivable, that's a bug.

### Phase 6h — Wearable insights

**Input:** `users/<user>/wearables/parsed/*.json` — produced by `pipeline/parse_apple_health.py`, which streams the multi-GB `export.xml` (never a DOM parse — it OOMs) into structured JSON: sleep stages, heart rate, HRV, VO2max, steps, workouts, weight history, ECGs.
**Tool:** `pipeline/06h_wearable.py` — exits cleanly with no output for users without a parsed export (Olga has one; Sergii does not).
**Outputs:**
- `chronotype_wearable.md` — the **authoritative behavioural chronotype call**, from three independent watch-derived reads on circadian phase: sleep-timing MSFsc (Roenneberg MCTQ), heart-rate nadir, and deep-sleep distribution. Explicitly supersedes the imputation-unstable genetic GRS313 polygenic chronotype score.
- `wearable_insights.md` — sleep architecture, cardio-fitness trends (resting HR / HRV / VO2max), multi-year body history, rhythm events, activity baseline, and what each measured fact changes versus the genetic priors.

Methodology is anchored to Apple HealthKit semantics: only `Apple Watch`-sourced records (measured sleep, not iPhone Sleep-Schedule intentions), Ultra-2 era only (2024-01-01 cutoff), union-merge of overlapping stage segments, gap-based sessionisation, nap exclusion.

### Phase 6i — CGM analysis + multi-omics integration

**Input:** `users/<user>/wearables/parsed/glucose.json` — Dexcom / CGM records pulled out of the Apple Health export by `parse_apple_health.py`. Exits cleanly with no output for users without a CGM series.
**Tool:** `pipeline/06i_cgm_analysis.py`
**Outputs:**
- `cgm_analysis.md` — CGM metrics per wear session and pooled: mean / SD / CV, GMI (Bergenstal 2018) + eAG, Time-in-Ranges (TIR 70–180, tight 70–140, lows, highs), MAGE (Baghurst turning-point) + CONGA-1, nocturnal nadir + dawn phenomenon (joined to the parsed sleep record), weekday/weekend split, glucose×sleep and glucose×exercise comparisons, and a **DNA×bloods×CGM integration** (TCF7L2 / FTO context, a TyG estimate, a follow-up request list). All values in both mg/dL and mmol/L (NL units).
- `cgm.json` — machine-readable metrics bundle.
- `cgm_agp.png` — ambulatory-glucose-profile chart (matplotlib).

The report is explicit about its limits: short non-contiguous wears, no meal log, no lab HbA1c. `verify_all.sh` warns if `glucose.json` exists but `cgm_analysis.md` does not.

### Phase 8 — PDF rendering

**Input:** Markdown reports
**Output:** PDFs in `users/<user>/reports/`
**Tool:** pandoc → HTML5 → WeasyPrint → PDF
**Stylesheet:** inline CSS heredoc in `pipeline/08_build_pdfs.sh`. Beyond the base typography, the CSS defines a visual tier system:
- `.tier-a / .tier-b / .tier-c` — left-border colour coding (red / orange / green) for action callouts
- `.caveat` — yellow callout for "measurement dependency" notes (used in `shared/snippets/caveat_bloods.md`)
- `.bottom-line` — blue box surfacing key takeaways that would otherwise be buried after long tables
- `.badge-validated / .badge-chip-only / .badge-refuted` — inline pills for the chip→Beagle→TOPMed validation framing
- `.tier-a-row / .tier-b-row` — table-row tinting

**Build script:** `pipeline/08_build_pdfs.sh` with two helpers:
- `render_single(md, pdf, title)` — single-file render, skips if input missing
- `build_bundle(out_md, out_pdf, title, cover_subtitle, sources...)` — concatenates sources, existence-guards each `cat` so missing files don't break the build, renders bundled PDF

Auto-builds `v2_full.pdf` when any v2-master doc exists (`v2_integrated.md`, `*_TOPMed_*.md`, or `v3_integrated.md` — accommodates users with custom v2-master naming like Olga's `Olga_Health_TOPMed_v3_2026.md`).

Cover dates dynamic via `$(date +%Y-%m-%d)`.

---

## 5. Three imputation paths — when each applies

```
                ┌─────────────────────────┐
                │  What do you need?      │
                └────────────┬────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ Just chip-   │   │ Imputed but      │   │ Imputed clinical │
│ direct calls │   │ offline / privacy│   │ grade            │
│              │   │                  │   │                  │
│ → Phase 1    │   │ → Beagle local   │   │ → TOPMed         │
│   normalize  │   │   1000G panel    │   │   200k panel     │
│              │   │                  │   │                  │
│ 174k SNPs    │   │ 30.7M variants   │   │ 422.7M variants  │
│              │   │ 2.5M at R²≥0.3   │   │ 8.1M at R²≥0.3   │
│              │   │                  │   │                  │
│ Use for:     │   │ Use for:         │   │ Use for:         │
│ - Phase 1    │   │ - PRS draft      │   │ - PRS final      │
│   verify     │   │ - cross-check    │   │ - Disease screen │
│ - Sanity     │   │ - offline mode   │   │ - Anything       │
│   on v0      │   │                  │   │   clinical-grade │
│ - PharmCAT   │   │                  │   │                  │
│   (chip is   │   │                  │   │                  │
│   all PGx    │   │                  │   │                  │
│   needs)     │   │                  │   │                  │
└──────────────┘   └──────────────────┘   └──────────────────┘
        │                    │                    │
        └────────────────────┴────────────────────┘
                             │
                             ▼
                ┌──────────────────────────┐
                │  All three feed into the │
                │  same downstream phases  │
                │  (annotate, screen, PRS, │
                │  bundle, synthesize)     │
                └──────────────────────────┘
```

---

## 6. Tool catalog

| Tool | Role | Why it | Replaces commercial |
|---|---|---|---|
| `snps` (Python lib) | Parse MyHeritage / 23andMe / AncestryDNA / FTDNA CSV → VCF, build remap | Standard format conversion across 4 vendors | — |
| `bcftools` / `htslib` | VCF manipulation, filtering, merging, sorting | Universal genomics CLI | — |
| `pandas` (chunked) | Tabular data (annotated TSV processing); chunked load on multi-GB TSVs | Standard, with `chunksize=200_000` to avoid OOM | — |
| **OpenCRAVAT** | Variant annotation hub (calls 18 sub-databases per variant) | Single command runs ClinVar + AlphaMissense + REVEL + EVE + CADD + GWAS + OMIM + ... | parts of SelfDecode |
| **PharmCAT 3.2.0** | Clinical-grade pharmacogenomics (CPIC/DPWG/FDA-graded drug response) | What FDA-equivalent labs use; works on TOPMed-imputed VCFs (chip-only AncestryDNA hits a normalisation incompatibility — TOPMed is the workaround) | NutraHacker drugs section, beats most consumer PGx |
| **Beagle 5.5** | Local imputation against 1000G phase 3 b37 panel | Free, runs in ~8 min wall-clock for full autosomes (after liftover-header race fix shipped 2026-05-10) | imputation step of SelfDecode (when offline) |
| **TOPMed Imputation Server** | Cloud imputation against 200k-genome panel | Highest-quality imputation publicly available. Token preflight + password validation added 2026-05-11 to fail fast on bad credentials. | imputation step of SelfDecode |
| **gnomAD API** (GraphQL) | Population allele frequencies (filter false-alarm P/LP) | The standard frequency reference | parts of any P/LP screen |
| **PGS Catalog API** + custom Python | Polygenic risk score computation (`pipeline/05_pgs_compute.py`) | Public peer-reviewed scores. Size guard auto-falls-back to R²≥0.8 input if VCF >2 GB. | Genomelink trait reports, parts of SelfDecode |
| **`pyliftover`** | GRCh38 ↔ GRCh37 chain-file based liftover | Simple Python lib for the Beagle round-trip | — |
| `unzip -P`, `7z` | Decrypt TOPMed encrypted result zips | Standard archive tools. Password validation on first-zip prevents 22 silent empty unzips on bad password. | — |
| **Claude Code subagents** | Multi-agent LLM synthesis (synthesizer / reviewer / reconciler) | Uses user's existing Claude subscription, no API key | the AI synthesis layer of SelfDecode / FoundMyFitness |
| **pandoc + WeasyPrint** | Markdown → HTML5 → PDF | Open-source typesetting; CSS-only visual tier system (tier-a/b/c, badges, caveat callouts, bottom-line boxes) | — |
| **matplotlib** | CGM ambulatory-glucose-profile + chronotype/HR-nadir charts | Standard plotting; charts embedded into reports | — |
| **BWA-MEM + samtools** | Clinical-WES re-alignment from FASTQ → sorted BAM (Veronika track only) | Standard short-read aligner; needed because the vendor exome VCF can't be trusted as a complete panel screen | — |
| **`pipeline/healthlake/`** | Document data lake — manifest, text extraction, canonical observations, FHIR NDJSON | Turns a pile of medical PDFs into traceable structured facts (FHIR / LOINC / UCUM) | parts of any PHR / health-record aggregator |
| **`pipeline/verify_all.sh`** | Per-user invariant check: no cross-user leaks, PDFs + data-inventory + CGM report present, dates fresh, profile valid | Catches drift at build-time rather than user-reading-time | — |

---

## 7. Where each public database fits

| Database | What it is | Used in phase | Use case |
|---|---|---|---|
| **ClinVar** (NCBI) | Clinical significance of every catalogued variant | Phase 2 (OpenCRAVAT) | "Does this variant cause disease?" |
| **PharmGKB / CPIC** | Drug-gene interactions, evidence-graded | Phase 3 (PharmCAT) | "Will this drug work for me?" |
| **AlphaMissense** (DeepMind) | AI prediction of protein impact for every possible missense variant | Phase 2 (OpenCRAVAT) | "Even without ClinVar curation, is this variant likely to break the protein?" |
| **REVEL, EVE, CADD** | Older-school variant-impact predictors | Phase 2 (OpenCRAVAT) | Cross-validation of AlphaMissense |
| **gnomAD** (Broad Institute) | Allele frequencies in 800k+ public exomes/genomes | Phase 4 + matrix | "Is this variant rare enough to actually matter?" |
| **CIViC** | Clinical evidence on cancer variants | Phase 2 (OpenCRAVAT) | Cancer-relevant interpretation |
| **GWAS Catalog** | Trait associations from genome-wide association studies | Phase 2 (OpenCRAVAT) | Background trait info |
| **OMIM** | Mendelian disease catalog | Phase 2 (OpenCRAVAT) | Gene → known disease lookup |
| **PGS Catalog** | Peer-reviewed polygenic risk scores (5,000+) | Phase 6 (custom Python) | Trait percentile rankings |
| **1000 Genomes Phase 3** | 2,504 fully-sequenced people across populations | Padding (TOPMed cohort filler) + Beagle reference | Imputation panel + cohort filler |
| **TOPMed r3** | 200,000 fully-sequenced people | TOPMed imputation server | Higher-quality imputation panel |

---

## 8. Output reports — full inventory

All in `users/<user>/reports/`. Not every user has every file — `verify_all.sh` enforces the required core (`v1_full.pdf` always; `v2_full.pdf` if a v2-master doc exists).

### v1 core (every user)

| File | Format | Audience | Built by |
|---|---|---|---|
| `v1_integrated.md` / `.pdf` | Master clinical | Patient + clinician | Phase 7 |
| `v1_one_pager.md` / `.pdf` | Action card | Wallet / fridge | Phase 7 |
| `v1_lifestyle.md` / `.pdf` | Narrative lifestyle plan | Patient | Phase 7 |
| `v1_trait_percentiles.md` / `.pdf` | Chip-only PGS percentiles | Patient | `pipeline/05_pgs_report.py` |
| `pl_findings.md` / `.pdf` | gnomAD-filtered P/LP screen | Clinical | `pipeline/04_pl_screen.py` via `_pl_screen_core.py` |
| `gp_letter_nl.md` / `.pdf` | Dutch GP follow-up lab request | huisarts | Phase 7 (Olga + Ruslan only) |
| `gp_letter_en.md` / `.pdf` | English GP follow-up lab request | clinician | Phase 7 (Olga + Ruslan only) |
| `domains/cardiovascular.md` / `metabolic.md` / `methylation.md` / `pharmacogenomics.md` / `hereditary_cancer.md` | Per-domain v1 deep-dives | Patient | Phase 7 |
| **`v1_full.pdf`** | Bundled cover + lifestyle + master + 5 domains + pl_findings + GP letters | Anyone | `build_bundle()` in `08_build_pdfs.sh` |

### v2 deep-dives (users with TOPMed-imputed data)

| File | Built by |
|---|---|
| `v2_integrated.md` (or `v3_integrated.md` / `*_TOPMed_*.md` for users who keep custom naming) | Phase 7 |
| `v2_pharmcat_humanized.md` | Phase 7 (plain-English drug-by-drug from PharmCAT JSON) |
| `v2_nutrigenomic_matrix.md` | Phase 7, fed by `pipeline/06c_nutrigenomic_topmed_delta.py` |
| `v2_trait_percentiles.md` | `pipeline/05_pgs_report.py --use-topmed` |
| `v2_pl_findings_topmed.md` | `pipeline/04b_pl_screen_topmed.py` via `_pl_screen_core.py` |
| `v2_diff_from_v1.md` | `pipeline/06d_v1_v2_diff.py` (auto-generated PGS shift summary) |
| `v2_dashboard.md` | `pipeline/06e_dashboard.py` (auto-generated 1-page "numbers at a glance") |
| `v2_wellness_overview.md` | `pipeline/06f_wellness_overview.py` (auto-generated consolidated index) |
| `v2_athletic.md` / `gut.md` / `hormones.md` / `immunity.md` / `longevity.md` / `mood_focus.md` / `senses.md` / `skin.md` / `sleep.md` | Phase 7 — 9 wellness domains; optional appendix for users without bloods/wearable (the overview replaces them in the bundle) |
| `ACTIONABLE_HEALTH_PROTOCOL.md` | Phase 7 — operational daily playbook |
| **`v2_full.pdf`** | Bundled by `build_bundle()` in `08_build_pdfs.sh` when v2-master doc exists |

### Traceability + measured-data reports

| File | Built by | For whom |
|---|---|---|
| `data_inventory.md` | `pipeline/06g_data_inventory.py` | every consumer-pipeline user (required by `verify_all.sh`) |
| `chronotype_wearable.md` | `pipeline/06h_wearable.py` | users with a parsed Apple Health export (Olga, Ruslan) |
| `wearable_insights.md` | `pipeline/06h_wearable.py` | users with a parsed Apple Health export |
| `cgm_analysis.md` / `cgm.json` / `cgm_agp.png` | `pipeline/06i_cgm_analysis.py` | users with a Dexcom/CGM series (Ruslan) |

### User-specific extras (Olga only)

| File | Purpose |
|---|---|
| `Olga_Health_TOPMed_v3_2026.md` / `.pdf` | All-in-one v3 deep-dive (Olga's chosen format; serves as her v2-master for bundle build) |
| `Olga_Chronotype_Schedule_2026.md` / `.pdf` | Apple-Health-derived sleep/circadian recommendations |
| `MEAL_PLAN.md` / `.pdf` | 7-day Dutch-context rotating menu |
| `SHOPPING_LIST.md` / `.pdf` | AH/Jumbo/Plus weekly grocery list |
| `NEXT_VISIT_PREP.md` / `.pdf` | Consolidated questions for next Erasmus MC visit |

Per-domain "draft" and "critique" markdowns (`reports/domains/*.draft.md`, `*.critique.md`) are kept as the audit trail of the multi-agent synthesis — useful if you want to see what the reviewer caught.

---

## 8a. Pipeline script catalog

| Script | Phase | Role |
|---|---|---|
| `_paths.py` | shared | `paths_for(user)` + `add_user_arg(parser)` + family-history helpers |
| `_pl_screen_core.py` | shared | Gene panels + gnomAD lookup + classification + markdown render |
| `01_normalize.py` / `01_verify.py` | 1 | snps lib → GRCh38 VCF; cross-check v0 |
| `02_opencravat.sh` / `02_verify.py` | 2 | 18-annotator OpenCRAVAT run |
| `03_pharmcat.sh` / `03_verify.py` | 3 | PharmCAT 3.2.0 clinical PGx |
| `04_pl_screen.py` | 4 | Chip P/LP screen (38-line entry point) |
| `04b_pl_screen_topmed.py` | 4b | TOPMed-imputed P/LP screen (36-line entry point) |
| `05_extract_bloods.py` | 5 | docx blood tables → structured JSON |
| `05_pgs_compute.py` | 5 | PGS Catalog scoring (with VCF-size auto-fallback guard) |
| `05_pgs_report.py` | 5 | Render trait-percentile markdown (chip or TOPMed) |
| `06_bundle.py` | 6 | 5 core domains (cardiovascular/metabolic/methylation/pharmacogenomics/hereditary_cancer) bundles |
| `06b_bundle_new_domains.py` | 6 | 9 wellness-domain bundles |
| `06c_nutrigenomic_topmed_delta.py` | 6c | TOPMed vs chip delta on 200-gene nutrigenomic panel (chunked TSV load) |
| `06d_v1_v2_diff.py` | 6d | Auto v1→v2 transition page |
| `06e_dashboard.py` | 6e | Auto 1-page "numbers at a glance" |
| `06f_wellness_overview.py` | 6f | Auto consolidated wellness-domain index |
| `06g_data_inventory.py` | 6g | Per-user data-inventory page (instance of `CAPABILITY_MATRIX.md`) |
| `06h_wearable.py` | 6h | Chronotype + wearable-insights reports from the parsed Apple Health export |
| `06i_cgm_analysis.py` | 6i | CGM metrics + DNA×bloods×CGM integration; emits report, `cgm.json`, AGP chart |
| `07_prepare_prompts.py` / `07_synthesize.py` | 7 | LLM prompt assembly + multi-agent synthesis orchestration |
| `08_build_pdfs.sh` | 8 | pandoc + weasyprint, with `build_bundle()` + `render_single()` helpers |
| `impute_topmed.sh` | imputation | Per-user TOPMed prep + submit (with token preflight + chr-prefix detection) |
| `topmed_monitor.sh` | imputation | Poll TIS API every 5 min until terminal state |
| `topmed_postprocess.sh` | imputation | Download + decrypt (with password validation) + concat + R² filter |
| `local_imputation_run.sh` | imputation | Beagle 5.5 per-chromosome pipeline |
| `local_imputation_liftover.py` | imputation | pyliftover-based GRCh38 ↔ GRCh37 (header-race fix shipped 2026-05-10) |
| `impute_family_member.sh` | imputation | End-to-end wrapper for onboarding a new person |
| `parse_apple_health.py` | wearable | Apple Health `export.xml` → structured JSON (streamed, never DOM-parsed); also extracts Dexcom/CGM glucose → `parsed/glucose.json` |
| `healthlake/00–04 + run_all.py` | healthlake | Document data-lake pipeline — see §8c |
| `verify_all.sh` | QA | Forbidden-string + PDF + data-inventory + CGM-report + staleness + profile check per user |

Note: a number of root-level `analyze_*.py` / `compute_hr_nadir_cosinor.py` / `make_*_charts.py` scripts (~3,000 lines) are **one-off circadian/chronotype research scripts**, not part of the numbered pipeline. They produced Ruslan's chronotype and HR-nadir charts; Phase 6h is the consolidated, user-aware successor and should be preferred for new work.

## 8b. Clinical-WES track (Veronika)

A fourth user, **Veronika** (`users/verinika/` + working dir `users/Verona/`), is **not** on the consumer-genomics pipeline. The input is a clinical whole-exome sequence from 3billion — paired-end FASTQ (~18 GB each), a vendor `.final.vcf.gz`, and a heavily-filtered annotation Excel — plus a clinical Synevo blood panel as PDF. The question is a single paediatric diagnosis, not a wellness report.

**Workflow (ad-hoc, in `users/Verona/align/`):**
1. **Re-align from FASTQ** — `bwa mem` against a chr-prefixed GRCh38, `samtools sort` → `EPB26-HODU.sorted.bam`. The vendor VCF cannot be trusted as a complete panel screen (its annotation Excel is ~10 % of the VCF; capture-kit coverage failures must be checked explicitly with `samtools depth`).
2. **Targeted gene-panel re-call** — `build_target_bed.py` / `build_panel_bed_refgene.py` build a BED over the genes of interest (the 9 Aicardi-Goutières genes); `bcftools call` re-genotypes inside that region (`recall_*.vcf.gz`).
3. **Read-based phasing** — `phase_*.py` scripts establish whether candidate variants sit in *cis* or *trans* directly from read pairs spanning both positions, plus variant-allele-fraction (VAF) cluster analysis.
4. **Hypothesis write-up** — `Veronika_AGS9_Hypothesis_v2.md` (+ EN/UA `.docx`): a biallelic RNU7-1 disruption hypothesis (AGS9), one Likely-Pathogenic 8 bp deletion in *trans* to a regulatory-cluster second hit, with a recommended clinical pathway (interferon signature panel, parental phasing, long-read WGS).

**Why it is a separate track:** different input format, different reference handling (chr-prefixed FASTA, capture-kit coverage QC), no PGS / PharmCAT / bundle / multi-agent-synthesis stages, and no `profile.json` / `reports/` contract — so `verify_all.sh` skips it. It reuses the project's tooling philosophy (open tools, full reproducibility, no black-box claims) but none of the numbered phases. If clinical-WES becomes recurring, this track is the candidate to formalise into its own numbered pipeline.

## 8c. Healthlake — document data lake

`pipeline/healthlake/` is an MVP for turning a user's pile of raw medical files (blood-test PDFs, historical attachments, imaging reports, questionnaires) into AI-ready, **traceable** structured data. Design rationale is in `DATA_ARCHITECTURE_RECOMMENDATION.md`; it is currently populated for **Ruslan only** (`users/ruslan/healthlake/`).

Four layers, bronze → gold:

| Layer | Contents | Built by |
|---|---|---|
| `manifest/` | `files.csv` (one sha256-backed row per source file), `documents.csv` (grouped clinical documents), `duplicates.csv` | `00_manifest.py` |
| `bronze/` | extracted text sidecars (`text/*.txt`) + `document_text.csv` (extractor / status / confidence per file) | `01_extract_documents.py` |
| `silver/` | canonical fact tables (`observations.csv`, `lab_results.csv`, `provenance.csv`) + `review_queue.csv` for unresolved items | `02_build_observations.py` |
| `exports/fhir/` | FHIR NDJSON: `Patient`, `DocumentReference`, `Observation`, `DiagnosticReport`, `Provenance` | `03_export_fhir.py` |
| `gold/` | model-ready views for LLMs / dashboards / Obsidian | `04_build_gold_views.py` |

Run the whole thing with `python3 pipeline/healthlake/run_all.py --user <name>` (`--force-extract` re-runs text extraction). The core unit is an **observation row** with full provenance down to source file / page / locator and an extraction-confidence score — Obsidian is treated as a generated reading layer, never the canonical store. It is not yet wired into the numbered pipeline or the bundles; it is the foundation for the eventual stateful daily-advice agent (§13).

## 9. File system structure

Since the multi-user refactor, **all per-user data lives under `users/<name>/`** — there is no top-level `data/` directory any more. `pipeline/_paths.py` is the single source of truth (see the "Multi-user layout" section near the top for the resolver contract).

```
HeathProject/
├── ARCHITECTURE.md                      ← THIS FILE
├── ARCHITECTURE.pdf                     rendered copy (rebuild after editing this file)
├── spec.md                              project plan / decisions
├── DATA_ARCHITECTURE_RECOMMENDATION.md  healthlake design rationale
├── EXTRACTION_PROMPT.md                 prompt template for medical-document extraction
├── .env / .topmed_password              secrets (TOPMED_API_TOKEN etc.; gitignored)
│
├── users/<name>/                        ← per-user namespace (resolved by _paths.py)
│   ├── profile.json                     name, sex, age, anthropometric, family hx,
│   │                                    data_provenance, key findings, tier_a_actions
│   ├── dna/
│   │   ├── raw/                         vendor chip CSV
│   │   ├── normalized/                  Phase 1: my_dna_grch38.vcf.gz (GRCh38 VCF)
│   │   ├── imputation_input/            chr-split / padded / v4.2 staging for TOPMed + Beagle
│   │   ├── imputed_local/               Beagle output (all_imputed_b38*.vcf.gz + per-chrom)
│   │   ├── topmed/topmed_user/          TOPMed: all_topmed_imputed.vcf.gz (full, PGS)
│   │   │                                + all_topmed_r2_08.vcf.gz (R²≥0.8, clinical-grade)
│   │   ├── annotated/                   Phase 2: OpenCRAVAT TSV (chip)
│   │   ├── annotated_imputed/           Phase 2 re-run on Beagle-imputed
│   │   └── annotated_topmed/            Phase 2 re-run on TOPMed-imputed
│   ├── bloods/                          Phase 5: structured blood JSON + screenshots
│   ├── wearables/
│   │   ├── apple_export/                raw Apple Health export (export.xml, ECGs, GPX)
│   │   └── parsed/                      parse_apple_health.py output; glucose.json = CGM
│   ├── healthlake/                      document data lake — bronze/silver/gold + FHIR (§8c)
│   ├── bundles/                         Phase 6: 14 domain JSONs + integrated.json + cgm.json
│   └── reports/
│       ├── domains/                     per-domain draft/critique/final markdowns + PDFs
│       └── *.md / *.pdf / *.png         all v1 + v2 + traceability outputs (see §8)
│
├── shared/                              ← cross-user reference data + reference panels
│   ├── CAPABILITY_MATRIX.md             static "data layer → unlocked reports" matrix
│   ├── snippets/                        canonical report fragments
│   ├── prompts/                         Phase 7 system + per-domain synthesis prompts
│   ├── pgs_cache/  gnomad_cache.json  _1kg_cache/
│   ├── pharmcat/                        PharmCAT 3.2.0 jar + reference data
│   ├── beagle/                          Beagle 5.5 jar + 1000G b37 reference panel
│   ├── fasta/                           GRCh38 + GRCh37 reference genomes
│   └── liftover/                        UCSC hg38↔hg19 chain files
│
└── pipeline/                            all executable scripts (see §8a catalog)
    ├── _paths.py  _pl_screen_core.py    shared modules
    ├── 01_…08_*                         the numbered phases
    ├── 06g/06h/06i_*                    data-inventory, wearable, CGM phases
    ├── parse_apple_health.py            wearable + CGM extraction
    ├── impute_*.sh  topmed_*.sh  local_imputation_*   imputation
    ├── healthlake/                      00–04 + run_all.py — document data lake
    └── verify_all.sh                    cross-user QA
```

---

## 10. How to run / re-run pieces

Every script takes `--user <name>` (Python) or `$1` / `$HEATH_USER` (shell). Set
`export HEATH_USER=olga` to make every command default to her.

```bash
# Full pipeline from scratch (chip → all reports), takes ~half a day
python3 pipeline/01_normalize.py --user ruslan        # Phase 1
bash    pipeline/02_opencravat.sh ruslan               # Phase 2 (~3 min)
bash    pipeline/03_pharmcat.sh   ruslan               # Phase 3 (~3 min)
python3 pipeline/04_pl_screen.py --user ruslan         # Phase 4
python3 pipeline/05_extract_bloods.py --user ruslan    # Phase 5
python3 pipeline/06_bundle.py --user ruslan            # Phase 6 — 5 core domains
python3 pipeline/06b_bundle_new_domains.py --user ruslan  #          9 wellness domains
# Phase 7: spawn subagents via Claude Code (interactive, in the chat)
bash    pipeline/08_build_pdfs.sh ruslan                # Phase 8 (markdown → PDF)

# After a TOPMed run: re-screen, re-score, regenerate the auto pages
python3 pipeline/04b_pl_screen_topmed.py --user ruslan
python3 pipeline/05_pgs_compute.py --user ruslan --use-topmed
python3 pipeline/05_pgs_report.py  --user ruslan --use-topmed
python3 pipeline/06d_v1_v2_diff.py --user ruslan       # v1→v2 transition page
python3 pipeline/06e_dashboard.py  --user ruslan       # numbers-at-a-glance
python3 pipeline/06f_wellness_overview.py --user ruslan
python3 pipeline/06g_data_inventory.py --user ruslan   # traceability page

# Wearable + CGM (only does anything if a parsed export exists)
python3 pipeline/parse_apple_health.py --user ruslan   # export.xml → parsed/*.json
python3 pipeline/06h_wearable.py --user ruslan         # chronotype + insights
python3 pipeline/06i_cgm_analysis.py --user ruslan     # CGM metrics + AGP chart

# Document data lake (Ruslan)
python3 pipeline/healthlake/run_all.py --user ruslan

# QA all users; rebuild this doc's PDF after editing it
bash pipeline/verify_all.sh
DYLD_LIBRARY_PATH=/opt/homebrew/lib bash pipeline/08_build_pdfs.sh ruslan

# Image a family member (parents, brother, etc.) end-to-end
bash pipeline/impute_family_member.sh ~/Downloads/father_dna.csv father
```

---

## 11. Key non-obvious decisions

These cost time to figure out and would be lost without writing them down.

| Decision | Why |
|---|---|
| Skip imputation in v1; do chip-only first | Wanted a "baseline" deliverable before adding complexity. v0 report (the docx) was already chip-only and incorrect; v1 needed to fix v0 first, then v2 expands. |
| OpenCRAVAT instead of writing own annotation pipeline | OpenCRAVAT already integrates 18 databases consistently. Building from scratch = months. |
| PharmCAT instead of OpenCRAVAT's pharmgkb module | OpenCRAVAT's pharmgkb module had a code bug; PharmCAT is the FDA-cited gold standard anyway. |
| Multi-agent LLM (synth → reviewer → reconciler) instead of single-pass | Single-pass had measurable overreach; reviewer caught dozens of bad effect-size claims. Quality > token cost. |
| Subagents (via Claude Code Agent tool) instead of direct Anthropic API | User's Claude subscription covers it; no API-key management, no extra billing. |
| Try TOPMed first, Beagle as fallback | TOPMed quality > Beagle quality (80× larger panel). Always try TOPMed first; fall back if their cluster is down. |
| Pad with 19 1000G EUR samples | TOPMed's 20-sample minimum is hard policy. Public 1000G samples work fine as fillers. |
| Drop chrX from imputation submission | Mixed-sex cohort breaks chrX QC. Acceptable since chrX has only ~5% of clinically actionable variants on this chip. Future improvement: pad with same-sex samples. |
| Weasyprint instead of LaTeX for PDFs | Weasyprint is one pip-install + one brew install. LaTeX requires multi-GB texlive distribution. |
| Memory entries for every key finding (e.g., APOE ε3/ε3) | Persists across sessions. Without memory, each new chat starts cold. |

---

## 12. Glossary

| Term | Plain English |
|---|---|
| **Variant / SNP** | A position in your DNA where you have a different letter than the reference human genome. SNP = "Single Nucleotide Polymorphism" = one-letter change. |
| **Genotype** | The two letters you have at a given position (one from each parent). |
| **Allele** | One of the possible letters at a position. The "reference allele" is what most people have; "alternate allele(s)" are variants. |
| **Heterozygous (het)** | You have two different alleles at a position (e.g., one A, one G). |
| **Homozygous (hom)** | You have two of the same allele (e.g., two As). |
| **VCF** | Variant Call Format — the standard file type for storing DNA variants. Tab-separated, one variant per row. |
| **Imputation** | Statistically guessing what's at DNA positions you didn't directly measure, by comparing to people who were fully sequenced. |
| **Reference panel** | The set of fully-sequenced people used as the basis for imputation. Bigger = better guesses. |
| **R² (DR2)** | "How confident is the imputation?" Range 0–1. ≥0.3 = usable for population-level analysis; ≥0.8 = clinical-grade. |
| **GRCh38 / hg38** | The current standard "human reference genome" coordinates. GRCh37/hg19 was the previous standard (still used by some old tools). |
| **PGS / PRS** | Polygenic (Risk) Score — a sum of weighted alleles across many variants, used to predict a trait or disease risk. |
| **P/LP** | "Pathogenic / Likely-Pathogenic" — ClinVar's two strongest categories for "this variant causes disease." |
| **ClinVar / OpenCRAVAT / PharmCAT / gnomAD** | See §7. The four most-referenced public databases / tools in this project. |
| **CYP, MTHFR, APOE, BRCA1/2, etc.** | Specific genes. CYP = cytochrome P450 family (drug metabolism). MTHFR = folate metabolism. APOE = lipid + Alzheimer's. BRCA1/2 = breast/ovarian/prostate cancer susceptibility. |
| **CPIC / DPWG** | Pharmacogenomics guideline-issuing bodies (US/international and Dutch respectively). PharmCAT outputs follow their guidelines. |
| **Liftover** | Converting variant positions from one reference genome version to another (e.g., GRCh37 → GRCh38). |

---

## 13. What's next (project roadmap, as of 2026-05-21)

| When | What | Notes |
|---|---|---|
| ✅ DONE | Multi-user layout | Ruslan + Olga + Sergii on the same `users/<name>/` structure |
| ✅ DONE | Three users with full report sets | v1 + v2 (TOPMed) where applicable |
| ✅ DONE | TOPMed + Beagle for all three | Sergii's chip P/LP triple-validated (chip → Beagle → TOPMed all refute) |
| ✅ DONE | chrX same-sex padding | `impute_topmed.sh` accepts `include-male` / `include-female` / `skip` chrX mode |
| ✅ DONE | Pipeline-wide robustness guards | Token preflight, password validation, PGS size guard, chunked TSV load |
| ✅ DONE | Cross-user-leak guard | `verify_all.sh` enforces every per-user report stands alone |
| ✅ DONE | CSS visual tier + auto v2 bundle | tier-a/b/c colour coding, badges, caveat callouts, bottom-line boxes, auto v2_full.pdf |
| ✅ DONE | v1→v2 transition + dashboard + wellness overview | Auto-generated by `06d` / `06e` / `06f` |
| ✅ DONE | Capability matrix + per-user data inventory | `shared/CAPABILITY_MATRIX.md` + `06g` traceability page, enforced by `verify_all.sh` |
| ✅ DONE | Wearable integration | `parse_apple_health.py` + `06h` — behavioural chronotype now supersedes the genetic GRS313 score |
| ✅ DONE | CGM analysis | `06i` — Dexcom G7 glucose → TIR / GMI / MAGE + DNA×bloods×CGM integration |
| ✅ DONE | Clinical-WES track (Veronika) | Exome FASTQ → re-align → AGS gene-panel screen → read-based phasing (§8b) |
| ✅ DONE (MVP) | Healthlake document data lake | `pipeline/healthlake/` — bronze→gold + FHIR; Ruslan only, not yet wired into bundles (§8c) |
| **Next** | Decide what to upgrade — possible directions: | |
| 📐 designed | **Concierge product layer** — funnel → weekly plan → book/order/calendar | Full design in [`PRODUCT_ARCHITECTURE.md`](./PRODUCT_ARCHITECTURE.md). Subsumes the two candidates below (daily-advice agent + web frontend) into one product. MVP = Whoop + Google Calendar live, rest as one-tap hand-offs. |
| candidate | Daily-advice agent that fuses genetics + wearable + blood + CGM + lifestyle over time | The long-term goal; healthlake's canonical observation store is the foundation it needs. Now the Recommendation Engine in `PRODUCT_ARCHITECTURE.md` §7. |
| candidate | Wire healthlake into the pipeline | Extend it to all users; feed its `silver/` facts into the Phase 6 bundles instead of one-off blood extraction |
| candidate | WGS upgrade (~€300-500) | Biggest long-term quality lever — replaces imputation for high-impact disease screens |
| candidate | Formalise the clinical-WES track | If WES recurs, turn the `users/Verona/align/` ad-hoc scripts into a numbered pipeline |
| candidate | Family-member onboarding via `impute_family_member.sh` | The wrapper exists; needs raw chip data for parents/brother |
| candidate | Tighter UX layer: web frontend or interactive dashboard | Currently all output is PDF; an HTML/web layer could surface "Numbers at a Glance" interactively |
| candidate | LLM-synthesis layer upgrade (Phase 7) | Multi-agent flow exists but is run interactively via Claude Code; could be scripted via Anthropic API |
| candidate | Live PGx-prescription checker | Sit on top of PharmCAT JSON output; respond to "I was just prescribed X" with a per-drug check |
