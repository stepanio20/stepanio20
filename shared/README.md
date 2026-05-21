# shared/

Cross-user reference data — public databases, tool JARs, reference panels. Never
per-user. All contents are **gitignored** (large, re-downloadable, public).

Expected layout:

```
shared/
├── snippets/        ← canonical report fragments (caveat_bloods.md, chip_refutation.md, data_gaps.md)
├── prompts/         ← Phase 7 LLM synthesis prompts (system + per-domain)
├── pgs_cache/       ← PGS Catalog scoring files (~per-trait, cached on demand)
├── pharmcat/        ← PharmCAT 3.2.0 JAR + reference data
├── beagle/          ← Beagle 5.5 JAR + b37.bref3 1000G reference panel (~1.5 GB)
├── fasta/           ← GRCh38 + GRCh37 primary assembly FASTAs (~6 GB)
└── liftover/        ← UCSC hg38↔hg19 chain files (~10 MB)
```

Two files in `shared/` are tracked in git when they exist, because they're
project-level rather than reference dumps:

- `shared/CAPABILITY_MATRIX.md` — static "data layer → unlocked reports" table
- `shared/snippets/*.md` — canonical report fragments (kept under version control
  so reports can reference them by path)

The download/setup step is TBD: a future `pipeline/setup_shared.sh` will fetch
everything listed above into the right subdirectory.
