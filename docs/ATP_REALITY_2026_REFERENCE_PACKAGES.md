# ATP Reality 2026 — source-only Category + Series reference Packages

**Scope:** two optional reference-data `CanonicalPackageDocument` fixtures,
`Category` and `Series`. This is **not** a playable tennis mode, a new
Official FAX default, an ATP licence, or automatic import into the Packages UI.
These are project-authored source references. Never brand them ATP-endorsed.

## Purpose and ownership boundary

The `ATP Earth` World Package models *historical country sport environments*.
The new Category document instead records the **2026 men's tennis competition
hierarchy** and headline singles ranking points; Series records **persistent
tournament identities** and their **observed 2026** category, host and surface.
Category and Series are different owners. A Series is *not* a season-specific
Edition: a calendar/Edition layer would separately encode dates, fields,
qualification, rankings, exact per-round scoring and tournament-specific rules.

Both files conform to the existing sporting-model-neutral
`CanonicalPackageDocument` v1 shape; an explicit Series
`SourceReference` points to the corresponding Category source entity.
The source `package_id` values are globally distinct and stable:

- `atp_reality_2026_category`
- `atp_reality_2026_series`

They are under `config/reference_packages/`, not the existing production
`config/world_packages/` registry. The current Package backbone may review
a supplied canonical document, but **no source registry, UI listing, semantic
Category/Series adapter, or runnable tennis tournament execution is claimed
or introduced** by this PR. Nothing modifies a Run, Save or existing packages.

## Real 2026 hierarchy and boundary

The 2026 reference Category package contains these distinct kinds:

| Competition class | Singles title points / ceiling | Key qualification |
| --- | ---: | --- |
| Grand Slam | 2,000 | Operated outside ATP; included in ATP ranking |
| Nitto ATP Finals | up to 1,500 | Undefeated champion ceiling; match-based group points |
| ATP Masters 1000 | 1,000 | Draw-specific points and qualifying nuances excluded |
| ATP 500 | 500 | 32/48-draw point tables differ below champion |
| ATP 250 | 250 | 32/48-draw point tables differ below champion |
| Challenger 175 / 125 / 100 / 75 / 50 | 175 / 125 / 100 / 75 / 50 | Five distinct 2026 Challenger categories |
| ITF M25 / M15 | 25 / 15 | Governed by ITF; official ATP-ranking points |
| Next Gen ATP Finals | no normal points table | Special format, not an ordinary ATP Finals |
| United Cup | up to 500 | Conditional player/opponent-based award, mixed teams |
| Laver Cup | no ATP ranking points | Special team event |
| Davis Cup | no ATP ranking points | ITF team competition |

The numerical column is **not** an exact all-round point table. In particular,
do not model ATP Finals as a normal 1,500-point knockout, treat team-event
points as an ordinary singles winner award, or assume every ATP event has the
same draw size. ATP's rulebook describes circuit categories differently from
the broader tennis-event and rankings ecosystem: this reference deliberately
includes externally organised events without falsely reclassifying their
governing bodies.

## Series scope

The 63 named identities are distributed:

- 4 Grand Slam tournaments (independent of ATP governance)
- 9 ATP Masters 1000
- 16 ATP 500
- 29 named ATP 250
- 1 ATP Finals, 1 Next Gen Finals and 3 separately classified team competitions

This inventory is **not a claim of a fully audited 2026 calendar**.
Official advance announcements and later 2026 listings differed and included
an unnamed `TBD` ATP 250 slot; an unknown tournament is *not* minted into a
fabricated stable Series ID. Full historical editions, sponsor/host changes,
discontinued/moved tournament identities, all Challenger events, all ITF
events, match formats, ranking policy, dates and court surfaces by edition
require independent source-level audit before any playable ATP analogue.

Historical years **1955–2025 must not inherit 2026 categories or tournament
membership**. The ATP was formed in 1972, its computer rankings began in
1973, and its Masters 1000 predecessor series dates to 1990. Historically
valid progression requires separately versioned, year-effective package
sources and tournament identities, not 72 copies of 2026.

## Primary evidence and provenance

Authoritative source starting points (consult live amendments before
claiming any complete future calendar):

1. [ATP 2026 rulebook](https://www.atptour.com/en/corporate/rulebook)
2. [ATP 2026 singles ranking breakdown](https://www.atptour.com/Rankings/Rankings-FAQ.aspx)
3. [ATP 2026 tournament calendar](https://www.atptour.com/en/news/what-is-the-2026-atp-tour-calendar)
4. [ATP 2026 calendar announcement](https://www.atptour.com/en/news/2026-atp-tour-calendar-announced)
5. [ATP 2026 historical media guide](https://www.atptour.com/-/media/files/media-guide/2026/2026-atp-media-guide-full.pdf)
6. [ATP Finals 2026 special point rules](https://www.nittoatpfinals.com/en/event/points-and-prize-money)
7. [ATP Challenger levels](https://www.atptour.com/en/news/what-is-)

As-of date: **2026-11-01**. The dataset intentionally has **no inferred
attendance, prize money, qualifying sizes, draw sizes, formats, tournament
dates, or historical continuity claims**. Current-year names/locations and
surfaces are descriptive, not timeless promises.

## Validation and next implementation gates

`tests/domain/test_atp_reality_2026_reference_packages.py` checks that both
files validate as canonical documents, each Category reference resolves in
this pair, identity is unique, the recorded event-level counts are coherent,
and the data is explicitly reference-only. It is a shape/consistency gate,
**not a real-world historical validation or end-to-end test**.

Before treating these as real Global Packages, a separate scoped PR must add
the production source registry and semantic adapters, validate the actual
category/series/entity/edition hierarchy against the Master, implement
Admin source review, explicit Run application/Save and sporting consumers.
First audit the 2026 series roster and unresolved `TBD` changes against
final ATP/ITF event records. None of those actions is authorized or implied
by the existence of these reference fixtures.
