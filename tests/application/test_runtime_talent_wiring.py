from __future__ import annotations

from collections import Counter

from beta_engine.application.api_services import SimulationApiService
from beta_engine.domain.countries import Country
from beta_engine.domain.players import AnnualTalentClassPlanner, TalentQualityBand
from beta_engine.infrastructure.db import DatabaseSettings, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository


def _service(tmp_path) -> SimulationApiService:
    db_file = tmp_path / "runtime_talent_wiring.db"
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{db_file}"))
    session_factory = create_session_factory(engine)
    repository = SimulationPersistenceRepository(engine=engine, session_factory=session_factory)
    return SimulationApiService(repository=repository)


def _country(*, code: str, population: int, strength: int) -> Country:
    return Country(
        code=code,
        name=code,
        flag_asset=None,
        region="TEST",
        population=population,
        squash_popularity=strength,
        squash_access=strength,
        development_quality=strength,
        competition_quality=strength,
        elite_support=strength,
        squash_tradition=strength,
    )


def _overall(player) -> float:
    return (
        player.technique
        + player.movement
        + player.physical
        + player.mental
        + player.consistency
        + player.clutch
        + player.recovery
    ) / 7.0


def test_runtime_generation_is_deterministic_for_same_seed_and_season(tmp_path) -> None:
    service = _service(tmp_path)
    countries = [
        _country(code="AAA", population=90_000_000, strength=4),
        _country(code="BBB", population=120_000_000, strength=2),
    ]

    left = [player.model_dump() for player in service._build_players(seed=2027, season=2031, countries=countries)]
    right = [player.model_dump() for player in service._build_players(seed=2027, season=2031, countries=countries)]

    assert left == right


def test_runtime_generation_changes_when_season_changes(tmp_path) -> None:
    service = _service(tmp_path)
    countries = [
        _country(code="AAA", population=90_000_000, strength=4),
        _country(code="BBB", population=120_000_000, strength=2),
    ]

    season_2031 = [player.model_dump() for player in service._build_players(seed=2027, season=2031, countries=countries)]
    season_2032 = [player.model_dump() for player in service._build_players(seed=2027, season=2032, countries=countries)]

    assert season_2031 != season_2032


def test_runtime_generation_no_longer_uses_equal_fixed_count_per_country(tmp_path) -> None:
    service = _service(tmp_path)
    countries = [
        _country(code="AAA", population=45_000_000, strength=4),
        _country(code="BBB", population=300_000_000, strength=2),
        _country(code="CCC", population=90_000_000, strength=3),
    ]

    players = service._build_players(seed=5151, season=2030, countries=countries)
    per_country = Counter(player.nationality for player in players)

    assert len(set(per_country.values())) > 1


def test_stronger_country_realises_better_top_end_runtime_players(tmp_path) -> None:
    service = _service(tmp_path)
    strong = _country(code="STR", population=55_000_000, strength=5)
    weak = _country(code="WEK", population=55_000_000, strength=1)

    players = service._build_players(seed=9191, season=2040, countries=[strong, weak])
    strong_players = sorted(
        [player for player in players if player.nationality == "STR"], key=_overall, reverse=True
    )
    weak_players = sorted(
        [player for player in players if player.nationality == "WEK"], key=_overall, reverse=True
    )

    # Country V1 improves realised development, not innate quality-band odds.
    assert _overall(strong_players[0]) > _overall(weak_players[0]) + 6.0


def test_population_affects_volume_without_absurd_domination_in_runtime(tmp_path) -> None:
    service = _service(tmp_path)
    huge_mid = _country(code="HUG", population=1_300_000_000, strength=3)
    small_mid = _country(code="SML", population=65_000_000, strength=3)

    players = service._build_players(seed=1010, season=2042, countries=[huge_mid, small_mid])
    per_country = Counter(player.nationality for player in players)

    assert per_country["HUG"] > per_country["SML"]
    assert per_country["HUG"] / per_country["SML"] < 3.5


def test_generational_talent_is_rare_and_exceptional_in_runtime(tmp_path) -> None:
    service = _service(tmp_path)
    planner = AnnualTalentClassPlanner()
    countries = [
        _country(code="AAA", population=120_000_000, strength=4),
        _country(code="BBB", population=95_000_000, strength=3),
        _country(code="CCC", population=180_000_000, strength=2),
    ]

    total_players = 0
    generational_players = []
    non_generational_players = []
    for season in range(2030, 2090):
        plan = planner.plan(year=season, seed=7777, countries=countries)
        generational_ids = {
            f"{allocation.country_code}-{talent.sequence:05d}"
            for allocation in plan.allocations
            for talent in allocation.talents
            if talent.quality_band == TalentQualityBand.GENERATIONAL
        }
        players = service._build_players(seed=7777, season=season, countries=countries)
        total_players += len(players)
        for player in players:
            if player.player_id in generational_ids:
                generational_players.append(player)
            else:
                non_generational_players.append(player)

    assert generational_players
    assert len(generational_players) / total_players < 0.006
    assert sum(_overall(player) for player in generational_players) / len(generational_players) > (
        sum(_overall(player) for player in non_generational_players) / len(non_generational_players)
    ) + 8.0
