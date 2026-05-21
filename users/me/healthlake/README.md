# healthlake/

Personal medical-document data lake (see [`../../../ARCHITECTURE.md`](../../../ARCHITECTURE.md) §8c).
Built by `pipeline/healthlake/run_all.py --user me`.

Layers (bronze → gold):

| Layer | Contents | Built by |
|---|---|---|
| `manifest/` | `files.csv` (one sha256-backed row per source file), `documents.csv`, `duplicates.csv` | `00_manifest.py` |
| `bronze/` | extracted text sidecars (`text/*.txt`) + `document_text.csv` | `01_extract_documents.py` |
| `silver/` | canonical fact tables: `observations.csv`, `lab_results.csv`, `provenance.csv`, `review_queue.csv` | `02_build_observations.py` |
| `exports/fhir/` | FHIR NDJSON: `Patient`, `DocumentReference`, `Observation`, `DiagnosticReport`, `Provenance` | `03_export_fhir.py` |
| `gold/` | model-ready views for LLMs / dashboards / Obsidian | `04_build_gold_views.py` |

Inputs come from `users/me/bloods/` (PDFs / Excels / scans) and any other medical
documents you drop in. The core unit is an **observation row** with full
provenance — source file + page + locator + extraction-confidence score.

All contents of this folder are **gitignored** — same reasoning as `bloods/`.
