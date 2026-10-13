# Completed pure-group Standings in real Run Admin — 13 October 2026

Status: implementation candidate for pre-alpha. This is a standalone vertical
slice on top of merged #1428; it does not alter the canonical sporting rules.

## Workflow

A Run Admin can prepare and play a pure round-robin tournament with the
existing Group Format and authoritative Simulation controls. When the
canonical preparation reports `group_match_execution_ready`, the exact
writable Run/Branch/Present Event page now provides a *completed group standings*
section. It does not infer standings from a merely scheduled or partially
played group. The panel reads the existing immutable Group Standings authority;
a missing (404) authority is clearly distinguished from an error.

If no authority exists, the panel links to authoritative Simulation. Once
all actual sporting Match Days are completed, the Admin may explicitly confirm
`group-standings/generate`. Production refuses incomplete/corrupt evidence,
and the frontend validates exact Run/Branch/Event scope, fingerprints,
unique players and contiguous table positions on the response.

An unresolved tie is shown as a **blocking Admin decision** with player
identities and the backend reason. The UI never invents a tie-break
criterion or chooses an ordering. A complete tie-resolution editor remains
a separate follow-up; API authority exists, but this screen does not silently
invoke it. After generation the table is immutable, read-only, and a separate
Simulation Save is required to preserve it in an immutable Saved Revision.

## Evidence

- Focused frontend tests for final authority integrity, 404 vs error,
  explicit confirmation, tie refusal, and read-only already frozen tables
- Existing browser smoke now reopens the *real Run-owned Admin Event* after
  six actually simulated games, Group Standings generation, Save and SQLite
  recovery, and verifies the frozen canonical table, in addition to
  pre-existing historical Saved Edition comparison
- Changed Python `pr_critical` acceptance guard protects that browser assertion

This is **pure groups** only. No hybrid knockout/ranking closure, no
implicit Run Save and no mocked sporting receipt.
