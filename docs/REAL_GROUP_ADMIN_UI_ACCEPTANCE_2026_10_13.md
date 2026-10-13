# Real group-tournament UI acceptance — 13 October 2026

## Previously unreachable browser path

The canonical tournament preparation keeps normal ranking-application events on
the default knockout Draw Input path until Format is chosen. PR #1425 only
displayed group controls when `next_required_action=configure_tournament_format`,
which is emitted for *Finals* Entry Fields, not ordinary ranking-application
events. Thus the ordinary real Run browser test had to POST Group Rules, Format,
Topology and Match Schedule via direct HTTP calls instead of the actual Admin.

## This change

- The ordinary, verified, frozen ranking-application Entry Field now offers an
  **explicit** group choice *before* a Draw Input, Draw or Format is frozen.
  Normal knockout UI remains available; nothing automatically adopts groups.
- Confirmation and strict group partition restrictions from
  `GroupFormatSetupPanel` stay in force. The controls are never shown on a
  different/historical Run/Branch or over an already frozen Draw/Format.
- The dedicated real Chromium/SQLite test adopts BO3 Group Rules, pure groups,
  Topology and six-round-robin-match schedule **using production browser UI**.
  Read-only HTTP checks confirm actual durable preparation and schedule.
  The existing real sporting simulation, Saved Edition and SQLite restart checks
  remain mandatory and unchanged.

There is no new sporting default for hybrid crossings, no fixture result,
no implicit Run Save, and no changed production backend authority.
