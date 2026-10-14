# Real hybrid knockout final — canonical Match Day 2, replay and SQLite restart

**14 October 2026.** This PR is a genuine sporting execution acceptance
after the already merged #1451 post-group entrants/bracket handoff.

## What works

1. In real Run Admin, create a two-group hybrid cup, seed no phantom athletes,
   play two independently seeded actual MatchEngine group matches in canonical
   Match Day 1, confirm both final group standings, and freeze the explicitly
   configured Group 1 winner vs Group 2 winner first-round bracket.
2. The ordinary authoritative Run driver derives the **next** Match Day
   (ordinal 2), exactly one knockout match from the frozen bracket. The
   operator must review and confirm this via the existing real Simulation UI;
   clicking the browser is the only execution path. No synthetic score,
   preselected match winner, fake HTTP response, or bypass of a Slot.
3. Verify the persisted authoritative MatchEngine replay: match identity is
   the bracket's frozen terminal ID, both opponent identities are exactly
   the two actual group winners, the winner is one of them, replay events
   exist with a non-empty result fingerprint, and stored replay context
   explicitly says **no RNG rerun**.
4. Verify the actual final is no longer eligible to be replayed as a pending
   Slot. Deliberately Save the resulting simulation into a new immutable
   revision, leaving the ancestor unchanged.
5. Restart the FastAPI process over the same SQLite file. Verify the exact
   group standings, knockout entrants, bracket, winner/loser fingerprint,
   replay list and full pre-match replay context are byte-for-byte stable.
6. Production Admin now offers a clear navigation link from an immutable
   hybrid bracket to the real Simulation Match Days.

## Scope

The result is a **played knockout final**, not an automatically published
tournament champion/Ranking source. Configuring hybrid phase point awards,
closing the canonical tournament Result, publishing Ranking points and
historic award replay are independent next acceptance gates. The existing
Saved Edition correctly does **not** fabricate `published_result` without
the explicit ranking policy/closure. For multi-round fields, this test
demonstrates the exact one-round smallest hybrid bracket; the backend's
multi-round support retains separate comprehensive acceptance gates.

Relevant verification:
- `scripts/real_hybrid_progression_browser_checks.py`
- `scripts/admin_saved_group_browser_smoke.py --hybrid-progression`
- `.github/workflows/prealpha-hybrid-format-browser.yml`
- `tests/application/test_real_hybrid_progression_browser_contract.py`
