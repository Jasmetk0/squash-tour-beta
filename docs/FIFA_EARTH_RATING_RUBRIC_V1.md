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
