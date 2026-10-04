from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_package_builder import load_earth_research_bundle


def test_fifa_first_reviewed_country_histories_are_complete_and_resolvable():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    assert set(bundle.research.countries) == {"CZE", "SVK"}
    assert bundle.research.data_cutoff.isoformat() == "2026-10-04"

    for code, history in bundle.research.countries.items():
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        assert history.years[1955].historical_entity
        assert history.years[2026].historical_entity
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.method == "derived_estimate"
                assert rating.calibration_model_id == "fifa-earth-reviewed-country-history-cze-svk.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    assert bundle.research.countries["CZE"].years[2006].ratings["squash_access"].confidence == "medium"
    assert bundle.research.countries["SVK"].years[2018].ratings["development_quality"].confidence == "medium"


def test_atp_first_itf_normalized_slice_is_registered_without_overclaiming_year_or_sex():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))
    assert bundle.research.countries == {}
    assert set(bundle.datasets) == {
        "itf-2019-cze-national-snapshot-v1",
        "itf-2019-deu-national-snapshot-v1",
    }
    assert len(bundle.observations) == 6

    cze_players = bundle.observations["itf-2019-cze-national-snapshot-v1#players"]
    deu_coaches = bundle.observations["itf-2019-deu-national-snapshot-v1#coaches"]
    assert cze_players.earth_country_code == "CZE"
    assert cze_players.sex_scope == "mixed"
    assert cze_players.observation_year is None
    assert deu_coaches.earth_country_code == "DEU"
    assert deu_coaches.observation_year is None
    assert "count_not_quality_measure" in deu_coaches.quality_flags
