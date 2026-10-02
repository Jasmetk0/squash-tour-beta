from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from urllib import error, request

import pytest
import uvicorn

from beta_engine.main import create_app

COUNTRIES_FIXTURE = {
    "dataset_status": "temporary_seed_demo",
    "countries": [
        {
            "code": "AAA",
            "name": "Alpha",
            "flag_asset": None,
            "region": "EUROPE",
            "population": 10_000_000,
            "wealth_support": 5,
            "squash_popularity": 5,
            "squash_tradition": 4,
            "system_quality": 5,
        },
        {
            "code": "BBB",
            "name": "Beta",
            "flag_asset": None,
            "region": "ASIA",
            "population": 80_000_000,
            "wealth_support": 2,
            "squash_popularity": 2,
            "squash_tradition": 2,
            "system_quality": 2,
        },
    ],
}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class ApiServer:
    def __init__(self, *, database_url: str, countries_config_path: str) -> None:
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        app = create_app(database_url=database_url, countries_config_path=countries_config_path)
        self.server = uvicorn.Server(uvicorn.Config(app=app, host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self) -> "ApiServer":
        self.thread.start()
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                _ = _request("GET", f"{self.base_url}/health")
                return self
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("server did not start")

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


def _request(method: str, url: str, payload: dict[str, object] | None = None) -> tuple[int, dict[str, object]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, method=method)
    req.add_header("content-type", "application/json")
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else {})
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        parsed = json.loads(raw) if raw else {}
        return int(exc.code), parsed


def _write_fixture(path: Path, payload: dict[str, object] = COUNTRIES_FIXTURE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@pytest.mark.pr_critical
def test_single_year_preview_is_deterministic_for_same_seed_and_year(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'preview.db'}", countries_config_path=str(countries_path)) as server:
        status_left, left = _request("GET", f"{server.base_url}/world/talent-class/preview?year=2030&seed=123")
        status_right, right = _request("GET", f"{server.base_url}/world/talent-class/preview?year=2030&seed=123")

    assert status_left == 200
    assert status_right == 200
    assert left == right
    assert left["total_talents"] == sum(item["planned_count"] for item in left["countries"])
    preview_country = left["countries"][0]
    assert sum(preview_country["expected_band_counts"].values()) == pytest.approx(
        preview_country["planned_count"]
    )
    for band, weight in preview_country["quality_weights"].items():
        assert preview_country["expected_band_counts"][band] == round(
            preview_country["planned_count"] * weight,
            4,
        )
    assert preview_country["expected_elite_talents"] == round(
        preview_country["expected_band_counts"]["elite_prospect"]
        + preview_country["expected_band_counts"]["special_prospect"]
        + preview_country["expected_band_counts"]["generational_talent"],
        4,
    )
    assert preview_country["expected_tour_talents"] == preview_country["expected_band_counts"]["strong_prospect"]
    assert preview_country["expected_pro_depth"] == preview_country["expected_band_counts"]["solid_prospect"]
    assert preview_country["elite_talents"] == (
        preview_country["actual_band_counts"]["elite_prospect"]
        + preview_country["actual_band_counts"]["special_prospect"]
        + preview_country["actual_band_counts"]["generational_talent"]
    )
    assert preview_country["tour_talents"] == preview_country["actual_band_counts"]["strong_prospect"]
    assert preview_country["pro_depth"] == preview_country["actual_band_counts"]["solid_prospect"]
    assert "dampener" in left["countries"][0]
    assert left["countries"][0]["dampener"]["active"] is False


def test_multi_year_summary_aggregates_counts_and_rates(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'summary.db'}", countries_config_path=str(countries_path)) as server:
        status, payload = _request("GET", f"{server.base_url}/world/talent-class/summary?year_start=2030&years=5&seed=77")

    assert status == 200
    assert payload["years"] == 5
    assert payload["total_talents_across_span"] > 0
    assert payload["average_total_talents_per_year"] > 0
    assert payload["total_talents_across_span"] == sum(item["total_planned_talents"] for item in payload["countries"])
    assert sum(payload["global_band_totals"].values()) == payload["total_talents_across_span"]
    assert payload["global_elite_talents"] == (
        payload["global_band_totals"]["elite_prospect"]
        + payload["global_band_totals"]["special_prospect"]
        + payload["global_band_totals"]["generational_talent"]
    )
    assert payload["global_tour_talents"] == payload["global_band_totals"]["strong_prospect"]
    assert payload["global_pro_depth"] == payload["global_band_totals"]["solid_prospect"]
    country = payload["countries"][0]
    assert country["total_elite_talents"] == (
        country["total_elite_count"] + country["total_special_count"] + country["total_generational_count"]
    )
    assert country["average_elite_talents_per_year"] == round(country["total_elite_talents"] / payload["years"], 4)


def test_preview_reflects_current_countries_config(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'reflect.db'}", countries_config_path=str(countries_path)) as server:
        _, before = _request("GET", f"{server.base_url}/world/talent-class/preview?year=2030&seed=123")
        updated = dict(COUNTRIES_FIXTURE)
        updated["countries"] = [
            *COUNTRIES_FIXTURE["countries"],
            {
                "code": "CCC",
                "name": "Gamma",
                "flag_asset": None,
                "region": "AFRICA",
                "population": 30_000_000,
                "wealth_support": 3,
                "squash_popularity": 3,
                "squash_tradition": 3,
                "system_quality": 3,
            },
        ]
        _write_fixture(countries_path, updated)
        _, after = _request("GET", f"{server.base_url}/world/talent-class/preview?year=2030&seed=123")

    assert before["country_count"] == 2
    assert after["country_count"] == 3
    assert len(after["countries"]) == 3
    assert any(country["country_code"] == "CCC" for country in after["countries"])


def test_preview_rejects_invalid_query_params(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'invalid.db'}", countries_config_path=str(countries_path)) as server:
        status_preview, payload_preview = _request("GET", f"{server.base_url}/world/talent-class/preview?year=bad&seed=1")
        status_summary, payload_summary = _request("GET", f"{server.base_url}/world/talent-class/summary?year_start=2030&years=0")

    assert status_preview == 422
    assert payload_preview["detail"]
    assert status_summary == 422
    assert payload_summary["detail"]

@pytest.mark.pr_critical
def test_talent_calibration_endpoint_is_typed_deterministic_and_read_only(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    database_path = tmp_path / "calibration.db"
    with ApiServer(database_url=f"sqlite:///{database_path}", countries_config_path=str(countries_path)) as server:
        before_status, before_runs = _request("GET", f"{server.base_url}/runs")
        status, first = _request("GET", f"{server.base_url}/world/talent-class/calibration?seed=77&sample_count=75")
        retry_status, retry = _request("GET", f"{server.base_url}/world/talent-class/calibration?seed=77&sample_count=75")
        invalid_status, _ = _request("GET", f"{server.base_url}/world/talent-class/calibration?sample_count=0")
        after_status, after_runs = _request("GET", f"{server.base_url}/runs")
    assert before_status == after_status == 200
    assert before_runs == after_runs
    assert status == retry_status == 200
    assert first == retry
    assert invalid_status == 422
    assert len(first["bands"]) == 5
    assert sum(row["generated_count"] for row in first["bands"]) == 75
    assert first["quality_policy_fingerprint"]
    assert first["sporting_profile_policy_fingerprint"]


def _comparison_payload(minimum: object = 110, maximum: object = 190) -> dict[str, object]:
    return {"seed": 77, "sample_count": 75, "candidate_ranges": {
        band: {"potential_min": minimum, "potential_max": maximum}
        for band in ("solid_prospect", "strong_prospect", "elite_prospect", "special_prospect", "generational_talent")
    }}


@pytest.mark.pr_critical
def test_candidate_comparison_endpoint_is_typed_deterministic_and_read_only(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'compare.db'}", countries_config_path=str(countries_path)) as server:
        _, before = _request("GET", f"{server.base_url}/runs")
        status, first = _request("POST", f"{server.base_url}/world/talent-class/calibration/compare", _comparison_payload())
        retry_status, retry = _request("POST", f"{server.base_url}/world/talent-class/calibration/compare", _comparison_payload())
        invalid = []
        missing = _comparison_payload()
        del missing["candidate_ranges"]["generational_talent"]
        invalid.append(_request("POST", f"{server.base_url}/world/talent-class/calibration/compare", missing)[0])
        for low, high in ((191, 190), (-1, 10), (10, 201), (110.5, 190)):
            invalid.append(_request("POST", f"{server.base_url}/world/talent-class/calibration/compare", _comparison_payload(low, high))[0])
        _, after = _request("GET", f"{server.base_url}/runs")
    assert status == retry_status == 200 and first == retry
    assert before == after
    assert invalid == [422] * 5
    assert first["global_comparison"]["delta"]["unchanged"] == 75
    assert first["candidate_sandbox_configuration_fingerprint"]


@pytest.mark.pr_critical
def test_multi_seed_comparison_endpoint_is_bounded_deterministic_and_read_only(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    payload = _comparison_payload()
    payload.pop("seed"); payload.pop("sample_count")
    payload.update(seed_start=20, seed_count=3, sample_count_per_seed=25)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'multi.db'}", countries_config_path=str(countries_path)) as server:
        _, before = _request("GET", f"{server.base_url}/runs")
        status, first = _request("POST", f"{server.base_url}/world/talent-class/calibration/compare-multi-seed", payload)
        retry_status, retry = _request("POST", f"{server.base_url}/world/talent-class/calibration/compare-multi-seed", payload)
        too_large = dict(payload, seed_count=6, sample_count_per_seed=50_000)
        invalid_status, _ = _request("POST", f"{server.base_url}/world/talent-class/calibration/compare-multi-seed", too_large)
        _, after = _request("GET", f"{server.base_url}/runs")
    assert status == retry_status == 200 and first == retry
    assert invalid_status == 422
    assert before == after
    assert first["seeds"] == [20, 21, 22]
    assert first["total_sample_count"] == 75
    assert sum(row["generated_count"] for row in first["pooled_bands"]) == 75
