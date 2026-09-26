from __future__ import annotations

import pytest

from beta_engine.application.authoritative_run_simulation_driver import AuthoritativeRunSimulationDriver
from beta_engine.domain.rankings.official import RankingWeek

from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request

from test_season_point_awards_service import make_points_service


@pytest.mark.pr_critical
def test_source_calendar_applies_to_run_and_projects_without_live_link(tmp_path):
    points, _ = make_points_service(tmp_path / "source")
    source_calendar_service = points.calendar_service
    source = source_calendar_service.get_calendar(season="2000/2001").calendar
    assert source is not None
    assert source.events

    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'calendar-package.db'}")
    server.app.state.season_calendar_registry_path = (
        source_calendar_service.calendar_registry_path
    )

    with server:
        run_id, branch_id, _ = _create_run(
            server,
            display_name="Run Calendar adapter",
        )
        base = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/packages"
        )
        source_root = base + "/source-calendar/2000-2001"

        status, preview = _request("POST", source_root + "/preview")
        assert status == 200, preview
        assert preview["document"]["package_type"] == "Calendar"
        assert preview["document"]["package_id"] == "calendar-2000-2001"
        assert preview["document"]["provenance"]["source_season"] == "2000/2001"

        status, applied = _request(
            "POST",
            source_root + "/confirm",
            {
                "command_id": "apply-season-calendar",
                "expected_head_revision_id": preview["saved_head_revision_id"],
                "expected_draft_version": preview["draft_version"],
                "expected_state_fingerprint": preview["current_state_fingerprint"],
                "expected_preview_fingerprint": preview["preview_fingerprint"],
                "conflict_resolutions": {},
            },
        )
        assert status == 200, applied

        projection_url = base + "/calendar/calendar-2000-2001"
        status, projection = _request("GET", projection_url)
        assert status == 200, projection
        assert projection["season"] == "2000/2001"
        assert projection["calendar"]["season"] == "2000/2001"
        assert len(projection["calendar"]["events"]) == len(source.events)
        assert {
            event["event_id"] for event in projection["calendar"]["events"]
        } == {event.event_id for event in source.events}
        assert len(projection["provenance"]) == len(source.events)
        frozen_fingerprint = projection["content_fingerprint"]

        driver = AuthoritativeRunSimulationDriver(
            server.app.state.runtime.repository._session_factory,
            points.result_service.match_service,
            points,
        )
        with server.app.state.runtime.repository._session_factory() as session:
            authoritative_calendar, mode, authority_fingerprint = (
                driver._calendar_authority(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    season="2000/2001",
                )
            )
        assert authoritative_calendar is not None
        assert mode == "run_package"
        assert authority_fingerprint == frozen_fingerprint
        assert {
            event.event_id for event in authoritative_calendar.events
        } == {event.event_id for event in source.events}

        registry = source_calendar_service._load_registry()
        changed = registry.calendars_by_season["2000/2001"]
        first = changed.events[0]
        changed.events[0] = first.model_copy(
            update={"event_name": first.event_name + " SOURCE-EDIT"}
        )
        source_calendar_service._save_registry(registry)

        status, unchanged = _request("GET", projection_url)
        assert status == 200, unchanged
        assert unchanged["content_fingerprint"] == frozen_fingerprint
        assert all(
            not event["event_name"].endswith("SOURCE-EDIT")
            for event in unchanged["calendar"]["events"]
        )

        with server.app.state.runtime.repository._session_factory() as session:
            authoritative_after_source_edit, mode, authority_fingerprint = (
                driver._calendar_authority(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    season="2000/2001",
                )
            )
        assert authoritative_after_source_edit is not None
        assert mode == "run_package"
        assert authority_fingerprint == frozen_fingerprint
        assert all(
            not event.event_name.endswith("SOURCE-EDIT")
            for event in authoritative_after_source_edit.events
        )

        # Once any Package state is applied, authoritative simulation must never
        # borrow a missing season Calendar from the mutable legacy registry.
        registry = source_calendar_service._load_registry()
        legacy_next = source.model_copy(deep=True)
        legacy_next.season = "2001/2002"
        legacy_next.events = [
            event.model_copy(update={"season": "2001/2002"})
            for event in legacy_next.events
        ]
        registry.calendars_by_season["2001/2002"] = legacy_next
        source_calendar_service._save_registry(registry)
        with server.app.state.runtime.repository._session_factory() as session:
            missing_calendar, mode, authority_fingerprint = driver._calendar_authority(
                session,
                run_id=run_id,
                branch_id=branch_id,
                season="2001/2002",
            )
        assert missing_calendar is None
        assert mode == "run_package_missing"
        assert authority_fingerprint is None

        # The same ownership fence applies to executable tournament discovery:
        # the source MatchPackage registry may contain this event, but without a
        # canonical Run-owned Draw it is not authoritative for a Package-backed Run.
        source_week = source.events[0].season_week
        with server.app.state.runtime.repository._session_factory() as session:
            discovered = driver._packages(
                RankingWeek(season_index=0, week=source_week),
                required=False,
                session=session,
                run_id=run_id,
                branch_id=branch_id,
            )
        assert discovered == ()

        status, changed_source_preview = _request(
            "POST", source_root + "/preview"
        )
        assert status == 200, changed_source_preview
        assert (
            changed_source_preview["document"]["provenance"][
                "source_calendar_fingerprint"
            ]
            != preview["document"]["provenance"]["source_calendar_fingerprint"]
        )
        status, rejected_update = _request(
            "POST",
            source_root + "/confirm",
            {
                "command_id": "reject-same-version-source-change",
                "expected_head_revision_id": changed_source_preview[
                    "saved_head_revision_id"
                ],
                "expected_draft_version": changed_source_preview["draft_version"],
                "expected_state_fingerprint": changed_source_preview[
                    "current_state_fingerprint"
                ],
                "expected_preview_fingerprint": changed_source_preview[
                    "preview_fingerprint"
                ],
                "conflict_resolutions": {},
            },
        )
        assert status == 409, rejected_update
