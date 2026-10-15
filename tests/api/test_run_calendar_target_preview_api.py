"""Real HTTP / SQLite v82 Run calendar planning, not a simulated sporting claim."""

from __future__ import annotations

import json
from urllib.parse import urlencode

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_revisions import saved_revision_content_hash
from beta_engine.infrastructure.db import (
    DatabaseSettings, create_session_factory, create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel, RunContainerModel
from tests.api.test_run_working_draft_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def _new_run(server: ApiServer, name: str) -> tuple[str, str, str]:
    code, run = _request(
        "POST", f"{server.base_url}/run-containers", {"display_name": name}
    )
    assert code == 201, run
    run_id = run["run_id"]
    branch_id = run["viewer_branch_id"]
    code, listing = _request(
        "GET", f"{server.base_url}/run-branches?{urlencode({'run_id': run_id})}"
    )
    assert code == 200, listing
    return run_id, branch_id, listing["run_branches"][0]["saved_head_revision_id"]


def _url(server, run_id, branch_id, **query):
    return (
        f"{server.base_url}/run-containers/{run_id}/branches/"
        f"{branch_id}/calendar/target-preview?{urlencode(query)}"
    )


def _signed_disposable_calendar(
    database_url: str, *, run_id: str, revision_id: str,
    calendar: RunCalendar | None,
):
    """Explicit TEST-ONLY signed fixture; production never rewrites old saves."""

    engine = create_sqlite_engine(DatabaseSettings(url=database_url))
    factory = create_session_factory(engine)
    with factory.begin() as session:
        run = session.get(RunContainerModel, run_id)
        revision = session.get(BranchSavedRevisionModel, revision_id)
        metadata = json.loads(run.metadata_json)
        payload = json.loads(revision.payload_json)
        if calendar is None:
            metadata.pop("run_calendar", None)
            payload["run"].pop("run_calendar", None)
        else:
            metadata["run_calendar"] = calendar.to_metadata()
            payload["run"]["run_calendar"] = calendar.to_metadata()
            run.timeline_start_season = calendar.start_year
            run.timeline_end_season = calendar.start_year + calendar.season_count - 1
            payload["run"]["timeline_start_season"] = run.timeline_start_season
            payload["run"]["timeline_end_season"] = run.timeline_end_season
        run.metadata_json = json.dumps(metadata)
        revision.payload_json = json.dumps(payload)
        revision.content_hash = saved_revision_content_hash(
            revision_id=revision.revision_id, run_id=revision.run_id,
            branch_id=revision.branch_id, sequence=revision.sequence,
            parent_revision_id=revision.parent_revision_id, kind=revision.kind,
            payload_schema_version=revision.payload_schema_version,
            payload=payload, change_summary=json.loads(revision.change_summary_json),
        )
    engine.dispose()


def test_fax_http_preview_maps_year_rollover_and_next_season_without_writes(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'fax-targets.db'}"
    with ApiServer(database_url=database_url) as server:
        run_id, branch_id, revision_id = _new_run(server, "Target FAX")
        saved_url = (
            f"{server.base_url}/run-containers/{run_id}/branches/"
            f"{branch_id}/saved-revisions/{revision_id}"
        )
        code, before = _request("GET", saved_url)
        assert code == 200, before

        code, at_year_boundary = _request("GET", _url(
            server, run_id, branch_id,
            season_index=0, week=25, advance_weeks=1,
        ))
        assert code == 200, at_year_boundary
        assert at_year_boundary["schema_version"] == "run_calendar_target_preview.v1"
        assert at_year_boundary["planning_only"] is True
        assert at_year_boundary["current_sporting_position_claimed"] is False
        assert at_year_boundary["full_simulation_preview_supported"] is True
        assert at_year_boundary["source"] == "selected_branch_saved_run_calendar"
        assert at_year_boundary["run_calendar"]["weeks_per_year"] == 61
        assert at_year_boundary["start"]["year_week"] == 61
        assert at_year_boundary["start"]["calendar_year"] == 2000
        assert at_year_boundary["target"]["year_week"] == 1
        assert at_year_boundary["target"]["calendar_year"] == 2001
        assert at_year_boundary["target"]["season_index"] == 0
        assert at_year_boundary["target"]["season_week"] == 26
        assert at_year_boundary["remaining_weeks_including_current"] == 3050 - 24
        assert at_year_boundary["last_run_week"]["season_index"] == 49
        assert at_year_boundary["last_run_week"]["year_week"] == 36
        assert at_year_boundary["last_run_week"]["calendar_year"] == 2050

        code, next_season = _request("GET", _url(
            server, run_id, branch_id,
            season_index=0, week=61, advance_weeks=1,
        ))
        assert code == 200, next_season
        assert next_season["target"]["season_index"] == 1
        assert next_season["target"]["season_week"] == 1
        assert next_season["target"]["season_label"] == "2001/2002"
        assert next_season["target"]["year_week"] == 37
        assert next_season["target"]["week_ordinal"] == 61

        code, last_week = _request("GET", _url(
            server, run_id, branch_id, season_index=49, week=61, advance_weeks=0
        ))
        assert code == 200, last_week
        assert last_week["remaining_weeks_including_current"] == 1
        assert last_week["target"] == last_week["last_run_week"]
        for args in (
            dict(season_index=49, week=61, advance_weeks=1),
            dict(season_index=50, week=1),
            dict(season_index=0, week=62),
        ):
            status, rejected = _request("GET", _url(server, run_id, branch_id, **args))
            assert status == 409, rejected
            assert rejected["detail"]["code"] == "run_calendar_target_preview_conflict"
        for args in (dict(season_index=0, week=0), dict(season_index=0, week=1, advance_weeks=-1)):
            assert _request("GET", _url(server, run_id, branch_id, **args))[0] == 422
        assert _request("GET", _url(server, run_id, "foreign-branch", season_index=0, week=1))[0] == 409
        assert _request("GET", saved_url) == (200, before)

    # Recreated HTTP runtime loads the same original Saved calendar, not a
    # cached request response or a mutable in-memory clock.
    with ApiServer(database_url=database_url) as server:
        code, after = _request("GET", _url(
            server, run_id, branch_id, season_index=0, week=61, advance_weeks=1
        ))
        assert code == 200, after
        assert after == next_season


@pytest.mark.parametrize(
    ("calendar", "week", "delta", "expected"),
    [
        (RunCalendar.earth_default(start_year=2030, season_count=3), 52, 1,
         (2031, 1, "2031")),
        (RunCalendar(52, 35, 2030, 3), 18, 1,
         (2031, 1, "2030/2031")),
        (RunCalendar(52, 35, 2030, 3), 52, 1,
         (2031, 35, "2031/2032")),
    ],
)
def test_http_read_only_future_w52_calendar_is_valid_math_but_not_executable(
    tmp_path, calendar, week, delta, expected,
):
    database_url = f"sqlite:///{tmp_path / 'w52-targets.db'}"
    with ApiServer(database_url=database_url) as server:
        run_id, branch_id, revision_id = _new_run(server, "Target W52")
        _signed_disposable_calendar(
            database_url, run_id=run_id, revision_id=revision_id, calendar=calendar
        )
        code, answer = _request("GET", _url(
            server, run_id, branch_id, season_index=0, week=week, advance_weeks=delta
        ))
        assert code == 200, answer
        assert answer["run_calendar"]["weeks_per_year"] == 52
        assert answer["run_calendar"]["start_year"] == 2030
        assert answer["full_simulation_preview_supported"] is False
        assert answer["planning_only"] is True
        target = answer["target"]
        assert (target["calendar_year"], target["year_week"], target["season_label"]) == expected
        assert answer["last_run_week"]["season_index"] == 2
        assert answer["last_run_week"]["week_ordinal"] == 155


def test_legacy_absent_calendar_and_tampered_current_metadata_fail_closed(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'legacy-targets.db'}"
    with ApiServer(database_url=database_url) as server:
        run_id, branch_id, revision_id = _new_run(server, "Legacy planning")
        _signed_disposable_calendar(
            database_url, run_id=run_id, revision_id=revision_id, calendar=None
        )
        url = _url(server, run_id, branch_id, season_index=0, week=61)
        code, legacy = _request("GET", url)
        assert code == 200, legacy
        assert legacy["run_calendar"]["schema_version"] == "legacy_fax_calendar.v0"
        assert legacy["target"]["year_week"] == 36

        engine = create_sqlite_engine(DatabaseSettings(url=database_url))
        factory = create_session_factory(engine)
        for bad in (
            '{"run_calendar":null}',
            '{"run_calendar":{"schema_version":"unknown"}}',
            'not JSON',
        ):
            with factory.begin() as session:
                session.get(RunContainerModel, run_id).metadata_json = bad
            code, rejected = _request("GET", url)
            assert code == 409, rejected
            assert rejected["detail"]["code"] == "run_calendar_target_preview_conflict"
        engine.dispose()
