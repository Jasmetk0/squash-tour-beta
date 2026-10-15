# Real hybrid Full Simulation human group-phase handoff — browser acceptance

15 October 2026. After merging #1478, the existing real hybrid browser path
now starts a genuine server-owned Full Simulation **before** Match Day 1, after
the exact adopted Week Schedule has been committed. The original task must
reach `awaiting_operator / group_phase_review_required` with **no** sporting
receipts or fake bracket, and the actual English Task Center must display the
human group-phase explanation.

The existing Chromium scenario then explicitly plays two actual MatchEngine
group games, freezes standings and real group winners, approves entrants and
one-round knockout bracket, plays the actual final, creates ranking policy,
closes ranking source, Saves the resulting Edition, publishes canonical week 2
ranking and verifies immutable SQLite restart. This new adapter checks that
the *same original* Full Simulation task is still awaiting operator, and all
three real match replays are unique, after the entire chain. The task never
silently resumed while the human performed sport and approvals.

This is real sporting browser evidence, **not** proof that this original task
has been resumed through Week Transition. That needs a separate explicit
continuation-after-approval acceptance. No uncontrolled concurrent executor,
no background scheduling beyond existing task mechanism, no synthetic scores.

Run: `scripts/admin_saved_group_browser_smoke.py --hybrid-progression`.
Workflow: `.github/workflows/prealpha-hybrid-format-browser.yml`, plus Fast
CI. Owner merges only after required final-HEAD checks green.
