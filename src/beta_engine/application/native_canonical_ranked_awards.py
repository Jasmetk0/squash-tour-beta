"""Derive Ranked point evidence from accepted native FAX Q/Main records."""

from dataclasses import dataclass

from beta_engine.application.canonical_tournament_points import (
    build_tournament_point_award_authority,
)
from beta_engine.application.season_point_awards_service import (
    FrozenPointAwardAuthority,
)
from beta_engine.domain.matches.models import MatchResult, MatchTerminationReason
from beta_engine.domain.players.calendar_continuation_match import (
    CalendarContinuationMatch,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.canonical_knockout_feeders import (
    CanonicalKnockoutFeederPlan,
)
from beta_engine.domain.tournaments.native_canonical_knockout import (
    native_progress,
    saved_ranked_point_table,
)
from beta_engine.domain.tournaments.point_award_authority import (
    TournamentPointAwardAuthority,
)
from beta_engine.domain.tournaments.result_authority import (
    TournamentMatchResultAuthority,
    TournamentResultAuthority,
    assemble_knockout_tournament_result,
)


@dataclass(frozen=True, slots=True)
class NativeCanonicalRankedAwards:
    result: TournamentResultAuthority
    awards: TournamentPointAwardAuthority


def _scoreline(result: MatchResult) -> str:
    parts = [
        f"{game.winner_games}-{game.loser_games}"
        if game.winner_player_id == result.winner_player_id
        else f"{game.loser_games}-{game.winner_games}"
        for game in result.sets
    ]
    if result.termination_reason == MatchTerminationReason.RETIREMENT:
        parts.append("RET")
    if not parts:
        raise ValueError("Canonical played match has no game score")
    return " ".join(parts)


def prepare_native_canonical_ranked_awards(
    *,
    plan: CanonicalKnockoutFeederPlan,
    matches: tuple[CalendarContinuationMatch, ...],
) -> NativeCanonicalRankedAwards:
    """Project one completed Ranked Draw without saving or publishing anything.

    The caller supplies the authenticated Saved plan and accepted slot records;
    feeder validation cannot substitute for the owner's slot-ledger proof.
    """
    event = plan.source.source_event
    if event.ranking_status != "ranked":
        raise ValueError("Native canonical point projection requires a Ranked source")
    if (
        event.duration_in_season_weeks != 1
        or event.start_season_week != event.season_week
        or event.end_season_week != event.season_week
        or any(match.week.week != event.season_week for match in matches)
    ):
        raise ValueError(
            "Native canonical point projection requires exact same-week play"
        )
    if plan.calendar.weeks_per_year != 61:
        raise ValueError(
            "Canonical point authority requires its existing 61-week ranking clock"
        )

    table = saved_ranked_point_table(event)

    progress = native_progress(plan, matches)
    if progress.champion_player_id is None or len(progress.accepted_match_ids) != len(
        plan.topology.plans
    ):
        raise ValueError(
            "Native canonical point projection requires every executable match completed"
        )

    accepted = {match.match_id: match for match in matches}
    terminal = accepted[plan.topology.terminal_group_id]
    week = RankingWeek(season_index=terminal.week.season_index, week=terminal.week.week)
    if (event.calendar_year, event.year_week) != (
        terminal.week.calendar_position.calendar_year,
        terminal.week.calendar_position.year_week,
    ):
        raise ValueError(
            "Native canonical points cannot reinterpret the Saved source date"
        )

    draw = plan.source.draw
    byes = dict(progress.bye_advances)
    rows = []
    for bracket in (*draw.qualification_brackets, draw.main):
        for node in bracket.nodes:
            record = accepted.get(node.node_id)
            if record is None:
                # Automatic advancement is result evidence, never an accepted MatchEngine record.
                winner = byes[node.node_id]
                loser = None
                scoreline = "BYE"
                result_fingerprint = canonical_hash(
                    {
                        "schema_version": "native_canonical_bye_result.v1",
                        "source_plan_fingerprint": progress.source_plan_fingerprint,
                        "match_id": node.node_id,
                        "winner_player_id": winner,
                    }
                )
            else:
                winner = record.result.winner_player_id
                loser = record.result.loser_player_id
                scoreline = _scoreline(record.result)
                result_fingerprint = record.fingerprint
            rows.append(
                TournamentMatchResultAuthority(
                    match_id=node.node_id,
                    draw_type=bracket.draw_type,
                    round_number=node.round_number,
                    bracket_position=node.round_sequence,
                    winner_player_id=winner,
                    loser_player_id=loser,
                    scoreline=scoreline,
                    result_fingerprint=result_fingerprint,
                )
            )

    result = assemble_knockout_tournament_result(
        run_id=draw.run_id,
        branch_id=draw.branch_id,
        week=week,
        draw=draw,
        matches=tuple(rows),
        native_feeder_plan_fingerprint=progress.source_plan_fingerprint,
    )
    awards = build_tournament_point_award_authority(
        result=result,
        point_authority=FrozenPointAwardAuthority(
            ranking_status="ranked",
            point_distribution=table,
            point_distribution_source="saved_native_fax_draw.ranking_points.v1",
        ),
        seed=plan.source.draw_input.draw_seed,
    )
    return NativeCanonicalRankedAwards(result=result, awards=awards)
