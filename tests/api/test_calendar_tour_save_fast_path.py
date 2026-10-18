"""Fast production HTTP/SQLite proof of atomic configured Tour Save validation.

Unlike the full two-Edition acceptance this test keeps a tiny 8-player opening
world so every code change gets feedback without 25-minute historical replay.
"""

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_tour_flow import (
    command,
    execute,
    inspect,
    save_tour,
    setup,
    tour_url,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def test_native_tour_save_validates_once_before_commit_and_rolls_back_on_error(
    tmp_path, monkeypatch,
):
    from beta_engine.infrastructure.db import repositories as storage

    database_url = f"sqlite:///{tmp_path / 'tour-atomic-save.db'}"
    with ApiServer(database_url=database_url) as server:
        repo, last_saved = setup(
            server, RunCalendar(52, 35, 2030, 3), initialize=False
        )
        initial_view = inspect(server)
        execute(server, command(initial_view, "initialize", name="quick-initialize"))
        dirty = inspect(server)
        assert not dirty["saved"]
        assert dirty["saved_head_revision_id"] == last_saved["revision_id"]

        # Deliberately break the ONE final snapshot verification, without
        # touching signed history, to prove validation still occurs before
        # the database transaction commits its new head and audit event.
        def reject_final_source(*_args, **_kwargs):
            raise ValueError("controlled Saved sporting validation failure")

        with monkeypatch.context() as patch:
            patch.setattr(storage, "load_saved_calendar_sources", reject_final_source)
            status, response = _request(
                "POST",
                tour_url(server) + "/save",
                {
                    "expected_draft_version": dirty["draft_version"],
                    "expected_calendar_tour_fingerprint": dirty["tour_fingerprint"],
                },
            )
        assert status == 409, response
        assert repo.get_branch_revision_state(branch_id="branch").saved_head_revision_id == dirty["saved_head_revision_id"]
        after_rollback = inspect(server)
        assert after_rollback["tour_fingerprint"] == dirty["tour_fingerprint"]
        assert not after_rollback["saved"]

        # Successful Save performs exactly one complete fold of the final
        # snapshot. A separate public history read still authenticates every
        # immutable sporting component independently after commit.
        called = []
        original = storage.load_saved_calendar_sources

        def count_final_source(*args, **kwargs):
            called.append(True)
            return original(*args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(storage, "load_saved_calendar_sources", count_final_source)
            receipt = save_tour(server)
        assert len(called) == 1
        stored = repo.get_branch_saved_revision(revision_id=receipt["revision_id"])
        assert stored is not None
        assert stored.content_hash == receipt["content_hash"]
        assert stored.payload["content"]["calendar_tour_authority"]["fingerprint"] == dirty["tour_fingerprint"]
