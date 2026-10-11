# Actual production initial-population evidence

See [procedure and interpretation](../../EARTH_INITIAL_POPULATION_COMPARISON.md).

- [Compact measurements](measured-results.json): exact engine/source and package
  fingerprints, ten real 1000-player runs, pooled numeric summaries and all
  250 per-seed country counts. No raw population rows are committed.
- [First browser run](first-browser-evidence.json): actual UI generation of two
  32-player populations, JSON/CSV downloads, scope/metric/count checks, backend
  restart, fresh browser read and main measured session reopen without POST.
- [Repeat browser run](cached-browser-evidence.json): same configuration reused the
  persisted session after table spacing fixes; zero regeneration on restart/read.
- [Pooled results](pooled-results.png), [country comparison](country-comparison.png)
  and [actual players](actual-players.png) are screenshots taken by Chromium from
  the running existing frontend against production FastAPI/SQLite. No mock data or
  edited screenshots were used.

The main 10000-player experiment was run by the production service CLI; the browser
created the smaller sample and inspected the saved main experiment. Large raw JSON,
CSV, logs and disposable SQLite remain under `work/earth-population/production`.
