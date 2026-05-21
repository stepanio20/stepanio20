# dna/raw/

**Put your raw DNA file here.** This is the CSV (or zipped CSV) downloaded from
your consumer-DNA service — *not* a PDF report.

Supported sources (all auto-detected by the `snps` Python library):

| Vendor | Typical filename | Build |
|---|---|---|
| MyHeritage | `MyHeritage_raw_dna_data.csv` | GRCh37 |
| 23andMe | `genome_<name>_v5_Full_<date>.txt` | GRCh37 |
| AncestryDNA | `AncestryDNA.txt` (inside the zip) | GRCh37 |
| FTDNA | `<kit>-FTDNA-Autosomal-2022.csv` | GRCh37 |

How to download (varies by vendor — current as of 2026):

- **MyHeritage**: Account → DNA → Manage DNA Kits → ⋯ → Download raw data
- **23andMe**: Account → Browse Raw Data → Download
- **AncestryDNA**: Settings → Download Raw DNA Data
- **FTDNA**: myFTDNA → Family Finder → Data Download → Build 37 Raw Data

After download:
1. If it's a zip, unzip it.
2. Drop the resulting `.csv` / `.txt` into this directory.
3. Run Phase 1: `python3 pipeline/01_normalize.py --user me`

The contents of this folder are **gitignored** — your raw DNA file is highly
personal and never committed.
