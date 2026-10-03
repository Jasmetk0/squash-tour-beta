"""Reviewed Admin Health edit application contract."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import select

from beta_engine.application.admin_health_edit import (
    AdminHealthEditRequest,
    AdminHealthEditService,
)
from beta_engine.application.run_container_creation_service import (
    RunContainerCreationService,
)
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.domain.players.health import (
    PlayerHealthRecord,
    bootstrap_health_state,
    carry_health_state_forward,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    PlayerHealthAdminEditReceiptModel,
)
from beta_engine.infrastructure.db.player_health_state import (
    PLAYER_HEALTH_COMPONENT_KEY,
    get_health,
    health_component,
    put_health,
)

pytestmark = pytest.mark.pr_critical


def _ids(*values: str):
    stream: Iterator[str] = iter(values)
    return lambda _kind: next(stream)


def _repository(tmp_path, name="admin-health-edit.db"):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / name}")
    )
    repository = SimulationPersistenceRepository(
        engine=engine,
        session_factory=create_session_factory(engine),
    )
    repository.bootstrap_schema()
    RunContainerCreationService(
        repository,
        _ids("run", "branch", "revision-0", "draft-0"),
    ).create_empty_run(display_name=f"Health {name}")
    with repository._session_factory.begin() as session:
        put_health(
            session,
            bootstrap_health_state(
                run_id="run",
                branch_id="branch",
                source_initial_world_fingerprint="world",
                player_ids=("p1",),
            ),
        )
    return repository, engine


def _prestart_request(*, draft_version=0, command_id="health-edit-1"):
    return AdminHealthEditRequest(
        command_id=command_id,
        player_id="p1",
        mode="pre_start_input",
        expected_draft_version=draft_version,
        records=(
            PlayerHealthRecord(
                record_id="old-knee",
                kind="Injury",
                condition_key="knee-history",
                lifecycle="Active",
                severity=28,
                affected_domains=("movement",),
                started_before_run=True,
                recovery_window_min_weeks=2,
                recovery_window_max_weeks=6,
                provenance="explicit Admin pre-start input",
            ),
        ),
        audit_label="Admin operator",
        audit_reason="Reviewed known pre-start knee history",
    )


def test_prestart_health_preview_is_read_only_commit_is_audited_and_retry_is_idempotent(
    tmp_path,
):
    repository, engine = _repository(tmp_path)
    try:
        service = AdminHealthEditService(repository)
        before = service.inspect(
            run_id="run", branch_id="branch", player_id="p1"
        )
        preview = service.preview(
            run_id="run",
            branch_id="branch",
            request=_prestart_request(),
        )
        after_preview = service.inspect(
            run_id="run", branch_id="branch", player_id="p1"
        )

        assert before == after_preview
        assert preview.before_state_fingerprint == before.state_fingerprint
        assert preview.after_state.players[0].records[0].started_before_run is True

        committed = service.commit(
            run_id="run",
            branch_id="branch",
            request=_prestart_request(),
            expected_preview_fingerprint=preview.preview_fingerprint,
        )
        assert committed.already_applied is False
        assert committed.draft_version == 1

        current = service.inspect(
            run_id="run", branch_id="branch", player_id="p1"
        )
        assert current.player.records[0].record_id == "old-knee"
        assert current.draft_version == 1
        draft = repository.get_viewer_branch_working_draft(
            run_id="run", branch_id="branch"
        )
        revision_state = repository.get_branch_revision_state(branch_id="branch")
        assert draft.status == "dirty"
        assert revision_state.working_draft.changes[-1]["kind"] == "player_health_state"
        assert (
            revision_state.working_draft.changes[-1]["fingerprint"]
            == committed.health_component_fingerprint
        )

        retried = service.commit(
            run_id="run",
            branch_id="branch",
            request=_prestart_request(),
            expected_preview_fingerprint=preview.preview_fingerprint,
        )
        assert retried.already_applied is True
        assert retried.state_fingerprint == committed.state_fingerprint

        corrected = _prestart_request(
            draft_version=1,
            command_id="health-edit-2",
        ).model_copy(
            update={
                "mode": "current_state_correction",
                "records": (
                    _prestart_request().records[0].model_copy(
                        update={"severity": 34}
                    ),
                ),
                "audit_reason": "Reviewed changed current knee severity",
            }
        )
        corrected_preview = service.preview(
            run_id="run",
            branch_id="branch",
            request=corrected,
        )
        service.commit(
            run_id="run",
            branch_id="branch",
            request=corrected,
            expected_preview_fingerprint=corrected_preview.preview_fingerprint,
        )
        with pytest.raises(ValueError, match="historical after restore or later correction"):
            service.commit(
                run_id="run",
                branch_id="branch",
                request=_prestart_request(),
                expected_preview_fingerprint=preview.preview_fingerprint,
            )

        with repository._session_factory() as session:
            receipt = session.get(
                PlayerHealthAdminEditReceiptModel,
                ("run", "branch", "health-edit-1"),
            )
            assert receipt is not None
            assert receipt.player_id == "p1"
            assert receipt.before_state_fingerprint == before.state_fingerprint
            assert receipt.after_state_fingerprint == committed.state_fingerprint
    finally:
        engine.dispose()


def test_health_commit_rejects_stale_preview_without_partial_write(tmp_path):
    repository, engine = _repository(tmp_path, "stale.db")
    try:
        service = AdminHealthEditService(repository)
        request = _prestart_request()
        preview = service.preview(
            run_id="run", branch_id="branch", request=request
        )
        before = service.inspect(
            run_id="run", branch_id="branch", player_id="p1"
        )
        with pytest.raises(ValueError, match="changed since reviewed preview"):
            service.commit(
                run_id="run",
                branch_id="branch",
                request=request,
                expected_preview_fingerprint="f" * 64,
            )
        assert (
            service.inspect(run_id="run", branch_id="branch", player_id="p1")
            == before
        )
        assert repository.get_viewer_branch_working_draft(
            run_id="run", branch_id="branch"
        ).draft_version == 0
        assert preview.preview_fingerprint != "f" * 64
    finally:
        engine.dispose()


def test_current_health_edit_is_current_week_only_and_rejects_future_facts(tmp_path):
    repository, engine = _repository(tmp_path, "current.db")
    try:
        with repository._session_factory.begin() as session:
            week1 = get_health(
                session,
                run_id="run",
                branch_id="branch",
                week=RankingWeek(season_index=0, week=1),
            )
            assert week1 is not None
            put_health(
                session,
                carry_health_state_forward(
                    week1,
                    target=RankingWeek(season_index=0, week=2),
                    target_player_ids=("p1",),
                ),
            )
            session.add(
                AuthoritativeWorldStateModel(
                    run_id="run",
                    branch_id="branch",
                    current_ordinal=1,
                    ranking_fingerprint="a" * 64,
                )
            )

        service = AdminHealthEditService(repository)
        with pytest.raises(ValueError, match="opening Week 1"):
            service.preview(
                run_id="run",
                branch_id="branch",
                request=_prestart_request(),
            )

        future = AdminHealthEditRequest(
            command_id="future",
            player_id="p1",
            mode="current_state_correction",
            expected_draft_version=0,
            records=(
                PlayerHealthRecord(
                    record_id="future-ankle",
                    kind="Injury",
                    condition_key="ankle",
                    lifecycle="Active",
                    severity=20,
                    affected_domains=("movement",),
                    onset_week=RankingWeek(season_index=0, week=3),
                    provenance="invalid future Admin fact",
                ),
            ),
            audit_label="Admin",
            audit_reason="Future fact must fail",
        )
        with pytest.raises(ValueError, match="cannot be in the future"):
            service.preview(
                run_id="run",
                branch_id="branch",
                request=future,
            )

        current = future.model_copy(
            update={
                "command_id": "current",
                "records": (
                    future.records[0].model_copy(
                        update={"onset_week": RankingWeek(season_index=0, week=2)}
                    ),
                ),
                "audit_reason": "Reviewed current ankle state",
            }
        )
        preview = service.preview(
            run_id="run",
            branch_id="branch",
            request=current,
        )
        result = service.commit(
            run_id="run",
            branch_id="branch",
            request=current,
            expected_preview_fingerprint=preview.preview_fingerprint,
        )
        assert result.week == RankingWeek(season_index=0, week=2)

        with repository._session_factory() as session:
            week2 = get_health(
                session,
                run_id="run",
                branch_id="branch",
                week=RankingWeek(season_index=0, week=2),
            )
            assert week2 is not None
            assert week2.predecessor_fingerprint == week1.fingerprint
    finally:
        engine.dispose()


def test_reviewed_health_edit_saves_as_recoverable_health_revision(tmp_path):
    repository, engine = _repository(tmp_path, "save.db")
    try:
        edit = AdminHealthEditService(repository)
        request = _prestart_request()
        preview = edit.preview(run_id="run", branch_id="branch", request=request)
        result = edit.commit(
            run_id="run",
            branch_id="branch",
            request=request,
            expected_preview_fingerprint=preview.preview_fingerprint,
        )

        draft = repository.get_viewer_branch_working_draft(
            run_id="run", branch_id="branch"
        )
        save = RunWorkingDraftService(
            repository,
            _ids("revision-health", "audit-health"),
        ).save_player_health(
            run_id="run",
            branch_id="branch",
            expected_draft_version=draft.draft_version,
            expected_player_health_fingerprint=result.health_component_fingerprint,
        )

        assert save.saved_revision.kind == "player_health_state"
        assert save.working_draft.status == "clean"
        saved_component = save.saved_revision.payload["content"][
            PLAYER_HEALTH_COMPONENT_KEY
        ]
        assert (
            saved_component["fingerprint"]
            == result.health_component_fingerprint
        )
        with repository._session_factory() as session:
            live = health_component(session, run_id="run", branch_id="branch")
            assert live == saved_component
    finally:
        engine.dispose()
