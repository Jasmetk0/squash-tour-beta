# One Full Simulation task across a second real SQLite restart

This browser acceptance extends the established genuine MatchEngine hybrid
journey and the merged Week-2-to-Week-3+ worker acceptance.

The first parent deliberately reached its Week-2 operator target and is
terminal. The second parent begins at the same Run's Saved Week 2 and executes
the real canonical simulation worker through Week 3 or later. Its task is
observed at a natural operator checkpoint.

Unlike the prior acceptance, the test **kills and restarts the SQLite-backed
server again** while this second task is pending. It proves the task ID,
parent command ID, frozen original command, revision/checkpoint, world position,
three group+knockout MatchEngine receipts, Saved head, and public Week-2
ranking are preserved. It then explicitly resumes this **same second task**
from production Chromium Task Center, checks a fresh audit revision, and
requires nondecreasing world chronology with identical existing sport/Viewer.

When the original blocker is still unresolved, another checkpoint at the
same week is valid. In that case no additional Week Transition is claimed.
The evidence records whether the world actually advanced further.

Does not reopen the first, terminal parent; create a third parent; fabricate
scores; monkeypatch the worker; or assert independent 50-season completion.
A new dedicated Chromium/SQLite CI workflow and negative PR-critical tests
guard the contract against incorrect lineage or historical drift.
