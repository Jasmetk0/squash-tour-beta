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

See [the implementation/research boundary](../../docs/EARTH_SPORT_HISTORY_V1.md)
for source limitations, provenance rules, audit/build commands and next steps.
