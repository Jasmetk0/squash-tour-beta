from __future__ import annotations

import pytest

from beta_engine.application.canonical_tournament_topology import (
    project_canonical_draw_to_match_topology,
)
from beta_engine.application.run_owned_match_package import (
    build_run_owned_match_package,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthorityBuilder
from beta_engine.domain.tournaments.draw_input_authority import TournamentDrawInputAuthority
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity
from beta_engine.domain.tournaments.models import CalendarEvent


pytestmark = pytest.mark.smoke


def _input(*, qualification=False, bye=False):
    if qualification:
        capacity = TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=2,
            qualifier_spots=1,
        )
        direct = ("A", "B", "C")
        q = ("D", "E")
        placeholders = ("Q1",)
    elif bye:
        capacity = TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=0,
            qualifier_spots=0,
            bye_slots=1,
        )
        direct = ("A", "B", "C")
        q = ()
        placeholders = ()
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


def _event():
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
        qualification_draw_size=0,
        qualifier_spots=0,
    )


def test_run_owned_package_is_built_without_legacy_draw_or_match_files():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(),
        command_id="draw",
    )
    package = build_run_owned_match_package(
        draw=draw,
        event=_event(),
        week=RankingWeek(season_index=0, week=1),
    )

    assert package.metadata.match_engine_version == "run_owned_match_package_projection.v1"
    assert package.metadata.draw_package_fingerprint == draw.fingerprint
    assert package.metadata.persistence_path is None
    assert package.persisted is True
    assert len(package.main_draw_matches) == 3
    assert package.qualification_matches == []

    topology = project_canonical_draw_to_match_topology(
        draw=draw,
        package=package,
    )
    assert len(topology.plans) == 3
    assert topology.terminal_group_id == draw.main.nodes[-1].node_id


def test_run_owned_package_projects_qualification_without_legacy_match_generation():
    draw_input = _input(qualification=True)
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=draw_input,
        command_id="draw",
    )
    event = _event().model_copy(
        update={
            "qualification_draw_size": 2,
            "qualifier_spots": 1,
        }
    )
    package = build_run_owned_match_package(
        draw=draw,
        event=event,
        week=RankingWeek(season_index=0, week=1),
    )
    topology = project_canonical_draw_to_match_topology(
        draw=draw,
        package=package,
    )

    assert len(package.qualification_matches) == 1
    assert len(package.main_draw_matches) == 3
    assert len(topology.plans) == 4
    assert len(topology.qualifier_promotions) == 1
    promotion = topology.qualifier_promotions[0]
    assert promotion.source_match_id == draw.qualification.nodes[-1].node_id
    assert promotion.target_match_id in {
        match.match_id for match in package.main_draw_matches
    }


def test_run_owned_package_executes_single_q_bye_as_canonical_auto_advance():
    draw_input = TournamentDrawInputAuthority(
        schema_version="tournament_draw_input_authority.v2",
        run_id="run",
        branch_id="branch",
        event_id="event",
        committed_by_command_id="input-q-bye",
        draw_seed=2468,
        main_seed_count=1,
        qualification_seed_count=1,
        field_sequence=1,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=2,
            qualifier_spots=1,
        ),
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=("A", "B", "C"),
        qualification_player_ids=("D",),
        qualifier_placeholder_ids=("Q1",),
        withdrawn_player_ids=(),
        main_seed_player_ids=("A",),
        qualification_seed_player_ids=("D",),
    )
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=draw_input,
        command_id="draw",
    )
    event = _event().model_copy(
        update={
            "qualification_draw_size": 2,
            "qualifier_spots": 1,
        }
    )
    package = build_run_owned_match_package(
        draw=draw,
        event=event,
        week=RankingWeek(season_index=0, week=1),
    )
    topology = project_canonical_draw_to_match_topology(
        draw=draw,
        package=package,
    )

    assert len(package.qualification_matches) == 1
    q_match = package.qualification_matches[0]
    assert q_match.status == "bye_auto_advance_pending"
    assert q_match.match_id in topology.bye_match_ids
    assert dict(topology.bye_winners)[q_match.match_id] == "D"
    assert len(topology.qualifier_promotions) == 1
    assert topology.qualifier_promotions[0].source_match_id == q_match.match_id


def test_run_owned_package_freezes_explicit_bye_from_canonical_draw():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(bye=True),
        command_id="draw",
    )
    event = _event().model_copy(update={"byes": 1})
    package = build_run_owned_match_package(
        draw=draw,
        event=event,
        week=RankingWeek(season_index=0, week=1),
    )
    topology = project_canonical_draw_to_match_topology(
        draw=draw,
        package=package,
    )

    assert sum(
        match.status == "bye_auto_advance_pending"
        for match in package.main_draw_matches
    ) == 1
    assert len(topology.bye_match_ids) == 1
    assert len(topology.bye_winners) == 1


def test_run_owned_package_rejects_calendar_week_mismatch():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(),
        command_id="draw",
    )
    with pytest.raises(ValueError, match="different week"):
        build_run_owned_match_package(
            draw=draw,
            event=_event(),
            week=RankingWeek(season_index=0, week=2),
        )