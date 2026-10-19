"""Saved-only, versioned historical records for the bounded native Tour.

No writes, new clock, generated rankings, match inference, or hidden unlocks.
Call ONLY after full Saved Revision and sporting/Tour lineage authentication.
Records are cumulative over explicit *completed season* windows. Tied holders
are co-holders; history is stamped at closure, NOT fabricated at match time.
"""
from __future__ import annotations

from collections import defaultdict

from beta_engine.application.calendar_tour_season_summary import (
    completed_season_indices,
    native_tour_season_summary,
)

# Small extensible catalog of measurable real-Edition facts, not inferred
# on-court wins or current ranking-points records. All are nonnegative.
METRICS = (
    ("player", "titles"),
    ("player", "finals"),
    ("player", "awarded_points"),
    ("country", "titles"),
    ("country", "finals"),
    ("country", "awarded_points"),
)
FIELDS = ("titles", "finals", "awarded_points")


def _ranking(candidates, field, *, limit):
    ordered = sorted(
        (v for v in candidates.values() if v[field] > 0),
        key=lambda row: (-row[field], row["entity_id"]),
    )
    ranked = []
    prev = None
    rank = 0
    for position, row in enumerate(ordered, start=1):
        if row[field] != prev:
            rank = position
            prev = row[field]
        if len(ranked) >= limit:
            break
        ranked.append({**row, "rank": rank})
    return ranked


def _empty(entity_id, *, scope, identities):
    if scope == "player":
        profile = identities[entity_id]
        return {
            "entity_id": entity_id, "label": profile.name,
            "country_code": profile.country_code,
            "titles": 0, "finals": 0, "awarded_points": 0,
        }
    return {
        "entity_id": entity_id, "label": entity_id,
        "country_code": entity_id,
        "titles": 0, "finals": 0, "awarded_points": 0,
    }


def signed_tour_records(
    state, world, *, as_of_season_index=None, from_season_index=0,
    country_code=None, leaderboard_limit=20,
):
    """Compute cumulative leaderboards and complete co-holder changes.

    The caller authenticates the entire Saved revision and the contained
    initial world *before* invoking this pure projection. The cutoff cannot
    name an in-progress Season, even if its Editions were confirmed in Draft.
    Country filters scope both the leaderboard and holder chronology.
    """
    if (state.run_id, state.branch_id) != (world.run_id, world.branch_id):
        raise ValueError("Native Records require the same Saved Run/Branch")
    if type(from_season_index) is not int or from_season_index < 0:
        raise ValueError("Records period start must be a nonnegative completed season index")
    if type(leaderboard_limit) is not int or not 1 <= leaderboard_limit <= 100:
        raise ValueError("Records leaderboard limit must be between 1 and 100")
    if country_code is not None and (
        not isinstance(country_code, str)
        or len(country_code) != 3 or not country_code.isalpha()
        or country_code != country_code.upper()
    ):
        raise ValueError("Records filter requires uppercase three-letter country")
    closed = tuple(sorted(set(completed_season_indices(state))))
    if not closed:
        raise ValueError("Native Records require at least one Signed closed Season")
    if as_of_season_index is None:
        as_of_season_index = closed[-1]
    if type(as_of_season_index) is not int or as_of_season_index not in closed:
        raise ValueError("Records as-of season is not Signed and completed")
    if from_season_index > as_of_season_index or from_season_index not in closed:
        raise ValueError("Records period start is not a Signed completed season")

    identities = {p.player_id: p for p in world.players}
    if len(identities) != len(world.players):
        raise ValueError("Records initial world contains duplicate identities")
    totals = {"player": {}, "country": {}}
    histories = {(scope, field): [] for scope, field in METRICS}
    previous = {(scope, field): (0, ()) for scope, field in METRICS}
    included_seasons = [
        index for index in closed
        if from_season_index <= index <= as_of_season_index
    ]
    source_seasons = []
    counted_editions = 0
    for index in included_seasons:
        summary = native_tour_season_summary(state, world, index)
        counted_editions += summary["completed_edition_count"]
        source_seasons.append({
            "season_index": index,
            "season_label": summary["season_label"],
            "boundary_command_id": summary["boundary_command_id"],
            "completed_edition_count": summary["completed_edition_count"],
            "source_tour_fingerprint": summary["source_tour_fingerprint"],
            "published_ranking_fingerprint": (
                summary["last_week_published_ranking"]["source_fingerprint"]
            ),
        })
        for scope, values, id_key in (
            ("player", summary["players"], "player_id"),
            ("country", summary["countries"], "country_code"),
        ):
            for row in values:
                eid = row[id_key]
                if (scope == "player" and eid not in identities):
                    raise ValueError("Records have a foreign player identity")
                if country_code is not None and (
                    (scope == "player" and identities[eid].country_code != country_code)
                    or (scope == "country" and eid != country_code)
                ):
                    continue
                total = totals[scope].setdefault(
                    eid, _empty(eid, scope=scope, identities=identities)
                )
                for field in FIELDS:
                    total[field] += row[field]

        for scope, field in METRICS:
            maximum = max((row[field] for row in totals[scope].values()), default=0)
            holders = tuple(sorted(
                eid for eid, row in totals[scope].items()
                if maximum > 0 and row[field] == maximum
            ))
            prior_maximum, prior_holders = previous[(scope, field)]
            if maximum > 0 and (
                maximum != prior_maximum or holders != prior_holders
            ):
                histories[(scope, field)].append({
                    "season_index": index,
                    "season_label": summary["season_label"],
                    "record_value": maximum,
                    "holder_ids": list(holders),
                    "change": (
                        "established" if prior_maximum == 0
                        else "improved" if maximum > prior_maximum
                        else "tied"
                    ),
                    "boundary_command_id": summary["boundary_command_id"],
                })
            previous[(scope, field)] = maximum, holders

    records = []
    for scope, field in METRICS:
        value, holders = previous[(scope, field)]
        rows = totals[scope]
        ranked = _ranking(rows, field, limit=leaderboard_limit)
        # The holder set can exceed the visible top-N table. Never drop any
        # tied record holders or present truncated co-holders as all holders.
        records.append({
            "record_id": f"native_tour.{scope}.{field}.v1",
            "scope": scope,
            "metric": field,
            "value": value,
            "holders": [
                _empty(eid, scope=scope, identities=identities)
                | {key: rows[eid][key] for key in FIELDS}
                for eid in holders
            ],
            "holder_history": histories[(scope, field)],
            "leaderboard": ranked,
            "leaderboard_total": len([
                row for row in rows.values() if row[field] > 0
            ]),
        })

    return {
        "schema_version": "native_tour_signed_records.v1",
        "run_id": state.run_id,
        "branch_id": state.branch_id,
        "source_tour_fingerprint": state.fingerprint,
        "as_of_season_index": as_of_season_index,
        "from_season_index": from_season_index,
        "country_code": country_code,
        "leaderboard_limit": leaderboard_limit,
        "completed_seasons": included_seasons,
        "completed_edition_count": counted_editions,
        "source_seasons": source_seasons,
        "records": records,
    }
