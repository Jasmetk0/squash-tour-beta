"""Real SQLite preparation guards; no native fork creation is claimed here."""

import pytest

from beta_engine.application.native_fork_baseline_preparation import (
    NativeForkBaselinePreparationService,
)
from beta_engine.infrastructure.db.models import RunContainerModel
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _create_run

pytestmark = pytest.mark.pr_critical


def test_native_baseline_preparation_rejects_metadata_conflicts_without_writes(
    tmp_path,
):
    path = tmp_path / "baseline-guards.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run, branch, revision = _create_run(server, display_name="Baseline source")
        _other_run, other_branch, other_revision = _create_run(
            server, display_name="Foreign source"
        )
        repo = server.app.state.runtime.repository
        service = NativeForkBaselinePreparationService(repo)
        valid = {
            "run_id": run,
            "source_branch_id": branch,
            "source_revision_id": revision,
            "target_branch_id": "unused-target",
        }
        cases = (
            ({}, "no authenticated played source"),
            ({"run_id": "missing"}, "missing or foreign"),
            ({"source_branch_id": other_branch}, "missing or foreign"),
            ({"source_revision_id": other_revision}, "not reachable"),
            ({"target_branch_id": branch}, "already in use"),
            ({"target_branch_id": other_branch}, "already in use"),
        )
        for change, message in cases:
            before = _dump(path)
            with pytest.raises(ValueError, match=message):
                service.prepare(**(valid | change))
            assert _dump(path) == before
        with repo._session_factory.begin() as session:
            session.get(RunContainerModel, run).read_only = True
        before = _dump(path)
        with pytest.raises(ValueError, match="read-only Run"):
            service.prepare(**valid)
        assert _dump(path) == before
        assert repo.get_run_branch(branch_id="unused-target") is None
