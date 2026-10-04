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

A third canonical family stores structural football events as source-specific datasets. The review seed contains **43 events across 25 datasets** for the nine-country calibration review set; a separate held-out validation seed adds **14 events across 7 datasets** for Germany, Brazil, Iceland and San Marino. These observations cover federation/league foundations, professionalisation, training centres, academy/youth-pathway launches, infrastructure milestones and governance discontinuities. They use `collection_method=official_narrative`, preserve original event years (including pre-1955 history), and encode dimension relevance only as quality flags such as `supports_development_quality` or `supports_squash_tradition`. They never encode a rating or effect size.

The Mohammed VI Academy timing conflict is intentionally stored twice (2009 establishment vs 2019 opening) under one conflict group rather than being silently reconciled.

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
view. It now partitions **1,328 canonical observations**: Big Count/Professional facts still use the reviewed identity-resolution layer, while structural events may enter directly only when the normalized observation carries the explicit `explicit_reviewed_event_to_earth` mapping. The result is 1,306 safe facts, 22 manual-review facts and zero unresolved facts. Aggregate-member observations are kept as components rather than silently summed, and the index is explicitly `rating_ready=false`.

See [the implementation/research boundary](../../docs/EARTH_SPORT_HISTORY_V1.md)
for source limitations, provenance rules, audit/build commands and next steps.


## Structural dimension evidence summary

`scripts/build_fifa_structural_dimension_evidence.py` projects canonical structural
events into a read-only 250-country view for `development_quality` and
`squash_tradition`.

The summary reports event timelines, first/last evidence year, pre-1955 history,
conflict groups and exact observation IDs. Event counts are explicitly documentation
coverage only: more events never imply a better football environment, and countries
without seeded structural events remain unknown rather than receiving a zero score.

Across both seeds, the structural summary contains 23 development-relevant and 25 tradition-relevant event references. Review and held-out counts remain separate; held-out events are explicitly forbidden as model-fit inputs. The Morocco academy timing conflict remains visible in the summary.
