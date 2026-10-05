from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.build_fifa_country_evidence_index import build_index


def test_country_evidence_index_partitions_all_canonical_fifa_facts() -> None:
    index = build_index()

    assert index["observation_count"] == 1449
    assert index["safe_country_evidence_count"] == 1427
    assert index["manual_review_count"] == 22
    assert index["unresolved_count"] == 0
    assert index["direct_mapped_observation_count"] == 164
    assert index["rating_ready"] is False

    safe_ids = [
        fact["observation_id"]
        for facts in index["countries"].values()
        for fact in facts
    ]
    manual_ids = [fact["observation_id"] for fact in index["manual_review"]]
    unresolved_ids = [fact["observation_id"] for fact in index["unresolved"]]

    all_ids = safe_ids + manual_ids + unresolved_ids
    assert len(all_ids) == 1449
    assert len(all_ids) == len(set(all_ids))


def test_usa_evidence_combines_2006_participation_and_2023_professional_facts() -> None:
    index = build_index()
    usa = index["countries"]["USA"]

    numeric_usa = [
        fact
        for fact in usa
        if fact["measurement_type"] != "football_structural_event"
    ]
    structural_usa = [
        fact
        for fact in usa
        if fact["measurement_type"] == "football_structural_event"
    ]
    assert len(numeric_usa) == 8
    assert len(structural_usa) == 8
    assert {fact["observation_year"] for fact in numeric_usa} == {2006, 2023}

    by_type = {fact["measurement_type"]: fact for fact in numeric_usa}
    assert by_type["players_all_registered_and_unregistered"]["numeric_value"] == 24_472_778
    assert by_type["players_registered_or_association_reported"]["numeric_value"] == 4_186_778
    assert by_type["professional_male_players_reported"]["numeric_value"] == 2_791
    assert by_type["professional_clubs_reported"]["numeric_value"] == 101
    assert by_type["fifa_mens_year_end_world_rank"]["numeric_value"] == 12

    assert {fact["identity_status"] for fact in usa} == {"direct"}
    assert {fact["earth_country_code"] for fact in usa} == {"USA"}
    assert {
        fact["identity_method"]
        for fact in structural_usa
    } == {"explicit_reviewed_event_to_earth"}


def test_gbr_keeps_home_associations_as_components_not_synthetic_totals() -> None:
    index = build_index()
    gbr = index["countries"]["GBR"]

    assert len(gbr) == 26
    assert {fact["identity_status"] for fact in gbr} == {"aggregate_member"}
    assert {fact["source_entity"] for fact in gbr} == {
        "England",
        "Scotland",
        "Wales",
        "Northern Ireland",
        "ENGLAND",
        "SCOTLAND",
        "WALES",
    }

    big_count = [fact for fact in gbr if fact["observation_year"] == 2006]
    professional = [fact for fact in gbr if fact["observation_year"] == 2023]

    assert len(big_count) == 20
    assert len(professional) == 6
    assert not any(fact["source_entity"] == "NORTHERN IRELAND" for fact in professional)


def test_kuwait_page_37_is_safe_but_page_38_stays_manual() -> None:
    index = build_index()

    kuwait = index["countries"]["KWT"]
    safe_page_37 = [
        fact
        for fact in kuwait
        if fact["source_id"] == "fifa-professional-2023"
        and fact["source_page"] == 37
    ]
    assert len(safe_page_37) == 2
    assert {fact["identity_status"] for fact in safe_page_37} == {"direct"}

    manual_page_38 = [
        fact
        for fact in index["manual_review"]
        if fact["source_id"] == "fifa-professional-2023"
        and fact["source_page"] == 38
    ]
    assert len(manual_page_38) == 2
    assert {fact["source_entity"] for fact in manual_page_38} == {"KUWAIT"}
    assert {tuple(fact["candidate_earth_codes"]) for fact in manual_page_38} == {("KGZ",)}

    kgz_professional = [
        fact
        for fact in index["countries"]["KGZ"]
        if fact["source_id"] == "fifa-professional-2023"
    ]
    assert all(fact["source_page"] != 38 for fact in kgz_professional)


def test_manual_big_count_historical_geographies_never_enter_safe_country_index() -> None:
    index = build_index()

    expected_manual_entities = {
        "Netherlands Antilles",
        "Curacao",
        "Serbia",
        "Sudan",
    }
    big_count_manual = [
        fact
        for fact in index["manual_review"]
        if fact["source_id"] == "fifa-big-count-2006"
    ]

    assert len(big_count_manual) == 20
    assert {fact["source_entity"] for fact in big_count_manual} == expected_manual_entities
    assert all(fact["earth_country_code"] is None for fact in big_count_manual)



def test_structural_events_enter_safe_country_evidence_without_fake_numeric_values() -> None:
    index = build_index()

    japan = [
        fact
        for fact in index["countries"]["JPN"]
        if fact["measurement_type"] == "football_structural_event"
    ]
    assert len(japan) == 6
    assert {fact["observation_year"] for fact in japan} == {
        1921,
        1965,
        1977,
        1986,
        1991,
        1993,
    }
    assert all(fact["numeric_value"] is None for fact in japan)
    assert all(fact["text_value"] for fact in japan)
    assert all(fact["identity_status"] == "direct" for fact in japan)


def test_morocco_source_timing_conflict_is_preserved_as_two_safe_facts() -> None:
    index = build_index()

    events = [
        fact
        for fact in index["countries"]["MAR"]
        if fact["measurement_type"] == "football_structural_event"
        and any(
            flag == "conflict_group:mar-mohammed-vi-academy-timing"
            for flag in fact["quality_flags"]
        )
    ]
    assert len(events) == 2
    assert {fact["observation_year"] for fact in events} == {2009, 2019}
    assert all("source_timing_conflict" in fact["quality_flags"] for fact in events)



def test_heldout_structural_facts_are_safe_but_explicitly_labelled() -> None:
    index = build_index()

    heldout_codes = {"DEU", "BRA", "ISL", "SMR"}
    heldout = [
        fact
        for code in heldout_codes
        for fact in index["countries"][code]
        if fact["measurement_type"] == "football_structural_event"
    ]

    assert len(heldout) == 14
    assert all(
        "held_out_validation_country" in fact["quality_flags"]
        for fact in heldout
    )
    assert all(fact["identity_status"] == "direct" for fact in heldout)


def test_explicit_reviewed_country_fact_is_admitted_without_global_identity_resolution() -> None:
    index = build_index()
    nzl_ids = {item["observation_id"] for item in index["countries"]["NZL"]}

    assert (
        "fifa-structural-ofc-new-zealand-grassroots-2011-v1#nzl-u19-organised-players-2011"
        in nzl_ids
    )


def test_pacific_association_identities_resolve_to_earth_territories_without_sovereign_collapse() -> None:
    index = build_index()

    expected = {
        "ASM": "fifa-big-count-2006-all-players-v2#american-samoa",
        "PYF": "fifa-big-count-2006-all-players-v2#tahiti",
        "NCL": "fifa-big-count-2006-all-players-v2#new-caledonia",
    }
    for earth_code, observation_id in expected.items():
        facts = {
            fact["observation_id"]: fact
            for fact in index["countries"][earth_code]
        }
        assert observation_id in facts
        assert facts[observation_id]["earth_country_code"] == earth_code

    pyf_ids = {
        fact["observation_id"]
        for fact in index["countries"]["PYF"]
    }
    ncl_ids = {
        fact["observation_id"]
        for fact in index["countries"]["NCL"]
    }
    assert "fifa-structural-ofc-tahiti-profile-v1#pyf-ftf-foundation-1989" in pyf_ids
    assert "fifa-structural-ofc-new-caledonia-profile-v1#ncl-fcf-foundation-1928" in ncl_ids
    assert not any("france" in observation_id.lower() for observation_id in pyf_ids | ncl_ids)
