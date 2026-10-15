# Next Week append-only schedule inspection (Master v81)

This is a read-only prerequisite for an explicitly authorized frozen Next Week extension, not extension itself. Earlier merged #1475 conservatively surfaced schedule drift as an operator checkpoint. This slice gives Run Admin and Global Task Center verified information about **what changed**.

GET `/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation/next-week/extension-inspection` enumerates pending Next Week receipts in this exact Branch. It compares each immutable old schedule fingerprint and ordered target Group IDs with the canonical current scheduled prefix, after materialized post-group knockout authority. Only an exact prefix match plus new slots actually owned by frozen hybrid knockout bracket matches is labeled `append_only_proven`. Any historical, corrupt, out-of-scope, version-incompatible, non-hybrid or intervening changed schedule is blocked or HTTP 409, never silently rebased.

Every response is labeled read-only, `automatic_rebase=false`; no command, sporting receipt, Worker, Save, World Event, Ranking Source or Target is mutated. Current operator flow remains Stop and newly reviewed simulation, not an implied same-parent Resume. React CS/EN cards show the actual new global slot ordinals only when proven, and explicitly say authorization is still separate.

Next independently reviewed slice: versioned, idempotent Admin approval and SQLite-fenced update of the frozen child range, with preserved original request fingerprint, old result prefix, 2000/01–2049/50 parent linkage, and genuine hybrid SQLite/Chromium acceptance. Before claiming safe automatic continuation, test concurrent writer ordering, re-review racing with task Resume, and deterministic replay. The read-only module tests are pure contract evidence, not proof of that mutation path.

Release acceptance still requires full 50-season and complete pre-alpha regression gates.
