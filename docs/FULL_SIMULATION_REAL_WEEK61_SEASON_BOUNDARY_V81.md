# Real Full Simulation boundary after 59 automatically progressed weeks (PR #1484)

Previous green Chromium evidence from #1483 demonstrates the second immutable
Full Simulation task advances from a genuinely published Week 2 all the way
to Week 61, and pauses precisely at `season_transition_save_required`.
A second physical SQLite restart and another Task Center resume preserve the
same task and checkpoint; forcing additional work without the explicit Save
is deliberately forbidden.

This independent browser acceptance uses that *same genuine MatchEngine*
group-to-knockout Run, the real Full Simulation worker and real process
restarts. It now requires an explicit Admin UI `Save authoritative simulation`
at Week 61 and confirms that public Viewer advances from Saved Week 2 to
Saved Week 61, preserving historical Weeks 1/2 and exactly 3 original match
receipts. The prior Week-2 Saved Revision remains immutable. It then obtains
the **canonical persisted** `season-transition/preflight` for Year 2000/01
to 2001/02.

If the preflight is ready, the existing **Review Season Transition** /
**Advance to next season** Admin UI must commit it. If calendar/configuration
or other domain prerequisites are missing, it instead records exact blockers
and refuses to fake a season. Either way, the operator explicitly resumes the
**same second Full Simulation task** from native Task Center; the checkpoint
must move beyond `season_transition_save_required`, its immutable original
command and task ID are unchanged, and sporting/history cannot be duplicated.

All checks must run on the PR's final HEAD. This is a genuine Week-61 Save
and season boundary handling acceptance, not a claim of 50 seasons without
operator decisions or configuration.
