from __future__ import annotations

import pytest

from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def test_copied_fax_preview_reports_missing_points_before_creating_a_run(
    tmp_path,
) -> None:
    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'fax-80-edition-preview.db'}"
    ) as server:
        points_path = tmp_path / "category-points.json"
        server.app.state.season_category_points_registry_path = points_path
        status, body = _request(
            "POST",
            f"{server.base_url}/run-containers/pre-alpha/fax-reference/preview",
            {
                "display_name": "Copied FAX acceptance preview",
                "world_package_id": "official_fax_world",
                "season": "2000/2001",
                "seed": 200001,
                "target_pool_size": 1000,
                "best_n": 15,
                "automatic_retirement_age": 46,
            },
        )

        assert status == 200, body
        assert body["schema_version"] == "pre_alpha_fax_reference_preview.v1"
        assert body["ready_to_materialize"] is False
        assert len(body["incomplete_points_event_ids"]) == 80
        assert body["world_entity_count"] > 0
        assert body["calendar_event_count"] == 80
        assert body["world_tour_edition_count"] == 80
        assert body["lower_tour_edition_count"] == 0
        assert body["required_world_tour_edition_count"] == 80
        assert len(body["world_source_fingerprint"]) == 64
        assert len(body["calendar_source_fingerprint"]) == 64

        from beta_engine.domain.run_packages import canonical_hash
        status, rejected = _request(
            "POST", f"{server.base_url}/run-containers/pre-alpha/fax-reference/materialize",
            {"request": body["request"], "expected_preview_fingerprint": canonical_hash(body)},
        )
        assert status == 409, rejected
        assert "complete authored ranking points" in rejected["detail"]["message"]
        assert server.app.state.runtime.repository.list_run_containers() == []
        assert not points_path.exists()
