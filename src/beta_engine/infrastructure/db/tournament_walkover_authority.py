"""Commit post-cutoff W/O into the authoritative Simulation Slot ledger."""

from __future__ import annotations

from sqlalchemy import select

from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
    AuthoritativeWalkoverGroupResult,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.walkover_authority import (
    TournamentWalkoverAuthorityBuilder,
)
from beta_engine.infrastructure.db.models import (
    SimulationEventGroupModel,
    SimulationSlotModel,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_replacement_cutoff_authority import (
    TournamentPlayerReplacementCutoffAuthorityStore,
)


class TournamentWalkoverAuthorityConflict(ValueError):
    pass


class TournamentWalkoverAuthorityStore:
    """Resolve and commit one Master §15.9 post-cutoff W/O.

    The target group must already belong to an authoritative Simulation Slot. This
    keeps chronology owned by the existing week schedule and lets W/O satisfy the
    planned group without creating a fake Match Engine result.
    """

    def __init__(self, session):
        self.session = session

    def commit(
        self,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
        event_id: str,
        command_id: str,
        withdrawn_player_id: str,
        slot_id: str,
        group_id: str,
    ) -> AuthoritativeWalkoverGroupResult:
        if not command_id or len(command_id) > 128:
            raise ValueError("W/O requires a valid command ID")

        cutoff = TournamentPlayerReplacementCutoffAuthorityStore(
            self.session
        ).resolve(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id=withdrawn_player_id,
        )
        if cutoff.status != "walkover_required" or not cutoff.played_matches:
            raise TournamentWalkoverAuthorityConflict(
                "W/O requires the withdrawn player's first real-match cutoff to have passed"
            )
        source_real_match_id = cutoff.played_matches[-1].match_id

        slot = self.session.get(
            SimulationSlotModel,
            (run_id, branch_id, week.ordinal, slot_id),
        )
        if slot is None:
            raise ValueError("W/O target Simulation Slot is not planned")
        plan = AuthoritativeSlotMatchExecutor._load_plan(slot)
        try:
            event_plan = next(
                item for item in plan.match_events if item.group_id == group_id
            )
        except StopIteration as exc:
            raise ValueError("W/O target group is not planned in the requested slot") from exc
        if event_plan.event_id != event_id:
            raise ValueError("W/O target group belongs to a different tournament")
        if event_plan.participant_sources is None:
            raise ValueError(
                "canonical post-cutoff W/O requires explicit participant sources"
            )

        sources = tuple(event_plan.participant_sources)
        withdrawn_source = f"winner:{source_real_match_id}"
        if sources.count(withdrawn_source) != 1:
            raise TournamentWalkoverAuthorityConflict(
                "W/O target does not consume the withdrawn player's latest real-match win"
            )

        resolved = tuple(
            self._resolve_source(
                run_id=run_id,
                branch_id=branch_id,
                week=week,
                source=source,
            )
            for source in sources
        )
        withdrawn_index = sources.index(withdrawn_source)
        if resolved[withdrawn_index] != withdrawn_player_id:
            raise TournamentWalkoverAuthorityConflict(
                "W/O feeder no longer resolves to the withdrawn player"
            )
        winner_player_id = resolved[1 - withdrawn_index]
        if winner_player_id == withdrawn_player_id:
            raise TournamentWalkoverAuthorityConflict(
                "W/O opponent resolves to the withdrawn player"
            )

        draw = TournamentDrawAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if draw is None:
            raise ValueError("W/O requires canonical active Draw authority")

        authority = TournamentWalkoverAuthorityBuilder.build(
            run_id=run_id,
            branch_id=branch_id,
            week=week,
            slot_id=slot_id,
            slot_start_fingerprint=plan.slot_start_fingerprint,
            group_id=group_id,
            event_id=event_id,
            match_id=event_plan.match_id,
            command_id=command_id,
            draw_authority_fingerprint=draw.fingerprint,
            withdrawn_player_id=withdrawn_player_id,
            winner_player_id=winner_player_id,
            source_real_match_id=source_real_match_id,
            participant_sources=sources,
            resolved_player_ids=resolved,
            replacement_cutoff_authority=cutoff,
        )
        return AuthoritativeSlotMatchExecutor(self.session).execute_walkover_group(
            authority=authority,
            expected_slot_start_fingerprint=plan.slot_start_fingerprint,
        )

    def _resolve_source(
        self,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
        source: str,
    ) -> str:
        if source.startswith("player:"):
            return source.removeprefix("player:")
        if not source.startswith("winner:"):
            raise ValueError("W/O participant source is unsupported")
        feeder_id = source.removeprefix("winner:")
        row = self.session.scalar(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == run_id,
                SimulationEventGroupModel.branch_id == branch_id,
                SimulationEventGroupModel.week_ordinal == week.ordinal,
                SimulationEventGroupModel.group_id == feeder_id,
            )
        )
        if row is None:
            raise TournamentWalkoverAuthorityConflict(
                "W/O opponent/source is not resolved by authoritative progression yet"
            )
        return AuthoritativeSlotMatchExecutor._load_group(
            row
        ).result.winner_player_id
