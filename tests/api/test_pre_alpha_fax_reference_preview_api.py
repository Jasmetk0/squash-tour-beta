from __future__ import annotations

import pytest

from tests.api.test_saved_revision_history_api import ApiServer, _request


pytestmark = pytest.mark.pr_critical


def test_copied_fax_reference_api_preview_uses_reviewed_80_edition_acceptance_source(
    tmp_path,
) -> None:
    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'fax-80-edition-preview.db'}"
    ) as server:
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
        assert body["ready_to_materialize"] is True
        assert body["world_entity_count"] > 0
        assert body["calendar_event_count"] == 80
        assert body["world_tour_edition_count"] == 80
        assert body["lower_tour_edition_count"] == 0
        assert body["required_world_tour_edition_count"] == 80
        assert len(body["world_source_fingerprint"]) == 64
        assert len(body["calendar_source_fingerprint"]) == 64
