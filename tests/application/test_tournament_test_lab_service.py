from __future__ import annotations

from types import SimpleNamespace

import pytest

from beta_engine.application.run_branch_creation_service import RunBranchCreationService
from beta_engine.application.run_container_creation_service import RunContainerCreationService
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.tournament_test_lab_service import (
    TournamentLabRunSnapshotEvidence,
    TournamentLabAssertions,
    TournamentLabRequest,
    TournamentLabRunDraftApplyRequest,
    TournamentLabRunDraftPreviewRequest,
    TournamentLabSavedRevisionCopyRequest,
    TournamentLabScenario,
    TournamentLabSessionCreateRequest,
    TournamentLabSessionImportRequest,
    TournamentLabSessionRunRequest,
    TournamentLabSessionUpdateRequest,
    TournamentTestLabService,
)
from beta_engine.domain.matches import MatchParticipantContext
from beta_engine.domain.players import HiddenCareerTraits, Player
from beta_engine.domain.players.attribute_catalog import CANONICAL_PLAYER_ATTRIBUTES
from beta_engine.domain.players.sporting import PlayerSportingRecord, PlayerSportingWeekState
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.entry_field import TournamentEntryField, TournamentEntryFieldCapacity
from beta_engine.domain.tournaments.format_authority import TournamentFormatAuthority
from beta_engine.domain.tournaments.draw_input_authority import TournamentDrawInputAuthority
from beta_engine.infrastructure.db.repositories import BranchSavedRevisionHistoryRecord, BranchSavedRevisionRecord
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    Base,
    RunTournamentLabDraftModel,
    TournamentLabSessionModel,
)
from beta_engine.infrastructure.db.run_tournament_lab_draft_state import (
    RUN_TOURNAMENT_LAB_DRAFT_COMPONENT_KEY,
    load_saved_run_tournament_lab_drafts,
)


pytestmark = pytest.mark.pr_critical


def _participant(player_id: str, base: int) -> MatchParticipantContext:
    return MatchParticipantContext(
        player=Player(
            player_id=player_id,
            name=player_id,
            age=27,
            nationality="TST",
            technique=base,
            movement=base,
            physical=base,
            mental=base,
            consistency=base,
            clutch=base,
            recovery=base,
            play_style="tempo-controller",
            archetype="all-court tactician",
            hidden_career_traits=HiddenCareerTraits(
                potential_ceiling=90,
                growth_curve="balanced",
                professionalism=0.7,
                ambition=0.7,
                travel_tolerance=0.7,
                schedule_aggression=0.6,
                injury_proneness=0.2,
                resilience=0.8,
            ),
        )
    )


def _scenario(
    *,
    count: int = 8,
    capacity: int = 8,
    format_kind: str = "knockout",
    stop_after_round: int | None = None,
) -> TournamentLabScenario:
    participants = tuple(
        _participant(f"P{index}", 94 - index * 3)
        for index in range(1, count + 1)
    )
    return TournamentLabScenario(
        scenario_id=f"lab-{count}-{capacity}",
        display_name="Tournament Lab test",
        format_kind=format_kind,
        participants=participants,
        main_draw_size=capacity,
        seed_order_player_ids=tuple(item.player.player_id for item in participants),
        draw_seed=1701,
        match_seed=2701,
        stop_after_round=stop_after_round,
        assertions=TournamentLabAssertions(
            expected_played_match_count=(count - 1 if capacity == count else None)
        ),
    )


def test_tournament_lab_replays_shared_draw_and_match_kernels_deterministically() -> None:
    service = TournamentTestLabService()
    request = TournamentLabRequest(scenario=_scenario())

    first = service.run(request)
    second = service.run(request)

    assert first == second
    assert first.compatibility.runnable_in_lab is True
    assert first.compatibility.normal_run_compatible is True
    assert first.compatibility.run_mutation_performed is False
    assert first.compatibility.run_live_link is False
    assert any("TournamentDrawAuthorityBuilder" in value for value in first.compatibility.shared_authorities)
    assert any("MatchEngine.simulate" in value for value in first.compatibility.shared_authorities)
    assert first.draw is not None
    assert first.draw.main.bracket_size == 8
    assert first.draw.algorithm_version == "idealized_seed_tiers.v2"
    assert first.format_authority_fingerprint
    assert first.draw_input_fingerprint
    assert first.draw_authority_fingerprint
    assert len(first.runs) == 1
    run = first.runs[0]
    assert run.tournament_complete is True
    assert run.champion_player_id in {f"P{index}" for index in range(1, 9)}
    assert run.played_match_count == 7
    assert all(row.status == "played" for row in run.match_results)
    assert all(row.result_fingerprint for row in run.match_results)
    assert all(row.rally_count > 0 for row in run.match_results)
    assert run.assertions[0].status == "passed"


def test_tournament_lab_batch_changes_match_seed_without_redrawing() -> None:
    result = TournamentTestLabService().run(
        TournamentLabRequest(
            scenario=_scenario(),
            batch_match_seeds=(100, 101, 102, 103),
        )
    )

    assert [row.match_seed for row in result.runs] == [100, 101, 102, 103]
    assert result.diagnostics.run_count == 4
    assert result.diagnostics.completed_run_count == 4
    assert sum(result.diagnostics.champions.values()) == 4
    assert result.diagnostics.average_played_match_count == 7
    assert len({row.run_fingerprint for row in result.runs}) >= 1
    assert result.draw_authority_fingerprint == result.draw.fingerprint


def test_tournament_lab_can_stop_after_round_without_fabricating_champion() -> None:
    scenario = _scenario(stop_after_round=1).model_copy(
        update={
            "assertions": TournamentLabAssertions(
                expected_champion_player_id="P1",
                expected_played_match_count=4,
            )
        }
    )
    result = TournamentTestLabService().run(TournamentLabRequest(scenario=scenario))

    run = result.runs[0]
    assert run.completed_rounds == 1
    assert run.tournament_complete is False
    assert run.champion_player_id is None
    assert run.played_match_count == 4
    assertions = {item.assertion: item for item in run.assertions}
    assert assertions["expected_champion_player_id"].status == "not_evaluated"
    assert assertions["expected_played_match_count"].status == "passed"


def test_tournament_lab_runs_unusual_bye_geometry_but_reports_normal_run_incompatibility() -> None:
    result = TournamentTestLabService().run(
        TournamentLabRequest(scenario=_scenario(count=8, capacity=16))
    )

    assert result.compatibility.runnable_in_lab is True
    assert result.compatibility.normal_run_compatible is False
    assert any(
        issue.code == "NONCANONICAL_CLASSIC_CAPACITY"
        for issue in result.compatibility.issues
    )
    assert result.draw is not None
    assert result.draw.main.bracket_size == 16
    assert result.runs[0].bye_advance_count > 0
    assert result.runs[0].champion_player_id is not None


def test_tournament_lab_invalid_or_unsupported_draft_is_inspectable_without_result() -> None:
    scenario = _scenario(format_kind="groups")
    result = TournamentTestLabService().run(TournamentLabRequest(scenario=scenario))

    assert result.compatibility.runnable_in_lab is False
    assert result.compatibility.normal_run_compatible is False
    assert any(
        issue.code == "GROUP_GEOMETRY_INCOMPLETE"
        for issue in result.compatibility.issues
    )
    assert result.draw is None
    assert result.runs == ()
    assert result.diagnostics.run_count == 0


def test_tournament_lab_seed_order_mismatch_blocks_execution_without_mutation() -> None:
    scenario = _scenario().model_copy(update={"seed_order_player_ids": ("P1", "P2")})
    result = TournamentTestLabService().run(TournamentLabRequest(scenario=scenario))

    assert result.compatibility.runnable_in_lab is False
    assert any(
        issue.code == "SEED_ORDER_NOT_FIELD_PERMUTATION"
        for issue in result.compatibility.issues
    )
    assert result.compatibility.run_mutation_performed is False
    assert result.runs == ()


def test_tournament_lab_rejects_duplicate_or_oversized_batch_seed_lists() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        TournamentLabRequest(scenario=_scenario(), batch_match_seeds=(1, 1))

    with pytest.raises(ValueError, match="at most"):
        TournamentLabRequest(
            scenario=_scenario(),
            batch_match_seeds=tuple(range(101)),
        )


def test_tournament_lab_built_ins_are_deterministic_and_read_only() -> None:
    service = TournamentTestLabService()
    rows = service.list_built_in_scenarios()

    assert [item.scenario_id for item in rows] == [
        "standard-eight-player-knockout",
        "oversized-eight-player-lab-bracket",
        "qualification-two-sections-to-eight-main",
        "two-groups-of-four",
        "two-groups-to-four-player-knockout",
    ]
    assert all(item.read_only is True for item in rows)
    assert all(item.scenario_fingerprint == item.scenario.fingerprint for item in rows)
    assert rows == TournamentTestLabService().list_built_in_scenarios()



def _persistent_service(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'tournament-lab-sessions.db'}"))
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    counter = {"value": 0}

    def id_factory(kind: str) -> str:
        counter["value"] += 1
        return f"{kind}-{counter['value']}"

    return engine, factory, TournamentTestLabService(factory, id_factory)


def test_tournament_lab_new_test_session_clones_built_in_without_live_link(tmp_path) -> None:
    engine, factory, service = _persistent_service(tmp_path)
    try:
        built_in = service.list_built_in_scenarios()[0]
        created = service.create_session(
            TournamentLabSessionCreateRequest(
                display_name="My Tournament Session",
                built_in_scenario_id=built_in.scenario_id,
            )
        )

        assert created.session_id == "tournament-lab-session-1"
        assert created.version == 1
        assert created.scenario.source_kind == "built_in_copy"
        assert created.scenario.source_reference == built_in.scenario_id
        assert created.scenario.source_fingerprint == built_in.scenario_fingerprint
        assert created.scenario.scenario_id == f"session-copy:{built_in.scenario_id}"
        assert created.scenario.display_name == "My Tournament Session"
        assert created.scenario.fingerprint != built_in.scenario_fingerprint
        assert service.get_session(created.session_id) == created
        assert service.list_sessions() == (created,)

        with factory() as session:
            row = session.get(TournamentLabSessionModel, created.session_id)
            assert row is not None
            assert row.version == 1
            assert row.source_kind == "built_in_copy"
            assert row.source_reference == built_in.scenario_id
            assert row.source_fingerprint == built_in.scenario_fingerprint
            assert row.fingerprint == created.fingerprint

        assert service.list_built_in_scenarios()[0] == built_in
    finally:
        engine.dispose()


def test_tournament_lab_session_update_and_run_use_reviewed_fingerprint(tmp_path) -> None:
    engine, _, service = _persistent_service(tmp_path)
    try:
        created = service.create_session(
            TournamentLabSessionCreateRequest(
                display_name="Editable Tournament",
                scenario=_scenario(),
            )
        )
        changed = created.scenario.model_copy(
            update={
                "draw_seed": created.scenario.draw_seed + 1,
                "display_name": "Edited Tournament",
            }
        )

        with pytest.raises(ValueError, match="changed since it was reviewed"):
            service.update_session(
                created.session_id,
                TournamentLabSessionUpdateRequest(
                    expected_session_fingerprint="0" * 64,
                    display_name="stale",
                    scenario=changed,
                ),
            )

        updated = service.update_session(
            created.session_id,
            TournamentLabSessionUpdateRequest(
                expected_session_fingerprint=created.fingerprint,
                display_name="Edited Tournament",
                scenario=changed,
            ),
        )
        assert updated.version == 2
        assert updated.display_name == "Edited Tournament"
        assert updated.scenario.draw_seed == created.scenario.draw_seed + 1

        with pytest.raises(ValueError, match="changed since it was reviewed"):
            service.run_session(
                updated.session_id,
                TournamentLabSessionRunRequest(
                    expected_session_fingerprint=created.fingerprint,
                    batch_match_seeds=(81, 82),
                ),
            )

        result = service.run_session(
            updated.session_id,
            TournamentLabSessionRunRequest(
                expected_session_fingerprint=updated.fingerprint,
                batch_match_seeds=(81, 82),
            ),
        )
        assert result.diagnostics.run_count == 2
        assert result.compatibility.run_mutation_performed is False
        assert result.compatibility.run_live_link is False
        assert result.scenario_fingerprint == updated.scenario.fingerprint
    finally:
        engine.dispose()



def test_tournament_lab_export_model_accepts_its_api_serialized_session_shape(tmp_path) -> None:
    engine, _, service = _persistent_service(tmp_path)
    try:
        created = service.create_session(
            TournamentLabSessionCreateRequest(display_name="Round trip", scenario=_scenario())
        )
        exported = service.export_session(created.session_id)
        api_payload = exported.model_dump(mode="json")

        reparsed = type(exported).model_validate(api_payload)

        assert reparsed == exported
        assert reparsed.export_fingerprint == exported.export_fingerprint
    finally:
        engine.dispose()


def test_tournament_lab_session_export_import_is_reviewed_copy_without_live_link(tmp_path) -> None:
    engine, _, service = _persistent_service(tmp_path)
    try:
        created = service.create_session(
            TournamentLabSessionCreateRequest(
                display_name="Export Source",
                scenario=_scenario(),
            )
        )
        exported = service.export_session(created.session_id)

        assert exported.session == created
        assert exported.session_fingerprint == created.fingerprint
        assert exported.scenario_fingerprint == created.scenario.fingerprint
        assert len(exported.export_fingerprint) == 64

        imported = service.import_session(
            TournamentLabSessionImportRequest(
                export_payload=exported,
                expected_export_fingerprint=exported.export_fingerprint,
                display_name="Imported Copy",
            )
        )

        assert imported.session_id != created.session_id
        assert imported.display_name == "Imported Copy"
        assert imported.version == 1
        assert imported.scenario == created.scenario
        assert imported.fingerprint != created.fingerprint
        assert service.get_session(created.session_id) == created
        assert service.get_session(imported.session_id) == imported

        changed = imported.scenario.model_copy(update={"draw_seed": imported.scenario.draw_seed + 99})
        updated = service.update_session(
            imported.session_id,
            TournamentLabSessionUpdateRequest(
                expected_session_fingerprint=imported.fingerprint,
                scenario=changed,
            ),
        )
        assert updated.scenario.draw_seed != created.scenario.draw_seed
        assert service.get_session(created.session_id).scenario == created.scenario
    finally:
        engine.dispose()


def test_tournament_lab_session_import_rejects_stale_reviewed_export(tmp_path) -> None:
    engine, _, service = _persistent_service(tmp_path)
    try:
        created = service.create_session(
            TournamentLabSessionCreateRequest(display_name="Export Source", scenario=_scenario())
        )
        exported = service.export_session(created.session_id)

        with pytest.raises(ValueError, match="changed since it was reviewed"):
            service.import_session(
                TournamentLabSessionImportRequest(
                    export_payload=exported,
                    expected_export_fingerprint="0" * 64,
                )
            )
        assert service.list_sessions() == (created,)
    finally:
        engine.dispose()

def test_tournament_lab_session_persistence_fails_closed_on_tampered_row(tmp_path) -> None:
    engine, factory, service = _persistent_service(tmp_path)
    try:
        created = service.create_session(
            TournamentLabSessionCreateRequest(
                display_name="Tamper Tournament",
                scenario=_scenario(),
            )
        )
        with factory.begin() as session:
            session.get(TournamentLabSessionModel, created.session_id).fingerprint = "0" * 64

        with pytest.raises(ValueError, match="persistence fingerprint mismatch"):
            service.get_session(created.session_id)
    finally:
        engine.dispose()


def test_tournament_lab_session_create_contract_requires_exactly_one_source() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        TournamentLabSessionCreateRequest(display_name="missing")

    with pytest.raises(ValueError, match="exactly one"):
        TournamentLabSessionCreateRequest(
            display_name="ambiguous",
            scenario=_scenario(),
            built_in_scenario_id="standard-eight-player-knockout",
        )



def test_tournament_lab_qualification_resolves_q_sections_into_main_placeholders() -> None:
    service = TournamentTestLabService()
    built_in = next(
        item for item in service.list_built_in_scenarios()
        if item.scenario_id == "qualification-two-sections-to-eight-main"
    )

    result = service.run(
        TournamentLabRequest(
            scenario=built_in.scenario,
            batch_match_seeds=(501,),
        )
    )

    assert result.compatibility.runnable_in_lab is True
    assert result.compatibility.normal_run_compatible is True
    assert result.draw is not None
    assert len(result.draw.qualification_brackets) == 2
    assert [section.section_id for section in result.draw.qualification_brackets] == ["Q1", "Q2"]
    assert result.draw.main.qualifier_placeholder_slots
    assert {item[0] for item in result.draw.main.qualifier_placeholder_slots} == {"Q1", "Q2"}

    run = result.runs[0]
    assert run.tournament_complete is True
    assert len(run.qualification_results) == 2
    assert [row.section_id for row in run.qualification_results] == ["Q1", "Q2"]
    assert all(row.winner_player_id is not None for row in run.qualification_results)
    assert sum(row.played_match_count for row in run.qualification_results) == 6
    assert run.played_match_count == 13
    assert run.assertions[0].status == "passed"
    q_winners = {row.winner_player_id for row in run.qualification_results}
    assert q_winners.issubset(
        {item.player.player_id for item in built_in.scenario.participants}
    )
    main_first_round_players = {
        player_id
        for row in run.match_results
        if row.round_number == 1
        for player_id in (row.player_a_id, row.player_b_id)
        if player_id is not None
    }
    assert q_winners.issubset(main_first_round_players)


def test_tournament_lab_qualification_diagnostics_fail_closed_for_invalid_geometry() -> None:
    participants = tuple(_participant(f"QBAD-{index}", 90 - index) for index in range(1, 9))
    scenario = TournamentLabScenario(
        scenario_id="bad-q",
        display_name="Bad Q",
        format_kind="knockout",
        participants=participants,
        main_draw_size=4,
        qualification_draw_size=6,
        qualifier_spots=2,
        qualification_player_ids=tuple(item.player.player_id for item in participants[4:]),
        seed_order_player_ids=tuple(item.player.player_id for item in participants),
        draw_seed=42,
        match_seed=43,
    )

    result = TournamentTestLabService().run(TournamentLabRequest(scenario=scenario))

    assert result.compatibility.runnable_in_lab is False
    assert result.draw is None
    assert result.runs == ()
    assert any(
        issue.code == "QUALIFICATION_SECTION_NOT_POWER_OF_TWO"
        for issue in result.compatibility.issues
    )


def test_tournament_lab_no_qualification_scenario_fingerprint_compatibility() -> None:
    scenario = _scenario()
    payload = scenario.model_dump(mode="json")
    assert "qualification_draw_size" not in payload
    assert "qualifier_spots" not in payload
    assert "qualification_player_ids" not in payload



def test_tournament_lab_pure_groups_use_shared_topology_schedule_and_standings() -> None:
    service = TournamentTestLabService()
    scenario = next(
        item.scenario for item in service.list_built_in_scenarios()
        if item.scenario_id == "two-groups-of-four"
    )

    result = service.run(TournamentLabRequest(scenario=scenario))

    assert result.compatibility.runnable_in_lab is True
    assert result.compatibility.normal_run_compatible is True
    assert result.draw is None
    assert result.topology_authority_fingerprint
    assert result.group_schedule_fingerprint
    assert any("TournamentTopologyAuthorityBuilder" in value for value in result.compatibility.shared_authorities)
    assert any("TournamentGroupStandingsBuilder" in value for value in result.compatibility.shared_authorities)

    run = result.runs[0]
    assert run.tournament_complete is True
    assert run.champion_player_id is None
    assert run.played_match_count == 12
    assert run.group_stage is not None
    assert run.group_stage.blocking_issue is None
    assert run.group_stage.match_day_count == 3
    assert len(run.group_stage.match_results) == 12
    assert run.group_stage.standings is not None
    assert len(run.group_stage.standings.groups) == 2
    assert all(len(group.rows) == 4 for group in run.group_stage.standings.groups)
    assert run.match_results == ()
    assert run.assertions[0].status == "passed"


def test_tournament_lab_groups_to_knockout_use_frozen_group_positions_and_crossings() -> None:
    service = TournamentTestLabService()
    scenario = next(
        item.scenario for item in service.list_built_in_scenarios()
        if item.scenario_id == "two-groups-to-four-player-knockout"
    )

    result = service.run(TournamentLabRequest(scenario=scenario))

    assert result.compatibility.runnable_in_lab is True
    run = result.runs[0]
    assert run.tournament_complete is True
    assert run.group_stage is not None
    assert run.group_stage.standings is not None
    assert run.hybrid_knockout_bracket is not None
    assert run.hybrid_knockout_bracket.entrant_count == 4
    assert run.hybrid_knockout_bracket.round_count == 2
    assert run.played_match_count == 15
    assert len(run.match_results) == 3
    assert run.champion_player_id is not None
    standings = run.group_stage.standings
    by_position = {
        (group.group_index, row.position): row.player_id
        for group in standings.groups
        for row in group.rows
    }
    first_round = sorted(
        (row for row in run.match_results if row.round_number == 1),
        key=lambda row: row.round_sequence,
    )
    assert {
        first_round[0].player_a_id,
        first_round[0].player_b_id,
    } == {by_position[(1, 1)], by_position[(2, 2)]}
    assert {
        first_round[1].player_a_id,
        first_round[1].player_b_id,
    } == {by_position[(2, 1)], by_position[(1, 2)]}
    assert run.assertions[0].status == "passed"


def test_tournament_lab_hybrid_stop_after_first_knockout_round_has_no_fake_champion() -> None:
    service = TournamentTestLabService()
    scenario = next(
        item.scenario for item in service.list_built_in_scenarios()
        if item.scenario_id == "two-groups-to-four-player-knockout"
    ).model_copy(
        update={
            "stop_after_round": 1,
            "assertions": TournamentLabAssertions(
                expected_champion_player_id="TLG-P1",
                expected_played_match_count=14,
            ),
        }
    )

    run = service.run(TournamentLabRequest(scenario=scenario)).runs[0]

    assert run.tournament_complete is False
    assert run.completed_rounds == 1
    assert run.champion_player_id is None
    assert run.played_match_count == 14
    assert len(run.match_results) == 2
    assertions = {item.assertion: item for item in run.assertions}
    assert assertions["expected_champion_player_id"].status == "not_evaluated"
    assert assertions["expected_played_match_count"].status == "passed"


def test_tournament_lab_groups_fail_closed_on_bad_crossing_contract() -> None:
    service = TournamentTestLabService()
    scenario = next(
        item.scenario for item in service.list_built_in_scenarios()
        if item.scenario_id == "two-groups-to-four-player-knockout"
    ).model_copy(update={"knockout_crossings": ()})

    result = service.run(TournamentLabRequest(scenario=scenario))

    assert result.compatibility.runnable_in_lab is False
    assert result.runs == ()
    assert any(
        issue.code == "HYBRID_CROSSINGS_INCOMPLETE"
        for issue in result.compatibility.issues
    )


class _TournamentHistoricalRepository:
    def __init__(self):
        revision = BranchSavedRevisionRecord(
            revision_id="revision-tournament",
            run_id="run-tournament",
            branch_id="branch-tournament",
            sequence=1,
            parent_revision_id=None,
            kind="test",
            payload_schema_version="test.v1",
            content_hash_algorithm="sha256",
            content_hash="a" * 64,
            payload={"content": {}},
            change_summary={},
        )
        self.history = BranchSavedRevisionHistoryRecord(
            run_id="run-tournament",
            branch_id="branch-tournament",
            saved_head_revision_id=revision.revision_id,
            saved_revisions=(revision,),
        )

    def get_branch_saved_revision_history(self, *, run_id: str, branch_id: str):
        if (run_id, branch_id) != (self.history.run_id, self.history.branch_id):
            raise KeyError("history missing")
        return self.history


def _historical_tournament_sources():
    player_ids = ("HIST-T1", "HIST-T2", "HIST-T3", "HIST-T4")
    capacity = TournamentEntryFieldCapacity(main_draw_size=4)
    field = TournamentEntryField(
        run_id="run-tournament",
        branch_id="branch-tournament",
        event_id="event-tournament",
        mode="initial",
        capacity=capacity,
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        applications_fingerprint="3" * 64,
        direct_main_player_ids=player_ids,
    )
    format_authority = TournamentFormatAuthority(
        run_id="run-tournament",
        branch_id="branch-tournament",
        event_id="event-tournament",
        target_season_index=0,
        configured_by_command_id="format-command",
        entry_field_fingerprint=field.fingerprint,
        format_kind="knockout",
    )
    draw_input = TournamentDrawInputAuthority(
        run_id="run-tournament",
        branch_id="branch-tournament",
        event_id="event-tournament",
        committed_by_command_id="draw-input-command",
        draw_seed=9876,
        main_seed_count=1,
        qualification_seed_count=0,
        field_sequence=1,
        capacity=capacity,
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint=field.fingerprint,
        direct_main_player_ids=player_ids,
        qualification_player_ids=(),
        qualifier_placeholder_ids=(),
        withdrawn_player_ids=(),
        main_seed_player_ids=(player_ids[0],),
        qualification_seed_player_ids=(),
    )
    component = {
        "entry_fields": (
            {
                "event_id": field.event_id,
                "sequence": 1,
                "payload_json": field.model_dump_json(),
            },
        ),
        "format_authorities": (
            {
                "event_id": format_authority.event_id,
                "payload_json": format_authority.model_dump_json(),
            },
        ),
        "draw_inputs": (
            {
                "event_id": draw_input.event_id,
                "payload_json": draw_input.model_dump_json(),
            },
        ),
        "topology_authorities": (),
    }

    class Profile:
        def __init__(self, player_id: str, index: int):
            self.player_id = player_id
            self.name = player_id
            self.nationality = "CZE"
            self.birth_year = 1974 + index
            self.birth_year_week = 1
            self.play_style = "attacking"
            self.archetype = "Power Attacker"
            self.source_generation_fingerprint = f"profile:{player_id}"
            self.hidden_career_traits = HiddenCareerTraits(
                potential_ceiling=99,
                growth_curve="Standard",
                professionalism=0.7,
                ambition=0.7,
                travel_tolerance=0.7,
                schedule_aggression=0.6,
                injury_proneness=0.2,
                resilience=0.8,
            )

    profiles = tuple(Profile(player_id, index) for index, player_id in enumerate(player_ids))
    records = tuple(
        PlayerSportingRecord(
            player_id=player_id,
            attributes=tuple((name, 160 - index * 5) for name in CANONICAL_PLAYER_ATTRIBUTES),
            potential_ovr=180,
            potential_identity=f"potential:{player_id}",
            potential_provenance="test",
            development_timing="Standard",
            current_form=110,
            long_term_form_norm=100,
            match_sharpness=75,
            long_term_fatigue=10,
        )
        for index, player_id in enumerate(player_ids)
    )
    sporting = PlayerSportingWeekState(
        run_id="run-tournament",
        branch_id="branch-tournament",
        week=RankingWeek(season_index=0, week=1),
        players=records,
        completed_context_fingerprint="bootstrap:not-a-completed-week",
        source_initial_world_fingerprint="4" * 64,
        stage_provenance="test",
    )

    class World:
        players = profiles

    return component, World(), sporting, player_ids


def test_tournament_lab_copies_verified_saved_revision_knockout_without_live_link(
    tmp_path, monkeypatch
) -> None:
    engine, factory, base_service = _persistent_service(tmp_path)
    try:
        component, world, sporting, player_ids = _historical_tournament_sources()
        import beta_engine.application.tournament_test_lab_service as module

        monkeypatch.setattr(
            module,
            "load_saved_simulation_slot_component",
            lambda payload, *, run_id, branch_id: component,
        )
        monkeypatch.setattr(
            module,
            "load_saved_initial_world",
            lambda payload, *, run_id, branch_id: world,
        )
        monkeypatch.setattr(
            module,
            "load_saved_sporting_bundle",
            lambda payload, *, run_id, branch_id: ((sporting,), None),
        )
        service = TournamentTestLabService(
            factory,
            base_service._id_factory,
            repository=_TournamentHistoricalRepository(),
        )

        copied = service.copy_saved_revision_tournament(
            TournamentLabSavedRevisionCopyRequest(
                display_name="Historical Tournament Copy",
                product_run_id="run-tournament",
                branch_id="branch-tournament",
                saved_revision_id="revision-tournament",
                event_id="event-tournament",
            )
        )

        assert copied.version == 1
        assert copied.scenario.source_kind == "run_snapshot_copy"
        assert copied.scenario.source_snapshot is not None
        assert copied.scenario.source_fingerprint == copied.scenario.source_snapshot.fingerprint
        assert copied.scenario.source_snapshot.saved_revision_content_hash == "a" * 64
        assert copied.scenario.source_snapshot.event_id == "event-tournament"
        assert copied.scenario.draw_seed == 9876
        assert copied.scenario.main_draw_size == 4
        assert copied.scenario.seed_order_player_ids[0] == player_ids[0]
        assert {item.player.player_id for item in copied.scenario.participants} == set(player_ids)
        assert len(copied.scenario.source_snapshot.participant_projection_fingerprints) == 4

        result = service.run_session(
            copied.session_id,
            TournamentLabSessionRunRequest(
                expected_session_fingerprint=copied.fingerprint,
                batch_match_seeds=(9001,),
            ),
        )
        assert result.compatibility.runnable_in_lab is True
        assert result.compatibility.run_mutation_performed is False
        assert result.compatibility.run_live_link is False
        assert result.runs[0].tournament_complete is True
    finally:
        engine.dispose()


def test_tournament_lab_historical_copy_fails_closed_for_wc_until_replacement_slice(
    tmp_path, monkeypatch
) -> None:
    engine, factory, base_service = _persistent_service(tmp_path)
    try:
        component, world, sporting, _ = _historical_tournament_sources()
        draw = TournamentDrawInputAuthority.model_validate_json(
            component["draw_inputs"][0]["payload_json"]
        )
        changed = draw.model_copy(
            update={"replacement_source_authority_fingerprints": ("5" * 64,)}
        )
        component = dict(component)
        component["draw_inputs"] = (
            {
                "event_id": changed.event_id,
                "payload_json": changed.model_dump_json(),
            },
        )
        import beta_engine.application.tournament_test_lab_service as module
        monkeypatch.setattr(module, "load_saved_simulation_slot_component", lambda *args, **kwargs: component)
        monkeypatch.setattr(module, "load_saved_initial_world", lambda *args, **kwargs: world)
        monkeypatch.setattr(module, "load_saved_sporting_bundle", lambda *args, **kwargs: ((sporting,), None))
        service = TournamentTestLabService(
            factory,
            base_service._id_factory,
            repository=_TournamentHistoricalRepository(),
        )

        with pytest.raises(ValueError, match="replacement-source fallback lineage|WC/LL/replacement"):
            service.copy_saved_revision_tournament(
                TournamentLabSavedRevisionCopyRequest(
                    display_name="Unsupported historical copy",
                    product_run_id="run-tournament",
                    branch_id="branch-tournament",
                    saved_revision_id="revision-tournament",
                    event_id="event-tournament",
                )
            )
        assert service.list_sessions() == ()
    finally:
        engine.dispose()


def test_tournament_lab_run_snapshot_source_fingerprint_must_bind_evidence() -> None:
    evidence = TournamentLabRunSnapshotEvidence(
        product_run_id="run-a",
        branch_id="branch-a",
        saved_revision_id="revision-a",
        saved_revision_content_hash="a" * 64,
        event_id="event-a",
        entry_field_fingerprint="b" * 64,
        format_authority_fingerprint="c" * 64,
        sporting_state_fingerprint="d" * 64,
        sporting_week_ordinal=0,
        participant_projection_fingerprints=("e" * 64,),
    )
    scenario = _scenario()
    with pytest.raises(ValueError, match="source snapshot fingerprint"):
        TournamentLabScenario(
            **scenario.model_dump(
                mode="python",
                exclude={"source_kind", "source_reference", "source_fingerprint", "source_snapshot"},
            ),
            source_kind="run_snapshot_copy",
            source_reference="run-a/branch-a/revision-a/event-a",
            source_fingerprint="0" * 64,
            source_snapshot=evidence,
        )


class _RunDraftPreviewRepository:
    def __init__(self, *, status: str = "clean", run_id: str = "target-run") -> None:
        self.status = status
        self.run_id = run_id

    def get_branch_revision_state(self, *, branch_id: str):
        if branch_id != "target-branch":
            raise KeyError("branch missing")
        return SimpleNamespace(
            run_id=self.run_id,
            branch_id=branch_id,
            saved_head_revision_id="target-revision-7",
            working_draft=SimpleNamespace(
                draft_version=12,
                status=self.status,
            ),
        )


def test_tournament_lab_run_draft_preview_binds_reviewed_session_and_target_head(
    tmp_path,
) -> None:
    engine, factory, base_service = _persistent_service(tmp_path)
    try:
        service = TournamentTestLabService(
            factory,
            base_service._id_factory,
            repository=_RunDraftPreviewRepository(),
        )
        created = service.create_session(
            TournamentLabSessionCreateRequest(
                display_name="Draft preview source",
                scenario=_scenario(),
            )
        )

        preview = service.preview_run_draft(
            created.session_id,
            TournamentLabRunDraftPreviewRequest(
                expected_session_fingerprint=created.fingerprint,
                product_run_id="target-run",
                branch_id="target-branch",
                event_id="target-event",
            ),
        )

        assert preview.schema_version == "tournament_test_lab_run_draft_preview.v1"
        assert preview.session_fingerprint == created.fingerprint
        assert preview.scenario_fingerprint == created.scenario.fingerprint
        assert preview.target_saved_revision_id == "target-revision-7"
        assert preview.target_working_draft_version == 12
        assert preview.target_working_draft_status == "clean"
        assert preview.ready_for_draft is True
        assert preview.mutation_performed is False
        assert preview.candidate.event_id == "target-event"
        assert preview.candidate.format_kind == created.scenario.format_kind
        assert preview.candidate_fingerprint == preview.candidate.fingerprint
        assert preview.issues == ()
    finally:
        engine.dispose()


def test_tournament_lab_run_draft_preview_fails_closed_on_dirty_or_stale_target(
    tmp_path,
) -> None:
    engine, factory, base_service = _persistent_service(tmp_path)
    try:
        service = TournamentTestLabService(
            factory,
            base_service._id_factory,
            repository=_RunDraftPreviewRepository(status="dirty"),
        )
        created = service.create_session(
            TournamentLabSessionCreateRequest(
                display_name="Blocked draft preview",
                scenario=_scenario(),
            )
        )

        with pytest.raises(ValueError, match="changed since it was reviewed"):
            service.preview_run_draft(
                created.session_id,
                TournamentLabRunDraftPreviewRequest(
                    expected_session_fingerprint="0" * 64,
                    product_run_id="target-run",
                    branch_id="target-branch",
                    event_id="target-event",
                ),
            )

        preview = service.preview_run_draft(
            created.session_id,
            TournamentLabRunDraftPreviewRequest(
                expected_session_fingerprint=created.fingerprint,
                product_run_id="target-run",
                branch_id="target-branch",
                event_id="target-event",
            ),
        )
        assert preview.ready_for_draft is False
        assert any(issue.code == "TARGET_WORKING_DRAFT_DIRTY" for issue in preview.issues)
        assert preview.mutation_performed is False

        wrong_run_service = TournamentTestLabService(
            factory,
            base_service._id_factory,
            repository=_RunDraftPreviewRepository(run_id="other-run"),
        )
        with pytest.raises(ValueError, match="does not belong"):
            wrong_run_service.preview_run_draft(
                created.session_id,
                TournamentLabRunDraftPreviewRequest(
                    expected_session_fingerprint=created.fingerprint,
                    product_run_id="target-run",
                    branch_id="target-branch",
                    event_id="target-event",
                ),
            )
    finally:
        engine.dispose()


def _run_backed_lab_service(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'tournament-lab-run-draft.db'}")
    )
    repository = SimulationPersistenceRepository(
        engine=engine,
        session_factory=create_session_factory(engine),
    )
    repository.bootstrap_schema()
    RunContainerCreationService(
        repository=repository,
        id_factory=iter(("run-lab", "branch-lab", "revision-root", "draft-root")).__next__,
    ).create_empty_run(display_name="Tournament Lab target")
    counter = {"value": 0}

    def ids(kind: str) -> str:
        counter["value"] += 1
        return f"{kind}-{counter['value']}"

    return engine, repository, TournamentTestLabService(
        repository._session_factory,
        ids,
        repository=repository,
    )


def test_tournament_lab_reviewed_run_draft_apply_is_atomic_idempotent_and_saveable(
    tmp_path,
) -> None:
    engine, repository, service = _run_backed_lab_service(tmp_path)
    try:
        created = service.create_session(
            TournamentLabSessionCreateRequest(
                display_name="Run draft source",
                scenario=_scenario(),
            )
        )
        preview = service.preview_run_draft(
            created.session_id,
            TournamentLabRunDraftPreviewRequest(
                expected_session_fingerprint=created.fingerprint,
                product_run_id="run-lab",
                branch_id="branch-lab",
                event_id="event-lab",
            ),
        )
        assert preview.ready_for_draft is True
        assert preview.preview_fingerprint == preview.fingerprint
        assert preview.target_saved_revision_id == "revision-root"
        assert preview.target_working_draft_version == 0

        request = TournamentLabRunDraftApplyRequest(
            command_id="apply-lab-draft-1",
            expected_session_fingerprint=created.fingerprint,
            product_run_id="run-lab",
            branch_id="branch-lab",
            event_id="event-lab",
            expected_saved_revision_id=preview.target_saved_revision_id,
            expected_working_draft_version=preview.target_working_draft_version,
            expected_preview_fingerprint=preview.fingerprint,
            expected_candidate_fingerprint=preview.candidate_fingerprint,
        )
        applied = service.apply_run_draft(created.session_id, request)
        assert applied.already_applied is False
        assert applied.working_draft_version == 1
        assert applied.candidate_fingerprint == preview.candidate_fingerprint

        replay = service.apply_run_draft(created.session_id, request)
        assert replay.already_applied is True
        assert replay.proposal_fingerprint == applied.proposal_fingerprint

        with repository._session_factory() as db:
            row = db.get(
                RunTournamentLabDraftModel,
                ("run-lab", "branch-lab", "event-lab"),
            )
            assert row is not None
            assert row.fingerprint == applied.proposal_fingerprint

        draft = repository.get_branch_revision_state(
            branch_id="branch-lab"
        ).working_draft
        assert draft.status == "dirty"
        assert draft.draft_version == 1
        assert draft.change_count == 1

        saved = RunWorkingDraftService(
            repository=repository,
            id_factory=iter(("revision-lab-draft", "audit-lab-draft")).__next__,
        ).save(
            run_id="run-lab",
            branch_id="branch-lab",
            expected_draft_version=1,
        )
        component = saved.saved_revision.payload["content"][
            RUN_TOURNAMENT_LAB_DRAFT_COMPONENT_KEY
        ]
        assert component["fingerprint"] == applied.draft_state_fingerprint
        loaded = load_saved_run_tournament_lab_drafts(
            saved.saved_revision.payload,
            run_id="run-lab",
            branch_id="branch-lab",
        )
        assert loaded is not None
        assert loaded.drafts[0].fingerprint == applied.proposal_fingerprint
        assert saved.working_draft.status == "clean"
    finally:
        engine.dispose()


def test_tournament_lab_run_draft_apply_rejects_stale_review_without_partial_write(
    tmp_path,
) -> None:
    engine, repository, service = _run_backed_lab_service(tmp_path)
    try:
        created = service.create_session(
            TournamentLabSessionCreateRequest(
                display_name="Stale Run draft",
                scenario=_scenario(),
            )
        )
        preview = service.preview_run_draft(
            created.session_id,
            TournamentLabRunDraftPreviewRequest(
                expected_session_fingerprint=created.fingerprint,
                product_run_id="run-lab",
                branch_id="branch-lab",
                event_id="event-lab",
            ),
        )
        with pytest.raises(ValueError, match="preview changed"):
            service.apply_run_draft(
                created.session_id,
                TournamentLabRunDraftApplyRequest(
                    command_id="stale-lab-draft",
                    expected_session_fingerprint=created.fingerprint,
                    product_run_id="run-lab",
                    branch_id="branch-lab",
                    event_id="event-lab",
                    expected_saved_revision_id=preview.target_saved_revision_id,
                    expected_working_draft_version=preview.target_working_draft_version,
                    expected_preview_fingerprint="0" * 64,
                    expected_candidate_fingerprint=preview.candidate_fingerprint,
                ),
            )

        with repository._session_factory() as db:
            assert db.get(
                RunTournamentLabDraftModel,
                ("run-lab", "branch-lab", "event-lab"),
            ) is None
        state = repository.get_branch_revision_state(branch_id="branch-lab")
        assert state.working_draft.status == "clean"
        assert state.working_draft.draft_version == 0
    finally:
        engine.dispose()


def test_saved_tournament_lab_run_draft_materializes_safely_on_branch_fork(
    tmp_path,
) -> None:
    engine, repository, service = _run_backed_lab_service(tmp_path)
    try:
        created = service.create_session(
            TournamentLabSessionCreateRequest(
                display_name="Forkable Run draft",
                scenario=_scenario(),
            )
        )
        preview = service.preview_run_draft(
            created.session_id,
            TournamentLabRunDraftPreviewRequest(
                expected_session_fingerprint=created.fingerprint,
                product_run_id="run-lab",
                branch_id="branch-lab",
                event_id="event-lab",
            ),
        )
        applied = service.apply_run_draft(
            created.session_id,
            TournamentLabRunDraftApplyRequest(
                command_id="fork-source-apply",
                expected_session_fingerprint=created.fingerprint,
                product_run_id="run-lab",
                branch_id="branch-lab",
                event_id="event-lab",
                expected_saved_revision_id=preview.target_saved_revision_id,
                expected_working_draft_version=preview.target_working_draft_version,
                expected_preview_fingerprint=preview.fingerprint,
                expected_candidate_fingerprint=preview.candidate_fingerprint,
            ),
        )
        saved = RunWorkingDraftService(
            repository=repository,
            id_factory=iter(("revision-fork-source", "audit-fork-source")).__next__,
        ).save(
            run_id="run-lab",
            branch_id="branch-lab",
            expected_draft_version=1,
        )

        forked = RunBranchCreationService(
            repository=repository,
            id_factory=iter(("branch-lab-copy", "draft-lab-copy")).__next__,
        ).create_from_saved_revision(
            run_id="run-lab",
            source_branch_id="branch-lab",
            source_saved_revision_id=saved.saved_revision.revision_id,
        )
        assert forked.branch_id == "branch-lab-copy"

        fork_state = repository.get_branch_revision_state(branch_id="branch-lab-copy")
        loaded = load_saved_run_tournament_lab_drafts(
            fork_state.saved_revision.payload,
            run_id="run-lab",
            branch_id="branch-lab-copy",
        )
        assert loaded is not None
        assert loaded.drafts[0].event_id == "event-lab"
        assert loaded.drafts[0].candidate_fingerprint == applied.candidate_fingerprint
        assert loaded.drafts[0].branch_id == "branch-lab-copy"
        assert loaded.drafts[0].fingerprint != applied.proposal_fingerprint
    finally:
        engine.dispose()
