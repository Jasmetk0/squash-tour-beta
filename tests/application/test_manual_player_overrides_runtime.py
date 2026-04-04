from __future__ import annotations

import json
from pathlib import Path

from beta_engine.application.api_services import SimulationApiService
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService
from beta_engine.infrastructure.db import DatabaseSettings, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository


def _write_overrides(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _service(tmp_path, overrides_payload: dict[str, object]) -> SimulationApiService:
    db_file = tmp_path / "manual_overrides_runtime.db"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_overrides(overrides_path, overrides_payload)

    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{db_file}"))
    session_factory = create_session_factory(engine)
    repository = SimulationPersistenceRepository(engine=engine, session_factory=session_factory)
    return SimulationApiService(
        repository=repository,
        manual_overrides_service=ManualPlayerOverridesService(config_path=overrides_path),
    )


def test_active_override_in_target_season_is_added_with_manual_provenance(tmp_path) -> None:
    service = _service(
        tmp_path,
        {
            "overrides": [
                {
                    "override_id": "egy-legend-2027",
                    "season": 2027,
                    "country_code": "EGY",
                    "player_name": "Manual Legend",
                    "age": 19,
                    "profile_tier": "generational",
                    "is_exceptional": True,
                    "enabled": True,
                }
            ]
        },
    )

    service.initialize_run(run_id="run-a", season=2027, seed=44, config_version="v1", config_fingerprint="fp")
    provenance = service.list_generated_player_provenance(run_id="run-a")
    manual_rows = [row for row in provenance if row.source_type == "manual_override"]

    assert manual_rows
    assert manual_rows[0].override_id == "egy-legend-2027"
    assert manual_rows[0].quality_band == "generational_talent"


def test_disabled_or_different_season_overrides_do_not_apply(tmp_path) -> None:
    service = _service(
        tmp_path,
        {
            "overrides": [
                {
                    "override_id": "disabled",
                    "season": 2027,
                    "country_code": "EGY",
                    "player_name": "Disabled Player",
                    "age": 20,
                    "profile_tier": "elite",
                    "enabled": False,
                },
                {
                    "override_id": "other-season",
                    "season": 2030,
                    "country_code": "ENG",
                    "player_name": "Other Season",
                    "age": 21,
                    "profile_tier": "special",
                    "enabled": True,
                },
            ]
        },
    )

    service.initialize_run(run_id="run-b", season=2027, seed=44, config_version=None, config_fingerprint=None)
    provenance = service.list_generated_player_provenance(run_id="run-b")

    assert all(row.source_type == "planner_generated" for row in provenance)


def test_same_seed_same_config_keeps_manual_override_generation_deterministic(tmp_path) -> None:
    payload = {
        "overrides": [
            {
                "override_id": "eng-super",
                "season": 2028,
                "country_code": "ENG",
                "player_name": "Super Talent",
                "age": 18,
                "profile_tier": "special",
                "enabled": True,
                "is_exceptional": True,
                "attribute_overrides": {"technique": 95},
            }
        ]
    }
    service = _service(tmp_path, payload)

    service.initialize_run(run_id="left", season=2028, seed=909, config_version="v", config_fingerprint="f")
    service.initialize_run(run_id="right", season=2028, seed=909, config_version="v", config_fingerprint="f")

    left = [row.__dict__ for row in service.list_generated_player_provenance(run_id="left") if row.source_type == "manual_override"]
    right = [row.__dict__ for row in service.list_generated_player_provenance(run_id="right") if row.source_type == "manual_override"]

    assert len(left) == 1
    assert [{k: v for k, v in row.items() if k != "run_id"} for row in left] == [
        {k: v for k, v in row.items() if k != "run_id"} for row in right
    ]


def test_invalid_enabled_override_country_fails_run_initialization_loudly(tmp_path) -> None:
    service = _service(
        tmp_path,
        {
            "overrides": [
                {
                    "override_id": "bad-country-override",
                    "season": 2027,
                    "country_code": "ZZZ",
                    "player_name": "Broken Override",
                    "age": 20,
                    "profile_tier": "elite",
                    "enabled": True,
                }
            ]
        },
    )

    try:
        service.initialize_run(
            run_id="invalid-country-run",
            season=2027,
            seed=505,
            config_version=None,
            config_fingerprint=None,
        )
    except ValueError as exc:
        message = str(exc)
        assert "bad-country-override" in message
        assert "ZZZ" in message
    else:
        raise AssertionError("run initialization should fail for enabled manual override with unknown country")


def test_target_season_manual_override_applies_in_bootstrapped_child_run(tmp_path) -> None:
    service = _service(
        tmp_path,
        {
            "overrides": [
                {
                    "override_id": "future-star",
                    "season": 2028,
                    "country_code": "EGY",
                    "player_name": "Future Star",
                    "age": 18,
                    "profile_tier": "special",
                    "enabled": True,
                }
            ]
        },
    )
    service.initialize_run(run_id="parent", season=2027, seed=1234, config_version=None, config_fingerprint=None)
    service.simulate_full_season(run_id="parent")
    service.rollover_to_next_season(run_id="parent")
    service.bootstrap_next_season_run(run_id="parent", child_run_id="child", child_seed=1234)

    provenance = service.list_generated_player_provenance(run_id="child")
    manual_rows = [row for row in provenance if row.source_type == "manual_override"]
    assert manual_rows
    assert manual_rows[0].override_id == "future-star"
