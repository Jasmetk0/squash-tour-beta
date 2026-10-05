from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_package_builder import load_earth_research_bundle


def test_fifa_first_reviewed_country_histories_are_complete_and_resolvable():
    bundle = load_earth_research_bundle(Path("config/earth_research/fifa_earth.json"))
    assert set(bundle.research.countries) == {"CZE", "SVK", "JPN", "IND", "MAR", "SEN", "FRO", "USA", "ZAF", "BRA", "DEU", "ISL", "SMR", "ARG", "MEX", "AUS", "NZL", "FJI", "PNG", "SLB", "COK", "ASM", "PYF", "NCL", "WSM", "TON", "VUT", "FRA", "ESP", "ITA", "NLD", "BEL", "PRT", "AUT", "DNK", "SWE", "CHE", "NOR", "FIN", "HRV", "SVN", "POL", "ROU", "UKR", "LTU", "LVA", "EST", "CAN"}
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
    expected_countries = {"CZE", "DEU", "USA", "AUS", "ESP", "SRB", "FRA", "GBR", "ARG", "JPN", "CAN", "ITA", "NED", "SWE", "SUI", "CRO", "POL", "CHN", "NOR", "GRE", "BEL", "ZAF", "DEN", "FIN", "NZL", "PRT", "IRL", "HUN", "ROU", "SVN", "SVK", "ISR", "BGR", "AUT", "TUR", "CYP", "BRA", "CHL", "COL", "MEX", "ECU", "IND", "KOR", "THA", "KAZ", "LVA", "EST", "LTU"}
    assert set(bundle.research.countries) == expected_countries
    assert bundle.research.data_cutoff.isoformat() == "2026-10-04"
    assert len(bundle.datasets) == 162
    assert len(bundle.observations) == 462

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
