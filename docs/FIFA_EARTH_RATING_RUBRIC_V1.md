# FIFA Earth numeric calibration rubric v1

Status: **prototype calibration only**. This rubric is deliberately separate from the Master and from the canonical `config/earth_research/fifa_earth.json`.

The purpose is to make a 1–10 rating mean the same thing across countries and decades before scaling to all Earth countries.

## General scale discipline

- 1.0–2.9: very weak / highly limited environment for the dimension.
- 3.0–4.9: organised but limited, uneven or institutionally shallow.
- 5.0–6.4: established national environment with meaningful structures.
- 6.5–7.9: strong environment with broad or high-quality structures.
- 8.0–8.9: internationally strong / deeply embedded / highly developed.
- 9.0–9.7: world-leading environment for the dimension.
- 9.8–10.0: exceptional historical benchmark; intentionally rare.

Anchor estimates should usually use 0.5-ish granularity. Tenths are primarily useful for deterministic annual interpolation and calibrated comparisons. A decimal is **not** a claim of measurement precision.

## Attribute-specific meaning

### `squash_popularity` — football popularity

Measures football's social/cultural penetration and relative importance inside the country.

Strong evidence:
- participation intensity after population normalisation;
- contemporary audience/cultural evidence;
- football's place among national sports;
- breadth of club/community engagement.

Do not:
- infer popularity directly from FIFA ranking;
- reward large absolute population/player totals without normalisation.

### `squash_access` — football access

Measures how feasible it is for a typical interested person to enter organised football.

Strong evidence:
- club/team/registration footprint;
- school/community pathways;
- geographic availability;
- facilities usable for participation;
- barriers created by geography, conflict, segregation or cost.

Do not:
- equate elite academies with mass access;
- punish small population by itself.

### `development_quality`

Measures systematic ability to develop players from youth participation toward higher levels.

Strong evidence:
- coach education;
- youth leagues;
- academies and talent centres;
- structured age-group pathways;
- repeated contemporaneous youth-development outputs.

Do not:
- use a later senior career to upgrade the environment that existed when the player was a child;
- treat one exceptional player as proof of a strong pipeline.

### `competition_quality`

Measures depth and quality of domestic competitive football and the level of meaningful opposition.

Strong evidence:
- league depth and professionalism;
- domestic competitive structure;
- club strength;
- national-team and club results as outcome evidence;
- depth of high-level players.

Results/rankings belong primarily here.

### `elite_support`

Measures institutional and professional support for high-performance football.

Strong evidence:
- professional clubs and player employment;
- federation technical capacity;
- high-performance centres;
- licensing/governance capability;
- elite coaching/science/medical and national-team support.

Do not:
- convert a one-off stadium/event directly into a permanent maximum;
- use mass participation as a substitute.

### `squash_tradition` — football tradition

Measures duration, continuity and embedded historical football culture/institutions.

Strong evidence:
- age and continuity of organised competition;
- long-lived clubs/federations;
- recurring national competitions;
- historical cultural embeddedness.

Tradition is intentionally slow-moving. A country can have high tradition and modest current competition quality.

## Temporal rules

- Every prototype country has explicit anchors at 1955 and 2026.
- Exact anchor years use `method="sourced_estimate"`: the **rating** is still a project estimate, while the sources support the underlying historical context.
- Non-anchor years use deterministic linear interpolation rounded to one decimal.
- A documented split, merge, league collapse/relaunch, governance normalisation or comparable structural break requires an anchor; normal interpolation may not jump across an unmodelled break.
- 2026 uses evidence available by the dataset cutoff and is not described as a complete-year measurement.
- No future leakage is allowed.

## Confidence

Confidence applies to the **rating estimate**, not merely the credibility of the source.

- `high`: multiple strong independent observations map clearly to the dimension.
- `medium`: good structural evidence but the 1–10 conversion remains modelled.
- `low`: sparse, indirect or comparative evidence dominates.

Prototype annual interpolation inherits the weaker confidence of its enclosing anchors.

## Prototype safety

The reviewable numeric source lives in `config/earth_research/fifa_earth_prototype_anchors_v2.json` and is materialised on demand.

It is intentionally **not** the canonical FIFA Earth input. Passing schema validation or producing 72 annual values is not realism validation. Prototype values must survive cross-country, time-series and six-attribute plausibility checks before migration into `fifa_earth.json`.


## Calibration audit rule added after the first prototype

The first materialisation exposed an important failure mode: a superficially plausible country series can still behave like one hidden "football strength" score if all six attributes rise together.

Prototype review therefore adds transition-level coupling flags:

- Review any anchor-to-anchor interval where five or six attributes move by at least 0.4 points.
- Review any ordinary interpolation interval longer than 20 years; long gaps should normally gain an intermediate evidence anchor or remain explicitly low-confidence.
- A flagged interval is not automatically wrong. A genuinely systemic reform may affect many dimensions, but the rationale must explain each affected dimension.
- Long-run correlation is diagnostic only, not a rejection rule. Event-specific deltas matter more.
- `squash_tradition` should almost never jump sharply because of one tournament result.
- Competition results may justify `competition_quality` movement without forcing corresponding changes in popularity, access or elite support.

The v2 anchor prototype responds to the first audit:
- Japan's league, training-centre and professionalisation anchors affect different dimensions by different amounts.
- Morocco adds a 1986 checkpoint so 1960–2009 is not one undifferentiated interpolation span.
- Faroe Islands adds a 2010 checkpoint; the artificial-turf breakpoint is concentrated mainly in access/development.
- South Africa keeps high popularity/tradition during apartheid while international competition and elite support are disrupted.
- United States allows professional competition/elite support to fall after the NASL collapse while access/tradition evolve differently.
- India remains deliberately low-confidence after 1996 and is explicitly blocked from canonical migration until additional modern anchors are researched.

## Reproducible prototype

`config/earth_research/fifa_earth_prototype_anchors_v2.json` is now the review source for the prototype.

Run:

```sh
PYTHONPATH=src python scripts/materialize_fifa_earth_prototype.py
PYTHONPATH=src python scripts/materialize_fifa_earth_prototype.py --output /tmp/fifa-earth-prototype.json
PYTHONPATH=src python scripts/materialize_fifa_earth_prototype.py --strict
```

The first command prints audit flags. The second materialises all 72 years for all prototype countries into the existing `EarthSportResearch` / `CountryRatingHistory` schema. `--strict` deliberately exits non-zero while unresolved review flags remain.

No checked-in materialised snapshot is authoritative. The v2 anchors plus deterministic materialisation are the single review path, avoiding stale duplicate data.


### Second calibration pass

The reviewable v2 anchors now resolve every >20-year interpolation gap in the nine-country prototype. The coupling audit counts only **same-direction** multi-attribute movement; mixed transitions such as U.S. access growth alongside post-NASL competition decline are treated as evidence of attribute independence, not coupling.

Additional U.S. anchors now cover 1988, 1990, 1993, 2003, 2007 and 2018 using official U.S. Soccer evidence. Japan adds 1991 for the legal establishment of the J.League before the 1993 competition launch. These anchors replace broad linear assumptions with documented institutional/development events.

A clean transition audit means only that this nine-country prototype has no mechanical long-gap/coupling/tradition-jump flags. It does **not** make FIFA Earth canonical-ready: country coverage, held-out plausibility comparison, historical-entity prototypes and the full evidence review are still required.


## Cross-country 2006 calibration pass

The transition audit can be clean while countries are still miscalibrated relative to each other. FIFA Big Count 2006 is therefore used as a common held-out checkpoint for prototype countries.

Rules:
- use population-normalised all-player, registered-player and club density as evidence, never raw country totals alone;
- Big Count primarily calibrates `squash_popularity` and `squash_access`;
- it does not directly determine development, competition quality or elite support;
- small populations are not penalised by absolute scale;
- contextual barriers such as geography, inequality and cost may keep access below a pure registration-density ranking;
- cultural popularity remains distinct from participation volume.

The first pass exposed three under-calibrated access cases:
- Faroe Islands: extraordinary per-capita registration/club density requires near-top access after the artificial-turf era;
- Slovakia: very high registered-player and club density requires materially stronger access than the first prototype implied;
- Czechia: similarly dense organised-football footprint requires a strong access band.

South Africa is raised more moderately because high participation coexists with lower club density and persistent inequality/geographic barriers. USA remains strong in access but below the three densest prototype cases, while its popularity remains lower because soccer was not the dominant national spectator sport.

This comparative pass is a prototype check, not a universal formula. Full FIFA Earth calibration still requires association-to-Earth identity reconciliation and a global population-normalised benchmark across all usable Big Count rows.


## Canonical empirical signal layer

Before any canonical 1–10 rating conversion, FIFA Earth now derives separate
measurement-level calibration signals from normalized, identity-resolved evidence.

`scripts/build_fifa_country_calibration_signals.py` produces:

- 2006 all-player participation per 1,000 population;
- 2006 registered-player footprint per 1,000 population;
- 2006 reported clubs per million population;
- 2023 men's professional players per million population;
- 2023 professional clubs per million population.

Each observed signal preserves the exact source observation IDs, source value,
population denominator, empirical descending rank and ascending midrank percentile.
All 250 Earth countries are present in the output; unobserved or incomplete evidence
remains missing rather than becoming zero.

These percentiles are **not** game ratings and there is deliberately no
`percentile / 10` or equivalent conversion. The observed comparison set differs by
signal, source definitions have explicit limitations, and each signal maps only to
the dimensions it can reasonably inform. In particular, Big Count evidence primarily
informs popularity/access, while professional-player/club density is evidence for
competition/elite-support ecosystem depth. None directly determines development,
tradition, or a universal "football strength" score.

GBR is treated conservatively: Big Count 2006 can use the reviewed sum of four
non-overlapping home-association counts; Professional 2023 remains missing at GBR
level because Northern Ireland is missing in the source. Manual identity cases are
never admitted into these signals.


## Prototype-versus-signal diagnostic audit

`scripts/audit_fifa_prototype_against_signals.py` compares the nine-country
prototype against the canonical empirical signal layer at the signal observation
year.

The audit uses Spearman rank agreement only as a diagnostic. It also lists
pairwise review inversions when one prototype country is at least 25 percentile
points stronger on a measured signal but at least 0.5 rating points lower on the
relevant prototype attribute.

Neither condition is a rejection rule. A country rating may legitimately differ
from one signal because access, affordability, institutional context, source
coverage and other evidence matter. The audit exists to identify places that need
human review before any transfer curve is made canonical.

The audit never writes ratings, never changes anchors and remains
`rating_ready=false`.


## Provisional dimension evidence-score model

`config/earth_research/calibration/fifa_dimension_evidence_model_v1.json`
defines the first explicit 1–10 transfer model over the canonical empirical signal
layer. This is a **calibration aid**, not canonical country-rating authorship.

The percentile→evidence-score curve is monotone and piecewise linear:

| Percentile | Evidence score |
|---:|---:|
| 0 | 1.5 |
| 5 | 2.5 |
| 15 | 3.5 |
| 30 | 4.5 |
| 50 | 5.5 |
| 70 | 6.5 |
| 85 | 7.5 |
| 95 | 8.5 |
| 99 | 9.3 |
| 100 | 9.7 |

The curve deliberately does not use `percentile / 10`. It aligns empirical
relative strength with the existing qualitative 1–10 rubric while leaving room
below/above observed samples and keeping 10.0 exceptional rather than automatic.

Current recipes:

- `squash_popularity@2006`: 100% participation intensity;
- `squash_access@2006`: 65% registered-player intensity + 35% club footprint;
- `competition_quality@2023`: 65% professional-player density + 35% professional-club density;
- `elite_support@2023`: 45% professional-player density + 55% professional-club density.

All required components must exist. Missing remains missing. The current source
slice does not produce quantitative evidence scores for `development_quality` or
`squash_tradition`.

Every result from
`scripts/build_fifa_dimension_evidence_scores.py` is marked
`rating_ready=false`. A later canonical rating may use these scores only alongside
independent historical/context evidence with exact observation provenance.


## Evidence-score versus prototype audit

`scripts/audit_fifa_dimension_scores_against_prototype.py` compares the provisional
1–10 evidence scores with the nine-country prototype at the same attribute/year.

The audit reports:
- signed and absolute score/rating delta;
- mean and maximum absolute delta by recipe;
- exact prototype method/confidence/anchor years;
- exact source observation IDs behind each evidence-score component;
- a human-review flag when the absolute difference is at least 1.5 points.

The 1.5-point threshold is a review heuristic, not a pass/fail rule. A large
difference can be legitimate because the prototype includes contextual evidence
outside the current quantitative source slice. A small difference likewise does not
validate the model. The audit never writes a canonical or recommended rating.


## Dimension evidence-score versus prototype audit

`scripts/audit_fifa_dimension_scores_against_prototype.py` compares the provisional
1–10 evidence scores directly against the nine-country review prototype on the same
scale.

For each available country/recipe it records:

- provisional evidence score;
- prototype rating at the same evidence year;
- signed and absolute delta;
- prototype method, confidence and anchor years;
- the component signal percentiles and exact source observation IDs.

An absolute delta of **1.5 or more** is surfaced for human review. This is not an
automatic failure and never changes a rating. Large deltas may reflect missing
context in the quantitative model; small deltas do not validate the model.

Expected review samples remain intentionally incomplete where source evidence is
missing: nine countries for 2006 popularity/access and six countries for 2023
competition/elite-support. This audit is the explicit gate before any evidence-score
recipe can be considered for canonical rating authoring.


## Calibration model V2 — scale and density separation

The first 1–10 evidence-score model exposed a structural error rather than a small
weighting error.

Review artifact results for model V1:
- access@2006: mean absolute delta 0.70 versus the nine-country prototype;
- popularity@2006: mean absolute delta 1.49, with major misses for Japan, India,
  Morocco and Senegal and an overstatement for the USA;
- competition_quality@2023: mean absolute delta 2.68;
- elite_support@2023: mean absolute delta 2.92.

The professional failures came from using only per-capita density. That rewards
small countries with concentrated professional ecosystems and heavily penalises
large countries that can sustain substantial absolute professional leagues. Density
therefore cannot stand in for competition quality or elite support.

Model V2 introduces two additional canonical signals:
- absolute men's professional-player scale;
- absolute professional-club scale.

The corresponding professional recipes now make absolute scale dominant and retain
per-capita density only as secondary evidence.

Model V2 also removes the automatic popularity evidence-score recipe. Big Count
participation intensity is still useful empirical evidence, but it cannot by itself
represent football's cultural/social importance. The review set showed that this
single-signal conversion materially underestimates Japan, India, Morocco and Senegal
while overstating the USA. Popularity therefore returns to an unsupported
quantitative-rating state until independent audience/cultural evidence is normalized.

Access remains the strongest current quantitative candidate because registered-player
and club-density rankings align much more closely with the reviewed prototype.

All V2 results remain `rating_ready=false`.


## V2 quantitative review decision

The V2 scale-dominant professional recipes are now protected by a reproducible
V1→V2 review policy in
`config/earth_research/calibration/fifa_dimension_evidence_v2_review_policy.json`
and `scripts/review_fifa_dimension_evidence_v2.py`.

Measured nine-country prototype audit results:

| Recipe | V1 MAD | V2 MAD | V2 max delta | V2 review countries |
|---|---:|---:|---:|---|
| competition quality 2023 | 2.683 | 0.600 | 1.9 | ZAF |
| elite support 2023 | 2.917 | 0.983 | 2.5 | ZAF |
| access 2006 | 0.700 | 0.700 | 2.0 | IND, USA |

Competition quality therefore passes the current quantitative review gate, but
**not** canonical authoring. Elite support remains context-required because the
candidate is systematically below the review prototype and professional counts do
not measure federation funding, technical centres, medical/science provision or
travel/support capacity.

The review explicitly forbids further V2 weight tuning against this same prototype
set merely to improve fit. The next evidence step must be independent held-out or
contextual validation. Popularity remains unsupported until independent
cultural/audience evidence is normalized; development quality and tradition remain
outside the current quantitative model.


## Rejected single-factor structural transfer hypotheses

Canonical structural evidence is useful context, but the review-set audit explicitly
rejects four tempting shortcuts as standalone rating rules.

Across the nine review countries:

| Hypothesis | 2026 prototype attribute | Spearman rho | Decision |
|---|---|---:|---|
| tradition evidence span alone | tradition | 0.0169 | rejected |
| pre-1955 event count alone | tradition | -0.0151 | rejected |
| development-history span alone | development quality | -0.0840 | rejected |
| development-evidence recency alone | development quality | -0.0252 | rejected |

The candidate threshold is |rho| >= 0.60; none is remotely close.

Therefore:
- an older federation or older national competition does **not** automatically mean
  a higher tradition rating;
- a longer documented academy/development history does **not** automatically mean
  higher development quality;
- recent development activity does **not** prove successful development outcomes;
- event counts remain documentation coverage, never quality weights.

This negative result does not make structural evidence irrelevant. It means any
future development/tradition calibration must be multifactor and supported by richer
independent evidence (for example coaching/licensing depth, academy coverage,
youth-competition structure and cultural/audience evidence) rather than a single
timeline statistic. Held-out BRA/DEU/ISL/SMR remain excluded from fitting.
