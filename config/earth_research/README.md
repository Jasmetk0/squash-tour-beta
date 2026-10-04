# Earth source research — incomplete

These are source catalogues and normalized/extracted observations, not usable World
Packages. Both `countries` maps remain empty. Do not fill missing research with
neutral scores or present modern surveys as measured history for 1955–2026.

The catalogues use `earth_sport_research.v2`. Populated rating evidence must cite
exact normalized observation IDs from registered, content-addressed
`earth_source_observations.v2` datasets.

## Canonical normalized observations

FIFA Big Count 2006 is the first canonical ingestion slice. Five datasets under
`observations/normalized/` preserve the checked-in 208-association source extract:

- all players — 208 observations;
- registered players — 208;
- unregistered players — 208;
- clubs — 206 because two source cells are missing and are not converted to zero;
- officials/staff — 208.

`fifa_earth.json` records semantic SHA-256 manifests for all five datasets.
`load_earth_research_bundle()` validates dataset identity, source, record count,
input-artifact hash and semantic hash before research can be audited/built.

FIFA Professional Football Report 2023 is the second canonical ingestion slice:
- men's professional players — 112 non-null national-page observations;
- professional clubs — 135 non-null national-page observations.

The two 2023 datasets preserve the source PDF SHA-256, page numbers, the mismatch
between extracted national sums and FIFA's published global headline, and the known
page-38 KUWAIT/Kyrgyzstan identity anomaly without silently reassigning it.

The Big Count normalization deliberately does **not**:
- invent country-level male/female splits missing from the checked-in extract;
- claim whether an individual cell was direct or statistically supplemented when
  that row-level flag is no longer present;
- treat registered-player, club or officials definitions as globally identical;
- map FIFA associations directly onto modern Earth geography. The reviewed identity
  reconciliation layer remains separate.

Other files directly under `observations/` are still raw/source-specific research
inputs until explicitly normalized. They must not be silently treated as comparable
measurements or referenced by new rating histories.

## Observation identity resolution

Canonical source facts remain association-level and are never rewritten in place.
`scripts/build_fifa_observation_identity_resolutions.py` deterministically derives
typed observation→Earth resolutions from the normalized datasets plus the reviewed
Big Count / Professional 2023 identity overrides. Each generated resolution set
binds the exact input dataset semantic hashes, override-artifact SHA-256 and Earth
identity catalogue SHA-256. Direct, aggregate-member, manual-review and unresolved
states are explicit; manual/unresolved facts never receive a resolved Earth code.

`scripts/build_fifa_country_evidence_index.py` is the next read-only calibration
view. It partitions every canonical FIFA observation exactly once: safe direct or
aggregate-member facts are indexed under their Earth code, while manual/unresolved
facts remain outside country evidence. Aggregate-member observations are kept as
components rather than silently summed, and the index is explicitly `rating_ready=false`.

See [the implementation/research boundary](../../docs/EARTH_SPORT_HISTORY_V1.md)
for source limitations, provenance rules, audit/build commands and next steps.


## Canonical structural-event evidence

FIFA Earth also contains canonical dated structural-event observations for reviewed
development/tradition context. These observations use
`measurement_type=football_structural_event`,
`collection_method=official_narrative`, and an explicit reviewed Earth mapping.

Current structural corpus:
- 43 review events across the nine-country calibration review set;
- 14 independently labelled held-out validation events for Germany, Brazil,
  Iceland and San Marino;
- 57 structural observations total;
- structural observations carry no numeric quality value.

`scripts/build_fifa_structural_dimension_evidence.py` exposes development/tradition
timelines without producing a score. Event count is documentation coverage, not
football quality. Countries with no seeded event remain unknown rather than zero.

Held-out events carry `held_out_validation_country` and must not be used to fit
transfer curves, weights or rating deltas. Morocco's conflicting 2009/2019 academy
timing remains an explicit unresolved source conflict rather than being collapsed.
