# Admin frontend consolidation — 22 October 2026

## Scope and authority

The owner requested review and consolidation of every remaining ordinary ChatGPT
PR. Baseline is `buuk` `a0308cef9214f83a814b1fecd23cb3a30cc55491`,
which already includes owner-merged #1606 and its independent paused-Player-run
correction. None of those Lab/backend changes are reimplemented here.

The 52 source PR heads below modify 114 distinct frontend files with no overlap.
They were applied together onto this baseline. Original branches remain intact;
superseded PRs can be closed with the integration link, never misrepresented as
individually merged. This is one owner-reviewed Admin usability integration,
not 52 separate merge/test cycles.

Useful changes include exact Saved source/calendar labels, Run-scoped selection,
country pagination, strict deep links, encoded navigation, truthful loading and
error states, archived-template protection, cache refresh and recoverable filters.
Read-only catalog discovery, neighboring-item navigation and responsive tables
improve inspection; they do not implement new sporting or simulation mechanics.
Legacy inspectors remain diagnostic surfaces, not canonical Saved authority.

## Independent review corrections

- Calendar Compare's new selection guard did not freeze a submitted Apply.
  Actual QueryClient offline pause/resume reproduced a command sent to a later
  selected source/season. The full confirmed API argument tuple is now captured
  synchronously. A late response cannot masquerade as the currently reviewed
  comparison; cache invalidation still runs for the completed command.
- App module 17 route tests now verify the actual localized Active/Warnings
  labels, scoped diagnostics guidance and exact 10-of-11 preview count.
  Their four earlier text expectations failed after the intended UI changes;
  no test or behavior assertion was removed.
- One trailing-whitespace error in the original World Library patch was removed.

## Validation boundary

A complete frontend run was executed on the clean baseline before attributing
failures to this integration. That baseline has 78 failures in 13 Viewer-related
test files. They concern existing deferred Viewer route/read-model/source-guard
contracts and are not silently disabled, edited or counted as passes here.
The exact full-suite failure-name comparison and executed scoped/build/hosted
results are recorded in the integration PR. No claim that the entire frontend
or whole pre-alpha is green follows from applicable PR checks.

The combined candidate must introduce no additional full-suite failures, pass
all touched component/route tests and the production build, and pass applicable
final-head hosted acceptance under docs/PRE_ALPHA_TEST_POLICY.md. Draft skips
are not executed checks. No backend policy, authority, persisted data, Master
product rule or CI exclusion changes are part of this work.

## Source inventory

Machine-readable paths and complete immutable source SHAs are in
[the source manifest](ADMIN_FRONTEND_CONSOLIDATION_SOURCES_2026_10_22.json).

| Source PR | Source head | Included purpose |
| --- | --- | --- |
| [#1578](https://github.com/Jasmetk0/squash-tour-beta/pull/1578) | `1da3eb5c9335aa415c6efd4d3a29bbc4576fb611` | fix(web): avoid invented ranking calendar dates in Saved Players views |
| [#1579](https://github.com/Jasmetk0/squash-tour-beta/pull/1579) | `6c32af1c84f56c0d44691b059dbd173f9893036f` | feat(web): browse and audit World Package catalogs without backend changes |
| [#1580](https://github.com/Jasmetk0/squash-tour-beta/pull/1580) | `bfae4fedec86462891c66857723d3ee97882bf82` | feat(web): distinguish linked and planned global diagnostics |
| [#1581](https://github.com/Jasmetk0/squash-tour-beta/pull/1581) | `40f0ef5b8ca2d38d76fabfeaa2631efc70c6d176` | feat(web): add persisted calendar template inventory filters |
| [#1582](https://github.com/Jasmetk0/squash-tour-beta/pull/1582) | `089ca521757c54e917d70be6ea32695ed8839778` | feat(web): search canonical category identities by tour |
| [#1583](https://github.com/Jasmetk0/squash-tour-beta/pull/1583) | `f6a06c1571c2a3259e3ec5699418c0661193a9cc` | feat(web): filter read-only season registry entries |
| [#1584](https://github.com/Jasmetk0/squash-tour-beta/pull/1584) | `f095dec2786ae37eaccab6bd1a7dfd11b99c2a39` | feat(web): filter read-only tournament master inventory |
| [#1585](https://github.com/Jasmetk0/squash-tour-beta/pull/1585) | `200e584c4352c7d771d67a597704685c165fc1a7` | feat(web): navigate adjacent derived category details |
| [#1586](https://github.com/Jasmetk0/squash-tour-beta/pull/1586) | `c43985b682737d48245f7f8cd7b52b23f59b4a7b` | feat(web): filter tournament template inventory without changing editor |
| [#1587](https://github.com/Jasmetk0/squash-tour-beta/pull/1587) | `7abfb93af751650bab7dabaf91dca2a66b0a6174` | feat(web): navigate adjacent tournament master details |
| [#1588](https://github.com/Jasmetk0/squash-tour-beta/pull/1588) | `ee9d62252e9e20b93ddd4b21b4d044aa34276152` | feat(web): browse read-only season template slots |
| [#1589](https://github.com/Jasmetk0/squash-tour-beta/pull/1589) | `d603436d7bbff8fb03e0797de4a3ad1954445c19` | feat(web): inspect persisted calendar template event lists |
| [#1590](https://github.com/Jasmetk0/squash-tour-beta/pull/1590) | `98202c50f41ea17b08fb4dcdea9f523bf5e75b15` | fix(web): recover Talent Preview after zero country matches |
| [#1591](https://github.com/Jasmetk0/squash-tour-beta/pull/1591) | `bf5afed17cbc361370a7996d0ca1bcc5b1fd834a` | feat(web): search Tour Seasons validation issues across panels |
| [#1592](https://github.com/Jasmetk0/squash-tour-beta/pull/1592) | `68b09d7d3d4dbc3e32dcc2d68f3d3064d750b76e` | fix(web): keep local sandbox event IDs unique after deletion |
| [#1593](https://github.com/Jasmetk0/squash-tour-beta/pull/1593) | `5e73b1626dfdf968fe19f055429135008e181ede` | docs(web): clarify pre-alpha Viewer limitations on landing |
| [#1594](https://github.com/Jasmetk0/squash-tour-beta/pull/1594) | `ad8fd3e0e443063379cafc081c01d77bfe6c556c` | feat(web): filter read-only season health checks by severity |
| [#1595](https://github.com/Jasmetk0/squash-tour-beta/pull/1595) | `bb258c927edfba2194245309883bee99ddc34c4b` | fix(web): prevent silent unarchiving in calendar template editor |
| [#1596](https://github.com/Jasmetk0/squash-tour-beta/pull/1596) | `2f6c9cf095d8d210e2e4c051c55123f2b9e545d1` | fix(web): distinguish loading from unavailable season workspace data |
| [#1597](https://github.com/Jasmetk0/squash-tour-beta/pull/1597) | `f150a7a2dd871e3db97804d65804acbb076c6775` | feat(web): accessible and scrollable season ranking preview tables |
| [#1598](https://github.com/Jasmetk0/squash-tour-beta/pull/1598) | `ff50d51304b40004add49dedaf61703b31f3f630` | fix(web): avoid double-decoding Concrete Season route IDs |
| [#1599](https://github.com/Jasmetk0/squash-tour-beta/pull/1599) | `a0a18e779577979dff07d373033585b34afe4cac` | fix(web): refresh calendar template inventory after successful creation |
| [#1600](https://github.com/Jasmetk0/squash-tour-beta/pull/1600) | `a9dd300f97084cd0600db089129accc8ffee92cd` | fix(web): keep Nation Dashboard detail selection scoped to its Run |
| [#1601](https://github.com/Jasmetk0/squash-tour-beta/pull/1601) | `cd4d5cf7629acce67453b1d24c20a93e9c831a44` | feat(web): truthful counts and accessible season calendar preview |
| [#1602](https://github.com/Jasmetk0/squash-tour-beta/pull/1602) | `64d5d015f762ee2d8bf88c919b345f7a7f4193a8` | feat(web): recover World Generation provenance filters and clarify empty results |
| [#1603](https://github.com/Jasmetk0/squash-tour-beta/pull/1603) | `d40f1f335d25f4dce0c60339e92c79b98e600434` | feat(web): scrollable Talent Calibration diagnostic tables |
| [#1604](https://github.com/Jasmetk0/squash-tour-beta/pull/1604) | `3050de20182d69cbfd6f26d24d4f085db8cfb0f2` | fix(web): normalize manual Dashboard Run IDs and encode detail routes |
| [#1605](https://github.com/Jasmetk0/squash-tour-beta/pull/1605) | `6e8111d6c39fee6b02469da236cb00e53e920361` | fix(web): distinguish unselected Branch from missing saved HEAD in Tour Calendar |
| [#1607](https://github.com/Jasmetk0/squash-tour-beta/pull/1607) | `cedcfe52df96e9f33bad31e2cf82b1fd974dfa91` | fix(web): prevent applying a stale Calendar Compare review |
| [#1608](https://github.com/Jasmetk0/squash-tour-beta/pull/1608) | `5c0252f3b379b7bacd618acc249e8feaef1f25fa` | fix(web): show truthful Finals qualification and result availability states |
| [#1609](https://github.com/Jasmetk0/squash-tour-beta/pull/1609) | `e0517d7d76deb109e48447b86e0ac787c7e4a59a` | fix(web): distinguish unknown, failed and missing Finals result states |
| [#1610](https://github.com/Jasmetk0/squash-tour-beta/pull/1610) | `c895f5cd82f1ff25beb433834e2bf57779224c61` | feat(web): recover Talent Intake country searches and distinguish true empty cohorts |
| [#1611](https://github.com/Jasmetk0/squash-tour-beta/pull/1611) | `9c35bf3da4db35f7192f73e51854d713db8a0fe1` | fix(web): show Season Category Points load, initialization and save errors |
| [#1612](https://github.com/Jasmetk0/squash-tour-beta/pull/1612) | `2f30c81e1afcb5455dd79359944b88085f15fe72` | fix(web): show truthful loading, missing and failed Finals overview states |
| [#1613](https://github.com/Jasmetk0/squash-tour-beta/pull/1613) | `bfb1b9c99f71bcc78c25978cf1f2e9e3e5babfbc` | fix(web): preserve encoded Run IDs in Season Chain navigation |
| [#1614](https://github.com/Jasmetk0/squash-tour-beta/pull/1614) | `2f2c341d1c671b1757b361743bce89ee3b6c7ab1` | fix(web): keep Bootstrap Lineage Run IDs safely encoded in links |
| [#1615](https://github.com/Jasmetk0/squash-tour-beta/pull/1615) | `456d1b1c5a38c46137c3e4fe09aeda5067525bb5` | fix(web): require an exact positive snapshot sequence in detail routes |
| [#1616](https://github.com/Jasmetk0/squash-tour-beta/pull/1616) | `68f18b36b3a57c067439d9ca01308ee8708480f0` | fix(web): reject malformed snapshot list deep-link selection IDs |
| [#1617](https://github.com/Jasmetk0/squash-tour-beta/pull/1617) | `97aae8a79c39bc4ab99757945439c30d2c098cad` | fix(web): reject malformed rollover season route IDs |
| [#1618](https://github.com/Jasmetk0/squash-tour-beta/pull/1618) | `fd0b296deb42f2141212011c37796e4952318954` | fix(web): stop week-history requests for invalid week URL parameters |
| [#1619](https://github.com/Jasmetk0/squash-tour-beta/pull/1619) | `902cdb245003b3be499890b3441c956bc4c26cfe` | fix(web): preserve Run IDs in Diagnostics and Finals navigation routes |
| [#1620](https://github.com/Jasmetk0/squash-tour-beta/pull/1620) | `f0f698e73ac0c6b25ac1302aa8086508338b7824` | fix(web): encode Run IDs throughout persisted Event Detail navigation |
| [#1621](https://github.com/Jasmetk0/squash-tour-beta/pull/1621) | `b2e9e8068d5d4081fb8b69903c328942192fa911` | fix(web): reject invalid selectedItem deep links in Activity Feed |
| [#1622](https://github.com/Jasmetk0/squash-tour-beta/pull/1622) | `d7da24da29e69604b76728c62283bc4cb80f73de` | fix(web): validate rollover browser seasons without implicit numeric coercion |
| [#1623](https://github.com/Jasmetk0/squash-tour-beta/pull/1623) | `908afe7a8c7d593821489e84f6851522dc9ce4d2` | fix(web): reject explicitly empty Saved Tour Branch deep links |
| [#1624](https://github.com/Jasmetk0/squash-tour-beta/pull/1624) | `3aeb30b77eb9072398a59504dc3d1bc10bc696de` | fix(web): label Run World country by validated data year |
| [#1625](https://github.com/Jasmetk0/squash-tour-beta/pull/1625) | `4af9a10bfdac7cdd56e736755bc062c89db4c4af` | fix(web): keep Run IDs encoded throughout Season Calendar navigation |
| [#1626](https://github.com/Jasmetk0/squash-tour-beta/pull/1626) | `b24ea1e9f4047a5157c38768d286653da3158d4c` | fix(web): encode Legacy Runs diagnostics links and open action |
| [#1627](https://github.com/Jasmetk0/squash-tour-beta/pull/1627) | `968434eb79358cfe0d124fad289dba8a26f1c632` | fix(web): prevent cross-Run selection in legacy player inspector |
| [#1628](https://github.com/Jasmetk0/squash-tour-beta/pull/1628) | `7dd3c3937d834687317bc1b4fd7c0a3de7390f83` | fix(web): reject cross-Run and cross-player legacy Career responses |
| [#1629](https://github.com/Jasmetk0/squash-tour-beta/pull/1629) | `060b8b2d727d77eca0437df84a2e2a575a3639b6` | fix(web): respect each Run calendar when labeling saved ranking weeks |
| [#1630](https://github.com/Jasmetk0/squash-tour-beta/pull/1630) | `f92710331049d081235803a8120f382c988ab8a3` | fix(web): reset Saved country roster and standings pages on source changes |

## Next boundary

After owner merge, resume a bounded canonical-engine/pre-alpha integration task
from the actual updated buuk. This cleanup improves day-to-day inspection and
prevents specific wrong-source actions; it is not realism calibration, an
entire season/release acceptance or complete Czech/English coverage of legacy UI.
