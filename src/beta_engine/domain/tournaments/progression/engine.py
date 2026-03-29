"""Deterministic tournament progression engine for qualification + main draw."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.draws.models import DrawEntrantType, DrawNode, DrawType, GeneratedDraw
from beta_engine.domain.matches import MatchContext, MatchEngine, MatchParticipantContext
from beta_engine.domain.players.models import Player
from beta_engine.domain.tournaments.models import TournamentTemplate
from beta_engine.domain.tournaments.progression.models import (
    MainDrawOutcome,
    MatchDisposition,
    Placement,
    PlaceholderResolution,
    PlaceholderResolutionStatus,
    QualificationOutcome,
    TournamentMatchRecord,
    TournamentResult,
    TournamentRoundResult,
)


@dataclass(slots=True)
class TournamentProgressionEngine:
    """Runs one deterministic event from draws through completion."""

    rng: DeterministicRng

    def run_tournament(
        self,
        *,
        event_id: str,
        season: int,
        week: int,
        template: TournamentTemplate,
        qualification_draw: GeneratedDraw,
        main_draw: GeneratedDraw,
        players_by_id: dict[str, Player],
    ) -> TournamentResult:
        event_rng = self.rng.branch(SeedScope.WEEK, season, week, event_id, "tournament_progression")

        qualification = self._run_qualification(
            event_id=event_id,
            template=template,
            draw=qualification_draw,
            players_by_id=players_by_id,
            event_rng=event_rng,
        )

        resolved_main, resolutions = self._resolve_qualifier_placeholders(
            draw=main_draw,
            qualifiers_in_order=qualification.qualifiers_in_order,
        )

        main_draw_outcome = self._run_main_draw(
            event_id=event_id,
            draw=resolved_main,
            players_by_id=players_by_id,
            event_rng=event_rng,
        )

        return TournamentResult(
            event_id=event_id,
            season=season,
            week=week,
            qualification=qualification,
            qualifier_slot_resolutions=resolutions,
            main_draw=main_draw_outcome,
        )

    def _run_qualification(
        self,
        *,
        event_id: str,
        template: TournamentTemplate,
        draw: GeneratedDraw,
        players_by_id: dict[str, Player],
        event_rng: DeterministicRng,
    ) -> QualificationOutcome:
        if template.qualifier_spots <= 0 or draw.bracket_size <= 1:
            return QualificationOutcome(rounds=[], qualifiers_in_order=[], qualifier_rounds_played=0)

        rounds_to_play = self._qualification_rounds_to_play(draw.bracket_size, template.qualifier_spots)
        outcome = self._play_draw(
            event_id=event_id,
            draw=draw,
            players_by_id=players_by_id,
            rounds_to_play=rounds_to_play,
            event_rng=event_rng,
        )

        final_round = max((r.round_number for r in outcome), default=0)
        qualifiers = [
            match.winner_player_id
            for round_result in outcome
            if round_result.round_number == final_round
            for match in sorted(round_result.matches, key=lambda m: m.round_sequence)
            if match.winner_player_id is not None
        ]

        unresolved = max(0, template.qualifier_spots - len(qualifiers))
        return QualificationOutcome(
            rounds=outcome,
            qualifiers_in_order=qualifiers,
            unresolved_qualifier_count=unresolved,
            qualifier_rounds_played=rounds_to_play,
        )

    def _run_main_draw(
        self,
        *,
        event_id: str,
        draw: GeneratedDraw,
        players_by_id: dict[str, Player],
        event_rng: DeterministicRng,
    ) -> MainDrawOutcome:
        outcome = self._play_draw(
            event_id=event_id,
            draw=draw,
            players_by_id=players_by_id,
            rounds_to_play=None,
            event_rng=event_rng,
        )

        final_round_number = max((round_result.round_number for round_result in outcome), default=0)
        final_matches = [
            m
            for round_result in outcome
            if round_result.round_number == final_round_number
            for m in round_result.matches
        ]
        final_match = final_matches[0] if final_matches else None

        champion = final_match.winner_player_id if final_match else None
        finalist = final_match.loser_player_id if final_match else None

        placements: list[Placement] = []
        if champion is not None:
            placements.append(Placement(player_id=champion, finish="CHAMPION"))
        if finalist is not None:
            placements.append(Placement(player_id=finalist, finish="FINALIST"))

        semifinal_round = final_round_number - 1
        if semifinal_round >= 1:
            semifinal_losers = [
                m.loser_player_id
                for round_result in outcome
                if round_result.round_number == semifinal_round
                for m in round_result.matches
                if m.loser_player_id is not None
            ]
            placements.extend(Placement(player_id=pid, finish="SEMIFINALIST") for pid in semifinal_losers)

        return MainDrawOutcome(
            rounds=outcome,
            champion_player_id=champion,
            finalist_player_id=finalist,
            placements=placements,
        )

    def _resolve_qualifier_placeholders(
        self,
        *,
        draw: GeneratedDraw,
        qualifiers_in_order: list[str],
    ) -> tuple[GeneratedDraw, list[PlaceholderResolution]]:
        slots = [slot.model_copy(deep=True) for slot in draw.slots]
        resolutions: list[PlaceholderResolution] = []

        qualifier_iter = iter(qualifiers_in_order)
        for slot_index in sorted(draw.qualifier_slot_indexes):
            slot = slots[slot_index - 1]
            candidate = next(qualifier_iter, None)
            if candidate is None:
                resolutions.append(
                    PlaceholderResolution(
                        draw_type=draw.draw_type,
                        slot_index=slot_index,
                        placeholder_type=slot.entrant_type,
                        placeholder_entry_id=slot.entry_id,
                        resolved_player_id=None,
                        source_label="QUALIFICATION_WINNER_PENDING",
                        status=PlaceholderResolutionStatus.UNRESOLVED,
                    )
                )
                continue

            slots[slot_index - 1] = slot.model_copy(
                update={
                    "entrant_type": DrawEntrantType.PLAYER,
                    "player_id": candidate,
                    "acceptance_status": None,
                    "metadata": {
                        **slot.metadata,
                        "resolved_from": "qualification_winner",
                    },
                }
            )
            resolutions.append(
                PlaceholderResolution(
                    draw_type=draw.draw_type,
                    slot_index=slot_index,
                    placeholder_type=slot.entrant_type,
                    placeholder_entry_id=slot.entry_id,
                    resolved_player_id=candidate,
                    source_label="QUALIFICATION_WINNER",
                    status=PlaceholderResolutionStatus.RESOLVED,
                )
            )

        return draw.model_copy(update={"slots": slots}), resolutions

    def _play_draw(
        self,
        *,
        event_id: str,
        draw: GeneratedDraw,
        players_by_id: dict[str, Player],
        rounds_to_play: int | None,
        event_rng: DeterministicRng,
    ) -> list[TournamentRoundResult]:
        source_winners: dict[str, str | None] = {}
        source_kinds: dict[str, DrawEntrantType] = {}
        for slot in draw.slots:
            source_winners[f"SLOT:{slot.slot_index}"] = slot.player_id
            source_kinds[f"SLOT:{slot.slot_index}"] = slot.entrant_type

        rounds: list[TournamentRoundResult] = []
        nodes = sorted(draw.nodes, key=lambda n: (n.round_number, n.round_sequence))
        match_engine = MatchEngine(
            rng=event_rng.branch(SeedScope.MATCH, draw.draw_type.value, draw.event_id, "matches")
        )

        for node in nodes:
            if rounds_to_play is not None and node.round_number > rounds_to_play:
                break

            top_player, top_kind = self._source_state(node.source_top, source_winners, source_kinds)
            bottom_player, bottom_kind = self._source_state(node.source_bottom, source_winners, source_kinds)

            record = self._play_node(
                event_id=event_id,
                draw_type=draw.draw_type,
                node=node,
                top_player_id=top_player,
                bottom_player_id=bottom_player,
                top_kind=top_kind,
                bottom_kind=bottom_kind,
                players_by_id=players_by_id,
                match_engine=match_engine,
            )
            source_winners[node.node_id] = record.winner_player_id
            source_kinds[node.node_id] = DrawEntrantType.PLAYER if record.winner_player_id else DrawEntrantType.TBD

            if not rounds or rounds[-1].round_number != node.round_number:
                rounds.append(TournamentRoundResult(draw_type=draw.draw_type, round_number=node.round_number, matches=[]))
            rounds[-1].matches.append(record)

        return rounds

    @staticmethod
    def _source_state(
        source_id: str,
        winners: dict[str, str | None],
        kinds: dict[str, DrawEntrantType],
    ) -> tuple[str | None, DrawEntrantType]:
        return winners.get(source_id), kinds.get(source_id, DrawEntrantType.TBD)

    def _play_node(
        self,
        *,
        event_id: str,
        draw_type: DrawType,
        node: DrawNode,
        top_player_id: str | None,
        bottom_player_id: str | None,
        top_kind: DrawEntrantType,
        bottom_kind: DrawEntrantType,
        players_by_id: dict[str, Player],
        match_engine: MatchEngine,
    ) -> TournamentMatchRecord:
        record = TournamentMatchRecord(
            draw_type=draw_type,
            node_id=node.node_id,
            round_number=node.round_number,
            round_sequence=node.round_sequence,
            top_source=node.source_top,
            bottom_source=node.source_bottom,
            top_player_id=top_player_id,
            bottom_player_id=bottom_player_id,
            disposition=MatchDisposition.UNRESOLVED,
        )

        if top_player_id is None and bottom_player_id is None:
            return record

        if top_player_id is None:
            return record.model_copy(
                update={
                    "winner_player_id": bottom_player_id,
                    "disposition": MatchDisposition.BYE_ADVANCE if top_kind == DrawEntrantType.BYE else MatchDisposition.WALKOVER_ADVANCE,
                }
            )

        if bottom_player_id is None:
            return record.model_copy(
                update={
                    "winner_player_id": top_player_id,
                    "disposition": MatchDisposition.BYE_ADVANCE if bottom_kind == DrawEntrantType.BYE else MatchDisposition.WALKOVER_ADVANCE,
                }
            )

        top_player = players_by_id[top_player_id]
        bottom_player = players_by_id[bottom_player_id]
        match_id = f"{event_id}:{draw_type.value}:{node.node_id}"
        result = match_engine.simulate(
            MatchContext(
                match_id=match_id,
                player_a=MatchParticipantContext(player=top_player),
                player_b=MatchParticipantContext(player=bottom_player),
            )
        )
        return record.model_copy(
            update={
                "winner_player_id": result.winner_player_id,
                "loser_player_id": result.loser_player_id,
                "disposition": MatchDisposition.PLAYED,
                "match_id": match_id,
                "match_result": result.model_dump(),
            }
        )

    @staticmethod
    def _qualification_rounds_to_play(bracket_size: int, qualifier_spots: int) -> int:
        if qualifier_spots <= 0 or qualifier_spots > bracket_size:
            raise ValueError("qualifier_spots must be in 1..bracket_size for qualification progression")
        if (qualifier_spots & (qualifier_spots - 1)) != 0:
            raise ValueError("qualifier_spots must be power-of-two for deterministic bracket sections")
        if bracket_size % qualifier_spots != 0:
            raise ValueError("bracket_size must be divisible by qualifier_spots")

        rounds = 0
        size = bracket_size
        while size > qualifier_spots:
            size //= 2
            rounds += 1
        return rounds
