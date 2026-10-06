from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_package_builder import load_earth_research_bundle


def test_fifa_first_reviewed_country_histories_are_complete_and_resolvable():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    assert set(bundle.research.countries) == {"CZE", "SVK", "JPN", "IND", "MAR", "SEN", "FRO", "USA", "ZAF", "BRA", "DEU", "ISL", "SMR", "ARG", "MEX", "AUS", "NZL", "FJI", "PNG", "SLB", "COK", "ASM", "PYF", "NCL", "WSM", "TON", "VUT", "FRA", "ESP", "ITA", "NLD", "BEL", "PRT", "AUT", "DNK", "SWE", "CHE", "NOR", "FIN", "HRV", "SVN", "POL", "ROU", "UKR", "LTU", "LVA", "EST", "CAN", "GRC", "SRB", "CHL", "HUN", "ISR", "BGR", "KAZ", "CHN", "TUR", "KOR", "THA", "COL", "CYP", "ECU", "IRL", "EGY", "MYS", "SAU", "ARE", "QAT", "OMN", "GHA", "NGA", "KEN", "UGA", "TZA", "ZMB", "ZWE", "MWI", "BWA", "NAM", "SWZ", "MOZ", "ANG", "LES", "CMR", "BEN", "GAB", "MUS", "MDG", "SEY", "RWA", "BDI", "GAM", "CPV", "DJI", "COM", "EQG", "GNB", "STP", "GIN", "LBR", "SLE", "TGO", "BFA", "MLI", "MRT", "NER", "CHA", "ETH", "ERI", "SDN", "SSD", "DZA", "CIV", "TUN", "LBY"}
    assert bundle.research.data_cutoff.isoformat() == "2026-10-03"
    assert len(bundle.research.countries) == 115
    assert len(bundle.datasets) == 162
    assert len(bundle.observations) == 1759

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


def test_fifa_fra_esp_batch_is_complete_and_temporally_dimensioned():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))

    for code in ("FRA", "ESP"):
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.calibration_model_id == "fifa-earth-country-history-fra-esp.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    fra = bundle.research.countries["FRA"]
    assert "fifa-structural-fff-history-v1#fra-dtn-training-plan-1970" not in fra.years[1969].ratings["development_quality"].observation_ids
    assert "fifa-structural-fff-history-v1#fra-dtn-training-plan-1970" in fra.years[1970].ratings["development_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#france" not in fra.years[2005].ratings["squash_popularity"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#france" in fra.years[2006].ratings["squash_popularity"].observation_ids
    assert "fifa-professional-2023-players-v2#france-p221" not in fra.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-players-v2#france-p221" in fra.years[2023].ratings["competition_quality"].observation_ids

    esp = bundle.research.countries["ESP"]
    assert "fifa-structural-rfef-ciudad-futbol-v1#esp-ciudad-inaugurated-2003" not in esp.years[2002].ratings["development_quality"].observation_ids
    assert "fifa-structural-rfef-ciudad-futbol-v1#esp-ciudad-inaugurated-2003" in esp.years[2003].ratings["development_quality"].observation_ids
    assert "fifa-structural-rfef-talent-development-2026-v1#esp-national-talent-process-2026" not in esp.years[2025].ratings["development_quality"].observation_ids
    assert "fifa-structural-rfef-talent-development-2026-v1#esp-national-talent-process-2026" in esp.years[2026].ratings["development_quality"].observation_ids
    assert "fifa-big-count-2006-clubs-v2#spain" in esp.years[2006].ratings["squash_access"].observation_ids


def test_atp_complete_histories_are_evidence_resolvable_and_temporally_bounded():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))
    expected_countries = {"CZE", "DEU", "USA", "AUS", "ESP", "SRB", "FRA", "GBR", "ARG", "JPN", "CAN", "ITA", "NED", "SWE", "SUI", "CRO", "POL", "CHN", "NOR", "GRE", "BEL", "ZAF", "DEN", "FIN", "NZL", "PRT", "IRL", "HUN", "ROU", "SVN", "SVK", "ISR", "BGR", "AUT", "TUR", "CYP", "BRA", "CHL", "COL", "MEX", "ECU", "IND", "KOR", "THA", "KAZ", "LVA", "EST", "LTU", "UKR", "MAR", "SEN", "ISL", "SMR", "FRO", "FJI", "PNG", "WSM", "SLB", "TON", "COK", "NCL", "ASM", "VUT", "EGY", "MYS", "PHL", "IDN", "SGP", "PAK", "GHA", "NGA", "KEN", "UGA", "TZA", "ZMB", "ZWE", "MWI", "BWA", "NAM", "SWZ", "MOZ", "ANG", "LES", "CMR", "BEN", "GAB", "MUS", "MDG", "SEY", "RWA", "BDI", "GAM", "CPV", "DJI", "COM", "EQG", "GNB", "STP", "GIN", "LBR", "SLE", "TGO", "BFA", "MLI", "MRT", "NER", "CHA", "ETH", "ERI", "SDN", "SSD", "DZA", "CIV", "TUN", "LBY"}
    assert set(bundle.research.countries) == expected_countries
    assert bundle.research.data_cutoff.isoformat() == "2026-10-04"
    assert len(bundle.datasets) == 333
    assert len(bundle.observations) == 735

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
        "NOR": "atp-earth-nor-gre-bel-rsa-model.v1",
        "GRE": "atp-earth-nor-gre-bel-rsa-model.v1",
        "BEL": "atp-earth-nor-gre-bel-rsa-model.v1",
        "ZAF": "atp-earth-nor-gre-bel-rsa-model.v1",
        "DEN": "atp-earth-den-fin-nzl-model.v1",
        "FIN": "atp-earth-den-fin-nzl-model.v1",
        "NZL": "atp-earth-den-fin-nzl-model.v1",
        "PRT": "atp-earth-prt-irl-model.v1",
        "IRL": "atp-earth-prt-irl-model.v1",
        "HUN": "atp-earth-hun-rou-model.v1",
        "ROU": "atp-earth-hun-rou-model.v1",
        "SVN": "atp-earth-svn-model.v1",
        "SVK": "atp-earth-svk-model.v1",
        "ISR": "atp-earth-isr-bgr-model.v1",
        "BGR": "atp-earth-isr-bgr-model.v1",
        "AUT": "atp-earth-aut-model.v1",
        "TUR": "atp-earth-tur-cyp-model.v1",
        "CYP": "atp-earth-tur-cyp-model.v1",
        "BRA": "atp-earth-bra-chl-model.v1",
        "CHL": "atp-earth-bra-chl-model.v1",
        "COL": "atp-earth-col-mex-model.v1",
        "MEX": "atp-earth-col-mex-model.v1",
        "ECU": "atp-earth-ecu-ind-model.v1",
        "IND": "atp-earth-ecu-ind-model.v1",
        "KOR": "atp-earth-kor-tha-model.v1",
        "THA": "atp-earth-kor-tha-model.v1",
        "KAZ": "atp-earth-kaz-model.v1",
        "LVA": "atp-earth-lva-est-model.v1",
        "EST": "atp-earth-lva-est-model.v1",
        "LTU": "atp-earth-ltu-model.v1",
        "UKR": "atp-earth-ukr-model.v1",
        "MAR": "atp-earth-mar-model.v1",
        "SEN": "atp-earth-sen-model.v1",
        "ISL": "atp-earth-isl-model.v1",
        "SMR": "atp-earth-smr-model.v1",
        "FRO": "atp-earth-fro-model.v1",
        "FJI": "atp-earth-fji-model.v1",
        "PNG": "atp-earth-png-model.v1",
        "WSM": "atp-earth-wsm-model.v1",
        "SLB": "atp-earth-slb-model.v1",
        "TON": "atp-earth-ton-model.v1",
        "COK": "atp-earth-cok-model.v1",
        "NCL": "atp-earth-ncl-model.v1",
        "ASM": "atp-earth-asm-model.v1",
        "VUT": "atp-earth-vut-model.v1",
        "EGY": "atp-earth-egy-model.v1",
        "MYS": "atp-earth-mys-model.v1",
        "PHL": "atp-earth-phl-model.v1",
        "IDN": "atp-earth-idn-model.v1",
        "SGP": "atp-earth-sgp-model.v1",
        "PAK": "atp-earth-pak-model.v1",
        "GHA": "atp-earth-gha-model.v1",
        "NGA": "atp-earth-nga-model.v1",
        "KEN": "atp-earth-ken-model.v1",
        "UGA": "atp-earth-uga-model.v1",
        "TZA": "atp-earth-tza-model.v1",
        "ZMB": "atp-earth-zmb-model.v1",
        "ZWE": "atp-earth-zwe-model.v1",
        "MWI": "atp-earth-mwi-model.v1",
        "BWA": "atp-earth-bwa-model.v1",
        "NAM": "atp-earth-nam-model.v1",
        "SWZ": "atp-earth-swz-model.v1",
        "MOZ": "atp-earth-moz-model.v1",
        "ANG": "atp-earth-ang-model.v1",
        "LES": "atp-earth-les-model.v1",
        "CMR": "atp-earth-cmr-model.v1",
        "BEN": "atp-earth-ben-model.v1",
        "GAB": "atp-earth-gab-model.v1",
        "MUS": "atp-earth-mus-model.v1",
        "MDG": "atp-earth-mdg-model.v1",
        "SEY": "atp-earth-sey-model.v1",
        "RWA": "atp-earth-rwa-model.v1",
        "BDI": "atp-earth-bdi-model.v1",
        "GAM": "atp-earth-gam-model.v1",
        "CPV": "atp-earth-cpv-model.v1",
        "DJI": "atp-earth-dji-model.v1",
        "COM": "atp-earth-com-model.v1",
        "EQG": "atp-earth-eqg-model.v1",
        "GNB": "atp-earth-gnb-model.v1",
        "STP": "atp-earth-stp-model.v1",
        "GIN": "atp-earth-gin-model.v1",
        "LBR": "atp-earth-lbr-model.v1",
        "SLE": "atp-earth-sle-model.v1",
        "TGO": "atp-earth-tgo-model.v1",
        "BFA": "atp-earth-bfa-model.v1",
        "MLI": "atp-earth-mli-model.v1",
        "MRT": "atp-earth-mrt-model.v1",
        "NER": "atp-earth-ner-model.v1",
        "CHA": "atp-earth-cha-model.v1",
        "ETH": "atp-earth-eth-model.v1",
        "ERI": "atp-earth-eri-model.v1",
        "SDN": "atp-earth-sdn-model.v1",
        "SSD": "atp-earth-ssd-model.v1",
        "DZA": "atp-earth-dza-model.v1",
        "CIV": "atp-earth-civ-model.v1",
        "TUN": "atp-earth-tun-model.v1",
        "LBY": "atp-earth-lby-model.v1",
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

    nor = bundle.research.countries["NOR"]
    assert "atp-ntpf-profile-v1#nor-clubs-2022" not in (
        nor.years[2021].ratings["squash_access"].observation_ids
    )
    assert "atp-ntpf-profile-v1#nor-clubs-2022" in (
        nor.years[2022].ratings["squash_access"].observation_ids
    )
    assert nor.years[2022].ratings["competition_quality"].value > (
        nor.years[2015].ratings["competition_quality"].value
    )

    gre = bundle.research.countries["GRE"]
    assert "atp-greece-clubs-2026-v1#gre-member-clubs-2026" not in (
        gre.years[2025].ratings["squash_access"].observation_ids
    )
    assert "atp-greece-clubs-2026-v1#gre-member-clubs-2026" in (
        gre.years[2026].ratings["squash_access"].observation_ids
    )
    assert gre.years[2021].ratings["competition_quality"].value > (
        gre.years[2015].ratings["competition_quality"].value
    )

    bel = bundle.research.countries["BEL"]
    assert bundle.observations[
        "atp-tennis-vlaanderen-scale-2026-v1#bel-flanders-members-2026"
    ].coverage_scope == "partial"
    assert "combined_tennis_padel" in bundle.observations[
        "atp-tennis-vlaanderen-scale-2026-v1#bel-flanders-members-2026"
    ].quality_flags
    assert "atp-tennis-vlaanderen-scale-2026-v1#bel-flanders-members-2026" not in (
        bel.years[2025].ratings["squash_access"].observation_ids
    )
    assert "atp-tennis-vlaanderen-scale-2026-v1#bel-flanders-members-2026" in (
        bel.years[2026].ratings["squash_access"].observation_ids
    )

    zaf = bundle.research.countries["ZAF"]
    assert "Union of South Africa" in zaf.years[1955].historical_entity
    assert "atp-tsa-development-v1#zaf-development-centres-2019" not in (
        zaf.years[2018].ratings["development_quality"].observation_ids
    )
    assert "atp-tsa-development-v1#zaf-development-centres-2019" in (
        zaf.years[2019].ratings["development_quality"].observation_ids
    )
    assert zaf.years[2018].ratings["competition_quality"].value > (
        zaf.years[2026].ratings["competition_quality"].value
    )

    nor = bundle.research.countries["NOR"]
    assert "atp-casper-ruud-v1#nor-first-atp-title-2020" not in (
        nor.years[2019].ratings["competition_quality"].observation_ids
    )
    assert "atp-casper-ruud-v1#nor-first-atp-title-2020" in (
        nor.years[2020].ratings["competition_quality"].observation_ids
    )
    assert nor.years[2022].ratings["competition_quality"].value > (
        nor.years[2015].ratings["competition_quality"].value
    )

    gre = bundle.research.countries["GRE"]
    assert "atp-tsitsipas-v1#gre-atp-finals-title-2019" not in (
        gre.years[2018].ratings["competition_quality"].observation_ids
    )
    assert "atp-tsitsipas-v1#gre-atp-finals-title-2019" in (
        gre.years[2019].ratings["competition_quality"].observation_ids
    )
    assert "atp-greece-clubs-2026-v1#gre-member-clubs-2026" not in (
        gre.years[2025].ratings["squash_access"].observation_ids
    )

    bel = bundle.research.countries["BEL"]
    assert bundle.observations[
        "atp-tennis-vlaanderen-scale-2026-v1#bel-flanders-members-2026"
    ].coverage_scope == "partial"
    assert bundle.observations[
        "atp-tennis-vlaanderen-scale-2026-v1#bel-flanders-members-2026"
    ].territory_mapping_method == "current_country_partial_association_context"
    assert "partial Belgium coverage" in (
        bel.years[2026].ratings["squash_access"].rationale
    )
    assert "atp-tennis-vlaanderen-scale-2026-v1#bel-flanders-members-2026" not in (
        bel.years[2025].ratings["squash_access"].observation_ids
    )

    zaf = bundle.research.countries["ZAF"]
    assert "Union of South Africa" in zaf.years[1955].historical_entity
    assert zaf.years[2018].ratings["competition_quality"].value > (
        zaf.years[2026].ratings["competition_quality"].value
    )
    assert "atp-tsa-development-v1#zaf-development-centres-2019" not in (
        zaf.years[2018].ratings["development_quality"].observation_ids
    )
    assert "atp-tsa-development-v1#zaf-development-centres-2019" in (
        zaf.years[2019].ratings["development_quality"].observation_ids
    )



def test_atp_source_scopes_and_current_competition_quality_are_semantically_guarded():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    aus_booking = bundle.observations["atp-aus-court-hire-2024-v1#aus-booking-hours-2024"]
    assert aus_booking.sex_scope == "mixed"
    assert aus_booking.age_scope is None
    assert "broad_public_use" in aus_booking.quality_flags

    bel_clubs = bundle.observations["atp-tennis-vlaanderen-scale-2026-v1#bel-flanders-clubs-2026"]
    bel_members = bundle.observations["atp-tennis-vlaanderen-scale-2026-v1#bel-flanders-members-2026"]
    assert bel_clubs.source_entity == "Tennis en Padel Vlaanderen"
    assert bel_members.source_entity == "Tennis en Padel Vlaanderen"
    assert bel_clubs.coverage_scope == "partial"
    assert "combined_tennis_padel" in bel_clubs.quality_flags

    nor = bundle.research.countries["NOR"].years[2026].ratings["competition_quality"]
    gre = bundle.research.countries["GRE"].years[2026].ratings["competition_quality"]
    bel = bundle.research.countries["BEL"].years[2026].ratings["competition_quality"]
    zaf = bundle.research.countries["ZAF"].years[2026].ratings["competition_quality"]

    assert nor.value == 7.4
    assert gre.value == 7.4
    assert bel.value == 7.7
    assert zaf.value == 7.2
    assert nor.confidence == gre.confidence == bel.confidence == "low"
    assert zaf.confidence == "medium"

    assert "atp-ntpf-profile-v1#nor-clubs-2022" in nor.observation_ids
    assert "atp-greece-clubs-2026-v1#gre-member-clubs-2026" in gre.observation_ids
    assert "atp-tennis-vlaanderen-scale-2026-v1#bel-flanders-clubs-2026" in bel.observation_ids
    assert "atp-tsa-structure-v1#zaf-head-office-divisions-2026" in zaf.observation_ids

    for rating in (nor, gre, bel, zaf):
        assert "outcome context" in rating.rationale.lower()


def test_atp_den_fin_nzl_batch_is_complete_and_dimensionally_grounded():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code in ("DEN", "FIN", "NZL"):
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.calibration_model_id == "atp-earth-den-fin-nzl-model.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    den = bundle.research.countries["DEN"]
    assert den.years[1990].ratings["squash_popularity"].value > (
        den.years[2016].ratings["squash_popularity"].value
    )
    assert "atp-dtf-members-2024-v1#den-members-2024" not in (
        den.years[2023].ratings["squash_access"].observation_ids
    )
    assert "atp-dtf-members-2024-v1#den-members-2024" in (
        den.years[2024].ratings["squash_access"].observation_ids
    )
    assert "atp-dtf-history-v1#den-senior-championships-current" in (
        den.years[2026].ratings["competition_quality"].observation_ids
    )

    fin = bundle.research.countries["FIN"]
    assert "atp-stl-annual-2025-v1#fin-members-2025" not in (
        fin.years[2024].ratings["squash_popularity"].observation_ids
    )
    assert "atp-stl-annual-2025-v1#fin-members-2025" in (
        fin.years[2025].ratings["squash_popularity"].observation_ids
    )
    assert "atp-stl-high-performance-2026-v1#fin-hp-system-2026" in (
        fin.years[2026].ratings["elite_support"].observation_ids
    )

    nzl = bundle.research.countries["NZL"]
    assert "atp-tennis-nz-home-2026-v1#nzl-hot-shots-venues-2026" not in (
        nzl.years[2025].ratings["squash_access"].observation_ids
    )
    assert "atp-tennis-nz-home-2026-v1#nzl-hot-shots-venues-2026" in (
        nzl.years[2026].ratings["squash_access"].observation_ids
    )
    hot_shots = bundle.observations[
        "atp-tennis-nz-home-2026-v1#nzl-hot-shots-venues-2026"
    ]
    assert hot_shots.age_scope == "children"
    assert "age_limited" in hot_shots.quality_flags
    assert nzl.years[2026].ratings["squash_access"].confidence == "low"
    assert "atp-tennis-nz-pathway-2025-v1#nzl-planning-competition-2025" in (
        nzl.years[2026].ratings["competition_quality"].observation_ids
    )


def test_atp_prt_irl_batch_preserves_scope_and_temporal_evidence():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code in ("PRT", "IRL"):
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.calibration_model_id == "atp-earth-prt-irl-model.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    prt = bundle.research.countries["PRT"]
    assert "atp-fpt-history-profile-v1#prt-practitioners-current-2026" not in (
        prt.years[2025].ratings["squash_popularity"].observation_ids
    )
    assert "atp-fpt-history-profile-v1#prt-practitioners-current-2026" in (
        prt.years[2026].ratings["squash_popularity"].observation_ids
    )
    assert "broad_participation_not_membership" in bundle.observations[
        "atp-fpt-history-profile-v1#prt-practitioners-current-2026"
    ].quality_flags
    assert "atp-fpt-junior-national-2025-v1#prt-u16-national-field-2025" in (
        prt.years[2025].ratings["competition_quality"].observation_ids
    )

    irl = bundle.research.countries["IRL"]
    profile = bundle.observations["atp-tennis-ireland-profile-v1#irl-clubs-current-2026"]
    assert profile.coverage_scope == "partial"
    assert profile.territory_mapping_method == "current_country_partial_association_context"
    assert "association_spans_northern_ireland" in profile.quality_flags
    assert "Northern Ireland" in irl.years[2026].territory_mapping_note
    assert irl.years[2026].ratings["squash_access"].confidence == "low"
    assert "atp-tennis-ireland-performance-v1#irl-team-ireland-support-2020" not in (
        irl.years[2019].ratings["elite_support"].observation_ids
    )
    assert "atp-tennis-ireland-performance-v1#irl-team-ireland-support-2020" in (
        irl.years[2020].ratings["elite_support"].observation_ids
    )
    assert "atp-tennis-ireland-performance-v1#irl-national-pathway-2026" in (
        irl.years[2026].ratings["competition_quality"].observation_ids
    )


def test_atp_hun_rou_batch_preserves_history_and_temporal_gating():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code in ("HUN", "ROU"):
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.calibration_model_id == "atp-earth-hun-rou-model.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    hun = bundle.research.countries["HUN"]
    assert hun.years[1989].historical_entity == "Hungarian People's Republic"
    assert hun.years[1990].historical_entity == "Hungary"
    assert "atp-mtsz-professional-plan-2025-v1#hun-national-training-support-2025" not in (
        hun.years[2024].ratings["development_quality"].observation_ids
    )
    assert "atp-mtsz-professional-plan-2025-v1#hun-national-training-support-2025" in (
        hun.years[2025].ratings["development_quality"].observation_ids
    )
    assert "atp-mtsz-international-events-2026-v1#hun-pro-international-events-2026" in (
        hun.years[2026].ratings["competition_quality"].observation_ids
    )

    rou = bundle.research.countries["ROU"]
    assert rou.years[1964].historical_entity == "Romanian People's Republic"
    assert rou.years[1965].historical_entity == "Socialist Republic of Romania"
    assert rou.years[1990].historical_entity == "Romania"
    assert "atp-frt-coach-licensing-v1#rou-coach-development-system" not in (
        rou.years[2018].ratings["development_quality"].observation_ids
    )
    assert "atp-frt-coach-licensing-v1#rou-coach-development-system" in (
        rou.years[2019].ratings["development_quality"].observation_ids
    )
    assert "atp-frt-u10-national-2025-v1#rou-u10-national-championship-2025" not in (
        rou.years[2024].ratings["competition_quality"].observation_ids
    )
    assert "atp-frt-u10-national-2025-v1#rou-u10-national-championship-2025" in (
        rou.years[2025].ratings["competition_quality"].observation_ids
    )


def test_atp_svn_history_preserves_pre_independence_context_and_modern_gating():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))
    svn = bundle.research.countries["SVN"]

    assert svn.missing_earth_years == []
    assert len(svn.years) == 72
    assert svn.years[1990].historical_entity == "Slovenian tennis within Yugoslavia"
    assert svn.years[1991].historical_entity == "Slovenia"
    assert "not treated as an independent Slovenian state" in svn.years[1990].territory_mapping_note

    for year in svn.years.values():
        assert len(year.ratings) == 6
        for rating in year.ratings.values():
            assert rating.calibration_model_id == "atp-earth-svn-model.v1"
            assert rating.observation_ids
            assert all(item in bundle.observations for item in rating.observation_ids)

    assert "atp-tenis-slovenija-profile-v1#svn-successor-1991" not in (
        svn.years[1990].ratings["squash_tradition"].observation_ids
    )
    assert "atp-tenis-slovenija-profile-v1#svn-successor-1991" in (
        svn.years[1991].ratings["squash_tradition"].observation_ids
    )
    assert "atp-tenis-slovenija-wtt-2026-v1#svn-wtt-development-project-2021" not in (
        svn.years[2020].ratings["competition_quality"].observation_ids
    )
    assert "atp-tenis-slovenija-wtt-2026-v1#svn-wtt-development-project-2021" in (
        svn.years[2021].ratings["competition_quality"].observation_ids
    )
    assert "atp-tenis-slovenija-profile-v1#svn-members-current-2026" not in (
        svn.years[2025].ratings["squash_access"].observation_ids
    )
    assert "atp-tenis-slovenija-profile-v1#svn-members-current-2026" in (
        svn.years[2026].ratings["squash_access"].observation_ids
    )
    assert "atp-tenis-slovenija-wtt-2026-v1#svn-wtt-events-2026" in (
        svn.years[2026].ratings["competition_quality"].observation_ids
    )
    assert "atp-tenis-slovenija-tutor-2026-v1#svn-tutor-programme-2026" in (
        svn.years[2026].ratings["development_quality"].observation_ids
    )


def test_atp_svk_history_uses_true_historical_anchors_before_independence():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))
    svk = bundle.research.countries["SVK"]

    assert svk.missing_earth_years == []
    assert len(svk.years) == 72
    assert svk.years[1992].historical_entity == "Slovak tennis within Czechoslovakia"
    assert svk.years[1993].historical_entity == "Slovakia"

    for year in svk.years.values():
        assert len(year.ratings) == 6
        for rating in year.ratings.values():
            assert rating.calibration_model_id == "atp-earth-svk-model.v1"
            assert rating.observation_ids
            assert all(item in bundle.observations for item in rating.observation_ids)

    for year in range(1955, 1990):
        for rating in svk.years[year].ratings.values():
            assert "atp-stz-institution-history-v1#svk-stz-registered-1990" not in rating.observation_ids
            assert "atp-stz-early-history-v1#svk-first-clubs-1899" in rating.observation_ids
            assert "atp-stz-early-history-v1#svk-international-tournament-1924" in rating.observation_ids

    assert "atp-stz-institution-history-v1#svk-itf-tennis-europe-1993" not in (
        svk.years[1992].ratings["competition_quality"].observation_ids
    )
    assert "atp-stz-institution-history-v1#svk-itf-tennis-europe-1993" in (
        svk.years[1993].ratings["competition_quality"].observation_ids
    )
    assert "atp-stz-structural-milestones-v1#svk-ntc-team-project-2000" not in (
        svk.years[1999].ratings["elite_support"].observation_ids
    )
    assert "atp-stz-structural-milestones-v1#svk-ntc-team-project-2000" in (
        svk.years[2000].ratings["elite_support"].observation_ids
    )
    assert "atp-stz-active-athletes-2025-v1#svk-active-athletes-2025" not in (
        svk.years[2024].ratings["squash_access"].observation_ids
    )
    assert "atp-stz-active-athletes-2025-v1#svk-active-athletes-2025" in (
        svk.years[2025].ratings["squash_access"].observation_ids
    )
    assert "atp-stz-leagues-2026-v1#svk-national-leagues-2026" in (
        svk.years[2026].ratings["competition_quality"].observation_ids
    )


def test_atp_isr_bgr_batch_preserves_temporal_and_semantic_scopes():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code in ("ISR", "BGR"):
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.calibration_model_id == "atp-earth-isr-bgr-model.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    isr = bundle.research.countries["ISR"]
    assert "atp-ita-overview-v1#isr-national-system-2026" not in (
        isr.years[2025].ratings["development_quality"].observation_ids
    )
    assert "atp-ita-overview-v1#isr-national-system-2026" in (
        isr.years[2026].ratings["development_quality"].observation_ids
    )
    assert "atp-ita-youth-calendar-2026-v1#isr-national-youth-events-2026" in (
        isr.years[2026].ratings["competition_quality"].observation_ids
    )
    assert "atp-ita-age10-circuit-2026-v1#isr-u10-events-2026" in (
        isr.years[2026].ratings["development_quality"].observation_ids
    )
    assert "geopolitical" in isr.years[2026].territory_mapping_note.lower()

    bgr = bundle.research.countries["BGR"]
    assert bgr.years[1989].historical_entity == "People's Republic of Bulgaria"
    assert bgr.years[1990].historical_entity == "Bulgaria"
    assert "atp-btf-sport-for-all-2025-v1#bgr-child-access-2025" not in (
        bgr.years[2024].ratings["development_quality"].observation_ids
    )
    assert "atp-btf-sport-for-all-2025-v1#bgr-child-access-2025" in (
        bgr.years[2025].ratings["development_quality"].observation_ids
    )
    assert "atp-btf-history-profile-v1#bgr-clubs-current-2026" not in (
        bgr.years[2025].ratings["squash_access"].observation_ids
    )
    assert "atp-btf-history-profile-v1#bgr-clubs-current-2026" in (
        bgr.years[2026].ratings["squash_access"].observation_ids
    )
    assert "atp-btf-calendar-framework-2026-v1#bgr-national-regional-calendar-2026" in (
        bgr.years[2026].ratings["competition_quality"].observation_ids
    )


def test_atp_aut_history_uses_current_scale_without_backcasting():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))
    aut = bundle.research.countries["AUT"]

    assert aut.missing_earth_years == []
    assert len(aut.years) == 72
    for year in aut.years.values():
        assert len(year.ratings) == 6
        for rating in year.ratings.values():
            assert rating.calibration_model_id == "atp-earth-aut-model.v1"
            assert rating.observation_ids
            assert all(item in bundle.observations for item in rating.observation_ids)

    assert "atp-oetv-itf-wtt-2025-v1#aut-itf-wtt-events-2025" not in (
        aut.years[2024].ratings["competition_quality"].observation_ids
    )
    assert "atp-oetv-itf-wtt-2025-v1#aut-itf-wtt-events-2025" in (
        aut.years[2025].ratings["competition_quality"].observation_ids
    )
    assert "atp-oetv-scale-v1#aut-members-2026" not in (
        aut.years[2025].ratings["squash_popularity"].observation_ids
    )
    assert "atp-oetv-scale-v1#aut-members-2026" in (
        aut.years[2026].ratings["squash_popularity"].observation_ids
    )
    assert "atp-oetv-scale-v1#aut-coaches-2026" in (
        aut.years[2026].ratings["development_quality"].observation_ids
    )
    assert "atp-oetv-major-events-2026-v1#aut-atp-events-2026" in (
        aut.years[2026].ratings["competition_quality"].observation_ids
    )
    assert bundle.observations[
        "atp-oetv-major-events-2026-v1#aut-atp-events-2026"
    ].numeric_value == 5
    assert aut.years[2026].ratings["competition_quality"].confidence == "high"


def test_atp_tur_cyp_batch_preserves_temporal_and_territorial_scope():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code in ("TUR", "CYP"):
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.calibration_model_id == "atp-earth-tur-cyp-model.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    tur = bundle.research.countries["TUR"]
    assert "atp-ttf-history-infrastructure-v1#tur-national-centres-2026" not in (
        tur.years[2025].ratings["development_quality"].observation_ids
    )
    assert "atp-ttf-history-infrastructure-v1#tur-national-centres-2026" in (
        tur.years[2026].ratings["development_quality"].observation_ids
    )
    assert "atp-ttf-calendar-2026-v1#tur-multilevel-calendar-2026" in (
        tur.years[2026].ratings["competition_quality"].observation_ids
    )
    assert "atp-ttf-coach-courses-2026-v1#tur-coach-course-capacity-2026" in (
        tur.years[2026].ratings["development_quality"].observation_ids
    )
    assert "atp-ttf-development-clubs-2026-v1#tur-development-workshop-clubs-2026" in (
        tur.years[2026].ratings["squash_access"].observation_ids
    )

    cyp = bundle.research.countries["CYP"]
    assert all(
        rating.confidence == "low"
        for year in cyp.years.values()
        for rating in year.ratings.values()
    )
    assert "partial association context" in cyp.years[2026].territory_mapping_note.lower()
    assert "atp-ctf-history-v1#cyp-itf-te-member-1984" not in (
        cyp.years[1983].ratings["competition_quality"].observation_ids
    )
    assert "atp-ctf-history-v1#cyp-itf-te-member-1984" in (
        cyp.years[1984].ratings["competition_quality"].observation_ids
    )
    assert "atp-ctf-history-v1#cyp-national-centre-1999" not in (
        cyp.years[1998].ratings["development_quality"].observation_ids
    )
    assert "atp-ctf-history-v1#cyp-national-centre-1999" in (
        cyp.years[1999].ratings["development_quality"].observation_ids
    )
    assert "atp-ctf-development-2026-v1#cyp-development-championship-2026" not in (
        cyp.years[2025].ratings["development_quality"].observation_ids
    )
    assert "atp-ctf-development-2026-v1#cyp-development-championship-2026" in (
        cyp.years[2026].ratings["development_quality"].observation_ids
    )


def test_atp_bra_chl_batch_preserves_temporal_development_evidence():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code in ("BRA", "CHL"):
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.calibration_model_id == "atp-earth-bra-chl-model.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    bra = bundle.research.countries["BRA"]
    assert "atp-cbt-profile-v1#bra-affiliated-athletes-current" not in (
        bra.years[2025].ratings["squash_access"].observation_ids
    )
    assert "atp-cbt-profile-v1#bra-affiliated-athletes-current" in (
        bra.years[2026].ratings["squash_access"].observation_ids
    )
    assert "atp-cbt-junior-regulations-2026-v1#bra-national-junior-grades-2026" in (
        bra.years[2026].ratings["competition_quality"].observation_ids
    )
    assert "atp-cbt-coach-registry-2026-v1#bra-coach-grades-2026" in (
        bra.years[2026].ratings["development_quality"].observation_ids
    )
    assert bundle.observations[
        "atp-bra-pre-cbt-history-v1#bra-parana-federation-1950"
    ].coverage_scope == "partial"

    chl = bundle.research.countries["CHL"]
    assert "atp-fetech-jti-2025-v1#chl-jti-centres-2025" not in (
        chl.years[2024].ratings["development_quality"].observation_ids
    )
    assert "atp-fetech-jti-2025-v1#chl-jti-centres-2025" in (
        chl.years[2025].ratings["development_quality"].observation_ids
    )
    assert "atp-fetech-minor-circuit-growth-2026-v1#chl-junior-circuit-growth-2026" not in (
        chl.years[2025].ratings["competition_quality"].observation_ids
    )
    assert "atp-fetech-minor-circuit-growth-2026-v1#chl-junior-circuit-growth-2026" in (
        chl.years[2026].ratings["competition_quality"].observation_ids
    )
    assert "atp-fetech-national-minors-2026-v1#chl-development-grants-2026" in (
        chl.years[2026].ratings["elite_support"].observation_ids
    )


def test_atp_col_mex_batch_preserves_current_evidence_gating():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code in ("COL", "MEX"):
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.calibration_model_id == "atp-earth-col-mex-model.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    col = bundle.research.countries["COL"]
    assert "atp-fct-interligas-sites-2025-v1#col-interligas-leagues-2025" not in (
        col.years[2024].ratings["competition_quality"].observation_ids
    )
    assert "atp-fct-interligas-sites-2025-v1#col-interligas-leagues-2025" in (
        col.years[2025].ratings["competition_quality"].observation_ids
    )
    assert "atp-fct-affiliation-competition-2026-v1#col-junior-tournaments-2026" not in (
        col.years[2025].ratings["competition_quality"].observation_ids
    )
    assert "atp-fct-affiliation-competition-2026-v1#col-junior-tournaments-2026" in (
        col.years[2026].ratings["competition_quality"].observation_ids
    )
    assert "atp-fct-child-circuit-2026-v1#col-child-circuit-2026" in (
        col.years[2026].ratings["development_quality"].observation_ids
    )

    mex = bundle.research.countries["MEX"]
    assert "atp-fmt-history-v1#mex-federation-founded-1963" not in (
        mex.years[1962].ratings["squash_tradition"].observation_ids
    )
    assert "atp-fmt-history-v1#mex-federation-founded-1963" in (
        mex.years[1963].ratings["squash_tradition"].observation_ids
    )
    assert "atp-fmt-cnij-2025-v1#mex-state-tournaments-2025" not in (
        mex.years[2024].ratings["competition_quality"].observation_ids
    )
    assert "atp-fmt-cnij-2025-v1#mex-state-tournaments-2025" in (
        mex.years[2025].ratings["competition_quality"].observation_ids
    )
    assert "atp-fmt-profile-2026-v1#mex-affiliates-2026" not in (
        mex.years[2025].ratings["squash_access"].observation_ids
    )
    assert "atp-fmt-profile-2026-v1#mex-affiliates-2026" in (
        mex.years[2026].ratings["squash_access"].observation_ids
    )
    assert "atp-fmt-regionals-2026-v1#mex-regional-players-2026" in (
        mex.years[2026].ratings["competition_quality"].observation_ids
    )


def test_atp_ecu_ind_batch_preserves_historical_and_modern_gating():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code in ("ECU", "IND"):
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.calibration_model_id == "atp-earth-ecu-ind-model.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    ecu = bundle.research.countries["ECU"]
    assert "atp-fet-history-profile-v1#ecu-federation-founded-1967" not in (
        ecu.years[1966].ratings["squash_tradition"].observation_ids
    )
    assert "atp-fet-history-profile-v1#ecu-federation-founded-1967" in (
        ecu.years[1967].ratings["squash_tradition"].observation_ids
    )
    assert "atp-fet-history-profile-v1#ecu-national-centre-facilities-2026" not in (
        ecu.years[2025].ratings["development_quality"].observation_ids
    )
    assert "atp-fet-history-profile-v1#ecu-national-centre-facilities-2026" in (
        ecu.years[2026].ratings["development_quality"].observation_ids
    )
    assert "atp-fet-junior-circuit-2026-v1#ecu-national-junior-circuit-2026" in (
        ecu.years[2026].ratings["competition_quality"].observation_ids
    )
    assert "atp-fet-jti-2026-v1#ecu-jti-recurring-stages-2026" in (
        ecu.years[2026].ratings["development_quality"].observation_ids
    )

    ind = bundle.research.countries["IND"]
    assert "atp-aita-history-v1#ind-national-stadium-1996" not in (
        ind.years[1995].ratings["squash_access"].observation_ids
    )
    assert "atp-aita-history-v1#ind-national-stadium-1996" in (
        ind.years[1996].ratings["squash_access"].observation_ids
    )
    assert "atp-aita-actc-2026-v1#ind-hpc-network-2026" not in (
        ind.years[2025].ratings["elite_support"].observation_ids
    )
    assert "atp-aita-actc-2026-v1#ind-hpc-network-2026" in (
        ind.years[2026].ratings["elite_support"].observation_ids
    )
    assert "atp-aita-coaching-2026-v1#ind-coach-course-system-2026" in (
        ind.years[2026].ratings["development_quality"].observation_ids
    )
    assert "atp-aita-ace2032-2026-v1#ind-u12-u14-world-team-pathway-2026" in (
        ind.years[2026].ratings["competition_quality"].observation_ids
    )


def test_atp_kor_tha_batch_preserves_network_calendar_and_infrastructure_gating():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code in ("KOR", "THA"):
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year in history.years.values():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.calibration_model_id == "atp-earth-kor-tha-model.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    kor = bundle.research.countries["KOR"]
    assert "atp-kta-history-v1#kor-atf-member-1968" not in (
        kor.years[1967].ratings["squash_tradition"].observation_ids
    )
    assert "atp-kta-history-v1#kor-atf-member-1968" in (
        kor.years[1968].ratings["squash_tradition"].observation_ids
    )
    assert "atp-kta-history-v1#kor-jangchung-courts-1971" not in (
        kor.years[1970].ratings["squash_access"].observation_ids
    )
    assert "atp-kta-history-v1#kor-jangchung-courts-1971" in (
        kor.years[1971].ratings["squash_access"].observation_ids
    )
    assert "atp-kta-history-v1#kor-itf-mens-circuit-1989" not in (
        kor.years[1988].ratings["competition_quality"].observation_ids
    )
    assert "atp-kta-history-v1#kor-itf-mens-circuit-1989" in (
        kor.years[1989].ratings["competition_quality"].observation_ids
    )
    assert "atp-kta-network-2026-v1#kor-regional-branches-2026" in (
        kor.years[2026].ratings["development_quality"].observation_ids
    )
    assert "atp-kta-calendar-2026-v1#kor-domestic-events-2026" in (
        kor.years[2026].ratings["competition_quality"].observation_ids
    )
    assert "atp-kta-calendar-2026-v1#kor-domestic-events-2026" not in (
        kor.years[2025].ratings["competition_quality"].observation_ids
    )

    tha = bundle.research.countries["THA"]
    assert "atp-ltat-national-centre-v1#tha-national-centre-10-courts-2022" not in (
        tha.years[2021].ratings["squash_access"].observation_ids
    )
    assert "atp-ltat-national-centre-v1#tha-national-centre-10-courts-2022" in (
        tha.years[2022].ratings["squash_access"].observation_ids
    )
    assert "atp-ltat-development-overview-v1#tha-national-development-role-2026" not in (
        tha.years[2025].ratings["development_quality"].observation_ids
    )
    assert "atp-ltat-development-overview-v1#tha-national-development-role-2026" in (
        tha.years[2026].ratings["development_quality"].observation_ids
    )
    assert "atp-ltat-calendar-2026-v1#tha-regional-development-series-2026" in (
        tha.years[2026].ratings["competition_quality"].observation_ids
    )
    assert "atp-ltat-calendar-2026-v1#tha-itf-junior-events-2026" in (
        tha.years[2026].ratings["competition_quality"].observation_ids
    )
    assert "atp-ltat-calendar-2026-v1#tha-itf-junior-events-2026" not in (
        tha.years[2025].ratings["competition_quality"].observation_ids
    )


def test_fifa_ita_nld_bel_prt_batch_is_complete_and_temporally_gated():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    batch = {"ITA", "NLD", "BEL", "PRT"}

    for code in batch:
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026

        for year_number, year in history.years.items():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.method == "derived_estimate"
                assert rating.calibration_model_id == "fifa-earth-country-history-ita-nld-bel-prt.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)
                if year_number < 2006:
                    assert rating.confidence == "low"
                if year_number < 2023:
                    assert "fifa-professional-2023" not in rating.source_ids
                    assert not any(
                        item.startswith("fifa-professional-2023-")
                        for item in rating.observation_ids
                    )

    ita = bundle.research.countries["ITA"]
    nld = bundle.research.countries["NLD"]
    bel = bundle.research.countries["BEL"]
    prt = bundle.research.countries["PRT"]

    assert nld.years[2006].ratings["squash_access"].value > ita.years[2006].ratings["squash_access"].value
    assert prt.years[2026].ratings["development_quality"].value >= 9.0
    assert ita.years[2026].ratings["competition_quality"].value < 9.0
    assert bel.years[2026].ratings["squash_access"].value > bel.years[1955].ratings["squash_access"].value


def test_fifa_aut_dnk_swe_che_batch_is_complete_comparable_and_temporally_gated():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    batch = {"AUT", "DNK", "SWE", "CHE"}

    for code in batch:
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026

        for year_number, year in history.years.items():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.method == "derived_estimate"
                assert rating.calibration_model_id == "fifa-earth-country-history-aut-dnk-swe-che.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)
                if year_number < 2006:
                    assert rating.confidence == "low"
                if year_number < 2023:
                    assert "fifa-professional-2023" not in rating.source_ids
                    assert not any(
                        item.startswith("fifa-professional-2023-")
                        for item in rating.observation_ids
                    )

    aut = bundle.research.countries["AUT"]
    dnk = bundle.research.countries["DNK"]
    swe = bundle.research.countries["SWE"]
    che = bundle.research.countries["CHE"]

    assert dnk.years[2006].ratings["squash_access"].value > aut.years[2006].ratings["squash_access"].value
    assert swe.years[2006].ratings["squash_access"].value >= dnk.years[2006].ratings["squash_access"].value
    assert swe.years[2023].ratings["competition_quality"].value >= 9.0
    assert che.years[2026].ratings["squash_popularity"].value < aut.years[2026].ratings["squash_popularity"].value


def test_fifa_nor_fin_hrv_svn_batch_preserves_governance_and_evidence_gating():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    batch = {"NOR", "FIN", "HRV", "SVN"}

    for code in batch:
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year_number, year in history.years.items():
            assert len(year.ratings) == 6
            for rating in year.ratings.values():
                assert rating.method == "derived_estimate"
                assert rating.calibration_model_id == "fifa-earth-country-history-nor-fin-hrv-svn.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)
                if year_number < 2006:
                    assert "fifa-big-count-2006" not in rating.source_ids
                    assert not any(item.startswith("fifa-big-count-2006-") for item in rating.observation_ids)
                if year_number < 2023:
                    assert "fifa-professional-2023" not in rating.source_ids
                    assert not any(item.startswith("fifa-professional-2023-") for item in rating.observation_ids)

    nor = bundle.research.countries["NOR"]
    assert nor.years[2006].ratings["squash_access"].value >= 9.5
    assert nor.years[2006].ratings["squash_access"].value > nor.years[2006].ratings["competition_quality"].value

    fin = bundle.research.countries["FIN"]
    assert "fifa-structural-uefa-finland-profile-v1#fin-regional-centres-2026" not in (
        fin.years[2025].ratings["development_quality"].observation_ids
    )
    assert "fifa-structural-uefa-finland-profile-v1#fin-regional-centres-2026" in (
        fin.years[2026].ratings["development_quality"].observation_ids
    )

    hrv = bundle.research.countries["HRV"]
    assert "Yugoslavia" in hrv.years[1990].historical_entity
    assert hrv.years[1991].historical_entity == "Croatia"
    assert hrv.years[1991].ratings["competition_quality"].value < hrv.years[1990].ratings["competition_quality"].value
    assert "fifa-structural-uefa-croatia-profile-v1#hrv-fifa-renewal-1992" not in (
        hrv.years[1991].ratings["competition_quality"].observation_ids
    )
    assert "fifa-structural-uefa-croatia-profile-v1#hrv-fifa-renewal-1992" in (
        hrv.years[1992].ratings["competition_quality"].observation_ids
    )

    svn = bundle.research.countries["SVN"]
    assert "Yugoslavia" in svn.years[1990].historical_entity
    assert svn.years[1991].historical_entity == "Slovenia"
    assert svn.years[1991].ratings["elite_support"].value < svn.years[1990].ratings["elite_support"].value
    assert "fifa-structural-uefa-slovenia-profile-v1#svn-uefa-membership-1993" not in (
        svn.years[1992].ratings["elite_support"].observation_ids
    )
    assert "fifa-structural-uefa-slovenia-profile-v1#svn-uefa-membership-1993" in (
        svn.years[1993].ratings["elite_support"].observation_ids
    )


def test_fifa_pol_rou_ukr_ltu_batch_preserves_soviet_transitions_and_gating():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    batch = {"POL", "ROU", "UKR", "LTU"}

    for code in batch:
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year_number, year in history.years.items():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == "fifa-earth-country-history-pol-rou-ukr-ltu.v1"
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)
                if year_number < 2006:
                    assert "fifa-big-count-2006" not in rating.source_ids
                if year_number < 2023:
                    assert "fifa-professional-2023" not in rating.source_ids

    pol = bundle.research.countries["POL"]
    assert "fifa-structural-uefa-poland-profile-v1#pol-euro-host-2012" not in pol.years[2011].ratings["elite_support"].observation_ids
    assert "fifa-structural-uefa-poland-profile-v1#pol-euro-host-2012" in pol.years[2012].ratings["elite_support"].observation_ids

    rou = bundle.research.countries["ROU"]
    assert "fifa-structural-uefa-romania-profile-v1#rou-frf-founded-1957" not in rou.years[1956].ratings["elite_support"].observation_ids
    assert "fifa-structural-uefa-romania-profile-v1#rou-frf-founded-1957" in rou.years[1957].ratings["elite_support"].observation_ids

    ukr = bundle.research.countries["UKR"]
    assert "Soviet" in ukr.years[1990].historical_entity
    assert ukr.years[1991].historical_entity == "Ukraine"
    assert ukr.years[1991].ratings["elite_support"].value < ukr.years[1990].ratings["elite_support"].value
    assert "fifa-structural-uefa-ukraine-profile-v1#ukr-first-league-cup-1992" not in ukr.years[1991].ratings["competition_quality"].observation_ids
    assert "fifa-structural-uefa-ukraine-profile-v1#ukr-first-league-cup-1992" in ukr.years[1992].ratings["competition_quality"].observation_ids
    assert ukr.years[2023].ratings["squash_access"].value < ukr.years[2022].ratings["squash_access"].value
    assert ukr.years[2023].ratings["squash_access"].confidence == "low"

    ltu = bundle.research.countries["LTU"]
    assert "Soviet" in ltu.years[1989].historical_entity
    assert ltu.years[1990].historical_entity == "Lithuania"
    assert ltu.years[1990].ratings["elite_support"].value < ltu.years[1989].ratings["elite_support"].value
    assert "fifa-structural-uefa-lithuania-profile-v1#ltu-fifa-readmission-1991" not in ltu.years[1990].ratings["competition_quality"].observation_ids
    assert "fifa-structural-uefa-lithuania-profile-v1#ltu-fifa-readmission-1991" in ltu.years[1991].ratings["competition_quality"].observation_ids


def test_atp_kaz_history_preserves_soviet_context_transition_constraints_and_current_gating():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))
    kaz = bundle.research.countries["KAZ"]

    assert kaz.missing_earth_years == []
    assert len(kaz.years) == 72
    assert kaz.years[1990].historical_entity == "Kazakh SSR within the Soviet Union"
    assert kaz.years[1991].historical_entity == "Kazakhstan"

    for year_number, year in kaz.years.items():
        assert len(year.ratings) == 6
        for rating in year.ratings.values():
            assert rating.calibration_model_id == "atp-earth-kaz-model.v1"
            assert rating.observation_ids
            assert all(item in bundle.observations for item in rating.observation_ids)
            if year_number < 2026:
                assert "atp-ktf-federation-profile-2026-v1#kaz-regional-branches-2026" not in rating.observation_ids
                assert "atp-ktf-infrastructure-2026-v1#kaz-high-performance-centres-2026" not in rating.observation_ids
                assert "atp-ktf-infrastructure-2026-v1#kaz-courts-2026" not in rating.observation_ids

    assert "atp-kaz-noc-history-v1#kaz-dynamo-programme-1933" in kaz.years[1955].ratings["squash_tradition"].observation_ids
    assert "atp-kaz-noc-history-v1#kaz-almaty-city-competition-1935" in kaz.years[1955].ratings["competition_quality"].observation_ids

    assert "atp-ktf-presidents-cup-history-v1#kaz-presidents-cup-since-1991" not in kaz.years[1990].ratings["competition_quality"].observation_ids
    assert "atp-ktf-presidents-cup-history-v1#kaz-presidents-cup-since-1991" in kaz.years[1991].ratings["competition_quality"].observation_ids

    assert "atp-ktf-transition-history-v1#kaz-underfunded-1990-2009" in kaz.years[1991].ratings["elite_support"].observation_ids
    assert "atp-ktf-transition-history-v1#kaz-underfunded-1990-2009" in kaz.years[2009].ratings["development_quality"].observation_ids
    assert "atp-ktf-transition-history-v1#kaz-underfunded-1990-2009" not in kaz.years[2010].ratings["elite_support"].observation_ids

    assert "atp-ktf-presidents-cup-history-v1#kaz-challenger-upgrade-2007" not in kaz.years[2006].ratings["competition_quality"].observation_ids
    assert "atp-ktf-presidents-cup-history-v1#kaz-challenger-upgrade-2007" in kaz.years[2007].ratings["competition_quality"].observation_ids

    assert kaz.years[2026].ratings["squash_access"].value == 8.8
    assert kaz.years[2026].ratings["development_quality"].value == 8.9
    assert kaz.years[2026].ratings["elite_support"].value == 8.9
    assert kaz.years[2026].ratings["competition_quality"].value < 9.0
    assert "atp-ktf-federation-profile-2026-v1#kaz-regional-branches-2026" in kaz.years[2026].ratings["squash_access"].observation_ids
    assert "atp-ktf-infrastructure-2026-v1#kaz-high-performance-centres-2026" in kaz.years[2026].ratings["development_quality"].observation_ids


def test_baltic_lva_est_fifa_and_atp_histories_keep_soviet_context_and_sport_specific_gating():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code in ("LVA", "EST"):
        fifa_history = fifa.research.countries[code]
        atp_history = atp.research.countries[code]
        assert fifa_history.missing_earth_years == []
        assert atp_history.missing_earth_years == []
        assert len(fifa_history.years) == 72
        assert len(atp_history.years) == 72
        assert "Soviet Union" in fifa_history.years[1990].historical_entity
        assert "Soviet Union" in atp_history.years[1990].historical_entity
        assert fifa_history.years[1991].historical_entity in {"Latvia", "Estonia"}
        assert atp_history.years[1991].historical_entity in {"Latvia", "Estonia"}

        for year_number, year in fifa_history.years.items():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == "fifa-earth-lva-est-model.v1"
                assert rating.observation_ids
                assert all(item in fifa.observations for item in rating.observation_ids)
                if year_number < 2006:
                    assert "fifa-big-count-2006" not in rating.source_ids
                if year_number < 2023:
                    assert "fifa-professional-2023" not in rating.source_ids

        for year_number, year in atp_history.years.items():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == "atp-earth-lva-est-model.v1"
                assert rating.observation_ids
                assert all(item in atp.observations for item in rating.observation_ids)
                if year_number < 2026:
                    assert "itf-members-2026" not in rating.source_ids
                    assert "atp-itf-baltic-members-2026-v1#est-itf-member-2026" not in rating.observation_ids
                    assert "atp-itf-baltic-members-2026-v1#lva-itf-member-2026" not in rating.observation_ids

    lva_fifa = fifa.research.countries["LVA"]
    assert "fifa-structural-uefa-latvia-profile-v1#lva-virsliga-uefa-1992" not in (
        lva_fifa.years[1991].ratings["competition_quality"].observation_ids
    )
    assert "fifa-structural-uefa-latvia-profile-v1#lva-virsliga-uefa-1992" in (
        lva_fifa.years[1992].ratings["competition_quality"].observation_ids
    )

    est_fifa = fifa.research.countries["EST"]
    assert "fifa-structural-uefa-estonia-profile-v1#est-ejl-reformed-1988" not in (
        est_fifa.years[1987].ratings["elite_support"].observation_ids
    )
    assert "fifa-structural-uefa-estonia-profile-v1#est-ejl-reformed-1988" in (
        est_fifa.years[1988].ratings["elite_support"].observation_ids
    )
    assert est_fifa.years[2006].ratings["squash_access"].value > (
        lva_fifa.years[2006].ratings["squash_access"].value
    )
    assert est_fifa.years[2023].ratings["competition_quality"].value > (
        lva_fifa.years[2023].ratings["competition_quality"].value
    )

    lva_atp = atp.research.countries["LVA"]
    assert "atp-lts-amateur-league-v1#lva-ltal-start-2013" not in (
        lva_atp.years[2012].ratings["competition_quality"].observation_ids
    )
    assert "atp-lts-amateur-league-v1#lva-ltal-start-2013" in (
        lva_atp.years[2013].ratings["competition_quality"].observation_ids
    )
    assert "atp-lts-profile-2026-v1#lva-athlete-coach-official-development-2026" not in (
        lva_atp.years[2025].ratings["development_quality"].observation_ids
    )
    assert "atp-lts-profile-2026-v1#lva-athlete-coach-official-development-2026" in (
        lva_atp.years[2026].ratings["development_quality"].observation_ids
    )

    est_atp = atp.research.countries["EST"]
    assert "atp-etl-soviet-context-v1#est-ssr-tennis-federation-1968" not in (
        est_atp.years[1967].ratings["squash_tradition"].observation_ids
    )
    assert "atp-etl-soviet-context-v1#est-ssr-tennis-federation-1968" in (
        est_atp.years[1968].ratings["squash_tradition"].observation_ids
    )
    assert "atp-etl-governance-2026-v1#est-coach-official-development-2026" in (
        est_atp.years[2026].ratings["development_quality"].observation_ids
    )



def test_atp_ltu_history_preserves_soviet_context_and_temporal_gating():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))
    ltu = bundle.research.countries["LTU"]

    assert ltu.missing_earth_years == []
    assert len(ltu.years) == 72
    assert ltu.reference_year == 2026

    for year in ltu.years.values():
        for rating in year.ratings.values():
            assert rating.calibration_model_id == "atp-earth-ltu-model.v1"
            assert rating.observation_ids
            assert all(item in bundle.observations for item in rating.observation_ids)

    assert "Soviet" in ltu.years[1989].historical_entity
    assert ltu.years[1990].historical_entity == "Lithuania"
    assert "atp-lts-lithuania-history-v1#ltu-federation-presidium-1959" not in ltu.years[1958].ratings["elite_support"].observation_ids
    assert "atp-lts-lithuania-history-v1#ltu-federation-presidium-1959" in ltu.years[1959].ratings["elite_support"].observation_ids
    assert "atp-lts-lithuania-governance-v1#ltu-lts-established-1995" not in ltu.years[1994].ratings["squash_tradition"].observation_ids
    assert "atp-lts-lithuania-governance-v1#ltu-lts-established-1995" in ltu.years[1995].ratings["squash_tradition"].observation_ids
    assert "atp-lts-lithuania-mandate-v1#ltu-national-federation-mandate-2022" not in ltu.years[2021].ratings["development_quality"].observation_ids
    assert "atp-lts-lithuania-mandate-v1#ltu-national-federation-mandate-2022" in ltu.years[2022].ratings["development_quality"].observation_ids



def test_fifa_can_history_is_complete_temporally_gated_and_conservative():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    can = bundle.research.countries["CAN"]

    assert can.missing_earth_years == []
    assert len(can.years) == 72
    assert can.reference_year == 2026

    for year_number, year in can.years.items():
        for rating in year.ratings.values():
            assert rating.calibration_model_id == "fifa-earth-can-model.v1"
            assert rating.observation_ids
            assert all(item in bundle.observations for item in rating.observation_ids)
            if year_number < 2006:
                assert "fifa-big-count-2006" not in rating.source_ids
            if year_number < 2023:
                assert "fifa-professional-2023" not in rating.source_ids
            if year_number < 2026:
                assert "canada-soccer-about-2026" not in rating.source_ids

    assert "fifa-big-count-2006-registered-v2#canada" not in can.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#canada" in can.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-structural-canada-soccer-development-v1#can-ltpd-2008" not in can.years[2007].ratings["development_quality"].observation_ids
    assert "fifa-structural-canada-soccer-development-v1#can-ltpd-2008" in can.years[2008].ratings["development_quality"].observation_ids
    assert can.years[2015].ratings["development_quality"].value > can.years[2013].ratings["development_quality"].value
    assert can.years[2019].ratings["competition_quality"].value > can.years[2015].ratings["competition_quality"].value
    assert "fifa-professional-2023-clubs-v2#canada-p138" not in can.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#canada-p138" in can.years[2023].ratings["competition_quality"].observation_ids
    assert "fifa-structural-canada-soccer-current-2026-v1#can-clubs-2026" not in can.years[2025].ratings["squash_access"].observation_ids
    assert "fifa-structural-canada-soccer-current-2026-v1#can-clubs-2026" in can.years[2026].ratings["squash_access"].observation_ids
    assert max(r.value for r in can.years[2026].ratings.values()) < 9.0



def test_fifa_grc_history_uses_time_gated_global_and_structural_evidence():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    grc = bundle.research.countries["GRC"]

    assert grc.missing_earth_years == []
    assert len(grc.years) == 72
    assert grc.reference_year == 2026

    for year_number, year in grc.years.items():
        for rating in year.ratings.values():
            assert rating.calibration_model_id == "fifa-earth-grc-model.v1"
            assert rating.observation_ids
            assert all(item in bundle.observations for item in rating.observation_ids)
            if year_number < 2006:
                assert "fifa-big-count-2006" not in rating.source_ids
            if year_number < 2023:
                assert "fifa-professional-2023" not in rating.source_ids

    assert "fifa-structural-hff-history-v1#gre-european-final-host-1971" not in grc.years[1970].ratings["competition_quality"].observation_ids
    assert "fifa-structural-hff-history-v1#gre-european-final-host-1971" in grc.years[1971].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-registered-v2#greece" not in grc.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#greece" in grc.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-professional-2023-clubs-v2#greece-p225" not in grc.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#greece-p225" in grc.years[2023].ratings["competition_quality"].observation_ids
    assert max(r.value for r in grc.years[2026].ratings.values()) < 9.0


def test_atp_ukr_history_preserves_soviet_context_war_shock_and_partial_continuity():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))
    ukr = bundle.research.countries["UKR"]

    assert ukr.missing_earth_years == []
    assert len(ukr.years) == 72
    assert ukr.reference_year == 2026

    for year in ukr.years.values():
        for rating in year.ratings.values():
            assert rating.calibration_model_id == "atp-earth-ukr-model.v1"
            assert rating.observation_ids
            assert all(item in bundle.observations for item in rating.observation_ids)

    assert "Soviet" in ukr.years[1990].historical_entity
    assert ukr.years[1991].historical_entity == "Ukraine"
    assert "atp-utf-history-development-v1#ukr-federation-1991" not in ukr.years[1990].ratings["elite_support"].observation_ids
    assert "atp-utf-history-development-v1#ukr-federation-1991" in ukr.years[1991].ratings["elite_support"].observation_ids
    assert "atp-utf-governance-infrastructure-v1#ukr-coach-conference-2015" not in ukr.years[2014].ratings["development_quality"].observation_ids
    assert "atp-utf-governance-infrastructure-v1#ukr-coach-conference-2015" in ukr.years[2015].ratings["development_quality"].observation_ids
    assert ukr.years[2022].ratings["squash_access"].value < ukr.years[2021].ratings["squash_access"].value
    assert ukr.years[2022].ratings["development_quality"].value < ukr.years[2021].ratings["development_quality"].value
    assert "atp-itf-ukraine-war-disruption-v1#ukr-irpin-seven-courts-destroyed-2022" not in ukr.years[2021].ratings["squash_access"].observation_ids
    assert "atp-itf-ukraine-war-disruption-v1#ukr-irpin-seven-courts-destroyed-2022" in ukr.years[2022].ratings["squash_access"].observation_ids
    assert "atp-utf-current-structure-2025-v1#ukr-national-youth-teams-2025" not in ukr.years[2024].ratings["development_quality"].observation_ids
    assert "atp-utf-current-structure-2025-v1#ukr-national-youth-teams-2025" in ukr.years[2025].ratings["development_quality"].observation_ids
    assert ukr.years[2026].ratings["squash_access"].value < ukr.years[2021].ratings["squash_access"].value



def test_fifa_srb_history_preserves_predecessor_context_and_global_data_gating():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    srb = bundle.research.countries["SRB"]

    assert srb.missing_earth_years == []
    assert len(srb.years) == 72
    assert srb.reference_year == 2026
    assert "Yugoslavia" in srb.years[1955].historical_entity
    assert "Yugoslavia" in srb.years[1992].historical_entity
    assert "Serbia and Montenegro" in srb.years[2005].historical_entity
    assert srb.years[2006].historical_entity == "Serbia"

    for year_number, year in srb.years.items():
        for rating in year.ratings.values():
            assert rating.calibration_model_id == "fifa-earth-srb-model.v1"
            assert rating.observation_ids
            assert all(item in bundle.observations for item in rating.observation_ids)
            if year_number < 2006:
                assert "fifa-big-count-2006" not in rating.source_ids
            if year_number < 2023:
                assert "fifa-professional-2023" not in rating.source_ids

    assert "fifa-structural-fss-history-v1#srb-independent-transition-2006" not in srb.years[2005].ratings["elite_support"].observation_ids
    assert "fifa-structural-fss-history-v1#srb-independent-transition-2006" in srb.years[2006].ratings["elite_support"].observation_ids
    assert "fifa-big-count-2006-registered-v2#serbia" not in srb.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#serbia" in srb.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-professional-2023-clubs-v2#serbia-p250" not in srb.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#serbia-p250" in srb.years[2023].ratings["competition_quality"].observation_ids
    assert max(r.value for r in srb.years[2026].ratings.values()) < 9.0


def test_atp_mar_history_separates_pre_frmt_foundation_and_current_mandate():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))
    mar = bundle.research.countries["MAR"]

    assert mar.missing_earth_years == []
    assert len(mar.years) == 72
    assert mar.reference_year == 2026
    assert "protectorate" in mar.years[1955].historical_entity
    assert mar.years[1956].historical_entity == "Morocco"

    for year_number, year in mar.years.items():
        for rating in year.ratings.values():
            assert rating.calibration_model_id == "atp-earth-mar-model.v1"
            assert rating.observation_ids
            assert all(item in bundle.observations for item in rating.observation_ids)
            if year_number < 2026:
                assert "cnom-frmt-profile" not in rating.source_ids

    assert "atp-frmt-statutes-v1#mar-frmt-founded-1957" not in mar.years[1956].ratings["squash_tradition"].observation_ids
    assert "atp-frmt-statutes-v1#mar-frmt-founded-1957" in mar.years[1957].ratings["squash_tradition"].observation_ids
    assert "atp-frmt-committee-history-v1#mar-mjid-presidency-1964" not in mar.years[1963].ratings["elite_support"].observation_ids
    assert "atp-frmt-committee-history-v1#mar-mjid-presidency-1964" in mar.years[1964].ratings["elite_support"].observation_ids
    assert "atp-frmt-current-mandate-v1#mar-access-ranking-competition-2026" not in mar.years[2025].ratings["squash_access"].observation_ids
    assert "atp-frmt-current-mandate-v1#mar-access-ranking-competition-2026" in mar.years[2026].ratings["squash_access"].observation_ids
    assert max(r.value for r in mar.years[2026].ratings.values()) < 9.0



def test_fifa_chl_history_keeps_global_and_2026_infrastructure_evidence_time_gated():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    chl = bundle.research.countries["CHL"]

    assert chl.missing_earth_years == []
    assert len(chl.years) == 72
    assert chl.reference_year == 2026

    for year_number, year in chl.years.items():
        for rating in year.ratings.values():
            assert rating.calibration_model_id == "fifa-earth-chl-model.v1"
            assert rating.observation_ids
            assert all(item in bundle.observations for item in rating.observation_ids)
            if year_number < 2006:
                assert "fifa-big-count-2006" not in rating.source_ids
            if year_number < 2023:
                assert "fifa-professional-2023" not in rating.source_ids
            if year_number < 2026:
                assert "anfp-chile-forward-2026" not in rating.source_ids

    assert "fifa-big-count-2006-registered-v2#chile" not in chl.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#chile" in chl.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-professional-2023-clubs-v2#chile-p174" not in chl.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#chile-p174" in chl.years[2023].ratings["competition_quality"].observation_ids
    assert "fifa-structural-chile-forward-2026-v1#chl-high-performance-complex-2026" not in chl.years[2025].ratings["development_quality"].observation_ids
    assert "fifa-structural-chile-forward-2026-v1#chl-high-performance-complex-2026" in chl.years[2026].ratings["development_quality"].observation_ids
    assert max(r.value for r in chl.years[2026].ratings.values()) < 9.0


def test_atp_sen_history_preserves_1975_shift_decline_and_modern_recovery_gating():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))
    sen = bundle.research.countries["SEN"]

    assert sen.missing_earth_years == []
    assert len(sen.years) == 72
    assert sen.reference_year == 2026
    assert "French West Africa" in sen.years[1955].historical_entity
    assert sen.years[1960].historical_entity == "Senegal"

    for year in sen.years.values():
        for rating in year.ratings.values():
            assert rating.calibration_model_id == "atp-earth-sen-model.v1"
            assert rating.observation_ids
            assert all(item in bundle.observations for item in rating.observation_ids)

    assert "atp-senegal-tennis-history-v1#sen-governance-transition-1975" not in sen.years[1974].ratings["elite_support"].observation_ids
    assert "atp-senegal-tennis-history-v1#sen-governance-transition-1975" in sen.years[1975].ratings["elite_support"].observation_ids
    assert sen.years[1985].ratings["development_quality"].value > sen.years[2001].ratings["development_quality"].value
    assert "atp-senegal-tennis-history-v1#sen-development-decline-1985-2001" in sen.years[1985].ratings["development_quality"].observation_ids
    assert "atp-senegal-tennis-history-v1#sen-development-decline-1985-2001" in sen.years[2001].ratings["competition_quality"].observation_ids
    assert "atp-senegal-tennis-history-v1#sen-development-decline-1985-2001" not in sen.years[2002].ratings["development_quality"].observation_ids
    assert "atp-fft-senegal-cooperation-2022-v1#sen-france-cooperation-2022" not in sen.years[2021].ratings["development_quality"].observation_ids
    assert "atp-fft-senegal-cooperation-2022-v1#sen-france-cooperation-2022" in sen.years[2022].ratings["development_quality"].observation_ids
    assert "atp-davis-cup-senegal-2025-v1#sen-africa-group-iii-promotion-2025" not in sen.years[2024].ratings["competition_quality"].observation_ids
    assert "atp-davis-cup-senegal-2025-v1#sen-africa-group-iii-promotion-2025" in sen.years[2025].ratings["competition_quality"].observation_ids
    assert "atp-itf-senegal-member-2026-v1#sen-itf-member-association-2026" not in sen.years[2025].ratings["squash_tradition"].observation_ids
    assert "atp-itf-senegal-member-2026-v1#sen-itf-member-association-2026" in sen.years[2026].ratings["squash_tradition"].observation_ids
    assert max(r.value for r in sen.years[2026].ratings.values()) < 9.0



def test_four_country_acceleration_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    expected_models = {
        ("fifa", "HUN"): "fifa-earth-hun-model.v1",
        ("fifa", "ISR"): "fifa-earth-isr-model.v1",
        ("atp", "ISL"): "atp-earth-isl-model.v1",
        ("atp", "SMR"): "atp-earth-smr-model.v1",
    }
    for (world, code), model_id in expected_models.items():
        bundle = fifa if world == "fifa" else atp
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    hun = fifa.research.countries["HUN"]
    assert "fifa-big-count-2006-registered-v2#hungary" not in hun.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#hungary" in hun.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-professional-2023-clubs-v2#hungary-p226" not in hun.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#hungary-p226" in hun.years[2023].ratings["competition_quality"].observation_ids

    isr = fifa.research.countries["ISR"]
    assert "fifa-structural-uefa-israel-history-v1#isr-afc-admission-1956" not in isr.years[1955].ratings["competition_quality"].observation_ids
    assert "fifa-structural-uefa-israel-history-v1#isr-afc-admission-1956" in isr.years[1956].ratings["competition_quality"].observation_ids
    assert "fifa-structural-uefa-israel-history-v1#isr-uefa-full-member-1994" not in isr.years[1993].ratings["competition_quality"].observation_ids
    assert "fifa-structural-uefa-israel-history-v1#isr-uefa-full-member-1994" in isr.years[1994].ratings["competition_quality"].observation_ids

    isl = atp.research.countries["ISL"]
    assert "atp-iceland-history-v1#isl-tsi-founded-1987" not in isl.years[1986].ratings["development_quality"].observation_ids
    assert "atp-iceland-history-v1#isl-tsi-founded-1987" in isl.years[1987].ratings["development_quality"].observation_ids
    assert "atp-iceland-history-v1#isl-kopavogur-hall-1995" not in isl.years[1994].ratings["squash_access"].observation_ids
    assert "atp-iceland-history-v1#isl-kopavogur-hall-1995" in isl.years[1995].ratings["squash_access"].observation_ids
    assert "atp-iceland-current-2026-v1#isl-indoor-instruction-2026" not in isl.years[2025].ratings["development_quality"].observation_ids
    assert "atp-iceland-current-2026-v1#isl-indoor-instruction-2026" in isl.years[2026].ratings["development_quality"].observation_ids

    smr = atp.research.countries["SMR"]
    assert "atp-san-marino-history-v1#smr-federation-founded-1957" not in smr.years[1956].ratings["squash_tradition"].observation_ids
    assert "atp-san-marino-history-v1#smr-federation-founded-1957" in smr.years[1957].ratings["squash_tradition"].observation_ids
    assert "atp-san-marino-history-v1#smr-tennis-centre-1991" not in smr.years[1990].ratings["squash_access"].observation_ids
    assert "atp-san-marino-history-v1#smr-tennis-centre-1991" in smr.years[1991].ratings["squash_access"].observation_ids
    assert "atp-san-marino-history-v1#smr-federal-school-2026" not in smr.years[2025].ratings["development_quality"].observation_ids
    assert "atp-san-marino-history-v1#smr-federal-school-2026" in smr.years[2026].ratings["development_quality"].observation_ids

    assert max(r.value for r in hun.years[2026].ratings.values()) < 9.0
    assert max(r.value for r in isr.years[2026].ratings.values()) < 9.0
    assert max(r.value for r in isl.years[2026].ratings.values()) < 9.0
    assert max(r.value for r in smr.years[2026].ratings.values()) < 9.0



def test_accelerated_bgr_kaz_fro_fji_batch_is_complete_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code, model_id in {
        "BGR": "fifa-earth-bgr-model.v1",
        "KAZ": "fifa-earth-kaz-model.v1",
    }.items():
        history = fifa.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in fifa.observations for item in rating.observation_ids)

    bgr = fifa.research.countries["BGR"]
    assert bgr.years[1955].historical_entity == "People's Republic of Bulgaria"
    assert bgr.years[1990].historical_entity == "Bulgaria"
    assert "fifa-big-count-2006-registered-v2#bulgaria" not in bgr.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#bulgaria" in bgr.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-structural-uefa-bulgaria-history-v1#bgr-house-of-football-2016" not in bgr.years[2015].ratings["development_quality"].observation_ids
    assert "fifa-structural-uefa-bulgaria-history-v1#bgr-house-of-football-2016" in bgr.years[2016].ratings["development_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#bulgaria-p212" not in bgr.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#bulgaria-p212" in bgr.years[2023].ratings["competition_quality"].observation_ids

    kaz = fifa.research.countries["KAZ"]
    assert "Soviet" in kaz.years[1990].historical_entity
    assert kaz.years[1991].historical_entity == "Kazakhstan"
    assert "fifa-structural-uefa-kazakhstan-history-v1#kaz-ssr-federation-1959" not in kaz.years[1958].ratings["elite_support"].observation_ids
    assert "fifa-structural-uefa-kazakhstan-history-v1#kaz-ssr-federation-1959" in kaz.years[1959].ratings["elite_support"].observation_ids
    assert "fifa-structural-uefa-kazakhstan-history-v1#kaz-independent-association-1992" not in kaz.years[1991].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-uefa-kazakhstan-history-v1#kaz-independent-association-1992" in kaz.years[1992].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-uefa-kazakhstan-history-v1#kaz-uefa-member-2002" not in kaz.years[2001].ratings["competition_quality"].observation_ids
    assert "fifa-structural-uefa-kazakhstan-history-v1#kaz-uefa-member-2002" in kaz.years[2002].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#kazakhstan-p230" not in kaz.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#kazakhstan-p230" in kaz.years[2023].ratings["competition_quality"].observation_ids

    for code, model_id in {
        "FRO": "atp-earth-fro-model.v1",
        "FJI": "atp-earth-fji-model.v1",
    }.items():
        history = atp.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in atp.observations for item in rating.observation_ids)

    fro = atp.research.countries["FRO"]
    assert "atp-faroe-island-games-2013-v1#fro-island-games-tennis-2013" not in fro.years[2012].ratings["competition_quality"].observation_ids
    assert "atp-faroe-island-games-2013-v1#fro-island-games-tennis-2013" in fro.years[2013].ratings["competition_quality"].observation_ids
    assert "atp-faroe-tennis-europe-2026-v1#fro-federation-founded-2017" not in fro.years[2016].ratings["development_quality"].observation_ids
    assert "atp-faroe-tennis-europe-2026-v1#fro-federation-founded-2017" in fro.years[2017].ratings["development_quality"].observation_ids
    assert "itf-faroe-membership-2026" not in fro.years[2025].ratings["elite_support"].source_ids
    assert "itf-faroe-membership-2026" in fro.years[2026].ratings["elite_support"].source_ids

    fji = atp.research.countries["FJI"]
    assert "British Fiji" in fji.years[1969].historical_entity
    assert fji.years[1970].historical_entity == "Fiji"
    assert "atp-fiji-juniors-2022-v1#fji-west-pacific-juniors-2022" not in fji.years[2021].ratings["development_quality"].observation_ids
    assert "atp-fiji-juniors-2022-v1#fji-west-pacific-juniors-2022" in fji.years[2022].ratings["development_quality"].observation_ids
    assert "atp-fiji-current-2026-v1#fji-district-club-network-2026" not in fji.years[2025].ratings["squash_access"].observation_ids
    assert "atp-fiji-current-2026-v1#fji-district-club-network-2026" in fji.years[2026].ratings["squash_access"].observation_ids

    for history in (bgr, kaz, fro, fji):
        assert max(r.value for r in history.years[2026].ratings.values()) < 9.0



def test_accelerated_chn_tur_png_wsm_batch_is_complete_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code, model_id in {
        "CHN": "fifa-earth-chn-model.v1",
        "TUR": "fifa-earth-tur-model.v1",
    }.items():
        history = fifa.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in fifa.observations for item in rating.observation_ids)

    chn = fifa.research.countries["CHN"]
    assert "fifa-structural-china-cup-v1#chn-national-cup-1956" not in chn.years[1955].ratings["competition_quality"].observation_ids
    assert "fifa-structural-china-cup-v1#chn-national-cup-1956" in chn.years[1956].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-registered-v2#china-pr" not in chn.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#china-pr" in chn.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-structural-china-development-v1#chn-grassroots-silver-2018" not in chn.years[2017].ratings["development_quality"].observation_ids
    assert "fifa-structural-china-development-v1#chn-grassroots-silver-2018" in chn.years[2018].ratings["development_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#china-pr-p25" not in chn.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#china-pr-p25" in chn.years[2023].ratings["competition_quality"].observation_ids
    assert "fifa-structural-china-youth-2026-v1#chn-youth-three-star-2026" not in chn.years[2025].ratings["development_quality"].observation_ids
    assert "fifa-structural-china-youth-2026-v1#chn-youth-three-star-2026" in chn.years[2026].ratings["development_quality"].observation_ids

    tur = fifa.research.countries["TUR"]
    assert "fifa-structural-turkiye-history-v1#tur-national-pro-league-1959" not in tur.years[1958].ratings["competition_quality"].observation_ids
    assert "fifa-structural-turkiye-history-v1#tur-national-pro-league-1959" in tur.years[1959].ratings["competition_quality"].observation_ids
    assert "fifa-structural-turkiye-history-v1#tur-uefa-member-1962" not in tur.years[1961].ratings["competition_quality"].observation_ids
    assert "fifa-structural-turkiye-history-v1#tur-uefa-member-1962" in tur.years[1962].ratings["competition_quality"].observation_ids
    assert "fifa-structural-turkiye-history-v1#tur-autonomy-1988" not in tur.years[1987].ratings["development_quality"].observation_ids
    assert "fifa-structural-turkiye-history-v1#tur-autonomy-1988" in tur.years[1988].ratings["development_quality"].observation_ids
    assert "fifa-structural-turkiye-history-v1#tur-national-centre-2014" not in tur.years[2013].ratings["elite_support"].observation_ids
    assert "fifa-structural-turkiye-history-v1#tur-national-centre-2014" in tur.years[2014].ratings["elite_support"].observation_ids
    assert "fifa-professional-2023-clubs-v2#turkiye-p256" not in tur.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#turkiye-p256" in tur.years[2023].ratings["competition_quality"].observation_ids

    for code, model_id in {
        "PNG": "atp-earth-png-model.v1",
        "WSM": "atp-earth-wsm-model.v1",
    }.items():
        history = atp.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in atp.observations for item in rating.observation_ids)

    png = atp.research.countries["PNG"]
    assert "pre-association" in png.years[1955].territory_mapping_note
    assert "atp-png-foundation-v1#png-association-founded-1963" not in png.years[1962].ratings["squash_tradition"].observation_ids
    assert "atp-png-foundation-v1#png-association-founded-1963" in png.years[1963].ratings["squash_tradition"].observation_ids
    assert "atp-png-governance-2001-v1#png-development-mandate-2001" not in png.years[2000].ratings["development_quality"].observation_ids
    assert "atp-png-governance-2001-v1#png-development-mandate-2001" in png.years[2001].ratings["development_quality"].observation_ids
    assert "atp-pacific-juniors-2022-v1#png-west-pacific-juniors-2022" not in png.years[2021].ratings["development_quality"].observation_ids
    assert "atp-pacific-juniors-2022-v1#png-west-pacific-juniors-2022" in png.years[2022].ratings["development_quality"].observation_ids
    assert "atp-png-current-2026-v1#png-otf-member-2026" not in png.years[2025].ratings["squash_tradition"].observation_ids
    assert "atp-png-current-2026-v1#png-otf-member-2026" in png.years[2026].ratings["squash_tradition"].observation_ids

    wsm = atp.research.countries["WSM"]
    assert "New Zealand administration" in wsm.years[1961].historical_entity
    assert wsm.years[1962].historical_entity == "Western Samoa"
    assert wsm.years[1997].historical_entity == "Samoa"
    assert "atp-samoa-member-2012-v1#wsm-otf-member-2012" not in wsm.years[2011].ratings["squash_tradition"].observation_ids
    assert "atp-samoa-member-2012-v1#wsm-otf-member-2012" in wsm.years[2012].ratings["squash_tradition"].observation_ids
    assert "atp-pacific-juniors-2022-v1#wsm-pacific-juniors-2022" not in wsm.years[2021].ratings["development_quality"].observation_ids
    assert "atp-pacific-juniors-2022-v1#wsm-pacific-juniors-2022" in wsm.years[2022].ratings["development_quality"].observation_ids
    assert "atp-samoa-current-2026-v1#wsm-current-federation-2026" not in wsm.years[2025].ratings["development_quality"].observation_ids
    assert "atp-samoa-current-2026-v1#wsm-current-federation-2026" in wsm.years[2026].ratings["development_quality"].observation_ids

    for history in (chn, tur, png, wsm):
        assert max(r.value for r in history.years[2026].ratings.values()) < 9.0



def test_fifa_kor_tha_accelerated_batch_is_complete_and_time_gated():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))

    for code, model_id in {
        "KOR": "fifa-earth-kor-model.v1",
        "THA": "fifa-earth-tha-model.v1",
    }.items():
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    kor = bundle.research.countries["KOR"]
    assert "fifa-structural-kfa-history-v1#kor-professional-league-1983" not in kor.years[1982].ratings["competition_quality"].observation_ids
    assert "fifa-structural-kfa-history-v1#kor-professional-league-1983" in kor.years[1983].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-registered-v2#korea-republic" not in kor.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#korea-republic" in kor.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-professional-2023-clubs-v2#korea-republic-p36" in kor.years[2023].ratings["competition_quality"].observation_ids

    tha = bundle.research.countries["THA"]
    assert "fifa-big-count-2006-registered-v2#thailand" not in tha.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#thailand" in tha.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-structural-thailand-grassroots-v1#tha-grassroots-silver-2022" not in tha.years[2021].ratings["development_quality"].observation_ids
    assert "fifa-structural-thailand-grassroots-v1#tha-grassroots-silver-2022" in tha.years[2022].ratings["development_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#thailand-p57" in tha.years[2023].ratings["competition_quality"].observation_ids

    assert max(r.value for r in kor.years[2026].ratings.values()) < 9.0
    assert max(r.value for r in tha.years[2026].ratings.values()) < 9.0



def test_atp_slb_ton_accelerated_batch_is_complete_and_time_gated():
    bundle = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code, model_id in {
        "SLB": "atp-earth-slb-model.v1",
        "TON": "atp-earth-ton-model.v1",
    }.items():
        history = bundle.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in bundle.observations for item in rating.observation_ids)

    slb = bundle.research.countries["SLB"]
    assert "pre-association" in slb.years[1955].territory_mapping_note
    assert "atp-pacific-foundations-2015-v1#slb-association-founded-1993" not in slb.years[1992].ratings["squash_tradition"].observation_ids
    assert "atp-pacific-foundations-2015-v1#slb-association-founded-1993" in slb.years[1993].ratings["squash_tradition"].observation_ids
    assert "atp-pacific-otf-members-2012-v1#slb-otf-member-2012" not in slb.years[2011].ratings["elite_support"].observation_ids
    assert "atp-pacific-otf-members-2012-v1#slb-otf-member-2012" in slb.years[2012].ratings["elite_support"].observation_ids
    assert "atp-solomon-juniors-2022-v1#slb-west-pacific-juniors-2022" not in slb.years[2021].ratings["development_quality"].observation_ids
    assert "atp-solomon-juniors-2022-v1#slb-west-pacific-juniors-2022" in slb.years[2022].ratings["development_quality"].observation_ids

    ton = bundle.research.countries["TON"]
    assert "pre-association" in ton.years[1955].territory_mapping_note
    assert "atp-pacific-foundations-2015-v1#ton-association-founded-1959" not in ton.years[1958].ratings["squash_tradition"].observation_ids
    assert "atp-pacific-foundations-2015-v1#ton-association-founded-1959" in ton.years[1959].ratings["squash_tradition"].observation_ids
    assert "atp-tonga-juniors-2024-v1#ton-east-pacific-juniors-2024" not in ton.years[2023].ratings["development_quality"].observation_ids
    assert "atp-tonga-juniors-2024-v1#ton-east-pacific-juniors-2024" in ton.years[2024].ratings["development_quality"].observation_ids
    assert "atp-tonga-current-2026-v1#ton-current-federation-2026" in ton.years[2026].ratings["development_quality"].observation_ids

    assert max(r.value for r in slb.years[2026].ratings.values()) < 9.0
    assert max(r.value for r in ton.years[2026].ratings.values()) < 9.0



def test_accelerated_col_cyp_cok_ncl_batch_is_complete_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code, model_id in {
        "COL": "fifa-earth-col-model.v1",
        "CYP": "fifa-earth-cyp-model.v1",
    }.items():
        history = fifa.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in fifa.observations for item in rating.observation_ids)

    col = fifa.research.countries["COL"]
    assert "fifa-big-count-2006-registered-v2#colombia" not in col.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#colombia" in col.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-professional-2023-clubs-v2#colombia-p175" not in col.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#colombia-p175" in col.years[2023].ratings["competition_quality"].observation_ids

    cyp = fifa.research.countries["CYP"]
    assert "British Cyprus" in cyp.years[1959].historical_entity
    assert cyp.years[1960].historical_entity == "Cyprus"
    assert "fifa-structural-cyprus-history-v1#cyp-uefa-member-1962" not in cyp.years[1961].ratings["competition_quality"].observation_ids
    assert "fifa-structural-cyprus-history-v1#cyp-uefa-member-1962" in cyp.years[1962].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-registered-v2#cyprus" not in cyp.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#cyprus" in cyp.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-professional-2023-clubs-v2#cyprus-p214" not in cyp.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#cyprus-p214" in cyp.years[2023].ratings["competition_quality"].observation_ids
    assert "fifa-structural-cyprus-history-v1#cyp-current-club-structure-2026" not in cyp.years[2025].ratings["squash_access"].observation_ids
    assert "fifa-structural-cyprus-history-v1#cyp-current-club-structure-2026" in cyp.years[2026].ratings["squash_access"].observation_ids

    for code, model_id in {
        "COK": "atp-earth-cok-model.v1",
        "NCL": "atp-earth-ncl-model.v1",
    }.items():
        history = atp.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in atp.observations for item in rating.observation_ids)

    cok = atp.research.countries["COK"]
    assert "New Zealand administration" in cok.years[1964].historical_entity
    assert cok.years[1965].historical_entity == "Cook Islands"
    assert "atp-cook-development-2020-v1#cok-schools-islands-programme-2020" not in cok.years[2019].ratings["development_quality"].observation_ids
    assert "atp-cook-development-2020-v1#cok-schools-islands-programme-2020" in cok.years[2020].ratings["development_quality"].observation_ids
    assert "atp-cook-juniors-2022-v1#cok-east-pacific-juniors-2022" not in cok.years[2021].ratings["competition_quality"].observation_ids
    assert "atp-cook-juniors-2022-v1#cok-east-pacific-juniors-2022" in cok.years[2022].ratings["competition_quality"].observation_ids
    assert "atp-cook-current-2026-v1#cok-current-programmes-2026" not in cok.years[2025].ratings["squash_access"].observation_ids
    assert "atp-cook-current-2026-v1#cok-current-programmes-2026" in cok.years[2026].ratings["squash_access"].observation_ids

    ncl = atp.research.countries["NCL"]
    assert "atp-ncl-oceania-championships-v1#ncl-first-oceania-champs-2010" not in ncl.years[2009].ratings["competition_quality"].observation_ids
    assert "atp-ncl-oceania-championships-v1#ncl-first-oceania-champs-2010" in ncl.years[2010].ratings["competition_quality"].observation_ids
    assert "atp-ncl-oceania-championships-v1#ncl-oceania-champs-2012" not in ncl.years[2011].ratings["competition_quality"].observation_ids
    assert "atp-ncl-oceania-championships-v1#ncl-oceania-champs-2012" in ncl.years[2012].ratings["competition_quality"].observation_ids
    assert "atp-ncl-current-2026-v1#ncl-clubs-licensees-2026" not in ncl.years[2025].ratings["squash_access"].observation_ids
    assert "atp-ncl-current-2026-v1#ncl-clubs-licensees-2026" in ncl.years[2026].ratings["squash_access"].observation_ids
    assert "atp-ncl-otf-current-2026-v1#ncl-otf-associate-2026" in ncl.years[2026].ratings["squash_tradition"].observation_ids

    for history in (col, cyp, cok, ncl):
        assert max(r.value for r in history.years[2026].ratings.values()) < 9.0


def test_accelerated_ecu_irl_asm_vut_batch_is_complete_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code, model_id in {
        "ECU": "fifa-earth-ecu-model.v1",
        "IRL": "fifa-earth-irl-model.v1",
    }.items():
        history = fifa.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in fifa.observations for item in rating.observation_ids)

    ecu = fifa.research.countries["ECU"]
    assert "fifa-big-count-2006-registered-v2#ecuador" not in ecu.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#ecuador" in ecu.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-professional-2023-clubs-v2#ecuador-p176" not in ecu.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#ecuador-p176" in ecu.years[2023].ratings["competition_quality"].observation_ids

    irl = fifa.research.countries["IRL"]
    assert "fifa-big-count-2006-registered-v2#republic-of-ireland" not in irl.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#republic-of-ireland" in irl.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-structural-ireland-hq-2007-v1#irl-national-campus-hq-2007" not in irl.years[2006].ratings["development_quality"].observation_ids
    assert "fifa-structural-ireland-hq-2007-v1#irl-national-campus-hq-2007" in irl.years[2007].ratings["development_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#republic-of-ireland-p245" not in irl.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#republic-of-ireland-p245" in irl.years[2023].ratings["competition_quality"].observation_ids

    for code, model_id in {
        "ASM": "atp-earth-asm-model.v1",
        "VUT": "atp-earth-vut-model.v1",
    }.items():
        history = atp.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in atp.observations for item in rating.observation_ids)

    asm = atp.research.countries["ASM"]
    assert "pre-association" in asm.years[1984].territory_mapping_note
    assert "atp-american-samoa-history-v1#asm-asta-founded-1985" not in asm.years[1984].ratings["squash_tradition"].observation_ids
    assert "atp-american-samoa-history-v1#asm-asta-founded-1985" in asm.years[1985].ratings["squash_tradition"].observation_ids
    assert "atp-pacific-games-2019-asm-vut-v1#asm-pacific-games-2019" not in asm.years[2018].ratings["competition_quality"].observation_ids
    assert "atp-pacific-games-2019-asm-vut-v1#asm-pacific-games-2019" in asm.years[2019].ratings["competition_quality"].observation_ids
    assert "atp-american-samoa-history-v1#asm-pacific-nations-host-2025" not in asm.years[2024].ratings["squash_access"].observation_ids
    assert "atp-american-samoa-history-v1#asm-pacific-nations-host-2025" in asm.years[2025].ratings["squash_access"].observation_ids
    assert "atp-aopp-2026-asm-vut-v1#asm-aopp-2026" not in asm.years[2025].ratings["development_quality"].observation_ids
    assert "atp-aopp-2026-asm-vut-v1#asm-aopp-2026" in asm.years[2026].ratings["development_quality"].observation_ids

    vut = atp.research.countries["VUT"]
    assert "New Hebrides" in vut.years[1979].historical_entity
    assert vut.years[1980].historical_entity == "Vanuatu"
    assert "pre-direct-evidence" in vut.years[2009].territory_mapping_note
    assert "atp-vanuatu-activity-2010-v1#vut-federation-active-2010" not in vut.years[2009].ratings["development_quality"].observation_ids
    assert "atp-vanuatu-activity-2010-v1#vut-federation-active-2010" in vut.years[2010].ratings["development_quality"].observation_ids
    assert "atp-vanuatu-kindy-2014-v1#vut-kindy-tennis-2014" not in vut.years[2013].ratings["squash_access"].observation_ids
    assert "atp-vanuatu-kindy-2014-v1#vut-kindy-tennis-2014" in vut.years[2014].ratings["squash_access"].observation_ids
    assert "atp-pacific-games-2019-asm-vut-v1#vut-pacific-games-2019" not in vut.years[2018].ratings["competition_quality"].observation_ids
    assert "atp-pacific-games-2019-asm-vut-v1#vut-pacific-games-2019" in vut.years[2019].ratings["competition_quality"].observation_ids
    assert "atp-vanuatu-davis-2026-v1#vut-pacific-oceania-davis-2026" not in vut.years[2025].ratings["elite_support"].observation_ids
    assert "atp-vanuatu-davis-2026-v1#vut-pacific-oceania-davis-2026" in vut.years[2026].ratings["elite_support"].observation_ids

    for history in (ecu, irl, asm, vut):
        assert max(r.value for r in history.years[2026].ratings.values()) < 9.0


def test_accelerated_egy_mys_dual_world_batch_is_complete_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code, model_id in {
        "EGY": "fifa-earth-egy-model.v1",
        "MYS": "fifa-earth-mys-model.v1",
    }.items():
        history = fifa.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in fifa.observations for item in rating.observation_ids)

    egy_f = fifa.research.countries["EGY"]
    assert "fifa-structural-egypt-history-v1#egy-caf-affiliation-1957" not in egy_f.years[1956].ratings["competition_quality"].observation_ids
    assert "fifa-structural-egypt-history-v1#egy-caf-affiliation-1957" in egy_f.years[1957].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-registered-v2#egypt" not in egy_f.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#egypt" in egy_f.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-structural-egypt-hq-2021-v1#egy-new-headquarters-2021" not in egy_f.years[2020].ratings["development_quality"].observation_ids
    assert "fifa-structural-egypt-hq-2021-v1#egy-new-headquarters-2021" in egy_f.years[2021].ratings["development_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#egypt-p85" not in egy_f.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#egypt-p85" in egy_f.years[2023].ratings["competition_quality"].observation_ids

    mys_f = fifa.research.countries["MYS"]
    assert "partly represented" in mys_f.years[1962].historical_entity
    assert mys_f.years[1963].historical_entity == "Malaysia"
    assert "fifa-big-count-2006-registered-v2#malaysia" not in mys_f.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#malaysia" in mys_f.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-structural-malaysia-statutes-2023-v1#mys-current-membership-development-2023" not in mys_f.years[2022].ratings["development_quality"].observation_ids
    assert "fifa-structural-malaysia-statutes-2023-v1#mys-current-membership-development-2023" in mys_f.years[2023].ratings["development_quality"].observation_ids
    assert "fifa-structural-malaysia-ntc-2024-v1#mys-ntc-groundbreaking-2024" not in mys_f.years[2023].ratings["elite_support"].observation_ids
    assert "fifa-structural-malaysia-ntc-2024-v1#mys-ntc-groundbreaking-2024" in mys_f.years[2024].ratings["elite_support"].observation_ids

    for code, model_id in {
        "EGY": "atp-earth-egy-model.v1",
        "MYS": "atp-earth-mys-model.v1",
    }.items():
        history = atp.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in atp.observations for item in rating.observation_ids)

    egy_a = atp.research.countries["EGY"]
    assert "atp-egypt-history-v1#egy-current-name-1976" not in egy_a.years[1975].ratings["squash_tradition"].observation_ids
    assert "atp-egypt-history-v1#egy-current-name-1976" in egy_a.years[1976].ratings["squash_tradition"].observation_ids
    assert "atp-egypt-league-2024-v1#egy-club-league-2024" not in egy_a.years[2023].ratings["competition_quality"].observation_ids
    assert "atp-egypt-league-2024-v1#egy-club-league-2024" in egy_a.years[2024].ratings["competition_quality"].observation_ids

    mys_a = atp.research.countries["MYS"]
    assert "partly represented" in mys_a.years[1962].historical_entity
    assert mys_a.years[1963].historical_entity == "Malaysia"
    assert "atp-malaysia-history-v1#mys-ltam-itf-1965" not in mys_a.years[1964].ratings["competition_quality"].observation_ids
    assert "atp-malaysia-history-v1#mys-ltam-itf-1965" in mys_a.years[1965].ratings["competition_quality"].observation_ids
    assert "atp-malaysia-history-v1#mys-national-academy-2014" not in mys_a.years[2013].ratings["development_quality"].observation_ids
    assert "atp-malaysia-history-v1#mys-national-academy-2014" in mys_a.years[2014].ratings["development_quality"].observation_ids
    assert "atp-malaysia-calendar-2026-v1#mys-itf-events-2026" not in mys_a.years[2025].ratings["competition_quality"].observation_ids
    assert "atp-malaysia-calendar-2026-v1#mys-itf-events-2026" in mys_a.years[2026].ratings["competition_quality"].observation_ids

    for history in (egy_f, mys_f, egy_a, mys_a):
        assert max(r.value for r in history.years[2026].ratings.values()) < 9.0


def test_accelerated_sau_are_phl_idn_batch_is_complete_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code, model_id in {
        "SAU": "fifa-earth-sau-model.v1",
        "ARE": "fifa-earth-are-model.v1",
    }.items():
        history = fifa.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in fifa.observations for item in rating.observation_ids)

    sau = fifa.research.countries["SAU"]
    assert "fifa-structural-saff-history-v1#sau-fifa-recognized-1956" not in sau.years[1955].ratings["competition_quality"].observation_ids
    assert "fifa-structural-saff-history-v1#sau-fifa-recognized-1956" in sau.years[1956].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-registered-v2#saudi-arabia" not in sau.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#saudi-arabia" in sau.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-professional-2023-clubs-v2#saudi-arabia-p52" not in sau.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#saudi-arabia-p52" in sau.years[2023].ratings["competition_quality"].observation_ids

    are = fifa.research.countries["ARE"]
    assert "Trucial States" in are.years[1970].historical_entity
    assert are.years[1971].historical_entity == "United Arab Emirates"
    assert "pre-national-federation" in are.years[1970].territory_mapping_note
    assert "fifa-structural-uaefa-history-v1#are-federation-founded-1971" not in are.years[1970].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-uaefa-history-v1#are-federation-founded-1971" in are.years[1971].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-uaefa-history-v1#are-fifa-member-1972" not in are.years[1971].ratings["competition_quality"].observation_ids
    assert "fifa-structural-uaefa-history-v1#are-fifa-member-1972" in are.years[1972].ratings["competition_quality"].observation_ids
    assert "fifa-structural-uaefa-history-v1#are-afc-member-1974" not in are.years[1973].ratings["competition_quality"].observation_ids
    assert "fifa-structural-uaefa-history-v1#are-afc-member-1974" in are.years[1974].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#united-arab-emirates-p60" not in are.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#united-arab-emirates-p60" in are.years[2023].ratings["competition_quality"].observation_ids

    for code, model_id in {
        "PHL": "atp-earth-phl-model.v1",
        "IDN": "atp-earth-idn-model.v1",
    }.items():
        history = atp.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in atp.observations for item in rating.observation_ids)

    phl = atp.research.countries["PHL"]
    assert "atp-philippines-governance-v1#phl-itf-suspension-2020" not in phl.years[2019].ratings["competition_quality"].observation_ids
    assert "atp-philippines-governance-v1#phl-itf-suspension-2020" in phl.years[2020].ratings["competition_quality"].observation_ids
    assert phl.years[2020].ratings["competition_quality"].value < phl.years[2019].ratings["competition_quality"].value
    assert "atp-philippines-reinstatement-v1#phl-itf-reinstated-2024" not in phl.years[2023].ratings["competition_quality"].observation_ids
    assert "atp-philippines-reinstatement-v1#phl-itf-reinstated-2024" in phl.years[2024].ratings["competition_quality"].observation_ids
    assert "atp-philippines-current-2026-v1#phl-itf-member-2026" not in phl.years[2025].ratings["squash_tradition"].observation_ids
    assert "atp-philippines-current-2026-v1#phl-itf-member-2026" in phl.years[2026].ratings["squash_tradition"].observation_ids

    idn = atp.research.countries["IDN"]
    assert idn.years[1955].historical_entity == "Indonesia"
    assert "atp-indonesia-jti-v1#idn-jti-joined-2019" not in idn.years[2018].ratings["development_quality"].observation_ids
    assert "atp-indonesia-jti-v1#idn-jti-joined-2019" in idn.years[2019].ratings["development_quality"].observation_ids
    assert "atp-indonesia-jti-v1#idn-jti-participants-2020" not in idn.years[2019].ratings["squash_access"].observation_ids
    assert "atp-indonesia-jti-v1#idn-jti-participants-2020" in idn.years[2020].ratings["squash_access"].observation_ids
    assert "atp-indonesia-jti-v1#idn-coach-education-bronze-2021" not in idn.years[2020].ratings["elite_support"].observation_ids
    assert "atp-indonesia-jti-v1#idn-coach-education-bronze-2021" in idn.years[2021].ratings["elite_support"].observation_ids
    assert "atp-indonesia-w25-2023-v1#idn-w25-jakarta-2023" not in idn.years[2022].ratings["competition_quality"].observation_ids
    assert "atp-indonesia-w25-2023-v1#idn-w25-jakarta-2023" in idn.years[2023].ratings["competition_quality"].observation_ids
    assert "atp-indonesia-current-2025-v1#idn-itf-member-2025" not in idn.years[2024].ratings["squash_tradition"].observation_ids
    assert "atp-indonesia-current-2025-v1#idn-itf-member-2025" in idn.years[2025].ratings["squash_tradition"].observation_ids

    for history in (sau, are, phl, idn):
        assert max(r.value for r in history.years[2026].ratings.values()) < 9.0


def test_accelerated_qat_omn_sgp_pak_batch_is_complete_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for code, model_id in {
        "QAT": "fifa-earth-qat-model.v1",
        "OMN": "fifa-earth-omn-model.v1",
    }.items():
        history = fifa.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in fifa.observations for item in rating.observation_ids)

    qat = fifa.research.countries["QAT"]
    assert "British protection" in qat.years[1970].historical_entity
    assert qat.years[1971].historical_entity == "Qatar"
    assert "fifa-structural-qfa-history-v1#qat-qfa-founded-1960" not in qat.years[1959].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-qfa-history-v1#qat-qfa-founded-1960" in qat.years[1960].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-qfa-history-v1#qat-fifa-member-1963" not in qat.years[1962].ratings["competition_quality"].observation_ids
    assert "fifa-structural-qfa-history-v1#qat-fifa-member-1963" in qat.years[1963].ratings["competition_quality"].observation_ids
    assert "fifa-structural-qfa-history-v1#qat-afc-member-1967" not in qat.years[1966].ratings["competition_quality"].observation_ids
    assert "fifa-structural-qfa-history-v1#qat-afc-member-1967" in qat.years[1967].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-registered-v2#qatar" not in qat.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#qatar" in qat.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-professional-2023-clubs-v2#qatar-p51" not in qat.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#qatar-p51" in qat.years[2023].ratings["competition_quality"].observation_ids
    assert "fifa-structural-qfa-strategy-2024-v1#qat-strategy-2024" not in qat.years[2023].ratings["development_quality"].observation_ids
    assert "fifa-structural-qfa-strategy-2024-v1#qat-strategy-2024" in qat.years[2024].ratings["development_quality"].observation_ids

    omn = fifa.research.countries["OMN"]
    assert "Muscat and Oman" in omn.years[1969].historical_entity
    assert omn.years[1970].historical_entity == "Oman"
    assert "fifa-structural-oman-cup-v1#omn-cup-eight-clubs-1972" not in omn.years[1971].ratings["competition_quality"].observation_ids
    assert "fifa-structural-oman-cup-v1#omn-cup-eight-clubs-1972" in omn.years[1972].ratings["competition_quality"].observation_ids
    assert "fifa-structural-ofa-history-v1#omn-ofa-founded-fifa-1978" not in omn.years[1977].ratings["elite_support"].observation_ids
    assert "fifa-structural-ofa-history-v1#omn-ofa-founded-fifa-1978" in omn.years[1978].ratings["elite_support"].observation_ids
    assert "fifa-structural-ofa-history-v1#omn-afc-member-1980" not in omn.years[1979].ratings["competition_quality"].observation_ids
    assert "fifa-structural-ofa-history-v1#omn-afc-member-1980" in omn.years[1980].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-registered-v2#oman" not in omn.years[2005].ratings["squash_access"].observation_ids
    assert "fifa-big-count-2006-registered-v2#oman" in omn.years[2006].ratings["squash_access"].observation_ids
    assert "fifa-professional-2023-clubs-v2#oman-p47" not in omn.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#oman-p47" in omn.years[2023].ratings["competition_quality"].observation_ids
    assert "fifa-structural-ofa-history-v1#omn-current-44-clubs-2026" not in omn.years[2025].ratings["squash_access"].observation_ids
    assert "fifa-structural-ofa-history-v1#omn-current-44-clubs-2026" in omn.years[2026].ratings["squash_access"].observation_ids

    for code, model_id in {
        "SGP": "atp-earth-sgp-model.v1",
        "PAK": "atp-earth-pak-model.v1",
    }.items():
        history = atp.research.countries[code]
        assert history.missing_earth_years == []
        assert len(history.years) == 72
        assert history.reference_year == 2026
        for year in history.years.values():
            for rating in year.ratings.values():
                assert rating.calibration_model_id == model_id
                assert rating.observation_ids
                assert all(item in atp.observations for item in rating.observation_ids)

    sgp = atp.research.countries["SGP"]
    assert "Colony of Singapore" in sgp.years[1962].historical_entity
    assert "within Malaysia" in sgp.years[1963].historical_entity
    assert sgp.years[1965].historical_entity == "Singapore"
    assert "atp-sgp-pak-jti-2021-v1#sgp-jti-active-2021" not in sgp.years[2020].ratings["development_quality"].observation_ids
    assert "atp-sgp-pak-jti-2021-v1#sgp-jti-active-2021" in sgp.years[2021].ratings["development_quality"].observation_ids
    assert "atp-singapore-j60-2026-v1#sgp-j60-kallang-2026" not in sgp.years[2025].ratings["competition_quality"].observation_ids
    assert "atp-singapore-j60-2026-v1#sgp-j60-kallang-2026" in sgp.years[2026].ratings["competition_quality"].observation_ids

    pak = atp.research.countries["PAK"]
    for year in (1955, 2026):
        ids = pak.years[year].ratings["squash_tradition"].observation_ids
        assert "atp-sgp-pak-foundation-v1#pak-association-founded-1947-itf" in ids
        assert "atp-pakistan-history-v1#pak-functional-since-1948" in ids
    assert "atp-pakistan-coach-development-v1#pak-coach-education-bronze-2020" not in pak.years[2019].ratings["development_quality"].observation_ids
    assert "atp-pakistan-coach-development-v1#pak-coach-education-bronze-2020" in pak.years[2020].ratings["development_quality"].observation_ids
    assert "atp-sgp-pak-jti-2021-v1#pak-jti-active-2021" not in pak.years[2020].ratings["development_quality"].observation_ids
    assert "atp-sgp-pak-jti-2021-v1#pak-jti-active-2021" in pak.years[2021].ratings["development_quality"].observation_ids
    assert "atp-pakistan-challenger-2025-v1#pak-islamabad-challenger-2025" not in pak.years[2024].ratings["competition_quality"].observation_ids
    assert "atp-pakistan-challenger-2025-v1#pak-islamabad-challenger-2025" in pak.years[2025].ratings["competition_quality"].observation_ids

    for history in (qat, omn, sgp, pak):
        assert max(r.value for r in history.years[2026].ratings.values()) < 9.0

def test_ghana_nigeria_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (
            fifa,
            {
                "GHA": "fifa-earth-gha-model.v1",
                "NGA": "fifa-earth-nga-model.v1",
            },
        ),
        (
            atp,
            {
                "GHA": "atp-earth-gha-model.v1",
                "NGA": "atp-earth-nga-model.v1",
            },
        ),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            assert history.reference_year == 2026
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.method == "derived_estimate"
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    # Ghana's CAF source chronology is intentionally preserved rather than silently
    # repaired: the page gives CAF affiliation 1956 but association creation 1957.
    gha_caf = fifa.observations[
        "fifa-structural-ghana-history-v1#gha-caf-affiliation-1956"
    ]
    gha_created = fifa.observations[
        "fifa-structural-ghana-history-v1#gha-created-1957"
    ]
    assert "source_internal_chronology_anomaly" in gha_caf.quality_flags
    assert "source_internal_chronology_anomaly" in gha_created.quality_flags
    assert (
        "fifa-structural-ghana-history-v1#gha-caf-affiliation-1956"
        not in fifa.research.countries["GHA"].years[1955]
        .ratings["competition_quality"]
        .observation_ids
    )
    assert (
        "fifa-structural-ghana-history-v1#gha-caf-affiliation-1956"
        in fifa.research.countries["GHA"].years[1956]
        .ratings["competition_quality"]
        .observation_ids
    )

    # Shared FIFA source families are strictly time gated.
    assert (
        "fifa-big-count-2006-all-players-v2#ghana"
        not in fifa.research.countries["GHA"].years[2005]
        .ratings["squash_popularity"]
        .observation_ids
    )
    assert (
        "fifa-big-count-2006-all-players-v2#ghana"
        in fifa.research.countries["GHA"].years[2006]
        .ratings["squash_popularity"]
        .observation_ids
    )
    assert (
        "fifa-professional-2023-players-v2#nigeria-p108"
        not in fifa.research.countries["NGA"].years[2022]
        .ratings["competition_quality"]
        .observation_ids
    )
    assert (
        "fifa-professional-2023-players-v2#nigeria-p108"
        in fifa.research.countries["NGA"].years[2023]
        .ratings["competition_quality"]
        .observation_ids
    )

    # Nigeria's institutional chronology also enters only at its stated dates.
    nga_fifa = fifa.research.countries["NGA"]
    assert (
        "fifa-structural-nigeria-history-v1#nga-caf-affiliation-1957"
        not in nga_fifa.years[1956].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-nigeria-history-v1#nga-caf-affiliation-1957"
        in nga_fifa.years[1957].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-nigeria-history-v1#nga-fifa-affiliation-1960"
        not in nga_fifa.years[1959].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-nigeria-history-v1#nga-fifa-affiliation-1960"
        in nga_fifa.years[1960].ratings["competition_quality"].observation_ids
    )

    # The historical tennis anchors are explicitly secondary-source evidence.
    assert "secondary_source" in atp.observations[
        "atp-ghana-history-v1#gha-amateur-lawn-tennis-association-1952"
    ].quality_flags
    assert "secondary_source" in atp.observations[
        "atp-nigeria-history-v1#nga-association-formed-1954"
    ].quality_flags

    gha_atp = atp.research.countries["GHA"]
    assert (
        "atp-ghana-current-v1#gha-junior-championships-2024"
        not in gha_atp.years[2023].ratings["development_quality"].observation_ids
    )
    assert (
        "atp-ghana-current-v1#gha-junior-championships-2024"
        in gha_atp.years[2024].ratings["development_quality"].observation_ids
    )
    assert (
        "atp-ghana-current-v1#gha-davis-zone-iii-2026"
        not in gha_atp.years[2025].ratings["competition_quality"].observation_ids
    )
    assert (
        "atp-ghana-masters-2026-v1#gha-mt100-hosting-2026"
        not in gha_atp.years[2025].ratings["competition_quality"].observation_ids
    )
    assert (
        "atp-ghana-current-v1#gha-davis-zone-iii-2026"
        in gha_atp.years[2026].ratings["competition_quality"].observation_ids
    )
    assert (
        "atp-ghana-masters-2026-v1#gha-mt100-hosting-2026"
        in gha_atp.years[2026].ratings["competition_quality"].observation_ids
    )

    nga_atp = atp.research.countries["NGA"]
    assert (
        "atp-nigeria-governance-2025-v1#nga-development-programmes-2025"
        not in nga_atp.years[2024].ratings["development_quality"].observation_ids
    )
    assert (
        "atp-nigeria-governance-2025-v1#nga-development-programmes-2025"
        in nga_atp.years[2025].ratings["development_quality"].observation_ids
    )
    assert (
        "atp-nigeria-m25-2026-v1#nga-m25-lagos-2026"
        not in nga_atp.years[2025].ratings["competition_quality"].observation_ids
    )
    assert (
        "atp-nigeria-m25-2026-v1#nga-m25-lagos-2026"
        in nga_atp.years[2026].ratings["competition_quality"].observation_ids
    )

def test_kenya_uganda_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (
            fifa,
            {
                "KEN": "fifa-earth-ken-model.v1",
                "UGA": "fifa-earth-uga-model.v1",
            },
        ),
        (
            atp,
            {
                "KEN": "atp-earth-ken-model.v1",
                "UGA": "atp-earth-uga-model.v1",
            },
        ),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            assert history.reference_year == 2026
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.method == "derived_estimate"
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    ken_fifa = fifa.research.countries["KEN"]
    assert (
        "fifa-structural-kenya-history-v1#ken-created-fifa-1960"
        not in ken_fifa.years[1959].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-kenya-history-v1#ken-created-fifa-1960"
        in ken_fifa.years[1960].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-kenya-history-v1#ken-caf-affiliation-1968"
        not in ken_fifa.years[1967].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-kenya-history-v1#ken-caf-affiliation-1968"
        in ken_fifa.years[1968].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-big-count-2006-all-players-v2#kenya"
        not in ken_fifa.years[2005].ratings["squash_popularity"].observation_ids
    )
    assert (
        "fifa-big-count-2006-all-players-v2#kenya"
        in ken_fifa.years[2006].ratings["squash_popularity"].observation_ids
    )
    assert (
        "fifa-professional-2023-clubs-v2#kenya-p95"
        not in ken_fifa.years[2022].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-professional-2023-clubs-v2#kenya-p95"
        in ken_fifa.years[2023].ratings["competition_quality"].observation_ids
    )
    assert all(
        "fifa-professional-2023-players-v2#kenya" not in observation_id
        for year in ken_fifa.years.values()
        for rating in year.ratings.values()
        for observation_id in rating.observation_ids
    )

    uga_fifa = fifa.research.countries["UGA"]
    assert (
        "fifa-structural-uganda-history-v1#uga-fifa-caf-1960"
        not in uga_fifa.years[1959].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-uganda-history-v1#uga-fifa-caf-1960"
        in uga_fifa.years[1960].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-professional-2023-players-v2#uganda-p121"
        not in uga_fifa.years[2022].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-professional-2023-players-v2#uganda-p121"
        in uga_fifa.years[2023].ratings["competition_quality"].observation_ids
    )

    # Early tennis chronology is explicitly secondary-source evidence.
    assert "secondary_source" in atp.observations[
        "atp-kenya-history-v1#ken-association-inception-1922"
    ].quality_flags
    assert "secondary_source" in atp.observations[
        "atp-uganda-history-v1#uga-association-founded-1948"
    ].quality_flags

    ken_atp = atp.research.countries["KEN"]
    assert (
        "atp-kenya-jti-2026-v1#ken-jti-pathway-2026"
        not in ken_atp.years[2025].ratings["development_quality"].observation_ids
    )
    assert (
        "atp-kenya-jti-2026-v1#ken-jti-pathway-2026"
        in ken_atp.years[2026].ratings["development_quality"].observation_ids
    )

    uga_atp = atp.research.countries["UGA"]
    assert (
        "atp-uganda-development-2025-v1#uga-jti-grassroots-by-2022"
        not in uga_atp.years[2021].ratings["development_quality"].observation_ids
    )
    assert (
        "atp-uganda-development-2025-v1#uga-jti-grassroots-by-2022"
        in uga_atp.years[2022].ratings["development_quality"].observation_ids
    )
    assert (
        "atp-uganda-development-2025-v1#uga-international-hosting-by-2022"
        not in uga_atp.years[2021].ratings["competition_quality"].observation_ids
    )
    assert (
        "atp-uganda-development-2025-v1#uga-international-hosting-by-2022"
        in uga_atp.years[2022].ratings["competition_quality"].observation_ids
    )
    assert (
        "atp-uganda-registration-2026-v1#uga-national-registration-2026"
        not in uga_atp.years[2025].ratings["elite_support"].observation_ids
    )
    assert (
        "atp-uganda-registration-2026-v1#uga-national-registration-2026"
        in uga_atp.years[2026].ratings["elite_support"].observation_ids
    )

def test_tanzania_zambia_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (
            fifa,
            {
                "TZA": "fifa-earth-tza-model.v1",
                "ZMB": "fifa-earth-zmb-model.v1",
            },
        ),
        (
            atp,
            {
                "TZA": "atp-earth-tza-model.v1",
                "ZMB": "atp-earth-zmb-model.v1",
            },
        ),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            assert history.reference_year == 2026
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.method == "derived_estimate"
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    tza_fifa = fifa.research.countries["TZA"]
    assert (
        "fifa-structural-tanzania-history-v1#tza-fifa-caf-1964"
        not in tza_fifa.years[1963].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-tanzania-history-v1#tza-fifa-caf-1964"
        in tza_fifa.years[1964].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-big-count-2006-all-players-v2#tanzania"
        not in tza_fifa.years[2005].ratings["squash_popularity"].observation_ids
    )
    assert (
        "fifa-big-count-2006-all-players-v2#tanzania"
        in tza_fifa.years[2006].ratings["squash_popularity"].observation_ids
    )
    assert (
        "fifa-professional-2023-clubs-v2#tanzania-p118"
        not in tza_fifa.years[2022].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-professional-2023-clubs-v2#tanzania-p118"
        in tza_fifa.years[2023].ratings["competition_quality"].observation_ids
    )
    assert all(
        "fifa-professional-2023-players-v2#tanzania" not in observation_id
        for year in tza_fifa.years.values()
        for rating in year.ratings.values()
        for observation_id in rating.observation_ids
    )

    zmb_fifa = fifa.research.countries["ZMB"]
    assert (
        "fifa-structural-zambia-history-v1#zmb-fifa-caf-1964"
        not in zmb_fifa.years[1963].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-zambia-history-v1#zmb-fifa-caf-1964"
        in zmb_fifa.years[1964].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-professional-2023-clubs-v2#zambia-p122"
        not in zmb_fifa.years[2022].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-professional-2023-clubs-v2#zambia-p122"
        in zmb_fifa.years[2023].ratings["competition_quality"].observation_ids
    )
    assert all(
        "fifa-professional-2023-players-v2#zambia" not in observation_id
        for year in zmb_fifa.years.values()
        for rating in year.ratings.values()
        for observation_id in rating.observation_ids
    )

    tza_atp = atp.research.countries["TZA"]
    assert "derived_pre_evidence_context" in atp.observations[
        "atp-tanzania-membership-v1#tza-pre-documented-baseline-1955-2014"
    ].quality_flags
    assert (
        "atp-tanzania-membership-v1#tza-itf-member-2015"
        not in tza_atp.years[2014].ratings["squash_tradition"].observation_ids
    )
    assert (
        "atp-tanzania-membership-v1#tza-itf-member-2015"
        in tza_atp.years[2015].ratings["squash_tradition"].observation_ids
    )
    assert (
        "atp-tanzania-world-team-cup-2025-v1#tza-womens-world-group-2025"
        not in tza_atp.years[2024].ratings["competition_quality"].observation_ids
    )
    assert (
        "atp-tanzania-world-team-cup-2025-v1#tza-womens-world-group-2025"
        in tza_atp.years[2025].ratings["competition_quality"].observation_ids
    )

    zmb_atp = atp.research.countries["ZMB"]
    assert "derived_pre_evidence_context" in atp.observations[
        "atp-zambia-history-v1#zmb-pre-documented-baseline-1955-2006"
    ].quality_flags
    assert (
        "atp-zambia-history-v1#zmb-active-association-2007"
        not in zmb_atp.years[2006].ratings["squash_tradition"].observation_ids
    )
    assert (
        "atp-zambia-history-v1#zmb-active-association-2007"
        in zmb_atp.years[2007].ratings["squash_tradition"].observation_ids
    )
    assert (
        "atp-zambia-reinstatement-2025-v1#zmb-itf-reinstated-2025"
        not in zmb_atp.years[2024].ratings["elite_support"].observation_ids
    )
    assert (
        "atp-zambia-reinstatement-2025-v1#zmb-itf-reinstated-2025"
        in zmb_atp.years[2025].ratings["elite_support"].observation_ids
    )
    assert (
        "atp-zambia-j30-2026-v1#zmb-j30-hosting-2026"
        not in zmb_atp.years[2025].ratings["competition_quality"].observation_ids
    )
    assert (
        "atp-zambia-j30-2026-v1#zmb-j30-hosting-2026"
        in zmb_atp.years[2026].ratings["competition_quality"].observation_ids
    )

def test_zimbabwe_malawi_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (
            fifa,
            {
                "ZWE": "fifa-earth-zwe-model.v1",
                "MWI": "fifa-earth-mwi-model.v1",
            },
        ),
        (
            atp,
            {
                "ZWE": "atp-earth-zwe-model.v1",
                "MWI": "atp-earth-mwi-model.v1",
            },
        ),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            assert history.reference_year == 2026
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.method == "derived_estimate"
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    zwe_fifa = fifa.research.countries["ZWE"]
    assert (
        "fifa-structural-zimbabwe-history-v1#zwe-created-fifa-1965"
        not in zwe_fifa.years[1964].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-zimbabwe-history-v1#zwe-created-fifa-1965"
        in zwe_fifa.years[1965].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-zimbabwe-history-v1#zwe-caf-affiliation-1980"
        not in zwe_fifa.years[1979].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-zimbabwe-history-v1#zwe-caf-affiliation-1980"
        in zwe_fifa.years[1980].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-big-count-2006-all-players-v2#zimbabwe"
        not in zwe_fifa.years[2005].ratings["squash_popularity"].observation_ids
    )
    assert (
        "fifa-big-count-2006-all-players-v2#zimbabwe"
        in zwe_fifa.years[2006].ratings["squash_popularity"].observation_ids
    )
    assert (
        "fifa-professional-2023-players-v2#zimbabwe-p123"
        not in zwe_fifa.years[2022].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-professional-2023-players-v2#zimbabwe-p123"
        in zwe_fifa.years[2023].ratings["competition_quality"].observation_ids
    )

    mwi_fifa = fifa.research.countries["MWI"]
    assert (
        "fifa-structural-malawi-history-v1#mwi-created-1966"
        not in mwi_fifa.years[1965].ratings["squash_tradition"].observation_ids
    )
    assert (
        "fifa-structural-malawi-history-v1#mwi-created-1966"
        in mwi_fifa.years[1966].ratings["squash_tradition"].observation_ids
    )
    assert (
        "fifa-structural-malawi-history-v1#mwi-fifa-caf-1968"
        not in mwi_fifa.years[1967].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-malawi-history-v1#mwi-fifa-caf-1968"
        in mwi_fifa.years[1968].ratings["competition_quality"].observation_ids
    )
    assert all(
        "fifa-professional-2023" not in source_id
        for year in mwi_fifa.years.values()
        for rating in year.ratings.values()
        for source_id in rating.source_ids
    )

    zwe_atp = atp.research.countries["ZWE"]
    assert "derived_pre_evidence_context" in atp.observations[
        "atp-zimbabwe-history-v1#zwe-pre-documented-baseline-1955-2019"
    ].quality_flags
    assert (
        "atp-zimbabwe-history-v1#zwe-play-possible-2020"
        not in zwe_atp.years[2019].ratings["squash_access"].observation_ids
    )
    assert (
        "atp-zimbabwe-history-v1#zwe-play-possible-2020"
        in zwe_atp.years[2020].ratings["squash_access"].observation_ids
    )
    assert (
        "atp-zimbabwe-development-2026-v1#zwe-eligible-2026"
        not in zwe_atp.years[2025].ratings["development_quality"].observation_ids
    )
    assert (
        "atp-zimbabwe-development-2026-v1#zwe-eligible-2026"
        in zwe_atp.years[2026].ratings["development_quality"].observation_ids
    )
    assert (
        "atp-zimbabwe-j100-2026-v1#zwe-j100-harare-2026"
        not in zwe_atp.years[2025].ratings["competition_quality"].observation_ids
    )
    assert (
        "atp-zimbabwe-j100-2026-v1#zwe-j100-harare-2026"
        in zwe_atp.years[2026].ratings["competition_quality"].observation_ids
    )

    mwi_atp = atp.research.countries["MWI"]
    assert "derived_pre_evidence_context" in atp.observations[
        "atp-malawi-history-v1#mwi-pre-documented-baseline-1955-2019"
    ].quality_flags
    assert (
        "atp-malawi-history-v1#mwi-play-possible-2020"
        not in mwi_atp.years[2019].ratings["squash_access"].observation_ids
    )
    assert (
        "atp-malawi-history-v1#mwi-play-possible-2020"
        in mwi_atp.years[2020].ratings["squash_access"].observation_ids
    )
    assert (
        "atp-malawi-development-2026-v1#mwi-eligible-2026"
        not in mwi_atp.years[2025].ratings["development_quality"].observation_ids
    )
    assert (
        "atp-malawi-development-2026-v1#mwi-eligible-2026"
        in mwi_atp.years[2026].ratings["development_quality"].observation_ids
    )

def test_botswana_namibia_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (
            fifa,
            {
                "BWA": "fifa-earth-bwa-model.v1",
                "NAM": "fifa-earth-nam-model.v1",
            },
        ),
        (
            atp,
            {
                "BWA": "atp-earth-bwa-model.v1",
                "NAM": "atp-earth-nam-model.v1",
            },
        ),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            assert history.reference_year == 2026
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.method == "derived_estimate"
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    bwa_fifa = fifa.research.countries["BWA"]
    assert (
        "fifa-structural-botswana-history-v1#bwa-created-1970"
        not in bwa_fifa.years[1969].ratings["squash_tradition"].observation_ids
    )
    assert (
        "fifa-structural-botswana-history-v1#bwa-created-1970"
        in bwa_fifa.years[1970].ratings["squash_tradition"].observation_ids
    )
    assert (
        "fifa-structural-botswana-history-v1#bwa-caf-1976"
        not in bwa_fifa.years[1975].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-botswana-history-v1#bwa-caf-1976"
        in bwa_fifa.years[1976].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-botswana-history-v1#bwa-fifa-1982"
        not in bwa_fifa.years[1981].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-botswana-history-v1#bwa-fifa-1982"
        in bwa_fifa.years[1982].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-professional-2023-players-v2#botswana-p73"
        not in bwa_fifa.years[2022].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-professional-2023-players-v2#botswana-p73"
        in bwa_fifa.years[2023].ratings["competition_quality"].observation_ids
    )

    nam_fifa = fifa.research.countries["NAM"]
    assert (
        "fifa-structural-namibia-history-v1#nam-created-1990"
        not in nam_fifa.years[1989].ratings["squash_tradition"].observation_ids
    )
    assert (
        "fifa-structural-namibia-history-v1#nam-created-1990"
        in nam_fifa.years[1990].ratings["squash_tradition"].observation_ids
    )
    assert (
        "fifa-structural-namibia-history-v1#nam-fifa-caf-1992"
        not in nam_fifa.years[1991].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-namibia-history-v1#nam-fifa-caf-1992"
        in nam_fifa.years[1992].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-professional-2023-clubs-v2#namibia-p106"
        in nam_fifa.years[2023].ratings["competition_quality"].observation_ids
    )
    assert all(
        "fifa-professional-2023-players-v2#namibia" not in observation_id
        for year in nam_fifa.years.values()
        for rating in year.ratings.values()
        for observation_id in rating.observation_ids
    )

    bwa_atp = atp.research.countries["BWA"]
    assert "derived_pre_evidence_context" in atp.observations[
        "atp-botswana-history-v1#bwa-pre-documented-baseline-1955-2019"
    ].quality_flags
    assert (
        "atp-botswana-history-v1#bwa-play-possible-2020"
        not in bwa_atp.years[2019].ratings["squash_access"].observation_ids
    )
    assert (
        "atp-botswana-history-v1#bwa-play-possible-2020"
        in bwa_atp.years[2020].ratings["squash_access"].observation_ids
    )
    assert (
        "atp-botswana-development-2026-v1#bwa-eligible-2026"
        in bwa_atp.years[2026].ratings["development_quality"].observation_ids
    )
    assert (
        "atp-botswana-events-2026-v1#bwa-w15-gaborone-2026"
        in bwa_atp.years[2026].ratings["competition_quality"].observation_ids
    )
    assert (
        "atp-botswana-events-2026-v1#bwa-j100-gaborone-2026"
        in bwa_atp.years[2026].ratings["squash_access"].observation_ids
    )

    nam_atp = atp.research.countries["NAM"]
    assert "derived_pre_evidence_context" in atp.observations[
        "atp-namibia-history-v1#nam-pre-documented-baseline-1955-2019"
    ].quality_flags
    assert (
        "atp-namibia-history-v1#nam-play-possible-2020"
        in nam_atp.years[2020].ratings["squash_access"].observation_ids
    )
    assert (
        "atp-namibia-development-2026-v1#nam-eligible-2026"
        in nam_atp.years[2026].ratings["development_quality"].observation_ids
    )
    assert (
        "atp-namibia-events-2026-v1#nam-j60-windhoek-2026"
        in nam_atp.years[2026].ratings["competition_quality"].observation_ids
    )

def test_eswatini_mozambique_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (
            fifa,
            {
                "SWZ": "fifa-earth-swz-model.v1",
                "MOZ": "fifa-earth-moz-model.v1",
            },
        ),
        (
            atp,
            {
                "SWZ": "atp-earth-swz-model.v1",
                "MOZ": "atp-earth-moz-model.v1",
            },
        ),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            assert history.reference_year == 2026
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.method == "derived_estimate"
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    swz_fifa = fifa.research.countries["SWZ"]
    assert (
        "fifa-structural-eswatini-history-v1#swz-created-1968"
        not in swz_fifa.years[1967].ratings["squash_tradition"].observation_ids
    )
    assert (
        "fifa-structural-eswatini-history-v1#swz-created-1968"
        in swz_fifa.years[1968].ratings["squash_tradition"].observation_ids
    )
    assert (
        "fifa-structural-eswatini-history-v1#swz-fifa-caf-1978"
        not in swz_fifa.years[1977].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-eswatini-history-v1#swz-fifa-caf-1978"
        in swz_fifa.years[1978].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-big-count-2006-all-players-v2#swaziland"
        not in swz_fifa.years[2005].ratings["squash_popularity"].observation_ids
    )
    assert (
        "fifa-big-count-2006-all-players-v2#swaziland"
        in swz_fifa.years[2006].ratings["squash_popularity"].observation_ids
    )
    assert all(
        "fifa-professional-2023" not in source_id
        for year in swz_fifa.years.values()
        for rating in year.ratings.values()
        for source_id in rating.source_ids
    )

    moz_fifa = fifa.research.countries["MOZ"]
    assert (
        "fifa-structural-mozambique-history-v1#moz-created-1976"
        not in moz_fifa.years[1975].ratings["squash_tradition"].observation_ids
    )
    assert (
        "fifa-structural-mozambique-history-v1#moz-created-1976"
        in moz_fifa.years[1976].ratings["squash_tradition"].observation_ids
    )
    assert (
        "fifa-structural-mozambique-history-v1#moz-fifa-caf-1980"
        not in moz_fifa.years[1979].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-structural-mozambique-history-v1#moz-fifa-caf-1980"
        in moz_fifa.years[1980].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-professional-2023-players-v2#mozambique-p105"
        not in moz_fifa.years[2022].ratings["competition_quality"].observation_ids
    )
    assert (
        "fifa-professional-2023-players-v2#mozambique-p105"
        in moz_fifa.years[2023].ratings["competition_quality"].observation_ids
    )

    swz_atp = atp.research.countries["SWZ"]
    assert "derived_pre_evidence_context" in atp.observations[
        "atp-eswatini-history-v1#swz-pre-documented-baseline-1955-2019"
    ].quality_flags
    assert (
        "atp-eswatini-history-v1#swz-play-possible-2020"
        not in swz_atp.years[2019].ratings["squash_access"].observation_ids
    )
    assert (
        "atp-eswatini-history-v1#swz-play-possible-2020"
        in swz_atp.years[2020].ratings["squash_access"].observation_ids
    )
    assert (
        "atp-eswatini-development-2026-v1#swz-eligible-2026"
        not in swz_atp.years[2025].ratings["development_quality"].observation_ids
    )
    assert (
        "atp-eswatini-development-2026-v1#swz-eligible-2026"
        in swz_atp.years[2026].ratings["development_quality"].observation_ids
    )

    moz_atp = atp.research.countries["MOZ"]
    assert "derived_pre_evidence_context" in atp.observations[
        "atp-mozambique-history-v1#moz-pre-documented-baseline-1955-2019"
    ].quality_flags
    assert (
        "atp-mozambique-history-v1#moz-play-possible-2020"
        not in moz_atp.years[2019].ratings["squash_access"].observation_ids
    )
    assert (
        "atp-mozambique-history-v1#moz-play-possible-2020"
        in moz_atp.years[2020].ratings["squash_access"].observation_ids
    )
    assert (
        "atp-mozambique-development-2026-v1#moz-eligible-2026"
        not in moz_atp.years[2025].ratings["development_quality"].observation_ids
    )
    assert (
        "atp-mozambique-development-2026-v1#moz-eligible-2026"
        in moz_atp.years[2026].ratings["development_quality"].observation_ids
    )



def test_angola_lesotho_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (fifa, {"ANG": "fifa-earth-ang-model.v1", "LES": "fifa-earth-les-model.v1"}),
        (atp, {"ANG": "atp-earth-ang-model.v1", "LES": "atp-earth-les-model.v1"}),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            assert history.reference_year == 2026
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.method == "derived_estimate"
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    ang_fifa = fifa.research.countries["ANG"]
    assert "fifa-structural-angola-history-v1#ang-created-1979" not in ang_fifa.years[1978].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-angola-history-v1#ang-created-1979" in ang_fifa.years[1979].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-angola-history-v1#ang-fifa-caf-1980" not in ang_fifa.years[1979].ratings["competition_quality"].observation_ids
    assert "fifa-structural-angola-history-v1#ang-fifa-caf-1980" in ang_fifa.years[1980].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#angola" not in ang_fifa.years[2005].ratings["squash_popularity"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#angola" in ang_fifa.years[2006].ratings["squash_popularity"].observation_ids
    assert "fifa-professional-2023-players-v2#angola-p71" not in ang_fifa.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-players-v2#angola-p71" in ang_fifa.years[2023].ratings["competition_quality"].observation_ids

    les_fifa = fifa.research.countries["LES"]
    assert "fifa-structural-lesotho-history-v1#les-fifa-caf-1964" not in les_fifa.years[1963].ratings["competition_quality"].observation_ids
    assert "fifa-structural-lesotho-history-v1#les-fifa-caf-1964" in les_fifa.years[1964].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#lesotho" in les_fifa.years[2006].ratings["squash_popularity"].observation_ids
    assert all(
        "fifa-professional-2023" not in source_id
        for year in les_fifa.years.values()
        for rating in year.ratings.values()
        for source_id in rating.source_ids
    )

    ang_atp = atp.research.countries["ANG"]
    assert "derived_pre_evidence_context" in atp.observations[
        "atp-angola-history-v1#ang-pre-documented-baseline-1955-2019"
    ].quality_flags
    assert "atp-angola-history-v1#ang-status-2020" not in ang_atp.years[2019].ratings["squash_access"].observation_ids
    assert "atp-angola-history-v1#ang-status-2020" in ang_atp.years[2020].ratings["squash_access"].observation_ids
    assert "atp-angola-development-2026-v1#ang-eligible-2026" not in ang_atp.years[2025].ratings["development_quality"].observation_ids
    assert "atp-angola-development-2026-v1#ang-eligible-2026" in ang_atp.years[2026].ratings["development_quality"].observation_ids

    les_atp = atp.research.countries["LES"]
    assert "derived_pre_evidence_context" in atp.observations[
        "atp-lesotho-history-v1#les-pre-documented-baseline-1955-2019"
    ].quality_flags
    assert "atp-lesotho-history-v1#les-status-2020" in les_atp.years[2020].ratings["squash_access"].observation_ids
    assert "atp-lesotho-development-2026-v1#les-eligible-2026" in les_atp.years[2026].ratings["development_quality"].observation_ids


def test_cameroon_benin_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (fifa, {"CMR": "fifa-earth-cmr-model.v1", "BEN": "fifa-earth-ben-model.v1"}),
        (atp, {"CMR": "atp-earth-cmr-model.v1", "BEN": "atp-earth-ben-model.v1"}),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            assert history.reference_year == 2026
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.method == "derived_estimate"
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    cmr = fifa.research.countries["CMR"]
    assert "fifa-structural-cameroon-history-v1#cmr-created-1959" not in cmr.years[1958].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-cameroon-history-v1#cmr-created-1959" in cmr.years[1959].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-cameroon-history-v1#cmr-fifa-1962" in cmr.years[1962].ratings["competition_quality"].observation_ids
    assert "fifa-structural-cameroon-history-v1#cmr-caf-1963" in cmr.years[1963].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#cameroon" in cmr.years[2006].ratings["squash_popularity"].observation_ids
    assert "fifa-professional-2023-players-v2#cameroon-p77" in cmr.years[2023].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#cameroon-p77" in cmr.years[2023].ratings["competition_quality"].observation_ids

    ben = fifa.research.countries["BEN"]
    assert "fifa-structural-benin-history-v1#ben-caf-1962" not in ben.years[1961].ratings["competition_quality"].observation_ids
    assert "fifa-structural-benin-history-v1#ben-caf-1962" in ben.years[1962].ratings["competition_quality"].observation_ids
    assert "fifa-structural-benin-history-v1#ben-fifa-1964" in ben.years[1964].ratings["competition_quality"].observation_ids
    assert "fifa-structural-benin-history-v1#ben-created-1976" in ben.years[1976].ratings["squash_tradition"].observation_ids
    assert "source_chronology_anomaly" in fifa.observations[
        "fifa-structural-benin-history-v1#ben-created-1976"
    ].quality_flags
    assert "fifa-professional-2023-clubs-v2#benin-p72" in ben.years[2023].ratings["competition_quality"].observation_ids
    assert all(
        "fifa-professional-2023-players-v2#benin" not in observation_id
        for year in ben.years.values()
        for rating in year.ratings.values()
        for observation_id in rating.observation_ids
    )

    for code, slug in (("CMR", "cameroon"), ("BEN", "benin")):
        history = atp.research.countries[code]
        key = code.lower()
        assert "derived_pre_evidence_context" in atp.observations[
            f"atp-{slug}-history-v1#{key}-pre-documented-baseline-1955-2019"
        ].quality_flags
        assert f"atp-{slug}-history-v1#{key}-status-2020" not in history.years[2019].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-history-v1#{key}-status-2020" in history.years[2020].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-development-2026-v1#{key}-eligible-2026" in history.years[2026].ratings["development_quality"].observation_ids


def test_gabon_mauritius_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (fifa, {"GAB": "fifa-earth-gab-model.v1", "MUS": "fifa-earth-mus-model.v1"}),
        (atp, {"GAB": "atp-earth-gab-model.v1", "MUS": "atp-earth-mus-model.v1"}),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    gab = fifa.research.countries["GAB"]
    assert "fifa-structural-gabon-history-v1#gab-created-1962" not in gab.years[1961].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-gabon-history-v1#gab-created-1962" in gab.years[1962].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-gabon-history-v1#gab-fifa-1966" in gab.years[1966].ratings["competition_quality"].observation_ids
    assert "fifa-structural-gabon-history-v1#gab-caf-1967" in gab.years[1967].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#gabon-p90" in gab.years[2023].ratings["competition_quality"].observation_ids
    assert all("fifa-professional-2023-players-v2#gabon" not in oid for y in gab.years.values() for r in y.ratings.values() for oid in r.observation_ids)

    mus = fifa.research.countries["MUS"]
    assert "fifa-structural-mauritius-history-v1#mus-created-1952" in mus.years[1955].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-mauritius-history-v1#mus-caf-1953" in mus.years[1955].ratings["competition_quality"].observation_ids
    assert "fifa-structural-mauritius-history-v1#mus-fifa-1964" not in mus.years[1963].ratings["competition_quality"].observation_ids
    assert "fifa-structural-mauritius-history-v1#mus-fifa-1964" in mus.years[1964].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#mauritius-p103" in mus.years[2023].ratings["competition_quality"].observation_ids
    assert all("fifa-professional-2023-players-v2#mauritius" not in oid for y in mus.years.values() for r in y.ratings.values() for oid in r.observation_ids)

    for code, slug in (("GAB", "gabon"), ("MUS", "mauritius")):
        h = atp.research.countries[code]
        key = code.lower()
        assert f"atp-{slug}-history-v1#{key}-status-2020" not in h.years[2019].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-history-v1#{key}-status-2020" in h.years[2020].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-development-2026-v1#{key}-eligible-2026" in h.years[2026].ratings["development_quality"].observation_ids


def test_madagascar_seychelles_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (fifa, {"MDG": "fifa-earth-mdg-model.v1", "SEY": "fifa-earth-sey-model.v1"}),
        (atp, {"MDG": "atp-earth-mdg-model.v1", "SEY": "atp-earth-sey-model.v1"}),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    mdg = fifa.research.countries["MDG"]
    assert "fifa-structural-madagascar-history-v1#mdg-created-1961" not in mdg.years[1960].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-madagascar-history-v1#mdg-created-1961" in mdg.years[1961].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-madagascar-history-v1#mdg-caf-1963" in mdg.years[1963].ratings["competition_quality"].observation_ids
    assert "fifa-structural-madagascar-history-v1#mdg-fifa-1964" in mdg.years[1964].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#madagascar" in mdg.years[2006].ratings["squash_popularity"].observation_ids
    assert all("fifa-professional-2023" not in sid for y in mdg.years.values() for r in y.ratings.values() for sid in r.source_ids)

    sey = fifa.research.countries["SEY"]
    assert "fifa-structural-seychelles-history-v1#sey-created-1979" not in sey.years[1978].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-seychelles-history-v1#sey-created-1979" in sey.years[1979].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-seychelles-history-v1#sey-fifa-1986" in sey.years[1986].ratings["competition_quality"].observation_ids
    assert "fifa-structural-seychelles-history-v1#sey-caf-1986" in sey.years[1986].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#seychelles" in sey.years[2006].ratings["squash_popularity"].observation_ids
    assert all("fifa-professional-2023" not in sid for y in sey.years.values() for r in y.ratings.values() for sid in r.source_ids)

    for code, slug in (("MDG", "madagascar"), ("SEY", "seychelles")):
        h = atp.research.countries[code]
        key = code.lower()
        assert f"atp-{slug}-history-v1#{key}-play-possible-2020" not in h.years[2019].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-history-v1#{key}-play-possible-2020" in h.years[2020].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-development-2026-v1#{key}-eligible-2026" in h.years[2026].ratings["development_quality"].observation_ids


def test_rwanda_burundi_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (fifa, {"RWA": "fifa-earth-rwa-model.v1", "BDI": "fifa-earth-bdi-model.v1"}),
        (atp, {"RWA": "atp-earth-rwa-model.v1", "BDI": "atp-earth-bdi-model.v1"}),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    rwa = fifa.research.countries["RWA"]
    assert "fifa-structural-rwanda-history-v1#rwa-created-1972" not in rwa.years[1971].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-rwanda-history-v1#rwa-created-1972" in rwa.years[1972].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-rwanda-history-v1#rwa-fifa-1978" in rwa.years[1978].ratings["competition_quality"].observation_ids
    assert "fifa-structural-rwanda-history-v1#rwa-caf-1978" in rwa.years[1978].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#rwanda" in rwa.years[2006].ratings["squash_popularity"].observation_ids

    bdi = fifa.research.countries["BDI"]
    assert "fifa-structural-burundi-history-v1#bdi-created-1948" in bdi.years[1955].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-burundi-history-v1#bdi-fifa-1972" in bdi.years[1972].ratings["competition_quality"].observation_ids
    assert "fifa-structural-burundi-history-v1#bdi-caf-1972" in bdi.years[1972].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#burundi" in bdi.years[2006].ratings["squash_popularity"].observation_ids

    for code, slug in (("RWA", "rwanda"), ("BDI", "burundi")):
        h = atp.research.countries[code]
        key = code.lower()
        assert f"atp-{slug}-history-v1#{key}-status-2020" not in h.years[2019].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-history-v1#{key}-status-2020" in h.years[2020].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-development-2026-v1#{key}-eligible-2026" in h.years[2026].ratings["development_quality"].observation_ids


def test_gambia_cape_verde_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (fifa, {"GAM": "fifa-earth-gam-model.v1", "CPV": "fifa-earth-cpv-model.v1"}),
        (atp, {"GAM": "atp-earth-gam-model.v1", "CPV": "atp-earth-cpv-model.v1"}),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    gam = fifa.research.countries["GAM"]
    assert "fifa-structural-gambia-history-v1#gam-created-1952" in gam.years[1955].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-gambia-history-v1#gam-caf-1966" in gam.years[1966].ratings["competition_quality"].observation_ids
    assert "fifa-structural-gambia-history-v1#gam-fifa-1968" in gam.years[1968].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#gambia" in gam.years[2006].ratings["squash_popularity"].observation_ids
    assert all("fifa-professional-2023" not in sid for y in gam.years.values() for r in y.ratings.values() for sid in r.source_ids)

    cpv = fifa.research.countries["CPV"]
    assert "fifa-structural-cape-verde-history-v1#cpv-created-1982" not in cpv.years[1981].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-cape-verde-history-v1#cpv-created-1982" in cpv.years[1982].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-cape-verde-history-v1#cpv-fifa-1986" in cpv.years[1986].ratings["competition_quality"].observation_ids
    assert "fifa-structural-cape-verde-history-v1#cpv-caf-2000" in cpv.years[2000].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#cape-verde-islands" in cpv.years[2006].ratings["squash_popularity"].observation_ids
    assert all("fifa-professional-2023" not in sid for y in cpv.years.values() for r in y.ratings.values() for sid in r.source_ids)

    for code, slug in (("GAM", "gambia"), ("CPV", "cape-verde")):
        h = atp.research.countries[code]
        key = code.lower()
        assert f"atp-{slug}-history-v1#{key}-status-2020" not in h.years[2019].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-history-v1#{key}-status-2020" in h.years[2020].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-development-2026-v1#{key}-eligible-2026" in h.years[2026].ratings["development_quality"].observation_ids


def test_djibouti_comoros_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (fifa, {"DJI": "fifa-earth-dji-model.v1", "COM": "fifa-earth-com-model.v1"}),
        (atp, {"DJI": "atp-earth-dji-model.v1", "COM": "atp-earth-com-model.v1"}),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    dji = fifa.research.countries["DJI"]
    assert "fifa-structural-djibouti-history-v1#dji-created-1979" not in dji.years[1978].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-djibouti-history-v1#dji-created-1979" in dji.years[1979].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-djibouti-history-v1#dji-fifa-1994" in dji.years[1994].ratings["competition_quality"].observation_ids
    assert "fifa-structural-djibouti-history-v1#dji-caf-1994" in dji.years[1994].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#djibouti" in dji.years[2006].ratings["squash_popularity"].observation_ids
    assert all("fifa-professional-2023" not in sid for y in dji.years.values() for r in y.ratings.values() for sid in r.source_ids)

    com = fifa.research.countries["COM"]
    assert "fifa-structural-comoros-history-v1#com-created-1979" not in com.years[1978].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-comoros-history-v1#com-created-1979" in com.years[1979].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-comoros-history-v1#com-fifa-2005" in com.years[2005].ratings["competition_quality"].observation_ids
    assert "fifa-structural-comoros-history-v1#com-caf-2005" in com.years[2005].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#comoros" in com.years[2006].ratings["squash_popularity"].observation_ids
    assert all("fifa-professional-2023" not in sid for y in com.years.values() for r in y.ratings.values() for sid in r.source_ids)

    for code, slug in (("DJI", "djibouti"), ("COM", "comoros")):
        h = atp.research.countries[code]
        key = code.lower()
        assert f"atp-{slug}-history-v1#{key}-status-2020" not in h.years[2019].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-history-v1#{key}-status-2020" in h.years[2020].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-development-2026-v1#{key}-eligible-2026" in h.years[2026].ratings["development_quality"].observation_ids


def test_equatorial_guinea_guinea_bissau_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (fifa, {"EQG": "fifa-earth-eqg-model.v1", "GNB": "fifa-earth-gnb-model.v1"}),
        (atp, {"EQG": "atp-earth-eqg-model.v1", "GNB": "atp-earth-gnb-model.v1"}),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    eqg = fifa.research.countries["EQG"]
    assert "fifa-structural-equatorial-guinea-history-v1#eqg-created-1957" not in eqg.years[1956].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-equatorial-guinea-history-v1#eqg-created-1957" in eqg.years[1957].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-equatorial-guinea-history-v1#eqg-fifa-1986" in eqg.years[1986].ratings["competition_quality"].observation_ids
    assert "fifa-structural-equatorial-guinea-history-v1#eqg-caf-1986" in eqg.years[1986].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#equatorial-guinea" in eqg.years[2006].ratings["squash_popularity"].observation_ids

    gnb = fifa.research.countries["GNB"]
    assert "fifa-structural-guinea-bissau-history-v1#gnb-created-1974" not in gnb.years[1973].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-guinea-bissau-history-v1#gnb-created-1974" in gnb.years[1974].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-guinea-bissau-history-v1#gnb-fifa-1986" in gnb.years[1986].ratings["competition_quality"].observation_ids
    assert "fifa-structural-guinea-bissau-history-v1#gnb-caf-1986" in gnb.years[1986].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#guinea-bissau" in gnb.years[2006].ratings["squash_popularity"].observation_ids

    for code, slug in (("EQG", "equatorial-guinea"), ("GNB", "guinea-bissau")):
        h = atp.research.countries[code]
        key = code.lower()
        assert f"atp-{slug}-history-v1#{key}-status-2020" not in h.years[2019].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-history-v1#{key}-status-2020" in h.years[2020].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-development-2026-v1#{key}-eligible-2026" in h.years[2026].ratings["development_quality"].observation_ids


def test_sao_tome_guinea_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (fifa, {"STP": "fifa-earth-stp-model.v1", "GIN": "fifa-earth-gin-model.v1"}),
        (atp, {"STP": "atp-earth-stp-model.v1", "GIN": "atp-earth-gin-model.v1"}),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    stp = fifa.research.countries["STP"]
    assert "fifa-structural-sao-tome-and-principe-history-v1#stp-created-1975" not in stp.years[1974].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-sao-tome-and-principe-history-v1#stp-created-1975" in stp.years[1975].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-sao-tome-and-principe-history-v1#stp-fifa-1986" in stp.years[1986].ratings["competition_quality"].observation_ids
    assert "fifa-structural-sao-tome-and-principe-history-v1#stp-caf-1986" in stp.years[1986].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#sao-tome-e-principe" in stp.years[2006].ratings["squash_popularity"].observation_ids
    assert all("fifa-professional-2023" not in sid for y in stp.years.values() for r in y.ratings.values() for sid in r.source_ids)

    gin = fifa.research.countries["GIN"]
    assert "fifa-structural-guinea-history-v1#gin-created-1960" not in gin.years[1959].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-guinea-history-v1#gin-created-1960" in gin.years[1960].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-guinea-history-v1#gin-fifa-1962" in gin.years[1962].ratings["competition_quality"].observation_ids
    assert "fifa-structural-guinea-history-v1#gin-caf-1963" in gin.years[1963].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#guinea" in gin.years[2006].ratings["squash_popularity"].observation_ids
    assert "fifa-professional-2023-clubs-v2#guinea-p93" in gin.years[2023].ratings["competition_quality"].observation_ids
    assert all("fifa-professional-2023-players-v2#guinea" not in oid for y in gin.years.values() for r in y.ratings.values() for oid in r.observation_ids)

    stp_atp = atp.research.countries["STP"]
    assert "derived_pre_evidence_context" in atp.observations[
        "atp-sao-tome-and-principe-history-v1#stp-pre-documented-baseline-1955-2025"
    ].quality_flags
    assert "atp-sao-tome-and-principe-history-v1#stp-pre-documented-baseline-1955-2025" in stp_atp.years[2025].ratings["squash_access"].observation_ids
    assert "atp-sao-tome-and-principe-development-2026-v1#stp-eligible-2026" in stp_atp.years[2026].ratings["development_quality"].observation_ids

    gin_atp = atp.research.countries["GIN"]
    assert "atp-guinea-history-v1#gin-status-2020" not in gin_atp.years[2019].ratings["squash_access"].observation_ids
    assert "atp-guinea-history-v1#gin-status-2020" in gin_atp.years[2020].ratings["squash_access"].observation_ids
    assert "atp-guinea-development-2026-v1#gin-eligible-2026" in gin_atp.years[2026].ratings["development_quality"].observation_ids


def test_liberia_sierra_leone_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (fifa, {"LBR": "fifa-earth-lbr-model.v1", "SLE": "fifa-earth-sle-model.v1"}),
        (atp, {"LBR": "atp-earth-lbr-model.v1", "SLE": "atp-earth-sle-model.v1"}),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    lbr = fifa.research.countries["LBR"]
    assert "fifa-structural-liberia-history-v1#lbr-created-1936" in lbr.years[1955].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-liberia-history-v1#lbr-caf-1962" in lbr.years[1962].ratings["competition_quality"].observation_ids
    assert "fifa-structural-liberia-history-v1#lbr-fifa-1964" in lbr.years[1964].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#liberia" in lbr.years[2006].ratings["squash_popularity"].observation_ids

    sle = fifa.research.countries["SLE"]
    assert "fifa-structural-sierra-leone-history-v1#sle-fifa-1959" in sle.years[1959].ratings["competition_quality"].observation_ids
    assert "fifa-structural-sierra-leone-history-v1#sle-created-1960" in sle.years[1960].ratings["squash_tradition"].observation_ids
    assert "source_chronology_anomaly" in fifa.observations[
        "fifa-structural-sierra-leone-history-v1#sle-created-1960"
    ].quality_flags
    assert "fifa-big-count-2006-all-players-v2#sierra-leone" in sle.years[2006].ratings["squash_popularity"].observation_ids

    for code, slug in (("LBR", "liberia"), ("SLE", "sierra-leone")):
        h = atp.research.countries[code]
        key = code.lower()
        assert f"atp-{slug}-history-v1#{key}-status-2020" not in h.years[2019].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-history-v1#{key}-status-2020" in h.years[2020].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-development-2026-v1#{key}-eligible-2026" in h.years[2026].ratings["development_quality"].observation_ids


def test_togo_burkina_faso_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (fifa, {"TGO": "fifa-earth-tgo-model.v1", "BFA": "fifa-earth-bfa-model.v1"}),
        (atp, {"TGO": "atp-earth-tgo-model.v1", "BFA": "atp-earth-bfa-model.v1"}),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    tgo = fifa.research.countries["TGO"]
    assert "fifa-structural-togo-history-v1#tgo-created-1960" not in tgo.years[1959].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-togo-history-v1#tgo-created-1960" in tgo.years[1960].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-togo-history-v1#tgo-fifa-1964" in tgo.years[1964].ratings["competition_quality"].observation_ids
    assert "fifa-structural-togo-history-v1#tgo-caf-1964" in tgo.years[1964].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#togo" in tgo.years[2006].ratings["squash_popularity"].observation_ids

    bfa = fifa.research.countries["BFA"]
    assert "fifa-structural-burkina-faso-history-v1#bfa-created-1960" in bfa.years[1960].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-burkina-faso-history-v1#bfa-caf-1961" in bfa.years[1961].ratings["competition_quality"].observation_ids
    assert "fifa-structural-burkina-faso-history-v1#bfa-fifa-1964" in bfa.years[1964].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#burkina-faso" in bfa.years[2006].ratings["squash_popularity"].observation_ids

    for code, slug in (("TGO", "togo"), ("BFA", "burkina-faso")):
        h = atp.research.countries[code]
        key = code.lower()
        assert f"atp-{slug}-history-v1#{key}-status-2020" in h.years[2020].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-development-2026-v1#{key}-eligible-2026" in h.years[2026].ratings["development_quality"].observation_ids


def test_mali_mauritania_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (fifa, {"MLI": "fifa-earth-mli-model.v1", "MRT": "fifa-earth-mrt-model.v1"}),
        (atp, {"MLI": "atp-earth-mli-model.v1", "MRT": "atp-earth-mrt-model.v1"}),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    mli = fifa.research.countries["MLI"]
    assert "fifa-structural-mali-history-v1#mli-created-1960" in mli.years[1960].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-mali-history-v1#mli-caf-1963" in mli.years[1963].ratings["competition_quality"].observation_ids
    assert "fifa-structural-mali-history-v1#mli-fifa-1964" in mli.years[1964].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#mali" in mli.years[2006].ratings["squash_popularity"].observation_ids
    assert "fifa-professional-2023-clubs-v2#mali-p101" in mli.years[2023].ratings["competition_quality"].observation_ids
    assert all("fifa-professional-2023-players-v2#mali" not in oid for y in mli.years.values() for r in y.ratings.values() for oid in r.observation_ids)

    mrt = fifa.research.countries["MRT"]
    assert "fifa-structural-mauritania-history-v1#mrt-created-1961" in mrt.years[1961].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-mauritania-history-v1#mrt-caf-1968" in mrt.years[1968].ratings["competition_quality"].observation_ids
    assert "fifa-structural-mauritania-history-v1#mrt-fifa-1970" in mrt.years[1970].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#mauritania" in mrt.years[2006].ratings["squash_popularity"].observation_ids
    assert all("fifa-professional-2023" not in sid for y in mrt.years.values() for r in y.ratings.values() for sid in r.source_ids)

    for code, slug in (("MLI", "mali"), ("MRT", "mauritania")):
        h = atp.research.countries[code]
        key = code.lower()
        assert f"atp-{slug}-history-v1#{key}-status-2020" in h.years[2020].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-development-2026-v1#{key}-eligible-2026" in h.years[2026].ratings["development_quality"].observation_ids


def test_niger_chad_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (fifa, {"NER": "fifa-earth-ner-model.v1", "CHA": "fifa-earth-cha-model.v1"}),
        (atp, {"NER": "atp-earth-ner-model.v1", "CHA": "atp-earth-cha-model.v1"}),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    ner = fifa.research.countries["NER"]
    assert "fifa-structural-niger-history-v1#ner-created-1961" in ner.years[1961].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-niger-history-v1#ner-fifa-1964" in ner.years[1964].ratings["competition_quality"].observation_ids
    assert "fifa-structural-niger-history-v1#ner-caf-1967" in ner.years[1967].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#niger" in ner.years[2006].ratings["squash_popularity"].observation_ids
    assert all("fifa-professional-2023" not in sid for y in ner.years.values() for r in y.ratings.values() for sid in r.source_ids)

    cha = fifa.research.countries["CHA"]
    assert "fifa-structural-chad-history-v1#cha-created-1962" in cha.years[1962].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-chad-history-v1#cha-fifa-1964" in cha.years[1964].ratings["competition_quality"].observation_ids
    assert "fifa-structural-chad-history-v1#cha-caf-1964" in cha.years[1964].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#chad" in cha.years[2006].ratings["squash_popularity"].observation_ids
    assert all("fifa-professional-2023" not in sid for y in cha.years.values() for r in y.ratings.values() for sid in r.source_ids)

    for code, slug in (("NER", "niger"), ("CHA", "chad")):
        h = atp.research.countries[code]
        key = code.lower()
        assert f"atp-{slug}-history-v1#{key}-status-2020" in h.years[2020].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-development-2026-v1#{key}-eligible-2026" in h.years[2026].ratings["development_quality"].observation_ids


def test_ethiopia_eritrea_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle, expected_models in (
        (fifa, {"ETH": "fifa-earth-eth-model.v1", "ERI": "fifa-earth-eri-model.v1"}),
        (atp, {"ETH": "atp-earth-eth-model.v1", "ERI": "atp-earth-eri-model.v1"}),
    ):
        for code, model_id in expected_models.items():
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            for year in history.years.values():
                assert len(year.ratings) == 6
                for rating in year.ratings.values():
                    assert rating.calibration_model_id == model_id
                    assert rating.observation_ids
                    assert all(item in bundle.observations for item in rating.observation_ids)

    eth = fifa.research.countries["ETH"]
    assert "fifa-structural-ethiopia-history-v1#eth-created-1943" in eth.years[1955].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-ethiopia-history-v1#eth-fifa-1952" in eth.years[1955].ratings["competition_quality"].observation_ids
    assert "fifa-structural-ethiopia-history-v1#eth-caf-1957" in eth.years[1957].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#ethiopia" in eth.years[2006].ratings["squash_popularity"].observation_ids
    assert "fifa-professional-2023-players-v2#ethiopia-p89" in eth.years[2023].ratings["elite_support"].observation_ids
    assert "fifa-professional-2023-clubs-v2#ethiopia-p89" in eth.years[2023].ratings["competition_quality"].observation_ids

    eri = fifa.research.countries["ERI"]
    assert "fifa-structural-eritrea-history-v1#eri-created-1996" not in eri.years[1995].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-eritrea-history-v1#eri-created-1996" in eri.years[1996].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-eritrea-history-v1#eri-fifa-1998" in eri.years[1998].ratings["competition_quality"].observation_ids
    assert "fifa-structural-eritrea-history-v1#eri-caf-1998" in eri.years[1998].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#eritrea" in eri.years[2006].ratings["squash_popularity"].observation_ids
    assert all("fifa-professional-2023" not in sid for y in eri.years.values() for r in y.ratings.values() for sid in r.source_ids)

    for code, slug in (("ETH", "ethiopia"), ("ERI", "eritrea")):
        h = atp.research.countries[code]
        key = code.lower()
        assert f"atp-{slug}-history-v1#{key}-status-2020" in h.years[2020].ratings["squash_access"].observation_ids
        assert f"atp-{slug}-development-2026-v1#{key}-eligible-2026" in h.years[2026].ratings["development_quality"].observation_ids


def test_sudan_south_sudan_dual_world_histories_are_complete_and_do_not_duplicate_predecessor_evidence():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle in (fifa, atp):
        for code in ("SDN", "SSD"):
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            assert all(len(year.ratings) == 6 for year in history.years.values())

    fifa_ssd = fifa.research.countries["SSD"]
    assert fifa_ssd.years[2010].historical_entity.endswith("present South Sudan territory")
    assert all(
        "sudan-history" not in observation_id or "south-sudan-history" in observation_id
        for rating in fifa_ssd.years[2010].ratings.values()
        for observation_id in rating.observation_ids
    )
    assert "fifa-structural-south-sudan-history-v1#ssd-created-2011" in (
        fifa_ssd.years[2011].ratings["squash_tradition"].observation_ids
    )
    assert "fifa-structural-south-sudan-history-v1#ssd-fifa-2012" in (
        fifa_ssd.years[2012].ratings["competition_quality"].observation_ids
    )

    atp_sdn = atp.research.countries["SDN"]
    assert "atp-sudan-history-v1#sdn-status-2020" in (
        atp_sdn.years[2020].ratings["squash_access"].observation_ids
    )
    assert "atp-sudan-development-2026-v1#sdn-eligible-2026" in (
        atp_sdn.years[2026].ratings["development_quality"].observation_ids
    )

    atp_ssd = atp.research.countries["SSD"]
    assert all(
        not observation_id.startswith("atp-sudan-")
        for rating in atp_ssd.years[2010].ratings.values()
        for observation_id in rating.observation_ids
    )
    assert "atp-south-sudan-federation-2026-v1#ssd-federation-listed-2026" in (
        atp_ssd.years[2026].ratings["squash_tradition"].observation_ids
    )


def test_dza_civ_dual_world_batch_is_complete_resolvable_and_time_gated():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))

    for bundle in (fifa, atp):
        for code in ("DZA", "CIV"):
            history = bundle.research.countries[code]
            assert history.missing_earth_years == []
            assert len(history.years) == 72
            assert history.reference_year == 2026
            assert all(len(year.ratings) == 6 for year in history.years.values())
            assert all(
                observation_id in bundle.observations
                for year in history.years.values()
                for rating in year.ratings.values()
                for observation_id in rating.observation_ids
            )

    fifa_dza = fifa.research.countries["DZA"]
    assert "dza-pre-association-1955-1961" in fifa_dza.years[1961].ratings["squash_tradition"].observation_ids[0]
    assert "fifa-structural-algeria-history-v1#dza-created-1962" in fifa_dza.years[1962].ratings["squash_tradition"].observation_ids
    assert "dza-fifa-1963" not in " ".join(fifa_dza.years[1962].ratings["competition_quality"].observation_ids)
    assert "fifa-structural-algeria-history-v1#dza-fifa-1963" in fifa_dza.years[1963].ratings["competition_quality"].observation_ids
    assert "fifa-structural-algeria-history-v1#dza-caf-1964" in fifa_dza.years[1964].ratings["elite_support"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#algeria" not in fifa_dza.years[2005].ratings["squash_popularity"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#algeria" in fifa_dza.years[2006].ratings["squash_popularity"].observation_ids
    assert "fifa-professional-2023-players-v2#algeria-p70" not in fifa_dza.years[2022].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-players-v2#algeria-p70" in fifa_dza.years[2023].ratings["competition_quality"].observation_ids

    fifa_civ = fifa.research.countries["CIV"]
    assert "fifa-structural-cote-divoire-history-v1#civ-created-1960" in fifa_civ.years[1960].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-cote-divoire-history-v1#civ-fifa-1964" not in fifa_civ.years[1963].ratings["competition_quality"].observation_ids
    assert "fifa-structural-cote-divoire-history-v1#civ-fifa-1964" in fifa_civ.years[1964].ratings["competition_quality"].observation_ids
    assert "fifa-professional-2023-clubs-v2#cote-d-ivoire-p83" in fifa_civ.years[2023].ratings["elite_support"].observation_ids
    assert all(
        "professional-2023-players" not in observation_id
        for rating in fifa_civ.years[2023].ratings.values()
        for observation_id in rating.observation_ids
    )

    atp_dza = atp.research.countries["DZA"]
    assert "atp-algeria-history-v1#dza-federation-created-1962" not in atp_dza.years[1961].ratings["squash_tradition"].observation_ids
    assert "atp-algeria-history-v1#dza-federation-created-1962" in atp_dza.years[1962].ratings["squash_tradition"].observation_ids
    assert "atp-algeria-jti-2021-v1#dza-jti-active-2021" not in atp_dza.years[2020].ratings["development_quality"].observation_ids
    assert "atp-algeria-jti-2021-v1#dza-jti-active-2021" in atp_dza.years[2021].ratings["development_quality"].observation_ids
    assert "atp-algeria-federal-centre-2023-v1#dza-itf-support-and-centre-plan-2023" in atp_dza.years[2023].ratings["elite_support"].observation_ids

    atp_civ = atp.research.countries["CIV"]
    assert "atp-cote-divoire-history-v1#civ-federation-created-1963" not in atp_civ.years[1962].ratings["squash_tradition"].observation_ids
    assert "atp-cote-divoire-history-v1#civ-federation-created-1963" in atp_civ.years[1963].ratings["squash_tradition"].observation_ids
    assert "atp-cote-divoire-history-v1#civ-cat-member-1973" in atp_civ.years[1973].ratings["competition_quality"].observation_ids
    assert "atp-cote-divoire-history-v1#civ-itf-member-1985" in atp_civ.years[1985].ratings["competition_quality"].observation_ids
    assert "atp-cote-divoire-jti-2021-v1#civ-jti-active-2021" in atp_civ.years[2021].ratings["development_quality"].observation_ids
    assert "atp-cote-divoire-history-v1#civ-strategy-2025" in atp_civ.years[2025].ratings["development_quality"].observation_ids
    assert "atp-cote-divoire-development-2026-v1#civ-eligible-2026" in atp_civ.years[2026].ratings["development_quality"].observation_ids


def test_tun_lby_dual_world_batch_is_complete_resolvable_and_temporal():
    fifa = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    atp = load_earth_research_bundle(Path("config/earth_research/atp_earth.json"))
    for bundle in (fifa, atp):
        for code in ("TUN", "LBY"):
            h = bundle.research.countries[code]
            assert h.missing_earth_years == []
            assert len(h.years) == 72
            assert all(len(y.ratings) == 6 for y in h.years.values())
            assert all(oid in bundle.observations for y in h.years.values() for r in y.ratings.values() for oid in r.observation_ids)
    tun = fifa.research.countries["TUN"]
    assert "fifa-structural-tunisia-history-v1#tun-created-1957" in tun.years[1957].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-tunisia-history-v1#tun-fifa-caf-1960" not in tun.years[1959].ratings["competition_quality"].observation_ids
    assert "fifa-structural-tunisia-history-v1#tun-fifa-caf-1960" in tun.years[1960].ratings["competition_quality"].observation_ids
    assert "fifa-big-count-2006-all-players-v2#tunisia" in tun.years[2006].ratings["squash_popularity"].observation_ids
    assert "fifa-professional-2023-clubs-v2#tunisia-p120" in tun.years[2023].ratings["elite_support"].observation_ids
    lby = fifa.research.countries["LBY"]
    assert "fifa-structural-libya-history-v1#lby-created-1962" in lby.years[1962].ratings["squash_tradition"].observation_ids
    assert "fifa-structural-libya-history-v1#lby-fifa-1964" in lby.years[1964].ratings["competition_quality"].observation_ids
    tun_atp = atp.research.countries["TUN"]
    assert "atp-tunisia-ntc-2024-v1#tun-bronze-ntc-2024" in tun_atp.years[2024].ratings["development_quality"].observation_ids
    assert "atp-tunisia-development-2026-v1#tun-eligible-2026" in tun_atp.years[2026].ratings["development_quality"].observation_ids
    lby_atp = atp.research.countries["LBY"]
    assert "atp-libya-development-2026-v1#lby-eligible-2026" in lby_atp.years[2026].ratings["development_quality"].observation_ids
