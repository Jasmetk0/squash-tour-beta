from __future__ import annotations

import pytest

from beta_engine.application.match_test_lab_service import (
    MatchLabRequest,
    MatchLabSavedRevisionPlayerImportRequest,
    MatchLabScenario,
    MatchLabSessionCreateRequest,
    MatchLabSessionRunRequest,
    MatchLabSessionUpdateRequest,
    MatchTestLabService,
)
from beta_engine.domain.matches import MatchContext, MatchParticipantContext
from beta_engine.application.initial_world import InitialWorldState
from beta_engine.application.season_player_bootstrap_service import SeasonActivePlayer
from beta_engine.domain.players import HiddenCareerTraits, Player
from beta_engine.domain.players.attribute_catalog import CANONICAL_PLAYER_ATTRIBUTES
from beta_engine.domain.players.initial_pool import GeneratedPlayerAttributes
from beta_engine.domain.players.sporting import PlayerSportingRecord, PlayerSportingWeekState
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.initial_world_state import capture_saved_initial_world, put_initial_world
from beta_engine.infrastructure.db.player_sporting_state import capture_saved_sporting, put_sporting
from beta_engine.infrastructure.db.repositories import BranchSavedRevisionHistoryRecord, BranchSavedRevisionRecord
from beta_engine.infrastructure.db import DatabaseSettings, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.models import Base, MatchLabSessionModel


pytestmark = pytest.mark.pr_critical


def _player(player_id: str, base: int) -> Player:
    return Player(
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


def _request(*, seeds: tuple[int, ...] = ()) -> MatchLabRequest:
    context = MatchContext(
        match_id="lab-match-1",
        player_a=MatchParticipantContext(player=_player("LAB-A", 86)),
        player_b=MatchParticipantContext(player=_player("LAB-B", 81)),
    )
    return MatchLabRequest(
        scenario=MatchLabScenario(
            scenario_id="portable-v1",
            context=context,
            seed=777,
        ),
        batch_seeds=seeds,
    )


def test_match_lab_exact_replay_is_deterministic_and_isolated() -> None:
    service = MatchTestLabService()
    request = _request()

    first = service.run(request)
    second = service.run(request)

    assert first == second
    assert first.compatibility.production_kernel.endswith("MatchEngine.simulate")
    assert first.compatibility.match_engine_version == "match_engine_v10"
    assert first.compatibility.portable is True
    assert first.compatibility.isolated is True
    assert first.compatibility.run_mutation_performed is False
    assert first.compatibility.run_live_link is False
    assert first.compatibility.normal_format is True
    assert first.compatibility.warnings == ()
    assert first.diagnostics.seed_count == 1
    assert len(first.results) == 1
    assert first.results[0].seed == 777
    assert first.results[0].rally_count > 0
    assert first.results[0].elapsed_seconds > 0


def test_match_lab_multi_seed_batch_uses_same_scenario_without_persistence() -> None:
    result = MatchTestLabService().run(_request(seeds=(100, 101, 102, 103, 104)))

    assert [row.seed for row in result.results] == [100, 101, 102, 103, 104]
    assert result.diagnostics.seed_count == 5
    assert sum(result.diagnostics.wins_by_player.values()) == 5
    assert result.diagnostics.distinct_result_count >= 1
    assert result.diagnostics.average_rally_count > 0
    assert result.diagnostics.average_elapsed_seconds > 0
    assert set(result.diagnostics.wins_by_player) <= {"LAB-A", "LAB-B"}


def test_match_lab_reports_nonstandard_format_compatibility_without_rejecting_kernel() -> None:
    request = _request()
    changed = request.model_copy(
        update={
            "scenario": request.scenario.model_copy(
                update={
                    "context": request.scenario.context.model_copy(
                        update={"best_of": 3}
                    )
                }
            )
        }
    )

    result = MatchTestLabService().run(changed)

    assert result.compatibility.normal_format is False
    assert any("non-standard match format" in warning for warning in result.compatibility.warnings)


def test_match_lab_run_snapshot_copy_requires_fingerprint_for_equivalence_claim() -> None:
    request = _request()
    changed = request.model_copy(
        update={
            "scenario": request.scenario.model_copy(
                update={
                    "source_kind": "run_snapshot_copy",
                    "source_reference": "run-a/branch-b/revision-c",
                }
            )
        }
    )

    result = MatchTestLabService().run(changed)

    assert result.compatibility.isolated is True
    assert result.compatibility.run_live_link is False
    assert any("source_fingerprint" in warning for warning in result.compatibility.warnings)


def test_match_lab_rejects_duplicate_or_oversized_batch_seed_lists() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        _request(seeds=(1, 1))

    with pytest.raises(ValueError, match="at most"):
        _request(seeds=tuple(range(101)))



def _persistent_service(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'match-lab-sessions.db'}"))
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    counter = {"value": 0}

    def id_factory(kind: str) -> str:
        counter["value"] += 1
        return f"{kind}-{counter['value']}"

    return engine, factory, MatchTestLabService(factory, id_factory)


def test_built_in_scenarios_are_read_only_and_deterministic() -> None:
    rows = MatchTestLabService().list_built_in_scenarios()

    assert [row.scenario_id for row in rows] == ["standard-even-match", "standard-strength-gap"]
    assert all(row.read_only is True for row in rows)
    assert all(row.scenario_fingerprint == row.scenario.fingerprint for row in rows)
    assert rows == MatchTestLabService().list_built_in_scenarios()


def test_new_test_session_clones_built_in_without_live_source_link(tmp_path) -> None:
    engine, factory, service = _persistent_service(tmp_path)
    try:
        built_in = service.list_built_in_scenarios()[0]
        created = service.create_session(
            MatchLabSessionCreateRequest(
                display_name="My isolated copy",
                built_in_scenario_id=built_in.scenario_id,
            )
        )

        assert created.session_id == "match-lab-session-1"
        assert created.version == 1
        assert created.scenario.source_kind == "built_in_copy"
        assert created.scenario.source_reference == built_in.scenario_id
        assert created.scenario.source_fingerprint == built_in.scenario_fingerprint
        assert created.scenario.fingerprint != built_in.scenario_fingerprint
        assert service.get_session(created.session_id) == created
        assert service.list_sessions() == (created,)

        edited_scenario = created.scenario.model_copy(
            update={
                "seed": created.scenario.seed + 1,
                "context": created.scenario.context.model_copy(update={"best_of": 3}),
            }
        )
        updated = service.update_session(
            created.session_id,
            MatchLabSessionUpdateRequest(
                expected_session_fingerprint=created.fingerprint,
                display_name="Edited isolated copy",
                scenario=edited_scenario,
            ),
        )
        assert updated.version == 2
        assert updated.display_name == "Edited isolated copy"
        assert updated.scenario.seed == built_in.scenario.seed + 1
        assert built_in.scenario.seed != updated.scenario.seed
        assert service.list_built_in_scenarios()[0] == built_in

        result = service.run_session(
            updated.session_id,
            MatchLabSessionRunRequest(
                expected_session_fingerprint=updated.fingerprint,
                batch_seeds=(11, 12),
            ),
        )
        assert result.diagnostics.seed_count == 2
        assert result.compatibility.run_mutation_performed is False
        assert result.compatibility.run_live_link is False

        with factory() as session:
            row = session.get(MatchLabSessionModel, created.session_id)
            assert row is not None
            assert row.version == 2
            assert row.fingerprint == updated.fingerprint
    finally:
        engine.dispose()


def test_session_update_and_run_reject_stale_fingerprint(tmp_path) -> None:
    engine, _, service = _persistent_service(tmp_path)
    try:
        scenario = _request().scenario
        created = service.create_session(
            MatchLabSessionCreateRequest(display_name="Portable session", scenario=scenario)
        )
        with pytest.raises(ValueError, match="changed since it was reviewed"):
            service.update_session(
                created.session_id,
                MatchLabSessionUpdateRequest(
                    expected_session_fingerprint="0" * 64,
                    scenario=scenario,
                ),
            )
        with pytest.raises(ValueError, match="changed since it was reviewed"):
            service.run_session(
                created.session_id,
                MatchLabSessionRunRequest(
                    expected_session_fingerprint="0" * 64,
                ),
            )
    finally:
        engine.dispose()


def test_session_persistence_detects_tampered_row(tmp_path) -> None:
    engine, factory, service = _persistent_service(tmp_path)
    try:
        created = service.create_session(
            MatchLabSessionCreateRequest(display_name="Tamper test", scenario=_request().scenario)
        )
        with factory.begin() as session:
            session.get(MatchLabSessionModel, created.session_id).fingerprint = "0" * 64
        with pytest.raises(ValueError, match="persistence fingerprint mismatch"):
            service.get_session(created.session_id)
    finally:
        engine.dispose()



def _historical_profile(player_id: str = "HIST-1") -> SeasonActivePlayer:
    return SeasonActivePlayer(
        player_id=player_id,
        name="Historical One",
        nationality="CZE",
        country_code="CZE",
        birth_year=1975,
        birth_year_week=1,
        age_years_at_season_start=25,
        age_weeks_at_season_start=25 * 61,
        current_ability=70,
        potential_ability=80,
        potential_tier="A",
        career_stage="prime",
        season="2000/2001",
        active_status="active",
        play_style="attacking",
        archetype="Power Attacker",
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=99,
            growth_curve="Standard",
            professionalism=0.5,
            ambition=0.5,
            travel_tolerance=0.5,
            schedule_aggression=0.5,
            injury_proneness=0.1,
            resilience=0.6,
        ),
        attributes=GeneratedPlayerAttributes(
            technique=70,
            movement=70,
            physical=70,
            mental=70,
            consistency=70,
            clutch=70,
            recovery=70,
        ),
        source_pool_player_id=player_id,
        source_generation_fingerprint=f"profile:{player_id}",
        source_generation="initial_pool",
        manual_override=False,
        locked_from_initial_pool=True,
        bootstrap_fingerprint="bootstrap",
        bootstrap_seed=1,
        bootstrap_id="bootstrap",
    )


def _historical_payload(factory) -> dict:
    profile = _historical_profile()
    world = InitialWorldState(
        run_id="run-historical",
        branch_id="branch-historical",
        players=(profile,),
        source_kind="production_initial_pool.v1",
        source_season="2000/2001",
        source_fingerprint="source",
        bootstrap_seed=1,
        bootstrap_fingerprint="bootstrap",
        adopted_by_command_id="adopt",
        audit_label="test",
        audit_reason="test",
        adoption_request_fingerprint="1" * 64,
    )
    sporting = PlayerSportingWeekState(
        run_id="run-historical",
        branch_id="branch-historical",
        week=RankingWeek(season_index=0, week=1),
        players=(
            PlayerSportingRecord(
                player_id=profile.player_id,
                attributes=tuple((name, 150) for name in CANONICAL_PLAYER_ATTRIBUTES),
                potential_ovr=180,
                potential_identity="potential:HIST-1",
                potential_provenance="test",
                development_timing="Standard",
                current_form=120,
                long_term_form_norm=100,
                match_sharpness=70,
                long_term_fatigue=15,
            ),
        ),
        completed_context_fingerprint="bootstrap:not-a-completed-week",
        source_initial_world_fingerprint=world.fingerprint,
        stage_provenance="test",
    )
    with factory.begin() as session:
        put_initial_world(session, world)
        put_sporting(session, sporting)
        payload = {"content": {}}
        capture_saved_initial_world(
            session, payload, run_id="run-historical", branch_id="branch-historical"
        )
        capture_saved_sporting(
            session, payload, run_id="run-historical", branch_id="branch-historical"
        )
    return payload


class _HistoricalRepository:
    def __init__(self, payload: dict):
        revision = BranchSavedRevisionRecord(
            revision_id="revision-historical",
            run_id="run-historical",
            branch_id="branch-historical",
            sequence=1,
            parent_revision_id=None,
            kind="test",
            payload_schema_version="test.v1",
            content_hash_algorithm="sha256",
            content_hash="a" * 64,
            payload=payload,
            change_summary={},
        )
        self.history = BranchSavedRevisionHistoryRecord(
            run_id="run-historical",
            branch_id="branch-historical",
            saved_head_revision_id=revision.revision_id,
            saved_revisions=(revision,),
        )

    def get_branch_saved_revision_history(self, *, run_id: str, branch_id: str):
        if (run_id, branch_id) != (self.history.run_id, self.history.branch_id):
            raise KeyError("history missing")
        return self.history


def test_saved_revision_player_import_copies_validated_historical_state_without_live_link(tmp_path) -> None:
    engine, factory, base_service = _persistent_service(tmp_path)
    try:
        payload = _historical_payload(factory)
        service = MatchTestLabService(
            factory,
            base_service._id_factory,
            repository=_HistoricalRepository(payload),
        )
        created = service.create_session(
            MatchLabSessionCreateRequest(
                display_name="Historical import",
                built_in_scenario_id="standard-even-match",
            )
        )
        imported = service.import_saved_revision_player(
            created.session_id,
            MatchLabSavedRevisionPlayerImportRequest(
                expected_session_fingerprint=created.fingerprint,
                product_run_id="run-historical",
                branch_id="branch-historical",
                saved_revision_id="revision-historical",
                player_id="HIST-1",
                side="player_a",
            ),
        )

        assert imported.version == 2
        assert imported.scenario.context.player_a.player.player_id == "HIST-1"
        assert imported.scenario.context.player_a.player.name == "Historical One"
        assert imported.scenario.context.player_a.player.nationality == "CZE"
        assert imported.scenario.context.player_a.form_modifier != 0
        assert imported.scenario.context.player_a.sharpness_modifier != 0
        assert imported.scenario.context.player_a.fatigue_modifier != 0
        assert len(imported.participant_imports) == 1
        evidence = imported.participant_imports[0]
        assert evidence.saved_revision_content_hash == "a" * 64
        assert evidence.player_id == "HIST-1"
        assert evidence.sporting_week_ordinal == 0
        assert evidence.canonical_projection_fingerprint
        assert imported.scenario.source_kind == "built_in_copy"

        result = service.run_session(
            imported.session_id,
            MatchLabSessionRunRequest(
                expected_session_fingerprint=imported.fingerprint,
                batch_seeds=(301, 302),
            ),
        )
        assert result.diagnostics.seed_count == 2
        assert result.compatibility.run_mutation_performed is False
        assert result.compatibility.run_live_link is False
    finally:
        engine.dispose()


def test_saved_revision_player_import_is_stale_safe_and_initial_world_only(tmp_path) -> None:
    engine, factory, base_service = _persistent_service(tmp_path)
    try:
        payload = _historical_payload(factory)
        service = MatchTestLabService(
            factory,
            base_service._id_factory,
            repository=_HistoricalRepository(payload),
        )
        created = service.create_session(
            MatchLabSessionCreateRequest(
                display_name="Historical import",
                built_in_scenario_id="standard-even-match",
            )
        )

        with pytest.raises(ValueError, match="changed since it was reviewed"):
            service.import_saved_revision_player(
                created.session_id,
                MatchLabSavedRevisionPlayerImportRequest(
                    expected_session_fingerprint="0" * 64,
                    product_run_id="run-historical",
                    branch_id="branch-historical",
                    saved_revision_id="revision-historical",
                    player_id="HIST-1",
                    side="player_a",
                ),
            )

        with pytest.raises(ValueError, match="not present in its Initial World"):
            service.import_saved_revision_player(
                created.session_id,
                MatchLabSavedRevisionPlayerImportRequest(
                    expected_session_fingerprint=created.fingerprint,
                    product_run_id="run-historical",
                    branch_id="branch-historical",
                    saved_revision_id="revision-historical",
                    player_id="PROSPECT-NOT-IN-INITIAL",
                    side="player_a",
                ),
            )
    finally:
        engine.dispose()
