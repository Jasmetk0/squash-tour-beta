"""Real custom-clock population -> reviewed adoption -> explicit Save -> fork/restart."""

import pytest

from beta_engine.application.run_package_service import RunPackageService
from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_player_generation_calendar_gate import (
    _dump,
    _generation,
    _world,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def root(server, branch="branch"):
    return server.base_url + f"/admin/players/runs/run/branches/{branch}/initial-world"


def request(server, **changes):
    code, draft = _request(
        "GET", server.base_url + "/run-containers/run/branches/branch/working-draft"
    )
    assert code == 200, draft
    return {
        "command_id": "calendar-population-1",
        "expected_saved_head": "r1",
        "expected_draft_version": draft["draft_version"],
        "expected_package_fingerprint": RunPackageService(
            server.app.state.runtime.repository
        )
        .get(run_id="run", branch_id="branch")
        .fingerprint,
        "generation": _generation(),
        "audit_label": "Admin",
        "audit_reason": "Reviewed initial population for this calendar",
        **changes,
    }


def review(server, payload):
    code, value = _request("POST", root(server) + "/calendar-adoption/preview", payload)
    assert code == 200, value
    return value


def confirm(server, payload, reviewed):
    return _request(
        "POST",
        root(server) + "/calendar-adoption",
        {
            "review": payload,
            "expected_initial_world_fingerprint": reviewed["initial_world_fingerprint"],
        },
    )


@pytest.mark.parametrize(
    "clock",
    [
        RunCalendar(52, 35, 2030, 3),
        RunCalendar(80, 80, 2100, 300),
        RunCalendar(1, 1, 0, 1),
    ],
)
def test_review_adopt_save_reopen_and_materialized_fork_preserve_actual_clock(
    tmp_path, clock
):
    path = tmp_path / "calendar-players.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, _ = _world(server, clock)
        payload = request(server)
        before = _dump(path)
        reviewed = review(server, payload)
        assert (
            reviewed["player_count_before"] == 0 and reviewed["player_count_after"] == 4
        )
        assert reviewed["pool_preview"]["run_calendar"] == clock.to_metadata()
        assert _dump(path) == before
        code, adopted = confirm(server, payload, reviewed)
        assert code == 201, adopted
        assert adopted["state"]["schema_version"] == "initial_world_state.v2"
        assert adopted["state"]["run_calendar"] == clock.to_metadata()
        assert adopted["fingerprint"] == reviewed["initial_world_fingerprint"]
        assert adopted["lifecycle_fingerprint"] == reviewed["lifecycle_fingerprint"]
        assert adopted["sporting_execution_supported"] is False
        from beta_engine.domain.rankings.official import RankingWeek
        from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle

        with (
            repo._session_factory() as session,
            pytest.raises(ValueError, match="Run-owned position"),
        ):
            get_lifecycle(
                session,
                run_id="run",
                branch_id="branch",
                week=RankingWeek(season_index=0, week=1),
            )
        after_adopt = _dump(path)
        assert confirm(server, payload, reviewed) == (code, adopted)
        assert _dump(path) == after_adopt
        code, save_preview = _request("GET", root(server) + "/save/preview")
        assert code == 200 and save_preview["can_save"], save_preview
        code, saved = _request(
            "POST",
            root(server) + "/save",
            {
                "expected_draft_version": save_preview["draft_version"],
                "expected_initial_world_fingerprint": adopted["fingerprint"],
            },
        )
        assert code == 201, saved
        revision = saved["saved_revision"]
        assert (
            revision["payload"]["content"]["player_lifecycle"]["states"][0][
                "initialization_stage"
            ]
            == "population_only"
        )
        assert "player_health_state" not in revision["payload"]["content"]
        assert "player_sporting" not in revision["payload"]["content"]
        assert all(
            "tour_entry_week" not in p
            for p in revision["payload"]["content"]["player_lifecycle"]["states"][0][
                "players"
            ]
        )
        assert repo.verify_branch_saved_revision_hash(revision_id="r0")
        assert repo.verify_branch_saved_revision_hash(revision_id="r1")
        assert repo.verify_branch_saved_revision_hash(
            revision_id=revision["revision_id"]
        )
        code, inventory = _request(
            "GET", server.base_url + "/admin/runs/run/branches/branch/saved-players"
        )
        assert code == 200 and inventory["total"] == 4, inventory
        code, fork = _request(
            "POST",
            server.base_url + "/run-containers/run/branches",
            {
                "source_branch_id": "branch",
                "source_saved_revision_id": revision["revision_id"],
            },
        )
        assert code == 201, fork
        code, copied = _request(
            "GET", root(server, fork["branch_id"]) + "/calendar-adoption"
        )
        assert code == 200, copied
        assert copied["state"]["players"] == adopted["state"]["players"]
        assert copied["state"]["branch_id"] == fork["branch_id"]
        assert repo.verify_branch_saved_revision_hash(
            revision_id=fork["saved_head_revision_id"]
        )
        # An exact committed retry still returns original bytes after Save.
        before_retry = _dump(path)
        assert confirm(server, payload, reviewed) == (201, adopted)
        assert _dump(path) == before_retry
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        assert _request("GET", root(server) + "/calendar-adoption") == (200, adopted)
        assert _request(
            "GET", root(server, fork["branch_id"]) + "/calendar-adoption"
        ) == (200, copied)


def test_mismatched_review_and_late_source_change_cannot_write(tmp_path):
    path = tmp_path / "stale.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _world(server, RunCalendar.earth_default())
        payload = request(server)
        reviewed = review(server, payload)
        before = _dump(path)
        for changes in (
            {"expected_saved_head": "r0"},
            {"command_id": "different"},
            {"generation": _generation(seed=803)},
            {"expected_draft_version": 0},
        ):
            code, error = confirm(server, {**payload, **changes}, reviewed)
            assert code == 409, error
            assert _dump(path) == before
        code, fork = _request(
            "POST",
            server.base_url + "/run-containers/run/branches",
            {"source_branch_id": "branch", "source_saved_revision_id": "r1"},
        )
        assert code == 201, fork
        code, changed = _request(
            "PUT",
            server.base_url
            + "/run-containers/run/branches/branch/working-draft/viewer-branch",
            {
                "viewer_branch_id": fork["branch_id"],
                "expected_draft_version": payload["expected_draft_version"],
            },
        )
        assert code == 200, changed
        code, saved = _request(
            "POST",
            server.base_url + "/run-containers/run/branches/branch/working-draft/save",
            {
                "expected_draft_version": changed["draft_version"],
            },
        )
        assert code == 201, saved
        after_save = _dump(path)
        code, error = confirm(server, payload, reviewed)
        assert code == 409, error
        assert _dump(path) == after_save


def test_adoption_retires_no_one_and_makes_no_tour_or_sporting_facts(tmp_path):
    path = tmp_path / "initial.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _world(server, RunCalendar.earth_default())
        payload = request(
            server,
            lifecycle_policy={
                "policy_id": "test-20",
                "automatic_retirement_age": 20,
                "provenance": "Explicit stored policy",
            },
            generation=_generation(min_age=20, max_age=20),
        )
        before = _dump(path)
        code, error = _request(
            "POST", root(server) + "/calendar-adoption/preview", payload
        )
        assert code == 409 and "retirement age" in str(error), error
        assert _dump(path) == before


def test_two_concurrent_confirmations_install_once_and_replay_without_generation(
    tmp_path, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import select

    from beta_engine.application.run_calendar_initial_pool_preview_service import (
        RunCalendarInitialPoolPreviewService,
    )
    from beta_engine.infrastructure.db.models import (
        InitialWorldStateModel,
        PlayerLifecycleWeekStateModel,
    )

    path = tmp_path / "concurrent.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, _ = _world(server, RunCalendar.earth_default())
        payload = request(server)
        reviewed = review(server, payload)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(lambda _: confirm(server, payload, reviewed), range(2))
            )
        assert results[0][0] == results[1][0] == 201, results
        assert results[0] == results[1]
        with repo._session_factory() as session:
            assert len(session.scalars(select(InitialWorldStateModel)).all()) == 1
            assert (
                len(session.scalars(select(PlayerLifecycleWeekStateModel)).all()) == 1
            )
        before = _dump(path)

        def refuse(*args, **kwargs):
            raise ValueError("New generation unavailable")

        monkeypatch.setattr(RunCalendarInitialPoolPreviewService, "preview", refuse)
        assert confirm(server, payload, reviewed) == results[0]
        assert _dump(path) == before


def test_lifecycle_write_failure_rolls_back_population_and_every_other_row(
    tmp_path, monkeypatch
):
    from beta_engine.infrastructure.db import player_lifecycle_state

    path = tmp_path / "rollback.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _world(server, RunCalendar.earth_default())
        payload = request(server)
        reviewed = review(server, payload)
        before = _dump(path)

        def refuse(*args, **kwargs):
            raise ValueError("Injected lifecycle write failure")

        monkeypatch.setattr(player_lifecycle_state, "put_lifecycle", refuse)
        code, error = confirm(server, payload, reviewed)
        assert code == 409 and "Injected lifecycle" in str(error), error
        assert _dump(path) == before


def test_save_restore_to_empty_then_back_keeps_v2_population_without_legacy_backfill(
    tmp_path,
):
    from beta_engine.application.run_saved_revision_restore_service import (
        RunSavedRevisionRestoreService,
    )
    from tests.application.test_run_package_review_acceptance import _ids

    path = tmp_path / "restore.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, _ = _world(server, RunCalendar.earth_default())
        payload = request(server)
        reviewed = review(server, payload)
        code, adopted = confirm(server, payload, reviewed)
        assert code == 201, adopted
        code, saved = _request(
            "POST",
            root(server) + "/save",
            {
                "expected_draft_version": payload["expected_draft_version"],
                "expected_initial_world_fingerprint": adopted["fingerprint"],
            },
        )
        assert code == 201, saved
        saved_id = saved["saved_revision"]["revision_id"]
        service = RunSavedRevisionRestoreService(
            repo, _ids("checkpoint-a", "restore-a", "audit-a")
        )
        emptied = service.restore_current_branch(
            run_id="run",
            branch_id="branch",
            target_saved_revision_id="r1",
            expected_head_saved_revision_id=saved_id,
            expected_draft_version=saved["working_draft"]["draft_version"],
            expected_current_viewer_branch_id="branch",
            explicit_confirmation=True,
        )
        assert _request("GET", root(server) + "/calendar-adoption")[0] == 404
        restored = RunSavedRevisionRestoreService(
            repo, _ids("checkpoint-b", "restore-b", "audit-b")
        ).restore_current_branch(
            run_id="run",
            branch_id="branch",
            target_saved_revision_id=saved_id,
            expected_head_saved_revision_id=emptied.saved_revision.revision_id,
            expected_draft_version=emptied.working_draft.draft_version,
            expected_current_viewer_branch_id="branch",
            explicit_confirmation=True,
        )
        assert _request("GET", root(server) + "/calendar-adoption") == (200, adopted)
        content = restored.saved_revision.payload["content"]
        assert content["initial_world"]["fingerprint"] == adopted["fingerprint"]
        assert "player_health_state" not in content and "player_sporting" not in content
        assert repo.verify_branch_saved_revision_hash(revision_id=saved_id)
        assert repo.verify_branch_saved_revision_hash(
            revision_id=restored.saved_revision.revision_id
        )


def test_actual_atp_earth_1000_players_adopt_save_and_reopen(tmp_path):
    path = tmp_path / "atp-1000.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _world(server, RunCalendar.earth_default(start_year=1955), world_id="atp_earth")
        payload = request(
            server,
            generation=_generation(world_package_id="atp_earth", target_pool_size=1000),
        )
        reviewed = review(server, payload)
        code, adopted = confirm(server, payload, reviewed)
        assert code == 201, adopted
        assert len(adopted["state"]["players"]) == 1000
        assert all(
            p["birth_year_week"] <= 52 and p["season"] == "1955"
            for p in adopted["state"]["players"]
        )
        code, saved = _request(
            "POST",
            root(server) + "/save",
            {
                "expected_draft_version": payload["expected_draft_version"],
                "expected_initial_world_fingerprint": adopted["fingerprint"],
            },
        )
        assert code == 201, saved
        assert server.app.state.runtime.repository.verify_branch_saved_revision_hash(
            revision_id=saved["saved_revision"]["revision_id"]
        )
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        assert _request("GET", root(server) + "/calendar-adoption") == (200, adopted)
        code, inventory = _request(
            "GET", server.base_url + "/admin/runs/run/branches/branch/saved-players"
        )
        assert code == 200 and inventory["total"] == 1000, inventory


def test_target_drift_after_generation_is_rechecked_under_writer_lock(
    tmp_path, monkeypatch
):
    from beta_engine.application.calendar_initial_world_adoption_service import (
        CalendarInitialWorldAdoptionService,
    )

    path = tmp_path / "late-drift.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _world(server, RunCalendar.earth_default())
        payload = request(server)
        reviewed = review(server, payload)
        code, fork = _request(
            "POST",
            server.base_url + "/run-containers/run/branches",
            {"source_branch_id": "branch", "source_saved_revision_id": "r1"},
        )
        assert code == 201, fork
        original = CalendarInitialWorldAdoptionService._candidate
        after_external_change = []

        def generate_then_change(self, **kwargs):
            candidate = original(self, **kwargs)
            code, changed = _request(
                "PUT",
                server.base_url
                + "/run-containers/run/branches/branch/working-draft/viewer-branch",
                {
                    "viewer_branch_id": fork["branch_id"],
                    "expected_draft_version": payload["expected_draft_version"],
                },
            )
            assert code == 200, changed
            after_external_change.append(_dump(path))
            return candidate

        monkeypatch.setattr(
            CalendarInitialWorldAdoptionService, "_candidate", generate_then_change
        )
        code, error = confirm(server, payload, reviewed)
        assert code == 409 and "stale" in str(error), error
        assert _dump(path) == after_external_change[0]
        assert _request("GET", root(server) + "/calendar-adoption")[0] == 404


def test_installed_v2_population_cannot_enter_legacy_sporting_writers(tmp_path):
    from beta_engine.application.initial_world import derive_initial_ranking_inputs
    from beta_engine.application.standalone_match_service import (
        StandaloneMatchService,
        StandaloneMatchSimulateCommand,
    )
    from beta_engine.infrastructure.db.initial_world_state import get_initial_world
    from beta_engine.infrastructure.db.player_health_state import bootstrap_health
    from beta_engine.infrastructure.db.player_sporting_state import (
        derive_bootstrap_sporting,
    )

    path = tmp_path / "v2-guard.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, _ = _world(server, RunCalendar.earth_default())
        payload = request(server)
        reviewed = review(server, payload)
        assert confirm(server, payload, reviewed)[0] == 201
        before = _dump(path)
        with repo._session_factory.begin() as session:
            world = get_initial_world(session, run_id="run", branch_id="branch")
            with pytest.raises(ValueError, match="Calendar InitialWorld"):
                derive_initial_ranking_inputs(world)
            with pytest.raises(ValueError, match="Calendar"):
                bootstrap_health(session, world)
            with pytest.raises(ValueError, match="Calendar"):
                derive_bootstrap_sporting(world)
        with pytest.raises(
            ValueError, match="Standalone match simulation cannot execute"
        ):
            StandaloneMatchService(repo._session_factory).simulate(
                run_id="run",
                branch_id="branch",
                command=StandaloneMatchSimulateCommand(
                    command_id="wrong-clock",
                    expected_workspace_fingerprint="a" * 64,
                    seed=1,
                    operator_label="Admin",
                    audit_reason="Calendar protection",
                ),
            )
        assert _dump(path) == before


def test_corrupt_live_lifecycle_fails_read_and_replay_without_repair(tmp_path):
    from beta_engine.infrastructure.db.models import PlayerLifecycleWeekStateModel

    path = tmp_path / "corrupt-life.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, _ = _world(server, RunCalendar.earth_default())
        payload = request(server)
        reviewed = review(server, payload)
        assert confirm(server, payload, reviewed)[0] == 201
        with repo._session_factory.begin() as session:
            session.get(
                PlayerLifecycleWeekStateModel, ("run", "branch", 0)
            ).fingerprint = "0" * 64
        before = _dump(path)
        code, error = _request("GET", root(server) + "/calendar-adoption")
        assert code == 409 and "fingerprint" in str(error), error
        assert confirm(server, payload, reviewed)[0] == 409
        assert _dump(path) == before
