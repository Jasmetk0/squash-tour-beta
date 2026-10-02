# Copied-FAX current-week Tournament Ranking Snapshot bootstrap

## Purpose

Advance the copied-FAX long-acceptance fixture through the first canonical Tournament Preparation phase without inventing Entry, Wild Card or Draw policy.

The service automates only a provenance-preserving mechanical step: bind every current-week World Tour Edition to the latest already-published Official Ranking at or before that week.

## Reviewed contract

Preview freezes:

- current authoritative RankingWeek,
- sorted current-week World Tour event IDs from the Run-owned Calendar Package,
- selected published Official Ranking week + fingerprint.

The preview fingerprint intentionally excludes current Tournament Ranking Snapshot adoption state, so an exact retry remains valid after successful adoption as long as the underlying week/calendar/publication inputs are unchanged.

## Apply

Apply executes under `BEGIN IMMEDIATE`, recomputes the reviewed preview and then, for each current-week event:

- adopts the selected published Official Ranking through `TournamentRankingSnapshotAuthorityStore`, or
- treats an already-identical authority as an exact retry,
- rejects any event that already froze a different ranking snapshot.

After application every event must have advanced beyond `ranking_snapshot_required` in the canonical Tournament Preparation state machine.

## Acceptance result

The persisted 1,000-player copied-FAX Week-1 integration fixture contains two World Tour Editions in SW1. Both start at `ranking_snapshot_required`; the reviewed bulk apply advances both to `entry_field_required`, and an exact second apply produces only retry evidence.

## Boundary

This slice does not decide who enters a tournament. It does not create applications, Entry Fields, Wild Cards, formats, draws or schedules. The next pre-alpha blocker is therefore the canonical Entry Field/application surface itself.
