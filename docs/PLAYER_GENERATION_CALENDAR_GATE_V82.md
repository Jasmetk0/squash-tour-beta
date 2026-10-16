# Run-owned generation calendar preflight — v82

The generation kernel and InitialWorld conversion still use the historical
2000/FAX clock. New Runs can store other valid calendars, but until the actual
birth/lifecycle/growth/ranking callers migrate, returning a newly sampled cohort
under those clocks would falsely present legacy dates and ages as Run-local facts.

`RunWorldInitialPoolPreviewService` therefore requires an explicit calendar
preflight dependency. Production constructs `RunWorldGenerationCalendarGuard`
with the real repository and verifies the selected Branch's saved calendar
before any generation. The same boundary is used by raw pool preview, Keep and
verified edit sessions, InitialWorld preview/adoption, selected-append generation,
and creation of new stored proposals. Direct generator URLs cannot bypass the
Home warning. This uses the same conservative temporary FAX compatibility gate
as the currently supported sporting path; it does not enable W52 execution.

The guard reads only. A later authoritative adoption still performs its own
check inside the writer transaction. Countries and package planning remain
available because they do not generate new players under an incorrect clock.
Missing legacy calendar fields retain their older meaning; explicit malformed
metadata or broken Saved proof cannot silently fall back to FAX.

Stored proposal inspection, listing and exact stored reopening do not generate
new players and do not run generation preflight. They preserve the originally
stored request, preview, identities and fingerprints. This change adds no fields
to those payloads and does not rewrite any historical Run or proposal.

Verification includes real HTTP/SQLite custom Run + World-copy + explicit Save
fixtures. Tests reject new W52/O1, W52/O35 with custom years and nondefault
horizons before generation/proposal writes, including Keep/edit requests, and
compare the complete database dump before and after. Default FAX produces exact
repeated previews; stored proposal reads stay byte-equivalent even when a test
sentinel makes new generation unavailable. Default preview/Keep hashes were
compared with the unchanged parent tree in both Python 3.11 and 3.12. Player
payload hashes are identical in this fixture and pinned; complete preview/Keep
hash pairs pin both observed historical baselines.

Isolated source/math tests inject an explicit legacy test preflight; actual
repository tests use the production Saved-clock guard. Two old assertions that
omitted newer optional naming/session fields were updated to their intended
legacy projection, without changing fingerprint production code.

Dependency: calendar creation/gates PR #1496, final parent
`6c8b2ed48e01ff927dca8995c84ac3308c90841d`. Age helpers PR #1497 is independent.
No merge is performed by the assistant. Next: version the actual player
generation/lifecycle time basis and propagate the Run clock, retaining old
hashes/replay, before relaxing the corresponding generation/sporting guard.

## Observed inherited runtime limitation

The parent and this branch both produce the same full preview/Keep bytes within
each tested Python version. Between 3.11 and 3.12 the fixture's population-weight
float diagnostics differ at the last bits (for example 11999999.99999999 versus
12000000.0), changing full preview hashes and the subsequent Keep request's
source fingerprint. Its actual player payloads are identical. This is an
observed inherited limit, not fixed or hidden by rounding old production data.
A future versioned canonical-number/runtime contract must address cross-runtime
proposal regeneration without rewriting historical snapshots or changing old
sampling semantics silently. Stored historical inspection still reads the exact
saved bytes. Do not claim cross-runtime regeneration equivalence from this PR.
