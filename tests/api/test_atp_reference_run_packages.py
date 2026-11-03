"""Source-only ATP Tour Category/Series via ordinary Run Package Preview/Apply/Save."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from urllib.parse import quote

import pytest

from beta_engine.application.atp_reference_package_adapter import (
    ATPReferencePackageAdapter,
    ATP_SOURCE,
    CATEGORY_ID,
    SERIES_ID,
    SETUP_ID,
)
from beta_engine.domain.run_packages import PackageType
from test_simulation_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def test_atp_reference_adapter_is_explicit_non_sporting_atomic_setup() -> None:
    adapter = ATPReferencePackageAdapter()
    doc = adapter.build_document()
    assert doc.package_type is PackageType.SETUP
    assert doc.package_id == SETUP_ID
    assert [child.package_type for child in doc.children] == [
        PackageType.CATEGORY, PackageType.SERIES
    ]
    assert [child.package_id for child in doc.children] == [CATEGORY_ID, SERIES_ID]
    assert [len(child.entities) for child in doc.children] == [11, 164]
    assert len(doc.entities) == 0
    assert doc.provenance["historical_2026_status"] == "provisional"
    assert "no_calendar" in doc.provenance["run_consumption"]
    assert all(
        entity.payload["not_squash_rules"] is True
        for child in doc.children for entity in child.entities
    )
    catalog = adapter.catalog()
    assert catalog["source_fingerprint"] == doc.source_fingerprint
    assert catalog["reference_span"] == {"from": 1990, "to": 2026}
    assert catalog["provisional_years"] == [2026]


def test_atp_reference_adapter_rejects_forged_category_dependency(tmp_path: Path) -> None:
    for filename in ("category.json", "series.json"):
        shutil.copyfile(ATP_SOURCE / filename, tmp_path / filename)
    path = tmp_path / "series.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["entities"][0]["references"][0]["source_entity_id"] = "forged_category"
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="incompatible Category references"):
        ATPReferencePackageAdapter(tmp_path).build_document()


def test_atp_reference_http_atomic_preview_apply_save_restore(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'atp-reference.db'}"
    with ApiServer(database_url=url) as server:
        status, run = _request("POST", server.base_url + "/run-containers",
                               {"display_name": "ATP reference only"})
        assert status in (200, 201), run
        run_id, branch_id = run["run_id"], run["viewer_branch_id"]
        base = (f"{server.base_url}/admin/runs/{quote(run_id, safe='')}"
                f"/branches/{quote(branch_id, safe='')}/packages")
        catalog_status, catalog = _request("GET", base + "/source-atp-reference/catalog")
        assert catalog_status == 200
        assert catalog["package_id"] == SETUP_ID
        assert [c["entity_count"] for c in catalog["children"]] == [11, 164]
        assert _request("GET", base)[1]["state"] is None

        status, preview = _request("POST", base + "/source-atp-reference/preview", {})
        assert status == 200, preview
        assert len(preview["additions"]) == 175
        assert not preview["conflicts"] and not preview["invalid"]
        assert not preview["unresolved"]
        assert _request("GET", base)[1]["state"] is None

        command = {
            "command_id": "install-atp-reference-v1",
            "expected_head_revision_id": preview["saved_head_revision_id"],
            "expected_draft_version": preview["draft_version"],
            "expected_state_fingerprint": preview["current_state_fingerprint"],
            "expected_preview_fingerprint": preview["preview_fingerprint"],
            "conflict_resolutions": {},
        }
        status, refused = _request("POST", base + "/source-atp-reference/confirm",
                                   {**command, "selected_entities": []})
        assert status == 409, refused
        assert _request("GET", base)[1]["state"] is None

        status, installed = _request("POST", base + "/source-atp-reference/confirm", command)
        assert status == 200, installed
        state = installed["state"]
        assert installed["draft_version"] == 1
        assert len(state["entities"]) == 175
        assert {v["package_type"] for v in state["package_versions"]} == {
            "Setup", "Category", "Series"
        }
        assert all(e["scope"].startswith("tennis.atp_tour.") for e in state["entities"])
        assert all(e["entity_kind"].startswith("tennis.") for e in state["entities"])
        assert _request("GET", base)[1]["fingerprint"] == installed["state_fingerprint"]
        status, retry = _request("POST", base + "/source-atp-reference/confirm", command)
        assert status == 200 and retry["already_applied"] is True
        assert retry["state_fingerprint"] == installed["state_fingerprint"]

        save_url = (
            f"{server.base_url}/run-containers/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/working-draft/save"
        )
        save_status, saved = _request(
            "POST", save_url, {"expected_draft_version": installed["draft_version"]}
        )
        assert save_status == 201, saved

    with ApiServer(database_url=url) as reopened:
        base = (
            f"{reopened.base_url}/admin/runs/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/packages"
        )
        status, state = _request("GET", base)
        assert status == 200
        assert state["fingerprint"] == installed["state_fingerprint"]
        assert len(state["state"]["entities"]) == 175
        assert sum(v["package_type"] == "Calendar"
                   for v in state["state"]["package_versions"]) == 0
