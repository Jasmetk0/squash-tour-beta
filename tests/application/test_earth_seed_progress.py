from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_package_builder import load_earth_research_bundle


def test_fifa_first_reviewed_country_histories_are_complete_and_resolvable():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    assert set(bundle.research.countries) == {"CZE", "SVK", "JPN", "IND", "MAR", "SEN", "FRO", "USA", "ZAF", "BRA", "DEU", "ISL", "SMR", "ARG", "MEX", "AUS", "NZL", "FJI", "PNG", "SLB", "COK", "ASM", "PYF", "NCL", "WSM", "TON", "VUT"}
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


def test_fifa_oceania_association_identity_batch_preserves_governance_and_territories():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    batch = {"ASM", "PYF", "NCL"}

    for code in batch:
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.method == "derived_estimate"
                assert rating.calibration_model_id == "fifa-earth-country-history-asm-pyf-ncl.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)
                assert "fifa-professional-2023" not in rating.source_ids

    asm = bundle.research.countries["ASM"]
    assert asm.years[2005].ratings["elite_support"].value < (
        asm.years[1998].ratings["elite_support"].value
    )
    assert asm.years[2007].ratings["elite_support"].value > (
        asm.years[2005].ratings["elite_support"].value
    )
    assert "fifa-structural-ofc-american-samoa-normalisation-v1#asm-normalisation-start-2005" in (
        asm.years[2005].ratings["elite_support"].observation_ids
    )

    pyf = bundle.research.countries["PYF"]
    assert pyf.years[2006].ratings["squash_access"].value >= 8.0
    assert pyf.years[2025].ratings["development_quality"].value > (
        pyf.years[2023].ratings["development_quality"].value
    )
    assert "fifa-structural-fifa-tahiti-development-2026-v1#pyf-talent-academy-2025" in (
        pyf.years[2025].ratings["development_quality"].observation_ids
    )
    assert "metropolitan France" in pyf.years[2026].territory_mapping_note

    ncl = bundle.research.countries["NCL"]
    assert ncl.years[1955].ratings["squash_tradition"].value >= 6.5
    assert "fifa-structural-fifa-new-caledonia-history-v1#ncl-league-launch-1928" in (
        ncl.years[1955].ratings["competition_quality"].observation_ids
    )
    assert "fifa-structural-ofc-new-caledonia-profile-v1#ncl-fifa-ofc-membership-2004" in (
        ncl.years[2004].ratings["elite_support"].observation_ids
    )
    assert ncl.years[2026].ratings["elite_support"].value > (
        ncl.years[2006].ratings["elite_support"].value
    )

    for code in ("PYF", "NCL"):
        history = bundle.research.countries[code]
        assert all(
            "france" not in item.lower()
            for year in history.years.values()
            for rating in year.ratings.values()
            for item in (*rating.source_ids, *rating.observation_ids)
        )



def test_fifa_wsm_ton_vut_batch_is_complete_and_dimensionally_temporal():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    batch = {"WSM", "TON", "VUT"}

    for code in batch:
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.method == "derived_estimate"
                assert rating.calibration_model_id == "fifa-earth-wsm-ton-vut-model.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    wsm = bundle.research.countries["WSM"]
    assert "backcast" in wsm.years[1955].ratings["squash_popularity"].rationale.lower()
    assert "fifa-big-count-2006-all-players-v2#samoa" not in (
        wsm.years[2005].ratings["squash_popularity"].observation_ids
    )
    assert "fifa-big-count-2006-all-players-v2#samoa" in (
        wsm.years[2006].ratings["squash_popularity"].observation_ids
    )
    assert wsm.years[2010].ratings["elite_support"].value < (
        wsm.years[2006].ratings["elite_support"].value
    )
    assert "fifa-structural-samoa-savaii-centre-2013-v1#wsm-savaii-centre-2013" in (
        wsm.years[2013].ratings["development_quality"].observation_ids
    )

    ton = bundle.research.countries["TON"]
    assert "backcast" in ton.years[1955].ratings["squash_access"].rationale.lower()
    assert "fifa-structural-tonga-vavau-2020-v1#ton-vavau-facility-2020" not in (
        ton.years[2019].ratings["squash_access"].observation_ids
    )
    assert "fifa-structural-tonga-vavau-2020-v1#ton-vavau-facility-2020" in (
        ton.years[2020].ratings["squash_access"].observation_ids
    )
    assert ton.years[2026].ratings["squash_popularity"].value < (
        ton.years[2026].ratings["squash_access"].value
    )
    assert "rugby" in ton.years[2026].ratings["squash_popularity"].rationale.lower()

    vut = bundle.research.countries["VUT"]
    assert "New Hebrides" in vut.years[1955].historical_entity
    assert "fifa-structural-ofc-vanuatu-profile-v1#vut-academy-pilot-start-2008" not in (
        vut.years[2007].ratings["development_quality"].observation_ids
    )
    assert "fifa-structural-ofc-vanuatu-profile-v1#vut-academy-pilot-start-2008" in (
        vut.years[2008].ratings["development_quality"].observation_ids
    )
    assert "fifa-structural-vanuatu-forward-2023-v1#vut-freshwater-stadium-2023" not in (
        vut.years[2022].ratings["elite_support"].observation_ids
    )
    assert "fifa-structural-vanuatu-forward-2023-v1#vut-freshwater-stadium-2023" in (
        vut.years[2023].ratings["elite_support"].observation_ids
    )
    assert "fifa-structural-ofc-vanuatu-profile-v1#vut-nations-cup-runner-up-2024" in (
        vut.years[2024].ratings["competition_quality"].observation_ids
    )

def test_fifa_pyf_backcasts_do_not_claim_future_infrastructure_as_historical_support():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    pyf = bundle.research.countries["PYF"]

    early = pyf.years[1955]
    for rating in early.ratings.values():
        assert "backcast" in rating.rationale.lower()
        assert "2023" not in rating.rationale
        assert "2025" not in rating.rationale
        assert all("pyf-artificial-pitch-2023" not in item for item in rating.observation_ids)
        assert all("pyf-talent-academy-2025" not in item for item in rating.observation_ids)

    assert "pyf-artificial-pitch-2023" in " ".join(
        pyf.years[2023].ratings["development_quality"].observation_ids
    )
    assert "pyf-talent-academy-2025" in " ".join(
        pyf.years[2025].ratings["development_quality"].observation_ids
    )
    assert "programme launch" in pyf.years[2025].ratings["development_quality"].rationale.lower()


def test_atp_complete_histories_are_evidence_resolvable_and_temporally_bounded():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))
    expected_countries = {"CZE", "DEU", "USA", "AUS", "ESP", "SRB", "FRA", "GBR", "ARG", "JPN", "CAN", "ITA", "NED", "SWE", "SUI", "CRO", "POL", "CHN"}
    assert set(bundle.research.countries) == expected_countries
    assert bundle.research.data_cutoff.isoformat() == "2026-10-04"
    assert len(bundle.datasets) == 58
    assert len(bundle.observations) == 212

    expected_models = {
        "CZE": "atp-earth-cze-deu-seed-model.v1",
        "DEU": "atp-earth-cze-deu-seed-model.v1",
        "USA": "atp-earth-usa-aus-esp-srb-model.v1",
        "AUS": "atp-earth-usa-aus-esp-srb-model.v1",
        "ESP": "atp-earth-usa-aus-esp-srb-model.v1",
        "SRB": "atp-earth-usa-aus-esp-srb-model.v1",
        "FRA": "atp-earth-fra-gbr-arg-jpn-model.v1",
        "GBR": "atp-earth-fra-gbr-arg-jpn-model.v1",
        "ARG": "atp-earth-fra-gbr-arg-jpn-model.v1",
        "JPN": "atp-earth-fra-gbr-arg-jpn-model.v1",
        "CAN": "atp-earth-can-ita-ned-swe-model.v1",
        "ITA": "atp-earth-can-ita-ned-swe-model.v1",
        "NED": "atp-earth-can-ita-ned-swe-model.v1",
        "SWE": "atp-earth-can-ita-ned-swe-model.v1",
        "SUI": "atp-earth-sui-cro-pol-chn-model.v1",
        "CRO": "atp-earth-sui-cro-pol-chn-model.v1",
        "POL": "atp-earth-sui-cro-pol-chn-model.v1",
        "CHN": "atp-earth-sui-cro-pol-chn-model.v1",
    }
    for code, history in bundle.research.countries.items():
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.method == "derived_estimate"
                assert rating.calibration_model_id == expected_models[code]
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
    assert bundle.research.countries["DEU"].years[2026].ratings["elite_support"].confidence == "medium"

    usa = bundle.research.countries["USA"]
    assert usa.years[1955].ratings["squash_popularity"].confidence == "low"
    assert "atp-usta-participation-2025-v1#usa-players-2025" not in (
        usa.years[1955].ratings["squash_popularity"].observation_ids
    )
    assert "atp-usta-participation-2025-v1#usa-players-2025" in (
        usa.years[2025].ratings["squash_popularity"].observation_ids
    )
    assert usa.years[2025].ratings["squash_popularity"].confidence == "medium"

    aus = bundle.research.countries["AUS"]
    assert aus.years[1955].ratings["competition_quality"].value == 10.0
    assert "partial" in aus.years[1955].territory_mapping_note.lower()
    assert "atp-aus-national-academy-2010-v1#aus-national-academy-support-2010" not in (
        aus.years[2009].ratings["development_quality"].observation_ids
    )
    assert "atp-aus-national-academy-2010-v1#aus-national-academy-support-2010" in (
        aus.years[2010].ratings["development_quality"].observation_ids
    )

    esp = bundle.research.countries["ESP"]
    assert esp.years[1965].ratings["competition_quality"].value > (
        esp.years[1955].ratings["competition_quality"].value
    )
    assert "atp-rfet-licences-2024-v1#esp-licences-2023-24" not in (
        esp.years[2023].ratings["squash_access"].observation_ids
    )
    assert "atp-rfet-licences-2024-v1#esp-licences-2023-24" in (
        esp.years[2024].ratings["squash_access"].observation_ids
    )

    srb = bundle.research.countries["SRB"]
    assert "Yugoslavia" in srb.years[1991].historical_entity
    assert srb.years[1992].ratings["elite_support"].value < (
        srb.years[1980].ratings["elite_support"].value
    )
    assert srb.years[2010].ratings["competition_quality"].value > (
        srb.years[2006].ratings["competition_quality"].value
    )
    assert "atp-tss-junior-support-2024-v1#srb-junior-support-and-missing-centre-2024" in (
        srb.years[2024].ratings["elite_support"].observation_ids
    )
    assert "missing national training centre" in (
        srb.years[2024].ratings["elite_support"].rationale.lower()
    )

    fra = bundle.research.countries["FRA"]
    assert "atp-fft-profile-2026-v1#fra-licences-2026" not in (
        fra.years[2025].ratings["squash_popularity"].observation_ids
    )
    assert "atp-fft-profile-2026-v1#fra-licences-2026" in (
        fra.years[2026].ratings["squash_popularity"].observation_ids
    )
    assert "atp-fft-dtn-history-v1#fra-first-dtn-1963" not in (
        fra.years[1962].ratings["development_quality"].observation_ids
    )
    assert "atp-fft-dtn-history-v1#fra-first-dtn-1963" in (
        fra.years[1963].ratings["development_quality"].observation_ids
    )

    gbr = bundle.research.countries["GBR"]
    assert "Northern Ireland" in gbr.years[2026].territory_mapping_note
    assert bundle.observations[
        "atp-lta-participation-2025-v1#gbr-adult-annual-2025"
    ].coverage_scope == "partial"
    assert bundle.observations[
        "atp-lta-participation-2025-v1#gbr-adult-annual-2025"
    ].territory_mapping_method == "current_country_partial_association_context"
    assert "atp-lta-participation-2025-v1#gbr-adult-annual-2025" not in (
        gbr.years[2024].ratings["squash_popularity"].observation_ids
    )
    assert "atp-lta-participation-2025-v1#gbr-adult-annual-2025" in (
        gbr.years[2025].ratings["squash_popularity"].observation_ids
    )

    arg = bundle.research.countries["ARG"]
    assert "atp-aat-profile-v1#arg-federated-players-current" not in (
        arg.years[2025].ratings["squash_access"].observation_ids
    )
    assert "atp-aat-profile-v1#arg-federated-players-current" in (
        arg.years[2026].ratings["squash_access"].observation_ids
    )
    assert "atp-arg-deta-2026-v1#arg-deta-interdisciplinary-support-2026" in (
        arg.years[2026].ratings["elite_support"].observation_ids
    )
    assert arg.years[2016].ratings["competition_quality"].value > (
        arg.years[2006].ratings["competition_quality"].value
    )

    jpn = bundle.research.countries["JPN"]
    assert jpn.years[2001].ratings["elite_support"].value < (
        jpn.years[2000].ratings["elite_support"].value
    )
    assert jpn.years[2008].ratings["elite_support"].value > (
        jpn.years[2001].ratings["elite_support"].value
    )
    assert "atp-jta-fuji-project-v1#jpn-male-top100-2017-2021" not in (
        jpn.years[2020].ratings["competition_quality"].observation_ids
    )
    assert "atp-jta-fuji-project-v1#jpn-male-top100-2017-2021" in (
        jpn.years[2021].ratings["competition_quality"].observation_ids
    )
    assert "decline" in jpn.years[2026].ratings["squash_popularity"].rationale.lower()

    can = bundle.research.countries["CAN"]
    assert "atp-tennis-canada-participation-2025-v1#can-players-2025" not in (
        can.years[2024].ratings["squash_popularity"].observation_ids
    )
    assert "atp-tennis-canada-participation-2025-v1#can-players-2025" in (
        can.years[2025].ratings["squash_popularity"].observation_ids
    )
    assert "atp-tennis-canada-ntc-v1#can-ntc-opened-2007" in (
        can.years[2007].ratings["development_quality"].observation_ids
    )

    ita = bundle.research.countries["ITA"]
    assert ita.years[2024].ratings["competition_quality"].value == 10.0
    assert "atp-fitp-junior-system-2025-v1#ita-federal-schools-2025" not in (
        ita.years[2024].ratings["development_quality"].observation_ids
    )
    assert "atp-fitp-junior-system-2025-v1#ita-federal-schools-2025" in (
        ita.years[2025].ratings["development_quality"].observation_ids
    )

    ned = bundle.research.countries["NED"]
    assert "combined tennis/padel" in ned.years[2026].ratings["squash_access"].rationale.lower()
    assert "atp-knltb-profile-v1#ned-members-current-2026" not in (
        ned.years[2025].ratings["squash_access"].observation_ids
    )
    assert "atp-knltb-profile-v1#ned-members-current-2026" in (
        ned.years[2026].ratings["squash_access"].observation_ids
    )

    swe = bundle.research.countries["SWE"]
    assert swe.years[1985].ratings["competition_quality"].value > (
        swe.years[2026].ratings["competition_quality"].value
    )
    assert swe.years[2026].ratings["squash_tradition"].value == 10.0
    assert "atp-svtf-annual-2025-v1#swe-rog-children-2025" not in (
        swe.years[2024].ratings["development_quality"].observation_ids
    )
    assert "atp-svtf-annual-2025-v1#swe-rog-children-2025" in (
        swe.years[2025].ratings["development_quality"].observation_ids
    )

    sui = bundle.research.countries["SUI"]
    assert "atp-swiss-tennis-profile-2026-v1#sui-members-2026" not in (
        sui.years[2025].ratings["squash_popularity"].observation_ids
    )
    assert "atp-swiss-tennis-profile-2026-v1#sui-members-2026" in (
        sui.years[2026].ratings["squash_popularity"].observation_ids
    )
    assert sui.years[2014].ratings["competition_quality"].value > (
        sui.years[1992].ratings["competition_quality"].value
    )

    cro = bundle.research.countries["CRO"]
    assert "Yugoslavia" in cro.years[1991].historical_entity
    assert cro.years[1992].historical_entity == "Croatia"
    assert "atp-hts-profile-v1#cro-itf-membership-1992" not in (
        cro.years[1991].ratings["squash_access"].observation_ids
    )
    assert "atp-hts-profile-v1#cro-itf-membership-1992" in (
        cro.years[1992].ratings["squash_access"].observation_ids
    )
    assert cro.years[2018].ratings["competition_quality"].value == 10.0

    pol = bundle.research.countries["POL"]
    assert "Polish People's Republic" in pol.years[1955].historical_entity
    assert "atp-pzt-history-v1#pol-dissolved-state-section-1951" in (
        pol.years[1955].ratings["elite_support"].observation_ids
    )
    assert "atp-pzt-training-2025-v1#pol-u12-training-2025" not in (
        pol.years[2024].ratings["development_quality"].observation_ids
    )
    assert "atp-pzt-training-2025-v1#pol-u12-training-2025" in (
        pol.years[2025].ratings["development_quality"].observation_ids
    )

    chn = bundle.research.countries["CHN"]
    assert "atp-china-ctj-2024-v1#chn-ranked-youth-2024" not in (
        chn.years[2023].ratings["development_quality"].observation_ids
    )
    assert "atp-china-ctj-2024-v1#chn-ranked-youth-2024" in (
        chn.years[2024].ratings["development_quality"].observation_ids
    )
    assert "atp-china-tennis-2025-review-v1#chn-men-top100-2025" not in (
        chn.years[2024].ratings["competition_quality"].observation_ids
    )
    assert "atp-china-tennis-2025-review-v1#chn-men-top100-2025" in (
        chn.years[2025].ratings["competition_quality"].observation_ids
    )
    assert chn.years[2026].ratings["development_quality"].value > (
        chn.years[2026].ratings["competition_quality"].value
    )

