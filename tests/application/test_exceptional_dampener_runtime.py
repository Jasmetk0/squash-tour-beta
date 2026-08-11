from __future__ import annotations

import json
from pathlib import Path

from beta_engine.application.api_services import SimulationApiService
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService
from beta_engine.domain.countries import Country
from beta_engine.domain.players import AnnualTalentClassPlanner, TalentQualityBand
from beta_engine.infrastructure.db import DatabaseSettings, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.repositories import PersistedGeneratedPlayerProvenanceRecord, SimulationPersistenceRepository


def _write_overrides(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _service(tmp_path, overrides_payload: dict[str, object]) -> SimulationApiService:
    db_file = tmp_path / "exceptional_dampener.db"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_overrides(overrides_path, overrides_payload)

    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{db_file}"))
    session_factory = create_session_factory(engine)
    repository = SimulationPersistenceRepository(engine=engine, session_factory=session_factory)
    repository.bootstrap_schema()
    return SimulationApiService(
        repository=repository,
        manual_overrides_service=ManualPlayerOverridesService(config_path=overrides_path),
    )


def _country(code: str, strength: int = 4) -> Country:
    return Country(
        code=code,
        name=code,
        flag_asset=None,
        region="TEST",
        population=90_000_000,
        squash_popularity=strength,
        squash_access=strength,
        development_quality=strength,
        competition_quality=strength,
        elite_support=strength,
        squash_tradition=strength,
    )


def test_manual_exceptional_override_is_audit_only_for_v1_innate_odds(tmp_path) -> None:
    countries = [_country("AAA")]
    with_override = _service(
        tmp_path,
        {
            "overrides": [
                {
                    "override_id": "aaa-legend-2030",
                    "season": 2030,
                    "country_code": "AAA",
                    "player_name": "Legend",
                    "age": 19,
                    "profile_tier": "generational",
                    "is_exceptional": True,
                    "enabled": True,
                }
            ]
        },
    )
    without_override = _service(tmp_path / "other", {"overrides": []})

    planner_with = AnnualTalentClassPlanner(
        dampener=with_override._build_recent_greatness_dampener(season=2032, include_history=True)
    )
    planner_without = AnnualTalentClassPlanner(
        dampener=without_override._build_recent_greatness_dampener(season=2032, include_history=True)
    )

    allocation_with = planner_with.plan(year=2032, seed=11, countries=countries).allocations[0]
    allocation_without = planner_without.plan(year=2032, seed=11, countries=countries).allocations[0]

    assert allocation_with.quality_weights == allocation_without.quality_weights
    assert allocation_with.dampener.active is True
    assert allocation_with.dampener.signal_count == 1
    assert set(allocation_with.dampener.multipliers.values()) == {1.0}
    assert any(item.reference_id == "aaa-legend-2030" for item in allocation_with.dampener.contributions)


def test_dampener_effect_decays_over_time_and_has_floor(tmp_path) -> None:
    service = _service(
        tmp_path,
        {
            "overrides": [
                {
                    "override_id": "aaa-legend-2030",
                    "season": 2030,
                    "country_code": "AAA",
                    "player_name": "Legend",
                    "age": 19,
                    "profile_tier": "generational",
                    "is_exceptional": True,
                    "enabled": True,
                }
            ]
        },
    )
    dampener = service._build_recent_greatness_dampener(season=2031, include_history=True)

    early = dampener.quality_multiplier(country_code="AAA", year=2031, band=TalentQualityBand.GENERATIONAL)
    later = dampener.quality_multiplier(country_code="AAA", year=2036, band=TalentQualityBand.GENERATIONAL)

    assert early >= 0.28
    assert early < later < 1.0


def test_dampener_is_country_scoped_not_global(tmp_path) -> None:
    service = _service(
        tmp_path,
        {
            "overrides": [
                {
                    "override_id": "aaa-legend-2030",
                    "season": 2030,
                    "country_code": "AAA",
                    "player_name": "Legend",
                    "age": 19,
                    "profile_tier": "generational",
                    "is_exceptional": True,
                    "enabled": True,
                }
            ]
        },
    )
    dampener = service._build_recent_greatness_dampener(season=2032, include_history=True)

    assert dampener.quality_multiplier(country_code="AAA", year=2032, band=TalentQualityBand.SPECIAL) < 1.0
    assert dampener.quality_multiplier(country_code="BBB", year=2032, band=TalentQualityBand.SPECIAL) == 1.0


def test_same_seed_and_history_is_deterministic(tmp_path) -> None:
    service = _service(tmp_path, {"overrides": []})
    countries = [_country("AAA"), _country("BBB")]

    left_players, _, left_country, left_prov = service._build_fresh_players_and_provenance(
        run_id="run-left",
        season=2035,
        seed=919,
        countries=countries,
        dataset_status=None,
        config_version=None,
        config_fingerprint=None,
    )
    right_players, _, right_country, right_prov = service._build_fresh_players_and_provenance(
        run_id="run-left",
        season=2035,
        seed=919,
        countries=countries,
        dataset_status=None,
        config_version=None,
        config_fingerprint=None,
    )

    assert [item.model_dump() for item in left_players] == [item.model_dump() for item in right_players]
    assert [item.__dict__ for item in left_country] == [item.__dict__ for item in right_country]
    assert [item.__dict__ for item in left_prov] == [item.__dict__ for item in right_prov]


def test_strong_country_still_has_elite_odds_under_dampener(tmp_path) -> None:
    service = _service(
        tmp_path,
        {
            "overrides": [
                {
                    "override_id": "str-legend-2030",
                    "season": 2030,
                    "country_code": "STR",
                    "player_name": "Legend",
                    "age": 20,
                    "profile_tier": "generational",
                    "is_exceptional": True,
                    "enabled": True,
                }
            ]
        },
    )
    planner = AnnualTalentClassPlanner(dampener=service._build_recent_greatness_dampener(season=2032, include_history=True))
    country = _country("STR", strength=5)

    weights = planner.plan(year=2032, seed=55, countries=[country]).allocations[0].quality_weights
    assert weights[TalentQualityBand.ELITE] > 0.04


def test_preview_mode_is_explicitly_neutral(tmp_path) -> None:
    service = _service(
        tmp_path,
        {
            "overrides": [
                {
                    "override_id": "aaa-legend-2030",
                    "season": 2030,
                    "country_code": "AAA",
                    "player_name": "Legend",
                    "age": 19,
                    "profile_tier": "generational",
                    "is_exceptional": True,
                    "enabled": True,
                }
            ]
        },
    )
    preview_dampener = service._build_recent_greatness_dampener(season=2032, include_history=False)
    diagnostics = preview_dampener.diagnostics(country_code="AAA", year=2032)

    assert diagnostics.active is False
    assert diagnostics.recent_greatness_score == 0.0


def test_fresh_run_dampener_uses_persisted_provenance_history_and_exposes_manual_source(tmp_path) -> None:
    service = _service(
        tmp_path,
        {
            "overrides": [
                {
                    "override_id": "aaa-legend-2030",
                    "season": 2030,
                    "country_code": "AAA",
                    "player_name": "Legend",
                    "age": 19,
                    "profile_tier": "generational",
                    "is_exceptional": True,
                    "enabled": True,
                }
            ]
        },
    )

    service.repository.replace_generated_player_provenance(
        run_id="hist-a",
        season=2031,
        records=[
            PersistedGeneratedPlayerProvenanceRecord(
                run_id="hist-a",
                season=2031,
                player_id="AAA-00001",
                country_code="AAA",
                talent_sequence=1,
                talent_seed_value=77,
                quality_band=TalentQualityBand.GENERATIONAL.value,
                is_top_band=True,
                source_type="planner_generated",
                override_id=None,
                origin_source_type="planner_generated",
                origin_quality_band=TalentQualityBand.GENERATIONAL.value,
                origin_override_id=None,
                origin_season=2031,
            )
        ],
    )

    dampener = service._build_recent_greatness_dampener(season=2032, include_history=True)
    diagnostics = dampener.diagnostics(country_code="AAA", year=2032)

    assert diagnostics.signal_count >= 2
    assert any(item.source == "manual_override" and item.reference_id == "aaa-legend-2030" for item in diagnostics.contributions)
    assert any(item.source == "planner_generated" for item in diagnostics.contributions)
