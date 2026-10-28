# Pre-alpha Run creation and Saved-preparation guidance

## Scope and authority

Master v85 §31.38 and `AGENTS.md` govern this small Run-setup slice.
Creating a Run requires only its unique display name. Optional calendar/range
review remains explicit and independent of Package selection. This slice does
not add a generator, a second readiness authority or a hidden Save.

## Changes

1. The create form synchronously fences overlapping submit events as well as
   disabling its submit control during the request. Only one authoritative
   `createEmptyRunContainer` command is sent for the same in-flight submission.
2. The returned Run ID, name, ownership and (when requested) calendar are checked
   before any navigation or local navigation hints are written.
3. If the server confirms a Run identity but returns a mismatched reviewed
   calendar, the form blocks a duplicate create and offers a link to inspect
   the existing Run. Uncertain transport errors explicitly advise checking
   the Run inventory before retrying. If the POST response is lost, the
   creation form now blocks another POST and offers an explicit fresh
   `listRunContainers` read for the exact requested name, without using local
   storage or cached listings as authority. A single exact match yields an
   inspection link (not an assertion of who created it). No match unlocks only
   an explicit manual retry, never an automatic retry; an unreadable, malformed
   or ambiguous inventory fails closed. The name remains fixed until that
   reconciliation has succeeded, so editing cannot accidentally bypass it.
   Invalid server-returned Run IDs and malformed unrelated inventory rows are
   rejected too: no guessed link, local identity update or false negative.
   During reconciliation the name, calendar toggle and reviewed calendar inputs
   are frozen together, so an uncertain POST cannot silently change meaning.
   A successful exact-name inventory read with no match unlocks the inputs,
   but never automatically sends another create request.
4. A best-effort inventory cache invalidation is not allowed to turn a
   server-confirmed Run creation into a false failure and a duplicate retry.
5. If routing itself fails after server-confirmed creation, the form says the
   Run **already exists**, disables repeated creation and links directly to the
   created Run rather than allowing another create.
6. Browser-local recent/last-Run persistence remains optional. The server
   creates the authoritative Run; unavailable storage does not prevent opening it.
7. The Run Home Saved-readiness card prioritizes review/Save of an unsaved
   Working Draft over further apparent missing-Saved setup actions. This is a
   navigation recommendation, **not** a Save, an authorization or a claim that
   all world content must exist before unrelated operations.
8. The preparation phase links to the existing global Test Lab, which does not
   require a Run. This does not create a parallel sporting world or authorize a
   Run operation.
9. An all-optional/all-saved inspection no longer claims that every foundation
   has been saved or that all sporting operations are ready. Each operation
   retains its own preflight and unsupported features stay unsupported.
10. Expanded CS/EN Saved-readiness evidence: the six counts are identified
    precisely as Run-owned World entities, Calendar entities (not Run time),
    Saved initial-population players (not all historical players), Health
    records (not match clearance), published ranking snapshots (not
    candidates), and changes in this Branch Working Draft only. The five
    backend statuses are explained without inventing an operation-wide block.
    A clean Working Draft is named **clean**, not generally **saved**;
    optional Health is not treated as universally ready. The checklist
    remains collapsed by default, with read-only route-scoped repair links.
    A scoped responsive checklist layout wraps explanations beside their
    repair links without changing other Run Home feeds. The original backend
    DTO/authority and operation preflights are unchanged.
11. The frontend contract also rejects an invalid Run calendar (nonpositive W,
    impossible season offset, negative year, zero horizon or wrong schema),
    blank Saved Revision identity, contradictory positive-count Saved
    foundation badges or impossible per-foundation statuses (e.g. World as
    "candidate only" or Working Draft as "missing"). These are fail-closed
    checks on received evidence, not
    new sporting prerequisites or alternate counts.


12. Repaired two misleading Run Home navigation actions against actual Admin
    routes. FAX-compatible initial ranking preparation/publication now targets
    the existing Run Home preparation panels through a stable
    `#run-initial-ranking` anchor, **not** the Simulation route — only when
    the Run and selected Branch actually expose the writable initial-ranking
    panels. Other calendars, protected Runs or non-editable Branches use the
    selected Branch's ranking candidates for read-only inspection, with an
    explicit warning that this is **not** permission to publish.
    A dirty Working Draft links to Branch/Saved history as **inspection only**,
    explaining that explicit Save belongs to the editor owning those changes.
    Existing Save, publication, candidate and simulation commands are unchanged.


13. Run Home now treats a Saved readiness fetch or refresh as unverified until
    the exact Run/Branch/HEAD/draft/calendar response is validated again.
    Cached prior successes remain hidden during refresh and after failure,
    including failed background refreshes that React Query may retain as data.
    A dedicated CS/EN read-only Retry is available for transport failure or
    identity mismatch; missing Saved HEAD is stated explicitly rather than
    leaving a disabled readiness query showing "loading" indefinitely.
    Retries never Save, publish, advance time or run simulation.
14. Readiness now additionally requires an independently verified Run container,
    a valid canonical Run calendar and a matching current Working Draft before
    presenting a Saved-foundations card. Previously a missing draft or malformed
    Run clock could silently skip the cross-feed comparison. All three
    read-only sources are re-fetched on manual recovery; a failed or foreign
    component keeps the guide hidden rather than providing false authority.
    Focused regressions cover offline draft, foreign draft and bad Run metadata.
15. The read-only DTO validator checks publication totals against the
    official-ranking evidence row, and rejects a claimed legacy FAX writer
    for non-FAX clock values. It deliberately does **not** infer legacy
    support merely from matching clock numbers, because historic read-time
    calendar versions may still be unsupported. These checks cannot authorize
    simulation or publication on their own.
16. Real HTTP/SQLite acceptance now exercises the read boundary, not just
    mocked frontend results: an empty FAX Run remains a valid, optional-Health
    preparation state across restart. A separate custom-calendar Run is forked
    through the actual API, stages a Working Draft change without changing
    Saved HEAD, rejects a stale Save version, then explicitly Saves. The
    assertions compare immutable Saved evidence and Working Draft versions on
    both Branches, including a fresh HTTP process/SQLite reopen. No test
    generates sporting results or pretends a candidate is published.

17. Real HTTP/SQLite creation reconciliation treats the first successful
    POST reply as unseen by the hypothetical client, then performs a fresh
    server inventory read with one exact name match and a similar other name.
    It verifies the Saved HEAD/clean Working Draft, an atomic 409 for the
    trimmed duplicate request, and persistence after service/SQLite restart.
    This is **not** transport-level reply loss or a universal concurrent
    idempotency guarantee.


18. Both Run Home readiness refresh controls now re-fetch Run metadata,
    selected-Branch Working Draft and the Saved-readiness DTO together. While
    any dependency refresh remains in flight, the prior Saved card is hidden.
    The changed frontend tests also exercise a delayed prior-Branch HTTP
    response arriving after a Branch switch: it must remain in the old query
    cache without contaminating the newly selected Branch's Saved evidence.
    A separate delayed old-Run response test verifies the same isolation after
    navigating to a different Run with another Saved HEAD. These are read-only
    inspections; no Save or sporting action is implied.

## Validation boundary

Focused React component regressions exercise rapid double-submit, rejected
inventory refresh, navigation failure/repeated submission after success, unavailable localStorage,
dirty-draft priority, all-optional Saved-inspection wording, and
URL encoding of returned Run identifiers, preparation-only Lab navigation,
CS/EN evidence labels, candidate versus published ranking, clean Working
Draft and encoded Run-scoped repair paths. An uncertain create can be retried **only after** a successful, matching-name
inventory reconciliation with no matching Run. A server-confirmed create cannot
be retried on the same form. The negative inventory result is point-in-time
evidence, not a guarantee about a concurrently completing request. The frontend scenarios mock the
API boundary, while the scoped backend tests in
`tests/api/test_run_home_readiness_api.py` exercise production HTTP/SQLite.
Neither is real-browser acceptance.

The relevant frontend test/build and final-head hosted checks must complete
successfully before the owner considers merging. Draft skips do not count as
passes. The full Master §31 pre-alpha release gates (including real FAX
50-season and 1,000-player acceptance) are unchanged.

## Parallel-work exclusion

As inspected on 28 October 2026, open PRs #1647, #1648, #1649 reserve native
groups/global slots, Saved Tour/player explorer and Admin Diagnostics
respectively. This slice modifies none of their tracked paths. All changes
are on one independent branch; only the project owner merges.
