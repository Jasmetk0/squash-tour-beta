"""Independent born-player draft from actual historical Saved authority/epochs."""

import pytest

from beta_engine.application.native_fork_baseline_installation import (
    NativeForkBaselineInstallationService,
)
from beta_engine.application.native_fork_baseline_preparation import (
    NativeForkBaselinePreparationService,
)
from beta_engine.application.native_fork_sporting_service import (
    NativeForkSportingService,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.run_prospect_source_state import (
    load_saved_run_prospect_source,
)
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_tour_flow import (
    command,
    execute,
    inspect,
    save_tour,
    setup,
)
from tests.api.test_native_prospect_source_epochs_http import (
    _review_new_year,
    _source_url,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.support.native_fork_sporting import exercise_native_fork_sporting

pytestmark = pytest.mark.smoke


def test_born_fork_draft_uses_historical_sources_after_original_advances_and_restarts(
    tmp_path,
):
    path = tmp_path / "born-fork-draft.db"
    db = f"sqlite:///{path}"
    with ApiServer(database_url=db) as server:
        clock = RunCalendar(7, 1, 2030, 3)
        repo, _ = setup(server, clock, 4)
        sign_prospects(server, repo, clock)
        execute(server, command(inspect(server), "transition", name="fork-birthday"))
        born = save_tour(server)["revision_id"]
        born_source = repo.get_branch_saved_revision(revision_id=born)
        url, request, review = _review_new_year(server, season=1)
        code, result = _request(
            "POST",
            url + "/materialize",
            {
                "request": request,
                "expected_saved_head": review["saved_head_revision_id"],
                "expected_review_fingerprint": review["review_fingerprint"],
                "explicit_confirmation": True,
                "audit_label": "Admin",
                "audit_reason": "Later actual prospect epoch for historical fork test",
            },
        )
        assert code == 201, result
        code, review = _request("GET", _source_url(server) + "/preview")
        assert code == 200 and review["can_save"], review
        code, saved = _request(
            "POST",
            _source_url(server),
            {
                "expected_draft_version": review["draft_version"],
                "expected_run_prospect_source_fingerprint": review[
                    "run_prospect_source_fingerprint"
                ],
                "expected_saved_head_revision_id": review["saved_head_revision_id"],
            },
        )
        assert code == 201, saved
        epoch_head = saved["saved_revision"]["revision_id"]
        baseline = NativeForkBaselinePreparationService(repo).prepare(
            run_id="run",
            source_branch_id="branch",
            source_revision_id=born,
            target_branch_id="native-born-target",
        )
        NativeForkBaselineInstallationService(repo).install(
            baseline=baseline,
            revision_id="native-born-root",
            draft_id="native-born-draft",
            audit_event_id="native-born-audit",
            display_name="Native born target",
            expected_source_head=epoch_head,
            expected_viewer_branch_id="branch",
        )
        initial_ids = {
            p.player_id
            for p in repo.get_initial_world(run_id="run", branch_id="branch").players
        }
        sporting = exercise_native_fork_sporting(
            repo,
            path,
            branch_id="native-born-target",
            player_pair=("born-native-15", min(initial_ids)),
        )
        service = NativeForkSportingService(repo)
        with repo._session_factory() as session:
            _, checkpoint, _, prospects = service._context(
                session, run_id="run", branch_id="native-born-target"
            )
        historical = load_saved_run_prospect_source(
            born_source.payload, run_id="run"
        ).for_week(baseline.week.ordinal)
        assert prospects == historical
        assert checkpoint.steps[0].match.canonical_projections[0].age == 15
        assert (
            checkpoint.steps[0].match.canonical_projections[0].hidden_career_traits
            is None
        )
        # The original can perform its genuine Week Transition/Save independently
        # while the target keeps its own earlier week and unsaved played draft.
        execute(
            server, command(inspect(server), "transition", name="original-after-fork")
        )
        original_head = save_tour(server)["revision_id"]
        assert (
            service.inspect(run_id="run", branch_id="native-born-target")["checkpoint"]
            == checkpoint
        )
        assert repo.get_branch_saved_revision(revision_id=born) == born_source
    with ApiServer(database_url=db) as server:
        repo = server.app.state.runtime.repository
        view = NativeForkSportingService(repo).inspect(
            run_id="run", branch_id="native-born-target"
        )
        assert view["checkpoint"] == sporting["checkpoint"]
        assert view["draft_version"] == sporting["draft_version"]
        assert view["checkpoint"].week.week == 3
        assert inspect(server)["state"]["week"]["week"] == 4
        assert inspect(server)["saved_head_revision_id"] == original_head
        assert repo.get_branch_saved_revision(revision_id=born) == born_source
