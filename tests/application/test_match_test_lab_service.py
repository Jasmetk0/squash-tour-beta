from __future__ import annotations

import pytest

from beta_engine.application.match_test_lab_service import (
    MatchLabRequest,
    MatchLabScenario,
    MatchLabSessionCreateRequest,
    MatchLabSessionRunRequest,
    MatchLabSessionUpdateRequest,
    MatchTestLabService,
)
from beta_engine.domain.matches import MatchContext, MatchParticipantContext
from beta_engine.domain.players import HiddenCareerTraits, Player
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
