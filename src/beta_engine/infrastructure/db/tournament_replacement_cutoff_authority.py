"""Resolve player-specific replacement cutoff from Run/Branch match receipts."""

from __future__ import annotations

from typing import Literal

from sqlalchemy import select

from beta_engine.domain.tournaments.replacement_cutoff_authority import (
    TournamentPlayedMatchCutoffEvidence,
    TournamentPlayerReplacementCutoffAuthority,
    TournamentPlayerReplacementCutoffAuthorityBuilder,
)
from beta_engine.domain.tournaments.walkover_authority import TournamentWalkoverResult
from beta_engine.infrastructure.db.models import (
    SimulationEventGroupModel,
    SimulationSlotModel,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)


class TournamentPlayerReplacementCutoffAuthorityStore:
    """Read validated authoritative match receipts without inventing clock state."""

    def __init__(self, session):
        self.session = session

    def resolve(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        player_id: str,
        draw_type: Literal["qualification", "main"] | None = None,
    ) -> TournamentPlayerReplacementCutoffAuthority:
        # Local import avoids making the domain authority depend on the application
        # executor while still reusing its complete persisted-group validation.
        from beta_engine.application.authoritative_slot_matches import (
            AuthoritativeSlotMatchExecutor,
        )

        allowed_match_ids: set[str] | None = None
        if draw_type is not None:
            draw = TournamentDrawAuthorityStore(self.session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if draw is None:
                raise ValueError("Draw-component replacement cutoff requires canonical Draw")
            if draw_type == "main":
                allowed_match_ids = {node.node_id for node in draw.main.nodes}
            else:
                allowed_match_ids = {
                    node.node_id
                    for bracket in draw.qualification_brackets
                    for node in bracket.nodes
                }

        groups = self.session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == run_id,
                SimulationEventGroupModel.branch_id == branch_id,
            )
        ).all()
        slots = self.session.scalars(
            select(SimulationSlotModel).where(
                SimulationSlotModel.run_id == run_id,
                SimulationSlotModel.branch_id == branch_id,
            )
        ).all()
        slot_ordinals = {
            (row.week_ordinal, row.slot_id): row.slot_ordinal for row in slots
        }

        evidence = []
        for row in groups:
            if allowed_match_ids is not None and row.match_id not in allowed_match_ids:
                continue
            loaded = AuthoritativeSlotMatchExecutor._load_group(row)
            protected = loaded.authoritative_input
            result = loaded.result
            if protected.event_id != event_id:
                continue
            if isinstance(result, TournamentWalkoverResult):
                # W/O is progression evidence, not another real match. It must not
                # move the first-real-match replacement cutoff.
                continue
            participants = (result.player_a_id, result.player_b_id)
            if player_id not in participants:
                continue
            key = (row.week_ordinal, row.slot_id)
            slot_ordinal = slot_ordinals.get(key)
            if slot_ordinal is None:
                raise ValueError(
                    "Replacement cutoff match receipt has no authoritative slot"
                )
            if result.winner_player_id == player_id:
                outcome = "win"
                opponent = result.loser_player_id
            elif result.loser_player_id == player_id:
                outcome = "loss"
                opponent = result.winner_player_id
            else:
                raise ValueError(
                    "Replacement cutoff match result does not contain requested player outcome"
                )
            if opponent == player_id:
                raise ValueError(
                    "Replacement cutoff real match cannot use the same player twice"
                )
            evidence.append(
                TournamentPlayedMatchCutoffEvidence(
                    match_id=row.match_id,
                    week_ordinal=row.week_ordinal,
                    slot_id=row.slot_id,
                    slot_ordinal=slot_ordinal,
                    group_id=row.group_id,
                    result_fingerprint=row.result_fingerprint,
                    opponent_player_id=opponent,
                    outcome=outcome,
                )
            )

        return TournamentPlayerReplacementCutoffAuthorityBuilder.build(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id=player_id,
            played_matches=evidence,
            draw_type=draw_type,
        )

    def resolve_many(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        player_ids: tuple[str, ...],
        draw_type: Literal["qualification", "main"] | None = None,
    ) -> tuple[TournamentPlayerReplacementCutoffAuthority, ...]:
        return tuple(
            self.resolve(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                player_id=player_id,
                draw_type=draw_type,
            )
            for player_id in sorted(set(player_ids))
        )
