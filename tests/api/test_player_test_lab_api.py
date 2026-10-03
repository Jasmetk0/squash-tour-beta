from __future__ import annotations

import pytest

from test_simulation_api import ApiServer, _request


pytestmark = pytest.mark.pr_critical


def test_player_lab_api_lists_builtin_and_runs_shared_kernel_scenario(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'player-lab.db'}") as server:
        status, scenarios = _request(
            "GET",
            f"{server.base_url}/admin/labs/player/scenarios",
        )
        assert status == 200, scenarios
        assert [item["scenario_id"] for item in scenarios] == [
            "development-activity-baseline",
            "health-projection-explicit-recovery",
        ]
        assert scenarios[0]["read_only"] is True

        payload = {"scenario": scenarios[0]["scenario"]}
        status, result = _request(
            "POST",
            f"{server.base_url}/admin/labs/player/run",
            payload,
        )

        assert status == 200, result
        assert result["schema_version"] == "player_test_lab_result.v1"
        assert result["scenario_id"] == "development-activity-baseline"
        assert result["compatibility"]["production_kernels"] == [
            "weekly_player_development_update",
            "between_week_state_update",
        ]
        assert result["compatibility"]["run_mutation_performed"] is False
        assert result["compatibility"]["run_live_link"] is False
        assert result["compatibility"]["health_supported"] is True
        assert result["compatibility"]["training_load_supported"] is False
        assert result["compatibility"]["career_ai_supported"] is False
        assert result["diagnostics"]["variant_count"] == 2
        assert result["diagnostics"]["duration_weeks"] == 8

        by_variant = {
            item["variant_id"]: item
            for item in result["variants"]
        }
        assert by_variant["active"]["snapshots"][-1]["match_sharpness"] == 80
        assert by_variant["idle"]["snapshots"][-1]["match_sharpness"] == 64
        assert by_variant["active"]["snapshots"][-1]["health_projection"]["numeric_effect_applied"] is False
        assert by_variant["active"]["snapshots"][-1]["health_projection"]["highest_current_severity"] == 0


def test_player_lab_api_exact_replay_is_identical(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'player-lab-replay.db'}") as server:
        status, scenarios = _request(
            "GET",
            f"{server.base_url}/admin/labs/player/scenarios",
        )
        assert status == 200, scenarios
        payload = {"scenario": scenarios[0]["scenario"]}

        first_status, first = _request(
            "POST",
            f"{server.base_url}/admin/labs/player/run",
            payload,
        )
        second_status, second = _request(
            "POST",
            f"{server.base_url}/admin/labs/player/run",
            payload,
        )

        assert first_status == second_status == 200
        assert first == second


def test_player_lab_api_rejects_misaligned_variant_horizons(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'player-lab-invalid.db'}") as server:
        status, scenarios = _request(
            "GET",
            f"{server.base_url}/admin/labs/player/scenarios",
        )
        assert status == 200, scenarios
        scenario = scenarios[0]["scenario"]
        scenario["variants"][1]["competitive_match_counts"] = [0]

        status, _ = _request(
            "POST",
            f"{server.base_url}/admin/labs/player/run",
            {"scenario": scenario},
        )
        assert status == 422


def test_player_lab_api_runs_explicit_health_projection_scenario(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'player-lab-health.db'}") as server:
        status, scenarios = _request(
            "GET",
            f"{server.base_url}/admin/labs/player/scenarios",
        )
        assert status == 200, scenarios
        scenario = next(
            item["scenario"]
            for item in scenarios
            if item["scenario_id"] == "health-projection-explicit-recovery"
        )

        status, result = _request(
            "POST",
            f"{server.base_url}/admin/labs/player/run",
            {"scenario": scenario},
        )
        assert status == 200, result
        by_variant = {item["variant_id"]: item for item in result["variants"]}
        injured = by_variant["explicit-injury"]
        assert injured["initial_health_projection"]["highest_current_severity"] == 40
        assert injured["initial_health_projection"]["affected_domains"] == ["movement"]
        assert injured["initial_health_projection"]["numeric_effect_applied"] is False
        assert injured["snapshots"][1]["health_projection"]["highest_current_severity"] == 20
        assert injured["snapshots"][2]["health_projection"]["highest_current_severity"] == 0
        assert result["compatibility"]["health_supported"] is True
