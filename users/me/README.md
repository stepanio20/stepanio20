# users/me/

Your personal namespace. The `me` user is the placeholder name for "you" — rename
the directory + update `_paths.py` once you have pipeline scripts in place.

Layout:

```
me/
├── profile.json          ← about you (you edit by hand)
├── dna/
│   ├── raw/              ← put the vendor CSV here
│   ├── normalized/       ← Phase 1 output (GRCh38 VCF)
│   ├── imputation_input/ ← TOPMed + Beagle staging
│   ├── imputed_local/    ← Beagle output
│   ├── topmed/           ← TOPMed output
│   ├── annotated/        ← Phase 2 output (chip)
│   ├── annotated_imputed/← Phase 2 re-run on Beagle-imputed
│   └── annotated_topmed/ ← Phase 2 re-run on TOPMed-imputed
├── bloods/               ← lab PDFs / Excels / scans
├── wearables/
│   ├── apple_export/     ← raw Apple Health export
│   └── parsed/           ← parsed JSON (sleep, HR, CGM…)
├── healthlake/           ← medical-document data lake
│   ├── manifest/         ← file inventory
│   ├── bronze/           ← extracted text
│   ├── silver/           ← canonical observations
│   ├── gold/             ← model-ready views
│   └── exports/          ← FHIR NDJSON
├── bundles/              ← 14 domain JSONs (Phase 6)
└── reports/              ← markdown + PDF deliverables
    └── domains/          ← per-domain draft / critique / final
```

Everything except `profile.json` and per-folder READMEs is gitignored — see
`/.gitignore` at the repo root.
