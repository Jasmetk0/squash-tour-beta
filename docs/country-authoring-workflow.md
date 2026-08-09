# Country authoring workflow

Countries are authored only inside an explicit World Package. See [World Package filesystem storage](world-package-storage.md) for the canonical directory contract.

Built-in packages are read-only application inputs. To edit countries, first clone Official FAX World to `config/world_packages/custom/<world_id>/`, then use the package-scoped Admin country operations or the tabular helper with an explicit package root:

```bash
python scripts/countries_tabular_tool.py export-csv \
  --package-root config/world_packages/custom/example_world \
  --csv /tmp/example-world-countries.csv
python scripts/countries_tabular_tool.py import-csv \
  --package-root config/world_packages/custom/example_world \
  --csv /tmp/example-world-countries.csv
```

CSV import is materialized as `countries/index.json` plus one identity and one file per supported attribute for every country. There is no aggregate country JSON source and no implicit package selection.
