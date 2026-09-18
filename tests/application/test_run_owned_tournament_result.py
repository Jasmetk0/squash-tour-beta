from __future__ import annotations

import hashlib
import json

import pytest

from beta_engine.application.ranking_tournament_ingestion import TournamentRankingBinding
from beta_engine.application.run_owned_match_package import build_run_owned_match_package
from beta_engine.application.season_point_awards_service import (
    EventPointAwardPackage,
    PointAwardMetadata,
    PointAwardSummary,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthorityBuilder
from beta_engine.domain.tournaments.draw_input_authority import TournamentDrawInputAuthority
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity
from beta_engine.domain.tournaments.models import CalendarEvent
from beta_engine.domain.tournaments.result_authority import (
    build_tournament_result_authority,
    project_tournament_result_legacy_dto,
)


pytestmark = pytest.mark.smoke


def _input(*, qualification=False):
    if qualification:
        capacity = TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=2,
            qualifier_spots=1,
        )
        direct = ("A", "B", "C")
        q = ("D", "E")
        placeholders = ("Q1",)
    else:
        capacity = TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=0,
            qualifier_spots=0,
        )
        direct = ("A", "B", "C", "D")
        q = ()
        placeholders = ()
    return TournamentDrawInputAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        committed_by_command_id="input",
        draw_seed=1234,
        main_seed_count=1,
        qualification_seed_count=1 if qualification else 0,
        field_sequence=1,
        capacity=capacity,
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=direct,
        qualification_player_ids=q,
        qualifier_placeholder_ids=placeholders,
        withdrawn_player_ids=(),
        main_seed_player_ids=direct[:1],
        qualification_seed_player_ids=q[:1] if qualification else (),
    )


def _multi_qualification_input():
    direct = ("A", "B", "C", "D")
    qualification = tuple(f"QF{index:02d}" for index in range(1, 17))
    return TournamentDrawInputAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        committed_by_command_id="input-multi-q",
        draw_seed=4321,
        main_seed_count=2,
        qualification_seed_count=4,
        field_sequence=1,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=8,
            qualification_draw_size=16,
            qualifier_spots=4,
        ),
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=direct,
        qualification_player_ids=qualification,
        qualifier_placeholder_ids=("Q1", "Q2", "Q3", "Q4"),
        withdrawn_player_ids=(),
        main_seed_player_ids=direct[:1],
        qualification_seed_player_ids=qualification[:4],
    )


def _multi_qualification_event():
    return CalendarEvent(
        event_id="event",
        season="2000/2001",
        season_week=1,
        calendar_year=2000,
        year_week=1,
        template_id="template",
        event_name="Canonical Multi-Q Open",
        category="TEST",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        region="Europe",
        main_draw_size=8,
        qualification_draw_size=16,
        qualifier_spots=4,
    )


def _event(*, qualification=False):
    return CalendarEvent(
        event_id="event",
        season="2000/2001",
        season_week=1,
        calendar_year=2000,
        year_week=1,
        template_id="template",
        event_name="Canonical Open",
        category="TEST",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        region="Europe",
        main_draw_size=4,
        qualification_draw_size=2 if qualification else 0,
        qualifier_spots=1 if qualification else 0,
    )


def _complete(draw, package):
    projected = package.model_copy(deep=True)
    qualifier_winners: dict[str, str] = {}

    def complete_bracket(bracket, records):
        winners = {}
        slots = {slot.slot_index: slot for slot in bracket.slots}
        by_id = {record.match_id: record for record in records}
        for node in sorted(
            bracket.nodes,
            key=lambda item: (item.round_number, item.round_sequence),
        ):
            def resolve(source):
                if source.startswith("winner:"):
                    return winners[source.removeprefix("winner:")]
                slot = slots[int(source.removeprefix("slot:"))]
                if slot.entrant_kind == "player":
                    return slot.player_id
                if slot.entrant_kind == "qualifier_placeholder":
                    winner = qualifier_winners.get(slot.placeholder_id)
                    if winner is None:
                        raise AssertionError("qualifier winner missing")
                    return winner
                if slot.entrant_kind == "bye":
                    return None
                raise AssertionError("unsupported source")

            top = resolve(node.source_top)
            bottom = resolve(node.source_bottom)
            record = by_id[node.node_id]
            if top is None or bottom is None:
                winner = bottom if top is None else top
                loser = None
                score = "BYE"
            else:
                winner = top
                loser = bottom
                score = "3-0"
            record.top_player_id = top
            record.bottom_player_id = bottom
            record.winner_player_id = winner
            record.loser_player_id = loser
            record.scoreline = score
            record.status = "completed"
            record.result_fingerprint = (
                f"{node.round_number:02x}{node.round_sequence:02x}".ljust(64, "a")
            )[:64]
            winners[node.node_id] = winner
        terminal = max(
            bracket.nodes,
            key=lambda n: (n.round_number, n.round_sequence),
        )
        return winners[terminal.node_id]

    for index, bracket in enumerate(draw.qualification_brackets, start=1):
        qualifier_winners[bracket.section_id or f"Q{index}"] = complete_bracket(
            bracket,
            projected.qualification_matches,
        )
    complete_bracket(
        draw.main,
        projected.main_draw_matches,
    )
    return projected


def test_canonical_result_derives_champion_finalist_and_stages_without_legacy_service():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(),
        command_id="draw",
    )
    package = build_run_owned_match_package(
        draw=draw,
        event=_event(),
        week=RankingWeek(season_index=0, week=1),
    )
    completed = _complete(draw, package)
    authority = build_tournament_result_authority(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=1),
        draw=draw,
        package=completed,
    )

    assert authority.champion_player_id == "A"
    assert authority.finalist_player_id in {"B", "C", "D"}
    assert len(authority.matches) == 3
    stages = {player.player_id: player.reached_stage for player in authority.players}
    assert stages[authority.champion_player_id] == "champion"
    assert stages[authority.finalist_player_id] == "finalist"
    assert sum(stage == "semifinal" for stage in stages.values()) == 2
    assert authority.draw_authority_fingerprint == draw.fingerprint


def test_canonical_result_preserves_qualification_provenance_into_main():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(qualification=True),
        command_id="draw",
    )
    event = _event(qualification=True)
    package = build_run_owned_match_package(
        draw=draw,
        event=event,
        week=RankingWeek(season_index=0, week=1),
    )
    completed = _complete(draw, package)
    authority = build_tournament_result_authority(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=1),
        draw=draw,
        package=completed,
    )

    assert authority.qualification_winner_ids == ("D",)
    q_winner = next(player for player in authority.players if player.player_id == "D")
    assert q_winner.qualifier is True
    assert q_winner.draw_type == "both"
    assert len(authority.matches) == 4

    dto = project_tournament_result_legacy_dto(
        authority=authority,