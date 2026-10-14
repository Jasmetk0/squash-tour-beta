# Authentic four-player cyclic tie: real Admin browser and SQLite acceptance

Status: isolated pre-alpha browser integration (14 October 2026).

## Test path

1. Chromium uses genuine Run, World, generated player, Event and Group Format
   setup through the real Admin frontend.
2. An isolated test-only **schedule/result input adapter** selects six natural
   rally-by-rally BO3 MatchEngine results from a bounded deterministic search.
   A/B/C are a genuine unresolved cyclic tie on all automatic criteria, D is last.
   These results do NOT pretend to arise from the Run's normal Match-Day RNG.
   The production generated group schedule remains stored separately.
3. Production FastAPI rejects premature standings generation (409). The real
   Admin interface renders its exact server-side unresolved case fingerprint,
   allows operator reordering C/A/B, requires an audit reason and confirmation.
4. Stale / modified case commands fail HTTP 409. Real browser commits the
   explicit decision to production SQLite. A backend restart reproduces the
   same saved decision and no longer exposes an unresolved case.
5. The browser confirms final group table generation; its A/B/C/D order,
   authority fingerprint and SQLite row are verified. A second backend restart
   reproduces the immutable final table and original resolution.
6. Screenshots, browser traces, service logs and structured evidence are retained.

## Not claimed

This is **not** a mock HTTP response, artificial match scoreboard or isolated
React test. It covers real HTTP/SQL mutations and a real Chromium user journey
on authentic MatchEngine result inputs.

The six test results were intentionally chosen separately from the Run-owned
automatic Match-Day schedule. Consequently this test does NOT prove an ordinary
Run produced a cyclic tie, a Run Saved Revision archived it, or a hybrid
knockout/ranking cycle closed. Those broader release gates remain open.

Implementation: scripts/real_group_cyclic_tie_browser_checks.py, the opt-in
--cyclic-tie-browser mode of scripts/admin_saved_group_browser_smoke.py and
.github/workflows/prealpha-real-cyclic-tie-browser.yml.
