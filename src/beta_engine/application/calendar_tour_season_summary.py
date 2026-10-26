"""Read-only seasonal history from an already authenticated Saved native Tour.

The caller MUST authenticate the complete Saved Revision and Tour/sporting
lineage via saved_tour() before using this projection. Only finished seasons
with a real signed Season Transition are visible. This never mutates a Run,
publishes a new ranking, or interprets prepared awards as ranking totals.
"""
from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace


def _completed_boundary(state, season_index, closure=None):
    clock = state.week.calendar
    if type(season_index) is not int or not 0 <= season_index < clock.season_count:
        raise ValueError("Season is outside this Run horizon")
    if closure and closure["completed_week"]["season_index"] == season_index:
        from beta_engine.domain.calendar.run_calendar import RunCalendar
        from beta_engine.domain.calendar.run_week_position import RunWeekPosition
        return SimpleNamespace(
            completed_week=RunWeekPosition(calendar=RunCalendar.from_metadata(closure["execution_calendar"]), **closure["completed_week"]),
            target_week=None, command_id=closure["parent_command_id"],
        )
    for transition in state.transitions:
        if (
            transition.completed_week.season_index == season_index
            and transition.completed_week.week == clock.weeks_per_year
            and transition.target_week.season_index == season_index + 1
            and transition.target_week.week == 1
            and transition.public_event.get("kind") == "season_transition_completed"
        ):
            return transition
    raise ValueError("Season has no signed terminal Season Transition")


def completed_season_indices(state, closure=None):
    """Only publicly closed, chronologically signed Seasons."""
    indices = tuple(
        t.completed_week.season_index
        for t in state.transitions
        if (
            t.public_event.get("kind") == "season_transition_completed"
            and t.completed_week.week == state.week.calendar.weeks_per_year
            and t.target_week.season_index == t.completed_week.season_index + 1
            and t.target_week.week == 1
        )
    )

    if closure:
        indices = tuple(sorted({*indices, closure["completed_week"]["season_index"]}))
    return indices


def saved_final_closure(payload, branch_id, inherited=None):
    """Projection only: caller already authenticated this complete Saved revision."""
    return payload.get("run", {}).get("native_branch_closures", {}).get(branch_id) or inherited


def native_tour_identities(state, world):
    players = {p.player_id: p for p in world.players}
    if len(players) != len(world.players):
        raise ValueError("Season summary lacks unique saved national identities")
    # Native participants have no replacement InitialWorld profile. Their
    # names/nationality are frozen by the authenticated actual match projection.
    if getattr(state,"schema_version",None) in {"calendar_tour_authority.v4", "calendar_tour_authority.v5", "native_fork_tour.v1"}:
        for receipt in state.receipts:
            identities = {**receipt.result.get("played", {}).get("participant_identities", {}), **receipt.result.get("participant_identities", {})}
            for pid, identity in identities.items():
                if pid not in players:
                    players[pid] = SimpleNamespace(**identity)
    return players


def native_tour_season_summary(state, world, season_index, *, closure=None):
    """Pure national comparison and actual Edition placements; no inferred wins.

    The final-week ranking is explicitly the ranking PUBLISHED at Week W;
    tournament points from that Week can first publish in next-season Week 1.
    We report awarded Edition points separately from Official Ranking points.
    """
    if (state.run_id, state.branch_id) != (world.run_id, world.branch_id):
        raise ValueError("Season summary requires the same signed Run/Branch world")
    boundary = _completed_boundary(state, season_index, closure)
    players = native_tour_identities(state, world)
    per_country = defaultdict(lambda: {
        "titles": 0, "finals": 0, "semifinals": 0,
        "quarterfinals": 0, "awarded_points": 0,
        "players": set(), "editions": set(),
    })
    per_player = defaultdict(lambda: {
        "titles": 0, "finals": 0, "awarded_points": 0, "editions": set(),
    })
    receipts = {
        r.request.get("command", {}).get("edition_id"): r
        for r in state.receipts
        if r.request.get("command", {}).get("action") == "play"
    }
    played_by_edition = {eid:receipt.result["played"] for eid,receipt in receipts.items()}
    for receipt in state.receipts:
        played_by_edition.update(receipt.result.get("completed_editions", {}))
    editions = []
    for authority in state.editions:
        item = authority.edition
        if item.week.season_index != season_index or not authority.result_confirmed:
            continue
        if item.week.ordinal > boundary.completed_week.ordinal:
            raise ValueError("Season summary attempted to read a future Edition")
        played = played_by_edition.get(item.edition_id)
        if not played or played.get("fingerprint") != authority.tournament_fingerprint:
            raise ValueError("Season Edition lacks authenticated played MatchEngine evidence")
        awards = played["prepared_awards"]
        if len(awards) != item.main_entrant_count:
            raise ValueError("Season Edition player awards differ from recorded field")
        placements = {a["reached_stage"]: a["player_id"] for a in awards if a["reached_stage"] in {"champion", "finalist"}}
        if set(placements) != {"champion", "finalist"}:
            raise ValueError("Season Edition has no authentic final placements")
        if placements["champion"] != played["winner_player_id"]:
            raise ValueError("Season Edition champion differs from signed MatchEngine")
        for award in awards:
            player_id = award["player_id"]
            profile = players.get(player_id)
            if profile is None:
                raise ValueError("Season results refer to an unknown national identity")
            country = profile.country_code
            row = per_country[country]
            row["players"].add(player_id)
            row["editions"].add(item.edition_id)
            row["awarded_points"] += award["main_points"]
            individual = per_player[player_id]
            individual["editions"].add(item.edition_id)
            individual["awarded_points"] += award["main_points"]
            stage = award["reached_stage"]
            if stage == "champion":
                row["titles"] += 1
                individual["titles"] += 1
            elif stage == "finalist":
                row["finals"] += 1
                individual["finals"] += 1
            elif stage == "semifinal":
                row["semifinals"] += 1
            elif stage == "quarterfinal":
                row["quarterfinals"] += 1
        champion_id = placements["champion"]
        finalist_id = placements["finalist"]
        editions.append({
            "edition_id": item.edition_id,
            "name": item.name,
            "week": item.week.week,
            "champion_player_id": champion_id,
            "champion_name": players[champion_id].name,
            "champion_country": players[champion_id].country_code,
            "finalist_player_id": finalist_id,
            "finalist_name": players[finalist_id].name,
            "finalist_country": players[finalist_id].country_code,
            "source_tournament_fingerprint": authority.tournament_fingerprint,
        })
    countries = [{
        "country_code": code,
        "titles": data["titles"], "finals": data["finals"],
        "semifinals": data["semifinals"], "quarterfinals": data["quarterfinals"],
        "awarded_points": data["awarded_points"],
        "distinct_players": len(data["players"]),
        "edition_appearances": len(data["editions"]),
    } for code, data in sorted(per_country.items())]
    top_players = [{
        "player_id": pid, "name": players[pid].name,
        "country_code": players[pid].country_code,
        "titles": data["titles"], "finals": data["finals"],
        "awarded_points": data["awarded_points"],
        "edition_appearances": len(data["editions"]),
    } for pid, data in sorted(per_player.items())]
    top_players.sort(key=lambda r: (-r["titles"], -r["awarded_points"], r["player_id"]))
    final_ranking = next((
        row for row in state.rankings
        if row.week.season_index == season_index
        and row.week.week == state.week.calendar.weeks_per_year
    ), None)
    if final_ranking is None:
        raise ValueError("Completed Season lacks its published Week W ranking")
    return {
        "schema_version": "native_tour_signed_season_summary.v1",
        "run_id": state.run_id,
        "branch_id": state.branch_id,
        "source_tour_fingerprint": state.fingerprint,
        "season_index": season_index,
        "season_label": state.week.calendar.label(season_index),
        "weeks_per_season": state.week.calendar.weeks_per_year,
        "boundary_command_id": boundary.command_id,
        "next_season_index": boundary.target_week.season_index if boundary.target_week else None,
        **({"closing_ranking": closure["closing_ranking"], "closure_marker_fingerprint": closure["fingerprint"]} if closure and not boundary.target_week else {}),
        "completed_edition_count": len(editions),
        "countries": countries,
        "editions": sorted(editions, key=lambda row: (row["week"], row["edition_id"])),
        "players": top_players,
        "last_week_published_ranking": {
            "week": final_ranking.week.week,
            "source_fingerprint": final_ranking.fingerprint,
            "top_players": [
                {"player_id": r.player_id, "rank": r.rank, "points": r.points}
                for r in final_ranking.rows[:10]
            ],
        },
    }


def compare_completed_seasons(state, world, season_index, compare_to=None, *, closure=None):
    selected = native_tour_season_summary(state, world, season_index, closure=closure)
    if compare_to is None:
        return {"selected": selected, "comparison": None, "country_deltas": []}
    other = native_tour_season_summary(state, world, compare_to, closure=closure)
    rows = {r["country_code"]: r for r in selected["countries"]}
    prior = {r["country_code"]: r for r in other["countries"]}
    deltas = [
        {
            "country_code": code,
            "titles_delta": rows.get(code, {}).get("titles", 0) - prior.get(code, {}).get("titles", 0),
            "finals_delta": rows.get(code, {}).get("finals", 0) - prior.get(code, {}).get("finals", 0),
            "awarded_points_delta": rows.get(code, {}).get("awarded_points", 0) - prior.get(code, {}).get("awarded_points", 0),
        }
        for code in sorted(set(rows) | set(prior))
    ]
    return {"selected": selected, "comparison": other, "country_deltas": deltas}
