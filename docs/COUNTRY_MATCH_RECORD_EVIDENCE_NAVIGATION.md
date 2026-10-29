# Country match record evidence — exact Saved Revision browsing

## Boundary

Admin → Run → World → Country → Records reads a **reachable immutable Saved
Revision**. Two per-period records are purely descriptive: most **played wins**
and most **played matches** by an eligible player of the country. Existing
server aggregates determine ties and values from the **full canonical source**,
not the 25-row paged response. Walkovers and BYEs never contribute. Country
of the athlete and tournament host remain distinct. No new sporting authority,
backend command, API schema, migration, shared client, simulation or mutation is
introduced.

## New scoped view checks

The match record overview and every selected evidence page must match the
requested Run, selected Branch, reachable Saved Revision and its original
revision-branch metadata, country, inclusive sporting interval, selected record,
zero-based offset and 25-row limit. Response schema and source are checked
before rendering. Both record categories and every tied holder must be valid.
Summary and detail must agree on the exact holder/record collection, population
counts, origin and period. Invalid or late data fails closed with a visible
CS/EN error and never contributes a displayed record or source link.

Each evidence row must be a canonical played match within the requested period,
with two different nonempty player IDs, a nonempty score and event identity, and
an actual tied winner (played wins) or tied country participant (played matches).
Duplicate event/match keys, wrong holder, walkover, wrong time, truncated in-range
page and incorrect has-more are rejected. The view does not invent rows or totals.

The evidence UI remounts its local cursor whenever Run, Branch, Saved Revision,
country, sporting period or selected record changes. The first new request is
for offset **0**, not the old revision's page 25/50. The zero-evidence case shows
**Page 0 / 0**, not Page 1 / 1. An intentionally out-of-range cursor offers
explicit first/last valid page recovery. CS/EN switches do not alter source or
page. Match hyperlinks preserve the exact source Branch/Revision and back-link
to the original Country record; a URL cannot grant access to a different Saved
Revision.

## Verification

- `countryMatchEvidenceValidation.test.ts`: pure contract tests for foreign
  sources, contradictory totals, wrong holders, period, duplicate evidence,
  walkovers and end-of-archive page semantics.
- `RunWorldCountryMatchHighlights.test.tsx`: mocked-API interaction tests for
  25-row page navigation, real source changes, locale, invalid detail, empty
  evidence and exact return links. These **do not** prove SQLite persistence.
- Existing real Country Records HTTP/SQLite browser acceptance and full pre-alpha
  release gates remain separate. No old acceptance, timeout, fixture or warning
  is weakened, and no claim of full release readiness is implied.

**Ownership and conflict boundary:** Only
`RunWorldCountryMatchHighlights.tsx`, its own new test,
`countryMatchEvidenceValidation.ts` and its new unit test, plus this document.
No edits to player Career PR #1652, common API clients/types, historical
read models, Player/Match Engine or Work's sporting/Save integration.
