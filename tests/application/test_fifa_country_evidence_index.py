from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.build_fifa_country_evidence_index import build_index


def test_country_evidence_index_partitions_all_canonical_fifa_facts() -> None:
    index = build_index()

    assert index["observation_count"] == 1285
    assert index["contextual_observation_count"] == 15
    assert index["safe_country_evidence_count"] == 1263
    assert index["manual_review_count"] == 22
    assert index["unresolved_count"] == 0
    assert index["rating_ready"] is False

    safe_ids = [
        fact["observation_id"]
        for facts in index["countries"].values()
        for fact in facts
    ]
    manual_ids = [fact["observation_id"] for fact in index["manual_review"]]
    unresolved_ids = [fact["observation_id"] for fact in index["unresolved"]]

    all_ids = safe_ids + manual_ids + unresolved_ids
    assert len(all_ids) == 1285
    assert len(all_ids) == len(set(all_ids))
    assert set(index["contextual_observation_dataset_sha256s"]) == {
        "uefa-czechia-history-events-v2",
        "uefa-czech-republic-2005-06-snapshot-v2",
    }
    assert len(index["input_observation_dataset_sha256s"]) == 7


def test_usa_evidence_combines_2006_participation_and_2023_professional_facts() -> None:
    index = build_index()
    usa = index["countries"]["USA"]

    assert len(usa) == 7
    assert {fact["observation_year"] for fact in usa} == {2006, 2023}

    by_type = {fact["measurement_type"]: fact for fact in usa}
    assert by_type["players_all_registered_and_unregistered"]["numeric_value"] == 24_472_778
    assert by_type["players_registered_or_association_reported"]["numeric_value"] == 4_186_778
    assert by_type["professional_male_players_reported"]["numeric_value"] == 2_791
    assert by_type["professional_clubs_reported"]["numeric_value"] == 101

    assert {fact["identity_status"] for fact in usa} == {"direct"}
    assert {fact["earth_country_code"] for fact in usa} == {"USA"}


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
