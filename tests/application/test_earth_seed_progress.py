from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_package_builder import load_earth_research_bundle


def test_fifa_first_reviewed_country_histories_are_complete_and_resolvable():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    assert set(bundle.research.countries) == {"CZE", "SVK", "JPN", "IND", "MAR", "SEN", "FRO", "USA", "ZAF", "BRA", "DEU", "ISL", "SMR", "ARG", "MEX", "AUS", "NZL", "FJI", "PNG", "SLB", "COK"}
    assert bundle.research.data_cutoff.isoformat() == "2026-10-03"

    for code in ("CZE", "SVK"):
        history = bundle.research.countries[code]
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


def test_fifa_second_reviewed_batch_is_complete_resolvable_and_preserves_conflicts():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    batch = {"JPN", "IND", "MAR", "SEN"}

    for code in batch:
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.method == "derived_estimate"
                assert rating.calibration_model_id == "fifa-earth-reviewed-country-history-jpn-ind-mar-sen.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    jpn = bundle.research.countries["JPN"]
    assert jpn.years[1977].ratings["development_quality"].confidence == "medium"
    assert "fifa-structural-jfa-history-v1#jpn-training-centre-1977" in (
        jpn.years[1977].ratings["development_quality"].observation_ids
    )

    ind = bundle.research.countries["IND"]
    assert ind.years[2023].ratings["development_quality"].confidence == "medium"

    mar = bundle.research.countries["MAR"]
    mar_development = mar.years[2020].ratings["development_quality"]
    assert mar_development.confidence == "low"
    assert {
        "fifa-structural-fifa-morocco-academy-2009-v1#mar-academy-established-2009",
        "fifa-structural-fifa-morocco-development-v1#mar-academy-opening-2019",
    }.issubset(set(mar_development.observation_ids))

    sen = bundle.research.countries["SEN"]
    assert sen.years[1955].ratings["squash_popularity"].confidence == "low"
    assert sen.years[2020].ratings["development_quality"].confidence == "medium"


def test_fifa_third_reviewed_batch_uses_shards_and_preserves_structural_breaks():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    batch = {"FRO", "USA", "ZAF"}

    for code in batch:
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.method == "derived_estimate"
                assert rating.calibration_model_id == "fifa-earth-reviewed-country-history-fro-usa-zaf.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    shard_root = Path("config/earth_research/countries/fifa_earth")
    assert all((shard_root / f"{code}.json").exists() for code in batch)

    fro = bundle.research.countries["FRO"]
    assert fro.years[1986].ratings["squash_access"].confidence == "medium"
    assert "fifa-structural-uefa-faroe-history-v1#fro-artificial-turf-1986" in (
        fro.years[1986].ratings["squash_access"].observation_ids
    )

    usa = bundle.research.countries["USA"]
    assert usa.years[1984].ratings["competition_quality"].value < (
        usa.years[1968].ratings["competition_quality"].value
    )
    assert usa.years[1996].ratings["competition_quality"].value > (
        usa.years[1984].ratings["competition_quality"].value
    )
    assert "fifa-structural-ussoccer-timeline-v1#usa-nasl-collapse-1984" in (
        usa.years[1984].ratings["competition_quality"].observation_ids
    )

    zaf = bundle.research.countries["ZAF"]
    assert zaf.years[1961].ratings["competition_quality"].value < (
        zaf.years[1955].ratings["competition_quality"].value
    )
    assert zaf.years[1992].ratings["competition_quality"].value > (
        zaf.years[1961].ratings["competition_quality"].value
    )
    assert "fifa-structural-caf-south-africa-v1#zaf-readmission-1992" in (
        zaf.years[1992].ratings["competition_quality"].observation_ids
    )


def test_fifa_heldout_batch_is_complete_independent_and_plausible():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    batch = {"BRA", "DEU", "ISL", "SMR"}
    ranking_prefix = "fifa-mens-year-end-ranking-2023-review-heldout-v1#"

    for code in batch:
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.method == "derived_estimate"
                assert rating.calibration_model_id == "fifa-earth-heldout-history-bra-deu-isl-smr.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)
                assert not any(item.startswith(ranking_prefix) for item in rating.observation_ids)

    competition_2023 = {
        code: bundle.research.countries[code].years[2023].ratings["competition_quality"].value
        for code in batch
    }
    assert competition_2023["BRA"] > competition_2023["DEU"] > competition_2023["ISL"] > competition_2023["SMR"]

    rank_2023 = {
        code: bundle.observations[f"{ranking_prefix}{code.lower()}"].numeric_value
        for code in batch
    }
    assert rank_2023 == {"BRA": 5.0, "DEU": 16.0, "ISL": 71.0, "SMR": 210.0}

    assert bundle.research.countries["DEU"].years[1955].historical_entity.startswith(
        "Federal Republic of Germany"
    )
    assert bundle.research.countries["SMR"].years[2006].ratings["squash_access"].value >= 9.0
    assert all(
        "fifa-professional-2023" not in rating.source_ids
        for year in bundle.research.countries["SMR"].years.values()
        for rating in year.ratings.values()
    )


def test_fifa_arg_mex_aus_nzl_batch_loads_sharded_sources_manifests_and_histories():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    batch = {"ARG", "MEX", "AUS", "NZL"}
    expected_datasets = {
        "fifa-structural-afa-history-v1",
        "fifa-structural-fmf-history-v1",
        "fifa-structural-football-australia-history-v1",
        "fifa-structural-ofc-new-zealand-history-v1",
        "fifa-structural-ofc-new-zealand-grassroots-2011-v1",
    }
    expected_sources = {
        "afa-history",
        "fmf-history",
        "football-australia-history",
        "ofc-new-zealand-history",
        "ofc-new-zealand-grassroots-2011",
    }

    assert expected_datasets <= bundle.datasets.keys()
    assert expected_sources <= bundle.research.sources.keys()

    for code in batch:
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.method == "derived_estimate"
                assert rating.calibration_model_id == "fifa-earth-country-history-arg-mex-aus-nzl.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    arg = bundle.research.countries["ARG"]
    assert arg.years[2023].ratings["competition_quality"].value >= 9.0
    assert arg.years[1955].ratings["squash_tradition"].value >= 8.5

    mex = bundle.research.countries["MEX"]
    assert mex.years[2006].ratings["squash_popularity"].value > (
        mex.years[2006].ratings["squash_access"].value
    )
    assert "fifa-structural-fmf-history-v1#mex-world-cup-host-1970" in (
        mex.years[1970].ratings["elite_support"].observation_ids
    )

    aus = bundle.research.countries["AUS"]
    assert aus.years[1960].ratings["elite_support"].value < aus.years[1955].ratings["elite_support"].value
    assert aus.years[1963].ratings["elite_support"].value > aus.years[1960].ratings["elite_support"].value
    assert aus.years[2005].ratings["competition_quality"].value > (
        aus.years[2004].ratings["competition_quality"].value
    )
    assert "fifa-structural-football-australia-history-v1#aus-a-league-launch-2005" in (
        aus.years[2005].ratings["competition_quality"].observation_ids
    )

    nzl = bundle.research.countries["NZL"]
    assert nzl.years[2011].ratings["development_quality"].value > (
        nzl.years[2006].ratings["development_quality"].value
    )
    assert "fifa-structural-ofc-new-zealand-grassroots-2011-v1#nzl-foundation-development-grants-2011" in (
        nzl.years[2011].ratings["development_quality"].observation_ids
    )


def test_fifa_oceania_sparse_batch_preserves_access_scale_and_missingness():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    batch = {"FJI", "PNG", "SLB", "COK"}

    for code in batch:
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.method == "derived_estimate"
                assert rating.calibration_model_id == "fifa-earth-country-history-fji-png-slb-cok.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    fji = bundle.research.countries["FJI"]
    assert fji.years[2006].ratings["squash_access"].value >= 8.0
    assert fji.years[2026].ratings["elite_support"].value > fji.years[2023].ratings["elite_support"].value
    assert {
        "fifa-professional-2023-players-v2#fiji-p189",
        "fifa-professional-2023-clubs-v2#fiji-p189",
    }.issubset(set(fji.years[2023].ratings["competition_quality"].observation_ids))

    png = bundle.research.countries["PNG"]
    assert png.years[2006].ratings["squash_access"].value < fji.years[2006].ratings["squash_access"].value
    assert "fifa-structural-ofc-png-profile-v1#png-geography-development-constraint" in (
        png.years[2026].ratings["squash_access"].observation_ids
    )

    slb = bundle.research.countries["SLB"]
    assert slb.years[2026].ratings["squash_popularity"].value >= 9.0
    assert slb.years[2026].ratings["squash_popularity"].value > (
        slb.years[2026].ratings["competition_quality"].value
    )
    assert slb.years[1955].ratings["squash_tradition"].confidence == "low"

    cok = bundle.research.countries["COK"]
    assert cok.years[2006].ratings["squash_access"].value >= 8.5
    assert cok.years[2006].ratings["squash_access"].value > (
        cok.years[2006].ratings["competition_quality"].value + 4.0
    )

    for code in ("PNG", "SLB", "COK"):
        assert all(
            "fifa-professional-2023" not in rating.source_ids
            for year in bundle.research.countries[code].years.values()
            for rating in year.ratings.values()
        )


def test_atp_first_complete_histories_are_evidence_resolvable_and_conservative():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))
    assert set(bundle.research.countries) == {"CZE", "DEU"}
    assert bundle.research.data_cutoff.isoformat() == "2026-10-04"
    assert len(bundle.datasets) == 8
    assert len(bundle.observations) == 33

    for code, history in bundle.research.countries.items():
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.method == "derived_estimate"
                assert rating.calibration_model_id == "atp-earth-cze-deu-seed-model.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    cze_players = bundle.observations["itf-2019-cze-national-snapshot-v1#players"]
    deu_coaches = bundle.observations["itf-2019-deu-national-snapshot-v1#coaches"]
    assert cze_players.sex_scope == "mixed"
    assert cze_players.observation_year is None
    assert deu_coaches.observation_year is None
    assert "count_not_quality_measure" in deu_coaches.quality_flags

    assert bundle.research.countries["CZE"].years[1955].ratings["squash_popularity"].confidence == "low"
    assert bundle.research.countries["CZE"].years[2025].ratings["development_quality"].confidence == "medium"
    assert bundle.research.countries["DEU"].years[1955].historical_entity.startswith("Federal Republic")
    assert bundle.research.countries["DEU"].years[1955].ratings["squash_popularity"].confidence == "low"
    assert bundle.research.countries["DEU"].years[2026].ratings["elite_support"].confidence == "medium"
