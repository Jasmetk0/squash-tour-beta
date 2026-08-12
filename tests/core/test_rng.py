import pytest

from beta_engine.core import (
    DeterministicRng,
    SeedPath,
    SeedScope,
    derive_child_seed,
    derive_seed_hierarchy,
)


def test_same_seed_and_inputs_produce_same_sequence() -> None:
    rng_a = DeterministicRng(2027)
    rng_b = DeterministicRng(2027)

    output_a = [rng_a.random(), rng_a.randint(1, 100), rng_a.uniform(0.0, 1.0)]
    output_b = [rng_b.random(), rng_b.randint(1, 100), rng_b.uniform(0.0, 1.0)]

    assert output_a == output_b


def test_different_derived_scopes_are_stable_and_distinct() -> None:
    season_seed = derive_child_seed(999, SeedScope.SEASON, 2030)
    week_seed = derive_child_seed(season_seed, SeedScope.WEEK, 12)
    match_seed = derive_child_seed(week_seed, SeedScope.MATCH, "2030-W12-M3")

    assert season_seed.value != week_seed.value
    assert week_seed.value != match_seed.value

    assert derive_child_seed(999, SeedScope.SEASON, 2030) == season_seed
    assert derive_child_seed(season_seed, SeedScope.WEEK, 12) == week_seed
    assert derive_child_seed(week_seed, SeedScope.MATCH, "2030-W12-M3") == match_seed


def test_hierarchy_derivation_is_reproducible() -> None:
    path = SeedPath(season=2028, week=7, match="QF-2")

    first = derive_seed_hierarchy(12345, path)
    second = derive_seed_hierarchy(12345, path)

    assert first == second
    assert list(first.keys()) == [
        SeedScope.GLOBAL,
        SeedScope.SEASON,
        SeedScope.WEEK,
        SeedScope.MATCH,
    ]


@pytest.mark.smoke
def test_branching_rng_uses_deterministic_child_seed() -> None:
    root_a = DeterministicRng(555)
    root_b = DeterministicRng(555)

    branch_a = root_a.branch(SeedScope.SEASON, 2031)
    branch_b = root_b.branch(SeedScope.SEASON, 2031)

    assert branch_a.seed == branch_b.seed
    assert [branch_a.randint(0, 10) for _ in range(4)] == [
        branch_b.randint(0, 10) for _ in range(4)
    ]
