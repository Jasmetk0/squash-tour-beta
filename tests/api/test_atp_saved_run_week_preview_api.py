"""Real HTTP and SQLite Run clock read for original ATP dated source weeks."""
from __future__ import annotations

from urllib.parse import quote

import pytest

from test_simulation_api import ApiServer, _request
from beta_engine.domain.run_packages import RunPackageState
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.application.atp_earth_run_calendar_preview import preview_atp_earth_weeks_on_run
from beta_engine.application.atp_saved_snapshot_week_preview import (
    audit_saved_atp_tour_bindings,
    build_saved_atp_reference_week_mapping,
)

pytestmark = pytest.mark.pr_critical


def _make_run(server, *, name: str, start: int = 2025, count: int = 2,
              offset: int = 1, weeks: int = 52):
    status, run = _request("POST", server.base_url + "/run-containers", {
        "display_name": name,
        "calendar": {
            "weeks_per_year": weeks,
            "season_start_year_week": offset,
            "start_year": start,
            "season_count": count,
        },
    })
    assert status == 201, run
    return run["run_id"], run["viewer_branch_id"]


def _url(server, run_id, branch_id, suffix=""):
    return (
        f"{server.base_url}/admin/runs/{quote(run_id, safe='')}"
        f"/branches/{quote(branch_id, safe='')}/packages/"
        "source-atp-reference-calendar/run-week-preview" + suffix
    )


def _saved_url(server, run_id, branch_id, suffix=""):
    return _url(server, run_id, branch_id, suffix).replace(
        "/source-atp-reference-calendar/",
        "/saved-source-atp-reference-calendar/",
    )


def test_saved_source_preview_requires_an_actual_saved_atp_package(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'atp-saved-required.db'}") as server:
        r, b = _make_run(server, name="Source not applied", start=2025, count=2)
        code, body = _request("GET", _saved_url(server, r, b, "?year=2025"))
        assert code == 409, body
        assert body["detail"]["code"] == "atp_saved_run_week_preview_conflict"
        # Original endpoint intentionally remains available as a SERVER source preview.
        assert _request("GET", _url(server, r, b, "?year=2025"))[0] == 200


def test_source_week_preview_on_real_saved_earth_clock_is_nondestructive(tmp_path):
    db = f"sqlite:///{tmp_path / 'atp-saved-week.db'}"
    with ApiServer(database_url=db) as server:
        run_id, branch_id = _make_run(
            server, name="ATP 2025–26 Earth W52", start=2025, count=2
        )
        base = server.base_url + f"/run-containers/{run_id}"
        working = base + f"/branches/{branch_id}/working-draft"
        before_run = _request("GET", base)
        before_draft = _request("GET", working)
        assert before_run[0] == 200
        assert before_draft[0] == 200
        code, preview = _request("GET", _url(
            server, run_id, branch_id, "?year=2025&year=2026"
        ))
        assert code == 200, preview
        assert preview["run_id"] == run_id
        assert preview["branch_id"] == branch_id
        assert preview["saved_run_calendar_verified"] is True
        assert preview["uses_current_server_reference_not_run_snapshot"] is True
        assert preview["run_mutated"] is False
        assert preview["working_draft_mutated"] is False
        assert preview["historical_revision_mutated"] is False
        assert preview["no_sporting_install"] is True
        assert preview["no_simulation_slot_or_match_generation"] is True
        assert preview["selected_atp_years"] == [2025, 2026]
        assert preview["calendar"]["weeks_per_year"] == 52
        assert preview["calendar"]["start_year"] == 2025
        chengdu = next(row for row in preview["events"]
                       if row["source_identity"] == "atp_2025_chengdu")
        assert chengdu["run_weeks"][0]["year_week"] == 38
        assert chengdu["source_finish_run_week"]["year_week"] == 39
        assert chengdu["source_finish_run_ordinal"] == chengdu["run_ordinals"][-1] + 1
        assert chengdu["source_finish_after_mapped_occupancy"] is True
        assert chengdu["source_finish_is_not_sporting_result_closure"] is True
        assert len(preview["events"]) > 80
        assert any(
            e["atp_season_year"] == 2026 and
            e["source_status"] == "provisional_published_schedule"
            for e in preview["events"]
        )
        assert all(
            0 <= v["season_index"] < 2
            for e in preview["events"] for v in e["run_weeks"]
        )
        assert _request("GET", base) == before_run
        assert _request("GET", working) == before_draft
        fingerprint = preview["preview_fingerprint"]
    with ApiServer(database_url=db) as server:
        code, reread = _request("GET", _url(
            server, run_id, branch_id, "?year=2026&year=2025"
        ))
        assert code == 200, reread
        assert reread == preview
        assert reread["preview_fingerprint"] == fingerprint
        assert _request("GET", server.base_url + f"/run-containers/{run_id}") == before_run
        assert _request(
            "GET", server.base_url + f"/run-containers/{run_id}/branches/{branch_id}/working-draft"
        ) == before_draft


def test_custom_season_offset_projects_to_native_position_and_is_still_readonly(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'atp-offset.db'}") as server:
        run_id, branch_id = _make_run(
            server, name="ATP custom Earth offset", start=2024, count=3, offset=37
        )
        code, preview = _request("GET", _url(
            server, run_id, branch_id, "?year=2025"
        ))
        assert code == 200, preview
        assert preview["calendar"]["season_start_year_week"] == 37
        item = next(
            e for e in preview["events"]
            if e["source_identity"] == "atp_2025_canadian_open"
        )
        assert [v["year_week"] for v in item["run_weeks"]] == [30, 31, 32]
        assert [v["season_week"] for v in item["run_weeks"]] == [46, 47, 48]
        assert all(v["season_index"] == 0 for v in item["run_weeks"])
        assert "three_week_interval_manual_sporting_review" in item["review_flags"]


def test_previewer_rejects_wrong_saved_clock_scope_and_invalid_selected_year(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'atp-bad.db'}") as server:
        r, b = _make_run(server, name="Earth 2025", start=2025, count=2)
        assert _request("GET", _url(server, r, b, "?year=2024"))[0] == 409
        assert _request("GET", _url(server, r, b, "?year=2025&year=2025"))[0] == 409
        assert _request("GET", _url(server, r, b, "?year=2027"))[0] == 422
        assert _request("GET", _url(server, r, "unknown-branch", "?year=2025"))[0] == 409
        # Default all-year request on a two-year Run must not silently omit data.
        assert _request("GET", _url(server, r, b))[0] == 409
        other_run, other_branch = _make_run(
            server, name="Default FAX W61", start=2000, count=50,
            offset=37, weeks=61
        )
        code, body = _request("GET", _url(
            server, other_run, other_branch, "?year=2025"
        ))
        assert code == 409, body
        assert "W=52" in body["detail"]["message"]


def test_api_never_treats_uninstalled_source_as_mutated_run_package(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'atp-ref-only.db'}") as server:
        r, b = _make_run(server, name="Empty Earth reference preview")
        packages = f"{server.base_url}/admin/runs/{r}/branches/{b}/packages"
        code, state = _request("GET", packages)
        assert code == 200, state
        assert state["state"] is None
        code, preview = _request("GET", _url(server, r, b, "?year=2025"))
        assert code == 200, preview
        assert preview["uses_current_server_reference_not_run_snapshot"] is True
        code, after = _request("GET", packages)
        assert code == 200
        assert after == state
        assert all("source_start_date" in item for item in preview["events"])


def test_reference_package_confirm_save_restart_then_weeks_remain_readonly(tmp_path):
    """Full real source Package CAS/Save must not accidentally gain sports authority."""
    db = f"sqlite:///{tmp_path / 'atp-w52-saved-package.db'}"
    with ApiServer(database_url=db) as server:
        run_id, branch_id = _make_run(
            server, name="ATP Saved Package in Earth W52", start=2025, count=2
        )
        packages = (
            f"{server.base_url}/admin/runs/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/packages"
        )
        code, source_preview = _request(
            "POST", packages + "/source-atp-reference-calendar/preview", {}
        )
        assert code == 200, source_preview
        assert not source_preview["invalid"]
        assert not source_preview["conflicts"]
        assert source_preview["document_identity"]["package_id"] == (
            "atp_tour_1990_2026_calendar_reference_setup"
        )
        confirm = {
            "command_id": "save-atp-reference-w52",
            "expected_head_revision_id": source_preview["saved_head_revision_id"],
            "expected_draft_version": source_preview["draft_version"],
            "expected_state_fingerprint": source_preview["current_state_fingerprint"],
            "expected_preview_fingerprint": source_preview["preview_fingerprint"],
            "conflict_resolutions": {},
        }
        code, applied = _request(
            "POST", packages + "/source-atp-reference-calendar/confirm", confirm
        )
        assert code == 200, applied
        assert applied["draft_version"] == 1
        assert all(
            e["entity_kind"] not in ("calendar.event.v1", "calendar.metadata.v1")
            for e in applied["state"]["entities"]
        )
        assert _request("GET", _saved_url(server, run_id, branch_id, "?year=2025"))[0] == 409
        code, saved = _request(
            "POST",
            f"{server.base_url}/run-containers/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/working-draft/save",
            {"expected_draft_version": applied["draft_version"]},
        )
        assert code == 201, saved
        before_packages = _request("GET", packages)
        assert before_packages[0] == 200
        assert len(before_packages[1]["state"]["entities"]) == 2619
        code, projected = _request(
            "GET", _url(server, run_id, branch_id, "?year=2025")
        )
        assert code == 200, projected
        code, saved_bound = _request(
            "GET", _saved_url(server, run_id, branch_id, "?year=2025")
        )
        assert code == 200, saved_bound
        assert saved_bound["saved_run_calendar_verified"] is True
        assert saved_bound["saved_package_source_verified"] is True
        assert saved_bound["uses_saved_run_package_snapshot"] is True
        assert saved_bound["uses_current_server_reference_not_run_snapshot"] is False
        assert saved_bound["source_mapping_fingerprint"] != projected["source_mapping_fingerprint"]
        assert saved_bound["summary"]["mapped_occurrences"] == projected["summary"]["mapped_occurrences"]
        assert saved_bound["events"] == projected["events"]
        audit_url = _saved_url(server, run_id, branch_id, "?year=2025&validate_tour_bindings=true")
        code, audited = _request("GET", audit_url)
        assert code == 200, audited
        bindings = audited["source_tour_bindings"]
        assert bindings["verified_occurrences"] == 2407
        assert len(bindings["occurrences_by_category"]) == 11
        assert bindings["occurrences_by_category"]["atp_250"] == 670
        assert len(bindings["selected_occurrences"]) == 57
        chengdu = bindings["selected_occurrences"]["atp_2025_chengdu"]
        assert chengdu["series_id"] == "chengdu"
        assert chengdu["category_id"] == "atp_250"
        assert chengdu["historical_category_label"] == "ATP Tour 250"
        assert audited["events"] == saved_bound["events"]
        boundary_url = _saved_url(
            server, run_id, branch_id,
            "?year=2024&year=2025&validate_tour_bindings=true&report_outside_horizon=true",
        )
        code, boundary = _request("GET", boundary_url)
        assert code == 200, boundary
        assert boundary["events"] == saved_bound["events"]
        assert boundary["outside_horizon"]
        assert all(row["atp_season_year"] == 2024 for row in boundary["outside_horizon"])
        assert set(boundary["source_tour_bindings"]["selected_occurrences"]) == {
            row["source_identity"] for group in ("events", "outside_horizon")
            for row in boundary[group]
        }
        assert all(e["source_finish_is_not_sporting_result_closure"] is True
                   for e in saved_bound["events"])
        assert saved_bound["no_sporting_install"] is True

        # Reconstructing the source from Saved bytes must reject local edits,
        # not silently accept data whose original baseline no longer matches.
        state = RunPackageState.model_validate(before_packages[1]["state"])
        mapping = build_saved_atp_reference_week_mapping(state)
        assert mapping["source_origin"] == "immutable_saved_run_package_state.v1"
        assert len(mapping["mappings"]) == 2407
        full = preview_atp_earth_weeks_on_run(
            calendar=RunCalendar.earth_default(start_year=1990, season_count=37),
            mapping=mapping, report_outside_horizon=True,
        )
        assert full["outside_horizon"] == []
        assert len(full["events"]) == 2407
        assert full["summary"]["distinct_run_weeks"] == 1284
        victim = next(e for e in state.entities if
                      e.source_entity_id == "atp_2025_chengdu")
        altered = victim.model_copy(update={"provenance": "manual"})
        bad = state.model_copy(update={"entities": tuple(
            altered if e is victim else e for e in state.entities
        )})
        with pytest.raises(ValueError, match="locally edited"):
            build_saved_atp_reference_week_mapping(bad)
        series = next(e for e in state.entities if e.entity_kind == "tennis.series.reference.v1")
        missing_series = state.model_copy(update={"entities": tuple(
            e for e in state.entities if e is not series
        )})
        with pytest.raises(ValueError, match="incomplete"):
            audit_saved_atp_tour_bindings(missing_series, selected_occurrences=frozenset())
        edited_series = series.model_copy(update={"provenance": "manual"})
        tampered_series = state.model_copy(update={"entities": tuple(
            edited_series if e is series else e for e in state.entities
        )})
        with pytest.raises(ValueError, match="locally edited"):
            audit_saved_atp_tour_bindings(tampered_series, selected_occurrences=frozenset())
        altered_occurrence = victim.model_copy(update={
            "payload": {**victim.payload, "category_id": "atp_500"},
            "references": tuple(
                ref.model_copy(update={"source_entity_id": "atp_500"})
                if ref.expected_entity_kind == "tennis.category.reference.v1" else ref
                for ref in victim.references
            ),
        })
        inconsistent = state.model_copy(update={"entities": tuple(
            altered_occurrence if e is victim else e for e in state.entities
        )})
        with pytest.raises(ValueError, match="does not match the Series year"):
            audit_saved_atp_tour_bindings(inconsistent, selected_occurrences=frozenset())
        assert projected["calendar"]["weeks_per_year"] == 52
        assert projected["no_sporting_install"] is True
        assert projected["run_mutated"] is False
        assert _request("GET", packages) == before_packages
    with ApiServer(database_url=db) as server:
        packages = (
            f"{server.base_url}/admin/runs/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/packages"
        )
        code, persisted = _request("GET", packages)
        assert code == 200
        assert persisted == before_packages[1]
        code, reread = _request(
            "GET", _url(server, run_id, branch_id, "?year=2025")
        )
        assert code == 200
        assert reread == projected
        code, saved_reread = _request(
            "GET", _saved_url(server, run_id, branch_id, "?year=2025")
        )
        assert code == 200, saved_reread
        assert saved_reread == saved_bound
        assert _request("GET", _saved_url(
            server, run_id, branch_id, "?year=2025&validate_tour_bindings=true",
        )) == (200, audited)
        assert saved_reread["uses_saved_run_package_snapshot"] is True
        assert reread["uses_current_server_reference_not_run_snapshot"] is True
        assert _request("GET", packages) == before_packages
