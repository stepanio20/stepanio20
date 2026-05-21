# Personal Genomics & Health Pipeline

A personal instance of the architecture described in [`ARCHITECTURE.md`](./ARCHITECTURE.md) —
an open-source pipeline that turns raw consumer-DNA data, blood panels, wearable
exports, and other personal health data into structured reports and recommendations.

## Status

**New repo, scaffolding only.** Directory layout is in place; pipeline code and
your own data go in next. See [`NEXT_STEPS.md`](./NEXT_STEPS.md).

## What goes where

| Path | What it holds | In git? |
|---|---|---|
| `ARCHITECTURE.md` | Full design doc — read this first | yes |
| `NEXT_STEPS.md` | Onboarding checklist | yes |
| `users/me/profile.json` | Your demographics + family history (you fill in) | yes |
| `users/me/dna/raw/` | Raw DNA file from MyHeritage / 23andMe / Ancestry | **gitignored** |
| `users/me/dna/{normalized,imputed_*,annotated*,topmed}/` | Pipeline intermediates | **gitignored** |
| `users/me/bloods/` | Blood-test PDFs / screenshots | **gitignored** |
| `users/me/wearables/apple_export/` | Apple Health `export.xml` | **gitignored** |
| `users/me/wearables/parsed/` | Parsed wearable + CGM JSON | **gitignored** |
| `users/me/healthlake/` | Medical-document data lake (bronze→gold + FHIR) | **gitignored** |
| `users/me/bundles/` | Per-domain JSONs (LLM input) | **gitignored** |
| `users/me/reports/` | Generated markdown + PDF reports | **gitignored** |
| `shared/` | Reference panels (PharmCAT, Beagle, FASTA, …) | **gitignored** (re-downloadable) |
| `pipeline/` | Scripts (added phase by phase) | yes |

## Privacy

Everything personal — raw DNA, blood-test source files, Apple Health exports,
generated reports, and the medical-document data lake — is gitignored. Only the
directory scaffolding (READMEs + `.gitkeep` markers), the `profile.json` template,
the architecture doc, and pipeline source code are tracked in git.

Secrets (`.env`, `.topmed_password`) are also gitignored.

## Start here

1. Read [`ARCHITECTURE.md`](./ARCHITECTURE.md) — at least §1, §2, §3 and §4.
2. Walk through [`NEXT_STEPS.md`](./NEXT_STEPS.md) — onboarding checklist.
3. Fill in [`users/me/profile.json`](./users/me/profile.json).
