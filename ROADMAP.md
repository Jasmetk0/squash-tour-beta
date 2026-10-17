# Active dependency path — Master v84

Audited base: `buuk` `5dce12a07acb980882a5454485681f9eb7e5af79` after #1519.
The owner alone merges. Default implementation is direct ordinary ChatGPT,
without launching paid Codex/agents. Refresh base and open PRs; avoid duplicate work.

| Order | Usable outcome | Current evidence / remaining work |
| --- | --- | --- |
| 0 | Consistent directly affected regression tests | A84-01 regression assertion repaired on this proposed branch for W52/61/80; joint ranking modules and final-HEAD CI must pass before merge |
| 1 | Run calendar creation and reviewed all-Branch extension | Creation is merged; #1508 adds real atomic manual Save, immutable history, fork/restore compatibility and receipts. #1509 Home guide is merged. Actual sporting continuation remains separate |
| 2 | Calendar-native real Run-owned match / main-only tournament, Save and replay | Proposed v84 match slice executes one actual opening-week W52/W80 BO5 with MatchEngine, manual immutable Save and cold replay from Saved population; native tournament/Slot authority, 57-attribute sporting evolution and CS/EN browser remain missing |
| 3 | Configured points, Official publication and actual Week/Season transitions | #1510–1519 candidates/staging/read adapters are merged, not official publication. New sources need Saved capture/restore/fork and authored configuration lineage |
| 4 | Annual development/recovery and durable Full Simulation use real Run W | Age helpers exist; migrate actual weekly updates with 1/W year units, preserve weekly deadlines, frozen task targets, simultaneity and explicit recovery |
| 5 | Populated multi-season acceptance and extended-horizon continuation | Prove real second-season sporting work and explicit work after Completed; preserve W61 reference and verify W52/W80/extended horizons |
| 6 | Historical-cohort initial world and remaining complete pre-alpha scope | Master 9.8–9.9, preparation/export, canonical attributes, intake, AI, Records and Saved Views remain targets, not done by calendar candidates |
| 7 | Release acceptance, then measured realism calibration | Full regression + all Master release gates; protected template copies, reference >=1,000 prestart nonretired players, 80 World Tour Editions/season and 50-season FAX acceptance |

Deliver coherent usable slices rather than another long sequence of read-only
provenance fragments. An implementation may need internal domain/storage changes;
do not publish unsupported operation buttons or strip legacy guards to fake progress.
No direct Saved JSON/hash rewrites in positive production-flow acceptance.

See [current state](CURRENT_STATE.md), [v84 audit](docs/PRE_ALPHA_CHECKPOINT_V84_2026_10_17.md)
and [full next task](docs/PRE_ALPHA_NEXT_CHATGPT_TASK_V84_2026_10_17.md).
New product decisions live in Master 9.9/21.3.1/27.24/31.39; their existence does
not establish runtime completion or resolve deferred initial-rule inheritance.
Historical candidate notes and dated evidence remain in Git and Master chapter 35.

## Candidate next vertical slice: real opening-week knockout

Following merged #1522, the current candidate extends real calendar
sporting to a full main-only four-player opening bracket, actual seeded
MatchEngine semifinals/final, exact replay and immutable manual Save.
This shares existing Saved capture/restore/restart while preserving
legacy exhibition schema and sporting guards. It is **not** official
tournament points, weekly publication or Week/Season Transition. Its
candidate tests/CI and distinct Chromium acceptance must be verified
before merge. Contract: [CALENDAR_OPENING_KNOCKOUT_V84.md](docs/CALENDAR_OPENING_KNOCKOUT_V84.md).
