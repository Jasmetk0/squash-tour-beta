"""ATP source-only historical Calendar via persisted Run Packages Preview/Confirm/Save."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from urllib.parse import quote

import pytest

from beta_engine.application.atp_historical_calendar_adapter import (
    ATPHistoricalCalendarAdapter, CALENDAR_SETUP_ID,
)
from beta_engine.application.atp_reference_package_adapter import ATP_SOURCE
from beta_engine.domain.run_packages import PackageType
from test_simulation_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def test_reference_calendar_setup_has_three_children_and_never_runnable_editions():
    source = ATPHistoricalCalendarAdapter()
    doc = source.build_document()
    assert doc.package_type == PackageType.SETUP
    assert doc.package_id == CALENDAR_SETUP_ID
    assert [child.package_type for child in doc.children] == [
        PackageType.CATEGORY, PackageType.SERIES, PackageType.CALENDAR
    ]
    assert [len(child.entities) for child in doc.children] == [11, 164, 1688]
    assert len(doc.children[-1].entities) == 37 + doc.children[-1].provenance["dated_occurrences"]
    cal = doc.children[-1]
    assert all(e.scope == "tennis.atp_tour.calendar.reference.1990_2026"
               for e in cal.entities)
    assert cal.provenance["run_consumption"] == (
        "opaque_reference_only_no_sporting_calendar"
    )
    assert all(e.payload["not_squash_rules"] is True for e in cal.entities)
    assert all(
        e.entity_kind not in ("calendar.event.v1", "calendar.metadata.v1")
        for e in cal.entities
    )
    assert source.catalog()["source_fingerprint"] == doc.source_fingerprint


def test_adapter_fails_closed_on_stale_calendar_snapshot(tmp_path: Path):
    for filename in (
        "category.json", "series.json", "seasons_1990_2026.json",
        "calendar_dates_v1.json", "calendar.json",
    ):
        shutil.copyfile(ATP_SOURCE / filename, tmp_path / filename)
    path = tmp_path / "calendar.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    event = next(e for e in doc["entities"] if
                 e["entity_kind"] == "tennis.calendar.occurrence.reference.v1")
    event["payload"]["start_date"] = "2025-12-31"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="stale or tampered"):
        ATPHistoricalCalendarAdapter(tmp_path).build_document()


def test_source_calendar_preview_confirm_save_reopen_and_idempotence(tmp_path: Path):
    uri = f"sqlite:///{tmp_path / 'atp-calendar-ref.db'}"
    with ApiServer(database_url=uri) as server:
        status, run = _request(
            "POST", server.base_url + "/run-containers",
            {"display_name": "ATP 1990–2026 reference Calendar"},
        )
        assert status in (200, 201), run
        run_id, branch_id = run["run_id"], run["viewer_branch_id"]
        base = (
            f"{server.base_url}/admin/runs/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/packages"
        )
        global_status, global_catalog = _request(
            "GET", server.base_url +
            "/admin/reference-packages/atp-tour-1990-2026-calendar"
        )
        assert global_status == 200, global_catalog
        local_status, catalog = _request(
            "GET", base + "/source-atp-reference-calendar/catalog"
        )
        assert local_status == 200 and catalog == global_catalog
        expected_calendar_size = catalog["children"][-1]["entity_count"]
        assert expected_calendar_size == 1688
        assert [c["entity_count"] for c in catalog["children"]] == [11, 164, expected_calendar_size]
        assert catalog["dated_years"] == [1996, 2000, 2001, 2002] + list(range(2004, 2027))
        assert catalog["undated_years"] == list(range(1990, 1996)) + [1997, 1998, 1999, 2003]
        assert _request("GET", base)[1]["state"] is None

        status, preview = _request(
            "POST", base + "/source-atp-reference-calendar/preview", {}
        )
        assert status == 200, preview
        assert len(preview["additions"]) == 11 + 164 + expected_calendar_size
        assert not preview["invalid"] and not preview["conflicts"]
        assert "document" not in preview  # avoid transmitting all historical JSON
        assert preview["document_identity"]["source_fingerprint"] == catalog["source_fingerprint"]
        assert _request("GET", base)[1]["state"] is None

        request = {
            "command_id": "install-atp-historical-calendar",
            "expected_head_revision_id": preview["saved_head_revision_id"],
            "expected_draft_version": preview["draft_version"],
            "expected_state_fingerprint": preview["current_state_fingerprint"],
            "expected_preview_fingerprint": preview["preview_fingerprint"],
            "conflict_resolutions": {},
        }
        refusal, _ = _request(
            "POST", base + "/source-atp-reference-calendar/confirm",
            {**request, "selected_entities": []},
        )
        assert refusal == 409
        status, applied = _request(
            "POST", base + "/source-atp-reference-calendar/confirm", request
        )
        assert status == 200, applied
        assert applied["draft_version"] == 1
        assert len(applied["state"]["entities"]) == 11 + 164 + expected_calendar_size
        assert {e["entity_kind"] for e in applied["state"]["entities"] if
                e["source_package_id"] == "atp_tour_1990_2026_calendar"} == {
                    "tennis.calendar.coverage.reference.v1",
                    "tennis.calendar.occurrence.reference.v1",
                }
        assert _request("GET", base)[1]["state"] is not None
        retry_status, retry = _request(
            "POST", base + "/source-atp-reference-calendar/confirm", request
        )
        assert retry_status == 200 and retry["already_applied"] is True

        saved_status, saved = _request(
            "POST",
            f"{server.base_url}/run-containers/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/working-draft/save",
            {"expected_draft_version": applied["draft_version"]},
        )
        assert saved_status == 201, saved
    with ApiServer(database_url=uri) as reopened:
        base = (
            f"{reopened.base_url}/admin/runs/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/packages"
        )
        state_status, persisted = _request("GET", base)
        assert state_status == 200
        assert len(persisted["state"]["entities"]) == 11 + 164 + expected_calendar_size
        assert _request(
            "GET", reopened.base_url +
            "/admin/reference-packages/atp-tour-1990-2026-calendar"
        )[0] == 200
