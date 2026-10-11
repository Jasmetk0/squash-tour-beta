"""Canonical closure for one pure single-group Tournament Edition."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.application.hybrid_tournament_closure import (
    _frozen_calendar_event,
    _ranking_source_boundary,
    _scoreline_from_group_receipt,
)
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
    prepare_canonical_tournament_ranking_sources,
    prepare_final_season_closing_ranking_results,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsAuthority,
)
from beta_engine.domain.tournaments.point_award_authority import (
    TournamentPhasePointComponent,
    TournamentPlayerPointAwardAuthority,
    TournamentPointAwardAuthority,
)
from beta_engine.domain.tournaments.prize_money_award_authority import (
    build_tournament_prize_money_award_authority,
)
from beta_engine.domain.tournaments.pure_groups_ranking_policy_authority import (
    TournamentPureGroupsRankingPolicyAuthority,
)
from beta_engine.domain.tournaments.result_authority import (
    TournamentMatchResultAuthority,
    TournamentPlayerResultAuthority,
    TournamentResultAuthority,
)
from beta_engine.infrastructure.db.models import SimulationEventGroupModel
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.tournament_group_match_schedule_authority import (
    TournamentGroupMatchScheduleAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_group_standings_authority import (
    TournamentGroupStandingsAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_pure_groups_ranking_policy_authority import (
    TournamentPureGroupsRankingPolicyAuthorityStore,
)


class TournamentPureGroupsClosureConflict(ValueError):
    """Frozen pure-groups evidence conflicts with immutable tournament history."""


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def pure_groups_closure_blockers(
    *,
    standings: TournamentGroupStandingsAuthority,
    policy: TournamentPureGroupsRankingPolicyAuthority | None,
    ranking_status: str,
) -> tuple[str, ...]:
    """Return only already-known product/config blockers."""

    if len(standings.groups) != 1 or standings.groups[0].group_index != 1:
        return ("groups_only_unique_outcome_required",)
    if ranking_status != "ranked":
        return ("pure_groups_unranked_completion_source_required",)
    if policy is None:
        return ("pure_groups_ranking_policy_required",)
    blockers: list[str] = []
    if policy.played_group_win_points > 0 and any(
        receipt.result_kind == "walkover" for receipt in standings.source_results
    ):
        blockers.append("pure_groups_group_walkover_ranking_unresolved")
    return tuple(blockers)


def build_pure_groups_tournament_result_authority(
    *,
    session: Session,
    run_id: str,
    branch_id: str,
    event_id: str,
    completed_week: RankingWeek,
    standings: TournamentGroupStandingsAuthority,
) -> TournamentResultAuthority:
    if (standings.run_id, standings.branch_id, standings.event_id) != (
        run_id,
        branch_id,
        event_id,
    ):
        raise ValueError("Pure-groups Tournament Result standings scope mismatch")
    if len(standings.groups) != 1 or standings.groups[0].group_index != 1:
        raise ValueError(
            "Pure-groups Tournament Result requires exactly one authoritative group"
        )

    schedule = TournamentGroupMatchScheduleAuthorityStore(session).get(
        run_id=run_id,
        branch_id=branch_id,
        event_id=event_id,
    )
    if schedule is None or schedule.fingerprint != standings.group_match_schedule_fingerprint:
        raise ValueError("Pure-groups Tournament Result lacks current Group Match Schedule")

    schedule_by_id = {match.match_id: match for match in schedule.matches}
    receipts_by_id = {receipt.match_id: receipt for receipt in standings.source_results}
    if set(schedule_by_id) != set(receipts_by_id):
        raise ValueError("Pure-groups Tournament Result group receipts are incomplete")

    group = standings.groups[0]
    players: dict[str, dict[str, object]] = {}
    for row in group.rows:
        players[row.player_id] = {
            "position": row.position,
            "played_group_wins": 0,
            "wins": 0,
            "losses": 0,
            "walkovers_received": row.walkovers_received,
            "retired_or_walkover_loss": bool(row.walkovers_conceded),
            "last_match_id": None,
        }

    matches: list[TournamentMatchResultAuthority] = []
    for scheduled in schedule.matches:
        receipt = receipts_by_id[scheduled.match_id]
        if receipt.winner_player_id not in players or receipt.loser_player_id not in players:
            raise ValueError("Pure-groups receipt references unknown player")
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
        matches.append(
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

    rows = tuple(sorted(group.rows, key=lambda row: row.position))
    if len(rows) < 2:
        raise ValueError("Pure-groups Tournament Result requires at least two players")

    result_players = tuple(
        TournamentPlayerResultAuthority(
            player_id=row.player_id,
            draw_type="group",
            reached_stage=f"group_position_{row.position}",
            last_match_id=(
                str(players[row.player_id]["last_match_id"])
                if players[row.player_id]["last_match_id"] is not None
                else None
            ),
            wins=int(players[row.player_id]["wins"]),
            losses=int(players[row.player_id]["losses"]),
            walkovers_received=int(players[row.player_id]["walkovers_received"]),
            retired_or_walkover_loss=bool(
                players[row.player_id]["retired_or_walkover_loss"]
            ),
            group_index=1,
            group_position=row.position,
            played_group_wins=int(players[row.player_id]["played_group_wins"]),
            group_walkovers_received=row.walkovers_received,
        )
        for row in rows
    )

    return TournamentResultAuthority(
        schema_version="tournament_result_authority.v3",
        run_id=run_id,
        branch_id=branch_id,
        event_id=event_id,
        completed_week=completed_week,
        group_standings_authority_fingerprint=standings.fingerprint,
        champion_player_id=rows[0].player_id,
        finalist_player_id=rows[1].player_id,
        players=result_players,
        matches=tuple(
            sorted(
                matches,
                key=lambda match: (
                    match.round_number,
                    match.bracket_position,
                    match.match_id,
                ),
            )
        ),
    )


def build_pure_groups_point_award_authority(
    *,
    result: TournamentResultAuthority,
    policy: TournamentPureGroupsRankingPolicyAuthority,
) -> TournamentPointAwardAuthority:
    if result.schema_version != "tournament_result_authority.v3":
        raise ValueError("Pure-groups point composition requires Tournament Result v3")
    if (result.run_id, result.branch_id, result.event_id) != (
        policy.run_id,
        policy.branch_id,
        policy.event_id,
    ):
        raise ValueError("Pure-groups point policy/result scope mismatch")
    if policy.played_group_win_points > 0 and any(
        (player.group_walkovers_received or 0) > 0 for player in result.players
    ):
        raise ValueError(
            "Pure-groups W/O ranking reward is unresolved; cannot compose points"
        )

    distribution = {"group:played_win": policy.played_group_win_points}
    distribution_fp = _hash(distribution)
    seed = int(
        hashlib.sha256(
            f"{result.fingerprint}|{policy.fingerprint}|pure-groups-awards".encode()
        ).hexdigest()[:15],
        16,
    )

    awards: list[TournamentPlayerPointAwardAuthority] = []
    for player in sorted(result.players, key=lambda item: item.player_id):
        assert player.played_group_wins is not None
        component = TournamentPhasePointComponent(
            component_id="group_played_wins",
            distribution_key="group:played_win",
            units=player.played_group_wins,
            points_per_unit=policy.played_group_win_points,
            points_awarded=player.played_group_wins * policy.played_group_win_points,
        )
        total = component.points_awarded
        player_fp = _hash(player.model_dump(mode="json"))
        award_payload = {
            "schema_version": "tournament_player_point_award_authority.v5",
            "event_id": result.event_id,
            "seed": seed,
            "player_id": player.player_id,
            "reached_stage": player.reached_stage,
            "qualifier": player.qualifier,
            "seed_number": player.seed_number,
            "ranking_points_awarded": total,
            "race_points_awarded": total,
            "phase_components": [component.model_dump(mode="json")],
            "source_tournament_result_fingerprint": result.fingerprint,
            "source_player_result_fingerprint": player_fp,
        }
        awards.append(
            TournamentPlayerPointAwardAuthority(
                player_id=player.player_id,
                reached_stage=player.reached_stage,
                ranking_points_awarded=total,
                race_points_awarded=total,
                phase_components=(component,),
                source_player_result_fingerprint=player_fp,
                award_fingerprint=_hash(award_payload),
            )
        )

    return TournamentPointAwardAuthority(
        schema_version="tournament_point_award_authority.v5",
        run_id=result.run_id,
        branch_id=result.branch_id,
        event_id=result.event_id,
        completed_week=result.completed_week,
        seed=seed,
        ranking_status="ranked",
        tournament_result_fingerprint=result.fingerprint,
        point_distribution=tuple(sorted(distribution.items())),
        point_distribution_fingerprint=distribution_fp,
        point_distribution_source=f"pure_groups_ranking_policy:{policy.fingerprint}",
        awards=tuple(awards),
        total_ranking_points=sum(a.ranking_points_awarded for a in awards),
        total_race_points=sum(a.race_points_awarded for a in awards),
    )


class TournamentPureGroupsClosureService:
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
        standings = TournamentGroupStandingsAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if standings is None:
            raise ValueError("Pure-groups closure requires final Group Standings")
        match_ids = tuple(receipt.match_id for receipt in standings.source_results)
        rows = self.session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == run_id,
                SimulationEventGroupModel.branch_id == branch_id,
                SimulationEventGroupModel.match_id.in_(match_ids),
            )
        ).all()
        by_match = {row.match_id: row for row in rows}
        if set(by_match) != set(match_ids):
            raise ValueError("Pure-groups closure lacks exact match receipts")
        week_ordinals = {row.week_ordinal for row in rows}
        if len(week_ordinals) != 1:
            raise ValueError("Pure-groups match receipts span multiple RankingWeeks")
        ordinal = next(iter(week_ordinals))
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
        calendar_event=None,
    ) -> OwnedTournamentRankingSource:
        standings = TournamentGroupStandingsAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        policy = TournamentPureGroupsRankingPolicyAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if standings is None:
            raise ValueError("Pure-groups closure requires final Group Standings")
        if calendar_event is None:
            calendar_event = _frozen_calendar_event(
                self.session,
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                completed_week=completed_week,
            )
        blockers = pure_groups_closure_blockers(
            standings=standings,
            policy=policy,
            ranking_status=calendar_event.ranking_status.value,
        )
        if blockers:
            raise ValueError(
                "Pure-groups Tournament closure is blocked: " + ", ".join(blockers)
            )
        assert policy is not None

        result = build_pure_groups_tournament_result_authority(
            session=self.session,
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            completed_week=completed_week,
            standings=standings,
        )
        awards = build_pure_groups_point_award_authority(
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
                or existing.canonical_prize_awards is None
                or existing.canonical_result.fingerprint != result.fingerprint
                or existing.canonical_awards.fingerprint != awards.fingerprint
                or existing.canonical_prize_awards.fingerprint != prize_awards.fingerprint
                or existing.binding != binding
            ):
                raise TournamentPureGroupsClosureConflict(
                    "Existing tournament source conflicts with pure-groups closure"
                )
            return existing
        return store.append(proposed)
