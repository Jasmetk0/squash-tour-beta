"""Season configuration contract for canonical World Tour Finals Race."""

import pytest

from beta_engine.domain.finals import WorldTourFinalsRaceConfiguration
from beta_engine.domain.rankings.official import RankingWeek


def fp(char: str) -> str:
    return char * 64


def configuration(**updates) -> WorldTourFinalsRaceConfiguration:
    values = dict(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
        finals_event_id="FINALS",
        eligible_categories=("DIAMOND", "WORLD_CHAMPIONSHIP"),
        best_n=5,
        cutoff_week=RankingWeek(season_index=0, week=50),
        cutoff_official_ranking_fingerprint=fp("a"),
        cutoff_transition_fingerprint=fp("b"),
        calendar_content_fingerprint=fp("c"),
        adopted_by_command_id="configure-finals-race",
    )
    values.update(updates)
    return WorldTourFinalsRaceConfiguration(**values)


@pytest.mark.pr_critical
def test_configuration_freezes_season_scope_and_stable_eligibility_identity():
    first = configuration()
    reopened = WorldTourFinalsRaceConfiguration.model_validate_json(
        first.model_dump_json()
    )

    assert reopened == first
    assert reopened.fingerprint == first.fingerprint
    assert reopened.eligibility_fingerprint == first.eligibility_fingerprint

    different_best_n = configuration(best_n=6)
    assert different_best_n.fingerprint != first.fingerprint
    assert (
        different_best_n.eligibility_fingerprint
        == first.eligibility_fingerprint
    )

    different_categories = configuration(eligible_categories=("DIAMOND",))
    assert (
        different_categories.eligibility_fingerprint
        != first.eligibility_fingerprint
    )


@pytest.mark.pr_critical
def test_configuration_rejects_cross_season_or_noncanonical_categories():
    with pytest.raises(ValueError, match="configured season"):
        configuration(cutoff_week=RankingWeek(season_index=1, week=1))

    with pytest.raises(ValueError, match="unique, sorted and non-empty"):
        configuration(eligible_categories=("WORLD_CHAMPIONSHIP", "DIAMOND"))

    with pytest.raises(ValueError, match="unique, sorted and non-empty"):
        configuration(eligible_categories=("DIAMOND", "DIAMOND"))

    with pytest.raises(ValueError, match="normalized"):
        configuration(eligible_categories=(" DIAMOND ",))
