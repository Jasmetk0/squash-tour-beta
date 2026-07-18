from __future__ import annotations

from sqlalchemy import text

from beta_engine.infrastructure.db import DatabaseSettings, SimulationRunInfo, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.repositories import RunProspectRecord, SimulationPersistenceRepository, deterministic_prospect_id
from beta_engine.application.season_models import SeasonState


def _repository(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'runs.db'}"))
    session_factory = create_session_factory(engine)
    repository = SimulationPersistenceRepository(engine=engine, session_factory=session_factory)
    repository.bootstrap_schema()
    return repository, engine


def _record(**overrides) -> RunProspectRecord:
    data = dict(
        prospect_id=deterministic_prospect_id(run_id="run-p", world_id="official_fax_world", season_start_year=2027, season_week=3, country_code="EGY", local_sequence=1, profile_version="prospect_profile_v1", cohort_policy_version="intake_volume_v1"),
        run_id="run-p", world_id="official_fax_world", season_start_year=2027, season_label="2027/2028", season_week=3,
        calendar_year=2027, year_week=10, birth_year=2012, birth_year_week=10, age=15, country_code="EGY", country_name="Egypt",
        status="prospect", source_type="weekly_15yo_cohort", cohort_policy_version="intake_volume_v1", profile_version="prospect_profile_v1",
        first_name=None, last_name=None, display_name="EGY Prospect 0001", short_name=None,
        identity_seed="identity-seed", profile_seed="profile-seed", development_seed="development-seed", potential_seed="potential-seed", trait_seed="trait-seed",
        profile_json={"identity_schema": "sparse"}, development_json={"curve_hint": "unset"}, potential_json={"reserved": True}, trait_json={"future_traits": []},
    )
    data.update(overrides)
    return RunProspectRecord(**data)


def test_bootstrap_creates_run_prospects_table(tmp_path):
    _, engine = _repository(tmp_path)
    with engine.connect() as connection:
        tables = {row[0] for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    assert "run_prospects" in tables


def test_insert_list_get_filter_and_json_round_trip(tmp_path):
    repository, _ = _repository(tmp_path)
    record = _record()
    repository.upsert_run_prospects([record])
    assert repository.list_run_prospects(run_id="missing") == []
    assert repository.list_run_prospects(run_id="run-p") == [record]
    assert repository.get_run_prospect(run_id="run-p", prospect_id=record.prospect_id) == record
    assert repository.list_run_prospects(run_id="run-p", country_code="egy") == [record]
    assert repository.list_run_prospects(run_id="run-p", season_week=3) == [record]
    assert repository.list_run_prospects(run_id="run-p", season_week=4) == []
    assert repository.list_run_prospects(run_id="run-p")[0].profile_json == {"identity_schema": "sparse"}


def test_upsert_is_idempotent_and_does_not_mutate_active_state_or_rankings(tmp_path):
    repository, _ = _repository(tmp_path)
    state = SeasonState(season=2027, ordered_events=[], next_event_index=0)
    repository.upsert_simulation_run(SimulationRunInfo(run_id="run-p", season=2027, seed=1))
    repository.save_season_state(run_id="run-p", state=state)
    before_state = repository.load_season_state(run_id="run-p")
    record = _record()
    repository.upsert_run_prospects([record])
    repository.upsert_run_prospects([record])
    assert repository.list_run_prospects(run_id="run-p") == [record]
    assert repository.load_season_state(run_id="run-p") == before_state
    assert repository.list_generated_player_provenance(run_id="run-p") == []
    assert repository.count_ranking_snapshots(run_id="run-p") == 0
    assert repository.count_race_snapshots(run_id="run-p") == 0


def test_deterministic_prospect_id_is_stable_and_input_sensitive():
    kwargs = dict(run_id="run", world_id="official_fax_world", season_start_year=2027, season_week=1, country_code="EGY", local_sequence=1, profile_version="v1", cohort_policy_version="c1")
    assert deterministic_prospect_id(**kwargs) == deterministic_prospect_id(**kwargs)
    assert deterministic_prospect_id(**kwargs) != deterministic_prospect_id(**(kwargs | {"local_sequence": 2}))

from beta_engine.application.run_prospect_materialization_service import (
    COHORT_POLICY_VERSION,
    PROFILE_VERSION,
    RunProspectMaterializationConflictError,
    RunProspectMaterializationService,
)
from beta_engine.application.run_weekly_intake_cohort_preview_service import RunWeeklyIntakeCohortPreviewService
from beta_engine.application.season_registry_service import SeasonRegistryService
from beta_engine.application.world_package_countries_service import WorldPackageCountriesService
from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService


def _materialization_service(repository: SimulationPersistenceRepository) -> RunProspectMaterializationService:
    preview = RunWeeklyIntakeCohortPreviewService(
        repository=repository,
        countries_service=WorldPackageCountriesService(registry_service=WorldPackageRegistryService(countries_service=CountriesConfigService(), manual_overrides_service=ManualPlayerOverridesService())),
        season_registry=SeasonRegistryService(),
    )
    return RunProspectMaterializationService(repository=repository, preview_service=preview)


def test_materialize_15yo_cohort_generates_deterministic_records_and_shells(tmp_path):
    repository, _ = _repository(tmp_path)
    repository.upsert_simulation_run(SimulationRunInfo(run_id="run-m", season=2027, seed=1))
    service = _materialization_service(repository)

    result = service.materialize_15yo_cohort(run_id="run-m", base_annual_intake_target=4, country_code="GER")

    assert result.requested_prospect_count == result.annual_target
    assert result.created_count == result.annual_target
    records = repository.list_run_prospects(run_id="run-m", country_code="GER", season_start_year=2027, limit=None)
    assert len(records) == result.annual_target
    first = records[0]
    assert first.prospect_id == deterministic_prospect_id(run_id="run-m", world_id="official_fax_world", season_start_year=2027, season_week=first.season_week, country_code="GER", local_sequence=1, profile_version=PROFILE_VERSION, cohort_policy_version=COHORT_POLICY_VERSION)
    assert first.age == 15
    assert first.status == "prospect"
    assert first.source_type == "weekly_15yo_cohort"
    assert first.display_name.startswith("GER Prospect ")
    assert all([first.identity_seed, first.profile_seed, first.development_seed, first.potential_seed, first.trait_seed])
    assert first.profile_json["reserved_for_future_attributes"] is True
    assert first.development_json["reserved_for_future_development"] is True
    assert first.potential_json["reserved_for_future_potential"] is True
    assert first.trait_json["reserved_for_future_traits"] is True


def test_materialize_15yo_cohort_is_idempotent_and_detects_conflicts(tmp_path):
    repository, _ = _repository(tmp_path)
    repository.upsert_simulation_run(SimulationRunInfo(run_id="run-i", season=2027, seed=1))
    service = _materialization_service(repository)

    first = service.materialize_15yo_cohort(run_id="run-i", base_annual_intake_target=2, country_code="GER")
    second = service.materialize_15yo_cohort(run_id="run-i", base_annual_intake_target=2, country_code="GER")
    assert first.created_count == first.annual_target
    assert second.created_count == 0
    assert second.skipped_count == first.annual_target
    assert second.already_materialized is True

    record = repository.list_run_prospects(run_id="run-i", country_code="GER", limit=None)[0]
    repository.upsert_run_prospects([RunProspectRecord(**(record.__dict__ | {"display_name": "Tampered Prospect"}))])
    try:
        service.materialize_15yo_cohort(run_id="run-i", base_annual_intake_target=2, country_code="GER")
    except RunProspectMaterializationConflictError as exc:
        assert exc.conflicts == [record.prospect_id]
    else:
        raise AssertionError("expected conflict")
    repaired = service.materialize_15yo_cohort(run_id="run-i", base_annual_intake_target=2, country_code="GER", overwrite=True)
    assert repaired.conflict_count == 1
    assert repository.get_run_prospect(run_id="run-i", prospect_id=record.prospect_id).display_name != "Tampered Prospect"


def test_materialization_policy_conflict_removes_only_stale_scope_records_on_overwrite(tmp_path):
    repository, _ = _repository(tmp_path)
    repository.upsert_simulation_run(SimulationRunInfo(run_id="run-policy", season=2027, seed=1))
    service = _materialization_service(repository)

    service.materialize_15yo_cohort(
        run_id="run-policy",
        base_annual_intake_target=2,
        country_code="GER",
    )
    unrelated = service.materialize_15yo_cohort(
        run_id="run-policy",
        base_annual_intake_target=2,
        country_code="BOG",
    )
    future_season_record = RunProspectRecord(
        **(
            repository.list_run_prospects(run_id="run-policy", country_code="BOG", limit=None)[0].__dict__
            | {"prospect_id": "future-season-prospect", "season_start_year": 2028}
        )
    )
    repository.upsert_run_prospects([future_season_record])

    try:
        service.materialize_15yo_cohort(
            run_id="run-policy",
            base_annual_intake_target=4,
            country_code="GER",
        )
    except RunProspectMaterializationConflictError as exc:
        assert exc.conflicts
    else:
        raise AssertionError("expected policy scope conflict")

    overwritten = service.materialize_15yo_cohort(
        run_id="run-policy",
        base_annual_intake_target=4,
        country_code="GER",
        overwrite=True,
    )
    ger_records = repository.list_run_prospects(
        run_id="run-policy",
        country_code="GER",
        season_start_year=2027,
        limit=None,
    )
    assert overwritten.conflict_count > 0
    assert len(ger_records) == overwritten.requested_prospect_count
    assert {record.prospect_id for record in ger_records}.isdisjoint(
        {record.prospect_id for record in repository.list_run_prospects(run_id="run-policy", country_code="BOG", season_start_year=2027, limit=None)}
    )
    assert unrelated.requested_prospect_count == repository.count_run_prospects(
        run_id="run-policy",
        country_code="BOG",
        season_start_year=2027,
    )
    assert repository.get_run_prospect(run_id="run-policy", prospect_id="future-season-prospect") == future_season_record
    assert "materialization_policy" in ger_records[0].profile_json
    assert ger_records[0].profile_json["materialization_policy"]["policy_fingerprint"]
