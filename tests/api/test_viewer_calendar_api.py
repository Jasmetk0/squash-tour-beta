from __future__ import annotations

from urllib.parse import quote

import pytest

from test_simulation_api import ApiServer, _request
from tests.api.test_viewer_tournament_entry_field_api import _repository
from tests.api.viewer_saved_revision_helpers import (
    canonical_product_run as _canonical_run,
)
from tests.application.test_viewer_calendar_read_model import calendar_state

from beta_engine.application.run_package_service import RunPackageService
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.domain.run_packages import CanonicalPackageDocument, PackageEntity


pytestmark = pytest.mark.pr_critical


def _calendar_document(run_id: str, branch_id: str) -> CanonicalPackageDocument:
    state = calendar_state(run_id=run_id, branch_id=branch_id)
    version = state.package_versions[0]
    source_entities = tuple(
        PackageEntity(
            source_entity_id=entity.source_entity_id,
            entity_kind=entity.entity_kind,
            entity_schema_version=entity.entity_schema_version,
            scope=entity.scope,
            payload=entity.payload,
            references=entity.references,
        )
        for entity in state.entities
    )
    return CanonicalPackageDocument(
        package_type=version.package_type,
        package_id=version.package_id,
        source_version=version.source_version,
        provenance=version.provenance,
        explicit_scope=version.document_explicit_scope,
        entities=source_entities,
    )


def _ids(*values: str):
    stream = iter(values)
    return lambda _: next(stream)


def test_viewer_calendar_is_published_only_from_saved_run_package_state(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'viewer-calendar.sqlite'}"
    with ApiServer(database_url=database_url) as server:
        branch_id, run_id = _canonical_run(server)
        repository = _repository(database_url)
        package_service = RunPackageService(repository)
        document = _calendar_document(run_id, branch_id)

        preview = package_service.preview(
            run_id=run_id,
            branch_id=branch_id,
            document=document,
        )
        applied = package_service.confirm(
            run_id=run_id,
            branch_id=branch_id,
            document=document,
            command_id="apply-viewer-calendar",
            expected_head_revision_id=preview.saved_head_revision_id,
            expected_draft_version=preview.draft_version,
            expected_state_fingerprint=preview.current_state_fingerprint,
            expected_preview_fingerprint=preview.preview_fingerprint,
        )
        assert applied.state is not None

        root = f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/calendar"

        # Applied Working Draft package state is intentionally not public yet.
        assert _request("GET", root)[0] == 404

        saved = RunWorkingDraftService(
            repository,
            _ids("viewer-calendar-saved", "viewer-calendar-audit"),
        ).save(
            run_id=run_id,
            branch_id=branch_id,
            expected_draft_version=applied.draft_version,
        )

        status, payload = _request("GET", root)
        assert status == 200, payload
        assert payload["schema_version"] == "viewer_run_calendar.v1"
        assert payload["product_run_id"] == run_id
        assert payload["viewer_branch_id"] == branch_id
        assert payload["season_count"] == 1
        assert payload["event_count"] == 1
        event = payload["seasons"][0]["events"][0]
        assert event["event_id"] == "EVENT-1"
        assert event["event_name"] == "Czech Open"
        assert event["season_week"] == 7
        assert event["template_id"] == "WT-PLAT"
        assert event["tour_level"] == "WORLD_TOUR"

        rendered = str(payload)
        for forbidden in (
            "package_id",
            "source_package",
            "fingerprint",
            "provenance",
            "run_local_id",
            "ranking_points",
            "prize_money",
        ):
            assert forbidden not in rendered

        # A later unsaved local Package edit must not cross the Viewer Save boundary.
        state = package_service.get(run_id=run_id, branch_id=branch_id)
        assert state is not None
        event_entity = next(
            entity
            for entity in state.entities
            if entity.source_entity_id == "EVENT-1"
        )
        changed_payload = dict(event_entity.payload)
        changed_payload["event_name"] = "UNSAVED LIVE NAME"
        package_service.edit_entity(
            run_id=run_id,
            branch_id=branch_id,
            run_local_id=event_entity.run_local_id,
            payload=changed_payload,
            expected_draft_version=saved.working_draft.draft_version,
            expected_state_fingerprint=state.fingerprint,
        )

        status, after_unsaved_edit = _request("GET", root)
        assert status == 200, after_unsaved_edit
        assert after_unsaved_edit["seasons"][0]["events"][0]["event_name"] == (
            "Czech Open"
        )
        assert "UNSAVED LIVE NAME" not in str(after_unsaved_edit)


def test_viewer_calendar_is_not_found_without_saved_calendar_package(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'viewer-calendar-missing.sqlite'}"
    with ApiServer(database_url=database_url) as server:
        _, run_id = _canonical_run(server)
        status, _ = _request(
            "GET",
            f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/calendar",
        )
        assert status == 404
