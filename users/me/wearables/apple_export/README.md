# wearables/apple_export/

**Put your raw Apple Health export here.** The expected layout (after unzipping
the export Apple gives you):

```
apple_export/
├── export.xml                  ← the main file (can be 1-5 GB for multi-year users)
├── export_cda.xml              ← optional
├── electrocardiograms/         ← optional
├── workout-routes/             ← optional
└── ... other Apple-generated subfolders
```

How to produce one:

1. iPhone → Health app → tap your profile photo (top-right)
2. Scroll to "Export All Health Data" → tap → wait (5–20 min)
3. Share → AirDrop / save to Files / iCloud
4. Unzip on your computer; the unzipped folder usually called `apple_health_export/`
5. Move the **contents** (not the wrapping folder) into this directory.

What the pipeline does:

- `pipeline/parse_apple_health.py --user me` streams `export.xml` (never DOM-parses
  — it OOMs on multi-GB files) into structured JSON under
  `users/me/wearables/parsed/`: sleep, heart rate, HRV, VO2max, steps, workouts,
  weight, ECGs.
- If you wear a Dexcom or FreeStyle Libre CGM, the parser also extracts a
  `parsed/glucose.json` series, which Phase 6i turns into a TIR / GMI / MAGE
  CGM report.

The contents of this folder are **gitignored** — the export contains your
location traces, heart-rate history, sleep records and other deeply personal data.
