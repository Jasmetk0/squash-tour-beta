# Country data authoring workflow (temporary bridge)

## Current status

- `config/world/countries.json` is the **runtime canonical file** currently loaded by the backend.
- The content in that file is explicitly a **temporary seed/demo dataset** for development slices, not final world content.
- Primary authoring direction is now the **in-app Countries Editor** (`/world/countries`).

## Authoring direction

Final country data is intended to be **user-authored** (not hardcoded in Python logic).
Tabular CSV remains a secondary backup/bridge workflow.

## Tabular bridge format

CSV columns (flat and spreadsheet-friendly):

- `code`
- `name`
- `flag_asset`
- `region`
- `population`
- `wealth_support`
- `squash_popularity`
- `squash_tradition`
- `system_quality`

## Tooling bridge

Script: `scripts/countries_tabular_tool.py`

Export canonical JSON -> CSV:

```bash
PYTHONPATH=src python scripts/countries_tabular_tool.py export-csv \
  --json config/world/countries.json \
  --csv config/world/countries.seed.demo.csv
```

Import CSV -> canonical JSON:

```bash
PYTHONPATH=src python scripts/countries_tabular_tool.py import-csv \
  --csv path/to/your/countries.csv \
  --json config/world/countries.json
```

## Replacement path for your own dataset

1. Prepare your own spreadsheet/CSV with the required columns.
2. Run `import-csv` to produce canonical runtime JSON.
3. Run backend validation/tests.
4. Commit only the resulting canonical JSON (and optionally your source CSV if desired).

This keeps runtime deterministic and config-driven while enabling practical user-authoring now.
