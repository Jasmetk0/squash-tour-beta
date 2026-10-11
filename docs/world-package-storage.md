# World Package filesystem storage

`config/world_packages/` is the only production root for World Package source data. Built-ins are stored at `official_fax_world/` and `real_world/`; editable clones are stored below `custom/<world_id>/`. The application does not scan or fall back to legacy world paths.

Each package contains:

```text
world.json
countries/
  index.json
  <CODE>/
    country.json
    attributes/
      population.json
      area_km2.json
      region.json
      travel_region.json
      wealth_support.json
      squash_popularity.json
      squash_tradition.json
      system_quality.json
      competition_density.json
      federation_quality.json
      court_count.json
      style_dna.json
geography/
  continents.json
  regions.json
  travel_regions.json
```

`world.json` carries semantic package metadata plus `package_format_version`. `countries/index.json` is the deterministic membership registry and contains stable, uppercase, three-letter codes only. A country's directory name is its identity; display-name changes do not rename it.

`country.json` contains identity and descriptive metadata (`code`, `name`, `flag_asset`, and `notes`). Every supported simulation attribute has its own typed `{schema_version, value}` file. To add a domain attribute, add it to the typed `Country` model, the storage adapter's required attribute list, validation, and every country that supports it; do not create speculative empty attributes.

Population uses `{schema_version, default_year, values_by_year}`. The adapter materializes the domain's compatible `population`, `default_population`, `default_population_year`, and `population_by_year` fields from that one timeline source.

Geography registries live under `geography/`, and validation checks country region and Travel Region references. Built-in packages are application-read-only; custom packages use staged directory replacement and atomic JSON writes. There is no aggregate `countries.json` and no legacy filesystem fallback.
