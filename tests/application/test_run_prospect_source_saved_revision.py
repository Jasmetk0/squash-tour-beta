from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.run_saved_revision_restore_service import (
    RunSavedRevisionRestoreService,
)
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.infrastructure.db import SavedRevisionRestoreUnsupportedError
from beta_engine.infrastructure.db.models import RunProspectModel
from beta_engine.infrastructure.db.run_prospect_source_state import (
    RUN_PROSPECT_SOURCE_COMPONENT_KEY,
    load_saved_run_prospect_source,
)

from test_saved_revision_restore import _id_factory, _repository, _run_with_saved_viewer_change


def _insert_prospect(repository, *, display_name: str = "CZE Prospect 0001") -> None:
    with repository._session_factory.begin() as session:
        session.add(
            RunProspectModel(
                prospect_id="prospect-one",
                run_id="run-one",
                world_id="world-one",
                season_start_year=2000,
                season_label="2000/01",
                season_week=10,
                calendar_year=2000,
                year_week=10,
                birth_year=1985,
                birth_year_week=10,
                age=15,
                country_code="CZE",
                country_name="Czechia",
                status="prospect",
                source_type="weekly_15yo_cohort",
                cohort_policy_version="weekly_15yo_cohort_v1",
                profile_version="prospect_profile_v1",
                first_name=None,
                last_name=None,
                display_name=display_name,
                short_name=display_name,
                identity_seed="identity-seed",
                profile_seed="profile-seed",
                development_seed="development-seed",
                potential_seed="potential-seed",
                trait_seed="trait-seed",
                profile_json="{}",
                development_json="{}",
                potential_json="{}",
                trait_json="{}",
            )
        )


def _save_prospect_source(repository):
    preview = repository.preview_run_prospect_source_save(
        run_id="run-one",
        branch_id="branch-one",
    )
    assert preview["can_save"] is True
    assert preview["prospect_count"] == 1
    fingerprint = preview["run_prospect_source_fingerprint"]
    assert isinstance(fingerprint, str) and len(fingerprint) == 64

    saved = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory("revision-three", "audit-two"),
    ).save_run_prospect_source(
        run_id="run-one",
        branch_id="branch-one",
        expected_draft_version=preview["draft_version"],
        expected_run_prospect_source_fingerprint=fingerprint,
    )
    return saved, fingerprint


def _save_followup_viewer_revision(repository):
    service = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory("revision-four", "audit-three"),
    )
    staged = service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-one",
        viewer_branch_id="branch-one",
        expected_draft_version=3,
    )
    return service.save(
        run_id="run-one",
        branch_id="branch-one",
        expected_draft_version=staged.draft_version,
    )


def test_explicit_prospect_source_save_captures_shared_run_reference(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'prospect-source-save.db'}")
    _run_with_saved_viewer_change(repository)
    _insert_prospect(repository)

    saved, fingerprint = _save_prospect_source(repository)

    assert saved.saved_revision.kind == "run_prospect_source"
    snapshot = load_saved_run_prospect_source(
        saved.saved_revision.payload,
        run_id="run-one",
    )
    assert snapshot is not None
    assert snapshot.fingerprint == fingerprint
    assert [item["prospect_id"] for item in snapshot.records] == ["prospect-one"]

    next_preview = repository.preview_run_prospect_source_save(
        run_id="run-one",
        branch_id="branch-one",
    )
    assert next_preview["has_unsaved_changes"] is False
    assert next_preview["can_save"] is False


def test_restore_preserves_run_scoped_source_and_reuses_exact_snapshot(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'prospect-source-restore.db'}")
    _run_with_saved_viewer_change(repository)
    _insert_prospect(repository)
    saved, fingerprint = _save_prospect_source(repository)
    followup = _save_followup_viewer_revision(repository)

    assert (
        followup.saved_revision.payload["content"][RUN_PROSPECT_SOURCE_COMPONENT_KEY][
            "fingerprint"
        ]
        == fingerprint
    )

    preview = RunSavedRevisionRestoreService(
        repository=repository,
        id_factory=_id_factory("unused-a", "unused-b", "unused-c"),
    ).preview_current_branch_restore(
        run_id="run-one",
        branch_id="branch-one",
        target_saved_revision_id=saved.saved_revision.revision_id,
    )
    assert preview.can_restore is True

    restored = RunSavedRevisionRestoreService(
        repository=repository,
        id_factory=_id_factory("checkpoint-prospect", "revision-five", "audit-four"),
    ).restore_current_branch(
        run_id="run-one",
        branch_id="branch-one",
        target_saved_revision_id=saved.saved_revision.revision_id,
        expected_head_saved_revision_id=followup.saved_revision.revision_id,
        expected_draft_version=5,
        expected_current_viewer_branch_id="branch-one",
        explicit_confirmation=True,
    )

    restored_snapshot = load_saved_run_prospect_source(
        restored.saved_revision.payload,
        run_id="run-one",
    )
    assert restored_snapshot is not None
    assert restored_snapshot.fingerprint == fingerprint
    with repository._session_factory() as session:
        live = session.query(RunProspectModel).filter_by(run_id="run-one").all()
        assert [item.prospect_id for item in live] == ["prospect-one"]


def test_restore_fails_closed_if_shared_run_prospect_source_changed(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'prospect-source-mismatch.db'}")
    _run_with_saved_viewer_change(repository)
    _insert_prospect(repository)
    saved, _ = _save_prospect_source(repository)
    followup = _save_followup_viewer_revision(repository)

    with repository._session_factory.begin() as session:
        prospect = session.query(RunProspectModel).filter_by(
            run_id="run-one",
            prospect_id="prospect-one",
        ).one()
        prospect.display_name = "Changed after save"
        prospect.short_name = "Changed after save"

    preview = RunSavedRevisionRestoreService(
        repository=repository,
        id_factory=_id_factory("unused-a", "unused-b", "unused-c"),
    ).preview_current_branch_restore(
        run_id="run-one",
        branch_id="branch-one",
        target_saved_revision_id=saved.saved_revision.revision_id,
    )
    assert preview.can_restore is False
    assert "run_prospect_source_mismatch" in {
        blocker.code for blocker in preview.blockers
    }
    assert "target_run_prospect_source_mismatch" in {
        blocker.code for blocker in preview.blockers
    }

    with pytest.raises(
        SavedRevisionRestoreUnsupportedError,
        match="Run prospect source evidence",
    ):
        RunSavedRevisionRestoreService(
            repository=repository,
            id_factory=_id_factory(
                "checkpoint-mismatch",
                "revision-five",
                "audit-four",
            ),
        ).restore_current_branch(
            run_id="run-one",
            branch_id="branch-one",
            target_saved_revision_id=saved.saved_revision.revision_id,
            expected_head_saved_revision_id=followup.saved_revision.revision_id,
            expected_draft_version=5,
            expected_current_viewer_branch_id="branch-one",
            explicit_confirmation=True,
        )

    assert repository.get_branch_saved_revision(revision_id="revision-five") is None


def test_legacy_target_without_prospect_source_is_blocked_when_run_source_exists(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'prospect-source-legacy-target.db'}")
    _run_with_saved_viewer_change(repository)
    _insert_prospect(repository)
    saved, _ = _save_prospect_source(repository)

    preview = RunSavedRevisionRestoreService(
        repository=repository,
        id_factory=_id_factory("unused-a", "unused-b", "unused-c"),
    ).preview_current_branch_restore(
        run_id="run-one",
        branch_id="branch-one",
        target_saved_revision_id="revision-two",
    )

    assert saved.saved_revision.revision_id == "revision-three"
    assert preview.can_restore is False
    assert "target_run_prospect_source_mismatch" in {
        blocker.code for blocker in preview.blockers
    }
