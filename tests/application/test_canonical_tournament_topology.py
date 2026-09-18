from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from beta_engine.application.canonical_tournament_topology import (
    project_canonical_draw_to_match_topology,
)
from beta_engine.application import authoritative_run_simulation_driver as driver_module
from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
)
from beta_engine.application.season_match_service import (
    MatchPackageMetadata,
    MatchPackageSummary,
    SeasonEventMatchPackage,
    SeasonMatchRecord,
)
from beta_engine.domain.simulation_slots import fingerprint
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthorityBuilder
from beta_engine.domain.tournaments.draw_input_authority import TournamentDrawInputAuthority
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity
from beta_engine.infrastructure.db.models import AdoptedTournamentAuthorityModel


pytestmark = pytest.mark.smoke


def _draw_input(*, with_qualification=False, with_bye=False):
    if with_qualification:
        capacity = TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=2,
            qualifier_spots=1,
        )
        direct = ("A", "B", "C")
        qualification = ("D", "E")
        placeholders = ("Q1",)
        main_seeds = ("A", "B")
        qualification_seeds = ("D",)
    elif with_bye:
        capacity = TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=0,
            qualifier_spots=0,
            bye_slots=1,
        )
        direct = ("A", "B", "C")
        qualification = ()
        placeholders = ()
        main_seeds = ("A", "B")
        qualification_seeds = ()
    else:
        capacity = TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=0,
            qualifier_spots=0,
        )
        direct = ("A", "B", "C", "D")
        qualification = ()
        placeholders = ()
        main_seeds = ("A", "B")
        qualification_seeds = ()
    return TournamentDrawInputAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        committed_by_command_id="draw-input",
        draw_seed=5150,
        main_seed_count=len(main_seeds),
        qualification_seed_count=len(qualification_seeds),
        field_sequence=1,
        capacity=capacity,
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=direct,
        qualification_player_ids=qualification,
        qualifier_placeholder_ids=placeholders,
        withdrawn_player_ids=(),
        main_seed_player_ids=main_seeds,
        qualification_seed_player_ids=qualification_seeds,
    )


def _player_for_source(bracket, source):
    if not source.startswith("slot:"):
        return None
    slot = bracket.slots[int(source.removeprefix("slot:")) - 1]
    return slot.player_id if slot.entrant_kind == "player" else None


def _package(draw):
    id_by_node = {}
    brackets = []
    if draw.qualification is not None:
        brackets.append(draw.qualification)
    brackets.append(draw.main)
    for bracket in brackets:
        for node in bracket.nodes:
            id_by_node[node.node_id] = (
                f"{draw.event_id}:{bracket.draw_type}:"
                f"R{node.round_number}-M{node.round_sequence}"
            )

    records = {"qualification": [], "main": []}
    for bracket in brackets:
        for node in bracket.nodes:
            target = next(
                (
                    candidate
                    for candidate in bracket.nodes
                    if f"winner:{node.node_id}"
                    in (candidate.source_top, candidate.source_bottom)
                ),
                None,
            )
            top_player = _player_for_source(bracket, node.source_top)
            bottom_player = _player_for_source(bracket, node.source_bottom)
            sources = (node.source_top, node.source_bottom)
            has_bye = any(
                source.startswith("slot:")
                and bracket.slots[int(source.removeprefix("slot:")) - 1].entrant_kind
                == "bye"
                for source in sources
            )
            records[bracket.draw_type].append(
                SeasonMatchRecord(
                    match_id=id_by_node[node.node_id],
                    event_id=draw.event_id,
                    draw_type=bracket.draw_type,
                    round_number=node.round_number,
                    round_name=f"R{node.round_number}",
                    bracket_position=node.round_sequence,
                    top_slot_id=node.source_top,
                    bottom_slot_id=node.source_bottom,
                    top_source=node.source_top,
                    bottom_source=node.source_bottom,
                    top_player_id=top_player,
                    bottom_player_id=bottom_player,
                    status="bye_auto_advance_pending"
                    if has_bye
                    else (
                        "pending"
                        if top_player is not None and bottom_player is not None
                        else "blocked_waiting_for_sources"
                    ),
                    winner_to_match_id=id_by_node[target.node_id] if target else None,
                    source_draw_fingerprint="legacy-payload-only",
                    generated_fingerprint=f"generated:{node.node_id}",
                )
            )

    total = len(records["qualification"]) + len(records["main"])
    return SeasonEventMatchPackage(
        event_id=draw.event_id,
        season="2000/2001",
        template_id="template",
        season_week=1,
        seed=99,
        dry_run=False,
        persisted=True,
        qualification_matches=records["qualification"],
        main_draw_matches=records["main"],
        summary=MatchPackageSummary(
            event_id=draw.event_id,
            total_matches=total,
            qualification_matches=len(records["qualification"]),
            main_draw_matches=len(records["main"]),
        ),
        metadata=MatchPackageMetadata(
            event_id=draw.event_id,
            season="2000/2001",
            seed=99,
            dry_run=False,
            persisted=True,
            build_fingerprint="match-package",
            draw_package_fingerprint="legacy-not-authority",
            active_players_fingerprint="players",
        ),
    )


def test_canonical_main_draw_owns_feeders_and_terminal():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_draw_input(),
        command_id="draw",
    )
    package = _package(draw)
    projection = project_canonical_draw_to_match_topology(
        draw=draw,
        package=package,
    )

    assert projection.draw_authority_fingerprint == draw.fingerprint
    assert len(projection.plans) == 3
    final = next(
        plan for plan in projection.plans if plan.group_id == projection.terminal_group_id
    )
    assert all(source.startswith("winner:") for source in final.participant_sources)
    first_round = [
        plan
        for plan in projection.plans
        if plan.group_id != projection.terminal_group_id
    ]
    assert all(
        all(source.startswith("player:") for source in plan.participant_sources)
        for plan in first_round
    )
    assert projection.bye_match_ids == ()
    assert projection.qualifier_promotions == ()


def test_matchpackage_cannot_override_canonical_direct_participant():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_draw_input(),
        command_id="draw",
    )
    package = _package(draw)
    first = package.main_draw_matches[0]
    package.main_draw_matches[0] = first.model_copy(
        update={"top_player_id": "WRONG"}
    )

    with pytest.raises(ValueError, match="direct participant conflicts"):
        project_canonical_draw_to_match_topology(draw=draw, package=package)


def test_matchpackage_cannot_override_canonical_feeder_target():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_draw_input(),
        command_id="draw",
    )
    package = _package(draw)
    first = package.main_draw_matches[0]
    package.main_draw_matches[0] = first.model_copy(
        update={"winner_to_match_id": "foreign-target"}
    )

    with pytest.raises(ValueError, match="feeder target conflicts"):
        project_canonical_draw_to_match_topology(draw=draw, package=package)


def test_canonical_bye_is_removed_from_execution_and_freezes_known_winner():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_draw_input(with_bye=True),
        command_id="draw",
    )
    package = _package(draw)
    projection = project_canonical_draw_to_match_topology(
        draw=draw,
        package=package,
    )

    assert len(projection.bye_match_ids) == 1
    assert len(projection.bye_winners) == 1
    assert len(projection.plans) == 2
    bye_id, bye_winner = projection.bye_winners[0]
    assert bye_id in projection.bye_match_ids
    assert bye_winner == "A"
    final = next(
        plan for plan in projection.plans if plan.group_id == projection.terminal_group_id
    )
    assert f"player:{bye_winner}" in final.participant_sources


def test_qualification_terminal_owns_main_placeholder_promotion():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_draw_input(with_qualification=True),
        command_id="draw",
    )
    package = _package(draw)
    projection = project_canonical_draw_to_match_topology(
        draw=draw,
        package=package,
    )

    assert len(projection.plans) == 4
    assert len(projection.qualifier_promotions) == 1
    promotion = projection.qualifier_promotions[0]
    qualification_plan = next(
        plan for plan in projection.plans if plan.match_id == promotion.source_match_id
    )
    target = next(
        plan for plan in projection.plans if plan.match_id == promotion.target_match_id
    )
    assert qualification_plan.event_id == draw.event_id
    assert f"winner:{qualification_plan.match_id}" in target.participant_sources
    assert promotion.qualifier_index == 1



def test_v5_draw_binding_does_not_rewrite_historical_v4_authority_fingerprint():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_draw_input(),
        command_id="draw",
    )
    package = _package(draw)
    week = RankingWeek(season_index=0, week=1)
    payload = package.model_dump(mode="json")
    payload["metadata"].pop("persistence_path", None)
    historical_expected = fingerprint(
        {
            "scope": ["run", "branch", week.ordinal],
            "tournaments": [
                {
                    "package": payload,
                    "point_award_authority": None,
                }
            ],
        }
    )

    historical_actual = AuthoritativeRunSimulationDriver._tournament_authority_fingerprint(
        "run",
        "branch",
        week,
        ((package, None, None),),
    )
    canonical_actual = AuthoritativeRunSimulationDriver._tournament_authority_fingerprint(
        "run",
        "branch",
        week,
        ((package, None, draw.fingerprint),),
    )

    assert historical_actual == historical_expected
    assert canonical_actual != historical_actual



def test_historical_frozen_authority_does_not_adopt_later_canonical_draw(monkeypatch):
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_draw_input(),
        command_id="draw",
    )
    package = _package(draw)
    payload = json.dumps(
        {
            "schema_version": "adopted_tournament_authority.v4",
            "tournaments": [
                {
                    "package": package.model_dump(mode="json"),
                    "point_award_authority": {
                        "event_id": "event",
                        "authority_fingerprint": "4" * 64,
                        "payload": {},
                    },
                }
            ],
        }
    )

    # Use the historical raw-package reader instead because constructing the
    # unrelated point-award authority contract is outside this topology test.
    payload = package.model_dump_json()

    class FakeSession:
        def get(self, model, key):
            if model is AdoptedTournamentAuthorityModel:
                return SimpleNamespace(package_json=payload)
            return None

    class FakeDrawStore:
        def __init__(self, session):
            pass

        def get(self, **kwargs):
            return draw

    monkeypatch.setattr(
        driver_module,
        "TournamentDrawAuthorityStore",
        FakeDrawStore,
    )
    driver = AuthoritativeRunSimulationDriver(None, None, None)
    resolved = driver._canonical_draw_binding(
        FakeSession(),
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=1),
        event_id="event",
    )
    assert resolved is None
