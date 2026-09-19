"""Resolve canonical Lucky Loser order from completed Qualification receipts."""

from __future__ import annotations

from sqlalchemy import select

from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
)
from beta_engine.domain.tournaments.lucky_loser_authority import (
    TournamentLuckyLoserAutoByeTerminalEvidence,
    TournamentLuckyLoserOrderAuthority,
    TournamentLuckyLoserOrderAuthorityBuilder,
    TournamentLuckyLoserQualificationMatchEvidence,
    TournamentLuckyLoserQualificationWinnerEvidence,
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


_REQUIRES_MATCH = object()


def _auto_bye_terminal_evidence(
    bracket,
    *,
    section_id: str,
) -> TournamentLuckyLoserAutoByeTerminalEvidence | None:
    players = tuple(
        slot.player_id
        for slot in bracket.slots
        if slot.player_id is not None
    )
    if len(players) != 1:
        return None

    slots = {slot.slot_index: slot for slot in bracket.slots}
    nodes = {node.node_id: node for node in bracket.nodes}
    memo = {}

    def resolve_source(source: str):
        if source.startswith("slot:"):
            slot_index = int(source.removeprefix("slot:"))
            slot = slots.get(slot_index)
            if slot is None:
                raise ValueError(
                    "Auto-BYE Qualification source references missing slot"
                )
            if slot.entrant_kind == "player":
                return slot.player_id
            if slot.entrant_kind == "bye":
                return None
            return _REQUIRES_MATCH
        if source.startswith("winner:"):
            node_id = source.removeprefix("winner:")
            return resolve_node(node_id)
        raise ValueError("Auto-BYE Qualification source type is unsupported")

    def resolve_node(node_id: str):
        if node_id in memo:
            return memo[node_id]
        node = nodes.get(node_id)
        if node is None:
            raise ValueError(
                "Auto-BYE Qualification source references missing node"
            )
        top = resolve_source(node.source_top)
        bottom = resolve_source(node.source_bottom)
        if top is _REQUIRES_MATCH or bottom is _REQUIRES_MATCH:
            resolved = _REQUIRES_MATCH
        elif top is not None and bottom is not None:
            resolved = _REQUIRES_MATCH
        else:
            resolved = top if top is not None else bottom
        memo[node_id] = resolved
        return resolved

    terminal = max(
        bracket.nodes,
        key=lambda item: (item.round_number, item.round_sequence),
    )
    winner = resolve_node(terminal.node_id)
    if winner is _REQUIRES_MATCH or winner is None:
        return None
    if winner != players[0]:
        raise ValueError(
            "Auto-BYE Qualification terminal winner differs from sole Q player"
        )
    return TournamentLuckyLoserAutoByeTerminalEvidence(
        match_id=terminal.node_id,
        section_id=section_id,
        winner_player_id=winner,
        qualification_bracket_fingerprint=bracket.fingerprint,
    )


class TournamentLuckyLoserOrderAuthorityStore:
    """Build bracket-Q LL priority only after every Q terminal has resolved."""

    def __init__(self, session):
        self.session = session

    def resolve_qualification_winner_evidence(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        draw,
        player_id: str,
    ) -> TournamentLuckyLoserQualificationWinnerEvidence:
        """Resolve exact Q-section terminal proof for one qualified Main occupant."""

        rows = self.session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == run_id,
                SimulationEventGroupModel.branch_id == branch_id,
            )
        ).all()
        rows_by_match = {}
        for row in rows:
            if row.match_id in rows_by_match:
                raise ValueError("Qualification winner evidence found duplicate match receipt")
            rows_by_match[row.match_id] = row

        matches = []
        for index, bracket in enumerate(draw.qualification_brackets, start=1):
            section_id = bracket.section_id or f"Q{index}"
            terminal = max(
                bracket.nodes,
                key=lambda item: (item.round_number, item.round_sequence),
            )
            auto = _auto_bye_terminal_evidence(bracket, section_id=section_id)
            if auto is not None:
                if auto.winner_player_id == player_id:
                    matches.append(
                        TournamentLuckyLoserQualificationWinnerEvidence(
                            section_id=section_id,
                            terminal_match_id=terminal.node_id,
                            winner_player_id=player_id,
                            evidence_kind="auto_bye_terminal",
                            evidence_fingerprint=bracket.fingerprint,
                        )
                    )
                continue

            row = rows_by_match.get(terminal.node_id)
            if row is None:
                continue
            loaded = AuthoritativeSlotMatchExecutor._load_group(row)
            if loaded.authoritative_input.event_id != event_id:
                continue
            result = loaded.result
            if result.match_id != terminal.node_id:
                raise ValueError("Qualification terminal receipt/result identity mismatch")
            if result.winner_player_id == player_id:
                matches.append(
                    TournamentLuckyLoserQualificationWinnerEvidence(
                        section_id=section_id,
                        terminal_match_id=terminal.node_id,
                        winner_player_id=player_id,
                        evidence_kind="played_terminal",
                        evidence_fingerprint=row.result_fingerprint,
                    )
                )

        if len(matches) != 1:
            raise TournamentLuckyLoserOrderUnavailable(
                "Player is not one uniquely resolved Qualification section winner"
            )
        return matches[0]

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
        if draw is None:
            raise TournamentLuckyLoserOrderUnavailable(
                "Lucky Loser order requires Draw and Tournament Ranking Snapshot"
            )
        return self.resolve_for_draw(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            draw=draw,
        )

    def resolve_for_draw(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        draw,
    ) -> TournamentLuckyLoserOrderAuthority:
        ranking = TournamentRankingSnapshotAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if ranking is None:
            raise TournamentLuckyLoserOrderUnavailable(
                "Lucky Loser order requires Draw and Tournament Ranking Snapshot"
            )
        if not draw.qualification_brackets:
            raise TournamentLuckyLoserOrderUnavailable(
                "Lucky Loser order requires bracket Qualification"
            )

        node_meta: dict[str, tuple[str, int]] = {}
        terminal_ids: set[str] = set()
        auto_bye_evidence = []
        for index, bracket in enumerate(draw.qualification_brackets, start=1):
            section_id = bracket.section_id or f"Q{index}"
            player_count = sum(
                slot.player_id is not None for slot in bracket.slots
            )
            if player_count == 0:
                raise TournamentLuckyLoserOrderUnavailable(
                    "Qualification section has no player to resolve"
                )
            auto_bye = _auto_bye_terminal_evidence(
                bracket,
                section_id=section_id,
            )
            if player_count == 1 and auto_bye is None:
                raise TournamentLuckyLoserOrderUnavailable(
                    "One-player Qualification terminal is not an unambiguous auto-BYE"
                )
            if auto_bye is not None:
                auto_bye_evidence.append(auto_bye)
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
        auto_bye_terminal_ids = {
            item.match_id for item in auto_bye_evidence
        }
        for row in rows:
            meta = node_meta.get(row.match_id)
            if meta is None:
                continue
            if row.match_id in auto_bye_terminal_ids:
                raise ValueError(
                    "Auto-BYE Qualification terminal cannot have competitive receipt"
                )
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

        resolved_terminal_ids = (
            resolved_terminals | auto_bye_terminal_ids
        )
        if resolved_terminal_ids != terminal_ids:
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
            auto_bye_terminal_evidence=tuple(
                sorted(
                    auto_bye_evidence,
                    key=lambda item: (item.section_id, item.match_id),
                )
            ),
        )
