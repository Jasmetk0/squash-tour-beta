"""Canonical hybrid Tournament Edition result + ranking-source closure."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
    prepare_canonical_tournament_ranking_sources,
    prepare_final_season_closing_ranking_results,
)
from beta_engine.domain.matches.models import MatchResult, MatchTerminationReason
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupResultReceipt,
    TournamentGroupStandingsAuthority,
)
from beta_engine.domain.tournaments.hybrid_knockout_bracket_authority import (
    TournamentHybridKnockoutBracketAuthority,
)
from beta_engine.domain.tournaments.hybrid_ranking_policy_authority import (
    TournamentHybridRankingPolicyAuthority,
)
from beta_engine.domain.tournaments.models import CalendarEvent
from beta_engine.domain.tournaments.prize_money_award_authority import (
    build_tournament_prize_money_award_authority,
)
from beta_engine.domain.tournaments.point_award_authority import (
    TournamentPhasePointComponent,
    TournamentPlayerPointAwardAuthority,
    TournamentPointAwardAuthority,
)
from beta_engine.domain.tournaments.result_authority import (
    TournamentMatchResultAuthority,
    TournamentPlayerResultAuthority,
    TournamentResultAuthority,
)
from beta_engine.domain.tournaments.walkover_authority import TournamentWalkoverResult
from beta_engine.infrastructure.db.authoritative_group_state import (
    load_authoritative_group,
)
from beta_engine.infrastructure.db.models import (
    AdoptedTournamentAuthorityModel,
    SimulationEventGroupModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.tournament_group_match_schedule_authority import (
    TournamentGroupMatchScheduleAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_group_standings_authority import (
    TournamentGroupStandingsAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_hybrid_knockout_bracket_authority import (
    TournamentHybridKnockoutBracketAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_hybrid_ranking_policy_authority import (
    TournamentHybridRankingPolicyAuthorityStore,
)


class TournamentHybridClosureConflict(ValueError):
    """Frozen hybrid evidence conflicts with an already-owned tournament source."""


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _scoreline_from_group_receipt(receipt: TournamentGroupResultReceipt) -> str:
    if receipt.result_kind == "walkover":
        return "W/O"
    if not receipt.games:
        raise ValueError("Played group result has no game evidence")
    return " ".join(
        f"{game.winner_points}-{game.loser_points}" for game in receipt.games
    )


def _scoreline_from_knockout_result(
    result: MatchResult | TournamentWalkoverResult,
) -> str:
    if isinstance(result, TournamentWalkoverResult):
        return "W/O"
    if not result.sets:
        raise ValueError("Played knockout result has no set evidence")
    score = " ".join(
        f"{item.winner_games}-{item.loser_games}" for item in result.sets
    )
    if result.termination_reason == MatchTerminationReason.RETIREMENT:
        return f"{score} RET"
    return score


def _knockout_loss_stage(*, round_number: int, round_count: int) -> str:
    distance = round_count - round_number
    mapping = {
        0: "finalist",
        1: "semifinal",
        2: "quarterfinal",
        3: "round_of_16",
        4: "round_of_32",
        5: "round_of_64",
        6: "round_of_128",
    }
    try:
        return mapping[distance]
    except KeyError as exc:
        raise ValueError("Hybrid knockout stage depth is unsupported") from exc


def _knockout_entrant_player_ids(
    bracket: TournamentHybridKnockoutBracketAuthority,
) -> frozenset[str]:
    entrants = {
        source.removeprefix("player:")
        for match in bracket.matches
        if match.round_number == 1
        for source in match.participant_sources
        if source.startswith("player:")
    }
    if len(entrants) != bracket.entrant_count:
        raise ValueError("Hybrid Knockout Bracket entrant provenance is incomplete")
    return frozenset(entrants)


def _frozen_calendar_event(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
    completed_week: RankingWeek,
) -> CalendarEvent:
    row = session.get(
        AdoptedTournamentAuthorityModel,
        (run_id, branch_id, completed_week.ordinal),
    )
    if row is None:
        raise ValueError(
            "Hybrid Tournament closure requires frozen adopted tournament evidence"
        )
    payload = json.loads(row.package_json)
    if payload.get("schema_version") != "adopted_tournament_authority.v7":
        raise ValueError(
            "Hybrid Tournament closure requires canonical adopted authority v7"
        )
    matches = [
        item
        for item in payload.get("tournaments", [])
        if item.get("event_id") == event_id
    ]
    if len(matches) != 1:
        raise ValueError(
            "Hybrid Tournament closure cannot resolve one frozen Calendar Event"
        )
    event = CalendarEvent.model_validate(matches[0]["calendar_event"])
    if event.event_id != event_id:
        raise ValueError("Hybrid Tournament frozen Calendar Event identity mismatch")
    return event


def required_hybrid_knockout_stages(
    bracket: TournamentHybridKnockoutBracketAuthority,
) -> tuple[str, ...]:
    stages = {"champion"}
    stages.update(
        _knockout_loss_stage(
            round_number=round_number,
            round_count=bracket.round_count,
        )
        for round_number in range(1, bracket.round_count + 1)
    )
    return tuple(sorted(stages))


def build_hybrid_tournament_result_authority(
    *,
    session: Session,
    run_id: str,
    branch_id: str,
    event_id: str,
    completed_week: RankingWeek,
    standings: TournamentGroupStandingsAuthority,
    bracket: TournamentHybridKnockoutBracketAuthority,
) -> TournamentResultAuthority:
    """Freeze one event result from exact group + knockout canonical receipts."""

    if (
        standings.run_id,
        standings.branch_id,
        standings.event_id,
        bracket.run_id,
        bracket.branch_id,
        bracket.event_id,
    ) != (
        run_id,
        branch_id,
        event_id,
        run_id,
        branch_id,
        event_id,
    ):
        raise ValueError("Hybrid Tournament Result source scope mismatch")

    schedule = TournamentGroupMatchScheduleAuthorityStore(session).get(
        run_id=run_id,
        branch_id=branch_id,
        event_id=event_id,
    )
    if schedule is None or schedule.fingerprint != standings.group_match_schedule_fingerprint:
        raise ValueError("Hybrid Tournament Result lacks current Group Match Schedule")
    schedule_by_id = {match.match_id: match for match in schedule.matches}
    receipts_by_id = {receipt.match_id: receipt for receipt in standings.source_results}
    if set(schedule_by_id) != set(receipts_by_id):
        raise ValueError("Hybrid Tournament Result group receipts are incomplete")

    players: dict[str, dict[str, object]] = {}
    for group in standings.groups:
        for row in group.rows:
            players[row.player_id] = {
                "group_index": group.group_index,
                "group_position": row.position,
                "played_group_wins": 0,
                "group_walkovers_received": row.walkovers_received,
                "wins": 0,
                "losses": 0,
                "walkovers_received": row.walkovers_received,
                "retired_or_walkover_loss": bool(row.walkovers_conceded),
                "knockout_stage": None,
                "eliminated_by": None,
                "last_match_id": None,
                "final_round_number": None,
            }
    if not players:
        raise ValueError("Hybrid Tournament Result has no group players")

    match_results: list[TournamentMatchResultAuthority] = []
    for scheduled in schedule.matches:
        receipt = receipts_by_id[scheduled.match_id]
        if receipt.winner_player_id not in players or receipt.loser_player_id not in players:
            raise ValueError("Hybrid group receipt references unknown player")
        if receipt.result_kind == "played":
            players[receipt.winner_player_id]["wins"] = (
                int(players[receipt.winner_player_id]["wins"]) + 1
            )
            players[receipt.loser_player_id]["losses"] = (
                int(players[receipt.loser_player_id]["losses"]) + 1
            )
            players[receipt.winner_player_id]["played_group_wins"] = (
                int(players[receipt.winner_player_id]["played_group_wins"]) + 1
            )
        players[receipt.winner_player_id]["last_match_id"] = scheduled.match_id
        players[receipt.loser_player_id]["last_match_id"] = scheduled.match_id
        match_results.append(
            TournamentMatchResultAuthority(
                match_id=scheduled.match_id,
                draw_type="group",
                round_number=scheduled.match_day_ordinal,
                bracket_position=scheduled.topology_match_index,
                winner_player_id=receipt.winner_player_id,
                loser_player_id=receipt.loser_player_id,
                scoreline=_scoreline_from_group_receipt(receipt),
                result_fingerprint=receipt.result_fingerprint,
            )
        )

    bracket_ids = tuple(match.match_id for match in bracket.matches)
    rows = session.scalars(
        select(SimulationEventGroupModel).where(
            SimulationEventGroupModel.run_id == run_id,
            SimulationEventGroupModel.branch_id == branch_id,
            SimulationEventGroupModel.week_ordinal == completed_week.ordinal,
            SimulationEventGroupModel.match_id.in_(bracket_ids),
        )
    ).all()
    by_match = {row.match_id: row for row in rows}
    if set(by_match) != set(bracket_ids):
        missing = sorted(set(bracket_ids) - set(by_match))
        raise ValueError(
            "Hybrid Tournament Result requires completed knockout receipts for: "
            + ", ".join(missing)
        )

    terminal_result: MatchResult | TournamentWalkoverResult | None = None
    for match in sorted(bracket.matches, key=lambda item: (item.round_number, item.match_index)):
        decoded = load_authoritative_group(by_match[match.match_id])
        result = decoded.result
        if (
            result.winner_player_id not in players
            or result.loser_player_id not in players
        ):
            raise ValueError("Hybrid knockout result references unknown group player")

        winner = players[result.winner_player_id]
        loser = players[result.loser_player_id]
        if isinstance(result, TournamentWalkoverResult):
            winner["walkovers_received"] = int(winner["walkovers_received"]) + 1
            loser["retired_or_walkover_loss"] = True
        else:
            winner["wins"] = int(winner["wins"]) + 1
            loser["losses"] = int(loser["losses"]) + 1
            if result.termination_reason == MatchTerminationReason.RETIREMENT:
                loser["retired_or_walkover_loss"] = True

        loss_stage = _knockout_loss_stage(
            round_number=match.round_number,
            round_count=bracket.round_count,
        )
        loser["knockout_stage"] = loss_stage
        loser["eliminated_by"] = result.winner_player_id
        loser["last_match_id"] = match.match_id
        loser["final_round_number"] = match.round_number
        winner["last_match_id"] = match.match_id
        winner["final_round_number"] = match.round_number

        match_results.append(
            TournamentMatchResultAuthority(
                match_id=match.match_id,
                draw_type="knockout",
                round_number=match.round_number,
                bracket_position=match.match_index,
                winner_player_id=result.winner_player_id,
                loser_player_id=result.loser_player_id,
                scoreline=_scoreline_from_knockout_result(result),
                result_fingerprint=decoded.result_fingerprint,
            )
        )
        if match.match_id == bracket.terminal_match_id:
            terminal_result = result

    if terminal_result is None:
        raise ValueError("Hybrid Tournament Result lacks terminal knockout result")
    champion_id = terminal_result.winner_player_id
    finalist_id = terminal_result.loser_player_id
    players[champion_id]["knockout_stage"] = "champion"

    result_players = []
    for player_id in sorted(players):
        state = players[player_id]
        knockout_stage = state["knockout_stage"]
        reached_stage = (
            str(knockout_stage)
            if knockout_stage is not None
            else f"group_position_{int(state['group_position'])}"
        )
        result_players.append(
            TournamentPlayerResultAuthority(
                player_id=player_id,
                draw_type="hybrid",
                reached_stage=reached_stage,
                final_round_number=(
                    int(state["final_round_number"])
                    if state["final_round_number"] is not None
                    else None
                ),
                eliminated_by_player_id=(
                    str(state["eliminated_by"])
                    if state["eliminated_by"] is not None
                    else None
                ),
                last_match_id=(
                    str(state["last_match_id"])
                    if state["last_match_id"] is not None
                    else None
                ),
                wins=int(state["wins"]),
                losses=int(state["losses"]),
                walkovers_received=int(state["walkovers_received"]),
                retired_or_walkover_loss=bool(state["retired_or_walkover_loss"]),
                group_index=int(state["group_index"]),
                group_position=int(state["group_position"]),
                played_group_wins=int(state["played_group_wins"]),
                group_walkovers_received=int(state["group_walkovers_received"]),
                knockout_reached_stage=(
                    str(knockout_stage) if knockout_stage is not None else None
                ),
            )
        )

    return TournamentResultAuthority(
        schema_version="tournament_result_authority.v2",
        run_id=run_id,
        branch_id=branch_id,
        event_id=event_id,
        completed_week=completed_week,
        group_standings_authority_fingerprint=standings.fingerprint,
        hybrid_knockout_bracket_authority_fingerprint=bracket.fingerprint,
        champion_player_id=champion_id,
        finalist_player_id=finalist_id,
        players=tuple(result_players),
        matches=tuple(
            sorted(
                match_results,
                key=lambda item: (
                    item.draw_type != "group",
                    item.round_number,
                    item.bracket_position,
                    item.match_id,
                ),
            )
        ),
    )


def hybrid_ranking_policy_blockers(
    *,
    standings: TournamentGroupStandingsAuthority,
    bracket: TournamentHybridKnockoutBracketAuthority,
    policy: TournamentHybridRankingPolicyAuthority | None,
) -> tuple[str, ...]:
    """Return product/config blockers without reading or mutating match execution state."""

    if policy is None:
        return ("hybrid_ranking_policy_required",)
    blockers: list[str] = []
    configured = dict(policy.knockout_stage_points)
    missing = [
        stage
        for stage in required_hybrid_knockout_stages(bracket)
        if stage not in configured
    ]
    if missing:
        blockers.append("hybrid_ranking_policy_incomplete")
    if policy.played_group_win_points > 0 and any(
        receipt.result_kind == "walkover"
        for receipt in standings.source_results
    ):
        blockers.append("hybrid_group_walkover_ranking_unresolved")
    return tuple(blockers)


def hybrid_tournament_closure_blockers(
    *,
    standings: TournamentGroupStandingsAuthority,
    bracket: TournamentHybridKnockoutBracketAuthority,
    policy: TournamentHybridRankingPolicyAuthority | None,
    calendar_event: CalendarEvent | None,
) -> tuple[str, ...]:
    blockers = list(
        hybrid_ranking_policy_blockers(
            standings=standings,
            bracket=bracket,
            policy=policy,
        )
    )
    if calendar_event is None:
        blockers.append("hybrid_calendar_event_evidence_required")
    elif calendar_event.ranking_status.value != "ranked":
        blockers.append("hybrid_ranked_closure_required")
    return tuple(dict.fromkeys(blockers))


def build_hybrid_tournament_point_award_authority(
    *,
    result: TournamentResultAuthority,
    policy: TournamentHybridRankingPolicyAuthority,
) -> TournamentPointAwardAuthority:
    """Compose one ranking award/player from explicit group + knockout phase rules."""

    if result.schema_version != "tournament_result_authority.v2":
        raise ValueError("Hybrid point composition requires Tournament Result v2")
    if (result.run_id, result.branch_id, result.event_id) != (
        policy.run_id,
        policy.branch_id,
        policy.event_id,
    ):
        raise ValueError("Hybrid point policy/result scope mismatch")

    # Master v68 defines W/O as a group-table-only win and does not decide whether
    # a separate Official Ranking 'group win' reward should also be granted for it.
    # Do not silently decide that question.
    if policy.played_group_win_points > 0 and any(
        (player.group_walkovers_received or 0) > 0 for player in result.players
    ):
        raise ValueError(
            "Hybrid group W/O ranking-phase reward is unresolved; cannot compose points"
        )

    knockout_distribution = dict(policy.knockout_stage_points)
    required = {
        player.knockout_reached_stage
        for player in result.players
        if player.knockout_reached_stage is not None
    }
    missing = sorted(stage for stage in required if stage not in knockout_distribution)
    if missing:
        raise ValueError(
            "Hybrid ranking policy lacks knockout stage values: " + ", ".join(missing)
        )

    distribution = {
        "group:played_win": policy.played_group_win_points,
        **{
            f"knockout:{stage}": value
            for stage, value in policy.knockout_stage_points
        },
    }
    distribution_fp = _hash(distribution)
    seed = int(
        hashlib.sha256(
            f"{result.fingerprint}|{policy.fingerprint}|hybrid-awards".encode()
        ).hexdigest()[:15],
        16,
    )

    awards = []
    for player in sorted(result.players, key=lambda item: item.player_id):
        if player.played_group_wins is None:
            raise ValueError("Hybrid result lacks played group-win provenance")
        components = [
            TournamentPhasePointComponent(
                component_id="group_played_wins",
                distribution_key="group:played_win",
                units=player.played_group_wins,
                points_per_unit=policy.played_group_win_points,
                points_awarded=player.played_group_wins
                * policy.played_group_win_points,
            )
        ]
        if player.knockout_reached_stage is not None:
            key = f"knockout:{player.knockout_reached_stage}"
            value = knockout_distribution[player.knockout_reached_stage]
            components.append(
                TournamentPhasePointComponent(
                    component_id="knockout_finish",
                    distribution_key=key,
                    units=1,
                    points_per_unit=value,
                    points_awarded=value,
                )
            )
        total = sum(component.points_awarded for component in components)
        player_fp = _hash(player.model_dump(mode="json"))
        award_payload = {
            "schema_version": "tournament_player_point_award_authority.v4",
            "event_id": result.event_id,
            "seed": seed,
            "player_id": player.player_id,
            "reached_stage": player.reached_stage,
            "qualifier": player.qualifier,
            "seed_number": player.seed_number,
            "ranking_points_awarded": total,
            "race_points_awarded": total,
            "phase_components": [
                component.model_dump(mode="json") for component in components
            ],
            "source_tournament_result_fingerprint": result.fingerprint,
            "source_player_result_fingerprint": player_fp,
        }
        awards.append(
            TournamentPlayerPointAwardAuthority(
                player_id=player.player_id,
                reached_stage=player.reached_stage,
                qualifier=False,
                ranking_points_awarded=total,
                race_points_awarded=total,
                phase_components=tuple(components),
                source_player_result_fingerprint=player_fp,
                award_fingerprint=_hash(award_payload),
            )
        )

    return TournamentPointAwardAuthority(
        schema_version="tournament_point_award_authority.v4",
        run_id=result.run_id,
        branch_id=result.branch_id,
        event_id=result.event_id,
        completed_week=result.completed_week,
        seed=seed,
        ranking_status="ranked",
        tournament_result_fingerprint=result.fingerprint,
        point_distribution=tuple(sorted(distribution.items())),
        point_distribution_fingerprint=distribution_fp,
        point_distribution_source=f"hybrid_ranking_policy:{policy.fingerprint}",
        awards=tuple(awards),
        total_ranking_points=sum(item.ranking_points_awarded for item in awards),
        total_race_points=sum(item.race_points_awarded for item in awards),
    )


def _ranking_source_boundary(
    completed_week: RankingWeek,
) -> tuple[RankingWeek | None, int | None]:
    if completed_week.week < 61:
        return RankingWeek(
            season_index=completed_week.season_index,
            week=completed_week.week + 1,
        ), None
    if completed_week.season_index < 49:
        return RankingWeek(
            season_index=completed_week.season_index + 1,
            week=1,
        ), None
    return None, completed_week.ordinal + 1


class TournamentHybridClosureService:
    """Freeze one hybrid tournament source after all bracket matches are complete."""

    def __init__(self, session: Session):
        self.session = session

    def close_from_current_receipts(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
    ) -> OwnedTournamentRankingSource:
        """Derive the exact completion week from the frozen terminal bracket receipts."""

        bracket = TournamentHybridKnockoutBracketAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if bracket is None:
            raise ValueError(
                "Hybrid Tournament closure requires frozen Knockout Bracket"
            )
        match_ids = tuple(match.match_id for match in bracket.matches)
        rows = self.session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == run_id,
                SimulationEventGroupModel.branch_id == branch_id,
                SimulationEventGroupModel.match_id.in_(match_ids),
            )
        ).all()
        by_match = {row.match_id: row for row in rows}
        if len(by_match) != len(rows):
            raise ValueError(
                "Hybrid Tournament closure found duplicate knockout match receipts"
            )
        if set(by_match) != set(match_ids):
            missing = sorted(set(match_ids) - set(by_match))
            raise ValueError(
                "Hybrid Tournament closure requires completed knockout receipts for: "
                + ", ".join(missing)
            )
        week_ordinals = {row.week_ordinal for row in rows}
        if len(week_ordinals) != 1:
            raise ValueError(
                "Hybrid Tournament knockout receipts span multiple RankingWeeks"
            )
        ordinal = next(iter(week_ordinals))
        if ordinal < 1 or ordinal > 50 * 61:
            raise ValueError("Hybrid Tournament completion week is outside Run range")
        completed_week = RankingWeek(
            season_index=(ordinal - 1) // 61,
            week=(ordinal - 1) % 61 + 1,
        )
        return self.close(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            completed_week=completed_week,
            command_id=command_id,
        )

    def close(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        completed_week: RankingWeek,
        command_id: str,
        calendar_event: CalendarEvent | None = None,
    ) -> OwnedTournamentRankingSource:
        standings = TournamentGroupStandingsAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        bracket = TournamentHybridKnockoutBracketAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        policy = TournamentHybridRankingPolicyAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if standings is None or bracket is None:
            raise ValueError(
                "Hybrid Tournament closure requires final Standings and Knockout Bracket"
            )
        if calendar_event is None:
            calendar_event = _frozen_calendar_event(
                self.session,
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                completed_week=completed_week,
            )

        blockers = hybrid_tournament_closure_blockers(
            standings=standings,
            bracket=bracket,
            policy=policy,
            calendar_event=calendar_event,
        )
        if blockers:
            raise ValueError(
                "Hybrid Tournament closure is blocked: " + ", ".join(blockers)
            )

        assert policy is not None
        assert calendar_event is not None

        result = build_hybrid_tournament_result_authority(
            session=self.session,
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            completed_week=completed_week,
            standings=standings,
            bracket=bracket,
        )
        awards = build_hybrid_tournament_point_award_authority(
            result=result,
            policy=policy,
        )
        prize_awards = build_tournament_prize_money_award_authority(
            result=result,
            event=calendar_event,
        )

        first_publication_week, closing_eligibility_ordinal = _ranking_source_boundary(
            completed_week
        )
        binding = TournamentRankingBinding(
            run_id=run_id,
            branch_id=branch_id,
            edition_id=event_id,
            event_id=event_id,
            completed_week=completed_week,
            first_publication_week=first_publication_week,
            closing_eligibility_ordinal=closing_eligibility_ordinal,
            validity_weeks=61,
            ranking_status="ranked",
            expected_result_fingerprint=result.fingerprint,
            expected_award_fingerprint=awards.fingerprint,
        )

        if binding.closing_only:
            prepare_final_season_closing_ranking_results(binding, result, awards)
            proposed = OwnedTournamentRankingSource(
                schema_version="owned_tournament_ranking_source.v6",
                binding=binding,
                canonical_result=result,
                canonical_awards=awards,
                canonical_prize_awards=prize_awards,
                adopted_by_command_id=command_id,
                provenance_kind=(
                    "canonical_run_owned_tournament_authorities_and_prize_money_final_closing"
                ),
            )
        else:
            prepare_canonical_tournament_ranking_sources(binding, result, awards)
            proposed = OwnedTournamentRankingSource(
                schema_version="owned_tournament_ranking_source.v5",
                binding=binding,
                canonical_result=result,
                canonical_awards=awards,
                canonical_prize_awards=prize_awards,
                adopted_by_command_id=command_id,
                provenance_kind=(
                    "canonical_run_owned_tournament_authorities_and_prize_money"
                ),
            )

        store = OwnedTournamentRankingSourceStore(self.session)
        existing = store.get(
            run_id=run_id,
            branch_id=branch_id,
            edition_id=event_id,
        )
        if existing is not None:
            if (
                existing.canonical_result is None
                or existing.canonical_awards is None
                or existing.canonical_result.fingerprint != result.fingerprint
                or existing.canonical_awards.fingerprint != awards.fingerprint
                or existing.canonical_prize_awards is None
                or existing.canonical_prize_awards.fingerprint != prize_awards.fingerprint
                or existing.binding != binding
            ):
                raise TournamentHybridClosureConflict(
                    "Existing tournament ranking source conflicts with hybrid closure"
                )
            return existing
        return store.append(proposed)
