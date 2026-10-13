# Saved Edition Group Match Schedule v1 — 13 October 2026

Read-only Master v80 Edition group chronology. This PR follows merged #1421
and never substitutes current Admin, official Viewer or a recalculated fixture
for a reachable historical Saved Revision.

## Source and validation

The new optional `group_schedule` field in the existing
`run_saved_tour_edition.v1` response is projected solely from the
restore-grade-validated `simulation_slots.group_match_schedules` component.
A saved Schedule is accepted only alongside saved Format and Topology
authorities from the identical Event, original owner Branch and Run. All
stored fingerprints and command IDs must agree. The canonical
`TournamentGroupMatchScheduleBuilder.build` replays the stored immutable
Format/Topology and must exactly equal the saved Schedule. Incoherent,
duplicate, stale, foreign-Branch or forged records fail closed.

The source includes authentic round-robin group, top/bottom players,
Match Day ordinal, within-day order and effective BO3/BO5 format. It is NOT a
calendar date or wall-clock start. Published scoreline and Match replay links
exist only for a match independently present in the Saved Revision's canonical
group-phase Tournament Result. Where absent, display "Not canonically
published", never invent a result or rally history. A result contradicting
the saved pairing raises a conflict. Pure-groups and groups+knockout formats
are handled by the same immutable group Schedule; knockout phase results
remain separately shown via the existing canonical results authority.

## UI

Within the Edition's **Schedule & matches** tab, the new group section
displays Match Day, group, order, pairing, BO format and optional canonical
result/link. Existing global Week Simulation Schedule v2, Main/Qualification
anchors, Results and the six tabs remain intact. The Draw-only Main/
Qualification switch is unchanged. Missing group authority yields no group
table and does not affect older knockout Editions.

## Tests/limitations

Pure read-model tests cover a genuine deterministic 2x3 and 1x4 group
schedule, absence, foreign identity, duplicates and fingerprints. Frontend
tests cover CS/EN rendering/unknown result and wrong provenance. Existing
real Chromium Save/SQLite-restart acceptance protects the non-group paths;
a **real completed hybrid tournament browser fixture** and group standings
(tie-break and W/O) require separate, specialized authoring/acceptance and are
not claimed in this PR. No new CI workflow is created.
