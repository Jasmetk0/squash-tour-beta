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
