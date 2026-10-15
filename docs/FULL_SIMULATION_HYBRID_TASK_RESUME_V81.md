# Real hybrid Full Simulation original-task explicit continuation — Week 2

15 October 2026. Based on merged PR #1479, the browser acceptance plays two
real MatchEngine group matches, explicitly freezes standings, entrants and
knockout bracket, plays the actual final, freezes tournament point policy and
closes canonical ranking source. Admin **manually** reviews the ranking
transition authority and the Week-1→Week-2 transition and Saves the Published
Edition. The Full Simulation server task from *before* group Match Day remains
`awaiting_operator` throughout.

This PR goes further: at genuinely published Week 2, it explicitly and
idempotently narrows the *same original* Full Simulation parent target to
Week 2. In a separate real Chromium Task Center view, an operator provides
an audit label + reason and deliberately resumes the exact task. The server
must adopt `target_reached` rather than trying to replay old group/knockout
matches or alter the already published Saved Revision. It proves all three
replay identities, unchanged Saved head and Working Draft version, original task identity and
unchanged state after the server process is restarted by the existing test.
The test never patches the worker, seeds scores or synthesizes sporting data.

**Limit:** this verifies explicit continuation **after** human-controlled Week
Transition. It does **not** prove the original server task independently
executes the Week Transition or covers every future season/50-year run.
Independent full original-task Week Transition is the next integration gate.

The immutable Saved head and Draft version are compared separately from the
live Save-preview fingerprint: changing the audit target legitimately changes
unsaved command/audit evidence without replaying sporting results.
