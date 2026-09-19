"""Resolve canonical Lucky Loser order from completed Qualification receipts."""

from __future__ import annotations

from sqlalchemy import select

from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
)
from beta_engine.domain.tournaments.lucky_loser_authority import (
    TournamentLuckyLoserOrderAuthority,
    TournamentLuckyLoserOrderAuthorityBuilder,
    TournamentLuckyLoserQualificationMatchEvidence,
)
from beta_engine.infrastructure.db.models import SimulationEventGroupModel
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)


class TournamentLuckyLoserOrderUnavailable(ValueError):
    pass


class TournamentLuckyLoserOrderAuthorityStore:
    """Build bracket-Q LL priority only after every Q terminal has resolved."""

    def __init__(self, session):
        self.session = session

    def resolve(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
    ) -> TournamentLuckyLoserOrderAuthority:
        draw = TournamentDrawAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        ranking = TournamentRankingSnapshotAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if draw is None or ranking is None:
            raise TournamentLuckyLoserOrderUnavailable(
                "Lucky Loser order requires Draw and Tournament Ranking Snapshot"
            )
        if not draw.qualification_brackets:
            raise TournamentLuckyLoserOrderUnavailable(
                "Lucky Loser order requires bracket Qualification"
            )

        node_meta: dict[str, tuple[str, int]] = {}
        terminal_ids: set[str] = set()
        for index, bracket in enumerate(draw.qualification_brackets, start=1):
            section_id = bracket.section_id or f"Q{index}"
            player_count = sum(
                slot.player_id is not None for slot in bracket.slots
            )
            if player_count < 2:
                raise TournamentLuckyLoserOrderUnavailable(
                    "Auto-BYE Qualification terminal LL ordering is not implemented yet"
                )
            for node in bracket.nodes:
                if node.node_id in node_meta:
                    raise ValueError("Qualification Draw contains duplicate node identity")
                node_meta[node.node_id] = (section_id, node.round_number)
            terminal = max(
                bracket.nodes,
                key=lambda item: (item.round_number, item.round_sequence),
            )
            terminal_ids.add(terminal.node_id)

        rows = self.session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == run_id,
                SimulationEventGroupModel.branch_id == branch_id,
            )
        ).all()

        evidence = []
        seen_matches: set[str] = set()
        resolved_terminals: set[str] = set()
        for row in rows:
            meta = node_meta.get(row.match_id)
            if meta is None:
                continue
            loaded = AuthoritativeSlotMatchExecutor._load_group(row)
            protected = loaded.authoritative_input
            result = loaded.result
            if protected.event_id != event_id:
                continue
            if row.match_id in seen_matches:
                raise ValueError("Lucky Loser order found duplicate Q match receipt")
            seen_matches.add(row.match_id)
            if result.match_id != row.match_id:
                raise ValueError("Lucky Loser Q receipt/result identity mismatch")
            section_id, round_number = meta
            evidence.append(
                TournamentLuckyLoserQualificationMatchEvidence(
                    match_id=row.match_id,
                    section_id=section_id,
                    round_number=round_number,
                    winner_player_id=result.winner_player_id,
                    loser_player_id=result.loser_player_id,
                    result_fingerprint=row.result_fingerprint,
                )
            )
            if row.match_id in terminal_ids:
                resolved_terminals.add(row.match_id)

        if resolved_terminals != terminal_ids:
            raise TournamentLuckyLoserOrderUnavailable(
                "Lucky Loser order is unavailable until Qualification is complete"
            )

        return TournamentLuckyLoserOrderAuthorityBuilder.build(
            draw=draw,
            tournament_ranking_authority=ranking,
            completed_qualification_matches=tuple(
                sorted(
                    evidence,
                    key=lambda item: (
                        item.section_id,
                        item.round_number,
                        item.match_id,
                    ),
                )
            ),
        )
