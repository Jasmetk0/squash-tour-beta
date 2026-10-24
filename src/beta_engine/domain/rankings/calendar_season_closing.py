"""Closing-only Best N at a Run boundary; never opens/publishes a future week."""

from beta_engine.domain.rankings.calendar_terminal_result import (
    CalendarTerminalRankingResult,
    result_activation_ordinal,
)
from beta_engine.domain.run_packages import canonical_hash


def calculate_calendar_season_closing(*, calendar, completed_week, policy, players, results, previous, inherited_terminal_sources=()):
    completed = calendar.ordinal(completed_week.season_index, completed_week.week)
    if completed_week.week != calendar.weeks_per_year:
        raise ValueError("Closing Ranking requires the actual last Season Week")
    boundary = completed + 1
    ids = {p.player_id for p in players}
    if len(ids) != len(players) or len({p.tie_break_token for p in players}) != len(players):
        raise ValueError("Closing Ranking player identities/tokens must be unique")
    if len({(r.edition_id, r.player_id) for r in results}) != len(results):
        raise ValueError("Closing Ranking requires resolved unique Edition/player results")
    eligible = {pid: [] for pid in ids}
    for result in results:
        end = calendar.ordinal(result.completed_week.season_index, result.completed_week.week)
        activation = result_activation_ordinal(result, calendar)
        if isinstance(result, CalendarTerminalRankingResult) and (
            result.run_id != previous.run_id or (
                result.branch_id != previous.branch_id
                and (result.source_fingerprint, result.run_id, result.branch_id) not in inherited_terminal_sources
            )
        ):
            raise ValueError("Closing Ranking terminal result has a foreign owner")
        if result.player_id not in ids or not end < activation <= boundary or end > completed:
            raise ValueError("Closing Ranking result source is foreign/future")
        age = boundary - activation
        validity = result.validity_weeks if result.validity_weeks is not None else calendar.weeks_per_year
        if result.ranked and age < validity:
            eligible[result.player_id].append(result)
    prior = {r.player_id: r.rank for r in previous.rows}
    candidates = []
    for player in players:
        if player.retired or calendar.ordinal(player.tour_entry_week.season_index, player.tour_entry_week.week) >= boundary:
            continue
        counted = tuple(sorted(eligible[player.player_id], key=lambda r: (
            -r.points, -calendar.ordinal(r.completed_week.season_index, r.completed_week.week), r.edition_id,
        ))[:policy.best_n])
        points = sum(r.points for r in counted)
        profile = tuple(-r.points for r in counted) + (0,) * (policy.best_n - len(counted))
        ages = tuple(-calendar.ordinal(r.completed_week.season_index, r.completed_week.week) for r in counted)
        ages += (1,) * (policy.best_n - len(counted))
        candidates.append(((-points, profile, ages if points else (), prior.get(player.player_id, float("inf")), player.tie_break_token), player.player_id, points, counted))
    candidates.sort(key=lambda item: item[0])
    body = {
        "schema_version": "calendar_season_closing_ranking.v1",
        "run_id": previous.run_id, "branch_id": previous.branch_id,
        "execution_calendar": calendar.to_metadata(), "completed_week": completed_week.model_dump(mode="json"),
        "eligibility_boundary_ordinal": boundary, "policy": policy.model_dump(mode="json"),
        "predecessor_official_fingerprint": previous.fingerprint,
        "input_fingerprint": canonical_hash({
            "players": [p.model_dump(mode="json") for p in sorted(players, key=lambda p: p.player_id)],
            "results": [r.model_dump(mode="json") for r in sorted(results, key=lambda r: (r.edition_id, r.player_id))],
        }),
        "rows": [{"rank": rank, "player_id": pid, "points": points,
            "counted_results": [r.model_dump(mode="json") for r in counted]}
            for rank, (_, pid, points, counted) in enumerate(candidates, 1)],
    }
    return {**body, "fingerprint": canonical_hash(body)}
